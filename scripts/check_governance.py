"""Governance document check (run weekly by CI and on every PR).

Fails if any artefact path declared in docs/README.md is missing, any
document's "Next review" date is in the past, or a machine-readable record in
governance/*.yaml is missing a required section (e.g. severity levels,
re-evaluation triggers, ranked impacts with mitigations).

    python scripts/check_governance.py
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "README.md"
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def declared_paths() -> set[str]:
    paths = set()
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or "Declared at" in line:
            continue
        cells = line.split("|")
        if len(cells) > 4:
            for p in re.findall(r"`([^`]+)`", cells[3]):
                if "/" in p or p.endswith(".md"):
                    paths.add(p.split(" ")[0])
    return paths


def overdue_reviews(today: dt.date) -> list[str]:
    bad = []
    docs = [ROOT / "GOVERNANCE.md", *sorted((ROOT / "docs").rglob("*.md"))]
    for doc in docs:
        if doc.parent.name == "changes":
            continue
        for line in doc.read_text(encoding="utf-8").splitlines():
            if "next review" in line.lower() or "next access review" in line.lower():
                m = DATE.search(line)
                if m and dt.date.fromisoformat(m.group(1)) < today:
                    bad.append(f"{doc.relative_to(ROOT)}: next review {m.group(1)} has passed")
                break
    return bad


# governance/<file>.yaml -> top-level keys that must be present.
REQUIRED_RECORDS: dict[str, list[str]] = {
    "incident-response.yaml": ["owner", "severity_levels", "escalation_contacts", "runbook", "serious_incident_reevaluation"],
    "change-management.yaml": ["owner", "versioning", "reevaluate_before_release_when", "enforcement"],
    "regulatory-mapping.yaml": ["owner", "regulations"],
    "risk-assessment.yaml": ["owner", "risk_tier", "risk_tier_reasoning", "application_domain", "stakeholders", "scale", "environment"],
    "ethical-impacts.yaml": ["owner", "ranking_method", "impacts"],
    "oversight-roles.yaml": ["owner", "roles", "assignment_process", "separation_of_duties"],
    "human-approval-gates.yaml": ["owner", "high_risk_decision_paths", "human_controls"],
    "data-retention-policy.yaml": ["owner", "schedule", "evidence_access", "deletion_mechanisms"],
    "de-identification.yaml": ["owner", "privacy_guarantee", "methods", "validation"],
    "model-training-data.yaml": ["owner", "model", "licences", "permitted_use", "prohibited_use"],
    "synthetic-data-bias-assessment.yaml": ["owner", "sources", "bias_assessment", "limitations_disclosed"],
    "data-inventory.yaml": ["owner", "sqlite", "qdrant_payload"],
    "fairness-thresholds.yaml": ["owner", "parity_metric", "groups", "limits", "outcomes"],
    "fairness-test-plan.yaml": ["owner", "groups_to_test", "metrics", "numeric_thresholds", "procedure"],
    "fairness-mitigation-tradeoffs.yaml": ["owner", "mitigation_evaluated", "tradeoffs", "decision"],
    "model-card.yaml": ["owner", "model", "evaluation_approach", "system_description", "assumptions", "intended_use", "forbidden_use"],
    "system-limitations.yaml": ["owner", "failure_modes", "uncertainty_signals", "user_facing_text"],
    "explainability.yaml": ["owner", "approach", "endpoints", "why_this_fits"],
    "safety-requirements.yaml": ["owner", "requirements", "input_validation_by_endpoint"],
    "red-team-report.yaml": ["owner", "scenarios", "open_findings"],
    "robustness-evaluation.yaml": ["owner", "shifts_evaluated", "results", "interpretation"],
    "appeals-recourse.yaml": ["owner", "endpoints", "timeline", "outcome_handling"],
    "privacy-notice.yaml": ["owner", "ai_disclosure", "how_data_is_used", "legal_basis"],
    "decision-log-schema.yaml": ["owner", "columns", "rationale_fields", "decision_paths_logged"],
    "provenance.yaml": ["owner", "marked_outputs", "provenance_fields"],
    "threat-model.yaml": ["owner", "assets", "trust_boundaries", "threats", "gaps"],
    "llm-usage.yaml": ["owner", "llm_or_agent_paths", "enforcement", "input_schema_validation", "exfiltration_controls"],
    "supply-chain-security.yaml": ["owner", "lockfiles", "sbom", "secret_scanning", "branch_protection"],
    "vulnerability-management.yaml": ["owner", "detection", "severity_and_fix_times", "process", "cve_disclosure"],
    "pretrained-model-assessment.yaml": ["owner", "licence", "known_limitations", "safety_testing_record", "fitness_for_purpose"],
    "privacy-attack-assessment.yaml": ["owner", "membership_inference", "model_inversion"],
    "system-overview.yaml": ["owner", "purpose", "intended_users", "scope", "assumptions", "limitations"],
    "audit-log-integrity.yaml": ["owner", "append_only", "tamper_detection"],
}

# FAIR-03: the fairness result must hold numeric metrics and a valid outcome.
FAIRNESS_RESULT = ROOT / "governance" / "evidence" / "fairness-results.json"


def fairness_result_problems() -> list[str]:
    import json

    if not FAIRNESS_RESULT.exists():
        return ["missing governance/evidence/fairness-results.json"]
    r = json.loads(FAIRNESS_RESULT.read_text(encoding="utf-8"))
    bad = []
    if r.get("outcome") not in {"accept", "reject", "iterate"}:
        bad.append("fairness-results.json: outcome must be accept|reject|iterate")
    if not r.get("interpretation"):
        bad.append("fairness-results.json: missing interpretation")
    for attr, rows in (r.get("by_group") or {}).items():
        for row in rows:
            if not all(isinstance(row.get(k), (int, float)) for k in ("fmr", "fnmr", "genuine", "impostor")):
                bad.append(f"fairness-results.json: non-numeric metrics for {attr}")
                break
    if not r.get("by_group"):
        bad.append("fairness-results.json: no per-group metrics")
    return bad


def record_problems(today: dt.date) -> list[str]:
    bad = []
    for name, keys in REQUIRED_RECORDS.items():
        path = ROOT / "governance" / name
        if not path.exists():
            bad.append(f"missing governance record: governance/{name}")
            continue
        text = path.read_text(encoding="utf-8")
        top = set(re.findall(r"^([a-z_]+):", text, re.M))
        bad += [f"governance/{name}: missing section '{k}'" for k in keys if k not in top]
        m = re.search(r"^next_review:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
        if not m:
            bad.append(f"governance/{name}: no next_review date")
        elif dt.date.fromisoformat(m.group(1)) < today:
            bad.append(f"governance/{name}: next review {m.group(1)} has passed")
    impacts = ROOT / "governance" / "ethical-impacts.yaml"
    if impacts.exists():
        t = impacts.read_text(encoding="utf-8")
        if t.count("- rank:") != t.count("mitigation:"):
            bad.append("governance/ethical-impacts.yaml: every ranked impact needs a mitigation")
    return bad


def main() -> int:
    problems = [f"missing artefact: {p}" for p in sorted(declared_paths()) if not (ROOT / p).exists()]
    problems += overdue_reviews(dt.date.today())
    problems += record_problems(dt.date.today())
    problems += fairness_result_problems()
    for p in problems:
        print(f"::error::{p}")
    print(f"governance check: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
