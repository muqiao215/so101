#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
BRINGUP_PID_FILE="$RUNTIME_DIR/so101_real_min.pid"
WATCH_PID_FILE="$RUNTIME_DIR/main_arm_runtime_watch.pid"
WATCH_LOG_FILE="$RUNTIME_DIR/main_arm_runtime_watch.log"
STATUS_FILE="$RUNTIME_DIR/real_hardware_status.json"
GATE_FILE="$RUNTIME_DIR/real_hardware_command_gate.json"

is_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

read_pid_file() {
  local path="$1"
  if [[ -f "$path" ]]; then
    cat "$path" 2>/dev/null || true
  fi
}

bringup_pid="$(read_pid_file "$BRINGUP_PID_FILE")"
watch_pid="$(read_pid_file "$WATCH_PID_FILE")"

echo "[main-arm-runtime]"
echo "  port_env: ${SO101_MAIN_ARM_PORT:-auto-detect}"
echo "  tty_present: $(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | tr '\n' ' ' || true)"
echo "  bringup_pid: ${bringup_pid:-none}"
echo "  bringup_alive: $([[ -n "${bringup_pid:-}" ]] && is_alive "$bringup_pid" && echo yes || echo no)"
echo "  watcher_pid: ${watch_pid:-none}"
echo "  watcher_alive: $([[ -n "${watch_pid:-}" ]] && is_alive "$watch_pid" && echo yes || echo no)"
echo "  status_file: $([[ -f "$STATUS_FILE" ]] && echo present || echo missing)"
echo "  gate_file: $([[ -f "$GATE_FILE" ]] && echo present || echo missing)"
echo "  watch_log: $WATCH_LOG_FILE"

if [[ -f "$STATUS_FILE" ]]; then
  echo "  status_updated_at: $(python3 - <<'PY' "$STATUS_FILE"
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
print(payload.get('updatedAt', ''))
PY
)"
fi

if [[ -f "$GATE_FILE" ]]; then
  echo "  gate_reason_code: $(python3 - <<'PY' "$GATE_FILE"
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
print(payload.get('reasonCode', ''))
PY
)"
fi

if [[ -f "$WATCH_LOG_FILE" ]]; then
  echo "  watch_log_tail:"
  tail -n 10 "$WATCH_LOG_FILE" | sed 's/^/    /'
fi
