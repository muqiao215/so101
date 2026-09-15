#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/main_arm_runtime_state_watch_common.sh"

cleanup_stale_watch_artifacts
read_watch_meta
mapfile -t watcher_pids < <(get_watcher_pids)

if [[ ${#watcher_pids[@]} -eq 0 ]]; then
  echo "watcher_state=stopped"
  echo "watcher_pid=none"
  echo "watcher_port=${WATCH_META_PORT:-unknown}"
  echo "watcher_interval_sec=${WATCH_META_INTERVAL_SEC:-unknown}"
  echo "watcher_log=$WATCH_LOG_FILE"
  exit 0
fi

watcher_port="${WATCH_META_PORT:-${SO101_MAIN_ARM_PORT:-unknown}}"
watcher_interval="${WATCH_META_INTERVAL_SEC:-${SO101_MAIN_ARM_REFRESH_INTERVAL_SEC:-unknown}}"

echo "watcher_state=running"
echo "watcher_pid=${watcher_pids[0]}"
echo "watcher_pid_count=${#watcher_pids[@]}"
echo "watcher_port=$watcher_port"
echo "watcher_interval_sec=$watcher_interval"
echo "watcher_log=$WATCH_LOG_FILE"
