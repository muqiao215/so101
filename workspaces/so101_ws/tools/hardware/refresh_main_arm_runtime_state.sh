#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
STATUS_TMP="$RUNTIME_DIR/main_arm_runtime_status.tmp.json"
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/main_arm_runtime_state_watch_common.sh"

SO101_MAIN_ARM_PORT="${SO101_MAIN_ARM_PORT:-}"
SO101_MAIN_ARM_POWER_STATE="${SO101_MAIN_ARM_POWER_STATE:-已上电}"
SO101_MAIN_ARM_ALLOW_EXECUTE="${SO101_MAIN_ARM_ALLOW_EXECUTE:-1}"
SO101_MAIN_ARM_GATE_ENABLED="${SO101_MAIN_ARM_GATE_ENABLED:-1}"
SO101_MAIN_ARM_MODE="${SO101_MAIN_ARM_MODE:-最小动作验证}"
if [[ -z "${SO101_MAIN_ARM_GATE_REASON_CODE:-}" ]]; then
  if [[ "$SO101_MAIN_ARM_GATE_ENABLED" == "1" ]]; then
    SO101_MAIN_ARM_GATE_REASON_CODE="READY_FOR_MIN_MOTION"
  else
    SO101_MAIN_ARM_GATE_REASON_CODE="HWS_002_PENDING"
  fi
fi
if [[ -z "${SO101_MAIN_ARM_GATE_REASON:-}" ]]; then
  if [[ "$SO101_MAIN_ARM_GATE_ENABLED" == "1" ]]; then
    SO101_MAIN_ARM_GATE_REASON="已确认现场安全，允许最小动作验证"
  else
    SO101_MAIN_ARM_GATE_REASON="主臂已接入，执行放行仍由系统 gate 决定"
  fi
fi
SO101_MAIN_ARM_GATE_SOURCE="${SO101_MAIN_ARM_GATE_SOURCE:-so101-main-arm-serial}"
SO101_MAIN_ARM_CALIBRATION_PROFILE="${SO101_MAIN_ARM_CALIBRATION_PROFILE:-}"
DEFAULT_LOCAL_CALIBRATION_PROFILE="$ROOT_DIR/tools/hardware/real_hardware_calibration.local.json"

if [[ -z "$SO101_MAIN_ARM_PORT" ]]; then
  if SO101_MAIN_ARM_PORT="$(resolve_main_arm_port)"; then
    export SO101_MAIN_ARM_PORT
  else
    echo "[refresh-main-arm] ts=$(timestamp_now) reason=no /dev/ttyUSB* or /dev/ttyACM* detected" >&2
    exit 2
  fi
fi

mkdir -p "$RUNTIME_DIR"
trap 'rm -f "$STATUS_TMP"' EXIT

echo "[refresh-main-arm] ts=$(timestamp_now) begin port=$SO101_MAIN_ARM_PORT runtimeDir=$RUNTIME_DIR"

python3 "$ROOT_DIR/tools/hardware/export_main_arm_serial_status.py" \
  --port "$SO101_MAIN_ARM_PORT" \
  --power-state "$SO101_MAIN_ARM_POWER_STATE" \
  --mode "$SO101_MAIN_ARM_MODE" \
  $([[ "$SO101_MAIN_ARM_ALLOW_EXECUTE" == "1" ]] && echo "--allow-execute") \
  >"$STATUS_TMP"

python3 "$ROOT_DIR/tools/hardware/bridge_real_hardware_adapter.py" \
  --root-dir "$ROOT_DIR" \
  --source file \
  --input-file "$STATUS_TMP" \
  $([[ "$SO101_MAIN_ARM_GATE_ENABLED" == "1" ]] && echo "--gate-enabled") \
  --gate-reason-code "$SO101_MAIN_ARM_GATE_REASON_CODE" \
  --gate-reason "$SO101_MAIN_ARM_GATE_REASON" \
  --gate-source "$SO101_MAIN_ARM_GATE_SOURCE" \
  >/dev/null

if [[ -n "$SO101_MAIN_ARM_CALIBRATION_PROFILE" ]]; then
  echo "[refresh-main-arm] ts=$(timestamp_now) calibration profile requested from $SO101_MAIN_ARM_CALIBRATION_PROFILE"
  if python3 "$ROOT_DIR/tools/hardware/sync_real_hardware_calibration.py" \
    --root-dir "$ROOT_DIR" \
    --profile "$SO101_MAIN_ARM_CALIBRATION_PROFILE" \
    >/dev/null; then
    echo "[refresh-main-arm] ts=$(timestamp_now) calibration synced from $SO101_MAIN_ARM_CALIBRATION_PROFILE"
  else
    echo "[refresh-main-arm] ts=$(timestamp_now) calibration sync failed from $SO101_MAIN_ARM_CALIBRATION_PROFILE" >&2
    exit 1
  fi
elif [[ -f "$DEFAULT_LOCAL_CALIBRATION_PROFILE" ]]; then
  echo "[refresh-main-arm] ts=$(timestamp_now) calibration profile auto-selected from $DEFAULT_LOCAL_CALIBRATION_PROFILE"
  if python3 "$ROOT_DIR/tools/hardware/sync_real_hardware_calibration.py" \
    --root-dir "$ROOT_DIR" \
    --profile "$DEFAULT_LOCAL_CALIBRATION_PROFILE" \
    >/dev/null; then
    echo "[refresh-main-arm] ts=$(timestamp_now) calibration synced from local default profile"
  else
    echo "[refresh-main-arm] ts=$(timestamp_now) calibration sync failed from local default profile" >&2
    exit 1
  fi
fi

echo "[refresh-main-arm] ts=$(timestamp_now) runtime contract refreshed from $SO101_MAIN_ARM_PORT"
echo "[refresh-main-arm] ts=$(timestamp_now) powerState=$SO101_MAIN_ARM_POWER_STATE mode=$SO101_MAIN_ARM_MODE"
echo "[refresh-main-arm] ts=$(timestamp_now) gate updated allowExecute=$SO101_MAIN_ARM_ALLOW_EXECUTE gateEnabled=$SO101_MAIN_ARM_GATE_ENABLED source=$SO101_MAIN_ARM_GATE_SOURCE"
