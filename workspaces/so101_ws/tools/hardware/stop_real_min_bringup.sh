#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
PID_FILE="$RUNTIME_DIR/so101_real_min.pid"
WATCH_STATUS_HELPER="$ROOT_DIR/tools/hardware/main_arm_runtime_state_watch_status.sh"

echo "Stopping main arm runtime watcher before bringup shutdown..."
bash "$ROOT_DIR/tools/hardware/stop_main_arm_runtime_state_watch.sh" || true
bash "$WATCH_STATUS_HELPER" || true

python3 "$ROOT_DIR/tools/hardware/write_real_hardware_status.py" \
  --root-dir "$ROOT_DIR" \
  --offline \
  --control-interface "已停止" \
  --power-state "未上电" \
  --mode "安全待机" \
  --last-error "无" \
  --lock-execute >/dev/null

if [[ ! -f "$PID_FILE" ]]; then
  echo "No SO101 real min bringup PID file found"
  exit 0
fi

pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -z "$pid" ]]; then
  rm -f "$PID_FILE"
  echo "Removed empty SO101 real min bringup PID file"
  exit 0
fi

if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PID_FILE"
      echo "Stopped SO101 real min bringup"
      bash "$WATCH_STATUS_HELPER" || true
      exit 0
    fi
    sleep 1
  done
  kill -9 "$pid" 2>/dev/null || true
fi

rm -f "$PID_FILE"
echo "Stopped SO101 real min bringup"
bash "$WATCH_STATUS_HELPER" || true
