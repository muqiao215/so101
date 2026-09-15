#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVIDENCE_DIR="$ROOT_DIR/docs/evidence"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime/gzm004"

STAMP="$(date +%Y%m%d%H%M%S)"
ROS_DOMAIN_ID_VALUE="${ROS_DOMAIN_ID_VALUE:-82}"
ROS_RUNTIME_LOG_DIR="$RUNTIME_DIR/ros_logs"

DEMO_LAUNCH_LOG="$EVIDENCE_DIR/gzm-004-demo-launch-${STAMP}.log"
EXPORT_LOG="$EVIDENCE_DIR/gzm-004-export-${STAMP}.log"
MAPPING_YAML="$EVIDENCE_DIR/gzm-004-mapping-${STAMP}.yaml"
SYNC_LOG="$EVIDENCE_DIR/gzm-004-sync-${STAMP}.log"
BUILD_LOG="$EVIDENCE_DIR/gzm-004-build-${STAMP}.log"
BRINGUP_LOG="$EVIDENCE_DIR/gzm-004-bringup-${STAMP}.log"
STATUS_LOG="$EVIDENCE_DIR/gzm-004-status-${STAMP}.log"
TRAJ_LOG="$EVIDENCE_DIR/gzm-004-trajectory-${STAMP}.log"
PUB_LOG="$EVIDENCE_DIR/gzm-004-publish-${STAMP}.log"
CAPTURE_LOG="$EVIDENCE_DIR/gzm-004-capture-${STAMP}.log"
SUMMARY_MD="$EVIDENCE_DIR/GZM-004_验证记录_${STAMP}.md"

mkdir -p "$EVIDENCE_DIR" "$RUNTIME_DIR" "$ROS_RUNTIME_LOG_DIR"

cleanup() {
  if [[ -n "${CAPTURE_PID:-}" ]]; then
    kill "$CAPTURE_PID" 2>/dev/null || true
  fi
  if [[ -n "${BRINGUP_PID:-}" ]]; then
    kill "$BRINGUP_PID" 2>/dev/null || true
    wait "$BRINGUP_PID" 2>/dev/null || true
  fi
  if [[ -n "${DEMO_PID:-}" ]]; then
    kill "$DEMO_PID" 2>/dev/null || true
    wait "$DEMO_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

export ROS_DOMAIN_ID="$ROS_DOMAIN_ID_VALUE"
set +u
source /opt/ros/humble/setup.bash
source "$ROOT_DIR/install/setup.bash"
set -u

nohup env ROS_DOMAIN_ID="$ROS_DOMAIN_ID" ROS_LOG_DIR="$ROS_RUNTIME_LOG_DIR" \
  ros2 launch so101_moveit_config demo.launch.py \
  enable_move_group:=true \
  use_rviz:=false \
  use_gzclient:=false \
  >"$DEMO_LAUNCH_LOG" 2>&1 &
DEMO_PID="$!"

for _ in $(seq 1 90); do
  if grep -q "You can start planning now!" "$DEMO_LAUNCH_LOG"; then
    break
  fi
  sleep 1
done

if ! grep -q "You can start planning now!" "$DEMO_LAUNCH_LOG"; then
  echo "move_group did not become ready" >&2
  exit 1
fi

ROS_DOMAIN_ID="$ROS_DOMAIN_ID" ros2 run so101_moveit_config pick_place_runner.py \
  --iterations 1 \
  --retry-per-waypoint 1 \
  --planning-time 2.0 \
  --export-mapping-yaml "$MAPPING_YAML" \
  >"$EXPORT_LOG" 2>&1

kill "$DEMO_PID" 2>/dev/null || true
wait "$DEMO_PID" 2>/dev/null || true
unset DEMO_PID

python3 "$ROOT_DIR/src/so101_bringup/scripts/sync_action_template_mapping.py" \
  --export-yaml "$MAPPING_YAML" \
  --waypoints-yaml "$ROOT_DIR/src/so101_bringup/config/waypoints.yaml" \
  --target-template pick_place_default \
  --alias-template pick_place_red \
  --alias-template pick_place_blue \
  >"$SYNC_LOG" 2>&1

(
  cd "$ROOT_DIR"
  colcon build --packages-select so101_bringup
) >"$BUILD_LOG" 2>&1

set +u
source "$ROOT_DIR/install/setup.bash"
set -u

nohup env ROS_DOMAIN_ID="$ROS_DOMAIN_ID" ROS_LOG_DIR="$ROS_RUNTIME_LOG_DIR" \
  ros2 launch so101_bringup real_bringup.launch.py \
  enable_rosbridge:=false \
  use_mock_yolo:=false \
  >"$BRINGUP_LOG" 2>&1 &
BRINGUP_PID="$!"

for _ in $(seq 1 25); do
  if grep -q "Task executor ready" "$BRINGUP_LOG"; then
    break
  fi
  sleep 1
done

if ! grep -q "Task executor ready" "$BRINGUP_LOG"; then
  echo "task_executor did not become ready" >&2
  exit 1
fi

python3 "$ROOT_DIR/tools/e2e/capture_r2c003_flow.py" \
  --status-log "$STATUS_LOG" \
  --traj-log "$TRAJ_LOG" \
  --timeout-sec 30 \
  >"$CAPTURE_LOG" 2>&1 &
CAPTURE_PID="$!"

sleep 2

REQUEST_ID="req-gzm004-${STAMP}"
ORDER_ID="order-gzm004-${STAMP}"
COMMAND_JSON="{\"requestId\":\"${REQUEST_ID}\",\"orderId\":\"${ORDER_ID}\",\"actionTemplateId\":\"pick_place_default\",\"params\":{}}"

ROS_DOMAIN_ID="$ROS_DOMAIN_ID" ros2 topic pub --once /mes_task_cmd std_msgs/msg/String \
  "{data: '${COMMAND_JSON}'}" >"$PUB_LOG" 2>&1

wait "$CAPTURE_PID"
unset CAPTURE_PID

if ! grep -Eq '"code":[[:space:]]*"OK"' "$STATUS_LOG"; then
  echo "missing OK in $STATUS_LOG" >&2
  exit 1
fi

STEP_COUNT="$(grep -Eo '"code":[[:space:]]*"STEP"' "$STATUS_LOG" | wc -l | tr -d ' ')"
if [[ "$STEP_COUNT" -lt 8 ]]; then
  echo "expected at least 8 STEP events, got $STEP_COUNT" >&2
  exit 1
fi

MULTI_POINT_COUNT="$(python3 - "$TRAJ_LOG" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
count = 0
max_points = 0
for line in path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    payload = json.loads(line)
    point_count = int(payload.get("point_count", 0))
    if point_count > 1:
        count += 1
    max_points = max(max_points, point_count)
print(f"{count}:{max_points}")
PY
)"
MULTI_POINT_TRAJ_COUNT="${MULTI_POINT_COUNT%%:*}"
MAX_POINT_COUNT="${MULTI_POINT_COUNT##*:}"

