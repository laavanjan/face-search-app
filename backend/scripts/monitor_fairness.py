"""Scheduled fairness monitoring (FAIR-06). Run weekly by
.github/workflows/governance-monitoring.yml.

Evaluates the deployed model/threshold on the consented evaluation manifest
(path in FAIRNESS_MANIFEST, supplied by CI as a protected artifact) and writes a
dated report broken down by protected group and intersectional group.

Exit codes: 0 ok / iterate, 1 parity limits breached (reject), 2 no evaluation
data available (warning; the governance-review issue tracks it).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.services import fairness  # noqa: E402


def main() -> int:
    s = get_settings()
    out_dir = Path(os.environ.get("FAIRNESS_REPORT_DIR", "fairness-reports"))
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = os.environ.get("FAIRNESS_MANIFEST")
    if manifest_path and Path(manifest_path).exists():
        manifest = fairness.load_manifest(Path(manifest_path))
    else:
        print("::warning::FAIRNESS_MANIFEST not available - running synthetic demo; real monitoring pending.")
        manifest = fairness.synthetic_manifest()
    report = fairness.evaluate(manifest, s.search_min_threshold, s.face_model_name)
    path = out_dir / f"fairness-{dt.date.today().isoformat()}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"dataset={report['dataset']} outcome={report['outcome']}")
    for attr, rows in report["by_group"].items():
        for r in rows:
            print(f"  {attr}={r[attr]}: FMR {r['fmr']:.4f} FNMR {r['fnmr']:.4f} (genuine pairs={r['genuine']})")
    for b in report["breaches"]:
        print(f"::error::{b}")
    if report["outcome"] == "reject":
        return 1
    return 2 if report["synthetic"] else 0


if __name__ == "__main__":
    sys.exit(main())
