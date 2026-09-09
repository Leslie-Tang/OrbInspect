"""Launch the greedy next-best-view inspection demo."""

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
    camera_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_perception'),
        'config',
        'camera.yaml',
    ])
    safety_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_safety'),
        'config',
        'safety.yaml',
    ])
    planner_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_guidance'),
        'config',
        'planner.yaml',
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
            description='Enable CSV logging for the greedy NBV demo.',
        ),
        Node(
            package='orbinspect_dynamics',
            executable='dynamics_node',
            name='hcw_dynamics_node',
            output='screen',
            parameters=[
                dynamics_config,
                {'initial_position_lvlh': [0.0, -24.0, 8.0]},
            ],
        ),
        Node(
            package='orbinspect_control',
            executable='controller_node',
            name='controller_node',
            output='screen',
            parameters=[
                control_config,
                {'publish_safe_command_passthrough': False},
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
            package='orbinspect_perception',
            executable='coverage_node',
            name='coverage_node',
            output='screen',
            parameters=[camera_config],
        ),
        Node(
            package='orbinspect_perception',
            executable='target_marker_node',
            name='target_marker_node',
            output='screen',
            parameters=[camera_config],
        ),
        Node(
            package='orbinspect_guidance',
            executable='inspection_planner_node',
            name='inspection_planner_node',
            output='screen',
            parameters=[planner_config],
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
