"""Fairness evaluation, thresholds and mitigation (FAIR-01..06)."""
import json
import subprocess
import sys
from pathlib import Path

from app.services import fairness

BACKEND = Path(__file__).resolve().parents[1]


def test_threshold_config_is_numeric_and_names_groups():
    t = fairness.load_thresholds()
    assert t["parity_metric"]["name"]
    assert set(t["groups"]) == set(fairness.ATTRIBUTES)
    for k, v in t["limits"].items():
        assert isinstance(v, (int, float)) and v > 0, k


def test_metrics_computed_per_group_and_intersectionally():
    r = fairness.evaluate(fairness.synthetic_manifest(), 0.35, "buffalo_l")
    t = fairness.load_thresholds()
    for attr in fairness.ATTRIBUTES:
        assert {row[attr] for row in r["by_group"][attr]} == set(t["groups"][attr])
        for row in r["by_group_detail"][attr]:
            assert 0 <= row["fmr"] <= 1 and 0 <= row["fnmr"] <= 1
            assert row["fmr_ci95"][0] <= row["fmr"] <= row["fmr_ci95"][1]
    assert len(r["intersectional"]) == 27


def test_synthetic_data_can_never_be_accepted():
    clean = fairness.synthetic_manifest(noise_base=0.3, noise_step=0.0)
    assert fairness.evaluate(clean, 0.35, "m")["outcome"] == "iterate"


def test_outcomes_on_non_synthetic_data():
    good = fairness.synthetic_manifest(noise_base=0.3, noise_step=0.0)
    good["synthetic"] = False
    assert fairness.evaluate(good, 0.35, "m")["outcome"] == "accept"

    skewed = fairness.synthetic_manifest(noise_base=1.0, noise_step=0.12)
    skewed["synthetic"] = False
    r = fairness.evaluate(skewed, 0.35, "m")
    assert r["outcome"] == "reject" and r["breaches"]

    small = fairness.synthetic_manifest(subjects_per_cell=1, noise_base=0.3, noise_step=0.0)
    small["synthetic"] = False
    assert fairness.evaluate(small, 0.35, "m")["outcome"] == "iterate"


def test_mitigation_sweep_reports_tradeoffs():
    r = fairness.mitigation_sweep(fairness.synthetic_manifest(), [0.25, 0.35, 0.45], current=0.35)
    assert r["current"]["threshold"] == 0.35
    assert r["recommended"]["worst_group_fnmr"] <= r["current"]["worst_group_fnmr"]
    assert {"overall_fmr", "overall_fnmr", "worst_group_fmr", "worst_group_fnmr"} <= set(r["sweep"][0])


def test_monitor_script_writes_group_report(tmp_path):
    env = {"FAIRNESS_REPORT_DIR": str(tmp_path), "PATH": "", "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")}
    p = subprocess.run([sys.executable, str(BACKEND / "scripts" / "monitor_fairness.py")], env=env, capture_output=True, text=True)
    assert p.returncode == 2, p.stderr  # synthetic only -> warning exit
    report = json.loads(next(tmp_path.glob("fairness-*.json")).read_text())
    assert report["by_group"]["skin_tone"]
