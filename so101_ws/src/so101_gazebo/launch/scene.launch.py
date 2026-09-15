import os
import re

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _strip_xml_comments(xml_str: str) -> str:
    """Remove XML comments to prevent '<!--' breaking the rcl argument parser.

    gazebo_ros2_control internally passes robot_description through rclcpp
    node arguments. The '--' inside '<!--' is misinterpreted as a CLI flag
    separator by rcl, causing:
        parser error Couldn't parse parameter override rule
    Official demos avoid this because xacro's toxml() strips comments.
    """
    return re.sub(r"<!--.*?-->", "", xml_str, flags=re.DOTALL)


def generate_launch_description():
    gazebo_pkg = get_package_share_directory("so101_gazebo")
    desc_pkg = get_package_share_directory("so101_description")
    bringup_pkg = get_package_share_directory("so101_bringup")

    world = os.path.join(gazebo_pkg, "worlds", "so101_workcell.world")
    urdf = os.path.join(desc_pkg, "urdf", "so101.urdf")
    controllers_yaml = os.path.join(bringup_pkg, "config", "controllers.yaml")

    with open(urdf, "r", encoding="utf-8") as f:
        robot_description_raw = f.read()

    # 1) Resolve __CONTROLLERS_YAML__ placeholder (replaces xacro $(find ...) )
    # 2) Strip XML comments (prevents rcl argument parser crash on '<!--')
    robot_description = _strip_xml_comments(
        robot_description_raw.replace("__CONTROLLERS_YAML__", controllers_yaml)
    )

    use_rsp = LaunchConfiguration("use_rsp")
    spawn_robot = LaunchConfiguration("spawn_robot")
    use_gzclient = LaunchConfiguration("use_gzclient")
    cleanup_existing = LaunchConfiguration("cleanup_existing")
    software_rendering = LaunchConfiguration("software_rendering")

    # Kill stale Gazebo processes before launch to avoid port 11345 conflicts.
    cleanup_gazebo = ExecuteProcess(
        cmd=[
            "bash",
            "-lc",
            "pkill -9 -x gzclient || true; pkill -9 -x gzserver || true",
        ],
        shell=False,
        condition=IfCondition(cleanup_existing),
        output="screen",
    )

    gzserver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("gazebo_ros"), "launch", "gzserver.launch.py")
        ),
        launch_arguments={
            "world": world,
            "init": "true",
            "factory": "true",
            "force_system": "true",
            "verbose": "true",
        }.items(),
    )
    gzclient_plain = ExecuteProcess(
        cmd=["gzclient"],
        condition=IfCondition(use_gzclient),
        output="screen",
    )
    gzclient_delayed = TimerAction(
        period=2.0,
        actions=[gzclient_plain],
    )
    gzserver_delayed = TimerAction(
        period=1.0,
        actions=[gzserver_launch],
    )

    # spawn_entity uses -topic (not -file) so that libgazebo_ros2_control.so
    # can read the <ros2_control> tags from the robot_description published
    # by robot_state_publisher.  Delayed 4s to let gzserver fully start.
    spawn_entity = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=["-topic", "robot_description", "-entity", "so101",
                   "-x", "0.0", "-y", "0.0", "-z", "0.80",
                   "-timeout", "30"],
        condition=IfCondition(spawn_robot),
        output="screen",
    )
    spawn_entity_delayed = TimerAction(
        period=4.0,
        actions=[spawn_entity],
    )

    return LaunchDescription([
        DeclareLaunchArgument("use_rsp", default_value="true"),
        DeclareLaunchArgument("spawn_robot", default_value="true"),
        DeclareLaunchArgument("use_gzclient", default_value="true"),
        DeclareLaunchArgument("cleanup_existing", default_value="true"),
        DeclareLaunchArgument("software_rendering", default_value="true"),
        SetEnvironmentVariable("GAZEBO_MODEL_DATABASE_URI", ""),
        SetEnvironmentVariable("LIBGL_ALWAYS_SOFTWARE", "1", condition=IfCondition(software_rendering)),
        SetEnvironmentVariable("QT_X11_NO_MITSHM", "1", condition=IfCondition(software_rendering)),
        cleanup_gazebo,
        gzserver_delayed,
        gzclient_delayed,
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": robot_description}],
            condition=IfCondition(use_rsp),
            output="screen",
        ),
        spawn_entity_delayed,
    ])
