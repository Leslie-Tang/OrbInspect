"""Launch one frozen-route replay or closed-loop verification run."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import EmitEvent
from launch.actions import ExecuteProcess
from launch.actions import IncludeLaunchDescription
from launch.actions import OpaqueFunction
from launch.actions import TimerAction
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from orbinspect_eval.experiment_index import create_experiment_layout
from orbinspect_eval.rosbag_manager import rosbag_record_arguments


def generate_launch_description() -> LaunchDescription:
    """Declare the frozen verification launch interface."""
    return LaunchDescription([
        DeclareLaunchArgument('result_dir'),
        DeclareLaunchArgument('scenario_id'),
        DeclareLaunchArgument(
            'method',
            default_value='adaptive_rollout_adp',
        ),
        DeclareLaunchArgument(
            'publish_mode',
            default_value='closed_loop',
        ),
        DeclareLaunchArgument('record', default_value='true'),
        DeclareLaunchArgument('record_bag', default_value='false'),
        DeclareLaunchArgument('headless', default_value='true'),
        DeclareLaunchArgument(
            'allow_accelerated_visualization',
            default_value='false',
        ),
        DeclareLaunchArgument(
            'gz_partition',
            default_value='orbinspect_real_iss',
        ),
        DeclareLaunchArgument('visual_startup_delay', default_value='0.0'),
        DeclareLaunchArgument('save_figures', default_value='true'),
        DeclareLaunchArgument('time_scale', default_value='1.0'),
        DeclareLaunchArgument('run_id', default_value=''),
        OpaqueFunction(function=_launch_setup),
    ])


def _launch_setup(context, *_args, **_kwargs):
    result_dir = _workspace_path(
        LaunchConfiguration('result_dir').perform(context)
    )
    scenario_id = LaunchConfiguration('scenario_id').perform(context)
    method = LaunchConfiguration('method').perform(context)
    publish_mode = LaunchConfiguration('publish_mode').perform(context)
    record = _as_bool(LaunchConfiguration('record').perform(context))
    record_bag = _as_bool(LaunchConfiguration('record_bag').perform(context))
    headless = _as_bool(LaunchConfiguration('headless').perform(context))
    allow_accelerated_visualization = _as_bool(
        LaunchConfiguration(
            'allow_accelerated_visualization'
        ).perform(context)
    )
    gz_partition = LaunchConfiguration('gz_partition').perform(context)
    save_figures = _as_bool(
        LaunchConfiguration('save_figures').perform(context)
    )
    requested_run_id = LaunchConfiguration('run_id').perform(context)
    time_scale = float(LaunchConfiguration('time_scale').perform(context))
    visual_startup_delay = float(
        LaunchConfiguration('visual_startup_delay').perform(context)
    )
    if time_scale <= 0.0:
        raise ValueError('time_scale must be positive')
    if visual_startup_delay < 0.0:
        raise ValueError('visual_startup_delay must be non-negative')
    if headless and visual_startup_delay > 0.0:
        raise ValueError('visual_startup_delay requires headless=false')
    accelerated = time_scale > 1.0 + 1.0e-9
    if accelerated and not headless and not allow_accelerated_visualization:
        raise ValueError(
            'accelerated visualization requires '
            'allow_accelerated_visualization=true'
        )
    if publish_mode not in {'replay', 'closed_loop'}:
        raise ValueError('publish_mode must be replay or closed_loop')

    input_manifest_path = result_dir / 'manifest.json'
    if not input_manifest_path.is_file():
        raise FileNotFoundError(input_manifest_path)
    input_manifest = json.loads(input_manifest_path.read_text())
    matching = [
        route for route in input_manifest['routes']
        if route['scenario_id'] == scenario_id
        and route['method'] == method
    ]
    if len(matching) != 1:
        raise ValueError(
            f'expected one route for {scenario_id}/{method}, found {len(matching)}'
        )
    route = matching[0]
    initial_state = [float(value) for value in route['initial_state']]
    run_id = requested_run_id or (
        f'ros_{publish_mode}_{scenario_id}_{method}'
    )
    paths = create_experiment_layout(run_id=run_id)

    verification_config = _share_file(
        'orbinspect_guidance',
        'config',
        'ros_verification.yaml',
    ).perform(context)
    shutil.copy2(
        verification_config,
        paths.config_snapshot_dir / 'ros_verification.yaml',
    )
    shutil.copy2(
        input_manifest_path,
        paths.config_snapshot_dir / 'input_manifest.json',
    )
    run_manifest = {
        'schema_version': 'orbinspect-ros-verification-run/v1',
        'scenario_id': scenario_id,
        'split': route['split'],
        'scenario_seed': route['scenario_seed'],
        'method': method,
        'publish_mode': publish_mode,
        'record_csv': record,
        'record_bag': record_bag,
        'headless': headless,
        'allow_accelerated_visualization': (
            allow_accelerated_visualization
        ),
        'gz_partition': gz_partition,
        'visual_startup_delay_s': visual_startup_delay,
        'time_scale': time_scale,
        'clock_mode': 'accelerated_sim_time' if accelerated else 'wall_time',
        'source_result_root': input_manifest['source_result_root'],
        'source_graph_hash': input_manifest[
            'source_files_sha256'
        ]['hcw_graph.json'],
        'source_scenario_hash': input_manifest[
            'source_files_sha256'
        ]['scenarios.json'],
        'source_route_hash': _route_hash(route),
        'safety_margin_m': input_manifest.get('safety_margin', 2.0),
        'vehicle_bounding_radius_m': input_manifest.get(
            'vehicle_bounding_radius',
            0.80,
        ),
        'mesh_transform': input_manifest.get(
            'mesh_transform',
            'legacy_translation_only_unknown',
        ),
        'input_bundle': str(result_dir),
        'input_manifest_sha256': _sha256(input_manifest_path),
        'configuration_sha256': _sha256(Path(verification_config)),
        'git_revision': input_manifest['git_revision'],
        'initial_state': initial_state,
        'planned_duration_s': route['duration_s'],
        'planned_action_count': route['action_count'],
    }
    run_manifest.update(_execution_source_state())
    (paths.config_snapshot_dir / 'run_manifest.json').write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True)
    )
    (paths.config_snapshot_dir / 'environment.json').write_text(
        json.dumps(_environment_snapshot(), indent=2, sort_keys=True) + '\n'
    )

    common = {
        'use_sim_time': accelerated,
    }
    replay_parameters = [
        verification_config,
        common,
        {
            'result_dir': str(result_dir),
            'scenario_id': scenario_id,
            'method': method,
            'publish_mode': publish_mode,
            'trajectory_source': 'csv',
            'loop': False,
            'time_scale': 1.0,
        },
    ]
    mission_actions = []
    if accelerated:
        mission_actions.append(Node(
            package='orbinspect_utils',
            executable='accelerated_clock_node',
            name='accelerated_clock_node',
            output='screen',
            parameters=[{
                'use_sim_time': False,
                'time_scale': time_scale,
                'wall_publish_rate': max(200.0, 20.0 * time_scale),
            }],
        ))
    mission_actions.extend([
        Node(
            package='orbinspect_guidance',
            executable='planned_trajectory_replay_node',
            name='planned_trajectory_replay_node',
            output='screen',
            parameters=replay_parameters,
        ),
        Node(
            package='orbinspect_guidance',
            executable='verification_evaluator_node',
            name='verification_evaluator_node',
            output='screen',
            parameters=[
                verification_config,
                common,
                {
                    'result_dir': str(result_dir),
                    'scenario_id': scenario_id,
                    'method': method,
                },
            ],
        ),
    ])

    if publish_mode == 'closed_loop':
        mission_actions.extend([
            Node(
                package='orbinspect_dynamics',
                executable='dynamics_node',
                name='hcw_dynamics_node',
                output='screen',
                parameters=[
                    verification_config,
                    common,
                    {
                        'initial_position_lvlh': initial_state[:3],
                        'initial_velocity_lvlh': initial_state[3:],
                    },
                ],
            ),
            Node(
                package='orbinspect_control',
                executable='controller_node',
                name='trajectory_tracking_controller',
                output='screen',
                parameters=[
                    verification_config,
                    common,
                    {'default_reference': initial_state[:3]},
                ],
            ),
            Node(
                package='orbinspect_safety',
                executable='safety_filter_node',
                name='safety_filter_node',
                output='screen',
                parameters=[verification_config, common],
            ),
        ])

    if record:
        mission_actions.append(
            Node(
                package='orbinspect_eval',
                executable='logger_node',
                name='csv_logger_node',
                output='screen',
                parameters=[
                    verification_config,
                    common,
                    {
                        'result_root': str(paths.result_dir.parent),
                        'run_id': paths.result_dir.name,
                        'reuse_run_id': True,
                        'save_figures': save_figures,
                        'default_reference': initial_state[:3],
                    },
                ],
            )
        )
    if record_bag:
        mission_actions.append(
            ExecuteProcess(
                cmd=[
                    'ros2',
                    *rosbag_record_arguments(
                        str(paths.rosbag_dir / 'orbinspect_run')
                    ),
                ],
                output='screen',
            )
        )

    actions = []
    if not headless:
        gazebo_launch = _share_file(
            'orbinspect_gazebo',
            'launch',
            'gazebo_iss_real.launch.py',
        )
        spawn_launch = _share_file(
            'orbinspect_gazebo',
            'launch',
            'spawn_cubesat_chaser.launch.py',
        )
        rviz_config = _share_file(
            'orbinspect_description',
            'rviz',
            'orbinspect_trajectory_validation.rviz',
        )
        actions.extend([
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(gazebo_launch),
                launch_arguments={'gz_partition': gz_partition}.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(spawn_launch),
                launch_arguments={'gz_partition': gz_partition}.items(),
            ),
            Node(
                package='ros_gz_bridge',
                executable='parameter_bridge',
                name='chaser_inspection_camera_bridge',
                output='screen',
                arguments=[
                    '/chaser/camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
                ],
                additional_env={'GZ_PARTITION': gz_partition},
            ),
            Node(
                package='rviz2',
                executable='rviz2',
                name='rviz2',
                output='screen',
                arguments=['-d', rviz_config],
                parameters=[common],
            ),
        ])

    if visual_startup_delay > 0.0:
        actions.append(TimerAction(
            period=visual_startup_delay,
            actions=mission_actions,
        ))
    else:
        actions.extend(mission_actions)

    actions.append(TimerAction(
        period=(
            visual_startup_delay
            + float(route['duration_s']) / time_scale
            + 10.0
        ),
        actions=[EmitEvent(event=Shutdown(
            reason='frozen verification route completed'
        ))],
    ))
    return actions


def _share_file(package: str, *parts: str) -> PathJoinSubstitution:
    return PathJoinSubstitution([FindPackageShare(package), *parts])


def _workspace_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _command_output(command: list[str]) -> str:
    """Return normalized diagnostic command output without failing launch."""
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=10.0,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return f'unavailable: {error}'
    output = completed.stdout.strip() or completed.stderr.strip()
    return output or f'exit_code={completed.returncode}'


def _execution_source_state() -> dict[str, object]:
    """Capture the actual execution checkout in addition to input provenance."""
    revision = _command_output(['git', 'rev-parse', 'HEAD'])
    status = _command_output(['git', 'status', '--porcelain=v1'])
    if status == 'exit_code=0':
        status = ''
    return {
        'execution_git_revision': revision,
        'execution_git_dirty': bool(status),
        'execution_git_status': status.splitlines(),
    }


def _environment_snapshot() -> dict[str, object]:
    """Capture the Ubuntu, ROS, Gazebo, RViz, Python, and CPU environment."""
    os_release: dict[str, str] = {}
    os_release_path = Path('/etc/os-release')
    if os_release_path.is_file():
        for line in os_release_path.read_text(encoding='utf-8').splitlines():
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            os_release[key] = value.strip().strip('"')
    cpu_model = ''
    cpuinfo_path = Path('/proc/cpuinfo')
    if cpuinfo_path.is_file():
        for line in cpuinfo_path.read_text(encoding='utf-8').splitlines():
            if line.lower().startswith('model name') and ':' in line:
                cpu_model = line.split(':', 1)[1].strip()
                break
    packages = _command_output([
        'dpkg-query', '-W', '-f=${Package}\t${Version}\n',
        'ros-jazzy-ros-base',
        'ros-jazzy-rviz2',
        'ros-jazzy-ros-gz-sim',
    ])
    return {
        'schema_version': 'orbinspect-environment/v1',
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'os_release': os_release,
        'kernel': platform.release(),
        'machine': platform.machine(),
        'cpu_model': cpu_model,
        'python_version': sys.version,
        'ros_distro': os.environ.get('ROS_DISTRO', ''),
        'ros_version': os.environ.get('ROS_VERSION', ''),
        'rmw_implementation': os.environ.get('RMW_IMPLEMENTATION', ''),
        'gazebo_sim_version': _command_output(['gz', 'sim', '--versions']),
        'ros_package_versions': packages.splitlines(),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _route_hash(route: dict[str, object]) -> str:
    payload = json.dumps(route, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode()).hexdigest()
