# CHG-0006: AWS EC2 deployment via GitHub Actions

| | |
|---|---|
| Date | 2026-11-24 |
| Requested by | @laavanjan |
| Approved by (System Owner) | @laavanjan |
| Class | minor |
| Release | v0.2.1 (no application code change) |
| Triggers | deployment |

## What changes
- `.github/workflows/deploy.yml`: after CI succeeds on `main`, builds the backend and frontend images, pushes them to ECR and deploys them to one EC2 host through SSM Run Command. AWS access is by GitHub OIDC, limited to the `production` environment of this repository.
- `backend/Dockerfile`: two-stage build. `insightface` compiles a C++ extension and needs `g++`; the compiler stays in the build stage and the runtime image gets only the virtualenv. Same dependencies, same entrypoint.
- `frontend/Dockerfile`, `docker-compose.prod.yml`, `deploy/` (Caddyfile, `bootstrap-ec2.sh`, `deploy.sh`, `README.md`), `.dockerignore` files.
- No change to `backend/app/**`, thresholds, model or retention settings.

## Re-evaluation
- Model / threshold: unchanged, so no new evaluation.
- Data: no new data. Photos and the governance DB live on the host's EBS volume (`/opt/face-search/data`); photos and Rekognition calls follow the existing `AWS_*` settings.
- Deployment: environment is a single EC2 host in the AWS region chosen at setup, served over HTTPS (Caddy / Let's Encrypt). Smoke test: `deploy.sh` waits for `GET /health` to return 200; then check `config_approved: true`.
- Privacy: no new recipients beyond AWS (already covered by `docs/privacy/cross-border-transfer-assessment.md`). Hosting region and the instance's disk are new places face data is stored. Re-check the assessment if the region is outside the one it covers.

## Re-indexing impact
None.

## Risk
- Host compromise exposes photos, the governance DB and the vector index. Mitigations: no SSH, only ports 80/443 open, secrets only on the host (`chmod 600`), `deploy.sh` refuses placeholder tokens, a missing `DATA_ENCRYPTION_KEY` or raw API tokens, and the deploy needs approval in the `production` environment.
- Single host and no standby: outages during deploys and instance failure. Mitigation: EBS snapshots.

## Rollout and rollback
First deploy follows `deploy/README.md`. Roll back by redeploying a previous commit or pinning older image tags in `/opt/face-search/stack.env`.

## Approval
Because the configuration snapshot is new on this host, an admin must approve it before indexing and search start: `POST /admin/config/approve {"change_id": "CHG-0006", ...}`.
