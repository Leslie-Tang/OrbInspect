"""Launch the ROS-native safety monitor and filter demo."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    record = LaunchConfiguration('record')
    dynamics_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_dynamics'),
        'config',
        'dynamics.yaml',
    ])
    control_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_control'),
        'config',
        'control.yaml',
    ])
    safety_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_safety'),
        'config',
        'safety.yaml',
    ])
    eval_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_eval'),
        'config',
        'eval.yaml',
    ])
    rviz_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_description'),
        'rviz',
        'orbinspect_research.rviz',
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'record',
            default_value='true',
            description='Enable CSV logging for the safety filter demo.',
        ),
        Node(
            package='orbinspect_dynamics',
            executable='dynamics_node',
            name='hcw_dynamics_node',
            output='screen',
            parameters=[
                dynamics_config,
                {'initial_position_lvlh': [20.0, -7.0, 0.0]},
            ],
        ),
        Node(
            package='orbinspect_control',
            executable='controller_node',
            name='controller_node',
            output='screen',
            parameters=[
                control_config,
                {
                    'default_reference': [20.0, 0.0, 0.0],
                    'publish_safe_command_passthrough': False,
                },
            ],
        ),
        Node(
            package='orbinspect_safety',
            executable='safety_monitor_node',
            name='safety_monitor_node',
            output='screen',
            parameters=[safety_config],
        ),
        Node(
            package='orbinspect_safety',
            executable='safety_filter_node',
            name='safety_filter_node',
            output='screen',
            parameters=[safety_config],
        ),
        Node(
            package='orbinspect_eval',
            executable='logger_node',
            name='csv_logger_node',
            output='screen',
            parameters=[eval_config],
            condition=IfCondition(record),
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
        ),
    ])
