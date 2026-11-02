"""User profile endpoints.

`/me` routes serve the caller's own account. `/{user_id}` and `/` are admin
only. The literal `/me` paths are declared before the `/{user_id}` catch-all so
"me" is never parsed as a UUID.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user, require_admin, require_host
from ..crud.user import add_role_to_user, create_user, get_user_by_email, get_user_by_id, list_users, update_user
from ..database import get_async_session
from ..schemas.user import UserCreate, UserRead, UserUpdate
from ..models.user import UserRole

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user=Depends(get_current_user)):
    """The signed-in user's own profile."""
    return current_user


@router.put("/me", response_model=UserRead)
async def update_current_user(
    user_update: UserUpdate,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Edit the signed-in user's own profile.

    The caller's own role is forwarded to the CRUD layer so it can stop a
    non-admin from escalating their own role through this endpoint.
    """
    role_value = current_user.role.value if isinstance(current_user.role, UserRole) else str(current_user.role)
    return await update_user(session, current_user, user_update, current_user_role=role_value)


@router.post("/receptionists", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_receptionist(
    user_in: UserCreate,
    _=Depends(require_host),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a hotel receptionist account for the signed-in host.

    The backend sets the staff account to verified immediately so the hotel can
    issue a password and the receptionist can sign in without a separate OTP step.
    """
    payload = user_in.model_copy(update={"role": "receptionist"})
    existing = await get_user_by_email(session, payload.email)

    if existing:
        if existing.has_role(UserRole.RECEPTIONIST):
            return existing
        await add_role_to_user(session, existing, UserRole.RECEPTIONIST)
        existing.is_verified = True
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        return existing

    user = await create_user(session, payload)
    user.is_verified = True
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserRead)
async def read_user(user_id: uuid.UUID, _=Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    """Fetch any user by id. Admin only."""
    user = await get_user_by_id(session, str(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/", response_model=list[UserRead])
async def read_users(_=Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    """List every user. Admin only."""
    return await list_users(session)
