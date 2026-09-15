#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INPUT_PATH="${1:-docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-candidate/manifest.json}"
OUTPUT_DIR="${2:-docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-native-uvrun}"

cd "$ROOT_DIR"

# ROS2 setup exports PYTHONPATH with system numpy/Pillow. That breaks LeRobot's
# pandas/numpy stack even inside `uv run --isolated`, so scrub it explicitly.
UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-300}" \
env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 \
  uv run --isolated --python 3.10 \
    --with 'lerobot==0.4.4' \
    --with 'evdev==1.6.1' \
    --with 'numpy>=2,<3' \
    --with 'pandas>=2.2,<2.4' \
    --with 'pyarrow>=15,<24' \
    --with 'pillow>=10,<12' \
    python tools/hardware/export_lerobot_candidate_to_native.py \
      "$INPUT_PATH" \
      --output-dir "$OUTPUT_DIR" \
      --overwrite \
      --fail-on-blocked
