# Governance artefact index

Every governance, risk, human-oversight and privacy control, where it is declared, and the code and
tests that implement it. Checked weekly by `scripts/check_governance.py`.

| Last reviewed | Next review |
|---|---|
| 2026-10-14 | 2027-01-14 |

## Governance & Accountability

| Control | Requirement | Declared at | Implemented / verified in |
|---|---|---|---|
| GOV-01 | Named accountable owner; owner approves changes | `GOVERNANCE.md`, `.github/CODEOWNERS` | `.github/workflows/ci.yml` (change-record gate) |
| GOV-02 | Purpose, intended users, prohibited use | `GOVERNANCE.md` §1-3 | `frontend/app/layout.tsx`, `frontend/app/privacy/page.tsx`, consent prompts |
| GOV-03 | Stakeholder impact assessment | `docs/governance/stakeholder-impact-assessment.md` | - |
| GOV-04 | Initial project risk assessment | `docs/risk/risk-assessment.md` | - |
| GOV-05 | Oversight roles named and enforced in code | `GOVERNANCE.md` §4, `docs/oversight/human-oversight.md` | `backend/app/security.py`, `backend/app/services/controls.py`; `tests/test_governance.py::test_least_privilege`, `test_config_change_requires_approval` |
| GOV-06 | Incident response, severities, escalation | `docs/governance/incident-response.md` | `POST /admin/controls` stop switch |
| GOV-07 | Monitoring schedule + coded workflow | `docs/governance/monitoring-schedule.md` | `.github/workflows/governance-monitoring.yml` |
| GOV-08 | Change management / version policy | `docs/governance/change-management.md` | `docs/changes/`, `.github/pull_request_template.md` |
| GOV-09 | Re-evaluate on model / data / deployment change and after incidents | `docs/governance/change-management.md` §3 | `Settings.governance_snapshot()` + `controls.ensure_allowed()` |
| GOV-10 | Applicable regulations mapped to controls | `docs/compliance/regulatory-applicability.md` | - |

## Risk Management & Impact Assessment

| Control | Requirement | Declared at | Implemented / verified in |
|---|---|---|---|
| RISK-01 | Domain, stakeholders, scale, environment | `docs/risk/risk-assessment.md` §1, §3, §4 | - |
| RISK-02 | Risk tier and reasoning | `docs/risk/risk-assessment.md` §2 | - |
| RISK-03 | Ethical impacts listed, ranked, mitigated | `docs/risk/risk-assessment.md` §5-6 | tests listed in §6 |
| RISK-04 | Residual risk acceptance signed by owner | `docs/risk/residual-risk-acceptance.md` | **awaiting owner signature** |
| RISK-05 | Maintained risk register | `docs/risk/risk-register.md` | - |
| RISK-06 | When to reassess risk | `docs/risk/reassessment-policy.md` | - |

## Human Oversight & Recourse

| Control | Requirement | Declared at | Implemented / verified in |
|---|---|---|---|
| HUMO-01 | Roles, qualifications, assignment | `docs/oversight/human-oversight.md` §1-3, `docs/oversight/oversight-register.md` | `backend/app/security.py` `ROLE_PERMISSIONS` |
| HUMO-02 | Pause / override / stop; every path gated; human takeover | `docs/oversight/human-oversight.md` §4 | `services/review.py`, `services/controls.py`; `test_stop_prevents_release`, `test_human_takeover_manual_match`, `test_admin_can_pause_and_resume` |
| HUMO-03 | Appeal endpoint/UI + documented process | `docs/oversight/appeals-and-sla.md`, `frontend/app/appeal/page.tsx` | `routes/appeals.py`; `test_appeal_restricts_photo_until_resolved` |
| HUMO-04 | Timeouts, retries, abstain on low confidence | `docs/oversight/human-oversight.md` §7 | `services/resilience.py`; `test_inference_deadline_returns_504`, `test_retry_only_transient` |
| HUMO-05 | Support SLA / dispute-resolution timeline | `docs/oversight/appeals-and-sla.md` | `APPEAL_ACK_DAYS`, `APPEAL_RESOLUTION_DAYS` |
| HUMO-06 | Human approval on every high-risk path; design documented | `docs/oversight/human-oversight.md` §4 | `test_upload_is_pending_until_reviewer_approves`, `test_search_results_released_only_after_review` |
| HUMO-07 | Human review of every important decision; AI never decides alone | `docs/oversight/human-oversight.md` §4.2 | `routes/search.py` returns a case, not matches |

## Data Governance & Privacy

| Control | Requirement | Declared at | Implemented / verified in |
|---|---|---|---|
| PRIV-01 | No personal data in logs; minimal schema; filter at collection | `docs/privacy/de-identification.md` §2 | `app/logging_setup.py`, `pipeline.prepare()`, `vector_store` allowlist; `test_logs_redact_personal_data`, `test_metadata_stripped_and_filename_not_stored` |
| PRIV-02 | Legal basis documented, typed, enforced | `docs/privacy/privacy-and-ai-use.md` §2-3 | `config.LegalBasis`, `services/privacy.py`; `test_upload_requires_consent_and_is_recorded` |
| PRIV-03 | UI and docs disclose AI use | `docs/privacy/privacy-and-ai-use.md` §1 | `frontend/app/layout.tsx`, `frontend/app/privacy/page.tsx` |
| PRIV-04 | TTL, deletion endpoint/job, retention policy | `docs/privacy/data-retention-policy.md` | `services/retention.py`, `DELETE /photos/{id}`; `test_retention_ttl_purges_expired_photos` |
| PRIV-05 | RBAC on every endpoint, least privilege | `docs/oversight/human-oversight.md` §1 | `backend/app/security.py`; `test_protected_endpoints_deny_anonymous` |
| PRIV-06 | Training-data provenance, licence, permitted use | `docs/privacy/training-data.md` | `face_engine.py` (`FACE_MODEL_NAME`, `allowed_modules`) |
| PRIV-07 | Cross-border transfer assessment | `docs/privacy/cross-border-transfer-assessment.md` | config gate on AWS settings |
| PRIV-08 | De-identification method, validation, guarantee | `docs/privacy/de-identification.md` | tests in §3 of that file |
| PRIV-09 | Synthetic data: generator, source, bias, limitations | `docs/privacy/synthetic-data.md` | `backend/tests/fixtures/synthetic_faces.py`; `test_synthetic_marker_rejected_in_production` |

