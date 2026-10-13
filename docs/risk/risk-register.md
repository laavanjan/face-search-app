# Risk register

| | |
|---|---|
| Owner | System Owner (@laavanjan) |
| Last reviewed | 2026-10-14 |
| Next review | 2027-01-14 (quarterly, per [monitoring-schedule.md](../governance/monitoring-schedule.md)) |

Scoring: Likelihood (L) and Impact (I) 1-5; score = L × I. **≥ 15 high, 8-14 medium, ≤ 7 low.**
Scores are residual (after current controls).

| ID | Risk | Category | L | I | Score | Controls in place | Further action | Owner | Due | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| R-01 | Faces indexed without the subject's consent | Privacy | 3 | 5 | 15 | Consent confirmation + audit; index review gate; appeal-triggered restriction; TTL | Collect per-subject consent records for organisational deployments | System Owner | 2027-01-14 | Open |
| R-02 | False match released to a requester | Ethics / accuracy | 2 | 4 | 8 | Similarity floor; reviewer verification before release; appeal on every result | Measure reviewer agreement rate quarterly | Human Reviewer | 2027-01-14 | Open |
| R-03 | Unequal error rates across demographic groups | Fairness | 3 | 4 | 12 | Human review; documented limitation; synthetic tests not used for accuracy | Build lawful, consented evaluation set; measure FMR/FNMR by group before any threshold/model change | System Owner | 2027-01-14 | Open |
| R-04 | API key leak gives access to photos | Security | 2 | 5 | 10 | Per-role keys; sha256 key option; session-only storage in browser; audit log; key revocation in runbook | Move to OIDC/short-lived tokens before multi-tenant use | System Owner | 2027-04-14 | Open |
| R-05 | Images transferred to AWS without adequate safeguards | Privacy / legal | 1 | 4 | 4 | AWS off by default; config gate; sanitized bytes only | Complete transfer assessment + AI opt-out before enabling | Privacy Owner | On enablement | Mitigated |
| R-06 | `buffalo_l` licence (non-commercial) breached by commercial use | Legal | 2 | 4 | 8 | Licence recorded; prohibited use stated | Obtain commercial licence or swap model before any commercial deployment | System Owner | Before commercial use | Open |
| R-07 | Single maintainer → no real separation of duties | Governance | 4 | 3 | 12 | `ALLOW_SELF_REVIEW=false` enforced in code | Assign a second Human Reviewer in the oversight register | System Owner | 2027-01-14 | Open - accepted time-limited |
| R-08 | Model stall or Qdrant outage blocks service | Reliability | 2 | 2 | 4 | Inference deadline, retries, timeouts, health endpoint | - | System Owner | - | Mitigated |
| R-09 | Data kept longer than necessary | Privacy | 1 | 3 | 3 | TTL sweep; query-image deletion; appeal/audit retention | - | Privacy Owner | - | Mitigated |
| R-10 | Repurposing for surveillance | Ethics / misuse | 2 | 5 | 10 | Prohibited-use policy in UI and docs; audit of every search; stop switch | Quarterly audit-log review for unusual search volume | System Owner | 2027-01-14 | Open |
| R-11 | Local disk / Qdrant not encrypted at rest | Security | 2 | 4 | 8 | Private storage; authenticated access | Enable disk encryption / S3 SSE-KMS in production | System Owner | Before production | Open |

## Change log

| Date | Change | By |
|---|---|---|
| 2026-10-14 | Register created after the 2026-10-13 agent audit; R-01-R-11 added | @laavanjan |
