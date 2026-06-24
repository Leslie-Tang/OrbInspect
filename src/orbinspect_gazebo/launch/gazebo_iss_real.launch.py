"""Launch Gazebo Harmonic with the NASA ISS visual model."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import ExecuteProcess
from launch.actions import Shutdown
from launch.substitutions import EnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    gz_partition = LaunchConfiguration('gz_partition')
    world_file = PathJoinSubstitution([
        FindPackageShare('orbinspect_gazebo'),
        'worlds',
        'iss_real_visual.sdf',
    ])
    description_models = PathJoinSubstitution([
        FindPackageShare('orbinspect_description'),
        'models',
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'gz_partition',
            default_value='orbinspect_real_iss',
            description='Gazebo Transport partition for this demo run.',
        ),
        ExecuteProcess(
            cmd=['gz', 'sim', '-r', world_file, '--force-version', '8'],
            name='gazebo',
            output='screen',
            additional_env={
                'GZ_PARTITION': gz_partition,
                'GZ_SIM_RESOURCE_PATH': [
                    description_models,
                    ':',
                    EnvironmentVariable('GZ_SIM_RESOURCE_PATH', default_value=''),
                ],
            },
            on_exit=Shutdown(),
        ),
    ])
