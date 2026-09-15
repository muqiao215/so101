# SO101 Leader Input Bridge Design

更新时间：2026-04-07

## 1. 目标

设计一个最小而正确的 `so101_leader_input_bridge`，把单只 `so101_leader` 稳定接入当前 ROS2 工作区。

这个节点的职责只有一个：

- 把 leader 可靠地变成 ROS 世界里的输入设备

这个节点**不负责**：

- 驱动 leader 主动运动
- 录制逻辑
- waypoint 生成
- 仿真镜像逻辑
- 工单执行

这些都应该作为 bridge 的下游消费者独立实现。

## 2. 设计结论

推荐采用：

- 单节点
- 只读
- Python
- 不引入自定义 ROS msg

节点名：

- `so101_leader_input_bridge`

包内建议位置：

- `src/so101_bringup/scripts/so101_leader_input_bridge.py`

推荐原因：

- 当前仓库已有 Python ROS2 节点模式
- 当前阶段不需要自定义接口复杂化系统
- 先把设备输入桥打稳，比同时做录制、镜像、模板生成更重要

## 3. 接口定义

### 3.1 Topics

#### `/leader/joint_states`

类型：

- `sensor_msgs/msg/JointState`

用途：

- 标准 ROS 关节状态输出
- 给 RViz、仿真镜像、前端、录制器、后续 waypoint 生成器使用

字段约定：

- `header.stamp`
  - bridge 采样时间
- `name`
  - 使用当前 SO101 统一关节名
- `position`
  - leader 当前关节角
- `velocity`
  - 当前阶段可留空
- `effort`
  - 当前阶段可留空

建议 joint 顺序：

- `shoulder_pan`
- `shoulder_lift`
- `elbow_flex`
- `wrist_flex`
- `wrist_roll`
- `gripper`

#### `/leader/raw_state`

类型：

- `std_msgs/msg/String`

用途：

- 原始设备状态
- 调试、回放、排障
- 暂不追求跨节点语义优雅，优先保真和快速落地

载荷格式：

- JSON string

建议字段：

- `deviceType`
- `port`
- `connected`
- `calibrated`
- `jointNames`
- `jointPositionsRaw`
- `jointPositionsRad`
- `readLatencyMs`
- `frameId`
- `seq`
- `timestamp`
- `lastError`

#### `/leader/status`

类型：

- `std_msgs/msg/String`

用途：

- 人类可读健康状态
- 前端和脚本快速读取

载荷格式：

- JSON string

建议字段：

- `state`
  - `BOOTING | DISCONNECTED | CALIBRATING | READY | DEGRADED | ERROR`
- `connected`
- `calibrated`
- `publishing`
- `hz`
- `lastFrameAgeMs`
- `lastError`
- `deviceLabel`

### 3.2 Parameters

最小参数集：

- `leader_type`
  - 默认：`so101_leader`
- `port`
  - 默认空；优先使用自动发现
- `publish_rate_hz`
  - 默认：`30.0`
- `joint_names`
  - 默认使用 SO101 六轴顺序
- `use_sim_time`
  - 默认：`false`
- `calibration_path`
  - 默认空；由底层库默认规则处理
- `raw_state_enabled`
  - 默认：`true`
- `status_topic_enabled`
  - 默认：`true`

### 3.3 Services

bridge 最小版只保留一个：

- `/leader/reload_calibration`
  - 类型：`std_srvs/srv/Trigger`

作用：

- 重新加载标定文件
- 不在当前阶段做重新标定流程本身

不建议在 LDR-001 里加入：

- start/stop recording
- zero/reset pose
- send command

这些都应该留到后续节点。

## 4. 内部状态机

最小状态机：

### `BOOTING`

进入条件：

- 节点启动

出口：

- 能连接设备 -> `CALIBRATING` 或 `READY`
- 连接失败 -> `DISCONNECTED`

### `DISCONNECTED`

进入条件：

- 未找到设备
- 串口不可用
- 底层初始化失败

