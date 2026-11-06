"""Small in-process sliding-window rate limiter for sensitive endpoints.

Prism Desk runs as a single backend process on the lab workstation, so
an in-memory limiter is sufficient. Behind Nginx, start Uvicorn with
``--proxy-headers`` so ``request.client.host`` is the real client.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, bucket: str, key: str, limit: int, window: int) -> bool:
        now = time.monotonic()

        with self._lock:
            hits = self._hits[(bucket, key)]

            while hits and hits[0] <= now - window:
                hits.popleft()

            if len(hits) >= limit:
                return False

            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def rate_limit(bucket: str, limit_setting: str):
    """Dependency factory: ``Depends(rate_limit("login", "LOGIN_RATE_LIMIT"))``."""

    def dependency(request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        client = request.client.host if request.client else "unknown"
        allowed = limiter.hit(
            bucket,
            client,
            getattr(settings, limit_setting),
            settings.RATE_LIMIT_WINDOW_SECONDS,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please wait and try again.",
            )

    return dependency
