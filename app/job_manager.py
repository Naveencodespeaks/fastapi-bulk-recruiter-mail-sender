import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .config import Settings
from .email_service import EmailService


TERMINAL_STATUSES = {"completed", "cancelled", "failed"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_error(error: Exception) -> str:
    message = f"{type(error).__name__}: {error}".replace("\r", " ").replace("\n", " ")
    return message[:400]


@dataclass
class EmailJob:
    id: str
    recipients: list[str]
    subject: str
    body: str
    resume_path: str
    resume_filename: str
    duplicate_count: int
    dry_run: bool

    status: str = "queued"
    processed: int = 0
    sent: int = 0
    failed: int = 0
    failures: list[dict[str, str]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    started_at: str | None = None
    completed_at: str | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def mark_running(self) -> None:
        with self.lock:
            if self.status == "queued":
                self.status = "running"
                self.started_at = utc_now_iso()

    def mark_success(self) -> None:
        with self.lock:
            self.processed += 1
            self.sent += 1

    def mark_failure(self, email: str, error: Exception) -> None:
        with self.lock:
            self.processed += 1
            self.failed += 1
            self.failures.append({"email": email, "error": safe_error(error)})

    def mark_completed(self) -> None:
        with self.lock:
            self.status = "completed"
            self.completed_at = utc_now_iso()

    def mark_cancelled(self) -> None:
        with self.lock:
            self.status = "cancelled"
            self.completed_at = utc_now_iso()

    def mark_fatal_failure(self, error: Exception) -> None:
        with self.lock:
            remaining = len(self.recipients) - self.processed
            if remaining > 0:
                self.failed += remaining
                self.processed += remaining
                self.failures.append(
                    {"email": "*job*", "error": safe_error(error)}
                )
            self.status = "failed"
            self.completed_at = utc_now_iso()

    def request_cancel(self) -> None:
        self.cancel_event.set()

    def snapshot(self) -> dict:
        with self.lock:
            total = len(self.recipients)
            percentage = round((self.processed / total) * 100, 2) if total else 0.0
            return {
                "id": self.id,
                "status": self.status,
                "total": total,
                "processed": self.processed,
                "sent": self.sent,
                "failed": self.failed,
                "duplicate_count": self.duplicate_count,
                "progress_percent": percentage,
                "resume_filename": self.resume_filename,
                "subject": self.subject,
                "dry_run": self.dry_run,
                "failures": list(self.failures),
                "created_at": self.created_at,
                "started_at": self.started_at,
                "completed_at": self.completed_at,
            }


class JobManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.email_service = EmailService(settings)
        self.jobs: dict[str, EmailJob] = {}
        self.queue: asyncio.Queue[str | None] = asyncio.Queue()
        self.worker_task: asyncio.Task | None = None
        self.stopping = False

    async def start(self) -> None:
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        self.worker_task = asyncio.create_task(self._worker(), name="email-job-worker")

    async def stop(self) -> None:
        self.stopping = True
        for job in self.jobs.values():
            if job.snapshot()["status"] not in TERMINAL_STATUSES:
                job.request_cancel()
        await self.queue.put(None)
        if self.worker_task:
            await self.worker_task

    async def _worker(self) -> None:
        while True:
            job_id = await self.queue.get()
            try:
                if job_id is None:
                    return
                job = self.jobs.get(job_id)
                if job is None:
                    continue
                await asyncio.to_thread(self.email_service.process_job, job)
            finally:
                self.queue.task_done()

    async def create_job(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        resume_bytes: bytes,
        resume_filename: str,
        duplicate_count: int,
    ) -> EmailJob:
        if self.stopping:
            raise RuntimeError("The application is shutting down.")

        job_id = uuid4().hex
        resume_path = self.settings.upload_dir / f"{job_id}.pdf"
        resume_path.write_bytes(resume_bytes)

        job = EmailJob(
            id=job_id,
            recipients=recipients,
            subject=subject,
            body=body,
            resume_path=str(resume_path),
            resume_filename=resume_filename,
            duplicate_count=duplicate_count,
            dry_run=self.settings.smtp_dry_run,
        )
        self.jobs[job_id] = job
        await self.queue.put(job_id)
        return job

    def get_job(self, job_id: str) -> EmailJob | None:
        return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> EmailJob | None:
        job = self.jobs.get(job_id)
        if job:
            job.request_cancel()
        return job
