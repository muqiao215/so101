# SO101 Episode Closure Plan

更新时间：2026-04-09

## 1. 目标

把当前 leader-only 链路从：

- 输入可视化
- waypoint 草稿生成

推进到：

- episode 录制
- episode 回放校验
- episode 数据资产沉淀

这一阶段的核心不是再做“能看”的结果，而是把系统推进到：

- 能录
- 能回放
- 能比较
- 能追溯
- 能复用

## 2. 当前前提

### 已完成

- `LDR-003` 第一阶段已打通：
  - leader 录制器
  - `start/stop/status/watch`
  - JSONL 原始录制
  - `stable/dense` 两种 waypoint 提取
  - 草稿合并回正式 `waypoints.yaml` 的 CLI
- 当前已经具备：
  - `docs/generated/leader-recordings/*.jsonl`
  - `docs/generated/leader-recordings/*.meta.json`
  - `docs/generated/leader-waypoints/*.waypoints.yaml`
  - `docs/generated/leader-waypoints/*.waypoints.summary.json`

### 未收口

- `LDR-001`
  - leader 标定复核
  - 真实 `/leader/joint_states` 稳定性复测
- `LDR-002`
  - RViz 镜像联动验收
  - 输入到虚拟模型的 joint mapping / 方向 / 零位一致性确认
- `CAL-002`
  - 当前仍为 `in_progress`

### 当前判断

现在还不能直接把“episode 数据资产”当作主产物，因为输入可信度还没正式收口。

最合理的执行顺序是：

1. 先收口输入可信度
2. 再推进 episode 级闭环

## 3. 进入 Episode 阶段的前置条件

以下三条全部满足，才算正式进入 episode 阶段：

### `P0` 完成 leader 标定复核

要求：

- `tools/hardware/run_calibrate_so101_leader.sh` 已完成一轮有效标定
- 标定结果已在当前环境稳定复用
- 标定后重新启动 bridge，不出现明显姿态漂移或轴向翻转

证据：

- 标定执行记录
- 复测命令
- 关键结果写入 `docs/进度日志.md`

### `P1` 确认 `/leader/joint_states` 连续稳定

要求：

- 连续运行至少 `60s`
- 无明显关节顺序错误
- 无明显跳变
- 无高频丢帧导致的状态断裂
- 实测采样频率稳定在目标范围附近

建议验证口径：

- 运行 leader bridge
- 启动 recorder
- 连续录制 `60s`
- 检查：
  - `frame_count`
  - `sample_rate_hz`
  - `invalid_frame_count`
  - `joint_name_mismatch_count`
  - `non_monotonic_stamp_count`

证据：

- `docs/generated/leader-recordings/*.jsonl`
- `docs/generated/leader-recordings/*.meta.json`

### `P2` 完成 RViz 镜像联动验收

要求：

- 手掰 leader 时，虚拟 SO101 连续跟随
- joint mapping 一致
- 方向一致
- 零位理解一致
- 至少完成一轮“home 附近 -> 中间姿态 -> 另一姿态 -> 返回”的人工验收

证据：

- 验收记录写入 `docs/进度日志.md`
- 若有必要，补截图或录屏

### 前置条件结论

`P0/P1/P2` 任一未过，都不算进入正式 episode 阶段。

## 4. 新阶段交付物

### `EP-001` 连续轨迹 episode 录制

目标：

- 录完整时间序列，而不是只录关键帧

最小记录字段：

- `timestamp`
- `leader_joint_positions`
- `leader_joint_names`
- `sim_target_positions`
- `gripper_state`
- `task_phase`
- `recording_metadata`
- `source_mode`
- `session_id`
- `operator`
- `note`

建议文件：

- `src/so101_bringup/scripts/leader_episode_recorder.py`
- `src/so101_bringup/launch/leader_episode_session.launch.py`
- `src/so101_bringup/test/test_leader_episode_recorder.py`
- `tools/hardware/run_leader_episode_session.sh`
- `tools/hardware/control_leader_episode.sh`

建议输出目录：

- `docs/generated/leader-episodes/<episode_id>/episode.jsonl`
- `docs/generated/leader-episodes/<episode_id>/episode.meta.json`

### `EP-002` Replay Validator

目标：

- 验证录下来的内容能稳定重放

必须支持两种回放：

1. 原始高频 episode 回放到 simulated arm
2. 由 episode 压缩出来的 waypoint 草稿回放到 simulated arm

最小输出指标：

- 总时长
- 总帧数
- 丢帧数
- 回放时延
- 关节误差统计
- 回放结果

建议文件：

- `src/so101_bringup/scripts/leader_episode_replay.py`
- `src/so101_bringup/scripts/leader_waypoint_replay.py`
- `src/so101_bringup/test/test_leader_episode_replay.py`
- `tools/hardware/replay_leader_episode.sh`
- `tools/hardware/replay_leader_waypoints.sh`

