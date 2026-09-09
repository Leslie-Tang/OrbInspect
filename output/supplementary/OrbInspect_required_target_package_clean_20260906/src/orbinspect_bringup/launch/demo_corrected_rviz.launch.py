"""Launch the accepted mesh-safe RViz/Gazebo verification demo."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import AnonName
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    """Provide a zero-required-argument entry point for the corrected demo."""
    result_dir = LaunchConfiguration('result_dir')
    scenario_id = LaunchConfiguration('scenario_id')
    method = LaunchConfiguration('method')
    time_scale = LaunchConfiguration('time_scale')
    visual_startup_delay = LaunchConfiguration('visual_startup_delay')
    gz_partition = LaunchConfiguration('gz_partition')
    run_id = LaunchConfiguration('run_id')
    record_bag = LaunchConfiguration('record_bag')

    verification_launch = PathJoinSubstitution([
        FindPackageShare('orbinspect_bringup'),
        'launch',
        'ros_verification.launch.py',
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'result_dir',
            default_value=(
                'data/results/'
                'ros_verification_input_validation002_radius080_20260812'
            ),
            description='Corrected frozen-route input bundle.',
        ),
        DeclareLaunchArgument(
            'scenario_id',
            default_value='validation_002',
            description='Accepted mesh-safe demonstration scenario.',
        ),
        DeclareLaunchArgument(
            'method',
            default_value='adaptive_rollout_adp',
            description='Planner route to verify.',
        ),
        DeclareLaunchArgument(
            'time_scale',
            default_value='5.0',
            description='Mission-time acceleration for the visual demo.',
        ),
        DeclareLaunchArgument(
            'visual_startup_delay',
            default_value='10.0',
            description='Seconds allowed for Gazebo and RViz to open.',
        ),
        DeclareLaunchArgument(
            'gz_partition',
            default_value=AnonName('orbinspect_corrected_rviz'),
            description='Unique Gazebo Transport partition.',
        ),
        DeclareLaunchArgument(
            'run_id',
            default_value='',
            description='Optional result directory name; blank is collision-safe.',
        ),
        DeclareLaunchArgument(
            'record_bag',
            default_value='true',
            description='Record the paper-grade ROS 2 topic archive.',
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(verification_launch),
            launch_arguments={
                'result_dir': result_dir,
                'scenario_id': scenario_id,
                'method': method,
                'publish_mode': 'closed_loop',
                'record': 'true',
                'record_bag': record_bag,
                'headless': 'false',
                'allow_accelerated_visualization': 'true',
                'gz_partition': gz_partition,
                'visual_startup_delay': visual_startup_delay,
                'save_figures': 'false',
                'time_scale': time_scale,
                'run_id': run_id,
            }.items(),
        ),
    ])
