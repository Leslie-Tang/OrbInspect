"""Spawn the CubeSat visual chaser and follow ROS odometry in Gazebo."""

from launch import LaunchDescription
from launch.actions import TimerAction
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
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
            'follow_rate': 5.0,
        }],
    )

    return LaunchDescription([
        TimerAction(period=2.0, actions=[spawn_chaser]),
        TimerAction(period=4.0, actions=[follow_chaser]),
    ])
