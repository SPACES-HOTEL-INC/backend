from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.otp import generate_otp, hash_otp, is_otp_expired, otp_expiry, verify_otp
from ..core.security import get_password_hash, verify_password
from ..models.user import User, UserRole
from ..schemas.user import UserCreate, UserUpdate


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user_in: UserCreate) -> User:
    role_value = UserRole.coerce(user_in.role)

    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        is_verified=False,
    )
    user.role = role_value
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def issue_otp(session: AsyncSession, user: User) -> str:
    """Generate, persist and return a fresh plaintext OTP for `user`."""
    code = generate_otp()
    user.otp_code = hash_otp(code)
    user.otp_expires_at = otp_expiry()
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return code


async def verify_user_otp(session: AsyncSession, email: str, code: str) -> User:
    """Validate `code` for `email` and flip the account to verified.

    Raises ValueError with a user-safe message on any failure; the router maps
    these to HTTP responses.
    """
    user = await get_user_by_email(session, email)
    if not user:
        raise ValueError("No account found for that email address.")

    if user.is_verified:
        raise ValueError("This account is already verified. Please sign in.")

    if is_otp_expired(user.otp_expires_at):
        raise ValueError("That verification code has expired. Please request a new one.")

    if not verify_otp(code, user.otp_code):
        raise ValueError("Incorrect verification code.")

    user.is_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(session, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def update_user(session: AsyncSession, user: User, user_in: UserUpdate, current_user_role: str = "consumer") -> User:
    update_data = user_in.model_dump(exclude_unset=True)

    if "role" in update_data:
        if current_user_role != "admin":
            del update_data["role"]

    if "email" in update_data and update_data["email"] != user.email:
        existing = await get_user_by_email(session, update_data["email"])
        if existing and existing.id != user.id:
            raise ValueError("Email already registered")

    if "password" in update_data and update_data["password"] is not None:
        update_data["password"] = get_password_hash(update_data["password"])

    for field, value in update_data.items():
        setattr(user, field, value)

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def list_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User))
    return result.scalars().all()
