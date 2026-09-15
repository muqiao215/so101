#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAMP="${1:-$(date +%Y%m%d%H%M%S)}"
API_BASE="${API_BASE:-http://127.0.0.1:8080}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:5173}"
LOG_FILE="$ROOT_DIR/docs/evidence/fe-inject-$STAMP.log"

usage() {
  cat <<EOF
Usage:
  $(basename "$0") [stamp]

Environment:
  API_BASE=$API_BASE
  FRONTEND_URL=$FRONTEND_URL

What it does:
  1. checks backend and frontend reachability
  2. calls tools/evidence/inject_fe_demo.sh
  3. stores the console output in docs/evidence/fe-inject-<stamp>.log
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

check_http() {
  local url="$1"
  local name="$2"
  if ! curl -fsS --max-time 5 "$url" >/dev/null; then
    echo "$name not reachable: $url" >&2
    exit 1
  fi
}

check_http "$API_BASE/api/ros/health" "backend"
check_http "$FRONTEND_URL" "frontend"

echo "writing demo log to $LOG_FILE"
bash "$ROOT_DIR/tools/evidence/inject_fe_demo.sh" "$STAMP" | tee "$LOG_FILE"

cat <<EOF

demo sequence complete
log_file: $LOG_FILE
suggested evidence:
  docs/evidence/fe-002-order-flow-$STAMP.png
  docs/evidence/fe-003-detection-stream-$STAMP.png
  docs/evidence/e2e-demo-$STAMP.webm
EOF
