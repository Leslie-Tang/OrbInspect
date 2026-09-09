from glob import glob

from setuptools import find_packages, setup


def package_files(pattern):
    return [path for path in glob(pattern) if not path.endswith('__pycache__')]


package_name = 'orbinspect_control'

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
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rugang',
    maintainer_email='rugang@todo.todo',
    description='Baseline spacecraft control package for OrbInspect.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'controller_node = orbinspect_control.controller_node:main',
            'reference_publisher_node = '
            'orbinspect_control.reference_publisher_node:main',
        ],
    },
)
