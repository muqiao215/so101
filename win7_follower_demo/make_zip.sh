#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$(cd "$ROOT/../.." && pwd)/docs/generated/win7-follower-demo"
STAMP="$(date +%Y%m%d-%H%M%S)"
ZIP_PATH="$OUT_DIR/so101_win7_follower_demo_${STAMP}.zip"

mkdir -p "$OUT_DIR"
(
  cd "$ROOT/.."
  zip -r "$ZIP_PATH" win7_follower_demo \
    -x 'win7_follower_demo/logs/*' \
    -x 'win7_follower_demo/__pycache__/*'
)

echo "$ZIP_PATH"
