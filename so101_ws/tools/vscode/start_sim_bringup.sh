#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
PID_FILE="$RUNTIME_DIR/so101_sim.pid"
LOG_FILE="$RUNTIME_DIR/so101_sim.log"

mkdir -p "$RUNTIME_DIR"

if [[ -f "$PID_FILE" ]]; then
  existing_pid="$(cat "$PID_FILE")"
  if kill -0 "$existing_pid" 2>/dev/null; then
    echo "SO101 sim bringup already running with PID $existing_pid"
  else
    rm -f "$PID_FILE"
  fi
fi

if [[ ! -f "$PID_FILE" ]]; then
  set +u
  source /opt/ros/humble/setup.bash
  if [[ -f "$ROOT_DIR/install/setup.bash" ]]; then
    source "$ROOT_DIR/install/setup.bash"
  fi
  set -u

  nohup ros2 launch so101_bringup sim_bringup.launch.py \
    use_mock_yolo:=false \
    enable_rosbridge:=true \
    >"$LOG_FILE" 2>&1 &
  echo "$!" > "$PID_FILE"
  echo "Started SO101 sim bringup with PID $(cat "$PID_FILE")"
fi

for _ in $(seq 1 60); do
  if ss -ltn | grep -qE '127\.0\.0\.1:9090|0\.0\.0\.0:9090|\[::\]:9090'; then
    echo "rosbridge ready on port 9090"
    exit 0
  fi
  sleep 2
done

echo "Timed out waiting for rosbridge on port 9090" >&2
if [[ -f "$LOG_FILE" ]]; then
  tail -n 80 "$LOG_FILE" >&2 || true
fi
exit 1
