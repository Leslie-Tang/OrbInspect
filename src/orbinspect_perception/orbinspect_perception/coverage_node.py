"""ROS node that computes inspection coverage from chaser odometry."""

from __future__ import annotations

from collections.abc import Sequence

from nav_msgs.msg import Odometry
from orbinspect_interfaces.msg import CoverageMap as CoverageMapMsg
from orbinspect_interfaces.msg import InspectionTarget as InspectionTargetMsg
from orbinspect_interfaces.msg import InspectionTargetArray
from orbinspect_perception.coverage_map import CoverageMap
from orbinspect_perception.inspection_target_manager import InspectionTargetManager
from orbinspect_perception.visibility_checker import CameraModel
from orbinspect_perception.visibility_checker import VisibilityChecker
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float64


class CoverageNode(Node):
    """Publish target coverage map and coverage ratio."""

    def __init__(self) -> None:
        super().__init__('coverage_node')

        self.declare_parameter('target_spacing', 8.0)
        self.declare_parameter('horizontal_fov_deg', 70.0)
        self.declare_parameter('vertical_fov_deg', 50.0)
        self.declare_parameter('min_range', 2.0)
        self.declare_parameter('max_range', 25.0)
        self.declare_parameter('max_view_angle_deg', 60.0)
        self.declare_parameter('dwell_time', 1.0)
        self.declare_parameter('publish_rate', 2.0)
        self.declare_parameter('frame_id', 'lvlh')

        self.frame_id = str(self.get_parameter('frame_id').value)
        target_spacing = self._positive_parameter('target_spacing')
        dwell_time = self._positive_parameter('dwell_time')
        publish_rate = self._positive_parameter('publish_rate')
        camera = CameraModel(
            horizontal_fov_deg=self._positive_parameter('horizontal_fov_deg'),
            vertical_fov_deg=self._positive_parameter('vertical_fov_deg'),
            min_range=self._positive_parameter('min_range'),
            max_range=self._positive_parameter('max_range'),
            max_view_angle_deg=self._positive_parameter('max_view_angle_deg'),
        )
        targets = InspectionTargetManager(target_spacing).generate_targets()
        self.coverage_map = CoverageMap(targets, dwell_time)
        self.visibility_checker = VisibilityChecker(camera)
        self.latest_position: tuple[float, float, float] | None = None
        self.last_update_time = self.get_clock().now()
        self.visible_target_count = 0
        self.new_targets_seen = 0

        self.targets_pub = self.create_publisher(InspectionTargetArray, '/inspection/targets', 10)
        self.coverage_map_pub = self.create_publisher(
            CoverageMapMsg,
            '/inspection/coverage_map',
            10,
        )
        self.coverage_ratio_pub = self.create_publisher(Float64, '/inspection/coverage_ratio', 10)
        self.create_subscription(Odometry, '/chaser/odom', self._odom_callback, 10)
        self.create_timer(1.0 / publish_rate, self._update_and_publish)

    def _odom_callback(self, msg: Odometry) -> None:
        self.latest_position = (
            float(msg.pose.pose.position.x),
            float(msg.pose.pose.position.y),
            float(msg.pose.pose.position.z),
        )

    def _update_and_publish(self) -> None:
        now = self.get_clock().now()
        dt = (now - self.last_update_time).nanoseconds * 1.0e-9
        self.last_update_time = now
        if self.latest_position is not None:
            visible_target_ids = {
                state.target.target_id
                for state in self.coverage_map.states
                if self.visibility_checker.is_visible(
                    self.latest_position,
                    state.target.position,
                    state.target.normal,
                )
            }
            self.visible_target_count, self.new_targets_seen = self.coverage_map.update(
                visible_target_ids,
                max(0.0, dt),
            )
        self._publish_targets()
        self._publish_coverage_map()
        self.coverage_ratio_pub.publish(Float64(data=self.coverage_map.coverage_ratio))

    def _publish_targets(self) -> None:
        msg = InspectionTargetArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.targets = [self._target_msg(state) for state in self.coverage_map.states]
        self.targets_pub.publish(msg)

    def _publish_coverage_map(self) -> None:
        msg = CoverageMapMsg()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.targets = [self._target_msg(state) for state in self.coverage_map.states]
        msg.total_targets = self.coverage_map.total_targets
        msg.inspected_targets = self.coverage_map.inspected_targets
        msg.coverage_ratio = self.coverage_map.coverage_ratio
        msg.visible_target_count = self.visible_target_count
        msg.new_targets_seen = self.new_targets_seen
        self.coverage_map_pub.publish(msg)

    def _target_msg(self, state) -> InspectionTargetMsg:
        msg = InspectionTargetMsg()
        msg.header.frame_id = self.frame_id
        msg.target_id = state.target.target_id
        msg.position.x, msg.position.y, msg.position.z = state.target.position
        msg.normal.x, msg.normal.y, msg.normal.z = state.target.normal
        msg.inspected = state.inspected
        msg.inspection_count = state.inspection_count
        msg.dwell_time = state.dwell_time
        return msg

    def _positive_parameter(self, name: str) -> float:
        value = float(self.get_parameter(name).value)
        if value <= 0.0:
            raise ValueError(f'{name} must be positive')
        return value


def main(args: Sequence[str] | None = None) -> None:
    rclpy.init(args=args)
    node = CoverageNode()
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
