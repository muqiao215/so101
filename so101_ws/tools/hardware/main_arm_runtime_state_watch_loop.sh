#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/main_arm_runtime_state_watch_common.sh"

ensure_runtime_dir

INTERVAL_SEC="${SO101_MAIN_ARM_REFRESH_INTERVAL_SEC:-5}"
WATCH_PORT="${SO101_MAIN_ARM_PORT:-}"

if [[ -z "$WATCH_PORT" ]]; then
  if ! WATCH_PORT="$(resolve_main_arm_port)"; then
    printf '[watch-main-arm] loop abort ts=%s reason=no-serial-port-detected\n' "$(timestamp_now)" >>"$WATCH_LOG_FILE"
    exit 2
  fi
fi

printf '[watch-main-arm] loop online ts=%s pid=%s interval=%ss port=%s\n' \
  "$(timestamp_now)" "$$" "$INTERVAL_SEC" "$WATCH_PORT" >>"$WATCH_LOG_FILE"

while true; do
  printf '[watch-main-arm] refresh begin ts=%s pid=%s port=%s\n' \
    "$(timestamp_now)" "$$" "$WATCH_PORT" >>"$WATCH_LOG_FILE"

  if SO101_MAIN_ARM_PORT="$WATCH_PORT" bash "$ROOT_DIR/tools/hardware/refresh_main_arm_runtime_state.sh" >>"$WATCH_LOG_FILE" 2>&1; then
    printf '[watch-main-arm] refresh ok ts=%s pid=%s port=%s\n' \
      "$(timestamp_now)" "$$" "$WATCH_PORT" >>"$WATCH_LOG_FILE"
  else
    rc=$?
    printf '[watch-main-arm] refresh failed ts=%s pid=%s port=%s rc=%s\n' \
      "$(timestamp_now)" "$$" "$WATCH_PORT" "$rc" >>"$WATCH_LOG_FILE"
  fi

  sleep "$INTERVAL_SEC"
done
