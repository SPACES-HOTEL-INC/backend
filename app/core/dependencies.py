"""Authentication and authorisation dependencies.

Route handlers depend on the functions here to turn a bearer token into a User,
and to gate on role. `get_current_user` rejects bad tokens; the optional variant
treats a missing or bad token as an anonymous visitor; `require_host` and
`require_admin` layer a role check on top.

The database is hit on every authenticated request, so deactivating a user takes
effect immediately rather than waiting for their token to expire.
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import decode_token
from ..crud.user import get_user_by_id
from ..database import get_async_session
from ..models.user import User, UserRole

# Documents the bearer scheme in /docs and makes FastAPI reject a request with
# no Authorization header before our code runs.
security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Resolve the bearer token to an active User, or raise 401.

    Every failure path returns 401 rather than 403 so an attacker cannot tell
    "token is invalid" apart from "user does not exist".
    """
    token = credentials.credentials

    # Catch token parsing/decoding errors gracefully
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # `sub` is the user id we stored when the token was minted.
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Re-read the user on each request so role changes and deactivation apply
    # without waiting for token expiry.
    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or invalid user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(HTTPBearer(auto_error=False)),
    session: AsyncSession = Depends(get_async_session),
) -> User | None:
    """Like `get_current_user` but returns None instead of raising.

    Used by routes that serve both anonymous and signed-in visitors. Note this
    deliberately swallows errors: a broken token is treated as no token.
    """
    if not credentials:
        return None
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except Exception:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        return None
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency guard: authenticated *and* an admin, else 403."""
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_host(user: User = Depends(get_current_user)) -> User:
    """Dependency guard: authenticated *and* a host, else 403.

    Admins also satisfy this, since `is_host` is true for them. An account
    holding both consumer and host roles passes it too.
    """
    if not user.is_host:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Host access required")
    return user