"""In-memory sliding-window rate limits for abuse cases found in the red-team
exercise (governance/red-team-report.yaml):

- failed authentication (API-key guessing): AUTH_FAILURE_LIMIT per client per window
- public appeal submissions (flooding / mass photo restriction): APPEAL_SUBMIT_LIMIT per client per window

Single-process only; behind several workers, put the same limits on the
reverse proxy as well.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

WINDOW_SECONDS = 600
AUTH_FAILURE_LIMIT = 20
APPEAL_SUBMIT_LIMIT = 5

_lock = threading.Lock()
_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _count(bucket: str, key: str, now: float) -> deque:
    q = _hits[(bucket, key)]
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    return q


def check(bucket: str, key: str, limit: int) -> None:
    with _lock:
        if len(_count(bucket, key, time.time())) >= limit:
            raise HTTPException(429, "Too many requests; try again later.", headers={"Retry-After": str(WINDOW_SECONDS)})


def hit(bucket: str, key: str) -> None:
    with _lock:
        now = time.time()
        _count(bucket, key, now).append(now)


def limit_appeal_submissions(request: Request) -> None:
    key = client_key(request)
    check("appeal", key, APPEAL_SUBMIT_LIMIT)
    hit("appeal", key)


def reset_for_tests() -> None:
    with _lock:
        _hits.clear()
