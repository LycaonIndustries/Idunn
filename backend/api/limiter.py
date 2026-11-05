"""Rate limiting configuration and SlowAPI integration for Iðunn."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Default IP-based rate limiter to prevent computational and external LLM quota exhaustion.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
    storage_uri="memory://",
)
