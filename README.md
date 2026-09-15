# SO101 软硬一体总仓

SO-ARM100（SO-101）机械臂的单一仓库：真机上位机 + ROS 2 仿真/MoveIt + 毕设 MES，2026-09-15 起由三个仓库合并而来（`so101`、`so101_ws`、`so101-ros2-arm`，后两者已归档）。

## 结构

| 目录 | 内容 |
|---|---|
| `mint_follower_demo/` | 真机上位机：物理标定参数、示教录制/复现、员工面板、动作前视觉快照。入口 `app.py`，或仓库根 `./start.sh` |
| `so101_ws/src/` | ROS 2 工作区：`so101_description`(URDF)、`so101_moveit_config`、`so101_mujoco`、`so101_gazebo`、`so101_bringup`、`yolov8_detector`、上游 `SO-ARM100`（vendored） |
| `so101_ws/mes_backend` · `mes_frontend/` | 毕设 MES（后端 + 前端） |
| `so101_ws/tools/` · `docs/` | 工具脚本与毕设文档/证据 |

## 分支说明

- 真机侧用 Python 直连串口（飞控板协议），不依赖 ROS。
- 仿真/规划侧是 ROS 2（URDF + MoveIt2 + MuJoCo/Gazebo）。
- 两侧共用 `so101_ws/src/so101_description` 的同一套 URDF 描述。

## 历史

- 2026-06-25 前后：真机示教/复现工作流（原 `so101` 仓）。
- 2026-09-15：并入 `so101_ws`（仿真/MoveIt/MES，原私有仓）的完整工作区快照；早期 Java MES 演示仓 `so101-ros2-arm` 归档，其 ROS2 部分在本仓 `so101_ws/src/` 中以更完整的形态存在。
