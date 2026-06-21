"""
Optional Basilisk dynamics backend adapter.

Basilisk is intentionally optional and HCW remains the default workflow.
"""

from __future__ import annotations

from collections.abc import Sequence
import importlib.util

import rclpy
from rclpy.node import Node


def basilisk_available() -> bool:
    """Return true when a Basilisk Python module can be imported."""
    return importlib.util.find_spec('Basilisk') is not None


class BasiliskUnavailableError(RuntimeError):
    """Raised when the optional Basilisk backend is requested but unavailable."""


class BasiliskAdapterNode(Node):
    """Placeholder ROS node for future Basilisk-backed propagation."""

    def __init__(self) -> None:
        super().__init__('basilisk_adapter_node')
        if not basilisk_available():
            raise BasiliskUnavailableError(
                'Basilisk is not installed; use dynamics_backend:=hcw or install Basilisk'
            )
        self.get_logger().info('Basilisk detected, but detailed adapter is deferred')


def main(args: Sequence[str] | None = None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = BasiliskAdapterNode()
        rclpy.spin(node)
    except BasiliskUnavailableError as exc:
        print(str(exc))
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
