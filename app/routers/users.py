import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user, require_admin
from ..crud.user import get_user_by_id, list_users, update_user
from ..database import get_async_session
from ..schemas.user import UserRead, UserUpdate
from ..models.user import UserRole

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user=Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserRead)
async def update_current_user(
    user_update: UserUpdate,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    role_value = current_user.role.value if isinstance(current_user.role, UserRole) else str(current_user.role)
    return await update_user(session, current_user, user_update, current_user_role=role_value)


@router.get("/{user_id}", response_model=UserRead)
async def read_user(user_id: uuid.UUID, _=Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    user = await get_user_by_id(session, str(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/", response_model=list[UserRead])
async def read_users(_=Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    return await list_users(session)