建议输出目录：

- `docs/generated/leader-episodes/<episode_id>/replay-raw.json`
- `docs/generated/leader-episodes/<episode_id>/replay-waypoints.json`

### `EP-003` Episode Dataset Schema

目标：

- 把录制结果从“散乱 JSONL 文件”升级成统一数据资产

最小 schema 字段：

- `episode_id`
- `task_name`
- `created_at`
- `operator`
- `source_mode`
- `robot_profile`
- `calibration_version`
- `raw_record_path`
- `draft_waypoint_path`
- `merged_waypoint_version`
- `replay_raw_result_path`
- `replay_waypoint_result_path`
- `notes`

建议文件：

- `tools/hardware/episode_manifest.py`
- `tools/hardware/test_episode_manifest.py`

建议输出：

- `docs/generated/leader-episodes/<episode_id>/manifest.json`

## 5. 非目标

本阶段明确不做：

- `so101_follower` 真机执行闭环
- 把 leader 伪装成真实执行臂
- 复杂前端扩展
- 额外视觉融合扩写
- 真实抓取执行闭环
- 首页或展示层改版

## 6. 验收标准

本阶段完成的判定条件：

1. 能稳定录制一个 `10s ~ 30s` 的 leader 操作 episode
2. 能从该 episode 自动生成 waypoint 草稿
3. 能完成一次原始 episode replay，并输出校验结果
4. 能完成一次 waypoint replay，并输出校验结果
5. 能为 episode 生成统一 manifest
6. 能根据 episode 追溯到 calibration 版本和配置来源

## 7. 任务拆分

为避免继续把所有工作塞进 `LDR-003`，本阶段新增独立任务编号：

### `EP-001` Episode Recorder Schema

目标：

- 定义 episode 原始记录字段与最小 JSONL 结构

建议文件：

- `docs/generated/leader-episodes/README.md`
- `tools/hardware/episode_manifest.py`

验收：

- 字段定义固定
- 至少一份样例通过校验

### `EP-002` Episode Recorder File Layout

目标：

- 固化 episode 目录布局、命名规则和元数据输出

建议文件：

- `src/so101_bringup/scripts/leader_episode_recorder.py`
- `src/so101_bringup/test/test_leader_episode_recorder.py`
- `tools/hardware/run_leader_episode_session.sh`

验收：

- 单次录制可生成完整 episode 目录

### `EP-003` Replay Validator

目标：

- 验证 raw replay / waypoint replay 均成立

建议文件：

- `src/so101_bringup/scripts/leader_episode_replay.py`
- `src/so101_bringup/scripts/leader_waypoint_replay.py`
- `src/so101_bringup/test/test_leader_episode_replay.py`

验收：

- 至少一个 episode 可完成两种 replay
- 能输出误差、时延、结果

### `EP-004` Episode Manifest And Metadata

目标：

- 形成统一的 episode manifest

建议文件：

- `tools/hardware/episode_manifest.py`
- `tools/hardware/test_episode_manifest.py`

验收：

- manifest 可追溯到：
  - 原始录制
  - waypoint 草稿
  - replay 结果
  - calibration 版本

### `EP-005` Regression Demo

目标：

- 固化一个可重复执行的 demo episode

建议文件：

- `tools/hardware/run_episode_regression_demo.sh`
- `docs/evidence/EP-005_*.md`

验收：

- 同一条 demo 能重复录制、重复回放、重复比较

## 8. 推荐执行顺序

严格按顺序，不跳步：

1. 收口 `P0`
   - leader 标定复核
2. 收口 `P1`
   - `/leader/joint_states` 稳定性复测
3. 收口 `P2`
   - RViz 镜像联动验收
4. 开始 `EP-001`
5. 再做 `EP-002`
6. 再做 `EP-003`
7. 最后做 `EP-005`

## 9. 立即下一步

不是直接做 dataset，不是继续做展示层，而是先把输入可信度补齐：

1. 完成 leader 标定复核
2. 复测 `/leader/joint_states`
3. 完成 RViz 镜像联动验收

这三条完成后，再正式进入 episode 闭环实现。

## 10. 与现有任务板的关系

当前阶段建议这样理解：

- `LDR-001`
  - 负责输入可信度基础
- `LDR-002`
  - 负责映射可信度基础
- `LDR-003`
  - 负责从录制器升级到 episode 主线
- `LDR-004`
  - 后续可自然吸收 `episode dataset` 资产

在任务板层面，`EP-*` 作为 `LDR-003` 之后的新细分任务，不替代 `LDR-001/LDR-002` 的前置地位。
