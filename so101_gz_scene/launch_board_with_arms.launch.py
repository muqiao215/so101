import math
import os
import re

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _strip_xml_comments(xml_str: str) -> str:
    """去掉 XML 注释，避免 <!-- 让 rclcpp 参数解析器把 -- 当成 CLI 分隔符而炸"""
    return re.sub(r"<!--.*?-->", "", xml_str, flags=re.DOTALL)


def _strip_gazebo_ros2_control_plugin(xml_str: str) -> str:
    return re.sub(
        r"\s*<gazebo>\s*<plugin(?=[^>]*filename=\"libgazebo_ros2_control\.so\")[\s\S]*?</plugin>\s*</gazebo>",
        "",
        xml_str,
        flags=re.DOTALL,
    )


def _copy_controllers_yaml_to_ascii_path(source_path: str) -> str:
    """gazebo_ros2_control can throw while parsing non-ASCII parameter paths."""
    target_path = "/tmp/so101_gazebo_controllers.yaml"
    data = open(source_path, encoding="utf-8").read()
    if not os.path.exists(target_path) or open(target_path, encoding="utf-8").read() != data:
        with open(target_path, "w", encoding="utf-8") as fh:
            fh.write(data)
    return target_path


def _compute_spawn_pose(calib, arm_key):
    """
    board_frame -> <arm>_mount_frame -> <arm>_base_link
    """
    m = calib["mounts"][arm_key]
    mx, my, _mz = m["board_xyz"]
    m_yaw = math.radians(m["yaw_deg"])

    off = calib["mount_to_base_link_offset_m"]["xyz"]
    yaw_off = math.radians(calib["forward_axis"].get("yaw_offset_deg", 0.0))
    spawn_z = float(calib.get("spawn_base_z_m", 0.0))

    bx_off, by_off = (math.cos(m_yaw) * off[0] - math.sin(m_yaw) * off[1],
                      math.sin(m_yaw) * off[0] + math.cos(m_yaw) * off[1])
    bx = mx + bx_off
    by = my + by_off
    bz = spawn_z + off[2]
    b_yaw = m_yaw + yaw_off
    return bx, by, bz, b_yaw


def _build_robot_description(urdf_path, controllers_yaml_path, *, enable_ros2_control=True):
    """读 URDF,剥 XML 注释,把 __CONTROLLERS_YAML__ 占位符替换为 controllers.yaml 路径。

    这样 gazebo_ros2_control 在 Load 时能正确读到 controllers.yaml,
    且没有 <!-- 注释让 rclcpp 参数解析器炸裂(段错误)。
    """
    raw = open(urdf_path, encoding="utf-8").read()
    description = _strip_xml_comments(raw.replace("__CONTROLLERS_YAML__", controllers_yaml_path))
    if not enable_ros2_control:
        description = _strip_gazebo_ros2_control_plugin(description)
    return description


