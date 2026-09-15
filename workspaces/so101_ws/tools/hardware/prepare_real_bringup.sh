#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
LOG_FILE="$RUNTIME_DIR/real_bringup_preflight.log"
BUILD_LOG="$RUNTIME_DIR/real_bringup_build.log"
ROS_LOG_DIR="$RUNTIME_DIR/ros_logs_real_prepare"

mkdir -p "$RUNTIME_DIR"
mkdir -p "$ROS_LOG_DIR"

python3 "$ROOT_DIR/tools/hardware/write_real_hardware_status.py" \
  --root-dir "$ROOT_DIR" \
  --offline \
  --control-interface "软件预检" \
  --power-state "未上电" \
  --mode "软件预检完成" \
  --last-error "无" \
  --lock-execute >/dev/null

set +u
source /opt/ros/humble/setup.bash
set -u

colcon build --packages-select so101_bringup >"$BUILD_LOG" 2>&1

set +u
source "$ROOT_DIR/install/setup.bash"
set -u

export ROS_LOG_DIR
ros2 launch so101_bringup real_bringup.launch.py --show-args >"$LOG_FILE"

echo "Prepared safe real bringup software baseline."
echo "Build log: $BUILD_LOG"
echo "Launch args snapshot: $LOG_FILE"
echo "Status file: $RUNTIME_DIR/real_hardware_status.json"
