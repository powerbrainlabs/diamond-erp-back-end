#!/usr/bin/env bash
# Deploys one service on the droplet. Runs as the forced command for the
# `deploy` user's CI key, so the only input is:
#   SSH_ORIGINAL_COMMAND="<backend|frontend> <40-char git sha>"
# A short-lived GHCR token arrives on stdin and is never written to disk
# outside a temp dir that is removed on exit.
set -euo pipefail

DEPLOY_DIR=/opt/diamond-erp/deploy
STATE_FILE="$DEPLOY_DIR/.env"
REGISTRY=ghcr.io
HEALTH_TIMEOUT_SECONDS=120
MIN_FREE_GB=3
COMPOSE=(docker compose --project-directory "$DEPLOY_DIR" -f "$DEPLOY_DIR/docker-compose.yml")

log() { printf '[deploy %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
die() { log "ERROR: $*"; exit 1; }

read -r service sha extra <<<"${SSH_ORIGINAL_COMMAND:-}"
[[ -z "${extra:-}" ]] || die "unexpected extra arguments"
[[ "${sha:-}" =~ ^[0-9a-f]{40}$ ]] || die "invalid commit sha"

case "${service:-}" in
  backend)
    var=BACKEND_IMAGE
    repo=powerbrainlabs/diamond-erp-backend
    container=diamond-erp-backend
    legacy_image=diamond-erp-backend:local
    health_url=http://127.0.0.1:8081/health
    ;;
  frontend)
    var=FRONTEND_IMAGE
    repo=powerbrainlabs/diamond-erp-frontend
    container=diamond-erp-frontend-preview
    legacy_image=diamond-erp-frontend:local
    health_url=http://127.0.0.1:8080/
    ;;
  *) die "unknown service '${service:-}'" ;;
esac

# Backend and frontend deploys both rewrite STATE_FILE; run one at a time.
exec 9>"$DEPLOY_DIR/.lock"
flock -w 900 9 || die "timed out waiting for another deploy"

token=$(head -c 4096 || true)
[[ -n "$token" ]] || die "no registry token on stdin"

free_gb=$(df --output=avail -BG / | tail -1 | tr -dc '0-9')
(( free_gb >= MIN_FREE_GB )) || die "only ${free_gb}G free on /, need ${MIN_FREE_GB}G to pull"

current=$(grep -E "^${var}=" "$STATE_FILE" | cut -d= -f2- || true)
[[ -n "$current" ]] || die "$var missing from $STATE_FILE"
new="$REGISTRY/$repo:$sha"

set_image() {
  local value=$1 tmp
  tmp=$(mktemp "$DEPLOY_DIR/.env.XXXXXX")
  grep -vE "^${var}=" "$STATE_FILE" > "$tmp" || true
  printf '%s=%s\n' "$var" "$value" >> "$tmp"
  chmod 640 "$tmp"
  mv "$tmp" "$STATE_FILE"
}

wait_healthy() {
  local deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    if curl -fsS -o /dev/null --max-time 5 "$health_url"; then
      return 0
    fi
    sleep 3
  done
  return 1
}

log "pulling $new"
docker_config=$(mktemp -d)
trap 'rm -rf "$docker_config"' EXIT
printf '%s' "$token" | DOCKER_CONFIG="$docker_config" docker login "$REGISTRY" -u ci --password-stdin >/dev/null
DOCKER_CONFIG="$docker_config" docker pull --quiet "$new"
rm -rf "$docker_config"

# One-time cutover: the original containers were started with `docker run`,
# so compose can't adopt them. Remove a same-named container compose doesn't own.
if docker inspect "$container" >/dev/null 2>&1; then
  project=$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$container")
  if [[ -z "$project" ]]; then
    log "removing unmanaged container $container (cutover to compose)"
    docker rm -f "$container" >/dev/null
  fi
fi

log "starting $service at ${sha:0:7} (was $current)"
set_image "$new"
"${COMPOSE[@]}" up -d --no-deps "$service"

if ! wait_healthy; then
  log "health check failed at $health_url; last logs:"
  docker logs --tail 50 "$container" 2>&1 || true
  log "rolling back to $current"
  set_image "$current"
  "${COMPOSE[@]}" up -d --no-deps "$service"
  if wait_healthy; then
    log "rollback healthy"
  else
    log "rollback ALSO unhealthy, check the server"
  fi
  exit 1
fi

log "$service healthy at ${sha:0:7}"

# Keep only the running image and the previous one (for manual rollback).
docker images --format '{{.Repository}}:{{.Tag}}' \
  | grep -E "^($REGISTRY/$repo:|$legacy_image\$)" \
  | grep -vxF -e "$new" -e "$current" \
  | xargs -r docker rmi >/dev/null 2>&1 || true
docker image prune -f >/dev/null
log "done"
