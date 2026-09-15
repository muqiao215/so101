#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
GZCLIENT_PID_FILE="$RUNTIME_DIR/so101_visible_gzclient.pid"
GZCLIENT_LOG_FILE="$RUNTIME_DIR/so101_visible_gzclient.log"
RESET_GAZEBO_GUI="${RESET_GAZEBO_GUI:-false}"

mkdir -p "$RUNTIME_DIR"

if ! pgrep -x gzserver >/dev/null 2>&1; then
  echo "gzserver is not running; start sim core first:" >&2
  echo "  bash tools/e2e/start_sim_core_stack.sh" >&2
  exit 1
fi

if [[ "$RESET_GAZEBO_GUI" == "true" ]]; then
  mkdir -p "$HOME/.gazebo"
  if [[ -f "$HOME/.gazebo/gui.ini" ]]; then
    cp -f "$HOME/.gazebo/gui.ini" "$HOME/.gazebo/gui.ini.bak.$(date +%s)"
  fi
  cat >"$HOME/.gazebo/gui.ini" <<'EOF'
[geometry]
x=0
y=0
width=1280
height=900
EOF
  echo "reset gazebo gui state: $HOME/.gazebo/gui.ini"
fi

pkill -f '^gzclient' || true
sleep 1

setsid bash -lc "
  source /usr/share/gazebo/setup.bash
  source /opt/ros/humble/setup.bash
  source '$ROOT_DIR/install/setup.bash'
  export GAZEBO_MODEL_DATABASE_URI=''
  exec gzclient --verbose
" </dev/null >"$GZCLIENT_LOG_FILE" 2>&1 &

echo "$!" >"$GZCLIENT_PID_FILE"
echo "started standalone gzclient with PID $(cat "$GZCLIENT_PID_FILE")"
echo "log: $GZCLIENT_LOG_FILE"