if [[ "$MULTI_POINT_TRAJ_COUNT" -lt 8 ]]; then
  echo "expected at least 8 multi-point trajectories, got $MULTI_POINT_TRAJ_COUNT" >&2
  exit 1
fi

cat >"$SUMMARY_MD" <<EOF
# GZM-004 验证记录（${STAMP}）

## 执行命令

\`\`\`bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
bash tools/e2e/verify_gzm004_mapping.sh
\`\`\`

## 运行参数

- \`ROS_DOMAIN_ID=${ROS_DOMAIN_ID}\`
- export launch: \`ros2 launch so101_moveit_config demo.launch.py enable_move_group:=true use_rviz:=false use_gzclient:=false\`
- execute launch: \`ros2 launch so101_bringup real_bringup.launch.py enable_rosbridge:=false use_mock_yolo:=false\`
- command actionTemplateId: \`pick_place_default\`

## 验证结论

- \`pick_place_runner.py --export-mapping-yaml\` 已生成新的轨迹映射 YAML
- 导出结果已通过 \`sync_action_template_mapping.py\` 回灌到 \`action_templates\`
- \`task_executor\` 已消费模板中的映射轨迹，而不是退回单点 waypoint
- \`/mes_task_status\` 捕获到完整状态流：
  - \`STARTED\`
  - \`STEP x${STEP_COUNT}\`
  - \`OK\`
- \`/joint_trajectory_controller/joint_trajectory\` 捕获到 \`${MULTI_POINT_TRAJ_COUNT}\` 条多点轨迹，最大点数 \`${MAX_POINT_COUNT}\`

## 证据文件

- demo launch log:
  - \`docs/evidence/$(basename "$DEMO_LAUNCH_LOG")\`
- export log:
  - \`docs/evidence/$(basename "$EXPORT_LOG")\`
- mapping yaml:
  - \`docs/evidence/$(basename "$MAPPING_YAML")\`
- sync log:
  - \`docs/evidence/$(basename "$SYNC_LOG")\`
- build log:
  - \`docs/evidence/$(basename "$BUILD_LOG")\`
- bringup log:
  - \`docs/evidence/$(basename "$BRINGUP_LOG")\`
- status log:
  - \`docs/evidence/$(basename "$STATUS_LOG")\`
- trajectory log:
  - \`docs/evidence/$(basename "$TRAJ_LOG")\`
- publish log:
  - \`docs/evidence/$(basename "$PUB_LOG")\`
- capture log:
  - \`docs/evidence/$(basename "$CAPTURE_LOG")\`
EOF

echo "summary: $SUMMARY_MD"
echo "mapping_yaml: $MAPPING_YAML"
echo "status_log: $STATUS_LOG"
echo "trajectory_log: $TRAJ_LOG"
