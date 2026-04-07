import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings


logger = logging.getLogger(__name__)


def send_verification_code_email(*, email: str, code: str) -> None:
    subject = "Verify your Orbit account"
    body = f"Your Orbit verification code is: {code}"
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.EMAIL_FROM
    message["To"] = email
    message.set_content(body)

    if settings.EMAIL_SENDER_MODE == "console":
        print(
            f"[orbit-email] to={email} subject={subject} verification_code={code}",
            flush=True,
        )
        return

    if settings.EMAIL_SENDER_MODE == "smtp" and settings.SMTP_HOST:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        logger.info("Verification email sent via SMTP to %s", email)
        return

    logger.warning(
        "Unsupported EMAIL_SENDER_MODE '%s'; falling back to console logging.",
        settings.EMAIL_SENDER_MODE,
    )
    print(
        f"[orbit-email] to={email} subject={subject} verification_code={code}",
        flush=True,
    )
