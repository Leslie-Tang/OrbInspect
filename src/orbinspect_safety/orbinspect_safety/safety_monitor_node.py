"""ROS node that publishes keep-out zone safety status."""

from __future__ import annotations

from collections.abc import Sequence
import json

from nav_msgs.msg import Odometry
from orbinspect_safety.collision_checker import CollisionChecker
from orbinspect_safety.keepout_zones import KeepoutZoneModel
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String
from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray


class SafetyMonitorNode(Node):
    """Monitor chaser clearance to station keep-out geometry."""

    def __init__(self) -> None:
        super().__init__('safety_monitor_node')

        self.declare_parameter('safety_margin', 2.0)
        self.declare_parameter('caution_margin', 8.0)
        self.declare_parameter('publish_rate', 5.0)
        self.declare_parameter('frame_id', 'lvlh')

        self.frame_id = str(self.get_parameter('frame_id').value)
        self.checker = CollisionChecker(
            KeepoutZoneModel(
                safety_margin=self._positive_parameter('safety_margin'),
                caution_margin=self._positive_parameter('caution_margin'),
            )
        )
        publish_rate = self._positive_parameter('publish_rate')
        self.latest_position: tuple[float, float, float] | None = None
        self.latest_velocity: tuple[float, float, float] | None = None

        self.status_pub = self.create_publisher(String, '/chaser/safety_status', 10)
        self.marker_pub = self.create_publisher(MarkerArray, '/safety/markers', 10)
        self.create_subscription(Odometry, '/chaser/odom', self._odom_callback, 10)
        self.create_timer(1.0 / publish_rate, self._publish_status)

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

    def _publish_status(self) -> None:
        if self.latest_position is None:
            return
        assessment = self.checker.assess(self.latest_position)
        status = {
            'time': self.get_clock().now().nanoseconds * 1.0e-9,
            'minimum_distance': assessment.minimum_distance,
            'safety_margin': assessment.safety_margin,
            'clearance': assessment.clearance,
            'is_safe': assessment.is_safe,
            'in_caution_zone': assessment.in_caution_zone,
            'nearest_primitive': assessment.surface_distance.primitive_name,
        }
        self.status_pub.publish(String(data=json.dumps(status, sort_keys=True)))
        self.marker_pub.publish(self._make_markers(assessment))

    def _make_markers(self, assessment) -> MarkerArray:
        stamp = self.get_clock().now().to_msg()
        markers = MarkerArray()
        chaser = Marker()
        chaser.header.stamp = stamp
        chaser.header.frame_id = self.frame_id
        chaser.ns = 'safety'
        chaser.id = 0
        chaser.type = Marker.SPHERE
        chaser.action = Marker.ADD
        chaser.pose.position.x = self.latest_position[0]
        chaser.pose.position.y = self.latest_position[1]
        chaser.pose.position.z = self.latest_position[2]
        chaser.pose.orientation.w = 1.0
        chaser.scale.x = assessment.safety_margin * 2.0
        chaser.scale.y = assessment.safety_margin * 2.0
        chaser.scale.z = assessment.safety_margin * 2.0
        if assessment.is_safe:
            chaser.color.r = 0.1
            chaser.color.g = 0.8
            chaser.color.b = 0.2
        else:
            chaser.color.r = 0.9
            chaser.color.g = 0.1
            chaser.color.b = 0.1
        chaser.color.a = 0.35
        markers.markers.append(chaser)

        closest = Marker()
        closest.header.stamp = stamp
        closest.header.frame_id = self.frame_id
        closest.ns = 'safety'
        closest.id = 1
        closest.type = Marker.SPHERE
        closest.action = Marker.ADD
        point = assessment.surface_distance.closest_point
        closest.pose.position.x = point[0]
        closest.pose.position.y = point[1]
        closest.pose.position.z = point[2]
        closest.pose.orientation.w = 1.0
        closest.scale.x = 0.5
        closest.scale.y = 0.5
        closest.scale.z = 0.5
        closest.color.r = 1.0
        closest.color.g = 0.7
        closest.color.b = 0.0
        closest.color.a = 0.9
        markers.markers.append(closest)
        return markers

    def _positive_parameter(self, name: str) -> float:
        value = float(self.get_parameter(name).value)
        if value <= 0.0:
            raise ValueError(f'{name} must be positive')
        return value


def main(args: Sequence[str] | None = None) -> None:
    rclpy.init(args=args)
    node = SafetyMonitorNode()
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
