"""Record a compressed full-station chaser-following ISS inspection view."""

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
    output_path = LaunchConfiguration('output_path')
    max_frames = LaunchConfiguration('max_frames')
    fps = LaunchConfiguration('fps')
    gz_partition = LaunchConfiguration('gz_partition')
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
    follow_camera_launch = PathJoinSubstitution([
        FindPackageShare('orbinspect_gazebo'),
        'launch',
        'spawn_follow_camera.launch.py',
    ])
    control_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_control'),
        'config',
        'control.yaml',
    ])
    trajectory_config = PathJoinSubstitution([
        FindPackageShare('orbinspect_guidance'),
        'config',
        'offline_trajectory_recording.yaml',
    ])
    gz_image_topic = '/orbinspect/chaser_follow_camera/image'
    ros_image_topic = '/orbinspect/chaser_follow_camera/image'

    return LaunchDescription([
        DeclareLaunchArgument(
            'output_path',
            default_value='data/results/video_capture/full_iss_chaser_follow_view.mp4',
            description='MP4 output path for the full ISS follow-view recording.',
        ),
        DeclareLaunchArgument(
            'max_frames',
            default_value='720',
            description='Number of camera frames to save.',
        ),
        DeclareLaunchArgument(
            'fps',
            default_value='12.0',
            description='Output video frames per second.',
        ),
        DeclareLaunchArgument(
            'gz_partition',
            default_value=AnonName('orbinspect_full_iss_recording'),
            description='Gazebo Transport partition for this recording run.',
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
                'initial_position_lvlh': [-48.0, -30.0, 10.0],
                'initial_velocity_lvlh': [0.0, 0.0, 0.0],
            }],
        ),
        Node(
            package='orbinspect_control',
            executable='controller_node',
            name='controller_node',
            output='screen',
            parameters=[control_config, {
                'max_acceleration': 0.015,
                'position_gain': 0.0012,
                'velocity_gain': 0.08,
                'publish_safe_command_passthrough': True,
            }],
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
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(follow_camera_launch),
            launch_arguments={'gz_partition': gz_partition}.items(),
        ),
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='chaser_follow_camera_bridge',
            output='screen',
            arguments=[
                f'{gz_image_topic}@sensor_msgs/msg/Image[gz.msgs.Image',
            ],
            remappings=[(gz_image_topic, ros_image_topic)],
            additional_env={'GZ_PARTITION': gz_partition},
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
