"""Exponential backoff retry policies and resilience decorators for storage and network calls."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
from pymongo.errors import AutoReconnect, NetworkTimeout, ServerSelectionTimeoutError
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)

# Transient database connectivity exceptions that warrant automatic backoff retries.
TRANSIENT_DB_ERRORS = (
    AutoReconnect,
    NetworkTimeout,
    ServerSelectionTimeoutError,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
    httpx.ConnectError,
)

# Transient external AI provider and HTTP gateway errors.
TRANSIENT_PROVIDER_ERRORS = (
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.PoolTimeout,
)


def _log_retry_attempt(retry_state: RetryCallState) -> None:
    """Log retry warning when a transient network or database error triggers backoff.

    Args:
        retry_state: State of current retry invocation.
    """
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    attempt = retry_state.attempt_number
    # Log warning to track intermittent infrastructure glitches in observability dashboards.
    logger.warning(
        "Transient failure during %s (attempt %d/3): %s. Backing off with jitter...",
        retry_state.fn.__name__ if retry_state.fn else "operation",
        attempt,
        str(exc) if exc else "Unknown error",
    )


def with_db_retry(
    max_attempts: int = 3,
    initial_delay: float = 0.2,
    max_delay: float = 2.5,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Apply exponential backoff with jitter on transient database socket or DNS failures.

    Args:
        max_attempts: Maximum retry count before reraising exception.
        initial_delay: Minimum backoff time in seconds.
        max_delay: Maximum capped backoff time in seconds.

    Returns:
        Tenacity retry decorator wrapping async or sync database methods.
    """
    # Wrap database execution with jittered exponential backoff to recover from cold starts.
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(multiplier=initial_delay, max=max_delay, exp_base=2),
        retry=retry_if_exception_type(TRANSIENT_DB_ERRORS),
        before_sleep=_log_retry_attempt,
        reraise=True,
    )


def with_provider_retry(
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 3.0,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Apply exponential backoff with jitter on external AI provider timeouts and gateway errors.

    Args:
        max_attempts: Maximum retry count before reraising exception.
        initial_delay: Minimum backoff time in seconds.
        max_delay: Maximum capped backoff time in seconds.

    Returns:
        Tenacity retry decorator wrapping async HTTP calls.
    """
    # Protect AI calls against transient 502/504 gateway drops and timeouts.
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(multiplier=initial_delay, max=max_delay, exp_base=2),
        retry=retry_if_exception_type(TRANSIENT_PROVIDER_ERRORS),
        before_sleep=_log_retry_attempt,
        reraise=True,
    )
