"""Offline fairness evaluation and bias mitigation for face matching.

Used by backend/scripts/evaluate_fairness.py, fairness_mitigation_experiment.py
and monitor_fairness.py - never by the API at request time.

- Metrics (fairlearn MetricFrame), computed separately per protected group and
  per intersectional group: FMR (false-match rate, impostor pairs scoring >=
  threshold) and FNMR (false-non-match rate, genuine pairs scoring < threshold),
  with Wilson 95% confidence intervals and pair counts.
- Groups and numeric limits come from governance/fairness-thresholds.yaml.
- Group labels come ONLY from a consented evaluation manifest. They are never
  inferred from images: face_engine loads detection + recognition only.
- Mitigation: a single group-blind threshold chosen to minimise the worst-group
  FMR, because per-group thresholds would require inferring protected
  attributes at search time, which this system forbids.
- Outcome: accept | reject | iterate. Synthetic data or too few pairs per group
  always yields "iterate" - it can never be used to accept a model.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from fairlearn.metrics import MetricFrame, count, false_negative_rate, false_positive_rate

ROOT = Path(__file__).resolve().parents[3]
THRESHOLDS_FILE = ROOT / "governance" / "fairness-thresholds.yaml"
ATTRIBUTES = ("skin_tone", "age_band", "gender_presentation")


def load_thresholds(path: Path = THRESHOLDS_FILE) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


# --- data -------------------------------------------------------------------------


def synthetic_manifest(
    seed: int = 7, subjects_per_cell: int = 4, images_per_subject: int = 3, noise_base: float = 1.0, noise_step: float = 0.12
) -> dict:
    """Clearly labelled synthetic evaluation set: random identities with
    group-dependent capture noise, so the pipeline and reports can be exercised
    end to end. Says nothing about the real model."""
    t = load_thresholds()
    rng = np.random.default_rng(seed)
    groups = t["groups"]
    # Capture noise per skin-tone group: genuine cosine ~ 1/(1+sigma^2), so a
    # deliberately larger sigma for one group makes the reports show a disparity.
    noise = {g: noise_base + noise_step * i for i, g in enumerate(groups["skin_tone"])}
    samples, sid = [], 0
    for st in groups["skin_tone"]:
        for ab in groups["age_band"]:
            for gp in groups["gender_presentation"]:
                for _ in range(subjects_per_cell):
                    base = rng.standard_normal(512)
                    for _ in range(images_per_subject):
                        v = base + noise[st] * rng.standard_normal(512)
                        samples.append(
                            {
                                "subject_id": f"syn-{sid}",
                                "embedding": (v / np.linalg.norm(v)).astype(np.float32).tolist(),
                                "groups": {"skin_tone": st, "age_band": ab, "gender_presentation": gp},
                            }
                        )
                    sid += 1
    return {"dataset": "synthetic-demo", "synthetic": True, "consent_basis": "n/a (generated)", "samples": samples}


def load_manifest(path: Path) -> dict:
    """JSON manifest: {dataset, consent_basis, samples: [{subject_id, groups, embedding}]}.
    Embeddings come from running face_engine on the consented images offline."""
    m = json.loads(Path(path).read_text(encoding="utf-8"))
    for s in m["samples"]:
        missing = [a for a in ATTRIBUTES if a not in s.get("groups", {})]
        if missing:
            raise ValueError(f"sample {s.get('subject_id')} lacks group labels {missing}")
    m.setdefault("synthetic", False)
    return m


def pair_frame(manifest: dict) -> pd.DataFrame:
    """All within-group comparison pairs with cosine scores."""
    s = manifest["samples"]
    emb = np.asarray([x["embedding"] for x in s], dtype=np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    sims = emb @ emb.T
    i, j = np.triu_indices(len(s), k=1)
    subj = np.asarray([x["subject_id"] for x in s])
    df = pd.DataFrame({"score": sims[i, j], "genuine": subj[i] == subj[j]})
    for a in ATTRIBUTES:
        gi = np.asarray([x["groups"][a] for x in s])
        df[a] = np.where(gi[i] == gi[j], gi[i], None)  # cross-group pairs excluded per attribute
    return df


# --- metrics ----------------------------------------------------------------------


def _wilson(k: float, n: float) -> list[float]:
    if n == 0:
        return [0.0, 1.0]
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 5), round(min(1.0, c + h), 5)]


def group_metrics(df: pd.DataFrame, threshold: float, attribute: str | list[str]) -> list[dict]:
    cols = [attribute] if isinstance(attribute, str) else list(attribute)
    sub = df.dropna(subset=cols)
    y_true = sub["genuine"].astype(int)
    y_pred = (sub["score"] >= threshold).astype(int)
    mf = MetricFrame(
        metrics={"fmr": false_positive_rate, "fnmr": false_negative_rate, "pairs": count},
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=sub[cols],
    )
    rows = []
    for key, r in mf.by_group.iterrows():
        key = key if isinstance(key, tuple) else (key,)
        mask = np.logical_and.reduce([sub[c] == k for c, k in zip(cols, key)])
        g = sub[mask]
        gen, imp = int(g["genuine"].sum()), int((~g["genuine"]).sum())
        fm = int(((g["score"] >= threshold) & ~g["genuine"]).sum())
        fnm = int(((g["score"] < threshold) & g["genuine"]).sum())
        rows.append(
            {
                "group": dict(zip(cols, key)),
                "genuine_pairs": gen,
                "impostor_pairs": imp,
                "fmr": round(float(r["fmr"]), 6),
                "fmr_ci95": _wilson(fm, imp),
                "fnmr": round(float(r["fnmr"]), 6),
                "fnmr_ci95": _wilson(fnm, gen),
            }
        )
    return rows


def evaluate(manifest: dict, threshold: float, model: str) -> dict:
    t = load_thresholds()
    lim = t["limits"]
    df = pair_frame(manifest)
    per_attr = {a: group_metrics(df, threshold, a) for a in ATTRIBUTES}
    inter = group_metrics(df, threshold, list(ATTRIBUTES))
    breaches, thin = [], []
    for a, rows in per_attr.items():
        fmrs = [r["fmr"] for r in rows]
        fnmrs = [r["fnmr"] for r in rows]
        for r in rows:
            if r["genuine_pairs"] < lim["min_genuine_pairs_per_group"] or r["impostor_pairs"] < lim["min_impostor_pairs_per_group"]:
                thin.append({"attribute": a, **r["group"]})
            if r["fmr"] > lim["max_group_fmr"]:
                breaches.append(f"{a}={r['group'][a]}: FMR {r['fmr']} > {lim['max_group_fmr']}")
            if r["fnmr"] > lim["max_group_fnmr"]:
                breaches.append(f"{a}={r['group'][a]}: FNMR {r['fnmr']} > {lim['max_group_fnmr']}")
        if max(fnmrs) - min(fnmrs) > lim["max_fnmr_gap"]:
            breaches.append(f"{a}: FNMR gap {max(fnmrs) - min(fnmrs):.4f} > {lim['max_fnmr_gap']}")
        if min(fmrs) > 0 and max(fmrs) / min(fmrs) > lim["max_fmr_ratio"]:
            breaches.append(f"{a}: FMR ratio {max(fmrs) / min(fmrs):.2f} > {lim['max_fmr_ratio']}")
    if manifest.get("synthetic"):
        outcome, why = "iterate", "Synthetic data cannot support acceptance; run on the consented evaluation set."
    elif thin:
        outcome, why = "iterate", "Some groups are below the minimum pair counts; collect more consented samples."
    elif breaches:
        outcome, why = "reject", "Parity limits breached; do not deploy this model/threshold."
    else:
        outcome, why = "accept", "All groups within limits at the evaluated threshold."
    # Summary first: readers (and tools) that only see the head of the file get the decision.
    return {
        "outcome": outcome,
        "interpretation": why,
        "run_date": dt.date.today().isoformat(),
        "dataset": manifest.get("dataset"),
        "synthetic": bool(manifest.get("synthetic")),
        "model": model,
        "threshold": threshold,
        "parity_metric": t["parity_metric"]["name"],
        "breaches": breaches,
        "by_group": {a: [_brief(r) for r in rows] for a, rows in per_attr.items()},
        "overall": group_metrics(df.assign(all="all"), threshold, "all")[0],
        "limits": lim,
        "consent_basis": manifest.get("consent_basis"),
        "insufficient_samples": thin,
        "by_group_detail": per_attr,
        "intersectional": inter,
    }


def _brief(r: dict) -> dict:
    return {**r["group"], "fmr": r["fmr"], "fnmr": r["fnmr"], "genuine": r["genuine_pairs"], "impostor": r["impostor_pairs"]}


def mitigation_sweep(manifest: dict, thresholds: list[float], current: float) -> dict:
    """Group-blind threshold mitigation: for each candidate threshold, report
    overall and worst-group FMR/FNMR; recommend the threshold with the lowest
    worst-group FMR whose worst-group FNMR stays within the limit."""
    lim = load_thresholds()["limits"]
    df = pair_frame(manifest)
    rows = []
    for th in thresholds:
        per = [r for a in ATTRIBUTES for r in group_metrics(df, th, a)]
        overall = group_metrics(df.assign(all="all"), th, "all")[0]
        rows.append(
            {
                "threshold": round(th, 3),
                "overall_fmr": overall["fmr"],
                "overall_fnmr": overall["fnmr"],
                "worst_group_fmr": max(r["fmr"] for r in per),
                "worst_group_fnmr": max(r["fnmr"] for r in per),
            }
        )
    ok = [r for r in rows if r["worst_group_fnmr"] <= lim["max_group_fnmr"]]
    best = min(ok or rows, key=lambda r: (r["worst_group_fmr"], r["worst_group_fnmr"]))
    base = min(rows, key=lambda r: abs(r["threshold"] - current))
    return {"current": base, "recommended": best, "sweep": rows, "synthetic": bool(manifest.get("synthetic"))}
