import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    desc_pkg = get_package_share_directory("so101_description")
    bringup_pkg = get_package_share_directory("so101_bringup")

    urdf_file = os.path.join(desc_pkg, "urdf", "so101.urdf")
    waypoints_file = os.path.join(bringup_pkg, "config", "waypoints.yaml")

    with open(urdf_file, "r", encoding="utf-8") as f:
        robot_description = f.read()

    enable_rosbridge = LaunchConfiguration("enable_rosbridge")
    use_mock_yolo = LaunchConfiguration("use_mock_yolo")
    command_execution_enabled = LaunchConfiguration("command_execution_enabled")
    detection_trigger_enabled = LaunchConfiguration("detection_trigger_enabled")
    detection_confidence_threshold = LaunchConfiguration("detection_confidence_threshold")
    detection_trigger_cooldown_sec = LaunchConfiguration("detection_trigger_cooldown_sec")
    detection_template_map_json = LaunchConfiguration("detection_template_map_json")

    return LaunchDescription(
        [
            DeclareLaunchArgument("enable_rosbridge", default_value="true"),
            DeclareLaunchArgument("use_mock_yolo", default_value="false"),
            DeclareLaunchArgument("command_execution_enabled", default_value="true"),
            DeclareLaunchArgument("detection_trigger_enabled", default_value="true"),
            DeclareLaunchArgument("detection_confidence_threshold", default_value="0.5"),
            DeclareLaunchArgument("detection_trigger_cooldown_sec", default_value="8.0"),
            DeclareLaunchArgument(
                "detection_template_map_json",
                default_value='{"red":"pick_place_red","blue":"pick_place_blue"}',
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[{"robot_description": robot_description}],
                output="screen",
            ),
            ExecuteProcess(
                cmd=[
                    "python3",
                    os.path.join(bringup_pkg, "scripts", "task_executor.py"),
                    "--ros-args",
                    "-p",
                    f"waypoints_file:={waypoints_file}",
                    "-p",
                    ["command_execution_enabled:=", command_execution_enabled],
                    "-p",
                    ["detection_trigger_enabled:=", detection_trigger_enabled],
                    "-p",
                    ["detection_confidence_threshold:=", detection_confidence_threshold],
                    "-p",
                    ["detection_trigger_cooldown_sec:=", detection_trigger_cooldown_sec],
                    "-p",
                    ["detection_template_map_json:='", detection_template_map_json, "'"],
                ],
                output="screen",
            ),
            ExecuteProcess(
                cmd=["python3", os.path.join(bringup_pkg, "scripts", "mock_yolo_node.py")],
                condition=IfCondition(use_mock_yolo),
                output="screen",
            ),
            Node(
                package="rosbridge_server",
                executable="rosbridge_websocket",
                condition=IfCondition(enable_rosbridge),
                output="screen",
            ),
        ]
    )
