"""Global exception handlers.

Turns raised exceptions into JSON responses with a sensible status code so the
API never returns an HTML error page or a stack trace. Outside development the
client only ever sees a generic message; the full error goes to the log.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base for expected, client-visible failures.

    Carries the status code and message to send back, so raising this is
    preferable to letting a generic 500 escape.

        raise AppException(404, "Booking not found")
    """

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the handlers below to `app`. Called once from main.py."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        # Deliberate: the message is safe to show, it was written for clients.
        logger.error("AppException: %s | path=%s", exc.detail, request.url.path)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        # Always log the real cause, even in development where it is also
        # returned: database errors are the hardest to diagnose from a response.
        logger.error("SQLAlchemyError: %s | path=%s", str(exc), request.url.path)
        if settings.ENV == "development":
            return JSONResponse(status_code=500, content={"detail": str(exc)})
        # In production the detail can expose schema or connection strings.
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        # Last-resort catch-all for anything not handled above.
        if settings.ENV == "development":
            logger.exception("Unhandled exception: %s | path=%s", str(exc), request.url.path)
            return JSONResponse(status_code=500, content={"detail": str(exc)})
        # Production: log without a traceback, and never echo the message back.
        logger.error("Unhandled exception: %s | path=%s", str(exc), request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
