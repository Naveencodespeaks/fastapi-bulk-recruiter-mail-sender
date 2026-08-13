import mimetypes
import smtplib
import ssl
import time
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import TYPE_CHECKING

from .config import Settings

if TYPE_CHECKING:
    from .job_manager import EmailJob


class EmailService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _connect(self) -> smtplib.SMTP:
        context = ssl.create_default_context()

        if self.settings.smtp_use_ssl:
            client: smtplib.SMTP = smtplib.SMTP_SSL(
                self.settings.smtp_host,
                self.settings.smtp_port,
                timeout=self.settings.smtp_timeout_seconds,
                context=context,
            )
        else:
            client = smtplib.SMTP(
                self.settings.smtp_host,
                self.settings.smtp_port,
                timeout=self.settings.smtp_timeout_seconds,
            )
            client.ehlo()
            if self.settings.smtp_starttls:
                client.starttls(context=context)
                client.ehlo()

        client.login(
            self.settings.smtp_username,
            self.settings.smtp_password,
        )
        return client

    @staticmethod
    def _close(client: smtplib.SMTP | None) -> None:
        if client is None:
            return
        try:
            client.quit()
        except (smtplib.SMTPException, OSError):
            try:
                client.close()
            except OSError:
                pass

    def build_message(
        self,
        recipient: str,
        subject: str,
        body: str,
        resume_bytes: bytes,
        resume_filename: str,
    ) -> EmailMessage:
        message = EmailMessage()
        message["From"] = formataddr(
            (self.settings.smtp_from_name, self.settings.resolved_from_email)
        )
        message["To"] = recipient
        message["Subject"] = subject
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = make_msgid()
        message.set_content(body)

        mime_type, _ = mimetypes.guess_type(resume_filename)
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "pdf"

        message.add_attachment(
            resume_bytes,
            maintype=maintype,
            subtype=subtype,
            filename=resume_filename,
        )
        return message

    def process_job(self, job: "EmailJob") -> None:
        resume_path = Path(job.resume_path)
        resume_bytes = resume_path.read_bytes()
        client: smtplib.SMTP | None = None
        attempts_on_connection = 0

        try:
            job.mark_running()

            for index, recipient in enumerate(job.recipients):
                if job.cancel_event.is_set():
                    job.mark_cancelled()
                    return

                if self.settings.smtp_dry_run:
                    # Build the complete message even in dry-run mode so header and
                    # attachment errors are detected without contacting an SMTP server.
                    self.build_message(
                        recipient,
                        job.subject,
                        job.body,
                        resume_bytes,
                        job.resume_filename,
                    )
                    job.mark_success()
                else:
                    if (
                        client is None
                        or attempts_on_connection >= self.settings.smtp_reconnect_every
                    ):
                        self._close(client)
                        client = self._connect()
                        attempts_on_connection = 0

                    message = self.build_message(
                        recipient,
                        job.subject,
                        job.body,
                        resume_bytes,
                        job.resume_filename,
                    )

                    try:
                        client.send_message(
                            message,
                            from_addr=self.settings.resolved_from_email,
                            to_addrs=[recipient],
                        )
                        attempts_on_connection += 1
                        job.mark_success()
                    except smtplib.SMTPServerDisconnected:
                        # Retry once on a fresh connection. A disconnect after the SMTP
                        # server accepted a message can make delivery status uncertain.
                        self._close(client)
                        client = None
                        try:
                            client = self._connect()
                            client.send_message(
                                message,
                                from_addr=self.settings.resolved_from_email,
                                to_addrs=[recipient],
                            )
                            attempts_on_connection = 1
                            job.mark_success()
                        except Exception as retry_error:
                            self._close(client)
                            client = None
                            job.mark_failure(recipient, retry_error)
                    except Exception as send_error:
                        job.mark_failure(recipient, send_error)
                        self._close(client)
                        client = None

                if (
                    index < len(job.recipients) - 1
                    and not job.cancel_event.is_set()
                    and self.settings.bulk_send_delay_seconds > 0
                ):
                    job.cancel_event.wait(self.settings.bulk_send_delay_seconds)

            if job.cancel_event.is_set():
                job.mark_cancelled()
            else:
                job.mark_completed()
        except Exception as fatal_error:
            job.mark_fatal_failure(fatal_error)
        finally:
            self._close(client)
            try:
                resume_path.unlink(missing_ok=True)
            except OSError:
                pass
