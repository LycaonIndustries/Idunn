"""Asynchronous background job status and polling router."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from arq.connections import create_pool
from arq.jobs import Job, JobStatus
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..config import settings
from .deps import AuthenticatedUser, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


# Data transfer model for client polling responses.
class JobStatusResponse(BaseModel):
    """Schema representing asynchronous job execution status."""

    job_id: str = Field(..., description="Unique ARQ job identifier")
    status: str = Field(
        ...,
        description="Execution status: queued, in_progress, complete, not_found, or deferred",
    )
    result: Any | None = Field(None, description="Completed task result payload")
    enqueue_time: str | None = Field(None, description="ISO timestamp when task was enqueued")


async def get_redis_pool():
    """Acquire ArqRedis connection pool with zero retry blocking for web requests.

    Returns:
        Connected ArqRedis instance or None if broker is unavailable.
    """
    # Connect with immediate timeout to prevent thread blocking during offline tests.
    try:
        from arq.connections import RedisSettings

        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        redis_settings.conn_retries = 0
        return await create_pool(redis_settings, retry=0)
    except Exception as exc:
        logger.debug("Redis broker unreachable: %s", exc)
        return None


async def enqueue_background_task(function_name: str, *args: Any, **kwargs: Any) -> str | None:
    """Enqueue a job to the Redis ARQ queue if available.

    Args:
        function_name: Registered worker task function name.
        *args: Positional task arguments.
        **kwargs: Keyword task arguments.

    Returns:
        Created job identifier string, or None if Redis broker is unavailable.
    """
    # Attempt to dispatch heavy work to background queue.
    pool = await get_redis_pool()
    if pool is None:
        return None

    try:
        job = await pool.enqueue_job(function_name, *args, **kwargs)
        return job.job_id if job else None
    except Exception as exc:
        logger.warning("Could not enqueue task %s: %s", function_name, exc)
        return None
    finally:
        await pool.close()


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    user: CurrentUser,
) -> JobStatusResponse:
    """Retrieve current execution progress and output for an asynchronous task.

    Args:
        job_id: Unique task identifier.
        user: Authenticated caller identity.

    Returns:
        JobStatusResponse model with status string and result payload.
    """
    # Connect to Redis to check job execution state.
    pool = await get_redis_pool()
    if pool is None:
        return JobStatusResponse(job_id=job_id, status="not_found")

    try:
        job = Job(job_id=job_id, redis=pool)
        status = await job.status()
        if status == JobStatus.not_found:
            return JobStatusResponse(job_id=job_id, status="not_found")

        result = None
        if status == JobStatus.complete or getattr(status, "value", None) == "complete":
            result = await job.result(poll_delay=0)

        info = await job.info()
        enqueue_time = info.enqueue_time.isoformat() if info and info.enqueue_time else None

        return JobStatusResponse(
            job_id=job_id,
            status=status.value,
            result=result,
            enqueue_time=enqueue_time,
        )
    finally:
        await pool.close()