## Machine-readable records (`governance/*.yaml`)

Structured versions of the key policies, validated on every PR and weekly by
`scripts/check_governance.py` (required sections + review dates).

| Record | Controls |
|---|---|
| `governance/incident-response.yaml` | GOV-06, GOV-09 (serious incidents) |
| `governance/change-management.yaml` | GOV-08, GOV-09 |
| `governance/regulatory-mapping.yaml` | GOV-10 |
| `governance/risk-assessment.yaml` | RISK-01, RISK-02, GOV-04 |
| `governance/ethical-impacts.yaml` | RISK-03 |
| `governance/oversight-roles.yaml` | HUMO-01, GOV-05 |
| `governance/human-approval-gates.yaml` | HUMO-02, HUMO-06, HUMO-07 |
| `governance/data-retention-policy.yaml` | PRIV-04 |
| `governance/de-identification.yaml` | PRIV-01, PRIV-08 |
| `governance/model-training-data.yaml` | PRIV-06 |
| `governance/synthetic-data-bias-assessment.yaml` | PRIV-09 |
| `governance/data-inventory.yaml` | PRIV-01 |
| `governance/privacy-notice.yaml` | PRIV-03, TRAN-01 |
| `governance/fairness-test-plan.yaml` | FAIR-02 |
| `governance/fairness-thresholds.yaml` | FAIR-05 |
| `governance/evidence/fairness-results.json` | FAIR-01, FAIR-03 (generated by `backend/scripts/evaluate_fairness.py`) |
| `governance/fairness-mitigation-tradeoffs.yaml` | FAIR-04 (experiment: `backend/scripts/fairness_mitigation_experiment.py`) |
| `backend/scripts/monitor_fairness.py` | FAIR-06 (weekly in governance-monitoring workflow) |
| `governance/appeals-recourse.yaml` | FAIR-07, HUMO-03, HUMO-05 |
| `governance/system-limitations.yaml` | TRAN-02 |
| `governance/explainability.yaml` | TRAN-03 |
| `governance/model-card.yaml` | TRAN-04 |
| `governance/decision-log-schema.yaml` | TRAN-05, TRAN-06 (`backend/app/tracing.py`, `services/audit.py`) |
| `governance/provenance.yaml` | TRAN-08 (`services/provenance.py`) |
| `governance/safety-requirements.yaml` | SAFE-01, SAFE-04 |
| `backend/tests/test_edge_cases.py` | SAFE-02 |
| `governance/robustness-evaluation.yaml` | SAFE-03 (`backend/scripts/evaluate_robustness.py`, `tests/test_robustness.py`) |
| `governance/red-team-report.yaml` | SAFE-05 |
| `governance/threat-model.yaml` + `backend/app/middleware.py` | SEC-01 |
| `governance/llm-usage.yaml` | SEC-02 (no LLM paths; enforced by `tests/test_security.py`) |
| `governance/supply-chain-security.yaml` + `.github/workflows/security.yml` + `.gitleaks.toml` | SEC-03 |
| `backend/app/middleware.py` (RateLimitMiddleware) + `POST /abuse-reports` | SEC-04 |
| `governance/vulnerability-management.yaml` + `SECURITY.md` + `.github/dependabot.yml` | SEC-05 |
| `governance/pretrained-model-assessment.yaml` | SEC-06 |
| `governance/privacy-attack-assessment.yaml` | SEC-07 |
| `governance/system-overview.yaml` | DOC-01 |
| `governance/model-card.yaml` | DOC-03 |
| `governance/decision-log-schema.yaml` | DOC-04 |
| `backend/app/version_manifest.json` + `CHANGELOG.md` + `GET /version` | DOC-05 |
| `governance/data-retention-policy.yaml` (`evidence_access`) | DOC-06 |
| `governance/audit-log-integrity.yaml` + `GET /admin/audit/verify` | DOC-07 |
| `governance/accessibility-statement.yaml` + `frontend/app/accessibility/page.tsx` + `frontend/locales/` | ACC-01, ACC-08 |
| `governance/human-factors.yaml` | ACC-03 |
| `governance/vulnerable-users.yaml` | ACC-05 |
| `governance/human-alternative.yaml` + `POST /support` | ACC-06 |
| `governance/consent-design.yaml` | ACC-07 |
| `governance/societal-benefit.yaml` | SOC-01 |
| `governance/environmental-impact.yaml` + `backend/app/services/carbon.py` | SOC-03 |
| `governance/public-disclosure.yaml` + `GET /transparency-report` | SOC-07 |
| `governance/access-barriers.yaml` | SOC-08 |

## Change records

`docs/changes/` - one file per material or major change ([template](changes/TEMPLATE.md)).
