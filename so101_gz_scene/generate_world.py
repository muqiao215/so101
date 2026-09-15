#!/usr/bin/env python3
import math
from pathlib import Path


# =========================
# Reality map, unit: meter
# =========================

BOARD = {
    "size": [0.450, 0.455, 0.012],
    "pose": [0.225, 0.2275, -0.006, 0.0, 0.0, 0.0],
}

# mount_frame -> base_link offset (DERIVED from URDF base_link collision
# cylinder centered at (0,0,0.035): base footprint center == base_link XY
# origin; base bottom ~ base_link origin). See calibration.yaml.
# In meters, expressed in the arm frame.
MOUNT_TO_BASE_OFFSET = [0.0, 0.0, 0.0]
SPAWN_BASE_Z = 0.0  # base bottom rests on board top surface

ROBOTS = {
    # 主臂：正前方
    "master_arm": {
        "base_xyz": [0.060, 0.045, 0.000],
        "yaw": math.radians(90.0),
        "color": [0.1, 0.35, 1.0, 1.0],
    },

    # 从臂：纠正后的 x = 29 cm，不是 6 + 29
    # 角度按近照估算：82.5°
    "follower_arm": {
        "base_xyz": [0.290, 0.045, 0.000],
        "yaw": math.radians(82.5),
        "color": [1.0, 0.25, 0.1, 1.0],
    },
}

CAMERA = {
    "xyz": [0.085, 0.455, 0.105],
    "rpy": [0.0, 0.0, 0.0],
}

# A/B/C/D 是木板上的相机标定点，不是工作区域
CALIB_POINTS = {
    "A": [0.190, 0.155, 0.003],
    "B": [0.190, 0.230, 0.003],
    "C": [0.045, 0.235, 0.003],
    "D": [0.040, 0.170, 0.003],
}

# 示例方块，后面应该由 OpenCV 识别结果动态更新
DEMO_OBJECTS = {
    "blue_cube": {
        "pose": [0.120, 0.195, 0.0275, 0.0, 0.0, 0.0],
        "size": [0.055, 0.055, 0.055],
        "color": [0.0, 0.1, 1.0, 1.0],
    },
}


# =========================
# SDF helpers
# =========================

def rgba(color):
    return f"{color[0]} {color[1]} {color[2]} {color[3]}"


def pose_str(pose):
    return " ".join(f"{v:.6f}" for v in pose)


def box_model(name, pose, size, color, static=True, collision=True):
    collision_block = ""
    if collision:
        collision_block = f"""
      <collision name="collision">
        <geometry>
          <box>
            <size>{size[0]:.6f} {size[1]:.6f} {size[2]:.6f}</size>
          </box>
        </geometry>
      </collision>"""

    return f"""
    <model name="{name}">
      <static>{str(static).lower()}</static>
      <pose>{pose_str(pose)}</pose>
      <link name="link">
        <visual name="visual">
          <geometry>
            <box>
              <size>{size[0]:.6f} {size[1]:.6f} {size[2]:.6f}</size>
            </box>
          </geometry>
          <material>
            <ambient>{rgba(color)}</ambient>
            <diffuse>{rgba(color)}</diffuse>
          </material>
        </visual>{collision_block}
      </link>
    </model>
"""


def cylinder_model(name, pose, radius, length, color, static=True, collision=True):
    collision_block = ""
    if collision:
        collision_block = f"""
      <collision name="collision">
        <geometry>
          <cylinder>
            <radius>{radius:.6f}</radius>
            <length>{length:.6f}</length>
          </cylinder>
        </geometry>
      </collision>"""

    return f"""
    <model name="{name}">
      <static>{str(static).lower()}</static>
      <pose>{pose_str(pose)}</pose>
      <link name="link">
        <visual name="visual">
          <geometry>
            <cylinder>
              <radius>{radius:.6f}</radius>
              <length>{length:.6f}</length>
            </cylinder>
          </geometry>
          <material>
            <ambient>{rgba(color)}</ambient>
            <diffuse>{rgba(color)}</diffuse>
          </material>
        </visual>{collision_block}
      </link>
    </model>
"""


