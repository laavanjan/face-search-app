# Regulatory applicability and control mapping

| | |
|---|---|
| System | Face Search API ("face-search-api") + web UI |
| Owner | System Owner (@laavanjan) |
| Review date | 2026-10-14 |
| Next review | 2027-01-14, and before deploying to any new jurisdiction |
| Deployment jurisdictions | Not yet deployed beyond local/dev. **Each new deployment must record its jurisdiction(s) here before go-live.** |

> This is an engineering applicability assessment, not legal advice. A qualified privacy lawyer should
> confirm it before any production deployment that processes other people's faces.

## 1. Why biometric law applies

The service turns uploaded photos into 512-d face embeddings (`backend/app/services/face_engine.py`) and
compares them 1:N to find the same person (`pipeline.search`). That is processing of **biometric data
for the purpose of uniquely identifying a natural person**, which most privacy regimes treat as a
special or sensitive category.

## 2. Applicability determination

| Regulation | Applies? | Determination |
|---|---|---|
| **EU GDPR** (Reg. 2016/679), **UK GDPR** + DPA 2018 | Yes, if operators or data subjects are in the EU/UK | Art. 9 special-category data → explicit consent (Art. 9(2)(a)) is the chosen condition; Art. 6 basis = consent. DPIA (Art. 35) required: covered by [risk-assessment.md](../risk/risk-assessment.md). Household exemption may apply to a purely personal library, but not to any organisational use. |
| **EU AI Act** (Reg. 2024/1689) | Yes, if placed on the market / used in the EU | Remote biometric identification systems are high-risk (Annex III point 1(a)); untargeted scraping of facial images to build recognition databases is prohibited (Art. 5(1)(e)) - excluded by our prohibited-use policy. Purely personal non-professional use is outside scope (Art. 2(10)). |
| **Illinois BIPA** (740 ILCS 14) | Yes, if any data subject is in Illinois | Written release before collection; publicly available retention schedule with destruction when purpose is satisfied or within 3 years; no sale/profit; reasonable security. |
| **Texas CUBI** (Bus. & Com. Code §503.001), **Washington** RCW 19.375 | Yes, if subjects in TX / WA | Notice + consent before capture for a commercial purpose; destruction within a reasonable time / 1 year after purpose expires (TX). |
| **California CCPA/CPRA** | Yes, if a covered business processing CA residents' data | Biometric = sensitive personal information: notice at collection, right to limit, delete, know. |
| **Other national privacy laws** (e.g. Canada PIPEDA, Australia Privacy Act, Sri Lanka PDPA No. 9 of 2022, India DPDP Act 2023) | Assess per deployment | Most treat biometrics as sensitive; consent + purpose limitation + deletion rights are the common denominator, which the controls below address. |
| **AWS Service Terms** (Rekognition, S3) | Only when AWS is configured | Contractual. Rekognition terms allow AWS to use content to improve the service unless opted out via an AWS Organizations AI services opt-out policy - **opt out before enabling**. |
| **InsightFace model licence** | Always | Pretrained weights are for non-commercial research use; see [training-data.md](../privacy/training-data.md). |

## 3. Requirement → implementation mapping

Status: **Implemented** (code/test evidence), **Documented** (policy only), **Gap** (owner + target).

| Requirement | Source | Implementation / evidence | Owner | Status / gap |
|---|---|---|---|---|
| Lawful basis + explicit consent for biometrics | GDPR 6, 9(2)(a); BIPA 15(b) | `DATA_PROCESSING_LEGAL_BASIS` (enum, `config.py`); `/upload` and `/search` reject without `consent=true` and log `lawful_basis.asserted` with notice version (`services/privacy.py`); unchecked consent box in UI | System Owner | Implemented. Gap: consent is asserted by the operator, not collected from each data subject. Target: per-subject consent records before any organisational deployment (2027-01-14). |
| Transparency / notice at collection | GDPR 13; CCPA 1798.100; AI Act 50 | Persistent AI notice in `frontend/app/layout.tsx`; `/privacy` page; `GET /policy`; [privacy-and-ai-use.md](../privacy/privacy-and-ai-use.md) | System Owner | Implemented |
| Public retention schedule + destruction | BIPA 15(a); GDPR 5(1)(e); TX CUBI | `PHOTO_RETENTION_DAYS` TTL enforced by `services/retention.py` (hourly sweep + `python -m app.jobs.retention`); [data-retention-policy.md](../privacy/data-retention-policy.md) | Privacy Owner | Implemented |
| Right to erasure / deletion | GDPR 17; CCPA 1798.105 | `DELETE /photos/{id}`; appeal category `deletion_request` with `delete_photo` action; removes file + all vectors + pending candidates (`test_delete_endpoint_removes_file_and_vectors`) | Privacy Owner | Implemented |
| Right to object / restrict | GDPR 18, 21 | Appeal of category `indexing_objection` / `incorrect_match` immediately sets photo `disputed` (excluded from search) | Human Reviewer | Implemented |
| Right of access | GDPR 15; CCPA 1798.110 | Appeal category `access_request`; handled manually by reviewer within SLA | Privacy Owner | Documented. Gap: no self-service export. Target 2027-04-14. |
| Human oversight of high-risk AI | AI Act 14; GDPR 22 | Index approval gate, search-case review gate, stop switch, manual takeover ([human-oversight.md](../oversight/human-oversight.md)) | Human Reviewer | Implemented |
| Accuracy, robustness | AI Act 15 | Minimum similarity floor; detector thresholds; deadlines + retries (`services/resilience.py`) | System Owner | Partially implemented. Gap: no demographic fairness evaluation yet (risk R-03). Target 2027-01-14. |
| Record keeping / logging | AI Act 12; GDPR 30 | Audit log (`services/audit.py`); processing record at `GET /policy` | System Owner | Implemented |
| Security of processing | GDPR 32; BIPA 15(e) | RBAC deny-by-default (`security.py`); private storage + authenticated `/photos`; photo-id validation; log redaction (`logging_setup.py`) | System Owner | Implemented. Gap: no encryption at rest configured for local disk; enable S3 SSE / disk encryption in production. |
| Data minimisation | GDPR 5(1)(c) | EXIF/GPS stripped and filename dropped before storage and before AWS (`pipeline.prepare`); Qdrant payload allowlist; age/gender models not loaded | System Owner | Implemented |
| International transfers | GDPR Ch. V | Off by default; [cross-border-transfer-assessment.md](../privacy/cross-border-transfer-assessment.md) required before enabling AWS outside the data subjects' region | Privacy Owner | Documented |
| Breach notification | GDPR 33-34; state laws | [incident-response.md](../governance/incident-response.md) | Incident Owner | Documented |
| DPIA / risk assessment | GDPR 35; AI Act 9 | [risk-assessment.md](../risk/risk-assessment.md), [risk-register.md](../risk/risk-register.md) | System Owner | Documented |
| No sale / profit from biometrics | BIPA 15(c) | Prohibited in [GOVERNANCE.md](../../GOVERNANCE.md) §3 | System Owner | Documented |
