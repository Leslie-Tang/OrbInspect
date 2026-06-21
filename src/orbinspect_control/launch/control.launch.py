"""Launch the Phase 3 baseline controller and fixed reference publisher."""

from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    config_file = PathJoinSubstitution([
        FindPackageShare('orbinspect_control'),
        'config',
        'control.yaml',
    ])

    return LaunchDescription([
        Node(
            package='orbinspect_control',
            executable='controller_node',
            name='controller_node',
            output='screen',
            parameters=[config_file],
        ),
        Node(
            package='orbinspect_control',
            executable='reference_publisher_node',
            name='reference_publisher_node',
            output='screen',
            parameters=[config_file],
        ),
    ])
