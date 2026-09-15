#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"

stop_by_pid_file() {
  local pid_file="$1"
  local label="$2"

  if [[ ! -f "$pid_file" ]]; then
    echo "no pid file for $label"
    return 0
  fi

  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    for _ in $(seq 1 20); do
      if ! kill -0 "$pid" 2>/dev/null; then
        rm -f "$pid_file"
        echo "stopped $label"
        return 0
      fi
      sleep 1
    done
    kill -9 "$pid" 2>/dev/null || true
  fi

  rm -f "$pid_file"
  echo "stopped $label"
}

stop_by_pid_file "$RUNTIME_DIR/so101_e2e_frontend.pid" "frontend"
stop_by_pid_file "$RUNTIME_DIR/so101_e2e_backend.pid" "backend"
stop_by_pid_file "$RUNTIME_DIR/so101_e2e_ros.pid" "ros2 stack"
