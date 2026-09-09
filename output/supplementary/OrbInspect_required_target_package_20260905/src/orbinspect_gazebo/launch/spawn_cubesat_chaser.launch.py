"""Spawn the CubeSat visual chaser and follow ROS odometry in Gazebo."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import TimerAction
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    gz_partition = LaunchConfiguration('gz_partition')
    chaser_sdf = PathJoinSubstitution([
        FindPackageShare('orbinspect_description'),
        'models',
        'chaser_cubesat',
        'model.sdf',
    ])

    spawn_chaser = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_cubesat_chaser',
        arguments=[
            '-world',
            'iss_real_visual',
            '-file',
            chaser_sdf,
            '-name',
            'chaser',
            '-x',
            '0.0',
            '-y',
            '-35.0',
            '-z',
            '10.0',
        ],
        output='screen',
        additional_env={'GZ_PARTITION': gz_partition},
    )
    follow_chaser = Node(
        package='orbinspect_gazebo',
        executable='chaser_pose_follower',
        name='cubesat_chaser_pose_follower',
        output='screen',
        parameters=[{
            'entity_name': 'chaser',
            'world_name': 'iss_real_visual',
            'odom_topic': '/chaser/odom',
            'follow_rate': 20.0,
            'startup_delay': 2.0,
        }],
        additional_env={'GZ_PARTITION': gz_partition},
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'gz_partition',
            default_value='orbinspect_real_iss',
            description='Gazebo Transport partition that contains the chaser model.',
        ),
        TimerAction(period=2.0, actions=[spawn_chaser]),
        TimerAction(period=5.0, actions=[follow_chaser]),
    ])
