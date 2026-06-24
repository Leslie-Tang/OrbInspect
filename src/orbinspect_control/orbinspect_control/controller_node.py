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
        self.declare_parameter('controller_type', 'pd')
        self.declare_parameter('mean_motion', 0.0011313666536110225)
        self.declare_parameter('lqr_state_weights', [1.0, 1.0, 1.0, 80.0, 80.0, 80.0])
        self.declare_parameter('lqr_control_weights', [4000.0, 4000.0, 4000.0])
        self.declare_parameter('riccati_iterations', 200)
        self.declare_parameter('mpc_horizon', 8)
        self.declare_parameter('mpc_max_iterations', 35)
        self.declare_parameter('default_reference', [8.0, -20.0, 6.0])
        self.declare_parameter('frame_id', 'lvlh')
        self.declare_parameter('publish_safe_command_passthrough', True)

        self.frame_id = str(self.get_parameter('frame_id').value)
        self.publish_safe_passthrough = bool(
            self.get_parameter('publish_safe_command_passthrough').value
        )
        control_rate = self._positive_parameter('control_rate')
        self.controller = LQRController(
            position_gain=self._nonnegative_parameter('position_gain'),
            velocity_gain=self._nonnegative_parameter('velocity_gain'),
            max_acceleration=self._positive_parameter('max_acceleration'),
            controller_type=str(self.get_parameter('controller_type').value),
            mean_motion=self._positive_parameter('mean_motion'),
            control_dt=1.0 / control_rate,
            state_weights=self._vector_parameter('lqr_state_weights', 6),
            control_weights=self._vector_parameter('lqr_control_weights', 3),
            riccati_iterations=self._positive_int_parameter('riccati_iterations'),
            mpc_horizon=self._positive_int_parameter('mpc_horizon'),
            mpc_max_iterations=self._positive_int_parameter('mpc_max_iterations'),
        )

        self.state: tuple[float, float, float, float, float, float] | None = None
        self.reference = tuple(self._vector_parameter('default_reference', 3))
        self.reference_velocity = (0.0, 0.0, 0.0)
        self.feedforward_acceleration = (0.0, 0.0, 0.0)
        self.trajectory = Path()
        self.trajectory.header.frame_id = self.frame_id

        self.control_pub = self.create_publisher(
            AccelStamped,
            '/chaser/control_command',
            10,
        )
        self.safe_control_pub = (
            self.create_publisher(AccelStamped, '/chaser/safe_control_command', 10)
            if self.publish_safe_passthrough
            else None
        )
        self.trajectory_pub = self.create_publisher(Path, '/chaser/trajectory', 10)
        self.create_subscription(Odometry, '/chaser/odom', self._odom_callback, 10)
        self.create_subscription(
            PointStamped,
            '/chaser/reference',
            self._reference_callback,
            10,
        )
        self.create_subscription(
            Odometry,
            '/chaser/reference_state',
            self._reference_state_callback,
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
        self.reference_velocity = (0.0, 0.0, 0.0)
        self.feedforward_acceleration = (0.0, 0.0, 0.0)

    def _reference_state_callback(self, msg: Odometry) -> None:
        self.reference = (
            float(msg.pose.pose.position.x),
            float(msg.pose.pose.position.y),
            float(msg.pose.pose.position.z),
        )
        self.reference_velocity = (
            float(msg.twist.twist.linear.x),
            float(msg.twist.twist.linear.y),
            float(msg.twist.twist.linear.z),
        )
        self.feedforward_acceleration = (
            float(msg.twist.twist.angular.x),
            float(msg.twist.twist.angular.y),
            float(msg.twist.twist.angular.z),
        )

    def _publish_control(self) -> None:
        if self.state is None:
            return

        command = self.controller.compute_control(
            self.state,
            self.reference,
            self.reference_velocity,
            self.feedforward_acceleration,
        )
        msg = AccelStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.accel.linear.x = command[0]
        msg.accel.linear.y = command[1]
        msg.accel.linear.z = command[2]
        self.control_pub.publish(msg)

        if self.safe_control_pub is not None:
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

    def _positive_int_parameter(self, name: str) -> int:
        value = int(self.get_parameter(name).value)
        if value <= 0:
            raise ValueError(f'{name} must be positive')
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
