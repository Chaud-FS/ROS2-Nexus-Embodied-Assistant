"""Launch the Qwen-VL perception node."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params_file = LaunchConfiguration('params_file')
    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file',
            default_value=PathJoinSubstitution(
                [FindPackageShare('nexus_perception'), 'config', 'params.yaml']
            ),
            description='Path to the perception params file',
        ),
        Node(
            package='nexus_perception',
            executable='qwen_vl_node',
            name='qwen_vl_node',
            output='screen',
            parameters=[params_file],
        ),
    ])
