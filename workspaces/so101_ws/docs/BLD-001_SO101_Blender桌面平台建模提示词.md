# BLD-001：SO101 Blender 桌面平台建模提示词

## 目标定位

本任务不是替代 Gazebo。当前毕业设计目标是搭建一个小型智能制造桌面平台，Blender 应承担“桌面工位数字孪生、论文/答辩展示、前端资产、布局校准图”的角色。

- `Gazebo`：ROS2 控制链、MoveIt2、joint trajectory、执行基准与 benchmark。
- `RViz`：URDF、TF、关节状态、规划可视化。
- `Blender`：桌面平台几何布局、相机/工装/物料/安全区、流程动画、论文图和前端 glTF/GLB 资产。
- `真实桌面平台`：最终演示主体，完成工单下发、视觉确认、机械臂动作、状态回传。

## 代码基准

以下尺寸和坐标来自当前仓库，不是凭空设定。

| 元素 | 来源 | 尺寸 / 坐标 |
|---|---|---|
| 工作台 | `src/so101_gazebo/worlds/so101_workcell.world` | size `0.9 x 0.7 x 0.75 m`，pose center `(0.45, 0.0, 0.375)`，桌面高度 `z=0.75` |
| SO101 spawn | `src/so101_gazebo/launch/scene.launch.py` | entity `so101` spawn at `(0.0, 0.0, 0.80)` |
| pick bin | `so101_workcell.world` | center `(0.25, 0.18, 0.80)`，size `0.12 x 0.12 x 0.06 m`，红色 |
| place bin | `so101_workcell.world` | center `(0.25, -0.18, 0.80)`，size `0.12 x 0.12 x 0.06 m`，蓝色 |
| grasp target | `so101_workcell.world` | center `(0.292, 0.131, 0.758)`，size `0.018 x 0.018 x 0.016 m`，绿色动态目标 |
| overhead camera | `so101_workcell.world` | center `(0.45, 0.0, 1.65)`，body size `0.06 x 0.04 x 0.03 m`，FOV `1.047 rad`，image `640 x 480` |
| 关节顺序 | `waypoints.yaml` / RLG-005 | `[shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper]` |
| 实物主臂映射 | RLG-005 | leader -> Gazebo scale `[1, 1, 1, 1, -1, 1]`，二轴不反，五轴反 |
| 标准动作序列 | `waypoints.yaml` | `home -> above_pick -> pick -> lift_from_pick -> above_place -> place -> retreat -> home` |
| 视觉分类模板 | `waypoints.yaml` / `visionConsole.js` | `red -> pick_place_red`，`blue -> pick_place_blue` |
| MES 状态 | `MES_ROS2_接口协议.md` | `PENDING/RUNNING/DONE/ERROR`，ROS code 包含 `DETECTION_TRIGGER/STARTED/STEP/OK/...` |

坐标约定：保持 Gazebo/ROS 世界坐标，单位使用米，`X` 指向桌面长度方向，`Y` 指向左右料盒方向，`Z` 向上。Blender 中使用 `1 Blender Unit = 1 meter`，不要把场景整体重新居中到桌面中心。

## Blender 场景框架

建议文件结构：

```text
SO101_Desktop_Cell.blend
├── 00_world_reference
│   ├── ros_world_axes
│   ├── table_top_grid
│   └── dimension_labels
├── 10_workcell_geometry
│   ├── work_table
│   ├── pick_bin_red
│   ├── place_bin_blue
│   ├── grasp_target_green
│   ├── fixture_slots
│   └── safety_boundary
├── 20_robot
│   ├── so101_visual_or_imported_mesh
│   ├── joint_axis_labels
│   └── tcp_marker
├── 30_vision
│   ├── overhead_camera_body
│   ├── camera_mount_frame
│   ├── fov_cone_640x480
│   └── detection_overlay_plane
├── 40_mes_context
│   ├── mini_monitor
│   ├── order_status_cards
│   └── rosbridge_status_indicator
├── 50_process_animation
│   ├── order_created
│   ├── detection_trigger
│   ├── pick_sequence
│   ├── place_sequence
│   └── status_feedback
└── 90_export
    ├── render_camera_overview
    ├── render_camera_topdown
    └── glb_frontend_export
```

## 精细建模提示词

下面提示词可直接交给 Blender 建模助手、图生 3D 助手，或作为手工建模 checklist。

