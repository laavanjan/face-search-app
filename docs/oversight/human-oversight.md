# Human oversight design

| | |
|---|---|
| Owner | System Owner (@laavanjan) |
| Last reviewed | 2026-10-14 |
| Next review | 2027-01-14 |
| Code | `backend/app/security.py`, `backend/app/services/review.py`, `backend/app/services/controls.py`, `backend/app/routes/review.py`, `frontend/app/review/page.tsx`, `frontend/app/admin/page.tsx` |

## 1. Roles

Named roles - not "the team". Current assignees: [oversight-register.md](oversight-register.md).

| Role | Responsibility | Decision boundaries | API role / permissions |
|---|---|---|---|
| **Service Owner** | Operates the FastAPI/Qdrant deployment; can suspend indexing and search; approves configuration changes; executes deletions; incident commander | May stop the system at any time; may not release search results (not a reviewer by default) | `admin`: `photos:read`, `photos:delete`, `system:control`, `audit:read`, `appeals:manage` |
| **Human Reviewer** | Approves photos for indexing; verifies every search candidate; decides appeals | Decides whether a candidate may be treated as a match. **Cannot** review their own upload or search | `reviewer`: `photos:read`, `review:decide`, `appeals:manage` |
| **Privacy & Incident Owner** | Handles deletion / access / objection requests, retention, breaches | Approves erasure; decides breach notifications | `admin` (deletion), `reviewer` (appeals) |
| **Operator** | Uploads photos and requests searches within permitted use | Receives only reviewer-approved results | `operator`: `photos:read`, `photos:write`, `photos:search` |
| **Viewer** | Browses the indexed library | Read-only | `viewer`: `photos:read` |

A person may hold several roles (`name:operator+reviewer:token`), but the code still blocks them from
reviewing their own work unless `ALLOW_SELF_REVIEW=true`, which itself trips the config approval gate.

## 2. Required skills and qualifications

| Role | Minimum before access is granted |
|---|---|
| Human Reviewer | Completed face-recognition limitations and bias training (automation bias; error rates differ by age, skin tone, lighting, pose; a similarity score is **not** an identity decision); read this document, [appeals-and-sla.md](appeals-and-sla.md) and the prohibited-use list; 2 supervised review sessions |
| Service Owner | Can operate Docker/Qdrant/FastAPI, read logs, rotate keys, run `POST /admin/controls`; has read [incident-response.md](../governance/incident-response.md) and [change-management.md](../governance/change-management.md) |
| Privacy & Incident Owner | Working knowledge of the biometric privacy laws in [regulatory-applicability.md](../compliance/regulatory-applicability.md); retention and deletion procedures; breach-notification rules |
| Operator | Has read the permitted / prohibited use in [GOVERNANCE.md](../../GOVERNANCE.md) and the in-app notices |

## 3. Assignment and renewal

1. The System Owner (or the engineering manager in an organisational deployment) nominates a **primary and a backup** for each role.
2. The nominee completes the qualifications in §2. The approver records **assignee, role, approver, training date, effective date, backup** in [oversight-register.md](oversight-register.md) via a pull request (Code Owner review applies).
3. Only then is an `API_KEYS` entry with that role issued. Keys are personal: one name per key.
4. Assignments are reviewed **monthly** (access review in [monitoring-schedule.md](../governance/monitoring-schedule.md)) and **after every incident**. Leavers' keys are removed the same day.

Access-control linkage: only `admin` principals can change runtime controls or approve configuration
(`system:control`); only `reviewer` principals can approve indexing or release matches (`review:decide`).

## 4. Human approval gates (fail closed)

### 4.1 Indexing

```
POST /upload ─► pipeline.ingest ─► faces stored with review_status="pending"
                                   (excluded from vector_store.search)
                                          │
                     GET /review/photos ◄─┘   reviewer sees image, bboxes, det_score, quality, uploader
                                          │
          POST /review/photos/{id} approve ─► review_status="approved" ─► searchable
                                   reject  ─► photo + vectors deleted
```

### 4.2 Disclosure of search results

```
POST /search ─► consent check ─► similarity ≥ SEARCH_MIN_THRESHOLD (server floor)
            ─► review case "pending_review"; response has case_id and NO matches
                                          │
   GET /review/cases/{id} ◄───────────────┘  reviewer sees reference photo, each candidate photo,
                                             bbox, similarity score, threshold applied
   POST /review/cases/{id}/candidates/{face_id}   approve | reject | reopen   (reason required)
   POST /review/cases/{id}/manual-match           human takeover: add a photo the model missed
   POST /review/cases/{id}/close                  completed | no_match | stopped | escalated
   POST /review/cases/{id}/reopen                 only way back from a closed state
                                          │
   GET /search/cases/{id} ─► requester sees ONLY approved matches, ONLY when status = completed
```

- **Stop**: `stopped` cases never release anything, including candidates approved before the stop.
- **Fail closed**: no decision → nothing released. Completing requires every candidate to be decided.
- **Restriction**: a photo under appeal (`disputed`) is excluded from search and from previously released matches.

### 4.3 System-level intervention
- `POST /admin/controls` pauses indexing and/or search; both endpoints return 503 **before** any face analysis.
- Governance-sensitive configuration changes pause both until an admin approves (`POST /admin/config/approve`).

## 5. Evidence shown to reviewers
Reference image, candidate image, face bounding box, detector score, quality score, similarity score,
threshold applied, requester, timestamp.

## 6. Audit fields
Every decision writes: timestamp, actor, actor roles, action (e.g. `search.candidate.approve`,
`index.reject`, `search.case.stopped`, `control.search.pause`, `config.approve`), target id, reason.
Readable by `audit:read` at `GET /admin/audit`.

## 7. Low-confidence handling and reliability
- Faces below `MIN_DET_SCORE` or `MIN_FACE_SIZE` are not indexed or used; no face → 422, no decision.
- Similarity below `SEARCH_MIN_THRESHOLD` is never proposed; callers cannot lower it.
- Deadlines: model inference `INFERENCE_TIMEOUT_SECONDS` (→ 504), Qdrant `QDRANT_TIMEOUT_SECONDS`, AWS connect/read timeouts.
- Retries: bounded exponential backoff with jitter on transient Qdrant errors (`resilience.retry`, `REMOTE_RETRY_ATTEMPTS`); botocore standard retry mode for AWS (`AWS_MAX_ATTEMPTS`). Validation errors and `no_face_detected` are never retried. Rekognition degrades to InsightFace-only after retries.

## 8. Recourse
See [appeals-and-sla.md](appeals-and-sla.md).
