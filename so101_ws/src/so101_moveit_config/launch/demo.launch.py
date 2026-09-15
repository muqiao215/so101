import os
import re
import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def load_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
    desc_pkg = get_package_share_directory("so101_description")
    bringup_pkg = get_package_share_directory("so101_bringup")
    gazebo_pkg = get_package_share_directory("so101_gazebo")
    moveit_pkg = get_package_share_directory("so101_moveit_config")

    urdf_file = os.path.join(desc_pkg, "urdf", "so101.urdf")
    srdf_file = os.path.join(moveit_pkg, "config", "so101.srdf")
    kinematics_yaml = os.path.join(moveit_pkg, "config", "kinematics.yaml")
    ompl_yaml = os.path.join(moveit_pkg, "config", "ompl_planning.yaml")
    move_group_yaml = os.path.join(moveit_pkg, "config", "move_group.yaml")
    joint_limits_yaml = os.path.join(moveit_pkg, "config", "joint_limits.yaml")
    moveit_controllers_yaml = os.path.join(moveit_pkg, "config", "moveit_controllers.yaml")
    controllers_file = os.path.join(bringup_pkg, "config", "controllers.yaml")
    rviz_cfg = os.path.join(moveit_pkg, "rviz", "moveit.rviz")

    robot_description = _strip_xml_comments(
        load_file(urdf_file).replace("__CONTROLLERS_YAML__", controllers_file)
    )
    robot_description_semantic = load_file(srdf_file)

    use_rviz = LaunchConfiguration("use_rviz")
    use_gzclient = LaunchConfiguration("use_gzclient")
    enable_move_group = LaunchConfiguration("enable_move_group")
    controller_load_delay_sec = LaunchConfiguration("controller_load_delay_sec")

    # Launch Gazebo scene (gzserver + rsp + spawn_entity)
    gazebo_scene = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_pkg, "launch", "scene.launch.py")
        ),
        launch_arguments={
            "use_rsp": "false",
            "spawn_robot": "true",
            "use_gzclient": use_gzclient,
        }.items(),
    )

    kinematics_cfg = load_yaml(kinematics_yaml)
    ompl_cfg = load_yaml(ompl_yaml)
    move_group_cfg = load_yaml(move_group_yaml)
    joint_limits_cfg = load_yaml(joint_limits_yaml)
    moveit_controllers_cfg = load_yaml(moveit_controllers_yaml)

    move_group_parameters = [
        {"robot_description": robot_description},
        {"robot_description_semantic": robot_description_semantic},
        {"robot_description_kinematics": kinematics_cfg},
        ompl_cfg,
        move_group_cfg,
        {"robot_description_planning": joint_limits_cfg.get("joint_limits", {})},
        moveit_controllers_cfg,
        {"use_sim_time": True},
    ]

    # Controller manager only exists after gazebo_ros2_control has loaded
    # inside gzserver. We therefore delay the first spawner and give it a long
    # controller-manager timeout so cold starts in WSL do not fail fast.
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

    return LaunchDescription([
        DeclareLaunchArgument("use_rviz", default_value="true"),
        DeclareLaunchArgument("use_gzclient", default_value="true"),
        DeclareLaunchArgument("enable_move_group", default_value="false"),
        DeclareLaunchArgument("controller_load_delay_sec", default_value="35.0"),

        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            output="screen",
            parameters=[
                {"robot_description": robot_description},
                {"use_sim_time": True},
            ],
        ),

        gazebo_scene,

        # In this WSL/Gazebo setup the world file and /spawn_entity service can
        # take ~30s on a cold start, so controller loading must wait well past
        # the nominal spawn delay. Keep the delay explicit and tunable.
        TimerAction(
            period=controller_load_delay_sec,
            actions=[load_jsb],
        ),

        # Chain: after jsb loaded -> load jtc
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=load_jsb,
                on_exit=[load_jtc],
            )
        ),

        # Chain: after jtc loaded -> start move_group (if enabled)
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=load_jtc,
                on_exit=[
                    Node(
                        package="moveit_ros_move_group",
                        executable="move_group",
                        output="screen",
                        parameters=move_group_parameters,
                        condition=IfCondition(enable_move_group),
                    )
                ],
            )
        ),

        Node(
            package="rviz2",
            executable="rviz2",
            arguments=["-d", rviz_cfg],
            parameters=[
                {"robot_description": robot_description},
                {"robot_description_semantic": robot_description_semantic},
                {"robot_description_kinematics": kinematics_cfg},
                {"use_sim_time": True},
            ],
            condition=IfCondition(use_rviz),
            output="screen",
        ),
    ])
