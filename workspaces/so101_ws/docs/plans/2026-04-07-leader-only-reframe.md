# SO101 Leader-Only Reframe

更新时间：2026-04-07

## 1. 新判断

当前手头只有一只 `so101_leader`，没有 `so101_follower`。

结合当前仓库验证结果：

- 前端 -> backend -> rosbridge -> `task_executor`
- 状态流 `STARTED/STEP/OK`
- 订单最终 `DONE`

这些都已经能跑通。

但当前 `real_bringup.launch.py` 里并没有真实 follower 电机驱动或真实执行桥，所以这条链路只能证明：

- 工单链路通了
- 模板执行器通了
- 状态回传通了

不能证明：

- leader 本体已经作为真实执行臂完成动作

因此当前项目不能再继续以“单 leader = 真机执行臂”作为主假设。

## 2. 新定位

把当前硬件重新定义为：

- `so101_leader` = 输入设备 / 示教设备 / 遥操作设备

不再定义为：

- 真机执行机器人本体

项目主线从：

- 真机单工单闭环执行

改为：

- leader 输入端接入
- leader -> ROS2 状态桥
- leader -> 仿真臂 / RViz / UI 的示教链路
- 为未来 follower 接入保留兼容接口

## 3. 现有链路哪些还能直接利用

### 可以保留

- frontend 工单与状态 UI
- backend 订单、状态推送、实时流
- rosbridge 接入
- `task_executor` 模板与状态流逻辑
- `waypoints.yaml` 动作模板资产
- 真机状态卡与 runtime contract

### 需要改用途

- `/mes_task_cmd`
  - 不再默认解释为“真实执行臂开始动作”
  - 改成“驱动仿真执行器”或“驱动 leader-input 实验链”
- `E2E-HW-002`
  - 不再当作当前硬件前提下可完成的主线任务
  - 改成依赖 future follower 的 blocked 项

## 4. leader-only 可做的 4 条主线

### LDR-001 leader_input_bridge

目标：

- 读取 leader 各关节状态
- 统一发布为 ROS2 话题

建议输出：

- `/leader/joint_states`
- `/leader/raw_state`
- `/leader/health`

价值：

- 为 RViz、仿真、前端、录制统一提供输入源

### LDR-002 leader -> RViz / 仿真镜像

目标：

- 手掰 leader，屏幕里的虚拟 SO101 跟着动

实现方向：

- `/leader/joint_states` -> `joint_state_publisher` 或自定义 relay
- 在 RViz 或 Gazebo 中驱动虚拟 arm

价值：

- 立即形成可演示结果
- 验证 joint mapping、零位、方向、缩放和限位

### LDR-003 leader 教学录制 / 动作模板生成

目标：

- 从 leader 输入采样轨迹
- 生成 `waypoints.yaml` 兼容的关键帧或模板片段

输出：

- 新 waypoint 片段
- 新 action template 草稿
- 时间戳 + joint 序列日志

价值：

- 让 leader 真正成为“示教器”
- 当前仓库已有动作模板体系，可直接复用

### LDR-004 leader 数据采集 / imitation learning 前置研究

目标：

- 把 leader 变成数据采集端

内容：

- 关节状态流
- 操作时序
- 可选相机画面时间同步

价值：

- 即使没有 follower，也可以先把采集、标注、回放、可视化链路做出来

## 5. 推荐执行顺序

1. `LDR-001` leader_input_bridge
2. `LDR-002` leader -> RViz / Gazebo 镜像
3. `LDR-003` leader 教学录制与 waypoint 生成
4. `LDR-004` 数据采集实验
5. future follower 接入后再恢复 `E2E-HW-002`

## 6. 不再继续投入的方向

在没有 follower 的前提下，暂停继续投入：

- 单 leader 真实抓取执行
- leader 直接当正式执行臂的工单闭环
- 把当前 `task_executor DONE/OK` 误当作真实硬件执行完成

## 7. 下一步建议

立即把当前工程主线改成：

- `so101_leader_input_bridge`

而不是：

- `so101_real_driver_bridge`

这样做的好处是：

- 今天就能产出真实可用结果
- 不再建立错误预期
- 未来补 follower 时，接口还能复用
