#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "stop_e2e_stack.sh now defaults to visible demo mode cleanup."
echo "delegating to: bash tools/e2e/stop_visible_demo_stack.sh"

exec bash "$ROOT_DIR/tools/e2e/stop_visible_demo_stack.sh" "$@"
