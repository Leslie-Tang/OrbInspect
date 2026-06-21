"""Launch the ROS-only dynamics demo with Gazebo Harmonic visualization."""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    gazebo_launch = PathJoinSubstitution([
        FindPackageShare('orbinspect_gazebo'),
        'launch',
        'gazebo_iss.launch.py',
    ])
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
    spawn_chaser_launch = PathJoinSubstitution([
        FindPackageShare('orbinspect_gazebo'),
        'launch',
        'spawn_chaser.launch.py',
    ])

    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(gazebo_launch)),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(dynamics_launch)),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(control_launch)),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(spawn_chaser_launch)),
    ])
