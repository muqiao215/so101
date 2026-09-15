#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"

stop_matching_processes() {
  local pattern="$1"
  local label="$2"
  local pids

  pids="$(
    pgrep -f "$pattern" | while read -r pid; do
      if [[ "$pid" == "$$" || "$pid" == "$PPID" ]]; then
        continue
      fi
      echo "$pid"
    done || true
  )"
  if [[ -z "$pids" ]]; then
    echo "no residual process for $label"
    return 0
  fi

  echo "$pids" | xargs -r kill
  for _ in $(seq 1 20); do
    if ! pgrep -f "$pattern" >/dev/null 2>&1; then
      echo "stopped residual $label"
      return 0
    fi
    sleep 1
  done

  echo "$pids" | xargs -r kill -9
  echo "force stopped residual $label"
}

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

stop_by_pid_file "$RUNTIME_DIR/so101_visible_frontend.pid" "frontend"
stop_by_pid_file "$RUNTIME_DIR/so101_visible_backend.pid" "backend"
stop_by_pid_file "$RUNTIME_DIR/so101_visible_gzclient.pid" "visible gzclient"
stop_by_pid_file "$RUNTIME_DIR/so101_visible_ros.pid" "visible ros2 stack"

stop_matching_processes "$ROOT_DIR/mes_frontend/node_modules/.bin/vite --host 127.0.0.1" "frontend"
stop_matching_processes "$ROOT_DIR/mes_backend" "backend"
stop_matching_processes "ros2 launch so101_bringup sim_bringup.launch.py" "sim launch"
stop_matching_processes "share/so101_bringup/scripts/task_executor.py" "task executor"
stop_matching_processes "sim_color_detector_node.py" "sim color detector"
stop_matching_processes "yolov8_detector_node.py" "yolov8 detector"
stop_matching_processes "vision_target_projector_node.py" "vision target projector"
stop_matching_processes "vision_overlay_node.py" "vision overlay"
stop_matching_processes "vision_episode_recorder_node.py" "vision episode recorder"
stop_matching_processes "/robot_state_publisher --ros-args --params-file" "robot_state_publisher"
stop_matching_processes "controller_manager/spawner" "controller spawner"
stop_matching_processes "spawn_entity.py" "spawn_entity"
stop_matching_processes "rosbridge_websocket" "rosbridge"
stop_matching_processes "$ROOT_DIR/install/so101_gazebo/share/so101_gazebo/worlds/so101_workcell.world" "gzserver"
stop_matching_processes "^gzclient$" "gzclient"
stop_matching_processes "rviz2 -d" "rviz"
