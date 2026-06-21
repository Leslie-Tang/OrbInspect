"""Small rosbag2 command helpers for launch files."""

from __future__ import annotations


DEFAULT_ROSBAG_TOPICS = (
    '/chaser/odom',
    '/chaser/control_command',
    '/chaser/safe_control_command',
    '/chaser/safety_status',
    '/inspection/coverage_map',
    '/inspection/current_waypoint',
    '/inspection/planned_path',
    '/planner/status',
    '/planner/event',
)


def rosbag_record_arguments(output_path: str) -> list[str]:
    """Return `ros2 bag record` arguments for paper experiment topics."""
    return ['bag', 'record', '-o', output_path, '--topics', *DEFAULT_ROSBAG_TOPICS]
