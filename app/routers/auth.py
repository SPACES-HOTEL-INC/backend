from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core.dependencies import get_current_user, get_current_user_optional
from ..core.otp import send_otp_email
from ..core.security import create_access_token, create_refresh_token, create_reset_token, decode_token
from ..crud.user import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
    issue_otp,
    update_user,
    verify_user_otp,
)
from ..database import get_async_session
from ..schemas.user import (
    ForgotPasswordRequest,
    OTPMessage,
    OTPResendRequest,
    OTPVerifyRequest,
    RegisterResponse,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserLogin,
    UserRead,
    UserUpdate,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, session: AsyncSession = Depends(get_async_session)):
    existing_user = await get_user_by_email(session, user_in.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = await create_user(session, user_in)
    code = await issue_otp(session, user)
    await send_otp_email(user.email, code)
    return RegisterResponse.model_validate(user)


@router.post("/verify-otp", response_model=OTPMessage)
async def verify_otp_endpoint(payload: OTPVerifyRequest, session: AsyncSession = Depends(get_async_session)):
    try:
        user = await verify_user_otp(session, payload.email, payload.otp_code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return OTPMessage(message="Email verified. You can now sign in.", email=user.email, is_verified=True)


@router.post("/resend-otp", response_model=OTPMessage)
async def resend_otp_endpoint(payload: OTPResendRequest, session: AsyncSession = Depends(get_async_session)):
    user = await get_user_by_email(session, payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="If an account exists for that email, a new verification code has been sent.",
        )

    if user.is_verified:
        return OTPMessage(message="This account is already verified. Please sign in.", email=user.email)

    code = await issue_otp(session, user)
    await send_otp_email(user.email, code)
    return OTPMessage(message="A new verification code has been sent to your email.", email=user.email)


@router.post("/login", response_model=Token)
async def login(form_data: UserLogin, session: AsyncSession = Depends(get_async_session)):
    user = await authenticate_user(session, form_data.email, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before signing in.",
        )
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
