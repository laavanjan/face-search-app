"""Pseudonymisation and field encryption (governance/de-identification.yaml).

- `pseudonym(name)`: keyed HMAC-SHA256 of an account name. Audit rows, review
  records and vector payloads store this instead of the name, so the stores
  hold no direct identifiers; only someone holding DATA_ENCRYPTION_KEY can link
  a pseudonym back to a known account.
- `encrypt` / `decrypt`: Fernet (AES-128-CBC + HMAC) for appeal contact details,
  which are only decrypted for staff with appeals:manage.
Both use sub-keys derived from DATA_ENCRYPTION_KEY with distinct labels.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

log = logging.getLogger(__name__)

# No key is hard-coded. Without DATA_ENCRYPTION_KEY, development runs use a
# random per-process key (pseudonyms and encrypted contacts do not survive a
# restart); production refuses to start.
_EPHEMERAL_KEY = secrets.token_urlsafe(32)


def check_key() -> None:
    s = get_settings()
    if s.data_encryption_key:
        return
    if s.environment == "production":
        raise RuntimeError("DATA_ENCRYPTION_KEY must be set when ENVIRONMENT=production")
    log.warning("DATA_ENCRYPTION_KEY is empty: using a random per-process development key.")


def _subkey(label: str) -> bytes:
    master = (get_settings().data_encryption_key or _EPHEMERAL_KEY).encode()
    return hmac.new(master, label.encode(), hashlib.sha256).digest()


def mac(label: str, data: bytes) -> str:
    """HMAC-SHA256 under a purpose-specific sub-key (e.g. provenance signatures)."""
    return hmac.new(_subkey(label), data, hashlib.sha256).hexdigest()


def pseudonym(name: str) -> str:
    return "u_" + hmac.new(_subkey("audit-pseudonym"), name.encode(), hashlib.sha256).hexdigest()[:16]


def _fernet() -> Fernet:
    return Fernet(base64.urlsafe_b64encode(_subkey("appeal-contact")))


def encrypt(text: str) -> str:
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None
