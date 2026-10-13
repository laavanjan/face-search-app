"""Request tracing (TRAN-05).

Every request gets a trace ID at the entry point (TraceMiddleware, the
outermost middleware in main.py). It is:
- taken from a valid incoming X-Request-ID header or generated (uuid4 hex),
- returned to the caller in the X-Request-ID response header,
- added to every log line (TraceLogFilter -> %(trace_id)s),
- stored on every audit_log row (services/audit.py reads current_trace_id()),
so any decision can be followed from the HTTP request to its audit record.
"""
from __future__ import annotations

import logging
import re
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

HEADER = "X-Request-ID"
_VALID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_trace: ContextVar[str | None] = ContextVar("trace_id", default=None)


def current_trace_id() -> str | None:
    return _trace.get()


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(HEADER, "")
        trace_id = incoming if _VALID.fullmatch(incoming) else uuid.uuid4().hex
        token = _trace.set(trace_id)
        try:
            response = await call_next(request)
        finally:
            _trace.reset(token)
        response.headers[HEADER] = trace_id
        return response


class TraceLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = _trace.get() or "-"
        return True
