"""ROS node that filters nominal control commands for keep-out safety."""

from __future__ import annotations

from collections.abc import Sequence
import json

from geometry_msgs.msg import AccelStamped
from nav_msgs.msg import Odometry
from orbinspect_safety.collision_checker import CollisionChecker
from orbinspect_safety.keepout_zones import KeepoutZoneModel
from orbinspect_safety.projection_filter import ProjectionSafetyFilter
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String


class SafetyFilterNode(Node):
    """Publish filtered acceleration commands for the dynamics node."""

    def __init__(self) -> None:
        super().__init__('safety_filter_node')

        self.declare_parameter('safety_margin', 2.0)
        self.declare_parameter('caution_margin', 8.0)
        self.declare_parameter('max_acceleration', 0.01)
        self.declare_parameter('max_speed', 0.25)
        self.declare_parameter('repulsion_gain', 0.004)
        self.declare_parameter('braking_time', 4.0)
        self.declare_parameter('frame_id', 'lvlh')

        self.frame_id = str(self.get_parameter('frame_id').value)
        checker = CollisionChecker(
            KeepoutZoneModel(
                safety_margin=self._positive_parameter('safety_margin'),
                caution_margin=self._positive_parameter('caution_margin'),
            )
        )
        self.filter = ProjectionSafetyFilter(
            checker=checker,
            max_acceleration=self._positive_parameter('max_acceleration'),
            max_speed=self._positive_parameter('max_speed'),
            repulsion_gain=self._nonnegative_parameter('repulsion_gain'),
            braking_time=self._positive_parameter('braking_time'),
        )
        self.latest_position: tuple[float, float, float] | None = None
        self.latest_velocity = (0.0, 0.0, 0.0)

        self.safe_control_pub = self.create_publisher(
            AccelStamped,
            '/chaser/safe_control_command',
            10,
        )
        self.status_pub = self.create_publisher(String, '/chaser/safety_status', 10)
        self.create_subscription(Odometry, '/chaser/odom', self._odom_callback, 10)
        self.create_subscription(
            AccelStamped,
            '/chaser/control_command',
            self._control_callback,
            10,
        )

    def _odom_callback(self, msg: Odometry) -> None:
        self.latest_position = (
            float(msg.pose.pose.position.x),
            float(msg.pose.pose.position.y),
            float(msg.pose.pose.position.z),
        )
        self.latest_velocity = (
            float(msg.twist.twist.linear.x),
            float(msg.twist.twist.linear.y),
            float(msg.twist.twist.linear.z),
        )

    def _control_callback(self, msg: AccelStamped) -> None:
        command = (
            float(msg.accel.linear.x),
            float(msg.accel.linear.y),
            float(msg.accel.linear.z),
        )
        safe_command = command
        modified = False
        reason = 'no_state_yet'
        minimum_distance = 0.0
        safety_margin = 0.0
        clearance = 0.0
        in_caution_zone = False
        nearest_primitive = ''
        if self.latest_position is not None:
            result = self.filter.filter_command(
                self.latest_position,
                self.latest_velocity,
                command,
            )
            safe_command = result.command
            modified = result.modified
            reason = result.reason
            minimum_distance = result.minimum_distance
            safety_margin = result.safety_margin
            clearance = result.clearance
            in_caution_zone = result.in_caution_zone
            nearest_primitive = result.nearest_primitive

        safe_msg = AccelStamped()
        safe_msg.header = msg.header
        safe_msg.header.frame_id = self.frame_id
        safe_msg.accel.linear.x = safe_command[0]
        safe_msg.accel.linear.y = safe_command[1]
        safe_msg.accel.linear.z = safe_command[2]
        self.safe_control_pub.publish(safe_msg)
        self._publish_filter_status(
            modified,
            reason,
            minimum_distance,
            safety_margin,
            clearance,
            in_caution_zone,
            nearest_primitive,
            command,
            safe_command,
        )

    def _publish_filter_status(
        self,
        modified: bool,
        reason: str,
        minimum_distance: float,
        safety_margin: float,
        clearance: float,
        in_caution_zone: bool,
        nearest_primitive: str,
        nominal: tuple[float, float, float],
        safe: tuple[float, float, float],
    ) -> None:
        status = {
            'time': self.get_clock().now().nanoseconds * 1.0e-9,
            'minimum_distance': minimum_distance,
            'safety_margin': safety_margin,
            'clearance': clearance,
            'is_safe': clearance >= 0.0,
            'in_caution_zone': in_caution_zone,
            'nearest_primitive': nearest_primitive,
            'filter_active': modified,
            'filter_reason': reason,
            'ax_nom': nominal[0],
            'ay_nom': nominal[1],
            'az_nom': nominal[2],
            'ax_safe': safe[0],
            'ay_safe': safe[1],
            'az_safe': safe[2],
        }
        self.status_pub.publish(String(data=json.dumps(status, sort_keys=True)))

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


def main(args: Sequence[str] | None = None) -> None:
    rclpy.init(args=args)
    node = SafetyFilterNode()
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
