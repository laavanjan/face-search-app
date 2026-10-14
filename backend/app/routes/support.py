"""Support channel, human alternative and public disclosure (ACC-06, ACC-08, SOC-07).

POST /support (public, rate-limited, no account needed)
  - topic human_assistance is the human alternative route: ask a person to do
    the job instead of the AI (e.g. look through photos manually, or help with
    a form). It lands in the reviewers' queue like an appeal.
  - other topics: accessibility, language, cost, technical, other.
  - preferred_format lets the person say how they need the reply
    (email, phone, large print, easy read, sign-language interpreter).
GET /transparency-report (public)
  - aggregate counts for the last 90 days: searches, matches released,
    stopped cases, appeals and abuse reports by outcome, deletions.
  - counts from 1 to 4 are shown as "<5" so no individual can be singled out.
"""
from __future__ import annotations

import json
import time
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config import get_settings
from app.security import Principal, optional_principal
from app.services import appeals, db, ratelimit

router = APIRouter()

CONTACT = r"^([^@\s]+@[^@\s]+\.[^@\s]+|\+?[0-9 ()-]{7,20})$"


class SupportRequest(BaseModel):
    topic: Literal["human_assistance", "accessibility", "language", "cost", "technical", "other"]
    message: str = Field(min_length=5, max_length=2000)
    preferred_format: Literal["email", "phone", "large_print", "easy_read", "sign_language_interpreter", "other"] = "email"
    language: str = Field("en", min_length=2, max_length=10, pattern=r"^[a-zA-Z-]+$")
    contact: Optional[str] = Field(None, max_length=200, pattern=CONTACT)


@router.post("/support", status_code=201, dependencies=[Depends(ratelimit.limit_appeal_submissions)])
def support(body: SupportRequest, p: Optional[Principal] = Depends(optional_principal)):
    """Accessible contact endpoint; returns a reference + access token like an appeal."""
    text = f"[{body.topic}|reply:{body.preferred_format}|lang:{body.language}] {body.message}"
    return appeals.submit("support_request", text, None, None, None, body.contact, p)


def _bucket(n: int) -> int | str:
    return n if n == 0 or n >= 5 else "<5"


@router.get("/transparency-report")
def transparency_report():
    s = get_settings()
    since = time.time() - 90 * 86400
    with db.tx() as c:
        actions = dict(
            c.execute("SELECT action, COUNT(*) FROM audit_log WHERE ts >= ? GROUP BY action", (since,)).fetchall()
        )
        appeal_rows = c.execute(
            "SELECT category, status, outcome, created_at, resolved_at FROM appeals WHERE created_at >= ?", (since,)
        ).fetchall()
    by_cat: dict[str, dict] = {}
    days = []
    for r in appeal_rows:
        d = by_cat.setdefault(r["category"], {"received": 0, "resolved": 0, "upheld": 0})
        d["received"] += 1
        if r["status"] == "resolved":
            d["resolved"] += 1
            d["upheld"] += r["outcome"] in ("upheld", "partially_upheld")
            days.append((r["resolved_at"] - r["created_at"]) / 86400)
    days.sort()
    return {
        "period_days": 90,
        "generated_at": time.strftime("%Y-%m-%d", time.gmtime()),
        "small_counts_suppressed_below": 5,
        "searches_requested": _bucket(actions.get("search.case_created", 0)),
        "search_cases_completed": _bucket(actions.get("search.case.completed", 0)),
        "search_cases_stopped_by_reviewer": _bucket(actions.get("search.case.stopped", 0)),
        "search_cases_no_match": _bucket(actions.get("search.case.no_match", 0)),
        "matches_approved_by_humans": _bucket(actions.get("search.candidate.approve", 0)),
        "matches_rejected_by_humans": _bucket(actions.get("search.candidate.reject", 0)),
        "photos_rejected_at_index_review": _bucket(actions.get("index.reject", 0)),
        "photos_deleted": _bucket(actions.get("photo.delete", 0)),
        "appeals_and_reports": {k: {kk: _bucket(vv) for kk, vv in v.items()} for k, v in sorted(by_cat.items())},
        "median_days_to_resolve": round(days[len(days) // 2], 1) if len(days) >= 5 else None,
        "safeguards": {
            "human_review_of_every_match": True,
            "indexing_requires_approval": s.require_index_review,
            "photo_retention_days": s.photo_retention_days,
            "appeal_resolution_days": s.appeal_resolution_days,
        },
        "how_to_report_harm": "POST /abuse-reports or the 'Report misuse' option at /appeal - no account needed",
    }