def sphere_model(name, pose, radius, color, static=True, collision=False):
    collision_block = ""
    if collision:
        collision_block = f"""
      <collision name="collision">
        <geometry>
          <sphere>
            <radius>{radius:.6f}</radius>
          </sphere>
        </geometry>
      </collision>"""

    return f"""
    <model name="{name}">
      <static>{str(static).lower()}</static>
      <pose>{pose_str(pose)}</pose>
      <link name="link">
        <visual name="visual">
          <geometry>
            <sphere>
              <radius>{radius:.6f}</radius>
            </sphere>
          </geometry>
          <material>
            <ambient>{rgba(color)}</ambient>
            <diffuse>{rgba(color)}</diffuse>
          </material>
        </visual>{collision_block}
      </link>
    </model>
"""


def line_box_model(name, p1, p2, width, height, color):
    x1, y1, z1 = p1
    x2, y2, z2 = p2

    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    yaw = math.atan2(dy, dx)

    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    cz = max(z1, z2)

    return box_model(
        name=name,
        pose=[cx, cy, cz, 0.0, 0.0, yaw],
        size=[length, width, height],
        color=color,
        static=True,
        collision=False,
    )


def direction_arrow(name, base_xyz, yaw, color):
    """
    用两个 box 表示机械臂朝向。
    约定：箭头方向就是该机械臂 base_link 的正前方。
    """
    x, y, z = base_xyz
    z = 0.018

    length = 0.080
    width = 0.010
    height = 0.006

    cx = x + math.cos(yaw) * length / 2.0
    cy = y + math.sin(yaw) * length / 2.0

    shaft = box_model(
        name=f"{name}_front_arrow",
        pose=[cx, cy, z, 0.0, 0.0, yaw],
        size=[length, width, height],
        color=color,
        static=True,
        collision=False,
    )

    tip_len = 0.020
    tx = x + math.cos(yaw) * (length + tip_len / 2.0)
    ty = y + math.sin(yaw) * (length + tip_len / 2.0)

    tip = box_model(
        name=f"{name}_front_tip",
        pose=[tx, ty, z, 0.0, 0.0, yaw],
        size=[tip_len, width * 2.0, height],
        color=color,
        static=True,
        collision=False,
    )

    return shaft + tip


def axis_triad(name, origin_xyz, yaw, axis_len=0.060, thin=0.004):
    """
    Small XYZ triad (X red / Y green / Z blue) at origin_xyz, rotated by yaw.
    X is drawn along (cos yaw, sin yaw); Y perpendicular; Z straight up.
    """
    x0, y0, z0 = origin_xyz
    cos, sin = math.cos(yaw), math.sin(yaw)

    # X axis (red), length axis_len along forward
    x_cx = x0 + cos * axis_len / 2.0
    x_cy = y0 + sin * axis_len / 2.0
    xaxis = box_model(
        name=f"{name}_trX",
        pose=[x_cx, x_cy, z0, 0.0, 0.0, yaw],
        size=[axis_len, thin, thin],
        color=[1.0, 0.0, 0.0, 1.0],
        static=True,
        collision=False,
    )

    # Y axis (green), perpendicular to forward
    y_yaw = yaw + math.pi / 2.0
    y_cx = x0 + math.cos(y_yaw) * axis_len / 2.0
    y_cy = y0 + math.sin(y_yaw) * axis_len / 2.0
    yaxis = box_model(
        name=f"{name}_trY",
        pose=[y_cx, y_cy, z0, 0.0, 0.0, y_yaw],
        size=[axis_len, thin, thin],
        color=[0.0, 1.0, 0.0, 1.0],
        static=True,
        collision=False,
    )

    # Z axis (blue), straight up
    zaxis = box_model(
        name=f"{name}_trZ",
        pose=[x0, y0, z0 + axis_len / 2.0, 0.0, 0.0, 0.0],
        size=[thin, thin, axis_len],
        color=[0.0, 0.2, 1.0, 1.0],
        static=True,
        collision=False,
    )

    return xaxis + yaxis + zaxis


