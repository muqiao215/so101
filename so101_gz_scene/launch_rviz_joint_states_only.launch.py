import os
import re

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _strip_xml_comments(xml_str):
    return re.sub(r"<!--.*?-->", "", xml_str, flags=re.DOTALL)


def generate_launch_description():
    scene_dir = os.path.dirname(os.path.abspath(__file__))
    desc_share = get_package_share_directory("so101_description")
    urdf = os.path.join(desc_share, "urdf", "so101.urdf")
    rviz_config = os.path.join(scene_dir, "so101_kinematic.rviz")

    with open(urdf, encoding="utf-8") as fh:
        robot_description = _strip_xml_comments(fh.read())

    use_rviz = LaunchConfiguration("use_rviz")

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_rviz", default_value="true"),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[{"robot_description": robot_description}],
                output="screen",
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                arguments=["-d", rviz_config],
                condition=IfCondition(use_rviz),
                output="screen",
            ),
        ]
    )
