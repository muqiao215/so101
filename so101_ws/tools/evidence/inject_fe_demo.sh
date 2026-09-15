#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8080}"
STAMP="${1:-$(date +%Y%m%d%H%M%S)}"
ORDER_ID="order-fe-$STAMP"
ACTION_TEMPLATE="${ACTION_TEMPLATE:-pick_place_red}"

usage() {
  cat <<EOF
Usage:
  $(basename "$0") [stamp]

Environment:
  API_BASE=http://127.0.0.1:8080
  ACTION_TEMPLATE=pick_place_red

What it does:
  1. create order
  2. dispatch order
  3. inject one task-status event
  4. inject red and blue detection events
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

post_json() {
  local url="$1"
  local payload="$2"
  curl -fsS -X POST "$url" \
    -H 'Content-Type: application/json' \
    -d "$payload"
}

extract_json_field() {
  local field="$1"
  python3 -c 'import json,sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$field"
}

echo "[1/4] create order: $ORDER_ID"
CREATE_RESP="$(post_json "$API_BASE/api/orders" "{\"orderId\":\"$ORDER_ID\",\"actionTemplateId\":\"$ACTION_TEMPLATE\"}")"
printf '%s\n' "$CREATE_RESP"

echo "[2/4] dispatch order"
DISPATCH_RESP="$(post_json "$API_BASE/api/orders/$ORDER_ID/dispatch" '{}')"
printf '%s\n' "$DISPATCH_RESP"
REQUEST_ID="$(printf '%s' "$DISPATCH_RESP" | extract_json_field requestId)"

if [[ -z "$REQUEST_ID" ]]; then
  echo "dispatch response missing requestId" >&2
  exit 1
fi

echo "[3/4] inject status for requestId=$REQUEST_ID"
post_json "$API_BASE/api/ros/status" \
  "{\"requestId\":\"$REQUEST_ID\",\"state\":\"执行中\",\"code\":\"STEP\",\"message\":\"4/8 -> close_gripper\",\"ts\":1772188890001}"
printf '\n'

echo "[4/4] inject red/blue detections"
post_json "$API_BASE/api/ros/detections" \
  '{"count":1,"detections":[{"category":"red","confidence":0.95,"bbox":[120,160,220,320]}]}'
printf '\n'
post_json "$API_BASE/api/ros/detections" \
  '{"count":1,"detections":[{"category":"blue","confidence":0.93,"bbox":[300,150,420,310]}]}'
printf '\n'

cat <<EOF
done
order_id:   $ORDER_ID
request_id: $REQUEST_ID
EOF
