from glob import glob

from setuptools import find_packages, setup


def package_files(pattern):
    return [path for path in glob(pattern) if not path.endswith('__pycache__')]


package_name = 'orbinspect_gazebo'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', package_files('launch/*')),
        ('share/' + package_name + '/config', package_files('config/*')),
        ('share/' + package_name + '/worlds', package_files('worlds/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rugang',
    maintainer_email='rugang@todo.todo',
    description=(
        'Gazebo Harmonic worlds, launch files, and bridge configuration '
        'for OrbInspect visualization.'
    ),
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'chaser_pose_follower = orbinspect_gazebo.chaser_pose_follower:main',
            'follow_camera_pose_node = '
            'orbinspect_gazebo.follow_camera_pose_node:main',
            'image_video_recorder = '
            'orbinspect_gazebo.image_video_recorder:main',
        ],
    },
)
