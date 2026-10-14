"""HTTP middleware: deny-by-default authentication gate and global rate limit
(SEC-01, SEC-04). Order in main.py, outermost first:

  TraceMiddleware -> CORSMiddleware -> RateLimitMiddleware -> AuthGateMiddleware -> routes

- AuthGateMiddleware refuses every request without a valid API key unless the
  (method, path) is in PUBLIC_ROUTES. It runs before routing, so a route that
  forgets its own dependency is still protected. Routes then check the specific
  permission (security.require_permissions).
- RateLimitMiddleware caps requests per client per minute (RATE_LIMIT_PER_MINUTE).
  Narrower limits for failed logins and public appeals/abuse reports live in
  services/ratelimit.py.
"""
from __future__ import annotations

import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import get_settings
from app.security import optional_principal
from app.services import ratelimit

PUBLIC_ROUTES: tuple[tuple[str, re.Pattern], ...] = tuple(
    (m, re.compile(p))
    for m, p in [
        ("GET", r"^/$"),
        ("GET", r"^/health$"),
        ("GET", r"^/policy$"),
        ("GET", r"^/(docs|redoc|openapi\.json)$"),
        ("POST", r"^/appeals$"),                      # recourse for people without accounts
        ("GET", r"^/appeals/[0-9a-f]{32}$"),          # needs X-Appeal-Token (checked in route)
        ("POST", r"^/abuse-reports$"),                # misuse reporting, rate-limited
        ("POST", r"^/support$"),                      # accessible support / human alternative
        ("GET", r"^/transparency-report$"),           # public aggregate disclosure
    ]
)


def is_public(method: str, path: str) -> bool:
    if method == "OPTIONS":  # CORS preflight carries no credentials
        return True
    return any(m == method and p.match(path) for m, p in PUBLIC_ROUTES)


class AuthGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if is_public(request.method, request.url.path):
            return await call_next(request)
        key = ratelimit.client_key(request)
        if ratelimit.exceeded("auth", key, ratelimit.AUTH_FAILURE_LIMIT):  # key-guessing lockout
            return JSONResponse({"detail": "Too many failed authentication attempts; try again later."},
                                status_code=429, headers={"Retry-After": str(ratelimit.WINDOW_SECONDS)})
        if optional_principal(request) is None:
            if request.headers.get("authorization") or request.headers.get("x-api-key"):
                ratelimit.hit("auth", key)
            return JSONResponse({"detail": "Authentication required"}, status_code=401,
                                headers={"WWW-Authenticate": "Bearer"})
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        limit = get_settings().rate_limit_per_minute
        if limit > 0:
            key = ratelimit.client_key(request)
            if not ratelimit.allow("global", key, limit, window=60):
                return JSONResponse({"detail": "Too many requests; slow down."}, status_code=429,
                                    headers={"Retry-After": "60"})
        return await call_next(request)
