#!/usr/bin/env bash
# Runs ON the EC2 host (as root) via SSM Run Command from .github/workflows/deploy.yml.
# Required env: REGISTRY (ECR registry host), AWS_REGION, IMAGE_TAG (git SHA).
set -euo pipefail

: "${REGISTRY:?}" "${AWS_REGION:?}" "${IMAGE_TAG:?}"

APP=/opt/face-search
STACK="$APP/stack.env"
BACKEND_ENV="$APP/backend.env"

[ -f "$STACK" ] || { echo "Missing $STACK. Run deploy/bootstrap-ec2.sh first."; exit 1; }
[ -f "$BACKEND_ENV" ] || { echo "Missing $BACKEND_ENV. See deploy/README.md."; exit 1; }

# Refuse to run a production deploy with the example secrets.
if grep -qi 'change-me' "$BACKEND_ENV"; then
  echo "backend.env still contains change-me placeholders."; exit 1
fi
if ! grep -qE '^DATA_ENCRYPTION_KEY=.{20,}' "$BACKEND_ENV"; then
  echo "backend.env needs a real DATA_ENCRYPTION_KEY (20+ chars)."; exit 1
fi
if ! grep -qE '^API_KEYS=.*sha256:[0-9a-fA-F]{64}' "$BACKEND_ENV"; then
  echo "backend.env API_KEYS must use sha256:<hex> tokens in production."; exit 1
fi

set_var() {
  { grep -v "^$1=" "$STACK" || true; echo "$1=$2"; } > "$STACK.tmp"
  mv "$STACK.tmp" "$STACK"
}
previous_backend=$(grep '^BACKEND_IMAGE=' "$STACK" | cut -d= -f2- || true)
set_var BACKEND_IMAGE "$REGISTRY/face-search-backend:$IMAGE_TAG"
set_var FRONTEND_IMAGE "$REGISTRY/face-search-frontend:$IMAGE_TAG"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"

cd "$APP/repo"
dc() { docker compose --project-name face-search --env-file "$STACK" -f docker-compose.prod.yml "$@"; }

dc pull
dc up -d --remove-orphans

echo "Waiting for the backend to report healthy..."
for i in $(seq 1 36); do
  if dc exec -T backend python -c \
    "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=5).status == 200 else 1)" \
    >/dev/null 2>&1; then
    echo "Backend healthy after $((i * 5))s."
    docker image prune -f >/dev/null
    dc ps
    exit 0
  fi
  sleep 5
done

echo "Backend did not become healthy in 180s. Recent logs:"
dc logs --tail 80 backend
echo "Previous backend image was: ${previous_backend:-none}"
exit 1
