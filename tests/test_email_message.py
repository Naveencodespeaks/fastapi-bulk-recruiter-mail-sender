from app.config import Settings
from app.email_service import EmailService


def test_message_has_exactly_one_to_and_no_cc_or_bcc():
    settings = Settings(
        _env_file=None,
        smtp_username="sender@example.com",
        smtp_password="secret",
        smtp_from_email="sender@example.com",
        smtp_from_name="Sai Naveen",
    )
    service = EmailService(settings)

    message = service.build_message(
        recipient="recruiter@example.com",
        subject="Application",
        body="Please find my résumé attached.",
        resume_bytes=b"%PDF-1.4 test",
        resume_filename="SaiNaveen_AI_Engineer.pdf",
    )

    assert message["To"] == "recruiter@example.com"
    assert message["Cc"] is None
    assert message["Bcc"] is None
    assert len(list(message.iter_attachments())) == 1