```text
Create a precise Blender digital twin scene for a desktop intelligent manufacturing demo cell based on ROS2 SO101.

Use metric units. Set 1 Blender Unit = 1 meter. Preserve the Gazebo/ROS world coordinate frame: X is table length direction, Y is left/right material-bin direction, Z is up. Do not recenter the scene. Add visible red/green/blue XYZ axis arrows near world origin.

Scene style:
- Compact desktop industrial lab platform, not sci-fi, not a large factory.
- Clean gray tabletop, light industrial aluminum fixtures, soft purple-white UI accent matching a Vue MES dashboard.
- Use subtle color differences, not high-contrast neon. Red and blue are only for material bins and detected categories.
- Render should be clear enough for a graduation thesis figure and a defense slide.

Core geometry:
1. Work table:
   - Name: work_table
   - Position center: (0.45, 0.0, 0.375)
   - Dimensions: 0.90 m X length, 0.70 m Y width, 0.75 m Z height
   - Top surface is exactly z = 0.75 m
   - Material: matte dark gray side panels, slightly lighter top, bevel edges radius 0.01 m
   - Add a faint 0.05 m grid on the tabletop, aligned with ROS X/Y axes.

2. SO101 robot:
   - Name: so101_robot
   - Base reference/spawn position: (0.0, 0.0, 0.80)
   - Use imported SO101 mesh from the ROS package if available; otherwise create a clean proxy with:
     - circular base radius about 0.19 m
     - shoulder housing about 0.19 x 0.088 x 0.17 m
     - upper arm length about 0.34 m
     - forearm length about 0.30 m
     - compact wrist and two-finger gripper
   - Joint order labels must be visible:
     1 shoulder_pan
     2 shoulder_lift
     3 elbow_flex
     4 wrist_flex
     5 wrist_roll
     6 gripper
   - Add a small TCP marker sphere at the gripper centerline.
   - Add a note near joint 5: “wrist_roll is reversed in real-leader to Gazebo mapping”.

3. Pick bin:
   - Name: pick_bin_red
   - Center: (0.25, 0.18, 0.80)
   - Dimensions: 0.12 x 0.12 x 0.06 m
   - Color: muted red, not glossy
   - Add label: “pick / red / pick_place_red”

4. Place bin:
   - Name: place_bin_blue
   - Center: (0.25, -0.18, 0.80)
   - Dimensions: 0.12 x 0.12 x 0.06 m
   - Color: muted blue, not glossy
   - Add label: “place / blue / pick_place_blue”

5. Grasp target:
   - Name: grasp_target_green
   - Center: (0.292, 0.131, 0.758)
   - Dimensions: 0.018 x 0.018 x 0.016 m
   - Color: soft green
   - Place it on the tabletop so its bottom aligns to z = 0.75 m.
   - Add a tiny shadow and label: “dynamic grasp_target”.

6. Fixed fixture slots:
   - Add two shallow fixture pockets on the tabletop around pick and place zones.
   - Each pocket outer size: 0.16 x 0.16 m, depth visually 0.006 m.
   - Pick pocket centered at (0.25, 0.18, 0.753).
   - Place pocket centered at (0.25, -0.18, 0.753).
   - Material: light gray anodized aluminum, bevel radius 0.004 m.

7. Overhead vision camera:
   - Name: overhead_vision_camera
   - Body center: (0.45, 0.0, 1.65)
   - Body dimensions: 0.06 x 0.04 x 0.03 m
   - Lens points downward toward the tabletop center.
   - Add black camera body and small glass lens.
   - Add a simple aluminum mount frame rising from the back-right of the table:
     - vertical post diameter 0.025 m, height from z=0.75 to z=1.65
     - horizontal boom length about 0.35 m
   - Add translucent camera frustum cone:
     - horizontal FOV: 1.047 rad, label “640 x 480 / 15 Hz”
     - cone should cover pick_bin_red, place_bin_blue and grasp_target_green.

8. MES monitor and status display:
   - Add a small desktop monitor outside or behind the table, readable but secondary.
   - Suggested position: center around (0.72, -0.40, 0.98), tilted toward viewer.
   - Screen size: about 0.22 x 0.14 m.
   - Show simplified UI cards:
     - orderId
     - actionTemplateId
     - rosbridge connected
     - detection: red / blue
     - state: PENDING -> RUNNING -> DONE
   - Use soft purple-white UI cards, consistent with the current frontend style.

9. Safety and traceability:
   - Add a thin translucent safety boundary on tabletop:
     - rectangle from X 0.05 to 0.60, Y -0.30 to 0.30, Z 0.752
     - color: faint amber, opacity 0.12
   - Add three small status towers or indicator dots:
     - green: rosbridge connected
     - blue: vision active
     - amber: manual intervention / safe stop
   - Add a clipboard or QR-like tag on the table labeled “traceable run artifact”.

10. Process path visualization:
   - Draw a thin dotted path from above_pick -> pick -> lift_from_pick -> above_place -> place -> retreat.
   - Use current action sequence:
     home, above_pick, pick, lift_from_pick, above_place, place, retreat, home.
   - Show small numbered markers for each step.
   - Do not claim real grasp success. Label it “planned pick-place workflow / visual confirmation + fixed fixture positioning”.

Required render cameras:
- Camera A: isometric overview, shows robot, table, bins, overhead camera, MES monitor.
- Camera B: top-down view matching the overhead camera concept.
- Camera C: close-up of pick/place bins and target cube.
- Camera D: joint-axis detail view showing joint 5 wrist_roll reverse note.

Output:
- Save the Blender file as SO101_Desktop_Cell.blend.
- Export a lightweight GLB named so101_desktop_cell_preview.glb for web preview.
- Render PNGs at 1920x1080:
  1 overview.png
  2 topdown_vision_layout.png
  3 workflow_steps.png
  4 joint_axis_reference.png

Negative constraints:
- Do not build a huge factory floor.
- Do not add conveyor belts unless explicitly requested later.
- Do not make the scene cyberpunk or neon.
- Do not imply successful physical grasp/lift if only using Gazebo or visual mock data.
- Do not change the ROS/Gazebo coordinates or table dimensions.
```

