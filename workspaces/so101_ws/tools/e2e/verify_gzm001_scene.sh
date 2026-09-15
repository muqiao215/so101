#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVIDENCE_DIR="$ROOT_DIR/docs/evidence"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime/gzm001"

STAMP="$(date +%Y%m%d%H%M%S)"
ROS_DOMAIN_ID_VALUE="${ROS_DOMAIN_ID_VALUE:-81}"
ROS_RUNTIME_LOG_DIR="$RUNTIME_DIR/ros_logs"

LAUNCH_LOG="$EVIDENCE_DIR/gzm-001-launch-${STAMP}.log"
CAPTURE_LOG="$EVIDENCE_DIR/gzm-001-capture-${STAMP}.log"
MODELS_LOG="$EVIDENCE_DIR/gzm-001-models-${STAMP}.log"
TF_LOG="$EVIDENCE_DIR/gzm-001-tf-${STAMP}.log"
SUMMARY_MD="$EVIDENCE_DIR/GZM-001_验证记录_${STAMP}.md"

mkdir -p "$EVIDENCE_DIR" "$RUNTIME_DIR" "$ROS_RUNTIME_LOG_DIR"

cleanup() {
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
  ros2 launch so101_gazebo scene.launch.py use_gzclient:=false \
  >"$LAUNCH_LOG" 2>&1 &
LAUNCH_PID="$!"

for _ in $(seq 1 45); do
  if grep -q "Spawn status: SpawnEntity: Successfully spawned entity \\[so101\\]" "$LAUNCH_LOG" &&
     grep -q "Loaded gazebo_ros2_control." "$LAUNCH_LOG"; then
    break
  fi
  sleep 1
done

if ! grep -q "Spawn status: SpawnEntity: Successfully spawned entity \\[so101\\]" "$LAUNCH_LOG"; then
  echo "spawn_entity did not succeed" >&2
  exit 1
fi

if ! grep -q "Loaded gazebo_ros2_control." "$LAUNCH_LOG"; then
  echo "gazebo_ros2_control did not load" >&2
  exit 1
fi

{
  for model in work_table pick_bin place_bin so101; do
    echo "--- ${model} ---"
    gz model -m "$model" -p
  done
} >"$MODELS_LOG" 2>&1

grep "robot_state_publisher]: got segment" "$LAUNCH_LOG" >"$TF_LOG" || true

for model in work_table pick_bin place_bin so101; do
  if ! grep -q -- "--- ${model} ---" "$MODELS_LOG"; then
    echo "missing model ${model} in $MODELS_LOG" >&2
    exit 1
  fi
done

for frame in base_link shoulder_link upper_arm_link wrist_link gripper_frame_link; do
  if ! grep -q "got segment ${frame}" "$TF_LOG"; then
    echo "missing TF segment ${frame} in $TF_LOG" >&2
    exit 1
  fi
done

cat >"$SUMMARY_MD" <<EOF
# GZM-001 验证记录（${STAMP}）

## 执行命令

\`\`\`bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
bash tools/e2e/verify_gzm001_scene.sh
\`\`\`

## 运行参数

- \`ROS_DOMAIN_ID=${ROS_DOMAIN_ID}\`
- launch: \`ros2 launch so101_gazebo scene.launch.py use_gzclient:=false\`

## 验证结论

- Gazebo headless 场景启动成功
- \`spawn_entity\` 成功生成 \`so101\`
- \`gazebo_ros2_control\` 成功加载
- Gazebo CLI 已查询到实体：
  - \`work_table\`
  - \`pick_bin\`
  - \`place_bin\`
  - \`so101\`
- \`robot_state_publisher\` 日志已覆盖关键 frame：
  - \`base_link\`
  - \`shoulder_link\`
  - \`upper_arm_link\`
  - \`wrist_link\`
  - \`gripper_frame_link\`

## 证据文件

- launch log:
  - \`docs/evidence/$(basename "$LAUNCH_LOG")\`
- models log:
  - \`docs/evidence/$(basename "$MODELS_LOG")\`
- tf log:
  - \`docs/evidence/$(basename "$TF_LOG")\`
EOF

echo "summary: $SUMMARY_MD"
echo "launch_log: $LAUNCH_LOG"
echo "models_log: $MODELS_LOG"
echo "tf_log: $TF_LOG"
