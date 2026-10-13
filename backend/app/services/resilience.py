"""Deadlines and bounded retries for critical paths.

- `retry` wraps remote calls (Qdrant). Only transient failures are retried:
  transport errors/timeouts, HTTP 429 and 5xx. Validation errors, auth errors
  and `no_face_detected` are never retried.
- `run_with_deadline` bounds model inference so a stuck model load or CPU
  inference surfaces as a 504 to the caller instead of hanging the request.
AWS calls use botocore's own retry/timeout config (see aws_config()).
"""
from __future__ import annotations

import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Callable, TypeVar

from app.config import get_settings

log = logging.getLogger(__name__)
T = TypeVar("T")

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="inference")


class DeadlineExceeded(TimeoutError):
    pass


def is_transient(exc: BaseException) -> bool:
    try:
        import httpx

        if isinstance(exc, (httpx.TransportError, httpx.TimeoutException)):
            return True
    except ImportError:  # pragma: no cover
        pass
    try:
        from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

        if isinstance(exc, ResponseHandlingException):
            return True
        if isinstance(exc, UnexpectedResponse):
            code = getattr(exc, "status_code", 0) or 0
            return code == 429 or code >= 500
    except ImportError:  # pragma: no cover
        pass
    return isinstance(exc, (ConnectionError, TimeoutError))


def retry(fn: Callable[[], T], *, op: str, attempts: int | None = None) -> T:
    attempts = attempts or get_settings().remote_retry_attempts
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            if attempt >= attempts or not is_transient(e):
                if attempt > 1:
                    log.error("op=%s failed after %d attempt(s): %s", op, attempt, type(e).__name__)
                raise
            delay = min(2.0, 0.2 * 2 ** (attempt - 1)) * (0.5 + random.random())
            log.warning("op=%s transient %s, retry %d/%d", op, type(e).__name__, attempt, attempts)
            time.sleep(delay)
    raise RuntimeError("unreachable")


def run_with_deadline(fn: Callable[..., T], *args, timeout: float, op: str) -> T:
    fut = _pool.submit(fn, *args)
    try:
        return fut.result(timeout=timeout)
    except FutureTimeout as e:
        log.error("op=%s exceeded deadline of %.0fs", op, timeout)
        raise DeadlineExceeded(op) from e


def aws_config():
    from botocore.config import Config

    s = get_settings()
    return Config(
        connect_timeout=s.aws_connect_timeout_seconds,
        read_timeout=s.aws_read_timeout_seconds,
        retries={"max_attempts": s.aws_max_attempts, "mode": "standard"},
    )
