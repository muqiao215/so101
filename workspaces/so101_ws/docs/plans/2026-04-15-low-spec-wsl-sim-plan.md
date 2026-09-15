# SO101 低显卡 WSL 仿真分层方案

更新时间：2026-04-15

## 1. 目标

在硬件不稳定或显卡资源有限时，继续推进：

- replay validator 回归
- leader -> sim 输入链验证
- episode 资产生成与回放

原则：

- server-first
- headless-first
- browser-before-heavy-GUI
- 默认把仿真当测试场，不当展示场

## 2. 环境定位

推荐默认运行形态：

- WSL 内：
  - ROS 2 节点
  - Gazebo Sim server
  - replay / validator / manifest
- Windows 侧：
  - 浏览器查看轻量状态与 websocket 可视化
  - 必要时临时打开 RViz

不建议默认长期常驻：

- Gazebo GUI
- WSL 内高负载 3D GUI 常开
- 带渲染传感器的长时间回归

## 3. WSL 基础配置

### WSL 发行版要求

- 使用 `WSL 2`
- Ubuntu 启用 `systemd`

WSL 侧 `/etc/wsl.conf` 建议：

```ini
[boot]
systemd=true

[gpu]
enabled=true
```

Windows 用户目录下 `.wslconfig` 建议起点：

```ini
[wsl2]
memory=8GB
processors=4
swap=8GB
localhostForwarding=true
guiApplications=true
```

说明：

- 上述键值是本项目低到中等配置机器的工程起点
- 目标不是堆满资源，而是限制 WSL 虚拟机抢占主机

## 4. 仿真分层

### L0 零档：纯运动学回放

用途：

- 验证 `/leader/joint_states`
- 验证 joint mapping / 零位 / 方向
- 跑 replay validator 与 manifest 链

组件：

- `leader_recording_replay.py`
- `leader_joint_state_mirror.py`
- `robot_state_publisher`
- 可选 `rviz2`

默认要求：

- 不启 Gazebo
- 不启渲染传感器
- 不启 GUI 常驻

适合任务：

- identity / replay validator 回归
- 标准动作集复跑
- waypoint 提炼前的输入可信度检查

### L1 一档：轻物理无渲染

用途：

- 验证 simulated arm 与 ROS 2 控制链
- 验证 replay -> sim 执行的调度与时序

组件：

- Gazebo Sim server only
- `ros2_control` / 仿真控制链
- 不开 GUI
- 不开相机 / 深度 / 激光

推荐启动形态：

```bash
gz sim -s your_world.sdf -v 4
```

要求：

- world 只保留机械臂、地面、最小光照
- 不加复杂 mesh / 阴影 / 纹理

### L2 二档：按需渲染验证

用途：

- 只在需要 camera / render sensor / 特定渲染行为时启用

推荐启动形态：

```bash
DISPLAY= gz sim -s -r --headless-rendering your_world.sdf -v 4
```

要求：

- 仅专项验证时使用
- 不作为默认回归档位

## 5. Gazebo World 建议

默认回归 world 只保留：

- 机械臂
- 地板
- 简单光源

默认回归不保留：

- 相机
- 深度
- 激光
- 复杂材质
- 高多边形 mesh
- 大量动态物体

如需浏览器轻量查看，可预留 websocket server system：

```xml
<plugin
  filename="gz-sim-websocket-server-system"
  name="gz::sim::systems::WebsocketServer">
  <port>9002</port>
  <publication_hz>20</publication_hz>
  <max_connections>-1</max_connections>
</plugin>
```

项目建议：

- 默认 `publication_hz=20`
- 先保稳定，再追更高刷新率

## 6. RViz 使用口径

RViz 降级为：

- 按需启动的调试工具
- 不做默认常驻窗口

WSL 兼容问题时的保底命令：

```bash
export LIBGL_ALWAYS_SOFTWARE=true
rviz2
```

```bash
QT_QPA_PLATFORM=xcb rviz2
```

## 7. 目录与入口分层建议

建议后续把 launch / script 分成三层：

### 零档入口

- `leader_recording_replay.launch.py`
- `leader_rviz_replay.launch.py`

### 一档入口

- 新增 `leader_sim_replay_headless.launch.py`
- 只拉起：
  - replay source
  - simulated arm
  - 必需控制链

### 二档入口

- 新增 `leader_sim_replay_render.launch.py`
- 在一档基础上附加：
  - render sensor
  - websocket / 特定可视化

## 8. 回归策略

默认回归顺序：

1. `validator` 坏样本矩阵
2. `L0` 零档 replay
3. `L1` 轻物理 headless replay
4. 仅在需要时进入 `L2`

默认回归时长：

- 单次 `10s` 到 `30s`

默认产物：

- `replay-raw.json`
- `manifest.json`
- validator 摘要

默认不优先产出：

- 视频
- GUI 截图
- 长时渲染录屏

## 9. 当前建议执行顺序

1. 先把 `validator` 结构性坏样本矩阵补全
2. 再新增 `L1` headless simulated-arm replay 入口
3. 让 `replay -> sim -> validator -> manifest` 成为第一条软件闭环
4. 最后再考虑 GUI 展示与渲染专项验证

## 10. 与现有计划的关系

- 本文档是 `docs/plans/2026-04-09-episode-closure.md` 的仿真执行补充
- 本文档不替代 `P0/P1/P2`
- 在硬件恢复前，默认按本文档推进软件闭环