def generate_launch_description():
    scene_dir = os.path.dirname(os.path.abspath(__file__))
    world = os.path.join(scene_dir, "generated", "so101_board_world.sdf")
    calib_yaml = os.path.join(scene_dir, "calibration.yaml")
    report_path = os.path.join(scene_dir, "calibration_report.txt")

    with open(calib_yaml) as fh:
        calib = yaml.safe_load(fh)

    desc_share = get_package_share_directory("so101_description")
    urdf = os.path.join(desc_share, "urdf", "so101.urdf")
    controllers_yaml = os.path.join(
        get_package_share_directory("so101_bringup"),
        "config", "controllers.yaml",
    )
    controllers_yaml_for_gazebo = _copy_controllers_yaml_to_ascii_path(controllers_yaml)
    mesh_dir = os.path.join(desc_share, "meshes", "so101")
    inherited_ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
    inherited_ament_prefix_path = os.environ.get("AMENT_PREFIX_PATH", "")

    # 预处理 URDF:剥注释 + 替换 controllers 路径。只有 master 加载
    # ros2_control,避免双臂同时创建根命名空间下的 /controller_manager。
    master_robot_description = _build_robot_description(
        urdf, controllers_yaml_for_gazebo, enable_ros2_control=True
    )
    follower_robot_description = _build_robot_description(
        urdf, controllers_yaml_for_gazebo, enable_ros2_control=False
    )

    use_gzclient = LaunchConfiguration("use_gzclient")

    gzserver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("gazebo_ros"),
                         "launch", "gzserver.launch.py")
        ),
        launch_arguments={
            "world": world,
            "init": "true",
            "factory": "true",
            "force_system": "true",
            "verbose": "true",
        }.items(),
    )

    gzclient = ExecuteProcess(
        cmd=["gzclient"],
        condition=IfCondition(use_gzclient),
        output="screen",
    )

    # robot_state_publisher 发布到不同 description topic,供两次 spawn 使用。
    master_robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="master_robot_state_publisher",
        parameters=[{"robot_description": master_robot_description}],
        remappings=[("robot_description", "master_robot_description")],
        output="screen",
    )
    follower_robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        parameters=[{"robot_description": follower_robot_description}],
        remappings=[("robot_description", "follower_robot_description")],
        output="screen",
    )

    def spawn_arm(entity, arm_key, delay, description_topic):
        bx, by, bz, b_yaw = _compute_spawn_pose(calib, arm_key)
        # 用 -topic robot_description 模式 spawn,这样 gazebo_ros2_control 能正确
        # 从 robot_description topic 读取 <ros2_control> 标签
        return TimerAction(
            period=delay,
            actions=[Node(
                package="gazebo_ros",
                executable="spawn_entity.py",
                arguments=[
                    "-topic", description_topic,
                    "-entity", entity,
                    "-x", "%.6f" % bx,
                    "-y", "%.6f" % by,
                    "-z", "%.6f" % bz,
                    "-Y", "%.6f" % b_yaw,
                    "-timeout", "30",
                ],
                output="screen",
            )],
        )

    calibration_proc = TimerAction(
        period=8.0,
        actions=[ExecuteProcess(
            cmd=[
                "python3", os.path.join(scene_dir, "calibration_node.py"),
                "--ros-args",
                "-p", "calibration_yaml:=%s" % calib_yaml,
                "-p", "report_path:=%s" % report_path,
                "-p", "urdf_path:=%s" % urdf,
                "-p", "mesh_dir:=%s" % mesh_dir,
                "-p", "master_model:=master_arm",
                "-p", "follower_model:=follower_arm",
                "-p", "publish_joint_states:=false",
            ],
            output="screen",
        )],
    )

    load_joint_state_broadcaster = TimerAction(
        period=12.0,
        actions=[Node(
            package="controller_manager",
            executable="spawner",
            arguments=[
                "joint_state_broadcaster",
                "--controller-manager",
                "/controller_manager",
                "--controller-manager-timeout",
                "60",
            ],
            output="screen",
        )],
    )

    load_joint_trajectory_controller = TimerAction(
        period=14.0,
        actions=[Node(
            package="controller_manager",
            executable="spawner",
            arguments=[
                "joint_trajectory_controller",
                "--controller-manager",
                "/controller_manager",
                "--controller-manager-timeout",
                "60",
            ],
            output="screen",
        )],
    )

    return LaunchDescription([
        DeclareLaunchArgument("use_gzclient", default_value="true"),
        SetEnvironmentVariable("GAZEBO_MODEL_PATH",
                               os.path.dirname(desc_share)),
        # 关键:让 gzserver 子进程能找到 controller_manager / hardware_interface
        SetEnvironmentVariable("LD_LIBRARY_PATH",
                               "/opt/ros/humble/lib:/opt/ros/humble/lib/x86_64-linux-gnu:"
                               "/opt/ros/humble/opt/gz_vendor/lib:"
                               "/usr/lib/x86_64-linux-gnu/gazebo-11/plugins:"
                               "/usr/lib/x86_64-linux-gnu:"
                               "/usr/lib:"
                               "/lib/x86_64-linux-gnu:"
                               + inherited_ld_library_path),
        SetEnvironmentVariable("AMENT_PREFIX_PATH",
                               inherited_ament_prefix_path),
        gzserver_launch,
        gzclient,
        master_robot_state_publisher,
        follower_robot_state_publisher,
        spawn_arm("master_arm", "master_arm", delay=4.0,
                  description_topic="master_robot_description"),
        spawn_arm("follower_arm", "follower_arm", delay=5.0,
                  description_topic="follower_robot_description"),
        load_joint_state_broadcaster,
        load_joint_trajectory_controller,
        calibration_proc,
    ])
