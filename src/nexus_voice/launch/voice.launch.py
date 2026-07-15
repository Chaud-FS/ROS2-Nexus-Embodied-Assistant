"""Launch the voice module (STT + TTS)."""
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
                [FindPackageShare('nexus_voice'), 'config', 'params.yaml']
            ),
            description='Path to the voice params file',
        ),
        Node(
            package='nexus_voice',
            executable='stt_node',
            name='stt_node',
            output='screen',
            parameters=[params_file],
        ),
        Node(
            package='nexus_voice',
            executable='tts_node',
            name='tts_node',
            output='screen',
            parameters=[params_file],
        ),
    ])
