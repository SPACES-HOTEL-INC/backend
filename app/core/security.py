"""Password hashing and JWT issuing/verification.

Every token is a signed JWT. The `token_type` claim ("access", "refresh" or
"reset") is what stops a token minted for one purpose being replayed against
another, so always create the right kind and check the claim on the way back in.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import settings

# bcrypt only. deprecated="auto" lets us rotate to a stronger scheme later
# without invalidating existing hashes.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash a plaintext password for storage. Never store the plaintext."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time check of a submitted password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, expires_delta: timedelta | None, token_type: str) -> str:
    """Shared JWT builder.

    `subject` is the user's id as a string, per the JWT spec.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    to_encode: dict[str, Any] = {
        "sub": subject,
        "exp": now + expires_delta,
        "iat": now,
        # Distinguishes this token from the other kinds this service issues.
        "token_type": token_type,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Short-lived token sent to the browser and attached to API requests."""
    return _create_token(subject, expires_delta, "access")


def create_refresh_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Long-lived token exchanged for a new access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.refresh_token_expire_minutes)
    return _create_token(subject, expires_delta, "refresh")


def create_reset_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Single-purpose password-reset token, valid 30 minutes by default."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=30)
    return _create_token(subject, expires_delta, "reset")


def decode_token(token: str) -> dict[str, Any]:
    """Verify signature and expiry, returning the claims.

    Raises ValueError for anything invalid or expired so callers can map a bad
    token onto a single 401 response. Note this does not check `token_type`;
    callers that care must assert on the claim themselves.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise ValueError("Could not validate credentials") from exc
