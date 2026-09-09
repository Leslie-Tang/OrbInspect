"""Launch optional Basilisk backend demo or the default HCW fallback."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch.substitutions import PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    dynamics_backend = LaunchConfiguration('dynamics_backend')
    dynamics_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_dynamics'),
        'config',
        'dynamics.yaml',
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'dynamics_backend',
            default_value='hcw',
            description='Dynamics backend: hcw or basilisk.',
        ),
        Node(
            package='orbinspect_dynamics',
            executable='dynamics_node',
            name='hcw_dynamics_node',
            output='screen',
            parameters=[dynamics_config],
            condition=IfCondition(PythonExpression([
                "'",
                dynamics_backend,
                "' == 'hcw'",
            ])),
        ),
        Node(
            package='orbinspect_dynamics',
            executable='basilisk_adapter_node',
            name='basilisk_adapter_node',
            output='screen',
            condition=IfCondition(PythonExpression([
                "'",
                dynamics_backend,
                "' == 'basilisk'",
            ])),
        ),
    ])