## 工业平台还需要补哪些模拟流程

如果目标是模仿“工业平台”，只建一个机械臂和料盒还不够。至少需要补以下流程层，才像 MES 小型产线，而不是单机机械臂演示。

### 必须补的最小工业流程

1. 工单流转
   - `PENDING -> RUNNING -> DONE/ERROR`
   - 对应后端 `OrderRecord`、前端工单列表、ROS `/mes_task_status`。

2. 物料到位确认
   - 红/蓝物料进入固定工装槽位。
   - 视觉只负责类别识别和在位确认，不主张任意位姿抓取。

3. 视觉检测触发
   - `/detections` 输出 `category/confidence/bbox`。
   - `red -> pick_place_red`，`blue -> pick_place_blue`。
   - Blender 可用相机视锥、检测框 overlay 和类别标签表现。

4. 动作模板执行
   - `home -> above_pick -> pick -> lift_from_pick -> above_place -> place -> retreat -> home`
   - 每一步要有状态卡或路径 marker。

5. 状态回传与追溯
   - 显示 `requestId/orderId/actionTemplateId/state/code/message/ts`。
   - 体现“不是跑一次”，而是有日志、artifact、dashboard。

6. 异常分支
   - 无检测：不执行，状态 `BAD_REQUEST` 或等待。
   - 类别不匹配：`DETECTION_MISMATCH`。
   - 执行失败：`EXECUTION_ERROR`。
   - 忙碌：`BUSY`。

### 建议补的展示流程

1. 人工接管 / 急停
   - Blender 场景里放一个小型急停按钮和安全区。
   - 前端/论文里说明真实硬件前必须有低速、安全门和人工确认。

2. 相机标定与坐标系说明
   - 显示 ROS 世界坐标、相机 FOV、桌面平面。
   - 当前方案是固定工装定位，不需要完整手眼标定；后续扩展可做平面映射/手眼标定。

3. 质量检查
   - 放置后增加一个“检测放置区是否有物料”的虚拟检查节点。
   - 可在 Blender 里用第二个 overlay 表示 post-check。

4. 节拍统计
   - 显示 cycle time、success count、error count。
   - 对应毕设中的“工程稳定性、连续运行、状态时延”。

5. 数据闭环
   - 展示一条 episode artifact：image、detections、joint_states、task_status、report。
   - 对应当前 recorder/dataset/trainability smoke 链。

6. 主臂输入调试
   - 如果展示主臂，可作为“调试输入设备”放在旁边。
   - 只能标注为 leader input -> Gazebo simulated arm，不要写成真实 follower 闭环。

## 第一版交付建议

第一版不要做复杂动画，先交付四张图：

1. `overview.png`：SO101 桌面工位总览。
2. `topdown_vision_layout.png`：相机俯视、FOV、pick/place/target 坐标。
3. `workflow_steps.png`：MES 工单到动作序列的流程图式渲染。
4. `joint_axis_reference.png`：六轴名称与五轴反向说明。

这四张图能直接服务毕业设计说明书：系统总体方案、硬件平台设计、视觉布局、控制流程与调试问题说明。

## Gazebo / gz 导入资产

Blender 第一版资产先导出到 E 盘，随后已迁移进 `so101_gazebo` 包。E 盘仍作为 Blender 源文件、渲染图和外部导出包备份；项目内接入 Gazebo Classic GUI 预览和 Gazebo Sim headless smoke 共用的 OBJ+SDF 模型包。

