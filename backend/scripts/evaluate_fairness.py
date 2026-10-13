"""Fairness evaluation (FAIR-01, FAIR-03): per-group and intersectional FMR/FNMR.

    python backend/scripts/evaluate_fairness.py --manifest eval.json --out governance/evidence/fairness-results.json
    python backend/scripts/evaluate_fairness.py --synthetic-demo   # exercise the pipeline, outcome is always "iterate"

Manifest: consented evaluation set with self-reported group labels
(skin_tone, age_band, gender_presentation) and embeddings produced offline by
app.services.face_engine. Groups, parity metric and numeric limits come from
governance/fairness-thresholds.yaml. Exit code 1 when the outcome is "reject".
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.services import fairness  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--manifest", type=Path)
    src.add_argument("--synthetic-demo", action="store_true")
    ap.add_argument("--threshold", type=float, default=s.search_min_threshold)
    ap.add_argument("--model", default=s.face_model_name)
    ap.add_argument("--out", type=Path, default=fairness.ROOT / "governance" / "evidence" / "fairness-results.json")
    a = ap.parse_args(argv)

    manifest = fairness.synthetic_manifest() if a.synthetic_demo else fairness.load_manifest(a.manifest)
    report = fairness.evaluate(manifest, a.threshold, a.model)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"outcome={report['outcome']} breaches={len(report['breaches'])} -> {a.out}")
    return 1 if report["outcome"] == "reject" else 0


if __name__ == "__main__":
    sys.exit(main())
