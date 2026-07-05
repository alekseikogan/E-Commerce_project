#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.zdd.yml)
STATE_FILE="$ROOT/.zdd-active-color"
NGINX_DIR="$ROOT/nginx"

if [[ -f "$STATE_FILE" ]]; then
  COLOR="$(tr -d '[:space:]' < "$STATE_FILE")"
else
  COLOR="blue"
fi

if [[ "$COLOR" == "green" ]]; then
  WEB_SERVICE="web_green"
  PROFILE_ARGS=(--profile green)
else
  COLOR="blue"
  WEB_SERVICE="web_blue"
  PROFILE_ARGS=()
fi

echo "==> Active color: $COLOR ($WEB_SERVICE)"
cp "$NGINX_DIR/$COLOR.conf" "$NGINX_DIR/active.conf"

docker compose stop web 2>/dev/null || true

"${COMPOSE[@]}" "${PROFILE_ARGS[@]}" up -d --build \
  db db-replica rabbitmq \
  kafka kafka-init kafka-ui \
  kafka-rating-consumer kafka-load-consumer kafka-analytics-consumer \
  kafka-load-publisher \
  clickhouse clickhouse-init grafana \
  celery flower stripe-cli \
  "$WEB_SERVICE" nginx

echo "==> Site:    http://localhost:8088/"
echo "==> Health:  curl http://localhost:8088/health/"
