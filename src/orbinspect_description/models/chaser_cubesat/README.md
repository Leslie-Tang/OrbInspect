# chaser_cubesat

Visual-only CubeSat-style chaser model for OrbInspect demos.

The ROS-native HCW dynamics node remains the source of truth for spacecraft
state; Gazebo only mirrors `/chaser/odom` for visualization.