```text
E:\web\tools\blender-output\SO101_Desktop_Cell
├── SO101_Desktop_Cell.blend
├── so101_desktop_cell_preview.glb
├── overview.png
├── topdown_vision_layout.png
├── workflow_steps.png
├── joint_axis_reference.png
└── gazebo_model
    ├── README_GZ_IMPORT.md
    ├── so101_desktop_cell_test.world.sdf
    └── so101_desktop_cell
        ├── model.config
        ├── model.sdf
        └── meshes
            ├── so101_desktop_cell_visual.obj
            └── so101_desktop_cell_visual.mtl
```

项目内迁移位置：

```text
src/so101_gazebo
├── launch/desktop_cell_classic.launch.py
├── launch/desktop_cell_ign.launch.py
├── worlds/so101_desktop_cell_classic.world
├── worlds/so101_desktop_cell_ign.world.sdf
└── models/so101_desktop_cell
    ├── model.config
    ├── model.sdf
    └── meshes
        ├── so101_desktop_cell_visual.obj
        └── so101_desktop_cell_visual.mtl
```

当前 WSL 环境里 `/usr/bin/gz` 是 Gazebo Classic 11.10.2 的管理 CLI，不是新版 `gz sim` 入口；新版 Gazebo Sim 6.16.0 的可用入口是 `ign gazebo`。

如果目标是“打开 GUI 看桌面平台”，优先使用 Classic 可见入口：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch so101_gazebo desktop_cell_classic.launch.py
```

Windows 侧可用脚本：

```powershell
E:\web\code\so101_ws\tools\e2e\start_desktop_cell_gz_gui.cmd
```

该入口只用于 Blender 桌面工位视觉/比例/布局确认，不接主臂、不接从臂、不声明真实闭环。

Gazebo Sim 6 headless smoke 使用：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch so101_gazebo desktop_cell_ign.launch.py
```

无 GUI smoke：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch so101_gazebo desktop_cell_ign.launch.py use_gui:=false verbose:=4
```

如果直接打开 E 盘源 world，本机 WSL 测试命令应写成：

```bash
export IGN_GAZEBO_RESOURCE_PATH="/mnt/e/web/tools/blender-output/SO101_Desktop_Cell/gazebo_model:${IGN_GAZEBO_RESOURCE_PATH}"
export GZ_SIM_RESOURCE_PATH="/mnt/e/web/tools/blender-output/SO101_Desktop_Cell/gazebo_model:${GZ_SIM_RESOURCE_PATH}"
ign gazebo /mnt/e/web/tools/blender-output/SO101_Desktop_Cell/gazebo_model/so101_desktop_cell_test.world.sdf
```

Headless smoke 口径：

```bash
IGN_GAZEBO_RESOURCE_PATH="/mnt/e/web/tools/blender-output/SO101_Desktop_Cell/gazebo_model:${IGN_GAZEBO_RESOURCE_PATH}" \
GZ_SIM_RESOURCE_PATH="/mnt/e/web/tools/blender-output/SO101_Desktop_Cell/gazebo_model:${GZ_SIM_RESOURCE_PATH}" \
timeout 12s ign gazebo -s -r -v 4 \
  /mnt/e/web/tools/blender-output/SO101_Desktop_Cell/gazebo_model/so101_desktop_cell_test.world.sdf \
  > .vscode/.runtime/bld001_ign_gazebo_smoke.log 2>&1
```

2026-05-11 WSL smoke 结果：

- `ign gazebo --versions`：`6.16.0`
- `ign sdf --help` 可用，默认 SDF spec `1.9`
- `ign gazebo -s -r -v 4 ...so101_desktop_cell_test.world.sdf` 能加载 world，并初始化 `so101_desktop_cell_test`
- 日志出现 `World [so101_desktop_cell_test] initialized with [1ms] physics profile`
- `timeout` 结束码为 `124`，这是预期的短时 smoke 终止，不是导入失败
- 日志路径：`.vscode/.runtime/bld001_ign_gazebo_smoke.log`
- 项目内 Ignition launch smoke：`timeout 14s ros2 launch so101_gazebo desktop_cell_ign.launch.py use_gui:=false verbose:=4` 可加载 install 后的 `so101_desktop_cell_ign.world.sdf`，并初始化 `World [so101_desktop_cell_ign]`
- 项目内 smoke 日志路径：`.vscode/.runtime/bld001_project_ign_launch_smoke.log`
- Classic 模型校验：`gz sdf -k src/so101_gazebo/models/so101_desktop_cell/model.sdf` 通过
- Classic GUI 入口：`ros2 launch so101_gazebo desktop_cell_classic.launch.py`

注意：如果在 Codex 后台会话里启动 GUI 仍看不到窗口，先查 Gazebo 日志。2026-05-11 本轮已定位到后台会话没有可用 WSLg X11 socket，日志为 `Can't open display: :0`；这不是模型迁移失败。需要从 Windows Terminal / WSL 交互终端执行 Classic GUI 入口。
