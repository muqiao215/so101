#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/main_arm_runtime_state_watch_common.sh"

cleanup_stale_watch_artifacts
mapfile -t watcher_pids < <(get_watcher_pids)

if [[ ${#watcher_pids[@]} -eq 0 ]]; then
  rm -f "$WATCH_PID_FILE"
  clear_watch_meta
  echo "no main arm runtime watcher running"
  echo "watch log: $WATCH_LOG_FILE"
  exit 0
fi

echo "stopping main arm runtime watcher pid(s): ${watcher_pids[*]}"
kill "${watcher_pids[@]}" 2>/dev/null || true

remaining=("${watcher_pids[@]}")
for _ in $(seq 1 20); do
  next_remaining=()
  for pid in "${remaining[@]}"; do
    if is_pid_alive "$pid" && pid_matches_watch_loop "$pid"; then
      next_remaining+=("$pid")
    fi
  done
  if [[ ${#next_remaining[@]} -eq 0 ]]; then
    rm -f "$WATCH_PID_FILE"
    clear_watch_meta
    echo "stopped main arm runtime watcher"
    echo "watch log: $WATCH_LOG_FILE"
    exit 0
  fi
  remaining=("${next_remaining[@]}")
  sleep 1
done

kill -9 "${remaining[@]}" 2>/dev/null || true
rm -f "$WATCH_PID_FILE"
clear_watch_meta
echo "stopped main arm runtime watcher after force kill: ${remaining[*]}"
echo "watch log: $WATCH_LOG_FILE"
