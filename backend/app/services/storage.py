"""Photo storage abstraction: S3 when AWS is configured, local disk otherwise."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import BinaryIO

from app.config import get_settings

log = logging.getLogger(__name__)

_s3 = None


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
        )
    return _s3


def backend_name() -> str:
    return "s3" if get_settings().use_s3 else "local"


def save(photo_id: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """Persist bytes under `photo_id`; return a URL/path to fetch it."""
    s = get_settings()
    client = _get_s3()
    if client is not None:
        key = f"photos/{photo_id}"
        client.put_object(
            Bucket=s.s3_bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"s3://{s.s3_bucket_name}/{key}"
    # local
    dest = s.photo_dir / photo_id
    dest.write_bytes(data)
    return f"/photos/{photo_id}"


def load(photo_id: str) -> bytes:
    s = get_settings()
    client = _get_s3()
    if client is not None:
        obj = client.get_object(Bucket=s.s3_bucket_name, Key=f"photos/{photo_id}")
        return obj["Body"].read()
    path = s.photo_dir / photo_id
    if not path.exists():
        raise FileNotFoundError(photo_id)
    return path.read_bytes()


def public_url(photo_id: str) -> str:
    s = get_settings()
    if s.use_s3:
        return f"https://{s.s3_bucket_name}.s3.{s.aws_region}.amazonaws.com/photos/{photo_id}"
    return f"/photos/{photo_id}"


def exists(photo_id: str) -> bool:
    s = get_settings()
    if s.use_s3:
        try:
            _get_s3().head_object(Bucket=s.s3_bucket_name, Key=f"photos/{photo_id}")
            return True
        except Exception:
            return False
    return (s.photo_dir / photo_id).exists()
