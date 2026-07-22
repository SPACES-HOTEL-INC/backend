from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import decode_token
from ..crud.user import get_user_by_id
from ..database import get_async_session
from ..models.user import User, UserRole

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or invalid user")
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(HTTPBearer(auto_error=False)),
    session: AsyncSession = Depends(get_async_session),
) -> User | None:
    if not credentials:
        return None
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        return None
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_host(user: User = Depends(get_current_user)) -> User:
    if not user.is_host:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Host access required")
    return user
