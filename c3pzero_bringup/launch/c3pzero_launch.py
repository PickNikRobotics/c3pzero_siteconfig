# -*- coding: utf-8 -*-
import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import (
    OpaqueFunction,
    DeclareLaunchArgument,
    TimerAction,
    IncludeLaunchDescription,
)
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from ament_index_python.packages import get_package_share_directory
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition, UnlessCondition


def launch_setup(context, *args, **kwargs):

    # Configure launch arguments
    world = LaunchConfiguration("world")
    sim = LaunchConfiguration("sim")

    # Configure some helper variables and paths
    pkg_c3pzero_ignition = get_package_share_directory("c3pzero_ignition")
    pkg_c3pzero_navigation = get_package_share_directory("c3pzero_navigation")
    pkg_lidar = get_package_share_directory("hls_lfcd_lds_driver")
    pkg_driver = get_package_share_directory("c3pzero_driver")
    pkg_robot_description = get_package_share_directory("c3pzero_description")
    pkg_bringup = get_package_share_directory("c3pzero_bringup")

    # Hardware LIDAR
    lidar_launch_py = PythonLaunchDescriptionSource(
        [
            pkg_lidar,
            "/launch/hlds_laser.launch.py",
        ]
    )
    lidar_launch = IncludeLaunchDescription(
        lidar_launch_py,
        launch_arguments={
            "frame_id": "lidar_link",
        }.items(),
        condition=UnlessCondition(sim),
    )

    lidar_filter_node = Node(
        package="laser_filters",
        executable="scan_to_scan_filter_chain",
        name="laser_filters",
        output="both",
        parameters=[
            PathJoinSubstitution([pkg_bringup, "params", "angular_filter.yaml"])
        ],
        condition=UnlessCondition(sim),
    )

    # Hardware Driver
    driver_launch_py = PythonLaunchDescriptionSource(
        [
            pkg_driver,
            "/launch/driver.launch.py",
        ]
    )
    driver_launch = IncludeLaunchDescription(
        driver_launch_py,
        condition=UnlessCondition(sim),
    )

    # Parse xacro and publish robot state
    robot_description_path = os.path.join(
        pkg_robot_description, "urdf", "c3pzero_base.xacro"
    )

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            robot_description_path,
            " ",
            "simulation:=",
            sim,
            " ",
        ]
    )
    robot_description = {"robot_description": robot_description_content}

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="both",
        parameters=[robot_description, {"publish_frequency", "50"}],
        condition=UnlessCondition(sim),
    )

    # Bringup simulation world
    ignition_launch_py = PythonLaunchDescriptionSource(
        [
            pkg_c3pzero_ignition,
            "/launch/ignition.launch.py",
        ]
    )
    ignition_launch = IncludeLaunchDescription(
        ignition_launch_py,
        launch_arguments={
            "world": world,
        }.items(),
        condition=IfCondition(sim),
    )

    # Spawn simulated robot in Ignition Gazebo
    spawn_launch_py = PythonLaunchDescriptionSource(
        [
            pkg_c3pzero_ignition,
            "/launch/spawn_robot.launch.py",
        ]
    )
    spawn_launch = IncludeLaunchDescription(
        spawn_launch_py,
        launch_arguments={
            "rviz": "False",
        }.items(),
        condition=IfCondition(sim),
    )

    # Bringup Navigation2
    nav2_launch_py = PythonLaunchDescriptionSource(
        [
            pkg_c3pzero_navigation,
            "/launch/navigation.launch.py",
        ]
    )
    nav2_launch = IncludeLaunchDescription(
        nav2_launch_py,
    )

    nodes_and_launches = [
        robot_state_publisher_node,
        lidar_launch,
        lidar_filter_node,
        driver_launch,
        ignition_launch,
        TimerAction(period=15.0, actions=[spawn_launch]),
        TimerAction(period=5.0, actions=[nav2_launch]),
    ]

    return nodes_and_launches


def generate_launch_description():
    declared_arguments = []
    world_arg = DeclareLaunchArgument(
        "world",
        description="Name of world to display",
        choices=["empty", "simple", "house"],
        default_value="house",
    )
    sim_arg = DeclareLaunchArgument(
        "sim",
        description="If true launch simulation, else launch hardware",
        default_value="false",
    )
    declared_arguments.append(world_arg)
    declared_arguments.append(sim_arg)

    return LaunchDescription(
        declared_arguments + [OpaqueFunction(function=launch_setup)]
    )
