#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
PID_FILE="$RUNTIME_DIR/so101_real_min.pid"
LOG_FILE="$RUNTIME_DIR/so101_real_min.log"
ROS_LOG_DIR="$RUNTIME_DIR/ros_logs_real_min"
ENABLE_ROSBRIDGE="${ENABLE_ROSBRIDGE:-1}"
AUTO_REFRESH_MAIN_ARM_STATE="${AUTO_REFRESH_MAIN_ARM_STATE:-1}"
DEFAULT_COMMAND_EXECUTION_ENABLED="${DEFAULT_COMMAND_EXECUTION_ENABLED:-1}"
DEFAULT_DETECTION_TRIGGER_ENABLED="${DEFAULT_DETECTION_TRIGGER_ENABLED:-0}"
SO101_MAIN_ARM_ALLOW_EXECUTE="${SO101_MAIN_ARM_ALLOW_EXECUTE:-1}"
SO101_MAIN_ARM_GATE_ENABLED="${SO101_MAIN_ARM_GATE_ENABLED:-1}"
if [[ -z "${SO101_MAIN_ARM_GATE_REASON_CODE:-}" ]]; then
  if [[ "$SO101_MAIN_ARM_GATE_ENABLED" == "1" ]]; then
    SO101_MAIN_ARM_GATE_REASON_CODE="READY_FOR_MIN_MOTION"
  else
    SO101_MAIN_ARM_GATE_REASON_CODE="HWS_002_PENDING"
  fi
fi
if [[ -z "${SO101_MAIN_ARM_GATE_REASON:-}" ]]; then
  if [[ "$SO101_MAIN_ARM_GATE_ENABLED" == "1" ]]; then
    SO101_MAIN_ARM_GATE_REASON="已确认现场安全，允许前端直接下发最小动作验证工单"
  else
    SO101_MAIN_ARM_GATE_REASON="主臂已接入，执行放行仍由系统 gate 决定"
  fi
fi
WATCH_STATUS_HELPER="$ROOT_DIR/tools/hardware/main_arm_runtime_state_watch_status.sh"
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/main_arm_runtime_state_watch_common.sh"

mkdir -p "$RUNTIME_DIR"
mkdir -p "$ROS_LOG_DIR"

log_note() {
  printf '[real-min-bringup] %s\n' "$*"
}

log_warn() {
  printf '[real-min-bringup] %s\n' "$*" >&2
}

resolve_refresh_port() {
  if resolved_port="$(resolve_main_arm_port)"; then
    echo "$resolved_port"
    return 0
  fi
  return 1
}

reconcile_main_arm_runtime_state() {
  if [[ "$AUTO_REFRESH_MAIN_ARM_STATE" != "1" ]]; then
    log_note "Skipping main arm runtime refresh/watch because AUTO_REFRESH_MAIN_ARM_STATE=$AUTO_REFRESH_MAIN_ARM_STATE"
    return 0
  fi

  local refresh_port=""
  if refresh_port="$(resolve_refresh_port)"; then
    log_note "Using main arm port $refresh_port for refresh/watch reconciliation"
  else
    log_warn "No /dev/ttyUSB* or /dev/ttyACM* detected before refresh; refresh script will re-check"
  fi

  log_note "Running main arm runtime refresh..."
  if SO101_MAIN_ARM_PORT="${refresh_port:-}" \
    SO101_MAIN_ARM_ALLOW_EXECUTE="$SO101_MAIN_ARM_ALLOW_EXECUTE" \
    SO101_MAIN_ARM_GATE_ENABLED="$SO101_MAIN_ARM_GATE_ENABLED" \
    SO101_MAIN_ARM_GATE_REASON_CODE="$SO101_MAIN_ARM_GATE_REASON_CODE" \
    SO101_MAIN_ARM_GATE_REASON="$SO101_MAIN_ARM_GATE_REASON" \
    bash "$ROOT_DIR/tools/hardware/refresh_main_arm_runtime_state.sh"; then
    log_note "Main arm runtime state refreshed after bringup"
    log_note "Ensuring a single main arm runtime watcher is running..."
    SO101_MAIN_ARM_PORT="${refresh_port:-}" \
      SO101_MAIN_ARM_ALLOW_EXECUTE="$SO101_MAIN_ARM_ALLOW_EXECUTE" \
      SO101_MAIN_ARM_GATE_ENABLED="$SO101_MAIN_ARM_GATE_ENABLED" \
      SO101_MAIN_ARM_GATE_REASON_CODE="$SO101_MAIN_ARM_GATE_REASON_CODE" \
      SO101_MAIN_ARM_GATE_REASON="$SO101_MAIN_ARM_GATE_REASON" \
      bash "$ROOT_DIR/tools/hardware/watch_main_arm_runtime_state.sh"
    bash "$WATCH_STATUS_HELPER"
  else
    log_warn "Main arm runtime state refresh skipped or failed; watcher not started"
    return 1
  fi
}

