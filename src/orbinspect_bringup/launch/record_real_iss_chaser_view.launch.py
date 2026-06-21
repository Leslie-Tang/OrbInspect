"""Record a chaser-following Gazebo camera view of the real ISS demo."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    output_path = LaunchConfiguration('output_path')
    max_frames = LaunchConfiguration('max_frames')
    fps = LaunchConfiguration('fps')
    real_iss_demo = PathJoinSubstitution([
        FindPackageShare('orbinspect_bringup'),
        'launch',
        'demo_real_iss_trajectory.launch.py',
    ])
    follow_camera_launch = PathJoinSubstitution([
        FindPackageShare('orbinspect_gazebo'),
        'launch',
        'spawn_follow_camera.launch.py',
    ])
    gz_image_topic = '/orbinspect/chaser_follow_camera/image'
    ros_image_topic = '/orbinspect/chaser_follow_camera/image'

    return LaunchDescription([
        DeclareLaunchArgument(
            'output_path',
            default_value='data/results/chaser_follow_view.mp4',
            description='MP4 output path for the chaser-following camera view.',
        ),
        DeclareLaunchArgument(
            'max_frames',
            default_value='360',
            description='Number of camera frames to save before holding idle.',
        ),
        DeclareLaunchArgument(
            'fps',
            default_value='12.0',
            description='Output video frames per second.',
        ),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(real_iss_demo)),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(follow_camera_launch)),
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='chaser_follow_camera_bridge',
            output='screen',
            arguments=[
                f'{gz_image_topic}@sensor_msgs/msg/Image[gz.msgs.Image',
            ],
            remappings=[(gz_image_topic, ros_image_topic)],
        ),
        Node(
            package='orbinspect_gazebo',
            executable='image_video_recorder',
            name='chaser_follow_video_recorder',
            output='screen',
            parameters=[{
                'image_topic': ros_image_topic,
                'output_path': output_path,
                'fps': fps,
                'max_frames': max_frames,
            }],
        ),
    ])
