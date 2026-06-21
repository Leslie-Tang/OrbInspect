"""ROS 2 node for ROS-native HCW state propagation."""

from __future__ import annotations

from collections.abc import Sequence
import math

from geometry_msgs.msg import AccelStamped, TransformStamped
from nav_msgs.msg import Odometry
from orbinspect_dynamics.hcw_dynamics import HCWDynamics
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from tf2_ros import TransformBroadcaster


class HCWDynamicsNode(Node):
    """Publish the chaser LVLH state using HCW dynamics as truth."""

    def __init__(self) -> None:
        super().__init__('hcw_dynamics_node')

        self.declare_parameter('gravitational_parameter', 3.986004418e14)
        self.declare_parameter('earth_radius', 6378137.0)
        self.declare_parameter('reference_altitude', 400000.0)
        self.declare_parameter('mean_motion', 0.0)
        self.declare_parameter('integration_dt', 0.05)
        self.declare_parameter('publish_rate', 20.0)
        self.declare_parameter('initial_position_lvlh', [0.0, -35.0, 10.0])
        self.declare_parameter('initial_velocity_lvlh', [0.0, 0.0, 0.0])
        self.declare_parameter('frame_id', 'lvlh')
        self.declare_parameter('child_frame_id', 'chaser_body')

        self.integration_dt = self._positive_parameter('integration_dt')
        self.publish_rate = self._positive_parameter('publish_rate')
        self.frame_id = self.get_parameter('frame_id').value
        self.child_frame_id = self.get_parameter('child_frame_id').value

        mean_motion = self._mean_motion_from_parameters()
        self.dynamics = HCWDynamics(mean_motion)

        position = self._vector_parameter('initial_position_lvlh', 3)
        velocity = self._vector_parameter('initial_velocity_lvlh', 3)
        self.state = tuple(position + velocity)
        self.command_acceleration = (0.0, 0.0, 0.0)

        self.odom_pub = self.create_publisher(Odometry, '/chaser/odom', 10)
        self.state_pub = self.create_publisher(Odometry, '/chaser/state_lvlh', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.create_subscription(
            AccelStamped,
            '/chaser/safe_control_command',
            self._control_callback,
            10,
        )

        self.create_timer(self.integration_dt, self._integrate_once)
        self.create_timer(1.0 / self.publish_rate, self._publish_state)
        self._publish_state()

    def _control_callback(self, msg: AccelStamped) -> None:
        self.command_acceleration = (
            float(msg.accel.linear.x),
            float(msg.accel.linear.y),
            float(msg.accel.linear.z),
        )

    def _integrate_once(self) -> None:
        self.state = self.dynamics.rk4_step(
            self.state,
            self.command_acceleration,
            self.integration_dt,
        )

    def _publish_state(self) -> None:
        stamp = self.get_clock().now().to_msg()
        odom = self._make_odometry(stamp)
        self.odom_pub.publish(odom)
        self.state_pub.publish(odom)
        self.tf_broadcaster.sendTransform(self._make_transform(stamp))

    def _make_odometry(self, stamp) -> Odometry:
        rx, ry, rz, vx, vy, vz = self.state
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = self.frame_id
        odom.child_frame_id = self.child_frame_id
        odom.pose.pose.position.x = rx
        odom.pose.pose.position.y = ry
        odom.pose.pose.position.z = rz
        odom.pose.pose.orientation.w = 1.0
        odom.twist.twist.linear.x = vx
        odom.twist.twist.linear.y = vy
        odom.twist.twist.linear.z = vz
        return odom

    def _make_transform(self, stamp) -> TransformStamped:
        rx, ry, rz, _vx, _vy, _vz = self.state
        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = self.frame_id
        transform.child_frame_id = self.child_frame_id
        transform.transform.translation.x = rx
        transform.transform.translation.y = ry
        transform.transform.translation.z = rz
        transform.transform.rotation.w = 1.0
        return transform

    def _mean_motion_from_parameters(self) -> float:
        configured_mean_motion = float(self.get_parameter('mean_motion').value)
        if configured_mean_motion > 0.0:
            return configured_mean_motion

        mu = self._positive_parameter('gravitational_parameter')
        earth_radius = self._positive_parameter('earth_radius')
        altitude = self._positive_parameter('reference_altitude')
        reference_radius = earth_radius + altitude
        return math.sqrt(mu / reference_radius**3)

    def _positive_parameter(self, name: str) -> float:
        value = float(self.get_parameter(name).value)
        if value <= 0.0:
            raise ValueError(f'{name} must be positive')
        return value

    def _vector_parameter(self, name: str, expected_length: int) -> list[float]:
        value = self.get_parameter(name).value
        if not isinstance(value, Sequence) or len(value) != expected_length:
            raise ValueError(f'{name} must contain {expected_length} elements')
        return [float(item) for item in value]


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = HCWDynamicsNode()
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
