"""Pinned versions (DOC-05), loaded from app/version_manifest.json.

Every output's provenance block, the OpenAPI version and GET /version report
these values, so any result can be tied to the exact code, model and data
schema that produced it.
"""
import json
from pathlib import Path

MANIFEST: dict = json.loads((Path(__file__).with_name("version_manifest.json")).read_text(encoding="utf-8"))

APP_VERSION: str = MANIFEST["code"]["version"]
MODEL_NAME: str = MANIFEST["model"]["name"]
DB_SCHEMA_VERSION: int = MANIFEST["data"]["governance_db_schema_version"]
