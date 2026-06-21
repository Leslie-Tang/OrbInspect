"""Spawn a Gazebo camera that follows the chaser for video recording."""

from launch import LaunchDescription
from launch.actions import TimerAction
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    camera_sdf = PathJoinSubstitution([
        FindPackageShare('orbinspect_description'),
        'models',
        'chaser_follow_camera',
        'model.sdf',
    ])

    spawn_camera = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_chaser_follow_camera',
        arguments=[
            '-file',
            camera_sdf,
            '-name',
            'chaser_follow_camera',
            '-x',
            '-10.0',
            '-y',
            '-45.0',
            '-z',
            '16.0',
        ],
        output='screen',
    )
    follow_camera = Node(
        package='orbinspect_gazebo',
        executable='follow_camera_pose_node',
        name='follow_camera_pose_node',
        output='screen',
        parameters=[{
            'entity_name': 'chaser_follow_camera',
            'world_name': 'iss_real_visual',
            'odom_topic': '/chaser/odom',
            'follow_rate': 8.0,
            'offset_xyz': [-8.0, -12.0, 6.0],
            'target_offset_xyz': [0.0, 0.0, 0.0],
        }],
    )

    return LaunchDescription([
        TimerAction(period=2.5, actions=[spawn_camera]),
        TimerAction(period=4.5, actions=[follow_camera]),
    ])
