"""Logging setup.

Called once at import time from main.py. Sends logs to stdout (so the platform
collects them) and, outside tests, to a rotating file on disk.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Relative to the working directory. Created eagerly because a missing
# directory makes RotatingFileHandler raise on first write.
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging():
    """Configure the root logger with console and optional file handlers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # stdout is what Render and other platforms scrape for logs.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Skip the on-disk handler in tests so runs do not clobber app.log.
    if os.getenv("ENV", "development") != "test":
        # Rotate at 10 MB, keeping 5 old files (~50 MB total).
        file_handler = RotatingFileHandler(
            LOGS_DIR / "app.log",
            encoding="utf-8",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Keep request logs, but silence SQLAlchemy unless SQL_ECHO is enabled,
    # otherwise every SELECT is logged.
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
