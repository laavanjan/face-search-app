# Residual risk acceptance record

| | |
|---|---|
| System | Face Search API + web UI, v0.2.0 |
| Risk assessment | [risk-assessment.md](risk-assessment.md) (2026-10-14) |
| Register snapshot | [risk-register.md](risk-register.md) (2026-10-14) |
| Scope of acceptance | Local / personal, non-commercial deployment with the default configuration (AWS off) |
| Valid until | 2027-01-14, or earlier on any trigger in [reassessment-policy.md](reassessment-policy.md) |

## Risks accepted

| ID | Residual score | Rationale for acceptance | Condition |
|---|---|---|---|
| R-01 | 15 (high) | Operator-asserted consent plus reviewer approval and immediate restriction on objection is proportionate for a personal library | **Not accepted** for organisational use - per-subject consent records required first |
| R-03 | 12 | Every match is verified by a human before release, which limits the impact of unequal error rates while an evaluation set is built | Fairness evaluation must precede any threshold or model change |
| R-07 | 12 | Single-maintainer project; code still enforces separation of duties, so a second reviewer key is needed to release results | Second reviewer assigned by 2027-01-14 |
| R-04, R-06, R-10, R-11 | 8-10 | Controls in place; further actions are tied to moving beyond personal/non-commercial use | Revisit before any shared or commercial deployment |

## Risks not accepted

Any use listed as prohibited in [GOVERNANCE.md §3](../../GOVERNANCE.md), any commercial deployment
(R-06), and any deployment with AWS enabled before the transfer assessment is complete (R-05).

## Sign-off

By signing, the System Owner accepts the residual risks above, within the stated scope and period.

| Role | Name / handle | Signature | Date |
|---|---|---|---|
| System Owner | @laavanjan | Signed - accepted by @laavanjan; entered at the owner's explicit instruction by Claude Code | 2026-10-14 |

> Status: **accepted.** The System Owner accepts the residual risks above, within the stated scope,
> until 2027-01-14.
