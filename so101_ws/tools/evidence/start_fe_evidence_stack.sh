#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/muqiao/dev/ros2/workspaces/so101_ws"
LOG_ROOT="$ROOT_DIR/docs/evidence/logs"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$LOG_ROOT/fe-evidence-$STAMP"

mkdir -p "$LOG_DIR"

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
    nohup mvn spring-boot:run >"$LOG_DIR/backend.log" 2>&1 &
    echo $! >"$LOG_DIR/backend.pid"
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
    nohup npm run dev -- --host 127.0.0.1 >"$LOG_DIR/frontend.log" 2>&1 &
    echo $! >"$LOG_DIR/frontend.pid"
  )
  wait_http_ok "http://127.0.0.1:5173" "frontend"
}

start_backend
start_frontend

cat <<EOF
stack ready
log_dir: $LOG_DIR
frontend: http://127.0.0.1:5173
backend:  http://127.0.0.1:8080

stop commands:
  test -f "$LOG_DIR/backend.pid" && kill \$(cat "$LOG_DIR/backend.pid")
  test -f "$LOG_DIR/frontend.pid" && kill \$(cat "$LOG_DIR/frontend.pid")
EOF
