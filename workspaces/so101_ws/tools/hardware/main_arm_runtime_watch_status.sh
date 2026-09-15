#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/main_arm_runtime_state_watch_common.sh"

STATUS_FILE="$RUNTIME_DIR/real_hardware_status.json"
INTERVAL_SEC="${SO101_MAIN_ARM_REFRESH_INTERVAL_SEC:-5}"
HEARTBEAT_WINDOW_SEC="${SO101_MAIN_ARM_HEARTBEAT_WINDOW_SEC:-$((INTERVAL_SEC * 3))}"

watch_pid=""
watch_pid_visible="false"
watch_heartbeat_fresh="false"

cleanup_stale_watch_artifacts

if [[ -f "$WATCH_PID_FILE" ]]; then
  watch_pid="$(cat "$WATCH_PID_FILE" 2>/dev/null || true)"
  if is_pid_alive "$watch_pid" && pid_matches_watch_loop "$watch_pid"; then
    watch_pid_visible="true"
  fi
fi

control_interface="待接入"
updated_at=""
if [[ -f "$STATUS_FILE" ]]; then
  mapfile -t status_lines < <(python3 - <<'PY' "$STATUS_FILE"
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("controlInterface", "待接入"))
print(payload.get("updatedAt", ""))
PY
)
  control_interface="${status_lines[0]:-待接入}"
  updated_at="${status_lines[1]:-}"
fi

last_refresh_ok_at=""
if [[ -f "$WATCH_LOG_FILE" ]]; then
  last_refresh_ok_at="$(
    python3 - <<'PY' "$WATCH_LOG_FILE" "$HEARTBEAT_WINDOW_SEC"
import re
import sys
from datetime import datetime
from pathlib import Path

log_path = Path(sys.argv[1])
heartbeat_window_sec = int(sys.argv[2])
pattern = re.compile(r"\[watch-main-arm\] refresh ok ts=(.+?) pid=")
last_ts = ""

for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
    match = pattern.search(line)
    if match:
        last_ts = match.group(1).strip()

if not last_ts:
    sys.exit(0)

timestamp = datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S %z")
age_sec = (datetime.now(timestamp.tzinfo) - timestamp).total_seconds()
if age_sec <= heartbeat_window_sec:
    print(last_ts)
PY
  )"
fi

if [[ -n "$last_refresh_ok_at" ]]; then
  watch_heartbeat_fresh="true"
fi

watch_running="false"
watch_health_source="none"
if [[ "$watch_pid_visible" == "true" ]]; then
  watch_running="true"
  watch_health_source="pid"
elif [[ "$watch_heartbeat_fresh" == "true" ]]; then
  watch_running="true"
  watch_health_source="heartbeat"
fi

echo "watcherPid: ${watch_pid:-none}"
echo "watcherPidVisible: $watch_pid_visible"
echo "watcherHeartbeatFresh: $watch_heartbeat_fresh"
echo "watcherRunning: $watch_running"
echo "watcherHealthSource: $watch_health_source"
echo "refreshIntervalSec: $INTERVAL_SEC"
echo "controlInterface: $control_interface"
echo "statusUpdatedAt: ${updated_at:-unknown}"
if [[ -n "$last_refresh_ok_at" ]]; then
  echo "lastRefreshOkAt: $last_refresh_ok_at"
fi
echo "watchLog: $WATCH_LOG_FILE"

if [[ -f "$WATCH_LOG_FILE" ]]; then
  echo "--- watch log tail ---"
  tail -n 10 "$WATCH_LOG_FILE"
fi
