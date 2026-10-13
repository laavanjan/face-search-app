"""Governance document check (run weekly by CI and on every PR).

Fails if any artefact path declared in docs/README.md is missing, or any
document's "Next review" date is in the past.

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


def main() -> int:
    problems = [f"missing artefact: {p}" for p in sorted(declared_paths()) if not (ROOT / p).exists()]
    problems += overdue_reviews(dt.date.today())
    for p in problems:
        print(f"::error::{p}")
    print(f"governance check: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
