"""Launch the first closed-loop fixed waypoint inspection mission."""

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
    mission_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_mission'),
        'config',
        'mission_default.yaml',
    ])
    rviz_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_description'),
        'rviz',
        'orbinspect_research.rviz',
    ])
    eval_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_eval'),
        'config',
        'eval.yaml',
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'record',
            default_value='true',
            description='Enable CSV logging for the fixed waypoint mission.',
        ),
        Node(
            package='orbinspect_dynamics',
            executable='dynamics_node',
            name='hcw_dynamics_node',
            output='screen',
            parameters=[
                dynamics_config,
                {'initial_position_lvlh': [0.0, -22.0, 6.0]},
            ],
        ),
        Node(
            package='orbinspect_control',
            executable='controller_node',
            name='controller_node',
            output='screen',
            parameters=[control_config],
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
            package='orbinspect_mission',
            executable='mission_manager_node',
            name='mission_manager_node',
            output='screen',
            parameters=[mission_config],
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
