import os
import re

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _strip_xml_comments(xml_str):
    return re.sub(r"<!--.*?-->", "", xml_str, flags=re.DOTALL)


def generate_launch_description():
    scene_dir = os.path.dirname(os.path.realpath(__file__))
    desc_share = get_package_share_directory("so101_description")
    urdf = os.path.join(desc_share, "urdf", "so101.urdf")
    rviz_config = os.path.join(scene_dir, "so101_kinematic.rviz")

    with open(urdf, encoding="utf-8") as fh:
        robot_description = _strip_xml_comments(fh.read())

    demo_root = LaunchConfiguration("demo_root")
    joint_map = LaunchConfiguration("joint_map")
    input_space = LaunchConfiguration("input_space")
    rate = LaunchConfiguration("rate")
    use_rviz = LaunchConfiguration("use_rviz")

    bridge_cmd = [
        "python3",
        os.path.join(scene_dir, "live_follower_joint_states.py"),
        "--demo-root",
        demo_root,
        "--joint-map",
        joint_map,
        "--input-space",
        input_space,
        "--rate",
        rate,
    ]

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "demo_root",
                default_value=os.path.join(os.path.dirname(scene_dir), "mint_follower_demo"),
            ),
            DeclareLaunchArgument(
                "joint_map",
                default_value=os.path.join(scene_dir, "so101_official_to_urdf.yaml"),
            ),
            DeclareLaunchArgument("input_space", default_value="official-normalized"),
            DeclareLaunchArgument("rate", default_value="10.0"),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[{"robot_description": robot_description}],
                output="screen",
            ),
            ExecuteProcess(cmd=bridge_cmd, output="screen"),
            Node(
                package="rviz2",
                executable="rviz2",
                arguments=["-d", rviz_config],
                condition=IfCondition(use_rviz),
                output="screen",
            ),
        ]
    )
