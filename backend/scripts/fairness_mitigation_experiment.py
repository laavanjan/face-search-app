"""Bias mitigation experiment (FAIR-04): group-blind threshold selection.

    python backend/scripts/fairness_mitigation_experiment.py --manifest eval.json
    python backend/scripts/fairness_mitigation_experiment.py --synthetic-demo

Sweeps candidate similarity thresholds and reports, for each, overall and
worst-group FMR/FNMR (fairlearn MetricFrame via app.services.fairness). The
recommended threshold minimises the worst-group false-match rate while keeping
every group's FNMR within governance/fairness-thresholds.yaml.

Why group-blind: per-group thresholds (e.g. fairlearn ThresholdOptimizer)
would need protected attributes at search time, i.e. inferring them from faces,
which this system prohibits. Trade-offs are recorded in
governance/fairness-mitigation-tradeoffs.yaml.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.services import fairness  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--manifest", type=Path)
    src.add_argument("--synthetic-demo", action="store_true")
    ap.add_argument("--from", dest="lo", type=float, default=0.25)
    ap.add_argument("--to", dest="hi", type=float, default=0.60)
    ap.add_argument("--step", type=float, default=0.025)
    ap.add_argument("--out", type=Path, default=fairness.ROOT / "governance" / "evidence" / "fairness-mitigation.json")
    a = ap.parse_args(argv)

    manifest = fairness.synthetic_manifest() if a.synthetic_demo else fairness.load_manifest(a.manifest)
    grid = [float(x) for x in np.arange(a.lo, a.hi + 1e-9, a.step)]
    result = fairness.mitigation_sweep(manifest, grid, current=s.search_min_threshold)
    result["dataset"] = manifest.get("dataset")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    c, r = result["current"], result["recommended"]
    print(f"current {c['threshold']}: worst FMR {c['worst_group_fmr']} FNMR {c['worst_group_fnmr']}")
    print(f"recommended {r['threshold']}: worst FMR {r['worst_group_fmr']} FNMR {r['worst_group_fnmr']} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
