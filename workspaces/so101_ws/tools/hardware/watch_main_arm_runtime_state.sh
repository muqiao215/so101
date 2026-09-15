#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/main_arm_runtime_state_watch_common.sh"

INTERVAL_SEC="${SO101_MAIN_ARM_REFRESH_INTERVAL_SEC:-5}"
cleanup_stale_watch_artifacts

WATCH_PORT="${SO101_MAIN_ARM_PORT:-}"
if [[ -z "$WATCH_PORT" ]]; then
  if ! WATCH_PORT="$(resolve_main_arm_port)"; then
    echo "main arm runtime watcher not started: no /dev/ttyUSB* or /dev/ttyACM* detected" >&2
    exit 2
  fi
fi

mapfile -t watcher_pids < <(get_watcher_pids)
if [[ ${#watcher_pids[@]} -gt 1 ]]; then
  echo "main arm runtime watcher duplicate set detected (${watcher_pids[*]}); restarting cleanly"
  bash "$ROOT_DIR/tools/hardware/stop_main_arm_runtime_state_watch.sh"
  mapfile -t watcher_pids < <(get_watcher_pids)
fi

if [[ ${#watcher_pids[@]} -eq 1 ]]; then
  read_watch_meta
  if [[ -z "$WATCH_META_PORT" || "$WATCH_META_PORT" != "$WATCH_PORT" ]]; then
    echo "main arm runtime watcher port changed or metadata missing; restarting for port $WATCH_PORT"
    bash "$ROOT_DIR/tools/hardware/stop_main_arm_runtime_state_watch.sh"
    mapfile -t watcher_pids < <(get_watcher_pids)
  fi
fi

if [[ ${#watcher_pids[@]} -eq 1 ]]; then
  echo "${watcher_pids[0]}" >"$WATCH_PID_FILE"
  write_watch_meta "${watcher_pids[0]}" "$WATCH_PORT" "$INTERVAL_SEC"
  echo "main arm runtime watcher already running with PID ${watcher_pids[0]}"
  echo "watch port: $WATCH_PORT"
  echo "watch interval: ${INTERVAL_SEC}s"
  echo "watch log: $WATCH_LOG_FILE"
  printf '[watch-main-arm] reuse ts=%s pid=%s port=%s interval=%ss\n' \
    "$(timestamp_now)" "${watcher_pids[0]}" "$WATCH_PORT" "$INTERVAL_SEC" >>"$WATCH_LOG_FILE"
  exit 0
fi

ensure_runtime_dir
printf '[watch-main-arm] start requested ts=%s interval=%ss port=%s\n' \
  "$(timestamp_now)" "$INTERVAL_SEC" "$WATCH_PORT" >>"$WATCH_LOG_FILE"

# Launch the loop in a fresh session so it survives the parent shell/tool process
# exiting. This matters when the watcher is started from one-shot command runners.
if command -v setsid >/dev/null 2>&1; then
  nohup env SO101_MAIN_ARM_PORT="$WATCH_PORT" SO101_MAIN_ARM_REFRESH_INTERVAL_SEC="$INTERVAL_SEC" \
    setsid bash "$WATCH_LOOP_SCRIPT" </dev/null >/dev/null 2>&1 &
else
  nohup env SO101_MAIN_ARM_PORT="$WATCH_PORT" SO101_MAIN_ARM_REFRESH_INTERVAL_SEC="$INTERVAL_SEC" \
    bash "$WATCH_LOOP_SCRIPT" </dev/null >/dev/null 2>&1 &
fi
watch_pid="$!"
echo "$watch_pid" >"$WATCH_PID_FILE"
write_watch_meta "$watch_pid" "$WATCH_PORT" "$INTERVAL_SEC"
sleep 1

if ! (is_pid_alive "$watch_pid" && pid_matches_watch_loop "$watch_pid"); then
  rm -f "$WATCH_PID_FILE"
  clear_watch_meta
  echo "main arm runtime watcher exited immediately; see $WATCH_LOG_FILE" >&2
  tail -n 40 "$WATCH_LOG_FILE" >&2 || true
  exit 1
fi

echo "started main arm runtime watcher with PID $watch_pid"
echo "watch port: $WATCH_PORT"
echo "watch interval: ${INTERVAL_SEC}s"
echo "watch log: $WATCH_LOG_FILE"
