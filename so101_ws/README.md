# SO-101 ROS2 Workspace

基于官方 [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100) (⭐5543) 仓库搭建的 ROS2 开发环境。

## 包结构

```
so101_ws/src/
├── SO-ARM100/              # 官方仓库（只读参考，含 STEP/STL/BOM）
├── so101_description/      # ROS2 URDF 描述包
│   ├── urdf/so101.urdf     # 官方 URDF（mesh路径已适配ROS2）
│   ├── meshes/so101/       # 官方 STL mesh
│   ├── launch/display.launch.py  # RViz2 可视化
│   └── rviz/display.rviz
├── so101_bringup/          # 启动配置
│   ├── config/waypoints.yaml     # 预设动作路径点
│   └── launch/
├── so101_gazebo/           # Gazebo 场景与工位
│   ├── worlds/so101_workcell.world
│   └── launch/scene.launch.py
├── so101_moveit_config/    # MoveIt2 配置与集成启动
│   ├── config/so101.srdf
│   └── launch/demo.launch.py
└── so101_mujoco/           # MuJoCo 仿真
    ├── models/             # 官方 MJCF + mesh
    │   ├── so101.xml
    │   ├── scene.xml
    │   └── assets/
    └── scripts/view_so101.py     # MuJoCo 可视化测试
```

## 快速开始

### 默认启动入口
```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
bash tools/e2e/stop_visible_demo_stack.sh
bash tools/e2e/start_visible_demo_stack.sh
```

如需一并打开 RViz：

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
USE_RVIZ=true bash tools/e2e/start_visible_demo_stack.sh
```

说明：
- 当前仓库默认演示入口已经切到“可见仿真演示模式”
- 默认停止入口同样统一为 `bash tools/e2e/stop_visible_demo_stack.sh`
- 旧入口脚本仅保留兼容，不再作为推荐命令写法

### RViz2 可视化（验证 URDF）
```bash
cd ~/dev/ros2/workspaces/so101_ws
colcon build
source install/setup.bash
ros2 launch so101_description display.launch.py
```

### SO-101 闭环 Bringup（仿真联调）
```bash
cd ~/dev/ros2/workspaces/so101_ws
colcon build --packages-select so101_description so101_bringup
source install/setup.bash
ros2 launch so101_bringup sim_bringup.launch.py
```

默认会启动：
- `robot_state_publisher`
- `ros2_control_node`（mock hardware）
- `joint_state_broadcaster`
- `joint_trajectory_controller`
- `joint_state_publisher`（可选，默认关闭）
- `rviz2`
- `task_executor`（消费 `/mes_task_cmd`，发布 `/mes_task_status`）
- `mock_yolo_node`（发布 `/detections`）
- `rosbridge_websocket`（端口 `9090`）

关闭模拟检测与 rosbridge：
```bash
ros2 launch so101_bringup sim_bringup.launch.py use_mock_yolo:=false enable_rosbridge:=false
```

纯命令行自测（推荐先跑）：
```bash
ros2 launch so101_bringup sim_bringup.launch.py use_rviz:=false enable_rosbridge:=false
```

### 下发任务命令（本地测试）
```bash
ros2 topic pub --once /mes_task_cmd std_msgs/msg/String \
  "{data: '{\"requestId\":\"req-001\",\"orderId\":\"order-001\",\"actionTemplateId\":\"pick_place_red\",\"params\":{}}'}"
```

查看执行状态：
```bash
ros2 topic echo /mes_task_status
```

### MuJoCo 可视化
```bash
pip install mujoco
cd src/so101_mujoco/scripts
python3 view_so101.py
```

### Gazebo 场景（GZM-001）
```bash
source /opt/ros/humble/setup.bash
source ~/dev/ros2/workspaces/so101_ws/install/setup.bash
ros2 launch so101_gazebo scene.launch.py
```

### Blender 桌面平台 Gazebo GUI 预览（BLD-001）
当前 WSL 里 `/usr/bin/gz` 是 Gazebo Classic 11，不是新版 `gz sim`。想直接看窗口，优先用 Classic `gzclient` 入口：
```bash
source /opt/ros/humble/setup.bash
source ~/dev/ros2/workspaces/so101_ws/install/setup.bash
ros2 launch so101_gazebo desktop_cell_classic.launch.py
```

如果从 Windows 侧交互终端启动，可直接执行：
```powershell
E:\web\code\so101_ws\tools\e2e\start_desktop_cell_gz_gui.cmd
```

说明：该入口只加载 Blender 导出的桌面工位视觉模型，用于看 GUI/布局/比例；不接主臂、不声明真实闭环。

### Blender 桌面平台 Gazebo Sim 预览（BLD-001）
```bash
source /opt/ros/humble/setup.bash
source ~/dev/ros2/workspaces/so101_ws/install/setup.bash
ros2 launch so101_gazebo desktop_cell_ign.launch.py
```

无 GUI smoke：
```bash
ros2 launch so101_gazebo desktop_cell_ign.launch.py use_gui:=false verbose:=4
```

说明：该入口使用 `ign gazebo` / Gazebo Sim 6，适合 headless smoke；现有 `scene.launch.py` 仍是 Gazebo Classic + ROS2 控制主链。

### MoveIt2 集成启动（GZM-002）
```bash
source /opt/ros/humble/setup.bash
source ~/dev/ros2/workspaces/so101_ws/install/setup.bash
ros2 launch so101_moveit_config demo.launch.py use_rviz:=false use_gzclient:=false
```

仅验证 Gazebo+控制链路（不启 move_group）：
```bash
ros2 launch so101_moveit_config demo.launch.py enable_move_group:=false use_rviz:=false
```

### 真机 Bringup（骨架）
```bash
ros2 launch so101_bringup real_bringup.launch.py
```
说明：当前仓库已打通任务协议与状态流，真机控制器插件接入需在 `ros2_control` 硬件接口层继续完善。

## 官方资源
- 硬件设计: https://github.com/TheRobotStudio/SO-ARM100
- LeRobot 控制: https://github.com/huggingface/lerobot
- LeRobot SO-101 教程: https://huggingface.co/docs/lerobot/so101
- MuJoCo 模型: https://github.com/google-deepmind/mujoco_menagerie/tree/main/trs_so_arm100

## MES 侧代码（新增）
- `mes_backend/`：Spring Boot 后端骨架（工单、rosbridge、WebSocket）
- `mes_frontend/`：PC 端演示页面（最小可用）
- `docs/MES_ROS2_接口协议.md`：MES 与 ROS2 话题/JSON 协议
