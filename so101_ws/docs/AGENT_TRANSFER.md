# SO101 Agent Transfer

更新时间：2026-04-09

## 1. 当前阶段

- 当前主线：真机第一轮
- 当前真机对象：仅主臂
- 当前优先口径：
  - 以 `docs/任务清单.md` 与 `docs/进度日志.md` 为准
  - 本文件只做简要交接摘要
- 当前边界：
  - 不做首页重构
  - 不做高级模式重设计
  - 不做 YOLO 大改
  - 不做轨迹工作台新功能
  - 前端只保留最小真机状态展示

## 2. 当前新判断

- 当前工程已经不该继续围绕“展示层补洞”推进
- 当前最该做的是：
  - 先收口输入可信度
  - 再推进 episode 级闭环
- 新规划文件：
  - `docs/plans/2026-04-09-episode-closure.md`

### 为什么

- `LDR-003` 已经证明 leader 输入链是通的：
  - 能录
  - 能提 waypoint 草稿
  - 能合并回正式配置
- 但 `LDR-001` / `LDR-002` / `CAL-002` 还没完全收口
- 所以后续不能直接把“episode 数据集”建立在尚未正式验收的输入质量上

## 3. 已完成到什么程度

### 已收住的部分

- 主臂 WSL 串口接入：
  - `/dev/ttyUSB0`
- runtime 状态刷新：
  - `tools/hardware/refresh_main_arm_runtime_state.sh`
- watcher 保活：
  - `tools/hardware/watch_main_arm_runtime_state.sh`
  - 已修复“一次性命令会话退出后 watcher 跟着死掉”的问题
- 本地校准文件工作流：
  - `tools/hardware/real_hardware_calibration.local.json`
  - 未传 `--profile` 时默认读取本地文件
- preflight：
  - `tools/hardware/check_real_hardware_preflight.py`
  - 当前已经达到：
    - `statusFresh=true`
    - `online=true`
    - `powerState=已上电`
    - `calibrationValid=true`
    - `homed=true`
    - `allowExecute=false`
    - `commandExecutionEnabled=false`
    - `gateReasonCode=HWS_002_PENDING`
- 安全证据入口：
  - `tools/hardware/collect_real_hardware_safety_evidence.py`
  - 已生成：
    - `.vscode/.runtime/real_hardware_safety_evidence.json`

### 当前结论

- 现在不是“链路不通”
- 也不是“校准缺失”
### 新增已收住部分

- leader-only 链路已推进到：
  - `leader_state_recorder`
  - `control_leader_recording.sh`
  - JSONL -> waypoint 草稿
  - `stable/dense` 提取
  - 草稿合并回 `src/so101_bringup/config/waypoints.yaml`

### 当前结论

- 当前已经不是“链路没通”
- 也不是“只能看 RViz”
- 当前真正的主线是：
  - 先完成 `LDR-001` / `LDR-002` / `CAL-002` 的收口
  - 再进入 `episode` 阶段

## 4. 当前最关键文件

### 看板与日志

- `docs/任务清单.md`
- `docs/进度日志.md`
- `docs/plans/2026-04-09-episode-closure.md`

### 串口/接入

- `tools/hardware/attach_main_arm_com4_to_wsl.sh`
- `tools/hardware/export_main_arm_serial_status.py`
- `tools/hardware/refresh_main_arm_runtime_state.sh`
- `tools/hardware/watch_main_arm_runtime_state.sh`
- `tools/hardware/main_arm_runtime_watch_status.sh`

### leader-only 主线

- `src/so101_bringup/scripts/so101_leader_input_bridge.py`
- `src/so101_bringup/scripts/leader_joint_state_mirror.py`
- `src/so101_bringup/scripts/leader_state_recorder.py`
- `tools/hardware/leader_recording_ctl.py`
- `tools/hardware/leader_recording_to_waypoints.py`
- `tools/hardware/merge_leader_waypoints_into_config.py`

### 校准

- `tools/hardware/real_hardware_calibration.py`
- `tools/hardware/validate_real_hardware_calibration.py`
- `tools/hardware/sync_real_hardware_calibration.py`
- `tools/hardware/real_hardware_calibration.local.json`

### 预检与证据

- `tools/hardware/real_hardware_preflight.py`
- `tools/hardware/check_real_hardware_preflight.py`
- `tools/hardware/real_hardware_safety_evidence.py`
- `tools/hardware/collect_real_hardware_safety_evidence.py`

### 前端真机状态

- `mes_frontend/src/lib/realHardwareStatus.js`
- `mes_frontend/src/components/RealHardwareStatusCard.vue`
- `mes_frontend/src/lib/__tests__/realHardwareStatus.test.js`

## 5. 立即下一步

按顺序做，不要跳：

1. 完成 `LDR-001`
   - leader 标定复核
   - `/leader/joint_states` 连续稳定复测
2. 完成 `LDR-002`
   - RViz 镜像联动验收
3. 完成 `CAL-002` 当前阶段收口
4. 然后按 `docs/plans/2026-04-09-episode-closure.md` 进入：
   - `EP-001`
   - `EP-002`
   - `EP-003`

## 6. 立即不要做

- 不要继续围着展示层打转
- 不要再把 leader-only 主线理解成“伪执行臂”
- 不要直接跳到 episode 数据集，而跳过输入可信度收口
- 不要把 `AGENT_TRANSFER.md` 当作唯一最新事实来源

## 7. 下一阶段目标

在 `LDR-001` / `LDR-002` / `CAL-002` 收口后，进入：

- leader-only episode 闭环：
  - 连续录制
  - replay 校验
  - dataset schema
