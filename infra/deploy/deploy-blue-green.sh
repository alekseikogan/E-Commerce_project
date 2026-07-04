#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.zdd.yml)
NGINX_DIR="$ROOT/nginx"
ACTIVE="$NGINX_DIR/active.conf"
STATE_FILE="$ROOT/.zdd-active-color"

if [[ -f "$STATE_FILE" ]]; then
  CURRENT="$(cat "$STATE_FILE")"
else
  CURRENT="blue"
fi

if [[ "$CURRENT" == "blue" ]]; then
  TARGET="green"
  TARGET_SERVICE="web_green"
  OLD_SERVICE="web_blue"
  TARGET_CONF="$NGINX_DIR/green.conf"
  TARGET_CONTAINER="mele_shop_web_green"
  PROFILE_ARGS=(--profile green)
else
  TARGET="blue"
  TARGET_SERVICE="web_blue"
  OLD_SERVICE="web_green"
  TARGET_CONF="$NGINX_DIR/blue.conf"
  TARGET_CONTAINER="mele_shop_web_blue"
  PROFILE_ARGS=()
fi

echo "==> Current live: $CURRENT"
echo "==> Deploying to: $TARGET"

echo "==> Build $TARGET_SERVICE"
"${COMPOSE[@]}" "${PROFILE_ARGS[@]}" build "$TARGET_SERVICE"

echo "==> Start $TARGET_SERVICE"
"${COMPOSE[@]}" "${PROFILE_ARGS[@]}" up -d "$TARGET_SERVICE"

echo "==> Wait for healthy"
for i in $(seq 1 30); do
  if docker exec "$TARGET_CONTAINER" curl -sf "http://localhost:8000/health/" 2>/dev/null | grep -q ok; then
    echo "    health endpoint ok"
    break
  fi
  if [[ "$i" -eq 30 ]]; then
    echo "ERROR: $TARGET_SERVICE not healthy"
    exit 1
  fi
  sleep 2
done

echo "==> Migrate (once, on target)"
"${COMPOSE[@]}" "${PROFILE_ARGS[@]}" run --rm "$TARGET_SERVICE" python manage.py migrate --noinput

"${COMPOSE[@]}" "${PROFILE_ARGS[@]}" run --rm "$TARGET_SERVICE" \
  python manage.py collectstatic --noinput

echo "==> Switch nginx to $TARGET"
cp "$TARGET_CONF" "$ACTIVE"
docker exec mele_shop_nginx nginx -s reload

echo "$TARGET" > "$STATE_FILE"
echo "==> Live is now: $TARGET"
echo "==> Old $OLD_SERVICE still running (rollback: cp nginx/${CURRENT}.conf nginx/active.conf && docker exec mele_shop_nginx nginx -s reload && echo $CURRENT > .zdd-active-color)"
echo "==> When OK, stop old: docker compose -f docker-compose.yml -f docker-compose.zdd.yml stop $OLD_SERVICE"
echo "==> Check: curl http://127.0.0.1:8088/health/"