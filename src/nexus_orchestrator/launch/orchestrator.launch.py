"""Launch the multimodal orchestrator node."""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='nexus_orchestrator',
            executable='orchestrator_node',
            name='nexus_orchestrator',
            output='screen',
        ),
    ])
