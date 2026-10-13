# Oversight role register

Assignment process: [human-oversight.md §3](human-oversight.md). Changes to this file go through a
pull request reviewed by the Code Owner. Keep personal contact details out of this file.

| Last access review | Next access review |
|---|---|
| 2026-10-14 | 2026-11-14 |

| Role | Primary | Backup | Approved by | Training completed | Effective from | API_KEYS name |
|---|---|---|---|---|---|---|
| System Owner / Service Owner | @laavanjan | _unassigned_ | @laavanjan (self, as repository owner) | n/a | 2026-10-14 | `adam` in `.env.example` → replace with real name |
| Human Reviewer | @laavanjan (interim, until a second person is assigned - R-07) | _unassigned_ | @laavanjan (System Owner) | Due by 2026-11-14 (human-oversight.md §2) | 2026-10-14 | `rita` in `.env.example` → replace with real name |
| Privacy & Incident Owner | @laavanjan (interim) | _unassigned_ | @laavanjan | - | 2026-10-14 | - |

## Access review log

| Date | Reviewer | Result |
|---|---|---|
| 2026-10-14 | @laavanjan | Register created. Example keys in `backend/.env.example` are placeholders, not assignments. |
| 2026-10-14 | @laavanjan | System Owner assigned as interim Human Reviewer. One person now holds both roles, so separation of duties is not met: `ALLOW_SELF_REVIEW` stays `false`, and searches this person runs cannot be released until a second reviewer is assigned (R-07). |
