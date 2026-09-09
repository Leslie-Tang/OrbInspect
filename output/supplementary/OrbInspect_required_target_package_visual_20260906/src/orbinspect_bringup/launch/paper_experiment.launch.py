"""Launch a paper-style OrbInspect experiment."""

from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import ExecuteProcess
from launch.actions import OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from orbinspect_eval.experiment_index import create_experiment_layout
from orbinspect_eval.experiment_index import snapshot_configs
from orbinspect_eval.report_generator import write_experiment_manifest
from orbinspect_eval.rosbag_manager import rosbag_record_arguments


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument('scenario', default_value='full_station'),
        DeclareLaunchArgument('method', default_value='greedy_nbv_safety_filter'),
        DeclareLaunchArgument('record', default_value='true'),
        DeclareLaunchArgument('save_figures', default_value='true'),
        DeclareLaunchArgument('run_id', default_value=''),
        DeclareLaunchArgument('dynamics_backend', default_value='hcw'),
        OpaqueFunction(function=_launch_setup),
    ])


def _launch_setup(context, *_args, **_kwargs):
    scenario = LaunchConfiguration('scenario').perform(context)
    method = LaunchConfiguration('method').perform(context)
    record = LaunchConfiguration('record')
    save_figures = LaunchConfiguration('save_figures')
    run_id = LaunchConfiguration('run_id').perform(context)
    dynamics_backend = LaunchConfiguration('dynamics_backend').perform(context)

    dynamics_config = _share_file('orbinspect_dynamics', 'config', 'dynamics.yaml')
    control_config = _share_file('orbinspect_control', 'config', 'control.yaml')
    camera_config = _share_file('orbinspect_perception', 'config', 'camera.yaml')
    safety_config = _share_file('orbinspect_safety', 'config', 'safety.yaml')
    planner_config = _share_file('orbinspect_guidance', 'config', 'planner.yaml')
    eval_config = _share_file('orbinspect_eval', 'config', 'eval.yaml')
    rviz_config = _share_file('orbinspect_description', 'rviz', 'orbinspect_research.rviz')

    paths = create_experiment_layout(run_id=run_id)
    config_snapshots = snapshot_configs(
        paths,
        [
            _perform(context, dynamics_config),
            _perform(context, control_config),
            _perform(context, camera_config),
            _perform(context, safety_config),
            _perform(context, planner_config),
            _perform(context, eval_config),
        ],
    )
    write_experiment_manifest(
        paths.result_dir,
        scenario,
        method,
        dynamics_backend,
        config_snapshots,
    )
    resolved_run_id = paths.result_dir.name
    rosbag_output = str(paths.rosbag_dir / 'orbinspect_run')

    return [
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
            parameters=[
                eval_config,
                {
                    'run_id': resolved_run_id,
                    'reuse_run_id': True,
                    'save_figures': save_figures,
                },
            ],
            condition=IfCondition(record),
        ),
        ExecuteProcess(
            cmd=['ros2', *rosbag_record_arguments(rosbag_output)],
            output='screen',
            condition=IfCondition(record),
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
        ),
    ]


def _share_file(package: str, *parts: str) -> PathJoinSubstitution:
    return PathJoinSubstitution([FindPackageShare(package), *parts])


def _perform(context, substitution) -> str:
    return str(Path(substitution.perform(context)))
