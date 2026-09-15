# SO101 Real Leader to Gazebo and Training Plan

更新时间：2026-04-26

## 1. 当前判断

下一阶段主线应先打通：

```text
真实 leader 主臂 -> /leader/joint_states -> Gazebo simulated arm -> recorder -> validator -> manifest
```

但在没有 follower 真机时，视觉不能停滞。视觉应作为并行主线推进：

```text
Gazebo RGB camera -> simulated detector / YOLO -> /detections -> backend/frontend/task trigger
```

当前不建议让视觉闭环抓取抢占主线，但建议先补齐 Gazebo 图像源、仿真检测、前后端显示和数据采集入口。原因是这条链不依赖 follower 真机，可以并行产生资产。

## 2. 已有基础

当前已经具备：

- 前端对应仿真链：
  - 前端可启动/观察 Gazebo、RViz 和 runtime 状态。
  - `runtimeTarget=simulation` 已能区分仿真与真机路径。
- 实物主臂对应 RViz 链：
  - 已有 `/leader/joint_states -> /joint_states` 镜像节点。
  - 已有 RViz mirror/replay 入口。
- leader-only episode 软件链：
  - JSONL recorder。
  - replay validator v2。
  - source episode quality gate。
  - L1 headless replay。
  - manifest 与 replay diagnostics。
- 视觉软件链：
  - `yolov8_detector` 已能订阅 `/camera/color/image_raw` 并发布 `/detections`。
  - mock detector、后端 rosbridge `/detections` 订阅、前端视觉控制台和 task trigger 已存在。
  - 2026-04-26 已新增 Gazebo 固定俯视 RGB camera 与仿真颜色检测节点。
- 已验证的关键结论：
  - L1 replay 链路可以通过。
  - 失败样本可被拆成源数据不合格和 replay 链路失败。
  - `source_quality_failed` 已能识别 joint limit 与 velocity limit 问题。

## 3. 下一阶段目标

把“实物主臂只到 RViz”推进到“实物主臂实时驱动 Gazebo”。

最小目标：

- 真实 leader 主臂动作能让 Gazebo 中的 simulated SO101 跟随。
- 输入经过 joint mapping、限位、速度门槛检查。
- Gazebo 跟随结果可以录制为 episode。
- 录制结果可以通过 validator 与 manifest 进入资产链。

## 4. 非目标

本阶段不做：

- follower 真机执行。
- 视觉闭环抓取。
- 复杂相机/深度/多传感器融合。
- 大规模模型训练。
- VLA/GR00T 正式微调。
- 前端大改版。

本阶段允许并行做：

- Gazebo RGB camera。
- Gazebo 红/蓝目标检测。
- `/detections` 到前端/后端/任务触发的仿真验证。
- 视觉数据采集与后续训练资产准备。

## 5. 新任务拆分

### `RLG-001` real leader to Gazebo bridge

目标：

- 新增一个最小桥接节点，将 `/leader/joint_states` 转成 Gazebo controller 可消费的轨迹/目标。

建议实现：

- `src/so101_bringup/scripts/leader_to_gazebo_bridge.py`
- `src/so101_bringup/launch/leader_to_gazebo.launch.py`
- `src/so101_bringup/test/test_leader_to_gazebo_bridge.py`

输入：

- `/leader/joint_states`

输出候选：

- `/joint_trajectory_controller/joint_trajectory`
- 或 `FollowJointTrajectory` action

第一版建议：

- 先用 `FollowJointTrajectory` action。
- 每次发送短 horizon point。
- 限制发布频率，避免把 leader 噪声逐帧硬灌进 controller。

验收：

- 无实物时可用历史 leader recording replay 驱动。
- 有实物时手掰 leader，Gazebo arm 可连续跟随。
- action result 不长期 timeout。

### `RLG-002` source quality gate for live leader stream

目标：

- 把已实现的 `source_episode_quality_gate.py` 从离线 JSONL 扩展到 live stream 的同类口径。

要求：

- 对 `/leader/joint_states` 做实时限位检查。
- 对相邻帧估算 velocity。
- 超限时输出 warning/status，不直接让不合格目标进入 Gazebo。

建议输出：

