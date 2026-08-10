"""Replay a saved offline planning result for Gazebo and RViz validation."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable

from geometry_msgs.msg import Point, PointStamped, PoseStamped, TransformStamped
from nav_msgs.msg import Odometry, Path as PathMsg
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from tf2_ros import TransformBroadcaster
from visualization_msgs.msg import Marker, MarkerArray


class PlannedTrajectoryReplayNode(Node):
    """Publish saved proposed viewpoints, camera attitude, and chaser trajectory."""

    def __init__(self) -> None:
        super().__init__('planned_trajectory_replay_node')
        self.declare_parameter('result_dir', 'data/results/offline_high_coverage_experiment')
        self.declare_parameter('method', 'set_cover_cw_tour')
        self.declare_parameter('frame_id', 'lvlh')
        self.declare_parameter('child_frame_id', 'chaser_body')
        self.declare_parameter('camera_frame_id', 'chaser_camera')
        self.declare_parameter('trajectory_source', 'standoff')
        self.declare_parameter('publish_mode', 'closed_loop')
        self.declare_parameter('publish_rate', 20.0)
        self.declare_parameter('time_scale', 20.0)
        self.declare_parameter('loop', True)
        self.declare_parameter('horizontal_fov_deg', 70.0)
        self.declare_parameter('vertical_fov_deg', 50.0)
        self.declare_parameter('fov_range', 25.0)
        self.declare_parameter('stop_before_time', 0.0)
        self.declare_parameter('safe_shell_radius', 110.0)
        self.declare_parameter('standoff_distance', 35.0)
        self.declare_parameter('path_sample_spacing', 0.75)
        self.declare_parameter('max_reference_speed', 0.08)
        self.declare_parameter('max_reference_acceleration', 0.01)
        self.declare_parameter(
            'station_mesh_resource',
            'package://orbinspect_description/models/iss_real/meshes/ISS_stationary_rviz.stl',
        )
        self.declare_parameter('station_mesh_scale', 1.065)

        self.result_dir = Path(str(self.get_parameter('result_dir').value))
        self.method = str(self.get_parameter('method').value)
        self.frame_id = str(self.get_parameter('frame_id').value)
        self.child_frame_id = str(self.get_parameter('child_frame_id').value)
        self.camera_frame_id = str(self.get_parameter('camera_frame_id').value)
        self.trajectory_source = str(self.get_parameter('trajectory_source').value)
        self.publish_mode = str(self.get_parameter('publish_mode').value)
        self.station_mesh_resource = str(self.get_parameter('station_mesh_resource').value)
        self.publish_rate = self._positive_parameter('publish_rate')
        self.time_scale = self._positive_parameter('time_scale')
        self.loop = bool(self.get_parameter('loop').value)
        self.horizontal_fov = self._positive_parameter('horizontal_fov_deg')
        self.vertical_fov = self._positive_parameter('vertical_fov_deg')
        self.fov_range = self._positive_parameter('fov_range')
        self.stop_before_time = float(self.get_parameter('stop_before_time').value)
        self.safe_shell_radius = self._positive_parameter('safe_shell_radius')
        self.standoff_distance = self._positive_parameter('standoff_distance')
        self.path_sample_spacing = self._positive_parameter('path_sample_spacing')
        self.max_reference_speed = self._positive_parameter('max_reference_speed')
        self.max_reference_acceleration = self._positive_parameter(
            'max_reference_acceleration'
        )
        self.station_mesh_scale = self._positive_parameter('station_mesh_scale')

        csv_trajectory = _load_trajectory(self.result_dir, self.method)
        self.viewpoints = _load_viewpoints(self.result_dir, self.method)
        if self.trajectory_source == 'standoff':
            self.trajectory = _build_standoff_trajectory(
                csv_trajectory,
                self.viewpoints,
                self.safe_shell_radius,
                self.standoff_distance,
                self.path_sample_spacing,
                self.max_reference_speed,
                self.max_reference_acceleration,
            )
            self.attitudes = _attitudes_from_trajectory(self.trajectory)
        else:
            self.trajectory = csv_trajectory
            self.attitudes = _load_attitudes(self.result_dir, self.method)
        if self.stop_before_time > 0.0:
            self.trajectory = [
                sample for sample in self.trajectory
                if sample['time'] < self.stop_before_time
            ]
        if not self.trajectory:
            raise ValueError(f'no trajectory rows found for method {self.method}')

        self.start_time = self.get_clock().now()
        self.last_index = 0
        self.latest_odom: Odometry | None = None
        self.executed_path = PathMsg()
        self.executed_path.header.frame_id = self.frame_id

        self.reference_pub = self.create_publisher(PointStamped, '/chaser/reference', 10)
        self.reference_state_pub = self.create_publisher(
            Odometry,
            '/chaser/reference_state',
            10,
        )
        self.attitude_reference_pub = self.create_publisher(
            PoseStamped,
            '/chaser/attitude_reference',
            10,
        )
        self.planned_path_pub = self.create_publisher(PathMsg, '/inspection/planned_path', 10)
        self.offline_path_pub = self.create_publisher(PathMsg, '/inspection/offline_path', 10)
        self.executed_path_pub = self.create_publisher(PathMsg, '/chaser/trajectory', 10)
        self.marker_pub = self.create_publisher(
            MarkerArray,
            '/visualization/planner_markers',
            10,
        )
        self.station_mesh_pub = self.create_publisher(
            Marker,
            '/visualization/station_mesh',
            10,
        )
        self.fov_pub = self.create_publisher(Marker, '/visualization/fov_marker', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        if self.publish_mode == 'replay':
            self.odom_pub = self.create_publisher(Odometry, '/chaser/odom', 10)
            self.state_pub = self.create_publisher(Odometry, '/chaser/state_lvlh', 10)
        elif self.publish_mode == 'closed_loop':
            self.create_subscription(Odometry, '/chaser/odom', self._odom_callback, 10)
        else:
            raise ValueError('publish_mode must be closed_loop or replay')

        self._publish_static_plan()
        self.create_timer(1.0 / self.publish_rate, self._tick)
        self.create_timer(1.0, self._publish_static_plan)
        self.get_logger().info(
            f'{self.publish_mode} validation using {len(self.trajectory)} trajectory '
            f'samples and {len(self.viewpoints)} viewpoints from {self.result_dir}'
        )

    def _odom_callback(self, msg: Odometry) -> None:
        self.latest_odom = msg

    def _tick(self) -> None:
        stamp = self.get_clock().now().to_msg()
        replay_time = self._current_replay_time()
        index = self._current_index(replay_time)
        sample = self._interpolated_sample(index, replay_time)
        attitude = self._interpolated_attitude(index, replay_time, sample)
        self.reference_pub.publish(_make_reference(stamp, self.frame_id, sample))
        self.reference_state_pub.publish(_make_reference_state(
            stamp,
            self.frame_id,
            self.child_frame_id,
            sample,
            attitude,
            self._feedforward_acceleration(index, replay_time),
        ))
        self.attitude_reference_pub.publish(
            _make_pose(stamp, self.frame_id, sample, attitude)
        )
        display_sample = sample
        if self.publish_mode == 'replay':
            odom = _make_odometry(
                stamp,
                self.frame_id,
                self.child_frame_id,
                sample,
                attitude,
            )
            self.odom_pub.publish(odom)
            self.state_pub.publish(odom)
            self.tf_broadcaster.sendTransform(_make_chaser_transform(
                stamp,
                self.frame_id,
                self.child_frame_id,
                sample,
                attitude,
            ))
        elif self.latest_odom is not None:
            display_sample = _sample_from_odometry(replay_time, self.latest_odom)
            self.tf_broadcaster.sendTransform(_make_chaser_transform(
                stamp,
                self.frame_id,
                self.child_frame_id,
                display_sample,
                attitude,
            ))
        self.tf_broadcaster.sendTransform(_make_camera_transform(
            stamp,
            self.child_frame_id,
            self.camera_frame_id,
        ))
        self._append_executed_pose(stamp, display_sample, attitude)
        self.executed_path_pub.publish(self.executed_path)
        self.fov_pub.publish(self._make_fov_marker(stamp, display_sample, attitude))
        if index < self.last_index:
            self._reset_executed_path()
        self.last_index = index

    def _current_replay_time(self) -> float:
        elapsed = (self.get_clock().now() - self.start_time).nanoseconds * 1.0e-9
        replay_time = elapsed * self.time_scale
        final_time = self.trajectory[-1]['time']
        if self.loop and final_time > 0.0:
            replay_time = replay_time % final_time
        return replay_time

    def _current_index(self, replay_time: float) -> int:
        for index, sample in enumerate(self.trajectory):
            if sample['time'] >= replay_time:
                return index
        return len(self.trajectory) - 1

    def _interpolated_sample(
        self,
        index: int,
        replay_time: float,
    ) -> dict[str, float]:
        if index <= 0:
            return dict(self.trajectory[0])
        if index >= len(self.trajectory):
            return dict(self.trajectory[-1])
        previous = self.trajectory[index - 1]
        current = self.trajectory[index]
        ratio = _segment_ratio(previous['time'], current['time'], replay_time)
        sample = {'time': replay_time}
        for key in ('rx', 'ry', 'rz', 'vx', 'vy', 'vz'):
            sample[key] = _lerp(previous[key], current[key], ratio)
        return sample

    def _feedforward_acceleration(
        self,
        index: int,
        replay_time: float,
    ) -> tuple[float, float, float]:
        if index <= 0 or len(self.trajectory) < 2:
            return _finite_difference_acceleration(self.trajectory[0], self.trajectory[1])
        if index >= len(self.trajectory):
            return _finite_difference_acceleration(self.trajectory[-2], self.trajectory[-1])
        previous = self.trajectory[index - 1]
        current = self.trajectory[index]
        _ = replay_time
        return _finite_difference_acceleration(previous, current)

    def _interpolated_attitude(
        self,
        index: int,
        replay_time: float,
        sample: dict[str, float],
    ) -> dict[str, float]:
        if index <= 0:
            return self.attitudes.get(self.trajectory[0]['time'], _default_attitude(sample))
        if index >= len(self.trajectory):
            return self.attitudes.get(self.trajectory[-1]['time'], _default_attitude(sample))
        previous = self.trajectory[index - 1]
        current = self.trajectory[index]
        previous_attitude = self.attitudes.get(previous['time'], _default_attitude(previous))
        current_attitude = self.attitudes.get(current['time'], _default_attitude(current))
        ratio = _segment_ratio(previous['time'], current['time'], replay_time)
        quaternion = _slerp(
            tuple(previous_attitude[key] for key in ('qx', 'qy', 'qz', 'qw')),
            tuple(current_attitude[key] for key in ('qx', 'qy', 'qz', 'qw')),
            ratio,
        )
        boresight = _unit(tuple(
            _lerp(
                previous_attitude[f'boresight_{axis}'],
                current_attitude[f'boresight_{axis}'],
                ratio,
            )
            for axis in ('x', 'y', 'z')
        ))
        return {
            'boresight_x': boresight[0],
            'boresight_y': boresight[1],
            'boresight_z': boresight[2],
            'qx': quaternion[0],
            'qy': quaternion[1],
            'qz': quaternion[2],
            'qw': quaternion[3],
        }

    def _append_executed_pose(
        self,
        stamp,
        sample: dict[str, float],
        attitude: dict[str, float],
    ) -> None:
        if len(self.executed_path.poses) > 1600:
            self.executed_path.poses = self.executed_path.poses[-1200:]
        pose = _make_pose(stamp, self.frame_id, sample, attitude)
        self.executed_path.header.stamp = stamp
        self.executed_path.poses.append(pose)

    def _reset_executed_path(self) -> None:
        self.executed_path = PathMsg()
        self.executed_path.header.frame_id = self.frame_id

    def _publish_static_plan(self) -> None:
        path = PathMsg()
        path.header.stamp = self.get_clock().now().to_msg()
        path.header.frame_id = self.frame_id
        for sample in self.trajectory:
            attitude = self.attitudes.get(sample['time'], _default_attitude(sample))
            path.poses.append(_make_pose(path.header.stamp, self.frame_id, sample, attitude))
        self.planned_path_pub.publish(path)
        self.offline_path_pub.publish(path)
        self.marker_pub.publish(self._make_viewpoint_markers(path.header.stamp))
        self.station_mesh_pub.publish(self._make_station_mesh_marker(path.header.stamp))

    def _make_viewpoint_markers(self, stamp) -> MarkerArray:
        markers = MarkerArray()
        for index, row in enumerate(self.viewpoints):
            sphere = Marker()
            sphere.header.stamp = stamp
            sphere.header.frame_id = self.frame_id
            sphere.ns = 'proposed_viewpoints'
            sphere.id = index
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose.position.x = row['viewpoint_x']
            sphere.pose.position.y = row['viewpoint_y']
            sphere.pose.position.z = row['viewpoint_z']
            sphere.pose.orientation.w = 1.0
            sphere.scale.x = 1.2
            sphere.scale.y = 1.2
            sphere.scale.z = 1.2
            sphere.color.r = 0.1
            sphere.color.g = 0.65
            sphere.color.b = 1.0
            sphere.color.a = 0.9
            markers.markers.append(sphere)

            ray = Marker()
            ray.header.stamp = stamp
            ray.header.frame_id = self.frame_id
            ray.ns = 'proposed_camera_boresight'
            ray.id = 1000 + index
            ray.type = Marker.ARROW
            ray.action = Marker.ADD
            ray.scale.x = 0.18
            ray.scale.y = 0.45
            ray.scale.z = 0.45
            ray.color.r = 1.0
            ray.color.g = 0.8
            ray.color.b = 0.1
            ray.color.a = 0.9
            start = Point(x=row['viewpoint_x'], y=row['viewpoint_y'], z=row['viewpoint_z'])
            end = Point(
                x=row['viewpoint_x'] + 6.0 * row['boresight_x'],
                y=row['viewpoint_y'] + 6.0 * row['boresight_y'],
                z=row['viewpoint_z'] + 6.0 * row['boresight_z'],
            )
            ray.points = [start, end]
            markers.markers.append(ray)
        return markers

    def _make_station_mesh_marker(self, stamp) -> Marker:
        marker = Marker()
        marker.header.stamp = stamp
        marker.header.frame_id = self.frame_id
        marker.ns = 'station_mesh'
        marker.id = 1
        marker.type = Marker.MESH_RESOURCE
        marker.action = Marker.ADD
        marker.mesh_resource = self.station_mesh_resource
        marker.mesh_use_embedded_materials = False
        marker.pose.orientation.y = 0.70710678118
        marker.pose.orientation.w = 0.70710678118
        marker.scale.x = self.station_mesh_scale
        marker.scale.y = self.station_mesh_scale
        marker.scale.z = self.station_mesh_scale
        marker.color.r = 0.72
        marker.color.g = 0.74
        marker.color.b = 0.78
        marker.color.a = 0.92
        return marker

    def _make_fov_marker(
        self,
        stamp,
        sample: dict[str, float],
        attitude: dict[str, float],
    ) -> Marker:
        marker = Marker()
        marker.header.stamp = stamp
        marker.header.frame_id = self.frame_id
        marker.ns = 'current_camera_fov'
        marker.id = 1
        marker.type = Marker.LINE_LIST
        marker.action = Marker.ADD
        marker.scale.x = 0.08
        marker.color.r = 0.95
        marker.color.g = 0.95
        marker.color.b = 0.2
        marker.color.a = 0.95
        origin = (sample['rx'], sample['ry'], sample['rz'])
        corners = _fov_corners(
            origin,
            (attitude['boresight_x'], attitude['boresight_y'], attitude['boresight_z']),
            self.horizontal_fov,
            self.vertical_fov,
            self.fov_range,
        )
        origin_point = _point(origin)
        for corner in corners:
            marker.points.extend([origin_point, _point(corner)])
        for start, end in zip(corners, corners[1:] + corners[:1]):
            marker.points.extend([_point(start), _point(end)])
        return marker

    def _positive_parameter(self, name: str) -> float:
        value = float(self.get_parameter(name).value)
        if value <= 0.0:
            raise ValueError(f'{name} must be positive')
        return value


def _load_trajectory(result_dir: Path, method: str) -> list[dict[str, float]]:
    rows = []
    for row in _read_csv(result_dir / 'raw' / 'trajectory.csv'):
        if row.get('method') != method:
            continue
        rows.append({
            'time': float(row['time']),
            'rx': float(row['rx']),
            'ry': float(row['ry']),
            'rz': float(row['rz']),
            'vx': float(row['vx']),
            'vy': float(row['vy']),
            'vz': float(row['vz']),
        })
    return rows


def _load_attitudes(result_dir: Path, method: str) -> dict[float, dict[str, float]]:
    rows = []
    for row in _read_csv(result_dir / 'raw' / 'attitude.csv'):
        if row.get('method') != method:
            continue
        rows.append({
            'time': float(row['time']),
            'boresight_x': float(row['boresight_x']),
            'boresight_y': float(row['boresight_y']),
            'boresight_z': float(row['boresight_z']),
        })
    return _continuous_attitudes(rows)


def _continuous_attitudes(rows: list[dict[str, float]]) -> dict[float, dict[str, float]]:
    attitudes = {}
    previous_y: tuple[float, float, float] | None = None
    previous_q: tuple[float, float, float, float] | None = None
    for row in rows:
        forward = _unit((row['boresight_x'], row['boresight_y'], row['boresight_z']))
        body_y = _continuous_body_y(forward, previous_y)
        body_z = _unit(_cross(forward, body_y))
        quaternion = _rotation_matrix_to_quaternion(forward, body_y, body_z)
        if previous_q is not None and _quaternion_dot(previous_q, quaternion) < 0.0:
            quaternion = tuple(-value for value in quaternion)
        previous_y = body_y
        previous_q = quaternion
        attitudes[row['time']] = {
            'boresight_x': forward[0],
            'boresight_y': forward[1],
            'boresight_z': forward[2],
            'qx': quaternion[0],
            'qy': quaternion[1],
            'qz': quaternion[2],
            'qw': quaternion[3],
        }
    return attitudes


def _continuous_body_y(
    forward: tuple[float, float, float],
    previous_y: tuple[float, float, float] | None,
) -> tuple[float, float, float]:
    if previous_y is not None:
        projected = _subtract(previous_y, _scale(forward, _dot(previous_y, forward)))
        if _dot(projected, projected) > 1.0e-8:
            return _unit(projected)
    reference = _least_aligned_axis(forward)
    return _unit(_cross(reference, forward))


def _least_aligned_axis(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    axes = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    return min(axes, key=lambda axis: abs(_dot(axis, vector)))


def _load_viewpoints(result_dir: Path, method: str) -> list[dict[str, float]]:
    viewpoints = []
    for row in _read_csv(result_dir / 'raw' / 'viewpoints.csv'):
        if row.get('method') != method:
            continue
        viewpoints.append({
            'viewpoint_x': float(row['viewpoint_x']),
            'viewpoint_y': float(row['viewpoint_y']),
            'viewpoint_z': float(row['viewpoint_z']),
            'boresight_x': float(row['boresight_x']),
            'boresight_y': float(row['boresight_y']),
            'boresight_z': float(row['boresight_z']),
        })
    return viewpoints


def _build_standoff_trajectory(
    csv_trajectory: list[dict[str, float]],
    viewpoints: list[dict[str, float]],
    safe_shell_radius: float,
    standoff_distance: float,
    sample_spacing: float,
    max_speed: float = 0.08,
    max_acceleration: float = 0.01,
) -> list[dict[str, float]]:
    if not csv_trajectory:
        return []
    _ = standoff_distance
    waypoints = [_project_to_shell(_position_from_sample(csv_trajectory[0]), safe_shell_radius)]
    for viewpoint in viewpoints:
        view_position = (
            viewpoint['viewpoint_x'],
            viewpoint['viewpoint_y'],
            viewpoint['viewpoint_z'],
        )
        waypoints.append(_project_to_shell(view_position, safe_shell_radius))
    return _sample_shell_arcs(
        waypoints,
        safe_shell_radius,
        sample_spacing,
        max_speed,
        max_acceleration,
    )


def _sample_shell_arcs(
    waypoints: list[tuple[float, float, float]],
    radius: float,
    spacing: float,
    max_speed: float = 0.08,
    max_acceleration: float = 0.01,
) -> list[dict[str, float]]:
    samples: list[dict[str, float]] = []
    time_value = 0.0
    for start, end in zip(waypoints, waypoints[1:]):
        start_direction = _unit(start)
        end_direction = _unit(end)
        angle = math.acos(max(-1.0, min(1.0, _dot(start_direction, end_direction))))
        arc_length = max(radius * angle, 1.0e-12)
        steps = max(1, int(math.ceil(arc_length / spacing)))
        duration = _limited_profile_duration(arc_length, max_speed, max_acceleration)
        for step in range(steps + 1):
            ratio = step / float(steps)
            sample_time = time_value + ratio * duration
            distance_along, speed_along, acceleration_along = _path_profile(
                ratio * duration,
                arc_length,
                max_speed,
                max_acceleration,
            )
            path_ratio = max(0.0, min(1.0, distance_along / arc_length))
            position_direction = _slerp_vector(start_direction, end_direction, path_ratio)
            position = _scale(_slerp_vector(start_direction, end_direction, ratio), radius)
            position = _scale(position_direction, radius)
            tangent = _arc_tangent(start_direction, end_direction, path_ratio)
            velocity = _scale(tangent, speed_along)
            acceleration = _scale(tangent, acceleration_along)
            if samples and abs(samples[-1]['time'] - sample_time) < 1.0e-9:
                continue
            samples.append(_sample_from_position(sample_time, position, velocity, acceleration))
        time_value += duration
    if not samples:
        samples.append(_sample_from_position(0.0, waypoints[0], (0.0, 0.0, 0.0)))
    return samples


def _limited_profile_duration(
    distance_value: float,
    max_speed: float,
    max_acceleration: float,
) -> float:
    ramp_distance = max_speed * max_speed / max_acceleration
    if distance_value <= ramp_distance:
        return 2.0 * math.sqrt(distance_value / max_acceleration)
    return distance_value / max_speed + max_speed / max_acceleration


def _path_profile(
    time_value: float,
    distance_value: float,
    max_speed: float,
    max_acceleration: float,
) -> tuple[float, float, float]:
    ramp_time = max_speed / max_acceleration
    ramp_distance = max_speed * max_speed / max_acceleration
    if distance_value <= ramp_distance:
        peak_speed = math.sqrt(distance_value * max_acceleration)
        ramp_time = peak_speed / max_acceleration
        total_time = 2.0 * ramp_time
        if time_value <= ramp_time:
            return (
                0.5 * max_acceleration * time_value * time_value,
                max_acceleration * time_value,
                max_acceleration,
            )
        decel_time = max(0.0, total_time - time_value)
        return (
            distance_value - 0.5 * max_acceleration * decel_time * decel_time,
            max_acceleration * decel_time,
            -max_acceleration,
        )
    cruise_distance = distance_value - ramp_distance
    cruise_time = cruise_distance / max_speed
    if time_value <= ramp_time:
        return (
            0.5 * max_acceleration * time_value * time_value,
            max_acceleration * time_value,
            max_acceleration,
        )
    if time_value <= ramp_time + cruise_time:
        cruise_elapsed = time_value - ramp_time
        return (
            0.5 * max_acceleration * ramp_time * ramp_time
            + max_speed * cruise_elapsed,
            max_speed,
            0.0,
        )
    total_time = 2.0 * ramp_time + cruise_time
    decel_time = max(0.0, total_time - time_value)
    return (
        distance_value - 0.5 * max_acceleration * decel_time * decel_time,
        max_acceleration * decel_time,
        -max_acceleration,
    )


def _arc_tangent(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    ratio: float,
) -> tuple[float, float, float]:
    eps = 1.0e-4
    left = _slerp_vector(start, end, max(0.0, ratio - eps))
    right = _slerp_vector(start, end, min(1.0, ratio + eps))
    return _unit(_subtract(right, left))


def _slerp_vector(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    ratio: float,
) -> tuple[float, float, float]:
    dot_value = max(-1.0, min(1.0, _dot(start, end)))
    if dot_value > 0.9995:
        return _unit(tuple(_lerp(start[index], end[index], ratio) for index in range(3)))
    if dot_value < -0.9995:
        helper = _least_aligned_axis(start)
        mid = _unit(_cross(start, helper))
        if ratio < 0.5:
            return _slerp_vector(start, mid, ratio * 2.0)
        return _slerp_vector(mid, end, (ratio - 0.5) * 2.0)
    theta = math.acos(dot_value)
    sin_theta = math.sin(theta)
    scale_start = math.sin((1.0 - ratio) * theta) / sin_theta
    scale_end = math.sin(ratio * theta) / sin_theta
    return _unit(_add(_scale(start, scale_start), _scale(end, scale_end)))


def _sample_from_position(
    time_value: float,
    position: tuple[float, float, float],
    velocity: tuple[float, float, float],
    acceleration: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> dict[str, float]:
    return {
        'time': time_value,
        'rx': position[0],
        'ry': position[1],
        'rz': position[2],
        'vx': velocity[0],
        'vy': velocity[1],
        'vz': velocity[2],
        'ax': acceleration[0],
        'ay': acceleration[1],
        'az': acceleration[2],
    }


def _position_from_sample(sample: dict[str, float]) -> tuple[float, float, float]:
    return (sample['rx'], sample['ry'], sample['rz'])


def _project_to_shell(
    point: tuple[float, float, float],
    radius: float,
) -> tuple[float, float, float]:
    direction = _unit(point)
    return _scale(direction, max(radius, _dot(point, point) ** 0.5))


def _attitudes_from_trajectory(
    trajectory: list[dict[str, float]],
) -> dict[float, dict[str, float]]:
    rows = []
    for sample in trajectory:
        position = _position_from_sample(sample)
        boresight = _unit(_scale(position, -1.0))
        rows.append({
            'time': sample['time'],
            'boresight_x': boresight[0],
            'boresight_y': boresight[1],
            'boresight_z': boresight[2],
        })
    return _continuous_attitudes(rows)


def _read_csv(path: Path) -> Iterable[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline='') as handle:
        yield from csv.DictReader(handle)


def _make_odometry(
    stamp,
    frame_id: str,
    child_frame_id: str,
    sample: dict[str, float],
    attitude: dict[str, float],
) -> Odometry:
    odom = Odometry()
    odom.header.stamp = stamp
    odom.header.frame_id = frame_id
    odom.child_frame_id = child_frame_id
    odom.pose.pose = _make_pose(stamp, frame_id, sample, attitude).pose
    odom.twist.twist.linear.x = sample['vx']
    odom.twist.twist.linear.y = sample['vy']
    odom.twist.twist.linear.z = sample['vz']
    return odom


def _make_reference_state(
    stamp,
    frame_id: str,
    child_frame_id: str,
    sample: dict[str, float],
    attitude: dict[str, float],
    acceleration: tuple[float, float, float],
) -> Odometry:
    odom = _make_odometry(stamp, frame_id, child_frame_id, sample, attitude)
    odom.twist.twist.angular.x = acceleration[0]
    odom.twist.twist.angular.y = acceleration[1]
    odom.twist.twist.angular.z = acceleration[2]
    return odom


def _finite_difference_acceleration(
    previous: dict[str, float],
    current: dict[str, float],
) -> tuple[float, float, float]:
    if all(key in current for key in ('ax', 'ay', 'az')):
        return (current['ax'], current['ay'], current['az'])
    dt = max(current['time'] - previous['time'], 1.0e-9)
    return (
        (current['vx'] - previous['vx']) / dt,
        (current['vy'] - previous['vy']) / dt,
        (current['vz'] - previous['vz']) / dt,
    )


def _sample_from_odometry(time_value: float, odom: Odometry) -> dict[str, float]:
    return {
        'time': time_value,
        'rx': float(odom.pose.pose.position.x),
        'ry': float(odom.pose.pose.position.y),
        'rz': float(odom.pose.pose.position.z),
        'vx': float(odom.twist.twist.linear.x),
        'vy': float(odom.twist.twist.linear.y),
        'vz': float(odom.twist.twist.linear.z),
    }


def _make_pose(
    stamp,
    frame_id: str,
    sample: dict[str, float],
    attitude: dict[str, float],
) -> PoseStamped:
    pose = PoseStamped()
    pose.header.stamp = stamp
    pose.header.frame_id = frame_id
    pose.pose.position.x = sample['rx']
    pose.pose.position.y = sample['ry']
    pose.pose.position.z = sample['rz']
    pose.pose.orientation.x = attitude['qx']
    pose.pose.orientation.y = attitude['qy']
    pose.pose.orientation.z = attitude['qz']
    pose.pose.orientation.w = attitude['qw']
    return pose


def _make_reference(stamp, frame_id: str, sample: dict[str, float]) -> PointStamped:
    msg = PointStamped()
    msg.header.stamp = stamp
    msg.header.frame_id = frame_id
    msg.point.x = sample['rx']
    msg.point.y = sample['ry']
    msg.point.z = sample['rz']
    return msg


def _make_chaser_transform(
    stamp,
    frame_id: str,
    child_frame_id: str,
    sample: dict[str, float],
    attitude: dict[str, float],
) -> TransformStamped:
    transform = TransformStamped()
    transform.header.stamp = stamp
    transform.header.frame_id = frame_id
    transform.child_frame_id = child_frame_id
    transform.transform.translation.x = sample['rx']
    transform.transform.translation.y = sample['ry']
    transform.transform.translation.z = sample['rz']
    transform.transform.rotation.x = attitude['qx']
    transform.transform.rotation.y = attitude['qy']
    transform.transform.rotation.z = attitude['qz']
    transform.transform.rotation.w = attitude['qw']
    return transform


def _make_camera_transform(stamp, parent_frame: str, camera_frame: str) -> TransformStamped:
    transform = TransformStamped()
    transform.header.stamp = stamp
    transform.header.frame_id = parent_frame
    transform.child_frame_id = camera_frame
    transform.transform.translation.x = 0.45
    transform.transform.rotation.w = 1.0
    return transform


def _default_attitude(sample: dict[str, float]) -> dict[str, float]:
    _ = sample
    return {
        'boresight_x': 1.0,
        'boresight_y': 0.0,
        'boresight_z': 0.0,
        'qx': 0.0,
        'qy': 0.0,
        'qz': 0.0,
        'qw': 1.0,
    }


def _fov_corners(
    origin: tuple[float, float, float],
    boresight: tuple[float, float, float],
    horizontal_fov_deg: float,
    vertical_fov_deg: float,
    fov_range: float,
) -> list[tuple[float, float, float]]:
    forward = _unit(boresight)
    world_up = (0.0, 0.0, 1.0)
    if abs(_dot(forward, world_up)) > 0.95:
        world_up = (0.0, 1.0, 0.0)
    right = _unit(_cross(forward, world_up))
    up = _unit(_cross(right, forward))
    half_width = fov_range * _tan_deg(horizontal_fov_deg / 2.0)
    half_height = fov_range * _tan_deg(vertical_fov_deg / 2.0)
    center = _add(origin, _scale(forward, fov_range))
    return [
        _add(_add(center, _scale(right, sx * half_width)), _scale(up, sy * half_height))
        for sx, sy in ((1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0))
    ]


def _point(values: tuple[float, float, float]) -> Point:
    return Point(x=values[0], y=values[1], z=values[2])


def _add(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _subtract(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(a: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    return (a[0] * factor, a[1] * factor, a[2] * factor)


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _unit(a: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = max((_dot(a, a)) ** 0.5, 1.0e-12)
    return (a[0] / norm, a[1] / norm, a[2] / norm)


def _rotation_matrix_to_quaternion(
    body_x: tuple[float, float, float],
    body_y: tuple[float, float, float],
    body_z: tuple[float, float, float],
) -> tuple[float, float, float, float]:
    matrix = (
        (body_x[0], body_y[0], body_z[0]),
        (body_x[1], body_y[1], body_z[1]),
        (body_x[2], body_y[2], body_z[2]),
    )
    trace = matrix[0][0] + matrix[1][1] + matrix[2][2]
    if trace > 0.0:
        scale_value = math.sqrt(trace + 1.0) * 2.0
        qw = 0.25 * scale_value
        qx = (matrix[2][1] - matrix[1][2]) / scale_value
        qy = (matrix[0][2] - matrix[2][0]) / scale_value
        qz = (matrix[1][0] - matrix[0][1]) / scale_value
    elif matrix[0][0] > matrix[1][1] and matrix[0][0] > matrix[2][2]:
        scale_value = math.sqrt(1.0 + matrix[0][0] - matrix[1][1] - matrix[2][2]) * 2.0
        qw = (matrix[2][1] - matrix[1][2]) / scale_value
        qx = 0.25 * scale_value
        qy = (matrix[0][1] + matrix[1][0]) / scale_value
        qz = (matrix[0][2] + matrix[2][0]) / scale_value
    elif matrix[1][1] > matrix[2][2]:
        scale_value = math.sqrt(1.0 + matrix[1][1] - matrix[0][0] - matrix[2][2]) * 2.0
        qw = (matrix[0][2] - matrix[2][0]) / scale_value
        qx = (matrix[0][1] + matrix[1][0]) / scale_value
        qy = 0.25 * scale_value
        qz = (matrix[1][2] + matrix[2][1]) / scale_value
    else:
        scale_value = math.sqrt(1.0 + matrix[2][2] - matrix[0][0] - matrix[1][1]) * 2.0
        qw = (matrix[1][0] - matrix[0][1]) / scale_value
        qx = (matrix[0][2] + matrix[2][0]) / scale_value
        qy = (matrix[1][2] + matrix[2][1]) / scale_value
        qz = 0.25 * scale_value
    norm_value = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    return (qx / norm_value, qy / norm_value, qz / norm_value, qw / norm_value)


def _quaternion_dot(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]


def _slerp(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    ratio: float,
) -> tuple[float, float, float, float]:
    dot_value = _quaternion_dot(a, b)
    if dot_value < 0.0:
        b = tuple(-value for value in b)
        dot_value = -dot_value
    dot_value = max(-1.0, min(1.0, dot_value))
    if dot_value > 0.9995:
        return _unit_quaternion(tuple(_lerp(a[index], b[index], ratio) for index in range(4)))
    theta_0 = math.acos(dot_value)
    sin_theta_0 = math.sin(theta_0)
    theta = theta_0 * ratio
    scale_a = math.sin(theta_0 - theta) / sin_theta_0
    scale_b = math.sin(theta) / sin_theta_0
    return tuple(scale_a * a[index] + scale_b * b[index] for index in range(4))


def _unit_quaternion(
    values: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    norm = max(sum(value * value for value in values) ** 0.5, 1.0e-12)
    return tuple(value / norm for value in values)


def _segment_ratio(start_time: float, end_time: float, replay_time: float) -> float:
    duration = max(end_time - start_time, 1.0e-12)
    return max(0.0, min(1.0, (replay_time - start_time) / duration))


def _lerp(start: float, end: float, ratio: float) -> float:
    return start + (end - start) * ratio


def _tan_deg(degrees: float) -> float:
    return math.tan(math.radians(degrees))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = PlannedTrajectoryReplayNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass
        finally:
            if rclpy.ok():
                rclpy.shutdown()


if __name__ == '__main__':
    main()
