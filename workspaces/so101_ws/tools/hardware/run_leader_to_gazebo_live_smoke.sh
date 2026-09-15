#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${REPORT_DIR:-$ROOT_DIR/docs/generated/leader-to-gazebo-live-smoke}"
EPISODE_ID="${EPISODE_ID:-leader_to_gazebo_live_smoke_$(date +%Y%m%d_%H%M%S)}"
REPORT_PATH="$REPORT_DIR/$EPISODE_ID.json"
LOG_PATH="$REPORT_DIR/$EPISODE_ID.log"
TIMEOUT_SEC="${TIMEOUT_SEC:-75}"
LEADER_TOPIC="${LEADER_TOPIC:-/leader/joint_states}"
STATUS_TOPIC="${STATUS_TOPIC:-/leader/gazebo_bridge/status}"

mkdir -p "$REPORT_DIR"

write_report() {
  local status="$1"
  local reason="$2"
  python3 - "$REPORT_PATH" "$status" "$reason" "$LOG_PATH" "$LEADER_TOPIC" "$STATUS_TOPIC" <<'PY'
import json
import sys
import time
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "schema": "leader_to_gazebo_live_smoke.v1",
    "status": sys.argv[2],
    "reason": sys.argv[3],
    "log_path": sys.argv[4],
    "leader_topic": sys.argv[5],
    "status_topic": sys.argv[6],
    "generated_at_wall_sec": round(time.time(), 6),
}
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY
}

set +u
source /opt/ros/humble/setup.bash
if [[ -f "$ROOT_DIR/install/setup.bash" ]]; then
  source "$ROOT_DIR/install/setup.bash"
fi
set -u

if ! timeout 8s ros2 topic echo "$LEADER_TOPIC" --once >/tmp/leader_to_gazebo_live_topic.txt 2>/tmp/leader_to_gazebo_live_topic.err; then
  write_report "blocked" "leader topic $LEADER_TOPIC did not produce a sample within 8 seconds"
  exit 2
fi

set +e
timeout "$TIMEOUT_SEC" ros2 launch so101_bringup leader_to_gazebo.launch.py \
  use_gzclient:=false \
  start_recording_replay:=false \
  leader_joint_states_topic:="$LEADER_TOPIC" \
  status_topic:="$STATUS_TOPIC" \
  controller_load_delay_sec:=8.0 \
  >"$LOG_PATH" 2>&1
launch_status=$?
set -e

if grep -q '"state": "READY"' "$LOG_PATH" && grep -q '"sent_goal_count": [1-9]' "$LOG_PATH"; then
  write_report "passed" "bridge reached READY and sent at least one goal"
  exit 0
fi

if [[ "$launch_status" -eq 124 ]]; then
  write_report "blocked" "launch timed out before READY plus sent goal evidence; inspect log"
  exit 2
fi

write_report "failed" "launch exited with status $launch_status before live smoke evidence"
exit 1