出口：

- 下次重试成功 -> `CALIBRATING` 或 `READY`

### `CALIBRATING`

进入条件：

- 设备可见，但底层报告未完成标定加载或标定无效

出口：

- 标定就绪 -> `READY`
- 标定失败 -> `ERROR`

### `READY`

进入条件：

- 设备连接成功
- 标定加载成功
- 连续读取正常

行为：

- 周期发布 `/leader/joint_states`
- 周期发布 `/leader/raw_state`
- 周期发布 `/leader/status`

出口：

- 连续读取抖动但未完全中断 -> `DEGRADED`
- 设备掉线 -> `DISCONNECTED`
- 明确异常 -> `ERROR`

### `DEGRADED`

进入条件：

- 读取延迟过高
- 丢帧
- 部分关节数据异常

行为：

- 继续发 `/leader/status`
- `/leader/joint_states` 可继续发最近一次有效值，但必须在状态里明确降级

出口：

- 恢复正常 -> `READY`
- 彻底失联 -> `DISCONNECTED`
- 明确异常 -> `ERROR`

### `ERROR`

进入条件：

- 底层报硬错误
- 标定文件不可解析
- joint 映射不一致

出口：

- 人工修正后重启节点
- 或调用 `reload_calibration` 恢复后回到 `CALIBRATING/READY`

## 5. 数据流

输入：

- `so101_leader` 设备读数
- 标定文件
- 串口/设备发现信息

bridge 输出：

- `/leader/joint_states`
- `/leader/raw_state`
- `/leader/status`

下游消费者：

- `leader_to_rviz_mirror`
- `leader_state_recorder`
- `leader_waypoint_generator`
- future `leader_to_gazebo_mirror`

## 6. 错误处理原则

- 只读桥绝不向硬件发送动作命令
- 设备断开时不要崩节点，进入 `DISCONNECTED`
- 数据降级时不要伪装成正常
- 标定问题单独显式报出，不混成一般串口错误
- `joint_states` 只发通过映射和单位转换后的稳定数据
- 原始异常留在 `/leader/raw_state` 与 `/leader/status`

## 7. 验收标准

### 最小验收

1. 节点能启动并输出明确状态
2. 设备连接成功时，`/leader/status` 进入 `READY`
3. `/leader/joint_states` 稳定发布 30Hz 左右
4. `name` 顺序固定、长度稳定
5. 手掰 leader 时，`position` 连续变化
6. 拔掉设备后，状态进入 `DISCONNECTED`
7. 不向硬件发送任何主动运动命令

### LDR-001 完成定义

- 上述最小验收全部通过
- 有一份 smoke 记录
- 有一段 10 秒 joint_states 录制样本
- 有一张 `ros2 topic echo /leader/joint_states --once` 证据

## 8. 推荐后续拆分

LDR-001 完成后，建议新增三个独立节点/工具：

- `leader_to_rviz_mirror`
  - 消费 `/leader/joint_states`
- `leader_state_recorder`
  - 负责录制和落盘
- `leader_waypoint_generator`
  - 负责把录制片段转成 waypoint/template 草稿

这样 bridge 永远只负责输入，不会膨胀成大杂烩。

## 9. 拒绝方案

### 方案 A：直接把 leader 当执行臂

拒绝原因：

- 与当前硬件角色不符
- 与官方抽象不符
- 会继续污染主线判断

### 方案 B：一开始就做 bridge + recorder + rviz mirror 一体化

拒绝原因：

- 失败时不好定位
- 分层不清
- 不利于 future follower 接入

### 方案 C：先定义自定义 ROS msg

拒绝原因：

- 现在收益太低
- 会放大迭代成本
- 当前阶段用 `JointState + JSON String` 足够

## 10. 下一步

实施顺序建议：

1. 实现 `so101_leader_input_bridge.py`
2. 增加最小 launch 入口
3. 补 node-level smoke test / manual smoke script
4. 再做 `LDR-002` 的 RViz 镜像
