"""Top-level launch: bring up the whole Nexus Embodied Assistant.

Starts, in order:
  * Gazebo + Nexus arm (nexus_description)
  * MoveIt2 move_group (nexus_moveit_config)
  * Qwen-VL perception (nexus_perception)
  * Voice STT/TTS (nexus_voice)
  * LLM brain (nexus_brain)
  * Multimodal orchestrator (nexus_orchestrator)
"""
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def _include(pkg, launch_file):
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare(pkg), 'launch', launch_file])
        )
    )


def generate_launch_description():
    return LaunchDescription([
        _include('nexus_description', 'gazebo.launch.py'),
        # Give Gazebo time to spawn controllers before MoveIt queries them.
        TimerAction(period=10.0, actions=[
            _include('nexus_moveit_config', 'moveit.launch.py'),
        ]),
        _include('nexus_perception', 'perception.launch.py'),
        _include('nexus_voice', 'voice.launch.py'),
        _include('nexus_brain', 'brain.launch.py'),
        TimerAction(period=12.0, actions=[
            _include('nexus_orchestrator', 'orchestrator.launch.py'),
        ]),
    ])
