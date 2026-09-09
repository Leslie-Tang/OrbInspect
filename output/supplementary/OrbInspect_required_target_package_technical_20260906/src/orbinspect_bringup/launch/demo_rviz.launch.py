"""Launch the ROS-only HCW dynamics, controller, logger, and RViz demo."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    record = LaunchConfiguration('record')
    dynamics_launch = PathJoinSubstitution([
        FindPackageShare('orbinspect_dynamics'),
        'launch',
        'dynamics.launch.py',
    ])
    control_launch = PathJoinSubstitution([
        FindPackageShare('orbinspect_control'),
        'launch',
        'control.launch.py',
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
            default_value='false',
            description='Enable paper-grade CSV logging.',
        ),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(dynamics_launch)),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(control_launch)),
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
