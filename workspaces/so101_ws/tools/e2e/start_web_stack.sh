#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
BACKEND_PID_FILE="$RUNTIME_DIR/so101_visible_backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/so101_visible_frontend.pid"
BACKEND_LOG_FILE="$RUNTIME_DIR/so101_visible_backend.log"
FRONTEND_LOG_FILE="$RUNTIME_DIR/so101_visible_frontend.log"

mkdir -p "$RUNTIME_DIR"

if ! nc -z -w 1 127.0.0.1 8080 >/dev/null 2>&1; then
  setsid bash -lc "
    cd '$ROOT_DIR/mes_backend'
    exec mvn spring-boot:run
  " </dev/null >"$BACKEND_LOG_FILE" 2>&1 &
  echo "$!" >"$BACKEND_PID_FILE"
  echo "started backend with PID $(cat "$BACKEND_PID_FILE")"
else
  echo "backend already running on 8080"
fi

if ! nc -z -w 1 127.0.0.1 5173 >/dev/null 2>&1; then
  setsid bash -lc "
    cd '$ROOT_DIR/mes_frontend'
    exec ./node_modules/.bin/vite --host 127.0.0.1
  " </dev/null >"$FRONTEND_LOG_FILE" 2>&1 &
  echo "$!" >"$FRONTEND_PID_FILE"
  echo "started frontend with PID $(cat "$FRONTEND_PID_FILE")"
else
  echo "frontend already running on 5173"
fi

echo "frontend: http://127.0.0.1:5173"
echo "backend:  http://127.0.0.1:8080"
