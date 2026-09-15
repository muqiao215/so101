#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${1:-/dev/ttyUSB0}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/docs/generated/leader-recordings}"
AUTO_START="${AUTO_START:-false}"
LEROBOT_PYTHON="${LEROBOT_PYTHON:-$HOME/.venvs/lerobot/bin/python}"

cd "$ROOT_DIR"
mkdir -p "$OUTPUT_DIR"
set +u
source /opt/ros/humble/setup.bash
source "$ROOT_DIR/install/setup.bash"
set -u

exec ros2 launch so101_bringup leader_recording_session.launch.py \
  port:="$PORT" \
  output_dir:="$OUTPUT_DIR" \
  auto_start:="$AUTO_START" \
  python_executable:="$LEROBOT_PYTHON"
