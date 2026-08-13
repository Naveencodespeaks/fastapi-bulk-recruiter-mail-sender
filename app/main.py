import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import get_settings
from .email_utils import parse_and_validate_recipients
from .job_manager import JobManager, TERMINAL_STATUSES
from .models import (
    JobSnapshot,
    RecipientValidationRequest,
    RecipientValidationResponse,
)


BASE_DIR = Path(__file__).resolve().parent
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = JobManager(settings)
    await manager.start()
    app.state.job_manager = manager
    yield
    await manager.stop()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_manager(request: Request) -> JobManager:
    return request.app.state.job_manager


def validate_header_value(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} is required.",
        )
    if "\r" in cleaned or "\n" in cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} cannot contain line breaks.",
        )
    return cleaned


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_name": settings.app_name},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/config")
async def config():
    return {
        "max_recipients": settings.bulk_max_recipients,
        "send_delay_seconds": settings.bulk_send_delay_seconds,
        "reconnect_every": settings.smtp_reconnect_every,
        "smtp_configured": settings.smtp_configured,
        "dry_run": settings.smtp_dry_run,
        "default_subject": settings.default_subject,
        "default_body": settings.default_body,
        "max_resume_size_mb": settings.max_resume_size_mb,
    }


@app.post(
    "/api/recipients/validate",
    response_model=RecipientValidationResponse,
)
async def validate_recipients(payload: RecipientValidationRequest):
    parsed = parse_and_validate_recipients(payload.recipients)
    return RecipientValidationResponse(
        valid=parsed.valid,
        invalid=parsed.invalid,
        duplicate_count=parsed.duplicate_count,
        total_tokens=parsed.total_tokens,
        within_limit=len(parsed.valid) <= settings.bulk_max_recipients,
        max_recipients=settings.bulk_max_recipients,
    )


@app.post(
    "/api/jobs",
    response_model=JobSnapshot,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_job(
    request: Request,
    recipients: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    confirmation: bool = Form(...),
    resume: UploadFile = File(...),
):
    if not confirmation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Confirm that you are authorized to contact these recipients.",
        )

    if not settings.smtp_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMTP is not configured. Update the .env file and restart the server.",
        )

    parsed = parse_and_validate_recipients(recipients)

    if not parsed.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid email addresses were supplied.",
        )

    if parsed.invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Correct or remove invalid email addresses before sending.",
                "invalid": parsed.invalid,
            },
        )

    if len(parsed.valid) > settings.bulk_max_recipients:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"The batch contains {len(parsed.valid)} unique recipients; "
                f"the configured limit is {settings.bulk_max_recipients}."
            ),
        )

    clean_subject = validate_header_value(subject, "Subject")
    clean_body = body.strip()
    if not clean_body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email body is required.",
        )
    if len(clean_body) > 100_000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email body is too large.",
        )

    filename = Path(resume.filename or "SaiNaveen_AI_Engineer.pdf").name
    if Path(filename).suffix.casefold() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The résumé must be a PDF file.",
        )

    max_bytes = settings.max_resume_size_mb * 1024 * 1024
    resume_bytes = await resume.read(max_bytes + 1)
    await resume.close()

    if len(resume_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"The résumé exceeds {settings.max_resume_size_mb} MB.",
        )
    if not resume_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded file does not appear to be a valid PDF.",
        )

    manager = get_manager(request)
    job = await manager.create_job(
        recipients=parsed.valid,
        subject=clean_subject,
        body=clean_body,
        resume_bytes=resume_bytes,
        resume_filename=filename,
        duplicate_count=parsed.duplicate_count,
    )
    return job.snapshot()


@app.get("/api/jobs/{job_id}", response_model=JobSnapshot)
async def get_job(job_id: str, request: Request):
    job = get_manager(request).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.snapshot()


@app.post("/api/jobs/{job_id}/cancel", response_model=JobSnapshot)
async def cancel_job(job_id: str, request: Request):
    job = get_manager(request).cancel_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.snapshot()


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str, request: Request):
    manager = get_manager(request)
    if manager.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    async def event_stream():
        previous_payload = None

        while True:
            if await request.is_disconnected():
                return

            job = manager.get_job(job_id)
            if job is None:
                yield 'event: error\ndata: {"detail":"Job not found"}\n\n'
                return

            snapshot = job.snapshot()
            payload = json.dumps(snapshot)

            if payload != previous_payload:
                yield f"data: {payload}\n\n"
                previous_payload = payload

            if snapshot["status"] in TERMINAL_STATUSES:
                return

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
