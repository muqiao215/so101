#!/usr/bin/env bash
set -euo pipefail

if curl -fsS -X POST http://127.0.0.1:8080/api/system/open-rviz >/dev/null 2>&1; then
  echo "rviz open request sent through backend"
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
set +u
source /opt/ros/humble/setup.bash
source "$ROOT_DIR/install/setup.bash"
set -u

RVIZ_CONFIG="$ROOT_DIR/install/so101_description/share/so101_description/rviz/display.rviz"

setsid bash -lc "
  source /opt/ros/humble/setup.bash
  source '$ROOT_DIR/install/setup.bash'
  exec rviz2 -d '$RVIZ_CONFIG'
" </dev/null >/tmp/so101_rviz_direct.log 2>&1 &

echo "backend unavailable, started rviz directly"
echo "log: /tmp/so101_rviz_direct.log"
