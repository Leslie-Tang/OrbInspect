"""Publish RViz markers for inspection targets."""

from __future__ import annotations

from collections.abc import Sequence

from orbinspect_interfaces.msg import InspectionTargetArray
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray


class TargetMarkerNode(Node):
    """Convert inspection targets into colored RViz markers."""

    def __init__(self) -> None:
        super().__init__('target_marker_node')
        self.declare_parameter('marker_scale', 0.7)
        self.marker_scale = self._positive_parameter('marker_scale')
        self.marker_pub = self.create_publisher(MarkerArray, '/visualization/target_markers', 10)
        self.create_subscription(
            InspectionTargetArray,
            '/inspection/targets',
            self._targets_callback,
            10,
        )

    def _targets_callback(self, msg: InspectionTargetArray) -> None:
        marker_array = MarkerArray()
        for index, target in enumerate(msg.targets):
            marker = Marker()
            marker.header = msg.header
            marker.ns = 'inspection_targets'
            marker.id = index
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            marker.pose.position = target.position
            marker.pose.orientation.w = 1.0
            marker.scale.x = self.marker_scale
            marker.scale.y = self.marker_scale
            marker.scale.z = self.marker_scale
            marker.color.a = 1.0
            if target.inspected:
                marker.color.r = 0.1
                marker.color.g = 0.85
                marker.color.b = 0.25
            else:
                marker.color.r = 1.0
                marker.color.g = 0.55
                marker.color.b = 0.05
            marker_array.markers.append(marker)
        self.marker_pub.publish(marker_array)

    def _positive_parameter(self, name: str) -> float:
        value = float(self.get_parameter(name).value)
        if value <= 0.0:
            raise ValueError(f'{name} must be positive')
        return value


def main(args: Sequence[str] | None = None) -> None:
    rclpy.init(args=args)
    node = TargetMarkerNode()
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
