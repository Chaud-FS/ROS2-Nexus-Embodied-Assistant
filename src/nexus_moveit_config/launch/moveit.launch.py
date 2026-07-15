"""Launch MoveIt2 move_group for the Nexus arm.

Assumes the robot has already been spawned into Gazebo
(ros2 launch nexus_description gazebo.launch.py) so that
joint states and the controllers are available.
"""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Robot description comes from the description package.
    description_pkg = get_package_share_directory('nexus_description')
    xacro_path = os.path.join(description_pkg, 'urdf', 'nexus_arm.urdf.xacro')
    robot_description = {'robot_description': Command(['xacro ', xacro_path])}

    moveit_config = MoveItConfigsBuilder(
        'nexus_arm', package_name='nexus_moveit_config'
    ).to_moveit_configs()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[robot_description, {'use_sim_time': use_sim_time}],
        output='screen',
    )

    move_group = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        name='move_group',
        output='screen',
        parameters=[
            robot_description,
            moveit_config.to_dict(),
            {'use_sim_time': use_sim_time},
        ],
        arguments=['--ros-args', '--log-level', 'WARN'],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        parameters=[
            robot_description,
            moveit_config.planning_pipelines,
            moveit_config.robot_description_semantic,
            moveit_config.kinematics,
            {'use_sim_time': use_sim_time},
        ],
        arguments=['-d', os.path.join(
            get_package_share_directory('nexus_moveit_config'),
            'config', 'moveit.rviz')] if os.path.exists(
            os.path.join(get_package_share_directory('nexus_moveit_config'),
                         'config', 'moveit.rviz')) else [],
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true',
                              description='Use simulation clock'),
        robot_state_publisher,
        move_group,
        rviz,
    ])
