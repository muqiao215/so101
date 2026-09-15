#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INPUT_PATH="${1:-}"
RATE_SCALE="${RATE_SCALE:-1.0}"
LOOP="${LOOP:-false}"
STAMP_MODE="${STAMP_MODE:-now}"

if [[ -z "$INPUT_PATH" ]]; then
  latest_path="$(ls -1t "$ROOT_DIR"/docs/generated/leader-recordings/leader-recording-*.jsonl 2>/dev/null | head -n 1 || true)"
  if [[ -z "$latest_path" ]]; then
    echo "No leader recording found under $ROOT_DIR/docs/generated/leader-recordings" >&2
    exit 1
  fi
  INPUT_PATH="$latest_path"
fi

cd "$ROOT_DIR"
set +u
source /opt/ros/humble/setup.bash
source "$ROOT_DIR/install/setup.bash"
set -u

exec ros2 launch so101_bringup leader_rviz_replay.launch.py \
  input_path:="$INPUT_PATH" \
  rate_scale:="$RATE_SCALE" \
  loop:="$LOOP" \
  stamp_mode:="$STAMP_MODE"
