#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
BACKEND_PID_FILE="$RUNTIME_DIR/real_full_stack_backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/real_full_stack_frontend.pid"

stop_pid_file() {
  local pid_file="$1"
  local name="$2"
  if [[ ! -f "$pid_file" ]]; then
    return 0
  fi

  local pid=""
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    echo "stopped $name pid=$pid"
  fi
  rm -f "$pid_file"
}

bash "$ROOT_DIR/tools/hardware/stop_real_min_bringup.sh" || true
stop_pid_file "$BACKEND_PID_FILE" "backend"
stop_pid_file "$FRONTEND_PID_FILE" "frontend"

echo "real full stack stopped"
