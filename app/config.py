from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


DEFAULT_SUBJECT = (
    "Application for Python / AI Engineer | FastAPI, GenAI, RAG, AWS"
)

DEFAULT_BODY = """Dear Hiring Manager,

I hope you are doing well.

I am Sai Naveen Adep, an AI Automation Engineer and Python Developer with over 2+ years of experience in building scalable backend applications using Python and FastAPI, also Generative AI solutions, agentic AI workflows, RAG pipelines.

My core technical skills include Python, FastAPI, LangChain, LangGraph, n8n, RAG, LLM integration, PostgreSQL, Docker, AWS, GitHub Actions, and REST API development.

Please find my résumé attached for your consideration.

Thank you for your time.

Best regards,
Sai Naveen Adep
AI Automation Engineer | Python Developer
+91 9391267369
sainaveenadepu@gmail.com
LinkedIn: linkedin.com/in/sainaveenadepu666
Location: Hyderabad, India
"""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Bulk Recruiter Email Sender"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    bulk_max_recipients: int = Field(default=500, ge=1, le=10000)
    bulk_send_delay_seconds: float = Field(default=3.0, ge=0, le=3600)
    smtp_reconnect_every: int = Field(default=40, ge=1, le=10000)
    smtp_timeout_seconds: int = Field(default=30, ge=5, le=300)
    max_resume_size_mb: int = Field(default=10, ge=1, le=50)

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Sai Naveen"

    smtp_starttls: bool = True
    smtp_use_ssl: bool = False
    smtp_dry_run: bool = False

    upload_dir: Path = PROJECT_ROOT / "runtime_uploads"
    default_subject: str = DEFAULT_SUBJECT
    default_body: str = DEFAULT_BODY

    @property
    def resolved_from_email(self) -> str:
        return self.smtp_from_email.strip() or self.smtp_username.strip()

    @property
    def smtp_configured(self) -> bool:
        if self.smtp_dry_run:
            return True

        return bool(
            self.smtp_host.strip()
            and self.smtp_username.strip()
            and self.smtp_password.strip()
            and self.resolved_from_email
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()