"""Launch robot_state_publisher + RViz to inspect the Nexus arm (no physics)."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_share = FindPackageShare('nexus_description')
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    xacro_file = PathJoinSubstitution([pkg_share, 'urdf', 'nexus_arm.urdf.xacro'])

    robot_description = {
        'robot_description': Command(['xacro ', xacro_file]),
        'use_sim_time': use_sim_time,
    }

    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[robot_description],
        output='screen',
    )

    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen',
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', PathJoinSubstitution([pkg_share, 'rviz', 'nexus_arm.rviz'])],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='Use simulation clock'),
        rsp,
        joint_state_publisher_gui,
        rviz,
    ])
