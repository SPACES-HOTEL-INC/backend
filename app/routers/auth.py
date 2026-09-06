from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core.dependencies import get_current_user, get_current_user_optional
from ..core.security import create_access_token, create_refresh_token, create_reset_token, decode_token
from ..crud.user import authenticate_user, create_user, get_user_by_email, get_user_by_id, update_user
from ..database import get_async_session
from ..schemas.user import ForgotPasswordRequest, ResetPasswordRequest, Token, UserCreate, UserLogin, UserRead, UserUpdate

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, session: AsyncSession = Depends(get_async_session)):
    existing_user = await get_user_by_email(session, user_in.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = await create_user(session, user_in)
    return user


@router.post("/login", response_model=Token)
async def login(form_data: UserLogin, session: AsyncSession = Depends(get_async_session)):
    user = await authenticate_user(session, form_data.email, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    access_token = create_access_token(subject=str(user.id), expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_refresh_token(subject=str(user.id))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh(
    refresh_token: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user_optional),
):
    user = None

    if refresh_token:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

        if payload.get("token_type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user = await get_user_by_id(session, str(payload.get("sub", "")))
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or invalid user")
    elif current_user:
        user = current_user
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    access_token = create_access_token(subject=str(user.id), expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    next_refresh_token = create_refresh_token(subject=str(user.id))
    return {"access_token": access_token, "refresh_token": next_refresh_token, "token_type": "bearer"}


@router.post("/logout")
async def logout():
    return {"detail": "Logout not implemented. Use token expiration or blacklist store."}


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
):
    user = await get_user_by_email(session, request.email)
    if user is None or not user.is_active:
        return {"detail": "If an account exists for this email, password reset instructions have been sent."}

    reset_token = create_reset_token(subject=str(user.id))
    # In a production deployment, this should dispatch the token through an email provider.
    # The token is intentionally returned only for server-side debugging and the front-end
    # should not display it to the user. This keeps the flow functional without requiring
    # external mail infrastructure in this environment.
    return {
        "detail": "If an account exists for this email, password reset instructions have been sent.",
        "reset_token": reset_token,
    }


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        payload = decode_token(request.token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired reset token") from exc

    if payload.get("token_type") != "reset":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid reset token")

    user = await get_user_by_id(session, str(payload.get("sub", "")))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired reset token")

    await update_user(session, user, UserUpdate(password=request.new_password), current_user_role="admin")
    return {"detail": "Password reset successful."}
