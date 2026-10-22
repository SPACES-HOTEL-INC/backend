"""Application configuration.

Every environment-specific value is declared once on `Settings` and read
through the single `settings` instance at the bottom of this file. Values come
from real environment variables first, then `.env`, then the defaults below.
"""

import secrets
from typing import List

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Security / JWT ---------------------------------------------------
    # SECRET_KEY signs access tokens and keys the OTP digests. No default: the
    # service refuses to start without a strong one.
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int | None = None
    REFRESH_TOKEN_EXPIRE_MINUTES: int | None = None

    # How long an emailed OTP stays valid.
    OTP_EXPIRY_MINUTES: int = 10

    @property
    def refresh_token_expire_minutes(self) -> int:
        """Refresh-token lifetime in minutes.

        Minutes win over days when both are set; 10080 (7 days) is the final
        fallback.
        """
        if self.REFRESH_TOKEN_EXPIRE_MINUTES is not None:
            return self.REFRESH_TOKEN_EXPIRE_MINUTES
        if self.REFRESH_TOKEN_EXPIRE_DAYS is not None:
            return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60
        return 10080

    # --- Database ---------------------------------------------------------
    # Used to build DATABASE_URL when one is not supplied directly.
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "spaces"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str | None = None

    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # SendGrid Transactional Email
    # Optional so the service still boots without a mail provider; OTP
    # delivery is skipped (and logged) when these are missing.
    SENDGRID_API_KEY: str | None = None
    EMAILS_FROM: str = "no-reply@spaces.app"
    EMAILS_FROM_NAME: str = "Spaces"

    # Browser origins allowed to call this API.
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "[::1]"]

    # "development" enables /docs and /redoc. Use "production" in deployment.
    ENV: str = "development"

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_MAX_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    REQUEST_TIMEOUT_SECONDS: int = 30
    MAX_UPLOAD_SIZE_MB: int = 10

    LOG_LEVEL: str = "INFO"
    # Logs every SQL statement. Verbose and unsafe for production.
    SQL_ECHO: bool = False

    # Shared secret for authenticating payment provider webhooks.
    PAYMENT_WEBHOOK_SECRET: str | None = None

    # Flutterwave keys used when creating and verifying payment transactions.
    FLW_PUBLIC_KEY: str = ""
    FLW_SECRET_KEY: str = ""
    FLW_ENCRYPTION_KEY: str = ""
    FLW_BASE_URL: str = "https://api.flutterwave.com/v3"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Environment variable names must match field names exactly.
        case_sensitive=True,
        # Unknown keys in .env are ignored rather than crashing the process.
        extra="ignore",
    )

    def _validate_secret_key(self) -> None:
        """Reject short or well-known secrets so tokens cannot be forged."""
        if len(self.SECRET_KEY) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        if self.SECRET_KEY in {"change-me", "secret", "wealthy_secret_key", "your-secret-key"}:
            raise ValueError(
                "SECRET_KEY is using a default or weak value. "
                "Set a strong, unique secret in your .env file."
            )

    def _validate_database_url(self) -> None:
        """Guarantee the asyncpg driver, which the async engine requires."""
        url = self.database_url
        if not url.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the postgresql+asyncpg:// dialect for async support. "
                f"Got: {url[:50]}..."
            )

    def _validate_allowed_hosts(self) -> None:
        """Reject wildcard host headers; a list of explicit domains is required."""
        if "*" in self.ALLOWED_HOSTS:
            raise ValueError("ALLOWED_HOSTS must not contain '*' in a deployed environment.")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_secret_key()
        self._validate_database_url()
        self._validate_allowed_hosts()

    @property
    def database_url(self) -> str:
        """The connection string, normalised to the asyncpg dialect."""
        if self.DATABASE_URL:
            # Fix standard Render/Heroku postgres:// scheme if present
            if self.DATABASE_URL.startswith("postgres://"):
                return self.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
            return self.DATABASE_URL

        # Fall back to assembling one from the individual POSTGRES_* parts.
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


# Single shared instance. Import this, never construct another.
settings = Settings()