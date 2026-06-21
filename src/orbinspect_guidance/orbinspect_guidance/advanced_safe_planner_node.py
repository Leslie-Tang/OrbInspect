"""ROS status node for the advanced safe planner placeholder."""

from __future__ import annotations

from collections.abc import Sequence
import json

from orbinspect_guidance.advanced_safe_planner import AdvancedPlannerConfig
from orbinspect_guidance.advanced_safe_planner import AdvancedSafePlanner
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String


class AdvancedSafePlannerNode(Node):
    """Publish placeholder status for future advanced safe planners."""

    def __init__(self) -> None:
        super().__init__('advanced_safe_planner_node')
        self.declare_parameter('method', 'placeholder')
        self.declare_parameter('horizon_steps', 20)
        self.declare_parameter('time_step', 1.0)
        self.declare_parameter('safety_margin', 2.0)
        self.declare_parameter('publish_rate', 1.0)
        config = AdvancedPlannerConfig(
            method=str(self.get_parameter('method').value),
            horizon_steps=int(self.get_parameter('horizon_steps').value),
            time_step=float(self.get_parameter('time_step').value),
            safety_margin=float(self.get_parameter('safety_margin').value),
        )
        self.planner = AdvancedSafePlanner(config)
        self.status_pub = self.create_publisher(String, '/advanced_planner/status', 10)
        publish_rate = float(self.get_parameter('publish_rate').value)
        if publish_rate <= 0.0:
            raise ValueError('publish_rate must be positive')
        self.create_timer(1.0 / publish_rate, self._publish_status)

    def _publish_status(self) -> None:
        status = {
            'time': self.get_clock().now().nanoseconds * 1.0e-9,
            'state': 'placeholder',
            'available': self.planner.available,
            'method': self.planner.config.method,
            'message': 'advanced safe planner scaffold is present but not active',
        }
        self.status_pub.publish(String(data=json.dumps(status, sort_keys=True)))


def main(args: Sequence[str] | None = None) -> None:
    rclpy.init(args=args)
    node = AdvancedSafePlannerNode()
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