- `/leader/gazebo_bridge/status`
- `source_quality_status`
- `limit_violation_count`
- `velocity_violation_count`
- `last_rejected_joint`

验收：

- 人为输入超限录制片段时，bridge 能拒绝或 clamp。
- status 能明确区分 `passed / source_quality_failed / degraded`。

### `RLG-003` real leader driven L1 episode run

目标：

- 将真实 leader 驱动 Gazebo 的过程录制成 episode。

最小产物：

- `source-quality.json`
- `leader-driven-gazebo-recording.jsonl`
- `replay-raw.json`
- `replay-diagnostics.json`
- `manifest.json`
- `l1-real-leader-gazebo-summary.json`

验收：

- 能完成一个 10 到 30 秒的真实 leader 驱动 Gazebo episode。
- manifest 能追溯到 calibration、URDF、source quality report。
- validator 能输出 passed/soft_failed/hard_failed/source_quality_failed。

### `RLG-004` frontend runtime mode exposure

目标：

- 前端不扩功能，只补一个明确运行模式入口：

```text
simulation
real_hardware
real_leader_to_gazebo
```

要求：

- 只展示状态与启动入口。
- 不做新大屏、不做复杂 3D。

验收：

- 用户能从前端选择“实物主臂驱动仿真”。
- backend 启动对应脚本。
- 页面显示 bridge/gazebo/rviz/quality status。

### `GZV-001` Gazebo RGB camera source

目标：

- Gazebo workcell 自带一个稳定 ROS camera，不再只有 GUI camera。

已实现：

- `src/so101_gazebo/worlds/so101_workcell.world`
- 新增 `overhead_vision_camera`。
- 发布口径：
  - `/camera/color/image_raw`
  - `/camera/color/camera_info`

验收：

- `bash tools/e2e/start_sim_vision_stack.sh` 可启动 Gazebo 视觉核心。
- `.vscode/.runtime/so101_visible_ros.log` 出现 `Publishing camera info to [/camera/color/camera_info]`。

### `GZV-002` simulated detector lane

目标：

- 没有训练模型或真实相机时，仍可用 Gazebo 场景红/蓝目标驱动 `/detections`。

已实现：

- `src/so101_bringup/scripts/sim_color_detector_node.py`
- `src/so101_bringup/test/test_sim_color_detector.py`
- `sim_bringup.launch.py` 新增：
  - `use_gazebo_color_detector`
  - `use_real_yolo`
  - `camera_image_topic`
  - `detections_topic`
  - `yolo_model_path`
  - `yolo_device`

启动：

```bash
bash tools/e2e/stop_visible_demo_stack.sh
bash tools/e2e/start_sim_vision_stack.sh
```

验收：

- 单测 `python3 -m unittest src/so101_bringup/test/test_sim_color_detector.py -v` 通过。
- `colcon build --packages-select so101_gazebo so101_bringup yolov8_detector` 通过。

### `GZV-003` vision-to-robot target bridge

目标：

- 把检测结果从“像素框”推进到“桌面目标候选”。

待实现：

- 相机 frame / TF 约定。
- camera_info 保存。
- pixel center 到 table plane 的简化投影。
- 输出 `/vision/targets` 或扩展 `/detections` payload。

### `GZV-005` to `GZV-008` vision dataset lane

目标：

- 将 Gazebo 图像、检测、episode 时间轴对齐，为后续 LeRobot/视觉训练准备资产。

已完成：

- `GZV-005` 采集 image metadata/snapshots、detections、vision targets、task status、joint states。
- `GZV-007` 验证 episode manifest、events、关键流计数、时间轴和快照文件。
- `GZV-008` 生成训练前置中间格式：`dataset-index.json` + `samples.jsonl`。
- `GZV-008` 以 image snapshot 为样本锚点，对齐 detection、vision target、joint_state、task_status，并暴露每条样本的时间偏差。
- `GZV-009` 生成 LeRobot 前置 candidate 包，默认将 `warn` 样本分流到 debug，不进入 train。
- `GZV-010` 将同步质量前移到采集端：关键流未就绪或已过期时不保存 image snapshot，并区分高频视觉/关节阈值与低频 task status 阈值。
- `GZV-011` 为 `/mes_task_status` 增加 heartbeat，复发最后状态并刷新 `ts`，让视觉 episode 持续具备任务上下文。
- `GZV-012` 前端对 `heartbeat=true` 降噪：保持状态新鲜，但不刷系统事件流和状态时间线。

