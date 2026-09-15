#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE_TOPIC="${IMAGE_TOPIC:-/camera/color/image_raw}"
INFO_TOPIC="${INFO_TOPIC:-/camera/color/camera_info}"
TIMEOUT_SEC="${TIMEOUT_SEC:-20}"
REPORT_PATH="${REPORT_PATH:-$ROOT_DIR/docs/generated/vision-episodes/sim-camera-topic-assertion.json}"

set +u
source /opt/ros/humble/setup.bash
if [ -f "$ROOT_DIR/install/setup.bash" ]; then
  source "$ROOT_DIR/install/setup.bash"
fi
set -u

tmp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

image_out="$tmp_dir/image.txt"
image_err="$tmp_dir/image.err"
info_out="$tmp_dir/info.txt"
info_err="$tmp_dir/info.err"

check_topic_once() {
  local topic="$1"
  local message_kind="$2"
  local output_path="$3"

  python3 - "$topic" "$message_kind" "$TIMEOUT_SEC" >"$output_path" <<'PY'
import json
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image


topic = sys.argv[1]
message_kind = sys.argv[2]
timeout_sec = float(sys.argv[3])
message_type = Image if message_kind == "image" else CameraInfo

rclpy.init()
node = Node("sim_camera_topic_assertion")
received = {}


def callback(msg):
    if message_kind == "image":
        received["summary"] = {
            "height": int(msg.height),
            "width": int(msg.width),
            "encoding": str(msg.encoding),
            "step": int(msg.step),
            "data_len": len(msg.data),
        }
    else:
        received["summary"] = {
            "height": int(msg.height),
            "width": int(msg.width),
            "frame_id": str(msg.header.frame_id),
        }


subscription = node.create_subscription(message_type, topic, callback, 10)
deadline = time.time() + timeout_sec
try:
    while rclpy.ok() and time.time() < deadline and "summary" not in received:
        rclpy.spin_once(node, timeout_sec=0.1)
finally:
    node.destroy_subscription(subscription)
    node.destroy_node()
    rclpy.shutdown()

if "summary" not in received:
    raise SystemExit(f"no {message_kind} sample received on {topic} within {timeout_sec:.1f}s")

print(json.dumps(received["summary"], ensure_ascii=False))
PY
}

image_status="passed"
info_status="passed"
image_error=""
info_error=""

if ! check_topic_once "$IMAGE_TOPIC" image "$image_out" 2>"$image_err"; then
  image_status="failed"
  image_error="$(tr '\n' ' ' <"$image_err" | sed 's/[[:space:]]\\+/ /g' | cut -c1-500)"
fi

if ! check_topic_once "$INFO_TOPIC" camera_info "$info_out" 2>"$info_err"; then
  info_status="failed"
  info_error="$(tr '\n' ' ' <"$info_err" | sed 's/[[:space:]]\\+/ /g' | cut -c1-500)"
fi

mkdir -p "$(dirname "$REPORT_PATH")"
python3 - "$REPORT_PATH" "$IMAGE_TOPIC" "$INFO_TOPIC" "$TIMEOUT_SEC" "$image_status" "$info_status" "$image_error" "$info_error" <<'PY'
import json
import sys
import time
from pathlib import Path

path = Path(sys.argv[1])
image_status = sys.argv[5]
info_status = sys.argv[6]
payload = {
    "schema_version": "sim_camera_topic_assertion.v1",
    "status": "passed" if image_status == "passed" and info_status == "passed" else "failed",
    "image_topic": sys.argv[2],
    "camera_info_topic": sys.argv[3],
    "timeout_sec": float(sys.argv[4]),
    "checks": {
        "image": {"status": image_status, "error": sys.argv[7]},
        "camera_info": {"status": info_status, "error": sys.argv[8]},
    },
    "wall_time_sec": round(time.time(), 6),
}
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": payload["status"], "report": str(path)}, ensure_ascii=False))
PY

if [ "$image_status" != "passed" ] || [ "$info_status" != "passed" ]; then
  exit 2
fi
