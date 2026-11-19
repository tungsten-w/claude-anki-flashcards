#!/usr/bin/env bash
# Deploys the landing page to the VPS (lawrencium) behind its Traefik.
# Run it from a machine that has the `vps` SSH alias (e.g. oxygen):
#   ./website/deploy/deploy.sh anki.wtungsten.work
# Env: VPS (ssh host, default "vps"), TRAEFIK_NETWORK (default "netbird_netbird").
# Needs passwordless sudo on the VPS: traefik-dynamic/ belongs to root.
# Does not touch NetBird's docker-compose.yml nor any existing route.
set -euo pipefail

DOMAIN="${1:?usage: deploy.sh <domain>}"
VPS="${VPS:-vps}"
REMOTE_DIR="/home/almalinux/anki-site"
DYN_DIR="/home/almalinux/netbird/traefik-dynamic"
HERE="$(cd "$(dirname "$0")" && pwd)"

[[ "$DOMAIN" =~ ^[a-z0-9.-]+$ ]] || { echo "invalid domain: $DOMAIN" >&2; exit 1; }

echo "==> checking Traefik network on $VPS"
NET="${TRAEFIK_NETWORK:-netbird_netbird}"
ssh "$VPS" "docker network inspect '$NET' >/dev/null" \
  || { echo "Docker network '$NET' not found. Run: ssh $VPS \"docker inspect netbird-traefik --format '{{json .NetworkSettings.Networks}}'\" and set TRAEFIK_NETWORK." >&2; exit 1; }

echo "==> uploading files"
ssh "$VPS" "mkdir -p '$REMOTE_DIR/public'"
rsync -a --delete --chmod=D755,F644 "$HERE/../public/" "$VPS:$REMOTE_DIR/public/"
rsync -a --chmod=F644 "$HERE/docker-compose.yml" "$HERE/nginx.conf" "$VPS:$REMOTE_DIR/"

echo "==> starting container"
ssh "$VPS" "cd '$REMOTE_DIR' && TRAEFIK_NETWORK='$NET' docker compose up -d --pull always"

echo "==> adding Traefik route for $DOMAIN"
# traefik-dynamic/ is owned by root: stage the file in our folder, then install it with sudo.
sed "s/__DOMAIN__/$DOMAIN/" "$HERE/anki-site.yml.template" | ssh "$VPS" "cat > '$REMOTE_DIR/anki-site.yml'"
ssh "$VPS" "sudo -n install -m 644 -o root -g root '$REMOTE_DIR/anki-site.yml' '$DYN_DIR/anki-site.yml'" \
  || { echo "sudo failed (needs a password?). Run on the VPS: sudo install -m 644 -o root -g root $REMOTE_DIR/anki-site.yml $DYN_DIR/anki-site.yml" >&2; exit 1; }

echo "==> done. Check: curl -sI https://$DOMAIN | head -20"
