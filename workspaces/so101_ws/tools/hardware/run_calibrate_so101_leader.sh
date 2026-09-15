#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${1:-/dev/ttyUSB0}"
LEROBOT_PYTHON="${LEROBOT_PYTHON:-$HOME/.venvs/lerobot/bin/python}"
LEROBOT_SITE="${LEROBOT_SITE:-$HOME/.venvs/lerobot/lib/python3.10/site-packages}"
USER_SITE="${USER_SITE:-$HOME/.local/lib/python3.10/site-packages}"
ROS_PYTHONPATH="/opt/ros/humble/lib/python3.10/site-packages:/opt/ros/humble/local/lib/python3.10/dist-packages"

export PYTHONPATH="$LEROBOT_SITE:$USER_SITE:$ROS_PYTHONPATH"

exec "$LEROBOT_PYTHON" "$ROOT_DIR/tools/hardware/calibrate_so101_leader.py" --port "$PORT"