def make_world():
    sdf_parts = []

    sdf_parts.append("""<?xml version="1.0" ?>
<sdf version="1.7">
  <world name="so101_real_to_sim_world">

    <gravity>0 0 -9.8</gravity>

    <plugin name="gazebo_ros_state" filename="libgazebo_ros_state.so">
      <ros>
        <namespace>/gazebo</namespace>
      </ros>
    </plugin>

    <scene>
      <ambient>0.7 0.7 0.7 1</ambient>
      <background>0.78 0.82 0.86 1</background>
      <shadows>true</shadows>
    </scene>

    <light name="sun" type="directional">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 2 0 0 0</pose>
      <diffuse>0.9 0.9 0.9 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.3 0.2 -1</direction>
    </light>
""")

    # 木板
    sdf_parts.append(box_model(
        name="wooden_board",
        pose=BOARD["pose"],
        size=BOARD["size"],
        color=[0.82, 0.66, 0.43, 1.0],
        static=True,
        collision=True,
    ))

    # 木板边框线，辅助看坐标
    board_x = BOARD["size"][0]
    board_y = BOARD["size"][1]
    z_line = 0.003
    edge_color = [0.05, 0.05, 0.05, 1.0]

    corners = {
        "front_left": [0.0, 0.0, z_line],
        "front_right": [board_x, 0.0, z_line],
        "back_right": [board_x, board_y, z_line],
        "back_left": [0.0, board_y, z_line],
    }

    sdf_parts.append(line_box_model(
        "board_front_edge",
        corners["front_left"],
        corners["front_right"],
        0.004,
        0.003,
        edge_color,
    ))
    sdf_parts.append(line_box_model(
        "board_right_edge",
        corners["front_right"],
        corners["back_right"],
        0.004,
        0.003,
        edge_color,
    ))
    sdf_parts.append(line_box_model(
        "board_back_edge",
        corners["back_right"],
        corners["back_left"],
        0.004,
        0.003,
        edge_color,
    ))
    sdf_parts.append(line_box_model(
        "board_left_edge",
        corners["back_left"],
        corners["front_left"],
        0.004,
        0.003,
        edge_color,
    ))

    # 坐标轴可视化
    sdf_parts.append(line_box_model(
        "axis_x_red",
        [0.0, 0.0, 0.008],
        [0.120, 0.0, 0.008],
        0.006,
        0.006,
        [1.0, 0.0, 0.0, 1.0],
    ))
    sdf_parts.append(line_box_model(
        "axis_y_green",
        [0.0, 0.0, 0.011],
        [0.0, 0.120, 0.011],
        0.006,
        0.006,
        [0.0, 1.0, 0.0, 1.0],
    ))
    sdf_parts.append(line_box_model(
        "axis_z_blue",
        [0.0, 0.0, 0.014],
        [0.0, 0.0, 0.120],
        0.006,
        0.006,
        [0.0, 0.2, 1.0, 1.0],
    ))

    # 真实 SO101 机械臂通过 spawn_entity 单独 spawn（见 launch_board_with_arms.launch.py）
    # 这里不再放圆柱占位，避免丢失细节
    for robot_name, robot in ROBOTS.items():
        x, y, z = robot["base_xyz"]
        yaw = robot["yaw"]
        color = robot["color"]

        # base_link 位置 = mount 位置 + Rz(yaw)·(mount->base offset)
        ox, oy, oz = MOUNT_TO_BASE_OFFSET
        bx = x + math.cos(yaw) * ox - math.sin(yaw) * oy
        by = y + math.sin(yaw) * ox + math.cos(yaw) * oy
        bz = z + oz

        # mount_frame 标记点（青色扁圆盘，贴在板面上）
        sdf_parts.append(cylinder_model(
            name=f"{robot_name}_mount_point",
            pose=[x, y, 0.004, 0.0, 0.0, 0.0],
            radius=0.014,
            length=0.004,
            color=[0.0, 0.8, 0.8, 1.0],
            static=True,
            collision=False,
        ))

        # base_link 标记点（黄色小球，位于底座中心上方，与 mount 共心）
        sdf_parts.append(sphere_model(
            name=f"{robot_name}_base_link_point",
            pose=[bx, by, 0.020 + bz, 0.0, 0.0, 0.0],
            radius=0.008,
            color=[0.95, 0.85, 0.10, 1.0],
            static=True,
            collision=False,
        ))

        # 每个臂 base_link 处的小三轴（X 红 / Y 绿 / Z 蓝），显示真实朝向
        sdf_parts.append(axis_triad(
            name=f"{robot_name}",
            origin_xyz=[bx, by, 0.090 + bz],
            yaw=yaw,
            axis_len=0.060,
            thin=0.004,
        ))

        sdf_parts.append(direction_arrow(
            name=robot_name,
            base_xyz=[x, y, z],
            yaw=yaw,
            color=color,
        ))

    # 摄像头占位
    cam_x, cam_y, cam_z = CAMERA["xyz"]
    sdf_parts.append(box_model(
        name="board_camera_placeholder",
        pose=[cam_x, cam_y, cam_z, 0.0, 0.0, 0.0],
        size=[0.035, 0.025, 0.025],
        color=[0.02, 0.02, 0.02, 1.0],
        static=True,
        collision=False,
    ))

    # 摄像头支架占位
    sdf_parts.append(box_model(
        name="camera_stand_placeholder",
        pose=[cam_x, cam_y, cam_z / 2.0, 0.0, 0.0, 0.0],
        size=[0.018, 0.018, cam_z],
        color=[0.55, 0.55, 0.55, 1.0],
        static=True,
        collision=False,
    ))

    # A/B/C/D 标定点
    point_colors = {
        "A": [1.0, 0.0, 0.0, 1.0],
        "B": [0.0, 1.0, 0.0, 1.0],
        "C": [0.0, 0.2, 1.0, 1.0],
        "D": [1.0, 0.0, 1.0, 1.0],
    }

    for name, p in CALIB_POINTS.items():
        sdf_parts.append(sphere_model(
            name=f"calib_{name}",
            pose=[p[0], p[1], p[2] + 0.006, 0.0, 0.0, 0.0],
            radius=0.008,
            color=point_colors[name],
            static=True,
            collision=False,
        ))

    # 标定四边形连线
    calib_line_color = [0.0, 1.0, 0.0, 1.0]
    sdf_parts.append(line_box_model(
        "calib_line_A_B",
        CALIB_POINTS["A"],
        CALIB_POINTS["B"],
        0.003,
        0.003,
        calib_line_color,
    ))
    sdf_parts.append(line_box_model(
        "calib_line_B_C",
        CALIB_POINTS["B"],
        CALIB_POINTS["C"],
        0.003,
        0.003,
        calib_line_color,
    ))
    sdf_parts.append(line_box_model(
        "calib_line_C_D",
        CALIB_POINTS["C"],
        CALIB_POINTS["D"],
        0.003,
        0.003,
        calib_line_color,
    ))
    sdf_parts.append(line_box_model(
        "calib_line_D_A",
        CALIB_POINTS["D"],
        CALIB_POINTS["A"],
        0.003,
        0.003,
        calib_line_color,
    ))

    # 示例物体
    for obj_name, obj in DEMO_OBJECTS.items():
        sdf_parts.append(box_model(
            name=obj_name,
            pose=obj["pose"],
            size=obj["size"],
            color=obj["color"],
            static=False,
            collision=True,
        ))

    sdf_parts.append("""
  </world>
</sdf>
""")

    return "".join(sdf_parts)


def main():
    out_dir = Path("generated")
    out_dir.mkdir(exist_ok=True)

    world_path = out_dir / "so101_board_world.sdf"
    world_path.write_text(make_world(), encoding="utf-8")

    print(f"Generated: {world_path}")
    print()
    print("Run:")
    print(f"  gz sim {world_path}")
    print()
    print("If your Gazebo is old:")
    print(f"  ign gazebo {world_path}")


if __name__ == "__main__":
    main()
