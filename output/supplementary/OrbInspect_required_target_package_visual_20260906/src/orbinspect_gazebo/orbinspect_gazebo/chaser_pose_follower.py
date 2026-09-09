"""Visual-only Gazebo chaser pose follower for ROS odometry."""

from __future__ import annotations

from collections.abc import Sequence
import shutil
import subprocess
from time import monotonic

from nav_msgs.msg import Odometry
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class ChaserPoseFollower(Node):
    """Mirror /chaser/odom into the Gazebo chaser model pose."""

    def __init__(self) -> None:
        super().__init__('chaser_pose_follower')

        self.declare_parameter('entity_name', 'chaser')
        self.declare_parameter('world_name', 'iss_external_empty')
        self.declare_parameter('odom_topic', '/chaser/odom')
        self.declare_parameter('follow_rate', 2.0)
        self.declare_parameter('command_timeout', 0.6)
        self.declare_parameter('startup_delay', 2.0)

        self.entity_name = str(self.get_parameter('entity_name').value)
        self.world_name = str(self.get_parameter('world_name').value)
        odom_topic = str(self.get_parameter('odom_topic').value)
        self.command_timeout = self._positive_parameter('command_timeout')
        self.startup_delay = self._nonnegative_parameter('startup_delay')
        follow_rate = self._positive_parameter('follow_rate')
        self.gz_executable = shutil.which('gz')
        self.latest_odom: Odometry | None = None
        self.warned_missing_gz = False
        self.start_time = monotonic()

        self.create_subscription(Odometry, odom_topic, self._odom_callback, 10)
        self.create_timer(1.0 / follow_rate, self._publish_pose_to_gazebo)

    def _odom_callback(self, msg: Odometry) -> None:
        self.latest_odom = msg

    def _publish_pose_to_gazebo(self) -> None:
        if self.latest_odom is None:
            return
        if monotonic() - self.start_time < self.startup_delay:
            return
        if self.gz_executable is None:
            if not self.warned_missing_gz:
                self.get_logger().warning(
                    'gz executable not found; Gazebo pose follow disabled'
                )
                self.warned_missing_gz = True
            return

        pose = self.latest_odom.pose.pose
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
            self._pose_request_text(
                self.entity_name,
                (
                    pose.position.x,
                    pose.position.y,
                    pose.position.z,
                ),
                (
                    pose.orientation.x,
                    pose.orientation.y,
                    pose.orientation.z,
                    pose.orientation.w,
                ),
            ),
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
            self.get_logger().debug('timed out while updating Gazebo chaser pose')

    def _positive_parameter(self, name: str) -> float:
        value = float(self.get_parameter(name).value)
        if value <= 0.0:
            raise ValueError(f'{name} must be positive')
        return value

    def _nonnegative_parameter(self, name: str) -> float:
        value = float(self.get_parameter(name).value)
        if value < 0.0:
            raise ValueError(f'{name} must be non-negative')
        return value

    @staticmethod
    def _format_values(values: Sequence[float]) -> list[str]:
        return [f'{float(value):.9g}' for value in values]

    @staticmethod
    def _pose_request_text(
        entity_name: str,
        position: Sequence[float],
        orientation: Sequence[float],
    ) -> str:
        px, py, pz = ChaserPoseFollower._format_values(position)
        qx, qy, qz, qw = ChaserPoseFollower._format_values(orientation)
        return (
            f'name: "{entity_name}" '
            f'position {{ x: {px} y: {py} z: {pz} }} '
            f'orientation {{ x: {qx} y: {qy} z: {qz} w: {qw} }}'
        )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = ChaserPoseFollower()
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
