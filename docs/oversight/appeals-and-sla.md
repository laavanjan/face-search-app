# Appeals, dispute resolution and support SLA

| | |
|---|---|
| Owner | Human Reviewer (process); System Owner (escalation) |
| Last reviewed | 2026-10-14 |
| Next review | 2027-01-14 |
| User-facing page | `/appeal` (`frontend/app/appeal/page.tsx`) |
| API | `POST /appeals` (public), `GET /appeals/{id}` (public status), `GET /appeals`, `POST /appeals/{id}/acknowledge`, `POST /appeals/{id}/resolve` (`appeals:manage`) |

## Who can appeal, and what

Anyone - an account is **not** required, because the people most affected (those shown in photos) are
usually not users.

| Category | Meaning | Immediate effect |
|---|---|---|
| `incorrect_match` | A released match shows a different person | If a photo id is given: photo set to `disputed` → excluded from search and from released matches |
| `indexing_objection` | "Do not index my face" | Same restriction |
| `deletion_request` | Erase a photo of me | Same restriction; resolution with `delete_photo` removes photo + all vectors |
| `access_request` | What data do you hold about me? | Handled manually by the Privacy Owner |
| `other` | Anything else | - |

Fields submitted: category, reason (10-2000 chars), optional photo/face/case reference, optional
contact. A "Report incorrect match" button next to every released result pre-fills the references.

## SLA

| Step | Target | Configured by |
|---|---|---|
| Acknowledge (status `received` → `in_review`) | **2 days** | `APPEAL_ACK_DAYS` |
| Decision (status `resolved`) | **30 days** (GDPR one-month response window) | `APPEAL_RESOLUTION_DAYS` |
| Restriction of the referenced photo | **Immediate** on submission | `services/appeals.py` |
| Escalation of a disputed decision | System Owner responds within 10 business days | This policy |

Each appeal stores `ack_by` and `resolve_by`; the reviewer queue flags `overdue` appeals, and overdue
appeals are checked in the weekly review ([monitoring-schedule.md](../governance/monitoring-schedule.md)).
An appeal more than 30 days old is a P2 incident.

## Outcomes

| Outcome | Typical action | Effect |
|---|---|---|
| `upheld` | `delete_photo` (needs `photos:delete`) or `none` (photo stays excluded) | Erasure, or permanent restriction |
| `partially_upheld` | `none` / `delete_photo` | As decided, with explanation |
| `rejected` | `restore_photo` | Photo returns to `approved` and searchable |

The resolution text is visible to the appellant at `GET /appeals/{id}`; contact details are not.
Every action is written to the audit log.

## Escalation

If the appellant disagrees, they reply quoting the reference. The System Owner re-examines the case
(see escalation table in [GOVERNANCE.md §6](../../GOVERNANCE.md)). The appellant may also complain to
their data protection authority.

## Retention

Appeals are deleted `APPEAL_RETENTION_DAYS` (365) after resolution ([data-retention-policy.md](../privacy/data-retention-policy.md)).
