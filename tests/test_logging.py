"""Tests for logging configuration and structured logging setup."""

import logging

from backend.logging_config import setup_logging


def test_setup_logging_configures_root_logger():
    """Verify setup_logging configures root logger handlers and log levels."""
    setup_logging(log_level="DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) > 0


def test_service_logger_emission(caplog):
    """Verify loggers in backend namespace emit log records."""
    setup_logging(log_level="INFO")
    logger = logging.getLogger("backend.services.cook_ai")
    with caplog.at_level(logging.INFO):
        logger.info("Evaluating pantry stock for user meal")
    assert "Evaluating pantry stock for user meal" in caplog.text
