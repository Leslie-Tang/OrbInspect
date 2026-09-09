"""Publish a deterministic accelerated ROS simulation clock."""

from __future__ import annotations

import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rosgraph_msgs.msg import Clock


class AcceleratedClockNode(Node):
    """Advance the /clock topic from monotonic wall time at a fixed scale."""

    def __init__(self) -> None:
        """Create the wall-clock-driven simulation clock."""
        super().__init__('accelerated_clock_node')
        self.declare_parameter('time_scale', 10.0)
        self.declare_parameter('wall_publish_rate', 200.0)
        self.time_scale = self._positive('time_scale')
        publish_rate = self._positive('wall_publish_rate')
        self.wall_start = time.monotonic()
        self.publisher = self.create_publisher(Clock, '/clock', 10)
        self.create_timer(1.0 / publish_rate, self._publish)
        self._publish()

    def _publish(self) -> None:
        elapsed = max(0.0, time.monotonic() - self.wall_start)
        sec, nanosec = _clock_fields(elapsed * self.time_scale)
        message = Clock()
        message.clock.sec = sec
        message.clock.nanosec = nanosec
        self.publisher.publish(message)

    def _positive(self, name: str) -> float:
        value = float(self.get_parameter(name).value)
        if value <= 0.0:
            raise ValueError(f'{name} must be positive')
        return value


def _clock_fields(seconds: float) -> tuple[int, int]:
    whole = int(seconds)
    nanosec = int(round((seconds - whole) * 1.0e9))
    if nanosec >= 1_000_000_000:
        whole += 1
        nanosec -= 1_000_000_000
    return whole, nanosec


def main(args: list[str] | None = None) -> None:
    """Run the accelerated clock node."""
    rclpy.init(args=args)
    node = AcceleratedClockNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RuntimeError as exc:
        if not (
            not rclpy.ok()
            and "Unable to convert call argument '0' to Python object" in str(exc)
        ):
            raise
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
