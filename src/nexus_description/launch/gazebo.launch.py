"""Launch the Nexus arm inside Gazebo with ros2_control controllers."""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_share = FindPackageShare('nexus_description')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    xacro_file = PathJoinSubstitution([pkg_share, 'urdf', 'nexus_arm.urdf.xacro'])
    world_file = PathJoinSubstitution([pkg_share, 'worlds', 'nexus_world.sdf'])

    robot_description = {
        'robot_description': Command(['xacro ', xacro_file]),
        'use_sim_time': use_sim_time,
    }

    # --- Gazebo ---
    gazebo = ExecuteProcess(
        cmd=['gazebo', '--verbose', '-s', 'libgazebo_ros_factory.so', world_file],
        output='screen',
    )

    # --- Robot state publisher ---
    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[robot_description],
        output='screen',
    )

    # --- Spawn the robot into Gazebo (table height = 0.45) ---
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', '-entity', 'nexus_arm',
                   '-x', '0.0', '-y', '0.0', '-z', '0.45'],
        output='screen',
    )

    # --- Controllers ---
    jsp_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/nexus/controller_manager'],
        output='screen',
    )
    arm_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller', '--controller-manager', '/nexus/controller_manager'],
        output='screen',
    )
    gripper_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['gripper_controller', '--controller-manager', '/nexus/controller_manager'],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true',
                              description='Use simulation (Gazebo) clock'),
        gazebo,
        rsp,
        spawn_entity,
        # Give Gazebo a moment to bring up the ros2_control plugin before spawning controllers.
        TimerAction(period=8.0, actions=[jsp_broadcaster, arm_spawner, gripper_spawner]),
    ])
