import secrets
from typing import List

from pydantic import AnyHttpUrl, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int | None = None
    REFRESH_TOKEN_EXPIRE_MINUTES: int | None = None

    @property
    def refresh_token_expire_minutes(self) -> int:
        if self.REFRESH_TOKEN_EXPIRE_MINUTES is not None:
            return self.REFRESH_TOKEN_EXPIRE_MINUTES
        if self.REFRESH_TOKEN_EXPIRE_DAYS is not None:
            return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60
        return 10080

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str | None = None

    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    ENV: str = "development"

    RATE_LIMIT_MAX_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    REQUEST_TIMEOUT_SECONDS: int = 30
    MAX_UPLOAD_SIZE_MB: int = 10

    LOG_LEVEL: str = "INFO"
    SQL_ECHO: bool = False

    PAYMENT_WEBHOOK_SECRET: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_secret_key()
        self._validate_database_url()

    def _validate_secret_key(self) -> None:
        if len(self.SECRET_KEY) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        if self.SECRET_KEY in {"change-me", "secret", "wealthy_secret_key", "your-secret-key"}:
            raise ValueError(
                "SECRET_KEY is using a default or weak value. "
                "Set a strong, unique secret in your .env file."
            )

    def _validate_database_url(self) -> None:
        url = self.database_url
        if not url.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the postgresql+asyncpg:// dialect for async support. "
                f"Got: {url[:50]}..."
            )

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
