#!/usr/bin/env bash
# scripts/monitor-deploy.sh
# Monitors Coolify deployment for is-ai-good-yet (App ID 2) on Hetzner VPS via Tailscale.
# Usage: ./scripts/monitor-deploy.sh [COMMIT_SHA]

set -euo pipefail

HETZNER_HOST="root@100.88.200.83"
APP_ID="2"
MAX_QUEUE_WAIT=120   # Seconds to wait for deployment row to appear
MAX_BUILD_WAIT=480   # Seconds to wait for build to finish
POLL_INTERVAL=5

TARGET_SHA="${1:-}"
if [ -z "$TARGET_SHA" ]; then
  TARGET_SHA=$(git rev-parse HEAD)
fi
SHORT_SHA="${TARGET_SHA:0:7}"
echo "==> Monitoring Coolify deployment for commit: $SHORT_SHA ($TARGET_SHA)"

echo "==> Polling Coolify DB for deployment queue entry..."
DEPLOY_ID=""
STATUS=""
ELAPSED=0

while [ $ELAPSED -lt $MAX_QUEUE_WAIT ]; do
  ROW=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$HETZNER_HOST" \
    "docker exec coolify-db psql -U coolify -d coolify -tAc \"SELECT id, status FROM application_deployment_queues WHERE application_id = '$APP_ID' AND commit LIKE '${SHORT_SHA}%' ORDER BY id DESC LIMIT 1;\"" 2>/dev/null || true)

  if [ -n "$ROW" ]; then
    DEPLOY_ID=$(echo "$ROW" | cut -d'|' -f1)
    STATUS=$(echo "$ROW" | cut -d'|' -f2)
    echo "==> Found deployment row #$DEPLOY_ID with initial status: $STATUS"
    break
  fi

  sleep $POLL_INTERVAL
  ELAPSED=$((ELAPSED + POLL_INTERVAL))
  echo "    Waiting for webhook/queue... (${ELAPSED}s / ${MAX_QUEUE_WAIT}s)"
done

if [ -z "$DEPLOY_ID" ]; then
  echo "ERROR: No deployment queue entry found for commit $SHORT_SHA after ${MAX_QUEUE_WAIT}s."
  echo "Check if GitHub webhook fired or manually trigger deploy via Coolify."
  exit 1
fi

BUILD_ELAPSED=0
while [ $BUILD_ELAPSED -lt $MAX_BUILD_WAIT ]; do
  STATUS=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$HETZNER_HOST" \
    "docker exec coolify-db psql -U coolify -d coolify -tAc \"SELECT status FROM application_deployment_queues WHERE id = '$DEPLOY_ID';\"" 2>/dev/null || true)

  echo "    [+$BUILD_ELAPSED s] Deployment #$DEPLOY_ID status: $STATUS"

  if [ "$STATUS" = "finished" ]; then
    echo "==> Deployment #$DEPLOY_ID finished successfully!"
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "ERROR: Deployment #$DEPLOY_ID reported FAILED!"
    echo "==> Fetching build log tail from Coolify DB:"
    ssh -o BatchMode=yes "$HETZNER_HOST" \
      "docker exec coolify-db psql -U coolify -d coolify -tAc \"SELECT logs FROM application_deployment_queues WHERE id = '$DEPLOY_ID';\"" | tail -n 25
    exit 1
  fi

  sleep $POLL_INTERVAL
  BUILD_ELAPSED=$((BUILD_ELAPSED + POLL_INTERVAL))
done

if [ "$STATUS" != "finished" ]; then
  echo "ERROR: Deployment #$DEPLOY_ID timed out after ${MAX_BUILD_WAIT}s (status: $STATUS)."
  exit 1
fi

echo "==> Verifying live container state on Hetzner..."
CONTAINER_INFO=$(ssh -o BatchMode=yes "$HETZNER_HOST" \
  "docker ps --filter 'name=is-ai-good-yet' --format '{{.Names}} | {{.Image}} | {{.Status}}'")
echo "    Container: $CONTAINER_INFO"

echo "==> Testing live HTTP response (https://is-ai-good-yet.com)..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://is-ai-good-yet.com)
echo "    HTTP Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" = "200" ]; then
  echo "==> SUCCESS: Site is live and healthy at https://is-ai-good-yet.com"
else
  echo "WARNING: Expected HTTP 200, got $HTTP_STATUS. Please verify manually."
fi
