# Governance - Face Search

| | |
|---|---|
| System | Face Search API + web UI (`backend/`, `frontend/`, `docker-compose.yml`, Qdrant / photo storage) |
| Risk tier | **High** - biometric identification (see [docs/risk/risk-assessment.md](docs/risk/risk-assessment.md)) |
| Accountable owner | **@laavanjan** (System Owner) |
| Document owner | @laavanjan |
| Last reviewed | 2026-10-14 |
| Next review | 2027-01-14 |

Index of every governance artefact and the control it satisfies: [docs/README.md](docs/README.md).

## 1. Purpose

Face Search finds the photos a given person appears in, **within a private photo collection that the
operator is entitled to process and where the people shown have consented**. A user uploads photos
(indexing) and later searches with a reference photo; the system proposes visually similar faces, and a
human reviewer confirms or rejects each one before anything is released.

## 2. Intended users

| User | Who they are |
|---|---|
| Operator | An individual organising their own photo library, or a staff member of an organisation searching images it is entitled to process (e.g. event photos with attendee consent). Uploads and searches. |
| Human Reviewer | A trained person, distinct from the operator, who approves indexing and verifies every search candidate. |
| Service Owner / admin | Runs the deployment, pauses processing, approves configuration changes, executes deletions. |
| Data subject | Anyone who appears in a photo. Not necessarily a user, but always able to appeal at `/appeal` without an account. |

## 3. Prohibited use

The system must **not** be used to:

- identify, track or surveil people without their authorisation or consent, including in public spaces or from CCTV;
- search for or identify strangers;
- process images scraped from the internet, social media or other public sources, or build a face database from them;
- support law-enforcement, border or immigration identification;
- make or support decisions about employment, housing, credit, insurance, education, healthcare or access to services;
- infer age, gender, ethnicity, emotion or other attributes (the code deliberately does not load those models);
- retrain, fine-tune or benchmark models on uploaded photos or embeddings, or export them as a dataset.

The UI repeats this at the point of use (`frontend/app/layout.tsx`, `/privacy`), and every upload and
search requires a consent confirmation that is written to the audit log.

## 4. Accountability and oversight roles

Roles, qualifications and how people are assigned are defined in
[docs/oversight/human-oversight.md](docs/oversight/human-oversight.md). Current assignees are recorded in
[docs/oversight/oversight-register.md](docs/oversight/oversight-register.md).

| Role | Accountable for | Enforced in code by |
|---|---|---|
| System Owner (@laavanjan) | Overall operation and risk acceptance; approves material changes; incident commander | `admin` role → `system:control`, `photos:delete`, `audit:read` (`backend/app/security.py`) |
| Human Reviewer | Indexing approval, verifying search candidates, appeals | `reviewer` role → `review:decide`, `appeals:manage` |
| Privacy & Incident Owner (@laavanjan, interim) | Deletion/access requests, retention, breach handling | `admin` role; appeal resolution with `delete_photo` |
| Operator | Lawful, in-scope use of upload and search | `operator` role → `photos:write`, `photos:search` |

Oversight scope covers `/upload`, `/search`, `/search/cases/*`, `/gallery`, `/photos/{photo_id}`,
`/review/*`, `/appeals/*` and `/admin/*`, including face-image retention, access reviews, model and
threshold changes, and incident escalation.

Code-level gates:

- **Deny-by-default RBAC**: every data endpoint requires a key whose role grants the specific permission (401/403 otherwise).
- **Separation of duties**: a reviewer cannot approve their own upload or search (`ALLOW_SELF_REVIEW=false`).
- **Approval gate on governance-sensitive config**: changing the model, detection thresholds, search floor, AWS usage, legal basis or retention pauses indexing and search until an admin approves the change with a change-record id (`backend/app/services/controls.py`).
- **Stop switch**: admins can pause indexing or search instantly (`POST /admin/controls`).
- **Audit log**: every approval, rejection, stop, deletion, config approval and consent confirmation is recorded with actor and role.

## 5. Change approval

- `.github/CODEOWNERS` assigns every path to @laavanjan. On the GitHub repository, enable branch protection on `main`: require a pull request, 1 approving review, **review from Code Owners**, and passing `CI` checks. *(Repository settings - must be switched on by the owner; it cannot be set from the code.)*
- CI (`.github/workflows/ci.yml`) fails a pull request that changes governance-sensitive files without adding a change record in `docs/changes/`.
- Policy: [docs/governance/change-management.md](docs/governance/change-management.md).

## 6. Escalation

| Step | Contact | When |
|---|---|---|
| 1 | Human Reviewer via `/review` | Disputed match, indexing question |
| 2 | System Owner @laavanjan (GitHub issue labelled `governance` or `incident`) | Appeal decision disputed, P1/P2 incident, policy question |
| 3 | System Owner, private security advisory on GitHub | P0 incident, suspected data exposure |

Severity definitions and response times: [docs/governance/incident-response.md](docs/governance/incident-response.md).

## 7. Known gaps

Single-maintainer project: until a second person is assigned as Human Reviewer, separation of duties
can only be met by issuing a reviewer key to someone else. This is tracked as R-07 in the
[risk register](docs/risk/risk-register.md) and accepted, time-limited, in the
[residual risk acceptance](docs/risk/residual-risk-acceptance.md).
