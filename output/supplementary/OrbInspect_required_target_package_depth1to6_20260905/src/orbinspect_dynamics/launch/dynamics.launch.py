"""Launch the ROS-native HCW dynamics node."""

from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    config_file = PathJoinSubstitution([
        FindPackageShare('orbinspect_dynamics'),
        'config',
        'dynamics.yaml',
    ])

    return LaunchDescription([
        Node(
            package='orbinspect_dynamics',
            executable='dynamics_node',
            name='hcw_dynamics_node',
            output='screen',
            parameters=[config_file],
        ),
    ])
