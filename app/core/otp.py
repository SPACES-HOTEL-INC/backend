"""Email OTP generation, hashing and expiry helpers.

The plaintext code is only ever held in memory for the duration of a request.
`otp_code` on the User model stores an HMAC-SHA256 digest keyed with
`settings.SECRET_KEY`, so a database leak does not expose usable codes.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from ..config import settings
from .email import is_email_configured, send_email

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_MAX_VALUE = 10**OTP_LENGTH - 1


def generate_otp() -> str:
    """Return a cryptographically random zero-padded 6-digit code."""
    return f"{secrets.randbelow(OTP_MAX_VALUE + 1):0{OTP_LENGTH}d}"


def otp_expiry() -> datetime:
    """Return the expiry timestamp for a freshly issued code."""
    return datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)


def hash_otp(code: str) -> str:
    """Return the keyed digest persisted in `User.otp_code`."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_otp(code: str, hashed_code: str | None) -> bool:
    """Constant-time comparison of a submitted code against a stored digest."""
    if not hashed_code:
        return False
    return hmac.compare_digest(hash_otp(code), hashed_code)


def is_otp_expired(expires_at: datetime | None) -> bool:
    """Treat a missing expiry as expired so codes are single-use in practice."""
    if expires_at is None:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= expires_at


async def send_otp_email(email: str, code: str) -> None:
    """Deliver the verification code through SendGrid.

    Dispatch failures are logged and swallowed: the OTP is already persisted, so
    a provider outage must not fail the signup or resend request. The user can
    retry with /resend-otp.
    """
    logger.info("Email verification OTP issued for %s (expires in %s min)", email, settings.OTP_EXPIRY_MINUTES)

    if not is_email_configured():
        logger.warning("SendGrid is not configured; skipping OTP email for %s", email)
        return

    try:
        await send_email(email, code)
    except Exception as exc:
        # Deliberately broad: a failed send must never fail the signup or
        # resend request. send_email already normalises provider errors to
        # EmailDeliveryError; this also covers a broken transport shim.
        logger.error("Failed to deliver OTP email to %s: %s", email, exc, exc_info=settings.ENV != "production")
