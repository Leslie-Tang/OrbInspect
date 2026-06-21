"""Publish a fixed LVLH waypoint for the Phase 3 RViz demo."""

from __future__ import annotations

from collections.abc import Sequence

from geometry_msgs.msg import PointStamped
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class ReferencePublisherNode(Node):
    """Publish a fixed reference point on /chaser/reference."""

    def __init__(self) -> None:
        super().__init__('reference_publisher_node')

        self.declare_parameter('reference_position', [8.0, -20.0, 6.0])
        self.declare_parameter('publish_rate', 2.0)
        self.declare_parameter('frame_id', 'lvlh')

        self.reference = self._vector_parameter('reference_position', 3)
        self.frame_id = str(self.get_parameter('frame_id').value)
        publish_rate = self._positive_parameter('publish_rate')

        self.reference_pub = self.create_publisher(
            PointStamped,
            '/chaser/reference',
            10,
        )
        self.create_timer(1.0 / publish_rate, self._publish_reference)
        self._publish_reference()

    def _publish_reference(self) -> None:
        msg = PointStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.point.x = self.reference[0]
        msg.point.y = self.reference[1]
        msg.point.z = self.reference[2]
        self.reference_pub.publish(msg)

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
    node = ReferencePublisherNode()
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
