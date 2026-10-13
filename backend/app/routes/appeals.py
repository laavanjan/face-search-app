"""Recourse: anyone can appeal; staff with appeals:manage resolve."""
from typing import Optional

from fastapi import APIRouter, Depends

from app.models.schemas import AppealRequest, AppealResolve
from app.security import Principal, optional_principal, require_permissions
from app.services import appeals

router = APIRouter(prefix="/appeals")
manager = require_permissions("appeals:manage")


@router.post("", status_code=201)
def submit(body: AppealRequest, p: Optional[Principal] = Depends(optional_principal)):
    return appeals.submit(
        body.category, body.reason, body.photo_id, body.face_id, body.case_id, body.contact, p
    )


@router.get("")
def list_appeals(status: Optional[str] = None, _: Principal = Depends(manager)):
    return {"items": appeals.list_all(status)}


@router.get("/{appeal_id}")
def status(appeal_id: str):
    """Public status lookup by the (unguessable) appeal id. No contact details."""
    return appeals.public_view(appeal_id)


@router.post("/{appeal_id}/acknowledge")
def acknowledge(appeal_id: str, p: Principal = Depends(manager)):
    return appeals.acknowledge(appeal_id, p)


@router.post("/{appeal_id}/resolve")
def resolve(appeal_id: str, body: AppealResolve, p: Principal = Depends(manager)):
    return appeals.resolve(appeal_id, body.outcome, body.resolution, body.action, p)
