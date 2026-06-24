"""Launch real ISS visual mesh demo with offline CW-aware trajectory guidance."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import AnonName
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    gz_partition = LaunchConfiguration('gz_partition')
    gazebo_launch = PathJoinSubstitution([
        FindPackageShare('orbinspect_gazebo'),
        'launch',
        'gazebo_iss_real.launch.py',
    ])
    dynamics_launch = PathJoinSubstitution([
        FindPackageShare('orbinspect_dynamics'),
        'launch',
        'dynamics.launch.py',
    ])
    spawn_chaser_launch = PathJoinSubstitution([
        FindPackageShare('orbinspect_gazebo'),
        'launch',
        'spawn_cubesat_chaser.launch.py',
    ])
    control_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_control'),
        'config',
        'control.yaml',
    ])
    trajectory_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_guidance'),
        'config',
        'offline_trajectory.yaml',
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'gz_partition',
            default_value=AnonName('orbinspect_real_iss_trajectory'),
            description='Gazebo Transport partition for this demo run.',
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gazebo_launch),
            launch_arguments={'gz_partition': gz_partition}.items(),
        ),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(dynamics_launch)),
        Node(
            package='orbinspect_control',
            executable='controller_node',
            name='controller_node',
            output='screen',
            parameters=[control_config],
        ),
        Node(
            package='orbinspect_guidance',
            executable='offline_trajectory_node',
            name='offline_trajectory_node',
            output='screen',
            parameters=[trajectory_config],
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(spawn_chaser_launch),
            launch_arguments={'gz_partition': gz_partition}.items(),
        ),
    ])
