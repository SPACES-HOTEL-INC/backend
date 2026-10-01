"""Application entry point.

Wires up logging, the database engine, middleware, exception handlers and every
API router. Anything a new developer should know about running this service
lives in the module docstring of the file that owns it.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .core import exceptions, logging
from .core.exceptions import register_exception_handlers
from .database import Base, engine
from .routers import auth, bookings, payments, properties, public_properties, reviews, rooms, settings as settings_router, support, users

logging.setup_logging()

# Ensure local upload directories exist. StaticFiles mounts this directory at
# startup and raises if it is missing, so create it before the app builds.
os.makedirs("static/uploads/properties", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start-up / shut-down hook.

    Fails fast when the database is unreachable so a broken instance never
    starts accepting traffic, and returns pooled connections on shutdown.
    """
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
    # Interactive docs are disabled in production so the schema is not public.
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None,
)

# Serves user-uploaded images. Only this prefix reaches the uploads folder;
# /.well-known/ is handled by a route further down and never touches disk.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Only compress responses above 1 kB; below that the overhead is not worth it.
app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.ENV == "production":
    # NOTE: allowed_hosts=["*"] currently accepts any Host header. It is a
    # placeholder waiting on the real deployed hostnames. Tighten this before
    # relying on Host-header protections.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

app.add_middleware(
    CORSMiddleware,
    # Configured origins first, then known dev/preview deployments. The regex
    # below also allows any Vercel preview URL for the frontend.
    allow_origins=[str(origin) for origin in settings.CORS_ORIGINS] + [
        "https://space-frontend-dev.vercel.app",
        "https://space-frontend-dev-git-main-samflixdps-projects.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "https://client-based.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Converts unhandled errors into JSON responses instead of leaking stack traces.
register_exception_handlers(app)

# Router order is cosmetic; each router owns a distinct URL prefix.
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(settings_router.router)
app.include_router(properties.router)
app.include_router(public_properties.router)
app.include_router(rooms.router)
app.include_router(bookings.router)
app.include_router(payments.router)
app.include_router(reviews.router)
app.include_router(support.router)


@app.get("/health", tags=["health"])
async def health_check():
    """Liveness probe. Answers as long as the process is running."""
    return {"status": "healthy"}


@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness probe for the load balancer."""
    return {"status": "ready"}


@app.get("/.well-known/replay-qa-security-nonce", tags=["security"])
async def replay_qa_nonce():
    """Static site-ownership proof consumed by the Replay QA scanner.

    Must answer 200 with this exact body as plain text, unauthenticated and
    without a redirect, so the nonce is returned verbatim rather than wrapped in
    JSON. The path is fixed; changing it invalidates the check.
    """
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("loopqa-sec-0CKnaqYI3WcTV2SKh1HaCnYyOaQPfQWHoRVIr66XOo0")


@app.get("/")
async def root():
    return {"message": "Spaces backend is running"}