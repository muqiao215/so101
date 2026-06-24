#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$(cd "$ROOT/../.." && pwd)/docs/generated/mint-follower-demo"
STAMP="$(date +%Y%m%d-%H%M%S)"
ZIP_PATH="$OUT_DIR/so101_mint_follower_demo_${STAMP}.zip"

mkdir -p "$OUT_DIR"
(
  cd "$ROOT/.."
  zip -r "$ZIP_PATH" mint_follower_demo \
    -x 'mint_follower_demo/logs/*' \
    -x 'mint_follower_demo/__pycache__/*'
)

echo "$ZIP_PATH"
