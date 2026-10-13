# Governance monitoring schedule

| | |
|---|---|
| Accountable owner | System Owner (@laavanjan) |
| Last reviewed | 2026-10-14 |
| Next review | 2027-01-14 |

## Cadence

| Cadence | Check | How | Evidence recorded in |
|---|---|---|---|
| Continuous | API liveness, pause state, config approval | `GET /health` (`status`, `indexing_paused`, `search_paused`, `config_approved`); `StatusBar` in the UI polls every 5 s | Uptime monitor of the deployment |
| Hourly | Retention sweep (expired photos, vectors, cases, appeals, audit rows) | In-app sweeper (`RETENTION_SWEEP_INTERVAL_MINUTES`); on Lambda, schedule `python -m app.jobs.retention` | `retention.sweep` entries in the audit log |
| **Weekly (Mon 06:00 UTC)** | Automated: test suite, API boots and `/health` is healthy, governance documents present and not past their review date | `.github/workflows/governance-monitoring.yml` | Workflow run; on failure a GitHub issue labelled `governance-review` is opened automatically |
| Weekly | Review queue health: pending index approvals, pending search cases, appeals approaching or past SLA | `/review` console; `GET /appeals` shows `overdue` | Note in the weekly `governance-review` issue |
| Monthly | Access review: who holds which key and role in `API_KEYS`; remove leavers; confirm reviewer training is current | `docs/oversight/oversight-register.md` | Register updated with date |
| Monthly | Configuration review: `backend/.env` / deployment env vs. last approved baseline; AWS/Qdrant settings | `GET /admin/controls` → `config.approved` | Register or `governance-review` issue |
| Monthly | Dependency and vulnerability review | `pip list --outdated`, `npm outdated`, GitHub Dependabot alerts | `governance-review` issue |
| Quarterly | Full governance review: risk register, risk assessment, regulatory applicability, retention policy, this schedule | All documents in [docs/README.md](../README.md) | New "Last reviewed" dates committed via PR |

## Where decisions go

Every review produces a GitHub issue labelled `governance-review` that lists findings, decisions and
owners. Remediation is tracked as linked issues/PRs. Material findings are added to the
[risk register](../risk/risk-register.md).

## Escalation

A failed weekly run that is not explained within 2 business days becomes a P2 incident
([incident-response.md](incident-response.md)).
