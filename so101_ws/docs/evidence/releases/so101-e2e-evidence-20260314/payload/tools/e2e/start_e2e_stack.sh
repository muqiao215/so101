#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
ROS_RUNTIME_LOG_DIR="$RUNTIME_DIR/ros_logs"

ROS_PID_FILE="$RUNTIME_DIR/so101_e2e_ros.pid"
BACKEND_PID_FILE="$RUNTIME_DIR/so101_e2e_backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/so101_e2e_frontend.pid"

ROS_LOG_FILE="$RUNTIME_DIR/so101_e2e_ros.log"
BACKEND_LOG_FILE="$RUNTIME_DIR/so101_e2e_backend.log"
FRONTEND_LOG_FILE="$RUNTIME_DIR/so101_e2e_frontend.log"

USE_RVIZ="${USE_RVIZ:-false}"
USE_MOCK_YOLO="${USE_MOCK_YOLO:-false}"

mkdir -p "$RUNTIME_DIR"
mkdir -p "$ROS_RUNTIME_LOG_DIR"

is_pid_alive() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

ensure_pid_file_is_fresh() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if ! is_pid_alive "$pid"; then
      rm -f "$pid_file"
    fi
  fi
}

is_port_listening() {
  local port="$1"
  nc -z -w 1 127.0.0.1 "$port" >/dev/null 2>&1
}

wait_for_port() {
  local port="$1"
  local name="$2"
  local i
  for i in $(seq 1 60); do
    if is_port_listening "$port"; then
      echo "$name ready on port $port"
      return 0
    fi
    sleep 2
  done
  echo "$name not ready on port $port" >&2
  return 1
}

wait_for_http() {
  local url="$1"
  local name="$2"
  local i
  for i in $(seq 1 60); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name ready: $url"
      return 0
    fi
    sleep 2
  done
  echo "$name not ready: $url" >&2
  return 1
}

start_ros() {
  ensure_pid_file_is_fresh "$ROS_PID_FILE"

  if is_port_listening 9090; then
    echo "rosbridge already listening on 9090, reusing existing ROS2 stack"
    return 0
  fi

  if [[ -f "$ROS_PID_FILE" ]]; then
    echo "ROS2 stack already running with PID $(cat "$ROS_PID_FILE")"
  else
    set +u
    source /opt/ros/humble/setup.bash
    if [[ -f "$ROOT_DIR/install/setup.bash" ]]; then
      source "$ROOT_DIR/install/setup.bash"
    fi
    set -u

    nohup env ROS_LOG_DIR="$ROS_RUNTIME_LOG_DIR" \
      ros2 launch so101_bringup sim_bringup.launch.py \
      use_rviz:="$USE_RVIZ" \
      use_mock_yolo:="$USE_MOCK_YOLO" \
      enable_rosbridge:=true \
      >"$ROS_LOG_FILE" 2>&1 &
    echo "$!" >"$ROS_PID_FILE"
    echo "started ROS2 stack with PID $(cat "$ROS_PID_FILE")"
  fi

  wait_for_port 9090 "rosbridge"
}

start_backend() {
  ensure_pid_file_is_fresh "$BACKEND_PID_FILE"

  if is_port_listening 8080; then
    echo "backend already listening on 8080, reusing existing process"
    return 0
  fi

  if [[ -f "$BACKEND_PID_FILE" ]]; then
    echo "backend already running with PID $(cat "$BACKEND_PID_FILE")"
  else
    setsid bash -lc "
      cd '$ROOT_DIR/mes_backend'
      exec mvn spring-boot:run
    " </dev/null >"$BACKEND_LOG_FILE" 2>&1 &
    echo "$!" >"$BACKEND_PID_FILE"
    echo "started backend with PID $(cat "$BACKEND_PID_FILE")"
  fi

  wait_for_http "http://127.0.0.1:8080/api/ros/health" "backend"
}

start_frontend() {
  ensure_pid_file_is_fresh "$FRONTEND_PID_FILE"

  if is_port_listening 5173; then
    echo "frontend already listening on 5173, reusing existing process"
    return 0
  fi

  if [[ -f "$FRONTEND_PID_FILE" ]]; then
    echo "frontend already running with PID $(cat "$FRONTEND_PID_FILE")"
  else
    setsid bash -lc "
      cd '$ROOT_DIR/mes_frontend'
      exec ./node_modules/.bin/vite --host 127.0.0.1
    " </dev/null >"$FRONTEND_LOG_FILE" 2>&1 &
    echo "$!" >"$FRONTEND_PID_FILE"
    echo "started frontend with PID $(cat "$FRONTEND_PID_FILE")"
  fi

  wait_for_http "http://127.0.0.1:5173" "frontend"
}

start_ros
start_backend
start_frontend

cat <<EOF
e2e stack ready
frontend: http://127.0.0.1:5173
backend:  http://127.0.0.1:8080
rosbridge: ws://127.0.0.1:9090

runtime dir:
  $RUNTIME_DIR

logs:
  $ROS_LOG_FILE
  $BACKEND_LOG_FILE
  $FRONTEND_LOG_FILE

stop:
  bash tools/e2e/stop_e2e_stack.sh
EOF
