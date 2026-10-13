"""Logging with personal-data redaction.

Every handler on the root and uvicorn loggers gets `RedactingFilter`, so
request paths, exception text and messages cannot leak photo/face ids,
filenames, emails, IPs, URLs (which may embed credentials) or bearer tokens.
Log event names + counts instead of identifiers.
"""
from __future__ import annotations

import logging
import re

from app.tracing import TraceLogFilter

_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\b(bearer|x-api-key[:=]?)\s+\S+"), r"\1 <token>"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<email>"),
    (re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://\S+"), "<url>"),
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"), "<id>"),
    (re.compile(r"\b[0-9a-fA-F]{32}\b"), "<id>"),
    (re.compile(r"(?i)[\w.()-]*\w\.(jpe?g|png|webp|heic|gif|bmp|tiff?)\b"), "<file>"),
    (re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,3}\b"), r"\1.x"),
]


def redact(text: str) -> str:
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text


def _redact_arg(a):
    return redact(a) if isinstance(a, str) else a


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # With args, msg is a %-format string: redacting it could corrupt the
        # placeholders (e.g. "%s://%s:%d" looks like a URL), so only the
        # interpolated values are redacted.
        if isinstance(record.msg, str) and not record.args:
            record.msg = redact(record.msg)
        if isinstance(record.args, tuple):
            # Keep tuple shape: uvicorn's AccessFormatter unpacks it.
            record.args = tuple(_redact_arg(a) for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {k: _redact_arg(v) for k, v in record.args.items()}
        if record.exc_info and not record.exc_text:
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
        return True


_FILTER = RedactingFilter()
_TRACE = TraceLogFilter()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s trace=%(trace_id)s :: %(message)s",
    )
    for name in ("", "uvicorn", "uvicorn.error", "uvicorn.access"):
        for h in logging.getLogger(name).handlers:
            for f in (_TRACE, _FILTER):
                if f not in h.filters:
                    h.addFilter(f)
