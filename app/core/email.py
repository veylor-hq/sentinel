from app.core.config import config
import aiosmtplib
from email.message import EmailMessage
from typing import Optional


async def send_email(
    to: str,
    subject: str,
    body: str,
    sender: Optional[str] = None,
):
    """
    Send an email using SMTP (works with Mailpit, Mailhog, or real providers).
    """
    if not config.SMTP_HOST or not config.SMTP_PORT or not config.SMTP_SENDER:
        print("SMTP is not configured, skipping email sending.")
        # TODO: add logging
        return
    message = EmailMessage()
    message["From"] = sender or config.SMTP_SENDER
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=config.SMTP_HOST,
        port=config.SMTP_PORT,
        username=config.SMTP_USER,
        password=config.SMTP_PASSWORD,
        start_tls=config.START_TLS,
        use_tls=config.USE_TLS,
    )
