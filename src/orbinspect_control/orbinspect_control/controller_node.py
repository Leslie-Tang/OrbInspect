"""ROS 2 baseline waypoint controller node."""

from __future__ import annotations

from collections.abc import Sequence

from geometry_msgs.msg import AccelStamped, PointStamped
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry, Path
from orbinspect_control.lqr_controller import LQRController
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class ControllerNode(Node):
    """Track a fixed LVLH waypoint using a saturated PD fallback."""

    def __init__(self) -> None:
        super().__init__('controller_node')

        self.declare_parameter('position_gain', 0.0008)
        self.declare_parameter('velocity_gain', 0.08)
        self.declare_parameter('max_acceleration', 0.01)
        self.declare_parameter('control_rate', 10.0)
        self.declare_parameter('default_reference', [8.0, -20.0, 6.0])
        self.declare_parameter('frame_id', 'lvlh')
        self.declare_parameter('publish_safe_command_passthrough', True)

        self.frame_id = str(self.get_parameter('frame_id').value)
        self.publish_safe_passthrough = bool(
            self.get_parameter('publish_safe_command_passthrough').value
        )
        self.controller = LQRController(
            position_gain=self._nonnegative_parameter('position_gain'),
            velocity_gain=self._nonnegative_parameter('velocity_gain'),
            max_acceleration=self._positive_parameter('max_acceleration'),
        )
        control_rate = self._positive_parameter('control_rate')

        self.state: tuple[float, float, float, float, float, float] | None = None
        self.reference = tuple(self._vector_parameter('default_reference', 3))
        self.trajectory = Path()
        self.trajectory.header.frame_id = self.frame_id

        self.control_pub = self.create_publisher(
            AccelStamped,
            '/chaser/control_command',
            10,
        )
        self.safe_control_pub = self.create_publisher(
            AccelStamped,
            '/chaser/safe_control_command',
            10,
        )
        self.trajectory_pub = self.create_publisher(Path, '/chaser/trajectory', 10)
        self.create_subscription(Odometry, '/chaser/odom', self._odom_callback, 10)
        self.create_subscription(
            PointStamped,
            '/chaser/reference',
            self._reference_callback,
            10,
        )
        self.create_timer(1.0 / control_rate, self._publish_control)

    def _odom_callback(self, msg: Odometry) -> None:
        self.state = (
            float(msg.pose.pose.position.x),
            float(msg.pose.pose.position.y),
            float(msg.pose.pose.position.z),
            float(msg.twist.twist.linear.x),
            float(msg.twist.twist.linear.y),
            float(msg.twist.twist.linear.z),
        )
        self._append_trajectory_pose(msg)

    def _reference_callback(self, msg: PointStamped) -> None:
        self.reference = (
            float(msg.point.x),
            float(msg.point.y),
            float(msg.point.z),
        )

    def _publish_control(self) -> None:
        if self.state is None:
            return

        command = self.controller.compute_control(self.state, self.reference)
        msg = AccelStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.accel.linear.x = command[0]
        msg.accel.linear.y = command[1]
        msg.accel.linear.z = command[2]
        self.control_pub.publish(msg)

        if self.publish_safe_passthrough:
            self.safe_control_pub.publish(msg)

    def _append_trajectory_pose(self, msg: Odometry) -> None:
        pose = PoseStamped()
        pose.header = msg.header
        pose.pose = msg.pose.pose
        self.trajectory.header.stamp = msg.header.stamp
        self.trajectory.poses.append(pose)
        if len(self.trajectory.poses) > 500:
            self.trajectory.poses = self.trajectory.poses[-500:]
        self.trajectory_pub.publish(self.trajectory)

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

    def _vector_parameter(self, name: str, expected_length: int) -> list[float]:
        value = self.get_parameter(name).value
        if not isinstance(value, Sequence) or len(value) != expected_length:
            raise ValueError(f'{name} must contain {expected_length} elements')
        return [float(item) for item in value]


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = ControllerNode()
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
