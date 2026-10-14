"""Environmental controls (SOC-03). Policy: governance/environmental-impact.yaml.

- Compute budget: face analysis seconds are metered per UTC day against
  INFERENCE_CPU_SECONDS_PER_DAY (app/config.py). When spent, new uploads and
  searches get 503 until midnight UTC - this bounds energy use and runaway
  batch jobs. Usage is shown in GET /admin/controls.
- Carbon tracking: offline evaluation runs (backend/scripts/evaluate_*.py) are
  wrapped in codecarbon's OfflineEmissionsTracker, appending energy (kWh) and
  CO2e to governance/evidence/emissions.csv. codecarbon is an evaluation-only
  dependency (requirements-dev.txt); without it the runs still work and log
  that tracking was skipped.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import threading
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings

try:  # evaluation-only dependency
    from codecarbon import OfflineEmissionsTracker
except ImportError:  # pragma: no cover - exercised when dev deps are absent
    OfflineEmissionsTracker = None

log = logging.getLogger(__name__)
_lock = threading.Lock()
_day = dt.date.min
_spent = 0.0


class ComputeBudgetExceeded(RuntimeError):
    pass


def _roll(today: dt.date) -> None:
    global _day, _spent
    if today != _day:
        _day, _spent = today, 0.0


def ensure_budget() -> None:
    budget = get_settings().inference_cpu_seconds_per_day
    if budget <= 0:
        return
    with _lock:
        _roll(dt.datetime.now(dt.timezone.utc).date())
        if _spent >= budget:
            raise ComputeBudgetExceeded(f"daily inference budget of {budget:.0f}s spent")


def charge(seconds: float) -> None:
    global _spent
    with _lock:
        _roll(dt.datetime.now(dt.timezone.utc).date())
        _spent += max(0.0, seconds)


def usage() -> dict:
    with _lock:
        _roll(dt.datetime.now(dt.timezone.utc).date())
        return {
            "day_utc": _day.isoformat(),
            "inference_seconds_used": round(_spent, 2),
            "inference_seconds_budget": get_settings().inference_cpu_seconds_per_day,
        }


def reset_for_tests() -> None:
    global _day, _spent
    with _lock:
        _day, _spent = dt.date.min, 0.0


@contextmanager
def track_emissions(project: str, output_dir: Path):
    """Measure energy + CO2e of an offline run with codecarbon, if installed."""
    if OfflineEmissionsTracker is None:
        log.warning("codecarbon not installed - emissions not tracked for %s", project)
        yield None
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    tracker = OfflineEmissionsTracker(
        project_name=project,
        output_dir=str(output_dir),
        output_file="emissions.csv",
        country_iso_code=os.environ.get("CODECARBON_COUNTRY", "GBR"),  # set to the deployment's grid
        log_level="error",
    )
    tracker.start()
    try:
        yield tracker
    finally:
        tracker.stop()
