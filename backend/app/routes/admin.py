"""Service Owner controls: stop/resume processing, approve config changes,
run retention, read the audit log."""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.models.schemas import ConfigApproval, ControlsUpdate
from app.security import Principal, require_permissions
from app.services import audit, controls, retention

router = APIRouter(prefix="/admin")
owner = require_permissions("system:control")


@router.get("/controls")
def get_controls(_: Principal = Depends(owner)):
    return controls.summary()


@router.post("/controls")
def set_controls(body: ControlsUpdate, p: Principal = Depends(owner)):
    if body.indexing_paused is not None:
        controls.set_paused("indexing", body.indexing_paused, p, body.reason)
    if body.search_paused is not None:
        controls.set_paused("search", body.search_paused, p, body.reason)
    return controls.summary()


@router.post("/config/approve")
def approve_config(body: ConfigApproval, p: Principal = Depends(owner)):
    return controls.approve_config(p, body.change_id, body.reason)


@router.post("/retention/run")
def run_retention(p: Principal = Depends(owner)):
    audit.record(p, "retention.manual_run")
    return retention.purge_expired()


@router.get("/audit/verify")
def verify_audit(_: Principal = Depends(require_permissions("audit:read"))):
    """Tamper check: recompute the audit-log hash chain (DOC-07)."""
    return audit.verify_chain()


@router.get("/audit")
def audit_log(
    limit: int = Query(200, ge=1, le=1000),
    action: Optional[str] = Query(None, max_length=64, pattern=r"^[a-z_.]+$"),
    _: Principal = Depends(require_permissions("audit:read")),
):
    return {"items": audit.recent(limit, action)}
