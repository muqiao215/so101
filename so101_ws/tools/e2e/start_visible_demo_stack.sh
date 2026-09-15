#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
ROS_RUNTIME_LOG_DIR="$RUNTIME_DIR/ros_logs_visible"

ROS_PID_FILE="$RUNTIME_DIR/so101_visible_ros.pid"
GZCLIENT_PID_FILE="$RUNTIME_DIR/so101_visible_gzclient.pid"
BACKEND_PID_FILE="$RUNTIME_DIR/so101_visible_backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/so101_visible_frontend.pid"

ROS_LOG_FILE="$RUNTIME_DIR/so101_visible_ros.log"
GZCLIENT_LOG_FILE="$RUNTIME_DIR/so101_visible_gzclient.log"
BACKEND_LOG_FILE="$RUNTIME_DIR/so101_visible_backend.log"
FRONTEND_LOG_FILE="$RUNTIME_DIR/so101_visible_frontend.log"

USE_RVIZ="${USE_RVIZ:-false}"
USE_MOCK_YOLO="${USE_MOCK_YOLO:-false}"
USE_GAZEBO_COLOR_DETECTOR="${USE_GAZEBO_COLOR_DETECTOR:-false}"
USE_REAL_YOLO="${USE_REAL_YOLO:-false}"
USE_VISION_TARGET_PROJECTION="${USE_VISION_TARGET_PROJECTION:-false}"
USE_VISION_OVERLAY="${USE_VISION_OVERLAY:-false}"
USE_VISION_EPISODE_RECORDER="${USE_VISION_EPISODE_RECORDER:-false}"
USE_GZCLIENT="${USE_GZCLIENT:-true}"
ENABLE_ROSBRIDGE="${ENABLE_ROSBRIDGE:-true}"
START_BACKEND="${START_BACKEND:-true}"
START_FRONTEND="${START_FRONTEND:-true}"
RESET_GAZEBO_GUI="${RESET_GAZEBO_GUI:-false}"
CAMERA_IMAGE_TOPIC="${CAMERA_IMAGE_TOPIC:-/camera/color/image_raw}"
DETECTIONS_TOPIC="${DETECTIONS_TOPIC:-/detections}"
VISION_TARGETS_TOPIC="${VISION_TARGETS_TOPIC:-/vision/targets}"
VISION_OVERLAY_TOPIC="${VISION_OVERLAY_TOPIC:-/vision/debug/image_overlay}"
VISION_EPISODE_ID="${VISION_EPISODE_ID:-}"
VISION_EPISODE_OUTPUT_DIR="${VISION_EPISODE_OUTPUT_DIR:-docs/generated/vision-episodes}"
VISION_SNAPSHOT_REQUIRED_STREAMS="${VISION_SNAPSHOT_REQUIRED_STREAMS:-detections,vision_targets,joint_states}"
VISION_SNAPSHOT_MAX_STREAM_AGE_SEC="${VISION_SNAPSHOT_MAX_STREAM_AGE_SEC:-0.75}"
VISION_IMAGE_SNAPSHOT_EVERY_N="${VISION_IMAGE_SNAPSHOT_EVERY_N:-30}"
VISION_MAX_IMAGE_SNAPSHOTS="${VISION_MAX_IMAGE_SNAPSHOTS:-20}"
STATUS_HEARTBEAT_ENABLED="${STATUS_HEARTBEAT_ENABLED:-true}"
STATUS_HEARTBEAT_PERIOD_SEC="${STATUS_HEARTBEAT_PERIOD_SEC:-1.0}"
BENCHMARK_REACH_ENABLED="${BENCHMARK_REACH_ENABLED:-false}"
BENCHMARK_PREFERRED_CATEGORY="${BENCHMARK_PREFERRED_CATEGORY:-auto}"
BENCHMARK_TRIGGER_COOLDOWN_SEC="${BENCHMARK_TRIGGER_COOLDOWN_SEC:-8.0}"
BENCHMARK_REPORT_DIR="${BENCHMARK_REPORT_DIR:-docs/generated/vision-episodes}"
BENCHMARK_REACH_THRESHOLD_M="${BENCHMARK_REACH_THRESHOLD_M:-0.08}"
YOLO_MODEL_PATH="${YOLO_MODEL_PATH:-yolov8n.pt}"
YOLO_DEVICE="${YOLO_DEVICE:-cpu}"

mkdir -p "$RUNTIME_DIR"
mkdir -p "$ROS_RUNTIME_LOG_DIR"

set +u
source /usr/share/gazebo/setup.bash
set -u
export GAZEBO_MODEL_DATABASE_URI=""