if [[ -f "$PID_FILE" ]]; then
  existing_pid="$(cat "$PID_FILE")"
  if kill -0 "$existing_pid" 2>/dev/null; then
    log_note "SO101 real min bringup already running with PID $existing_pid"
    reconcile_main_arm_runtime_state || true
    exit 0
  fi
  log_note "Removing stale bringup PID file for PID $existing_pid"
  rm -f "$PID_FILE"
fi

python3 "$ROOT_DIR/tools/hardware/write_real_hardware_status.py" \
  --root-dir "$ROOT_DIR" \
  --offline \
  --control-interface "软件预检 / 待接硬件目录" \
  --power-state "未上电" \
  --mode "保护待机" \
  --last-error "无" \
  --lock-execute >/dev/null

set +u
source /opt/ros/humble/setup.bash
if [[ -f "$ROOT_DIR/install/setup.bash" ]]; then
  source "$ROOT_DIR/install/setup.bash"
fi
set -u

export ROS_LOG_DIR
nohup ros2 launch so101_bringup real_bringup.launch.py \
  enable_rosbridge:="$([[ "$ENABLE_ROSBRIDGE" == "1" ]] && echo true || echo false)" \
  use_mock_yolo:=false \
  detection_trigger_enabled:="$([[ "$DEFAULT_DETECTION_TRIGGER_ENABLED" == "1" ]] && echo true || echo false)" \
  command_execution_enabled:="$([[ "$DEFAULT_COMMAND_EXECUTION_ENABLED" == "1" ]] && echo true || echo false)" \
  >"$LOG_FILE" 2>&1 &

echo "$!" >"$PID_FILE"
sleep 2

if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  log_warn "SO101 real min bringup exited before readiness check"
  rm -f "$PID_FILE"
  tail -n 80 "$LOG_FILE" >&2 || true
  exit 1
fi

log_note "Started SO101 real min bringup with PID $(cat "$PID_FILE")"
log_note "Log: $LOG_FILE"
log_note "rosbridge enabled: $ENABLE_ROSBRIDGE"
log_note "Default runtime mode: command_execution_enabled=$DEFAULT_COMMAND_EXECUTION_ENABLED detection_trigger_enabled=$DEFAULT_DETECTION_TRIGGER_ENABLED"
log_note "Main arm runtime gate defaults: allowExecute=$SO101_MAIN_ARM_ALLOW_EXECUTE gateEnabled=$SO101_MAIN_ARM_GATE_ENABLED"
reconcile_main_arm_runtime_state || true

if [[ "$ENABLE_ROSBRIDGE" != "1" ]]; then
  log_note "Skipping rosbridge port wait in CLI-first safe mode"
  exit 0
fi

for _ in $(seq 1 30); do
  if python3 - <<'PY'
import socket
sock = socket.socket()
sock.settimeout(0.2)
try:
    sock.connect(("127.0.0.1", 9090))
except OSError:
    raise SystemExit(1)
finally:
    sock.close()
PY
  then
    log_note "rosbridge ready on port 9090"
    exit 0
  fi
  sleep 1
done

log_warn "Timed out waiting for rosbridge on port 9090"
tail -n 80 "$LOG_FILE" >&2 || true
exit 1
