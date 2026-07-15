"""Launch the LLM decision brain node."""
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
                [FindPackageShare('nexus_brain'), 'config', 'params.yaml']
            ),
            description='Path to the brain params file',
        ),
        Node(
            package='nexus_brain',
            executable='llm_brain_node',
            name='llm_brain_node',
            output='screen',
            parameters=[params_file],
        ),
    ])
