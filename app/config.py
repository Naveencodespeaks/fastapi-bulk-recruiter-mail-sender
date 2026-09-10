from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_SUBJECT = (
    "Application for DevOps Engineer | AWS, Docker, Jenkins, Terraform, Kubernetes"
)

DEFAULT_BODY = """Dear Hiring Manager,

I am writing to express my interest in the DevOps Engineer position at your organization.

I am Sai Naveen Adep, an AI Generalist and Python Developer transitioning into Cloud and DevOps Engineering, with hands-on experience building, containerizing, deploying, and automating applications.

My technical experience includes:

- Linux and Shell Scripting
- Git and GitHub
- Docker and Docker Compose
- Jenkins and CI/CD Pipelines
- AWS including EC2, VPC, ECR, and EKS
- Terraform for Infrastructure as Code
- Kubernetes and Container Orchestration
- Application Deployment and Troubleshooting
- Monitoring and Observability Concepts
- Python and Backend Application Development

I have been working on practical DevOps projects involving Dockerized applications, Jenkins CI/CD pipelines, AWS infrastructure, Terraform, Kubernetes, and deployment automation. I am particularly interested in building reliable, scalable, and automated cloud infrastructure.

I am highly motivated to grow my career in DevOps and Cloud Engineering and would welcome the opportunity to contribute to your team. I am available to join immediately and am open to relocation if required.

Please find my resume attached for your consideration. I would appreciate the opportunity to discuss how my skills and experience align with the role.

Thank you for your time and consideration.

Best regards,
Sai Naveen Adep
AI Generalist | DevOps Engineer | AI Automation & Python Developer
Phone: +91 9391267369
Email: sainaveenadepu@gmail.com
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
