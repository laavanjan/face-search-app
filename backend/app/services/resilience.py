"""Reliability controls for critical paths (SAFE-04, HUMO-04).

| Control    | Where | Setting |
|------------|-------|---------|
| Timeout    | model inference via run_with_deadline -> 504; Qdrant client timeout; AWS connect/read timeouts (aws_config) | INFERENCE_TIMEOUT_SECONDS=60, QDRANT_TIMEOUT_SECONDS=20, AWS_*_TIMEOUT_SECONDS |
| Retry      | `retry`: bounded exponential backoff + jitter on transient Qdrant errors only (transport, timeout, 429, 5xx); botocore "standard" mode for AWS | REMOTE_RETRY_ATTEMPTS=3, AWS_MAX_ATTEMPTS=3 |
| Fallback   | Rekognition failure -> InsightFace-only scoring (rekognition.detect_faces returns None). Qdrant/storage failure after retries -> 503, nothing stored or disclosed (routes/common.pipeline_error) | - |
| Abstention | No decision when confidence is low: faces below MIN_DET_SCORE or MIN_FACE_SIZE are ignored; no face -> 422; candidates below SEARCH_MIN_THRESHOLD never proposed; every proposed match still needs a human | MIN_DET_SCORE=0.5, MIN_FACE_SIZE=40, SEARCH_MIN_THRESHOLD=0.35 |

Validation errors, auth errors and `no_face_detected` are never retried.
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
    from app.services import carbon

    carbon.ensure_budget()  # daily compute budget (SOC-03)

    def metered(*a):
        start = time.perf_counter()
        try:
            return fn(*a)
        finally:
            carbon.charge(time.perf_counter() - start)

    fut = _pool.submit(metered, *args)
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
