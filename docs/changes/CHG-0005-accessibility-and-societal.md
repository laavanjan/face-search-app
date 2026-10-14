# CHG-0005: Accessibility, human factors and societal controls (audit #50, ACC/SOC)

| | |
|---|---|
| Date | 2026-10-14 |
| Requested by | Agent audit report #50 (commit f1009fe) |
| Approved by (System Owner) | @laavanjan |
| Class | material |
| Release | v0.2.1 |
| Triggers | data (retention for minors), deployment |

## What changes
- **Vulnerable users (ACC-05)**: upload asks whether anyone under 18 is shown; guardian consent required; such photos always get human review and expire after `MINOR_PHOTO_RETENTION_DAYS` (30). New payload field `minor`.
- **Human factors (ACC-03)**: search needs a permitted `purpose` (`self` | `consenting_person`); approving a low-confidence candidate needs `acknowledge_low_confidence`; reviewer console hides model scores until revealed.
- **Human alternative + support (ACC-06, ACC-08)**: public `POST /support` (human assistance, accessibility, language, cost...), reply-format choice; `/accessibility` page.
- **Accessibility (ACC-01)**: English/Spanish UI (`frontend/locales`), skip link, focus styles, keyboard-operable dropzone, labels/live regions, reduced motion, larger touch targets, plain-language copy.
- **Consent (ACC-07)**: no pre-selected answers anywhere; test guards it.
- **Societal (SOC-01/03/07/08)**: compute budget (`INFERENCE_CPU_SECONDS_PER_DAY`) with metering, codecarbon tracking of evaluation runs, public `GET /transparency-report` + `/transparency` page, client-side photo shrinking, benefit/barrier/environment records.

## Re-evaluation
Model and thresholds unchanged. 119 backend tests pass; frontend builds.

## Config gate
`MINOR_PHOTO_RETENTION_DAYS` joins the governance-sensitive settings, so an existing deployment pauses indexing and search after upgrade until an admin approves this change: `POST /admin/config/approve {"change_id": "CHG-0005", ...}`.

## API changes
`POST /search` now requires form field `purpose`. `POST /upload` accepts `minors_present` / `guardian_consent`.