reset_gazebo_gui_state() {
  local gui_ini="$HOME/.gazebo/gui.ini"
  local backup=""

  mkdir -p "$HOME/.gazebo"
  if [[ -f "$gui_ini" ]]; then
    backup="${gui_ini}.bak.$(date +%s)"
    cp -f "$gui_ini" "$backup"
    echo "backed up gazebo gui state to $backup"
  fi

  cat >"$gui_ini" <<'EOF'
[geometry]
x=0
y=0
width=1280
height=900
EOF
  echo "reset gazebo gui state: $gui_ini"
}

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

wait_for_task_executor_graph() {
  local i
  for i in $(seq 1 30); do
    if bash -lc "
      source /opt/ros/humble/setup.bash
      source '$ROOT_DIR/install/setup.bash'
      python3 - <<'PY'
import rclpy
from rclpy.node import Node

rclpy.init()
node = Node('visible_stack_graph_probe')
subs = node.get_subscriptions_info_by_topic('/mes_task_cmd')
pubs = node.get_publishers_info_by_topic('/mes_task_status')
ok = bool(subs) and bool(pubs)
node.destroy_node()
rclpy.shutdown()
raise SystemExit(0 if ok else 1)
PY
    " >/dev/null 2>&1; then
      echo "task executor graph ready"
      return 0
    fi
    sleep 1
  done
  echo "task executor graph not ready" >&2
  return 1
}

