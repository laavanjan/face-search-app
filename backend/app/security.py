"""Authentication + role-based access control.

Deny by default: a request without a valid key gets 401, a principal without
the needed permission gets 403. Roles map to narrow permission sets so no role
implicitly gets everything (docs/oversight/human-oversight.md, "Roles").
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from functools import lru_cache

from fastapi import Depends, HTTPException, Request

from app.config import get_settings

log = logging.getLogger(__name__)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    # Can browse the indexed library.
    "viewer": frozenset({"photos:read"}),
    # Uploads photos and runs searches. Results stay hidden until reviewed.
    "operator": frozenset({"photos:read", "photos:write", "photos:search"}),
    # Human Reviewer: approves indexing, decides search candidates, handles appeals.
    "reviewer": frozenset({"photos:read", "review:decide", "appeals:manage"}),
    # Service Owner: pause/resume, approve config changes, deletion, audit.
    "admin": frozenset(
        {"photos:read", "photos:delete", "system:control", "audit:read", "appeals:manage"}
    ),
}


@dataclass(frozen=True)
class Principal:
    name: str
    roles: tuple[str, ...]
    permissions: frozenset[str]

    def can(self, perm: str) -> bool:
        return perm in self.permissions


@dataclass(frozen=True)
class _KeyEntry:
    principal: Principal
    token: str  # raw token, or "sha256:<hex>"

    def matches(self, presented: str) -> bool:
        if self.token.startswith("sha256:"):
            digest = hashlib.sha256(presented.encode()).hexdigest()
            return hmac.compare_digest(digest, self.token[7:].lower())
        return hmac.compare_digest(presented, self.token)


@lru_cache
def _key_entries(raw: str) -> tuple[_KeyEntry, ...]:
    entries = []
    for item in (p.strip() for p in raw.split(",")):
        if not item:
            continue
        parts = item.split(":", 2)
        if len(parts) != 3 or not all(parts):
            log.error("Ignoring malformed API_KEYS entry (expected name:role:token).")
            continue
        name, roles_s, token = parts
        roles = tuple(r for r in roles_s.split("+") if r)
        unknown = [r for r in roles if r not in ROLE_PERMISSIONS]
        if unknown:
            log.error("Ignoring API_KEYS entry with unknown role(s) %s.", unknown)
            continue
        perms = frozenset().union(*(ROLE_PERMISSIONS[r] for r in roles))
        entries.append(_KeyEntry(Principal(name, roles, perms), token))
    return tuple(entries)


def configured_principals() -> tuple[Principal, ...]:
    return tuple(e.principal for e in _key_entries(get_settings().api_keys))


def _presented_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return request.headers.get("x-api-key") or None


def optional_principal(request: Request) -> Principal | None:
    token = _presented_token(request)
    if not token:
        return None
    for e in _key_entries(get_settings().api_keys):
        if e.matches(token):
            return e.principal
    return None


def current_principal(request: Request) -> Principal:
    p = optional_principal(request)
    if p is None:
        raise HTTPException(
            401, "Authentication required", headers={"WWW-Authenticate": "Bearer"}
        )
    return p


def require_permissions(*perms: str):
    def dep(p: Principal = Depends(current_principal)) -> Principal:
        missing = [x for x in perms if not p.can(x)]
        if missing:
            raise HTTPException(403, f"Missing permission: {', '.join(missing)}")
        return p

    return dep