下一步：

- 原生 LeRobot v3 dataset 已由 `TRN-002` 跑通，环境口径固定为 `UV_HTTP_TIMEOUT=300 env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 uv run --isolated ...`，不要再走显式 venv；踩坑记录见 `docs/plans/2026-04-27-lerobot-uvrun-native-export-notes.md`。
- 如果要训练动作策略，必须补 follower action 或仿真执行动作标签；当前 candidate 的 `action` 只是 `vision_target_xyz`，不是执行臂关节动作。
- 如果后续需要更细采集质量可视化，在开发工作台增加 dataset validation / train-debug-rejected 面板。

## 6. WSL / Windows / GPU 策略

当前机器是 Windows + WSL2，GPU 为 NVIDIA GeForce RTX 3050 Laptop GPU。

建议分工：

### WSL 默认承担

- ROS 2 节点开发。
- Gazebo headless/server-first 仿真。
- replay validator。
- episode manifest。
- 数据清洗与格式转换。
- 小规模 smoke test。

### Windows 原生优先承担

- 需要稳定 GUI/GPU 的 Gazebo/RViz 可视化。
- 需要调用 Windows 侧驱动、USB、相机工具时。
- 未来如果接 Isaac/更重仿真，可优先考虑 Windows 原生或云端。

### 本机 RTX 3050 Laptop GPU 适合

- 推理验证。
- dataset viewer。
- 小 batch smoke training。
- ONNX/TensorRT 或轻量模型部署验证。
- 训练脚本能否跑通的最小检查。

### 本机 RTX 3050 Laptop GPU 不适合

- 大规模 imitation learning 正式训练。
- 多相机视频策略训练。
- VLA/GR00T 类大模型微调。
- 长时间高显存实验。

## 7. 训练策略

训练主线不应现在抢主线，但需要提前定路线。

### 短期：只跑数据链

目标：

- 把本项目 episode schema 对齐 LeRobot 数据结构。
- 用公开 SO101/LeRobot 数据集跑通 loader。
- 本机只跑 1 到 2 个 episode 的 smoke training。

### 中期：云端训练

推荐优先级：

1. Colab Pro/Pro+
   - 上手快。
   - 适合跑 LeRobot 示例、公开 SO101 数据、轻量微调。
2. RunPod
   - 适合固定 GPU、长时间训练、环境可控。
3. Google Cloud
   - 适合工程化训练与长期资产管理。
   - 配置与成本控制更复杂。

### 训练闭环

建议闭环：

```text
本机采集/清洗/校验 episode
  -> 转 LeRobot dataset
  -> 云端训练
  -> 下载 checkpoint
  -> 本机 L1/L2 replay 或仿真评估
  -> 最后再接 follower
```

## 8. 进入训练前的硬门槛

以下未完成前，不建议正式训练：

- `P0` leader 标定复核通过。
- `P1` `/leader/joint_states` 60 秒稳定复测通过。
- `P2` RViz 镜像验收通过。
- `RLG-001` 实物主臂可驱动 Gazebo。
- `source_quality_failed` 可稳定阻断坏样本。
- 至少 5 条合格 episode 能 replay passed 或 soft_failed。

## 9. 两周执行顺序

### Week 1

1. 实现 `RLG-001` 最小 bridge。
2. 用离线 leader recording replay 驱动 Gazebo，先不依赖真机。
3. 接入 source quality gate。
4. 产出第一条 `real_leader_to_gazebo` 等价的离线 L1 episode。

### Week 2

1. 真机恢复后跑真实 leader -> Gazebo。
2. 录制 3 到 5 条短 episode。
3. 固化 manifest 与 replay 结果。
4. 前端只补运行模式入口。
5. 开始 LeRobot 数据格式对齐，不做正式训练。

## 10. 当前结论

下一步代码工作应从 `RLG-001` 开始。

训练暂不进入主线，先作为并线规划：

- 本机负责数据、验证、推理、smoke。
- Colab/RunPod/Google Cloud 负责正式训练。
