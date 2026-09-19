"""Optional AWS Rekognition detection layer.

If AWS creds aren't set, callers should skip this and rely on InsightFace
detection alone. This module exposes a single `detect_faces` that returns
bounding boxes + a normalized quality score, or None when Rekognition is
disabled/unavailable.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.config import get_settings

log = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    s = get_settings()
    if not s.use_rekognition:
        return None
    if _client is None:
        import boto3

        _client = boto3.client(
            "rekognition",
            aws_access_key_id=s.aws_access_key_id,
            aws_secret_access_key=s.aws_secret_access_key,
            region_name=s.aws_region,
        )
    return _client


def detect_faces(image_bytes: bytes) -> Optional[list[dict]]:
    client = _get_client()
    if client is None:
        return None
    try:
        resp = client.detect_faces(Image={"Bytes": image_bytes}, Attributes=["DEFAULT"])
    except Exception as e:  # noqa: BLE001 - AWS surface is broad
        log.warning("Rekognition call failed: %s", e)
        return None
    out = []
    for fd in resp.get("FaceDetails", []):
        bb = fd["BoundingBox"]
        quality = fd.get("Quality", {})
        sharpness = quality.get("Sharpness", 50) / 100.0
        brightness = quality.get("Brightness", 50) / 100.0
        out.append(
            {
                "bbox_rel": (bb["Left"], bb["Top"], bb["Width"], bb["Height"]),
                "confidence": fd.get("Confidence", 0) / 100.0,
                "sharpness": sharpness,
                "brightness": brightness,
                "quality": min(1.0, sharpness * 0.7 + brightness * 0.3),
            }
        )
    return out
