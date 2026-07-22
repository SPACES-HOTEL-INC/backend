from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.error("AppException: %s | path=%s", exc.detail, request.url.path)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.error("SQLAlchemyError: %s | path=%s", str(exc), request.url.path)
        if settings.ENV == "development":
            return JSONResponse(status_code=500, content={"detail": str(exc)})
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        if settings.ENV == "development":
            logger.exception("Unhandled exception: %s | path=%s", str(exc), request.url.path)
            return JSONResponse(status_code=500, content={"detail": str(exc)})
        logger.error("Unhandled exception: %s | path=%s", str(exc), request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
