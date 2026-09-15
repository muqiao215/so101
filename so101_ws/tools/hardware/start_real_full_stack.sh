#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
BACKEND_PID_FILE="$RUNTIME_DIR/real_full_stack_backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/real_full_stack_frontend.pid"
BACKEND_LOG="$RUNTIME_DIR/real_full_stack_backend.log"
FRONTEND_LOG="$RUNTIME_DIR/real_full_stack_frontend.log"

mkdir -p "$RUNTIME_DIR"

is_port_listening() {
  local port="$1"
  ss -ltn "( sport = :$port )" | tail -n +2 | grep -q .
}

wait_http_ok() {
  local url="$1"
  local name="$2"
  local i
  for i in $(seq 1 40); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name ready: $url"
      return 0
    fi
    sleep 1
  done
  echo "$name not ready within timeout: $url" >&2
  return 1
}

start_backend() {
  if is_port_listening 8080; then
    echo "backend already listening on 8080, reusing existing process"
    return 0
  fi

  (
    cd "$ROOT_DIR/mes_backend"
    nohup mvn spring-boot:run >"$BACKEND_LOG" 2>&1 &
    echo $! >"$BACKEND_PID_FILE"
  )
  wait_http_ok "http://127.0.0.1:8080/api/ros/health" "backend"
}

start_frontend() {
  if is_port_listening 5173; then
    echo "frontend already listening on 5173, reusing existing process"
    return 0
  fi

  (
    cd "$ROOT_DIR/mes_frontend"
    nohup npm run dev -- --host 127.0.0.1 >"$FRONTEND_LOG" 2>&1 &
    echo $! >"$FRONTEND_PID_FILE"
  )
  wait_http_ok "http://127.0.0.1:5173" "frontend"
}

start_backend
start_frontend

ENABLE_ROSBRIDGE=1 \
DEFAULT_COMMAND_EXECUTION_ENABLED=1 \
DEFAULT_DETECTION_TRIGGER_ENABLED=0 \
SO101_MAIN_ARM_ALLOW_EXECUTE=1 \
SO101_MAIN_ARM_GATE_ENABLED=1 \
SO101_MAIN_ARM_GATE_REASON_CODE=READY_FOR_MIN_MOTION \
SO101_MAIN_ARM_GATE_REASON="已确认现场安全，允许前端直接下发最小动作验证工单" \
bash "$ROOT_DIR/tools/hardware/start_real_min_bringup.sh"

cat <<EOF
real full stack ready
frontend: http://127.0.0.1:5173
backend:  http://127.0.0.1:8080
bringup:  $RUNTIME_DIR/so101_real_min.log

default mode:
  - rosbridge enabled
  - frontend available
  - command execution enabled
  - detection trigger disabled
  - main arm refresh keeps allowExecute=true
EOF
