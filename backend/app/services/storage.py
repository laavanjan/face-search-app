"""Photo storage abstraction: S3 when AWS is configured, local disk otherwise.

Objects are private. Photos are only ever served through the authenticated
`GET /photos/{photo_id}` route; there are no public bucket URLs.
"""
from __future__ import annotations

import logging
import re

from app.config import get_settings
from app.services.resilience import aws_config

log = logging.getLogger(__name__)

_s3 = None

# Server-generated ids only: 32 hex chars + image extension. Rejecting
# anything else also blocks path traversal on the local backend.
PHOTO_ID_RE = re.compile(r"^[0-9a-f]{32}\.(jpg|jpeg|png|webp)$")


def valid_photo_id(photo_id: str) -> bool:
    return bool(PHOTO_ID_RE.fullmatch(photo_id))


def _check(photo_id: str) -> None:
    if not valid_photo_id(photo_id):
        raise FileNotFoundError("invalid photo id")


def _get_s3():
    global _s3
    s = get_settings()
    if not s.use_s3:
        return None
    if _s3 is None:
        import boto3

        _s3 = boto3.client(
            "s3",
            aws_access_key_id=s.aws_access_key_id,
            aws_secret_access_key=s.aws_secret_access_key,
            region_name=s.aws_region,
            config=aws_config(),
        )
    return _s3


def backend_name() -> str:
    return "s3" if get_settings().use_s3 else "local"


def save(photo_id: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """Persist bytes under `photo_id`; return the (authenticated) API path."""
    _check(photo_id)
    s = get_settings()
    client = _get_s3()
    if client is not None:
        client.put_object(
            Bucket=s.s3_bucket_name,
            Key=f"photos/{photo_id}",
            Body=data,
            ContentType=content_type,
        )
    else:
        (s.photo_dir / photo_id).write_bytes(data)
    return public_url(photo_id)


def load(photo_id: str) -> bytes:
    _check(photo_id)
    s = get_settings()
    client = _get_s3()
    if client is not None:
        try:
            obj = client.get_object(Bucket=s.s3_bucket_name, Key=f"photos/{photo_id}")
        except client.exceptions.NoSuchKey as e:
            raise FileNotFoundError("photo") from e
        return obj["Body"].read()
    path = s.photo_dir / photo_id
    if not path.exists():
        raise FileNotFoundError("photo")
    return path.read_bytes()


def delete(photo_id: str) -> bool:
    """Remove the stored object. Returns True if something was deleted."""
    _check(photo_id)
    s = get_settings()
    client = _get_s3()
    if client is not None:
        existed = exists(photo_id)
        client.delete_object(Bucket=s.s3_bucket_name, Key=f"photos/{photo_id}")
        return existed
    path = s.photo_dir / photo_id
    if path.exists():
        path.unlink()
        return True
    return False


def public_url(photo_id: str) -> str:
    # Always the protected API route, never a direct S3 URL.
    return f"/photos/{photo_id}"


def exists(photo_id: str) -> bool:
    if not valid_photo_id(photo_id):
        return False
    s = get_settings()
    if s.use_s3:
        try:
            _get_s3().head_object(Bucket=s.s3_bucket_name, Key=f"photos/{photo_id}")
            return True
        except Exception:
            return False
    return (s.photo_dir / photo_id).exists()
