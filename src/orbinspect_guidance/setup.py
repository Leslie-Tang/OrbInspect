from glob import glob

from setuptools import find_packages, setup


def package_files(pattern):
    return [path for path in glob(pattern) if not path.endswith('__pycache__')]


package_name = 'orbinspect_guidance'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', package_files('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rugang',
    maintainer_email='rugang@todo.todo',
    description='Inspection waypoint and planning package for OrbInspect.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'inspection_planner_node = '
            'orbinspect_guidance.inspection_planner_node:main',
            'advanced_safe_planner_node = '
            'orbinspect_guidance.advanced_safe_planner_node:main',
            'offline_trajectory_node = '
            'orbinspect_guidance.offline_trajectory_node:main',
            'offline_coverage_planner = '
            'orbinspect_guidance.offline_coverage_planner:main',
            'offline_planning_experiment = '
            'orbinspect_guidance.offline_planning_experiment:main',
            'offline_validation_matrix = '
            'orbinspect_guidance.offline_validation_matrix:main',
            'planned_trajectory_replay_node = '
            'orbinspect_guidance.planned_trajectory_replay_node:main',
        ],
    },
)
