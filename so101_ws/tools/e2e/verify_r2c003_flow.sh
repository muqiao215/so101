#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVIDENCE_DIR="$ROOT_DIR/docs/evidence"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime/r2c003"

STAMP="$(date +%Y%m%d%H%M%S)"
ROS_DOMAIN_ID_VALUE="${ROS_DOMAIN_ID_VALUE:-77}"
ROS_RUNTIME_LOG_DIR="$RUNTIME_DIR/ros_logs"

LAUNCH_LOG="$EVIDENCE_DIR/r2c-003-launch-${STAMP}.log"
STATUS_LOG="$EVIDENCE_DIR/r2c-003-status-${STAMP}.log"
TRAJ_LOG="$EVIDENCE_DIR/r2c-003-trajectory-${STAMP}.log"
PUB_LOG="$EVIDENCE_DIR/r2c-003-publish-${STAMP}.log"
CAPTURE_LOG="$EVIDENCE_DIR/r2c-003-capture-${STAMP}.log"
SUMMARY_MD="$EVIDENCE_DIR/R2C-003_验证记录_${STAMP}.md"

mkdir -p "$EVIDENCE_DIR" "$RUNTIME_DIR" "$ROS_RUNTIME_LOG_DIR"

cleanup() {
  if [[ -n "${CAPTURE_PID:-}" ]]; then
    kill "$CAPTURE_PID" 2>/dev/null || true
  fi
  if [[ -n "${LAUNCH_PID:-}" ]]; then
    kill "$LAUNCH_PID" 2>/dev/null || true
    wait "$LAUNCH_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

export ROS_DOMAIN_ID="$ROS_DOMAIN_ID_VALUE"
set +u
source /opt/ros/humble/setup.bash
source "$ROOT_DIR/install/setup.bash"
set -u

nohup env ROS_DOMAIN_ID="$ROS_DOMAIN_ID" ROS_LOG_DIR="$ROS_RUNTIME_LOG_DIR" \
  ros2 launch so101_bringup real_bringup.launch.py \
  enable_rosbridge:=false \
  use_mock_yolo:=false \
  >"$LAUNCH_LOG" 2>&1 &
LAUNCH_PID="$!"

for _ in $(seq 1 25); do
  if grep -q "Task executor ready" "$LAUNCH_LOG"; then
    break
  fi
  sleep 1
done

if ! grep -q "Task executor ready" "$LAUNCH_LOG"; then
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

REQUEST_ID="req-r2c-${STAMP}"
ORDER_ID="order-r2c-${STAMP}"
COMMAND_JSON="{\"requestId\":\"${REQUEST_ID}\",\"orderId\":\"${ORDER_ID}\",\"actionTemplateId\":\"pick_place_default\",\"params\":{}}"

ROS_DOMAIN_ID="$ROS_DOMAIN_ID" ros2 topic pub --once /mes_task_cmd std_msgs/msg/String \
  "{data: '${COMMAND_JSON}'}" >"$PUB_LOG" 2>&1

wait "$CAPTURE_PID"

if ! grep -Eq '"code":[[:space:]]*"STARTED"' "$STATUS_LOG"; then
  echo "missing STARTED in $STATUS_LOG" >&2
  exit 1
fi

STEP_COUNT="$(grep -Eo '"code":[[:space:]]*"STEP"' "$STATUS_LOG" | wc -l | tr -d ' ')"
if [[ "$STEP_COUNT" -lt 8 ]]; then
  echo "expected at least 8 STEP events, got $STEP_COUNT" >&2
  exit 1
fi

if ! grep -Eq '"code":[[:space:]]*"OK"' "$STATUS_LOG"; then
  echo "missing OK in $STATUS_LOG" >&2
  exit 1
fi

if ! grep -q '"joint_names"' "$TRAJ_LOG"; then
  echo "missing joint trajectory publish in $TRAJ_LOG" >&2
  exit 1
fi

cat >"$SUMMARY_MD" <<EOF
# R2C-003 验证记录（${STAMP}）

## 执行命令

\`\`\`bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
bash tools/e2e/verify_r2c003_flow.sh
\`\`\`

## 运行参数

- \`ROS_DOMAIN_ID=${ROS_DOMAIN_ID}\`
- launch: \`ros2 launch so101_bringup real_bringup.launch.py enable_rosbridge:=false use_mock_yolo:=false\`
- command requestId: \`${REQUEST_ID}\`
- command actionTemplateId: \`pick_place_default\`

## 验证结论

- \`/mes_task_cmd\` 成功触发 \`task_executor\`
- \`/joint_trajectory_controller/joint_trajectory\` 捕获到至少一条 \`JointTrajectory\`
- \`/mes_task_status\` 捕获到完整状态流：
  - \`STARTED\`
  - \`STEP x${STEP_COUNT}\`
  - \`OK\`

## 证据文件

- launch log:
  - \`docs/evidence/$(basename "$LAUNCH_LOG")\`
- status log:
  - \`docs/evidence/$(basename "$STATUS_LOG")\`
- trajectory log:
  - \`docs/evidence/$(basename "$TRAJ_LOG")\`
- publish log:
  - \`docs/evidence/$(basename "$PUB_LOG")\`
- capture log:
  - \`docs/evidence/$(basename "$CAPTURE_LOG")\`

## 关键摘要

- step_count: \`${STEP_COUNT}\`
- trajectory_topic: \`/joint_trajectory_controller/joint_trajectory\`
- status_topic: \`/mes_task_status\`
EOF

echo "summary: $SUMMARY_MD"
echo "status_log: $STATUS_LOG"
echo "trajectory_log: $TRAJ_LOG"
echo "publish_log: $PUB_LOG"
echo "capture_log: $CAPTURE_LOG"
