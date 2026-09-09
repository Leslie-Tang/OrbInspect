"""Gazebo follow-camera pose node for chaser video recording."""

from __future__ import annotations

from collections.abc import Sequence
import math
import shutil
import subprocess

from nav_msgs.msg import Odometry
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


Vector3 = tuple[float, float, float]
Quaternion = tuple[float, float, float, float]


class FollowCameraPoseNode(Node):
    """Mirror chaser odometry into a third-person Gazebo camera pose."""

    def __init__(self) -> None:
        super().__init__('follow_camera_pose_node')

        self.declare_parameter('entity_name', 'chaser_follow_camera')
        self.declare_parameter('world_name', 'iss_real_visual')
        self.declare_parameter('odom_topic', '/chaser/odom')
        self.declare_parameter('follow_rate', 8.0)
        self.declare_parameter('command_timeout', 0.6)
        self.declare_parameter('offset_xyz', [-8.0, -12.0, 6.0])
        self.declare_parameter('target_offset_xyz', [0.0, 0.0, 0.0])

        self.entity_name = str(self.get_parameter('entity_name').value)
        self.world_name = str(self.get_parameter('world_name').value)
        odom_topic = str(self.get_parameter('odom_topic').value)
        self.command_timeout = self._positive_parameter('command_timeout')
        follow_rate = self._positive_parameter('follow_rate')
        self.offset = self._vector_parameter('offset_xyz')
        self.target_offset = self._vector_parameter('target_offset_xyz')
        self.gz_executable = shutil.which('gz')
        self.latest_odom: Odometry | None = None
        self.warned_missing_gz = False

        self.create_subscription(Odometry, odom_topic, self._odom_callback, 10)
        self.create_timer(1.0 / follow_rate, self._publish_pose_to_gazebo)

    def _odom_callback(self, msg: Odometry) -> None:
        self.latest_odom = msg

    def _publish_pose_to_gazebo(self) -> None:
        if self.latest_odom is None:
            return
        if self.gz_executable is None:
            if not self.warned_missing_gz:
                self.get_logger().warning(
                    'gz executable not found; follow camera disabled'
                )
                self.warned_missing_gz = True
            return

        chaser = self.latest_odom.pose.pose.position
        target = (
            chaser.x + self.target_offset[0],
            chaser.y + self.target_offset[1],
            chaser.z + self.target_offset[2],
        )
        camera = (
            chaser.x + self.offset[0],
            chaser.y + self.offset[1],
            chaser.z + self.offset[2],
        )
        orientation = look_at_quaternion(camera, target)
        command = [
            self.gz_executable,
            'service',
            '-s',
            f'/world/{self.world_name}/set_pose',
            '--reqtype',
            'gz.msgs.Pose',
            '--reptype',
            'gz.msgs.Boolean',
            '--timeout',
            str(int(self.command_timeout * 1000.0)),
            '--req',
            self._pose_request_text(self.entity_name, camera, orientation),
        ]
        try:
            subprocess.run(
                command,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=self.command_timeout,
            )
        except subprocess.TimeoutExpired:
            self.get_logger().debug('timed out while updating follow camera pose')

    def _positive_parameter(self, name: str) -> float:
        value = float(self.get_parameter(name).value)
        if value <= 0.0:
            raise ValueError(f'{name} must be positive')
        return value

    def _vector_parameter(self, name: str) -> Vector3:
        value = self.get_parameter(name).value
        if not isinstance(value, Sequence) or len(value) != 3:
            raise ValueError(f'{name} must contain 3 elements')
        return (float(value[0]), float(value[1]), float(value[2]))

    @staticmethod
    def _format_values(values: Sequence[float]) -> list[str]:
        return [f'{float(value):.9g}' for value in values]

    @staticmethod
    def _pose_request_text(
        entity_name: str,
        position: Sequence[float],
        orientation: Sequence[float],
    ) -> str:
        px, py, pz = FollowCameraPoseNode._format_values(position)
        qx, qy, qz, qw = FollowCameraPoseNode._format_values(orientation)
        return (
            f'name: "{entity_name}" '
            f'position {{ x: {px} y: {py} z: {pz} }} '
            f'orientation {{ x: {qx} y: {qy} z: {qz} w: {qw} }}'
        )


def look_at_quaternion(camera: Sequence[float], target: Sequence[float]) -> Quaternion:
    """Return a world-frame quaternion with +X camera axis looking at target."""
    direction = _unit(_subtract(target, camera))
    yaw = math.atan2(direction[1], direction[0])
    pitch = math.atan2(-direction[2], math.hypot(direction[0], direction[1]))
    return _quaternion_from_euler(0.0, pitch, yaw)


def _subtract(left: Sequence[float], right: Sequence[float]) -> Vector3:
    return (
        float(left[0]) - float(right[0]),
        float(left[1]) - float(right[1]),
        float(left[2]) - float(right[2]),
    )


def _unit(values: Sequence[float]) -> Vector3:
    norm = math.sqrt(sum(float(value) * float(value) for value in values))
    if norm <= 0.0:
        raise ValueError('cannot normalize zero-length vector')
    return tuple(float(value) / norm for value in values)


def _quaternion_from_euler(roll: float, pitch: float, yaw: float) -> Quaternion:
    half_roll = 0.5 * roll
    half_pitch = 0.5 * pitch
    half_yaw = 0.5 * yaw
    cr = math.cos(half_roll)
    sr = math.sin(half_roll)
    cp = math.cos(half_pitch)
    sp = math.sin(half_pitch)
    cy = math.cos(half_yaw)
    sy = math.sin(half_yaw)
    return (
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy,
        cr * cp * cy + sr * sp * sy,
    )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = FollowCameraPoseNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            try:
                node.destroy_node()
            except KeyboardInterrupt:
                pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
