import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    bringup_pkg = get_package_share_directory("so101_bringup")
    gazebo_pkg = get_package_share_directory("so101_gazebo")

    rviz_config = os.path.join(
        get_package_share_directory("so101_description"), "rviz", "display.rviz"
    )
    waypoints_file = os.path.join(bringup_pkg, "config", "waypoints.yaml")

    use_rviz = LaunchConfiguration("use_rviz")
    use_gzclient = LaunchConfiguration("use_gzclient")
    use_mock_yolo = LaunchConfiguration("use_mock_yolo")
    enable_rosbridge = LaunchConfiguration("enable_rosbridge")
    detection_trigger_enabled = LaunchConfiguration("detection_trigger_enabled")
    detection_confidence_threshold = LaunchConfiguration("detection_confidence_threshold")
    detection_trigger_cooldown_sec = LaunchConfiguration("detection_trigger_cooldown_sec")
    detection_template_map_json = LaunchConfiguration("detection_template_map_json")
    controller_load_delay_sec = LaunchConfiguration("controller_load_delay_sec")

    gazebo_scene = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_pkg, "launch", "scene.launch.py")
        ),
        launch_arguments={
            "use_rsp": "true",
            "spawn_robot": "true",
            "use_gzclient": use_gzclient,
        }.items(),
    )

    load_jsb = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "120",
        ],
        output="screen",
    )

    load_jtc = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_trajectory_controller",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "120",
        ],
        output="screen",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_rviz", default_value="true"),
            DeclareLaunchArgument("use_gzclient", default_value="false"),
            DeclareLaunchArgument("use_mock_yolo", default_value="true"),
            DeclareLaunchArgument("enable_rosbridge", default_value="true"),
            DeclareLaunchArgument("detection_trigger_enabled", default_value="true"),
            DeclareLaunchArgument("detection_confidence_threshold", default_value="0.5"),
            DeclareLaunchArgument("detection_trigger_cooldown_sec", default_value="8.0"),
            DeclareLaunchArgument("controller_load_delay_sec", default_value="20.0"),
            DeclareLaunchArgument(
                "detection_template_map_json",
                default_value='{"red":"pick_place_red","blue":"pick_place_blue"}',
            ),
            gazebo_scene,
            TimerAction(
                period=controller_load_delay_sec,
                actions=[load_jsb],
            ),
            RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=load_jsb,
                    on_exit=[load_jtc],
                )
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                arguments=["-d", rviz_config],
                condition=IfCondition(use_rviz),
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
