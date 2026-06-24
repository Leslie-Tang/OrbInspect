"""Validate proposed offline trajectory and viewpoints in Gazebo and RViz."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import AnonName
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    result_dir = LaunchConfiguration('result_dir')
    method = LaunchConfiguration('method')
    trajectory_source = LaunchConfiguration('trajectory_source')
    time_scale = LaunchConfiguration('time_scale')
    loop = LaunchConfiguration('loop')
    stop_before_time = LaunchConfiguration('stop_before_time')
    gz_partition = LaunchConfiguration('gz_partition')
    publish_mode = LaunchConfiguration('publish_mode')
    record = LaunchConfiguration('record')

    gazebo_launch = PathJoinSubstitution([
        FindPackageShare('orbinspect_gazebo'),
        'launch',
        'gazebo_iss_real.launch.py',
    ])
    spawn_chaser_launch = PathJoinSubstitution([
        FindPackageShare('orbinspect_gazebo'),
        'launch',
        'spawn_cubesat_chaser.launch.py',
    ])
    rviz_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_description'),
        'rviz',
        'orbinspect_trajectory_validation.rviz',
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'result_dir',
            default_value='data/results/offline_high_coverage_experiment',
            description='Offline planning result directory containing raw CSV files.',
        ),
        DeclareLaunchArgument(
            'method',
            default_value='set_cover_cw_tour',
            description='Method row to replay from trajectory/viewpoint CSV files.',
        ),
        DeclareLaunchArgument(
            'trajectory_source',
            default_value='standoff',
            description='Use csv for raw planner trajectory or standoff for mesh-safe validation.',
        ),
        DeclareLaunchArgument(
            'time_scale',
            default_value='1.0',
            description='Replay speed multiplier relative to planned mission time.',
        ),
        DeclareLaunchArgument(
            'loop',
            default_value='false',
            description='Loop the replay after the final trajectory sample.',
        ),
        DeclareLaunchArgument(
            'stop_before_time',
            default_value='0.0',
            description=(
                'Only replay samples before this planned time; 0 disables clipping. '
                'Default avoids the known mesh-clearance violation in the current run.'
            ),
        ),
        DeclareLaunchArgument(
            'gz_partition',
            default_value=AnonName('orbinspect_proposed_validation'),
            description='Gazebo Transport partition for this validation run.',
        ),
        DeclareLaunchArgument(
            'publish_mode',
            default_value='closed_loop',
            description='closed_loop uses HCW dynamics; replay directly publishes odometry.',
        ),
        DeclareLaunchArgument(
            'record',
            default_value='true',
            description='Enable paper-grade planned-vs-executed CSV logging.',
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gazebo_launch),
            launch_arguments={'gz_partition': gz_partition}.items(),
        ),
        Node(
            package='orbinspect_dynamics',
            executable='dynamics_node',
            name='hcw_dynamics_node',
            output='screen',
            parameters=[{
                'initial_position_lvlh': [0.004700701439663278, -105.76186219724731, 30.23951855559007],
                'initial_velocity_lvlh': [0.0, 0.0, 0.0],
                'integration_dt': 0.05,
                'publish_rate': 20.0,
            }],
        ),
        Node(
            package='orbinspect_control',
            executable='controller_node',
            name='trajectory_tracking_controller',
            output='screen',
            parameters=[{
                'controller_type': 'mpc',
                'position_gain': 0.0015,
                'velocity_gain': 0.10,
                'max_acceleration': 0.03,
                'control_rate': 20.0,
                'mean_motion': 0.0011313666536110225,
                'lqr_state_weights': [1.0, 1.0, 1.0, 120.0, 120.0, 120.0],
                'lqr_control_weights': [1800.0, 1800.0, 1800.0],
                'riccati_iterations': 300,
                'mpc_horizon': 8,
                'mpc_max_iterations': 35,
                'default_reference': [0.004700701439663278, -105.76186219724731, 30.23951855559007],
                'frame_id': 'lvlh',
                'publish_safe_command_passthrough': False,
            }],
        ),
        Node(
            package='orbinspect_safety',
            executable='safety_filter_node',
            name='safety_filter_node',
            output='screen',
            parameters=[{
                'safety_margin': 2.0,
                'caution_margin': 8.0,
                'max_acceleration': 0.03,
                'max_speed': 0.35,
                'repulsion_gain': 0.004,
                'braking_time': 4.0,
                'frame_id': 'lvlh',
            }],
        ),
        Node(
            package='orbinspect_guidance',
            executable='planned_trajectory_replay_node',
            name='planned_trajectory_replay_node',
            output='screen',
            parameters=[{
                'result_dir': result_dir,
                'method': method,
                'trajectory_source': trajectory_source,
                'time_scale': time_scale,
                'loop': loop,
                'stop_before_time': stop_before_time,
                'publish_mode': publish_mode,
                'max_reference_speed': 0.08,
                'max_reference_acceleration': 0.01,
            }],
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(spawn_chaser_launch),
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
            package='orbinspect_eval',
            executable='logger_node',
            name='csv_logger_node',
            output='screen',
            parameters=[{
                'result_root': 'data/results',
                'run_id': '',
                'max_acceleration': 0.03,
                'default_reference': [0.004700701439663278, -105.76186219724731, 30.23951855559007],
                'save_figures': True,
            }],
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
