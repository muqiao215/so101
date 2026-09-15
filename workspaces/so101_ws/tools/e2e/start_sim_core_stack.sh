#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

exec env \
  USE_GZCLIENT=false \
  USE_RVIZ=false \
  START_BACKEND=false \
  START_FRONTEND=false \
  bash "$ROOT_DIR/tools/e2e/start_visible_demo_stack.sh"
