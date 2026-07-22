from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .core import exceptions, logging
from .core.exceptions import register_exception_handlers
from .database import Base, engine
from .routers import auth, bookings, payments, properties, reviews, rooms, users

logging.setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    logger = logging.getLogger(__name__)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: None)
        logger.info("Database connection established successfully.")
    except SQLAlchemyError as exc:
        logger.critical("Failed to connect to database on startup: %s", exc)
        raise
    yield
    await engine.dispose()


app = FastAPI(
    title="Spaces Backend API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.ENV == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.CORS_ORIGINS] + [
    "https://spaces-frontend-dev.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(properties.router)
app.include_router(rooms.router)
app.include_router(bookings.router)
app.include_router(payments.router)
app.include_router(reviews.router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}


@app.get("/ready", tags=["health"])
async def readiness_check():
    return {"status": "ready"}


@app.get("/")
async def root():
    return {"message": "Spaces backend is running"}
