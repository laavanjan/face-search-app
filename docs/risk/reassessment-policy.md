# Risk reassessment policy

| | |
|---|---|
| Owner | System Owner (@laavanjan) |
| Last reviewed | 2026-10-14 |
| Next review | 2027-01-14 |

The [risk assessment](risk-assessment.md), [risk register](risk-register.md) and
[residual risk acceptance](residual-risk-acceptance.md) must be reassessed:

## Scheduled
- **Quarterly** (next: 2027-01-14), as part of the governance review in [monitoring-schedule.md](../governance/monitoring-schedule.md).
- When the residual risk acceptance expires.

## Event-driven - before go-live of the change
1. **Model or threshold change** - any change listed in [change-management.md §3.1](../governance/change-management.md). The running system enforces this: it pauses indexing and search until an admin approves the change with a change-record id.
2. **New data category or source**, or change to preprocessing / stored payload.
3. **New processor or region** - enabling AWS Rekognition/S3, moving Qdrant to a cloud provider, changing AWS region.
4. **Scale beyond the approved maximum** in [risk-assessment.md §4](risk-assessment.md).
5. **Change of purpose or user base** - from personal to organisational use, multi-tenant, public access, or commercial use.
6. **Weakening a human-review gate** - e.g. `REQUIRE_INDEX_REVIEW=false` or `ALLOW_SELF_REVIEW=true` in a shared deployment.
7. **New jurisdiction** - update [regulatory-applicability.md](../compliance/regulatory-applicability.md) first.
8. **Serious incident** - every P0, and any P1 involving a review gate or personal data ([incident-response.md](../governance/incident-response.md)).
9. **Appeal signal** - more than 3 upheld `incorrect_match` appeals in a quarter, or any overdue appeal.
10. **Regulatory or licence change** affecting biometrics or the InsightFace weights.

## Output
A dated update to the risk assessment and register, a change record in `docs/changes/` where a change
triggered it, and a new signed residual risk acceptance when the residual picture changed.
