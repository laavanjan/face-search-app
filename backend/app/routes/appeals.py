"""Recourse endpoints (HUMO-03, FAIR-07). Timeline and outcome handling:
governance/appeals-recourse.yaml.

Access control (PRIV-05):
- POST /appeals is intentionally open: the people most affected (those shown
  in photos) have no account. It is validated (schemas.AppealRequest),
  rate-limited per client, and only ever *restricts* processing.
- GET /appeals/{id} is subject-scoped: it requires the X-Appeal-Token issued
  once at submission (only its hash is stored). Without it the appeal is
  indistinguishable from a missing one.
- Listing, acknowledging and resolving need appeals:manage, behind the
  router-level authentication in main.py.
"""
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, Header, Path

from app.models.schemas import AppealRequest, AppealResolve
from app.security import Principal, optional_principal, require_permissions
from app.services import appeals, ratelimit

AppealId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]

public_router = APIRouter(prefix="/appeals")
router = APIRouter(prefix="/appeals")
manager = require_permissions("appeals:manage")


@public_router.post("", status_code=201, dependencies=[Depends(ratelimit.limit_appeal_submissions)])
def submit(body: AppealRequest, p: Optional[Principal] = Depends(optional_principal)):
    """Returns the appeal with a one-time `access_token` for status lookups."""
    return appeals.submit(
        body.category, body.reason, body.photo_id, body.face_id, body.case_id, body.contact, p
    )


@public_router.get("/{appeal_id}")
def status(
    appeal_id: AppealId,
    x_appeal_token: Annotated[Optional[str], Header(max_length=64)] = None,
):
    """Status for the appellant only: needs the X-Appeal-Token from submission."""
    return appeals.public_view(appeal_id, x_appeal_token)


@router.get("")
def list_appeals(
    status: Optional[Literal["received", "in_review", "resolved"]] = None,
    _: Principal = Depends(manager),
):
    return {"items": appeals.list_all(status)}


@router.post("/{appeal_id}/acknowledge")
def acknowledge(appeal_id: AppealId, p: Principal = Depends(manager)):
    return appeals.acknowledge(appeal_id, p)


@router.post("/{appeal_id}/resolve")
def resolve(appeal_id: AppealId, body: AppealResolve, p: Principal = Depends(manager)):
    return appeals.resolve(appeal_id, body.outcome, body.resolution, body.action, p)
