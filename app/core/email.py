"""SendGrid transactional email transport.

Thin wrapper over the official `sendgrid` client. Callers hand over recipients,
a subject and body content; everything provider-specific stays in this module.
"""

import asyncio
import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, Mail, MimeType, To

from ..config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when the provider rejects or fails to accept a message."""


def is_email_configured() -> bool:
    return bool(settings.SENDGRID_API_KEY and settings.EMAILS_FROM)


def build_otp_email(recipient: str, code: str) -> Mail:
    """Compose the email verification message for a freshly issued OTP."""
    minutes = settings.OTP_EXPIRY_MINUTES
    message = Mail(
        from_email=(settings.EMAILS_FROM, settings.EMAILS_FROM_NAME),
        to_emails=To(recipient),
        subject="Verify your Spaces account",
    )
    message.add_content(
        Content(
            MimeType.text,
            f"Your email verification code is {code}\n\n"
            f"It expires in {minutes} minutes. "
            "If you did not create a Spaces account you can ignore this message.",
        )
    )
    message.add_content(
        Content(
            MimeType.html,
            "<p>Your email verification code is:</p>"
            f'<p style="font-size:28px;font-weight:700;letter-spacing:4px;margin:16px 0;">{code}</p>'
            f"<p>It expires in {minutes} minutes.</p>"
            "<p>If you did not create a Spaces account you can ignore this message.</p>",
        )
    )
    return message


def _send_sync(mail: Mail) -> None:
    """Blocking SendGrid call, executed in a worker thread."""
    client = SendGridAPIClient(settings.SENDGRID_API_KEY)
    response = client.send(mail)
    status = getattr(response, "status_code", 0)
    if status < 200 or status >= 300:
        raise EmailDeliveryError(f"SendGrid rejected the message with status {status}")


async def send_email(recipient: str, code: str) -> None:
    """Send the OTP email to `recipient` via SendGrid.

    The provider call is blocking, so it is pushed onto a worker thread to keep
    the event loop responsive.
    """
    if not settings.SENDGRID_API_KEY:
        raise EmailDeliveryError("SENDGRID_API_KEY is not configured")

    if not settings.EMAILS_FROM:
        raise EmailDeliveryError("EMAILS_FROM is not configured")

    mail = build_otp_email(recipient, code)
    try:
        await asyncio.to_thread(_send_sync, mail)
    except EmailDeliveryError:
        raise
    except Exception as exc:
        raise EmailDeliveryError(f"SendGrid request failed: {exc}") from exc

    logger.info("Verification email dispatched to %s via SendGrid", recipient)
