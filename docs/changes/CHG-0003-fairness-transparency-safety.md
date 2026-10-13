# CHG-0003: Fairness, transparency and safety controls (audit #50)

| | |
|---|---|
| Date | 2026-10-14 |
| Requested by | Agent audit report #50 (commit f1009fe) |
| Approved by (System Owner) | @laavanjan |
| Class | material |
| Release | v0.2.1 |
| Triggers | data, deployment |

## What changes
- **Fairness**: offline evaluation module `backend/app/services/fairness.py` (fairlearn MetricFrame, per-group and intersectional FMR/FNMR with 95% CIs), scripts `evaluate_fairness.py`, `fairness_mitigation_experiment.py`, `monitor_fairness.py` (weekly CI step), thresholds/plan/trade-off records. Evaluation-only dependencies in `backend/requirements-dev.txt`.
- **Transparency**: request trace IDs (`app/tracing.py`, `X-Request-ID`), `audit_log.trace_id` + structured `rationale` on every decision, explanation endpoints and confidence bands (`services/explain.py`), signed provenance on outputs (`services/provenance.py`), model card and limitations records, UI limitation text.
- **Safety**: path/query validation on every endpoint, decompression-bomb limit, 503 fallback after retries, rate limits on failed auth and public appeals (`services/ratelimit.py`), edge-case/adversarial and OOD test suites, robustness script, red-team report.
- **Privacy/access**: appeal status lookups need a per-appeal access token; data inventory with a schema test; pipeline guard moved to the top of `pipeline.py`.

## Re-evaluation
Model, thresholds, retention unchanged (config fingerprint unchanged). 98 backend tests pass.
Fairness and robustness results are **synthetic-demo only** - outcome `iterate` until a consented evaluation set exists.

## Data / schema
SQLite migration adds `audit_log.trace_id`, `audit_log.rationale`, `appeals.access_hash` automatically on start-up. Appeals filed before this change have no access token; staff can still see them.

## Rollout and rollback
Deploy; no config change needed. Rollback: redeploy v0.2.0 (extra columns are ignored).
