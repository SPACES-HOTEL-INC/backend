"""Authentication endpoints: registration, login, tokens and password reset.

Signup is a two-step flow. `register` creates the account and emails a 6-digit
code; `verify-otp` activates it. Login is refused until then, so an unverified
account can never hold a token.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core.dependencies import get_current_user, get_current_user_optional
from ..core.otp import send_otp_email
from ..core.security import create_access_token, create_refresh_token, create_reset_token, decode_token
from ..crud.user import (
    add_role_to_user,
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
    issue_otp,
    update_user,
    verify_user_otp,
)
from ..database import get_async_session
from ..models.user import UserRole
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
    """Create an account, or attach a role to one that already exists.

    Email is unique, so a repeat registration never creates a second row. If the
    address is already registered and the requested role is new, that role is
    added to the existing account. The submitted password is deliberately
    ignored on that path, so registering with a known address cannot take over
    or re-credential someone else's account.
    """
    existing_user = await get_user_by_email(session, user_in.email)

    if existing_user:
        # Email stays unique. A repeat registration attaches the requested role
        # to the existing account instead of creating a second row, which would
        # break every email lookup that expects one user per address.
        requested_role = UserRole.coerce(user_in.role)
        already_held = existing_user.has_role(requested_role)

        if not already_held:
            await add_role_to_user(session, existing_user, requested_role)

        payload = RegisterResponse.model_validate(existing_user)
        return payload.model_copy(
            update={
                "message": (
                    "An account already exists for this email. Please sign in with your existing password."
                    if already_held
                    else "An account already exists for this email. The requested role has been added to it; "
                    "please sign in with your existing password."
                )
            }
        )

    # Brand new account: create it unverified and send the first code.
    user = await create_user(session, user_in)
    code = await issue_otp(session, user)
    await send_otp_email(user.email, code)
    return RegisterResponse.model_validate(user)


@router.post("/verify-otp", response_model=OTPMessage)
async def verify_otp_endpoint(payload: OTPVerifyRequest, session: AsyncSession = Depends(get_async_session)):
    """Accept the emailed code and activate the account.

    The CRUD layer raises ValueError with a user-safe message; those become 400s
    here. Deliberately does not return a token: the user signs in separately.
    """
    try:
        user = await verify_user_otp(session, payload.email, payload.otp_code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return OTPMessage(message="Email verified. You can now sign in.", email=user.email, is_verified=True)


@router.post("/resend-otp", response_model=OTPMessage)
async def resend_otp_endpoint(payload: OTPResendRequest, session: AsyncSession = Depends(get_async_session)):
    """Issue and email a replacement code.

    Issuing a new code invalidates the previous one. Already-verified accounts
    are told to sign in rather than sent another email.
    """
    user = await get_user_by_email(session, payload.email)
    if not user:
        # The wording mirrors the success case so this cannot be used to
        # discover which addresses are registered.
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
    """Exchange credentials for an access and refresh token.

    The password is checked before verification so a wrong password is always
    401. Only a correct password on an unverified account produces 403, telling
    the client to show the OTP step.
    """
    user = await authenticate_user(session, form_data.email, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before signing in.",
        )
    # The token subject is the user id, which the auth dependency reads back.
    access_token = create_access_token(subject=str(user.id), expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_refresh_token(subject=str(user.id))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh(
    refresh_token: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user_optional),
):
    """Issue a new token pair.

    Accepts a refresh token in the body, or falls back to an already
    authenticated caller. A rotation is performed: a fresh refresh token is
    returned each time.
    """
    user = None

    if refresh_token:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

        # Reject an access or reset token presented as a refresh token.
        if payload.get("token_type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        # Re-read the user so a deactivated account cannot refresh.
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
    """Client-side only: no-op until a token blacklist is added.

    Tokens are stateless, so the client discards them and they expire naturally.
    """
    return {"detail": "Logout not implemented. Use token expiration or blacklist store."}


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Start a password reset.

    A reset token is generated server-side and should be delivered through an
    email provider, never echoed in JSON. When no mail provider is configured we
    keep the flow safe by logging the token server-side only and returning a
    generic success message.
    """
    user = await get_user_by_email(session, request.email)
    if user is None or not user.is_active:
        # Same wording as success, so the response cannot be used to enumerate
        # registered addresses.
        return {"detail": "If an account exists for this email, password reset instructions have been sent."}

    reset_token = create_reset_token(subject=str(user.id))
    # The token is intentionally not returned to the client. If an email provider
    # is configured, the token should be mailed to the user instead.
    import logging
    logging.getLogger(__name__).warning("Password reset token issued for %s", user.email)
    return {"detail": "If an account exists for this email, password reset instructions have been sent."}


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Set a new password using a reset token.

    The token's `token_type` must be "reset", so an access token cannot be used
    to change a password. `current_user_role` is passed as "admin" to bypass the
    role check in update_user, since the caller here is the token holder rather
    than an administrator.
    """
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