assert_visible_ros_stack_alive() {
  if [[ ! -f "$ROS_PID_FILE" ]]; then
    echo "visible ROS2 stack pid file is missing" >&2
    return 1
  fi

  local pid
  pid="$(cat "$ROS_PID_FILE")"
  if ! is_pid_alive "$pid"; then
    echo "visible ROS2 stack exited unexpectedly (pid $pid)" >&2
    return 1
  fi
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

is_gzclient_running() {
  pgrep -x gzclient >/dev/null 2>&1
}

wait_for_gzclient() {
  local timeout="${1:-20}"
  local i
  for i in $(seq 1 "$timeout"); do
    if is_gzclient_running; then
      echo "gzclient ready"
      return 0
    fi
    sleep 1
  done
  echo "gzclient not ready" >&2
  return 1
}

start_standalone_gzclient() {
  ensure_pid_file_is_fresh "$GZCLIENT_PID_FILE"

  if is_gzclient_running; then
    echo "gzclient already running"
    return 0
  fi

  if ! pgrep -x gzserver >/dev/null 2>&1; then
    echo "gzserver is not running, cannot attach gzclient" >&2
    return 1
  fi

  if [[ "$RESET_GAZEBO_GUI" == "true" ]]; then
    reset_gazebo_gui_state
  fi

  setsid bash -lc "
    source /usr/share/gazebo/setup.bash
    source /opt/ros/humble/setup.bash
    source '$ROOT_DIR/install/setup.bash'
    export GAZEBO_MODEL_DATABASE_URI=''
    exec gzclient --verbose
  " </dev/null >"$GZCLIENT_LOG_FILE" 2>&1 &
  echo "$!" >"$GZCLIENT_PID_FILE"
  echo "started standalone gzclient with PID $(cat "$GZCLIENT_PID_FILE")"
  wait_for_gzclient
}

ensure_visible_gzclient() {
  if [[ "$USE_GZCLIENT" != "true" ]]; then
    return 0
  fi

  if is_gzclient_running; then
    echo "gzclient already running"
    return 0
  fi
  start_standalone_gzclient
}

start_ros() {
  ensure_pid_file_is_fresh "$ROS_PID_FILE"
  ensure_pid_file_is_fresh "$GZCLIENT_PID_FILE"

  if [[ "$ENABLE_ROSBRIDGE" == "true" ]] && is_port_listening 9090; then
    if [[ -f "$ROS_PID_FILE" ]]; then
      echo "rosbridge already listening on 9090, reusing existing visible ROS2 stack"
      ensure_visible_gzclient
      return 0
    fi

    echo "rosbridge already listening on 9090 from another stack." >&2
    echo "visible demo mode requires a fresh sim so Gazebo camera/world settings apply cleanly." >&2
    echo "stop the old stack first, then rerun:" >&2
    echo "  bash tools/e2e/stop_visible_demo_stack.sh" >&2
    return 1
  fi

  if [[ -f "$ROS_PID_FILE" ]]; then
    echo "visible ROS2 stack already running with PID $(cat "$ROS_PID_FILE")"
  else
    set +u
    source /usr/share/gazebo/setup.bash
    source /opt/ros/humble/setup.bash
    if [[ -f "$ROOT_DIR/install/setup.bash" ]]; then
      source "$ROOT_DIR/install/setup.bash"
    fi
    set -u

    setsid bash -lc "
      source /usr/share/gazebo/setup.bash
      source /opt/ros/humble/setup.bash
      source '$ROOT_DIR/install/setup.bash'
      export ROS_LOG_DIR='$ROS_RUNTIME_LOG_DIR'
      exec ros2 launch so101_bringup sim_bringup.launch.py \
        use_gzclient:=false \
        use_rviz:='$USE_RVIZ' \
        use_mock_yolo:='$USE_MOCK_YOLO' \
        use_gazebo_color_detector:='$USE_GAZEBO_COLOR_DETECTOR' \
        use_real_yolo:='$USE_REAL_YOLO' \
        use_vision_target_projection:='$USE_VISION_TARGET_PROJECTION' \
        use_vision_overlay:='$USE_VISION_OVERLAY' \
        use_vision_episode_recorder:='$USE_VISION_EPISODE_RECORDER' \
        camera_image_topic:='$CAMERA_IMAGE_TOPIC' \
        detections_topic:='$DETECTIONS_TOPIC' \
        vision_targets_topic:='$VISION_TARGETS_TOPIC' \
        vision_overlay_topic:='$VISION_OVERLAY_TOPIC' \
        vision_episode_id:='$VISION_EPISODE_ID' \
        vision_episode_output_dir:='$VISION_EPISODE_OUTPUT_DIR' \
        vision_snapshot_required_streams:='$VISION_SNAPSHOT_REQUIRED_STREAMS' \
        vision_snapshot_max_stream_age_sec:='$VISION_SNAPSHOT_MAX_STREAM_AGE_SEC' \
        vision_image_snapshot_every_n:='$VISION_IMAGE_SNAPSHOT_EVERY_N' \
        vision_max_image_snapshots:='$VISION_MAX_IMAGE_SNAPSHOTS' \
        status_heartbeat_enabled:='$STATUS_HEARTBEAT_ENABLED' \
        status_heartbeat_period_sec:='$STATUS_HEARTBEAT_PERIOD_SEC' \
        benchmark_reach_enabled:='$BENCHMARK_REACH_ENABLED' \
        benchmark_preferred_category:='$BENCHMARK_PREFERRED_CATEGORY' \
        benchmark_trigger_cooldown_sec:='$BENCHMARK_TRIGGER_COOLDOWN_SEC' \
        benchmark_report_dir:='$BENCHMARK_REPORT_DIR' \
        benchmark_reach_threshold_m:='$BENCHMARK_REACH_THRESHOLD_M' \
        yolo_model_path:='$YOLO_MODEL_PATH' \
        yolo_device:='$YOLO_DEVICE' \
        enable_rosbridge:='$ENABLE_ROSBRIDGE'
    " </dev/null >"$ROS_LOG_FILE" 2>&1 &
    echo "$!" >"$ROS_PID_FILE"
    echo "started visible ROS2 stack with PID $(cat "$ROS_PID_FILE")"
  fi

  if [[ "$ENABLE_ROSBRIDGE" == "true" ]]; then
    wait_for_port 9090 "rosbridge"
  else
    echo "skipping rosbridge readiness check"
  fi
  assert_visible_ros_stack_alive
  wait_for_task_executor_graph
  ensure_visible_gzclient
}

start_backend() {
  if [[ "$START_BACKEND" != "true" ]]; then
    echo "skipping backend startup"
    return 0
  fi

  ensure_pid_file_is_fresh "$BACKEND_PID_FILE"

  if is_port_listening 8080; then
    echo "backend already listening on 8080, validating health endpoint"
    wait_for_http "http://127.0.0.1:8080/api/ros/health" "backend"
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
  if [[ "$START_FRONTEND" != "true" ]]; then
    echo "skipping frontend startup"
    return 0
  fi

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

if [[ "$ENABLE_ROSBRIDGE" == "true" ]]; then
  ROSBRIDGE_LINE="rosbridge: ws://127.0.0.1:9090"
else
  ROSBRIDGE_LINE="rosbridge: disabled"
fi

cat <<OUT
visible demo stack ready
frontend: http://127.0.0.1:5173
backend:  http://127.0.0.1:8080
$ROSBRIDGE_LINE

runtime dir:
  $RUNTIME_DIR

logs:
  $ROS_LOG_FILE
  $GZCLIENT_LOG_FILE
  $BACKEND_LOG_FILE
  $FRONTEND_LOG_FILE

notes:
  Gazebo GUI is attached as standalone gzclient after gzserver is stable
  RViz can be enabled with USE_RVIZ=true
  backend startup can be skipped with START_BACKEND=false
  frontend startup can be skipped with START_FRONTEND=false
  GUI state reset can be forced with RESET_GAZEBO_GUI=true

stop:
  bash tools/e2e/stop_visible_demo_stack.sh
OUT
