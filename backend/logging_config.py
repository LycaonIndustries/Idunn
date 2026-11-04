"""Centralized logging configuration for Iðunn Kitchen OS.

Provides structured logging with timestamps, component namespaces, and
customizable verbosity for local debugging and production diagnostics.
"""

import logging
import sys

from backend.config import settings


def setup_logging(log_level: str | None = None) -> None:
    """Configure system-wide logging with standardized format and level.

    Args:
        log_level: Optional explicit log level (DEBUG, INFO, WARNING, ERROR).
            If omitted, derives from settings.debug or settings.log_level.
    """
    # Determine appropriate severity threshold.
    if log_level is not None:
        level_name = log_level.upper()
    elif settings.debug:
        level_name = "DEBUG"
    else:
        level_name = settings.log_level.upper()

    numeric_level = getattr(logging, level_name, logging.INFO)

    # Standardized format string for readable log entries.
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Replace existing handlers to prevent duplicate output in tests or reload loops.
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        handler.setLevel(numeric_level)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
            handler.setLevel(numeric_level)

    # Mute overly verbose third-party loggers during debugging.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
