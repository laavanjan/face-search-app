#!/usr/bin/env bash
# One-time setup for the EC2 host (Amazon Linux 2023, x86_64). Run as root, e.g. from an
# SSM Session Manager shell:  sudo bash bootstrap-ec2.sh
# Attach the Elastic IP to the instance BEFORE running this, because the HTTPS hostname
# is derived from the instance's public IP.
set -euo pipefail

APP=/opt/face-search
COMPOSE_VERSION=v2.29.7

dnf install -y docker git
systemctl enable --now docker

# Compose plugin (not packaged on AL2023).
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version

# 2 GB swap: InsightFace + Qdrant + Next.js on a 4 GB instance can spike.
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

mkdir -p "$APP"/data/{qdrant,photos,governance,insightface}
chmod 700 "$APP"

# HTTPS hostname from the public IP: 203.0.113.7 -> 203-0-113-7.sslip.io
if [ ! -f "$APP/stack.env" ]; then
  token=$(curl -fsS -X PUT http://169.254.169.254/latest/api/token \
    -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')
  ip=$(curl -fsS -H "X-aws-ec2-metadata-token: $token" \
    http://169.254.169.254/latest/meta-data/public-ipv4)
  echo "SITE_ADDRESS=${ip//./-}.sslip.io" > "$APP/stack.env"
fi

echo
echo "Bootstrap done. Site address: $(grep ^SITE_ADDRESS "$APP/stack.env" | cut -d= -f2)"
echo "Next: create $APP/backend.env (see deploy/README.md), then run the Deploy workflow."
