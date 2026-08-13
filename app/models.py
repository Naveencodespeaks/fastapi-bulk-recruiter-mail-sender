from pydantic import BaseModel, Field


class RecipientValidationRequest(BaseModel):
    recipients: str = Field(min_length=3, max_length=250_000)


class RecipientValidationResponse(BaseModel):
    valid: list[str]
    invalid: list[str]
    duplicate_count: int
    total_tokens: int
    within_limit: bool
    max_recipients: int


class FailureDetail(BaseModel):
    email: str
    error: str


class JobSnapshot(BaseModel):
    id: str
    status: str
    total: int
    processed: int
    sent: int
    failed: int
    duplicate_count: int
    progress_percent: float
    resume_filename: str
    subject: str
    dry_run: bool
    failures: list[FailureDetail]
    created_at: str
    started_at: str | None
    completed_at: str | None
