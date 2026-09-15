#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
PID_FILE="$RUNTIME_DIR/so101_sim.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No SO101 sim bringup PID file found"
  exit 0
fi

pid="$(cat "$PID_FILE")"
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PID_FILE"
      echo "Stopped SO101 sim bringup"
      exit 0
    fi
    sleep 1
  done
  kill -9 "$pid" 2>/dev/null || true
fi

rm -f "$PID_FILE"
echo "Stopped SO101 sim bringup"
