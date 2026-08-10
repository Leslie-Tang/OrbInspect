"""ROS node that publishes a precomputed CW-aware inspection trajectory."""

from __future__ import annotations

from collections.abc import Sequence

from geometry_msgs.msg import PointStamped
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from nav_msgs.msg import Path
from orbinspect_guidance.offline_cw_trajectory import OfflineCWTrajectoryGenerator
from orbinspect_guidance.offline_cw_trajectory import TrajectoryPoint
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class OfflineTrajectoryNode(Node):
    """Publish offline CW trajectory references for the controller."""

    def __init__(self) -> None:
        super().__init__('offline_trajectory_node')

        self.declare_parameter('frame_id', 'lvlh')
        self.declare_parameter('publish_rate', 5.0)
        self.declare_parameter('waypoint_tolerance', 1.5)
        self.declare_parameter('hold_final_waypoint', True)
        self.declare_parameter('advance_by_time', False)
        self.declare_parameter('initial_position_lvlh', [0.0, -35.0, 10.0])
        self.declare_parameter('initial_velocity_lvlh', [0.0, 0.0, 0.0])
        self.declare_parameter('mean_motion', 0.0011313666536110225)
        self.declare_parameter('segment_duration', 160.0)
        self.declare_parameter('integration_dt', 1.0)
        self.declare_parameter('max_acceleration', 0.01)
        self.declare_parameter('position_gain', 0.00055)
        self.declare_parameter('velocity_gain', 0.055)
        self.declare_parameter('safety_margin', 2.0)
        self.declare_parameter('dwell_samples', 20)
        self.declare_parameter('inspection_radius', 24.0)
        self.declare_parameter('z_levels', [8.0, 14.0])
        self.declare_parameter('station_x_extent', 36.0)
        self.declare_parameter('station_y_offset', 18.0)

        self.frame_id = str(self.get_parameter('frame_id').value)
        self.waypoint_tolerance = self._positive_parameter('waypoint_tolerance')
        self.hold_final_waypoint = bool(self.get_parameter('hold_final_waypoint').value)
        self.advance_by_time = bool(self.get_parameter('advance_by_time').value)
        publish_rate = self._positive_parameter('publish_rate')
        initial_state = (
            self._fixed_vector_parameter('initial_position_lvlh', 3)
            + self._fixed_vector_parameter('initial_velocity_lvlh', 3)
        )

        generator = OfflineCWTrajectoryGenerator(
            mean_motion=self._positive_parameter('mean_motion'),
            max_acceleration=self._positive_parameter('max_acceleration'),
            position_gain=self._nonnegative_parameter('position_gain'),
            velocity_gain=self._nonnegative_parameter('velocity_gain'),
            integration_dt=self._positive_parameter('integration_dt'),
            segment_duration=self._positive_parameter('segment_duration'),
            safety_margin=self._positive_parameter('safety_margin'),
        )
        waypoints = generator.generate_waypoints(
            inspection_radius=self._positive_parameter('inspection_radius'),
            z_levels=self._vector_parameter('z_levels'),
            station_x_extent=self._positive_parameter('station_x_extent'),
            station_y_offset=self._positive_parameter('station_y_offset'),
        )
        self.plan = generator.rollout(
            initial_state,
            waypoints,
            dwell_samples=self._nonnegative_int_parameter('dwell_samples'),
        )
        self.reference_index = 0
        self.latest_state: tuple[float, float, float] | None = None
        self.start_time = self.get_clock().now()

        self.reference_pub = self.create_publisher(PointStamped, '/chaser/reference', 10)
        self.path_pub = self.create_publisher(Path, '/inspection/offline_path', 10)
        self.create_subscription(Odometry, '/chaser/odom', self._odom_callback, 10)
        self.create_timer(1.0 / publish_rate, self._tick)
        self._publish_path()
        self.get_logger().info(
            f'generated offline CW trajectory with {len(waypoints)} waypoints '
            f'and {len(self.plan)} samples'
        )

    def _odom_callback(self, msg: Odometry) -> None:
        self.latest_state = (
            float(msg.pose.pose.position.x),
            float(msg.pose.pose.position.y),
            float(msg.pose.pose.position.z),
        )

    def _tick(self) -> None:
        if not self.plan:
            return
        if self.advance_by_time:
            self._advance_reference_by_elapsed_time()
        elif self.latest_state is not None:
            self._advance_reference_if_reached()
        self._publish_reference(self.plan[self.reference_index])

    def _advance_reference_by_elapsed_time(self) -> None:
        elapsed = (self.get_clock().now() - self.start_time).nanoseconds * 1.0e-9
        while (
            self.reference_index < len(self.plan) - 1
            and self.plan[self.reference_index + 1].time <= elapsed
        ):
            self.reference_index += 1

    def _advance_reference_if_reached(self) -> None:
        if self.reference_index >= len(self.plan) - 1:
            return
        current = self.plan[self.reference_index].reference
        error = sum(
            (self.latest_state[index] - current[index]) ** 2
            for index in range(3)
        ) ** 0.5
        if error <= self.waypoint_tolerance:
            self._skip_to_next_distinct_reference()
            return
        if not self.hold_final_waypoint:
            self.reference_index += 1

    def _skip_to_next_distinct_reference(self) -> None:
        current = self.plan[self.reference_index].reference
        while self.reference_index < len(self.plan) - 1:
            self.reference_index += 1
            if self.plan[self.reference_index].reference != current:
                return

    def _publish_reference(self, point: TrajectoryPoint) -> None:
        msg = PointStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.point.x = point.reference[0]
        msg.point.y = point.reference[1]
        msg.point.z = point.reference[2]
        self.reference_pub.publish(msg)

    def _publish_path(self) -> None:
        path = Path()
        path.header.stamp = self.get_clock().now().to_msg()
        path.header.frame_id = self.frame_id
        for point in self.plan:
            pose = PoseStamped()
            pose.header = path.header
            pose.pose.position.x = point.reference[0]
            pose.pose.position.y = point.reference[1]
            pose.pose.position.z = point.reference[2]
            pose.pose.orientation.w = 1.0
            path.poses.append(pose)
        self.path_pub.publish(path)

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

    def _nonnegative_int_parameter(self, name: str) -> int:
        value = int(self.get_parameter(name).value)
        if value < 0:
            raise ValueError(f'{name} must be non-negative')
        return value

    def _vector_parameter(self, name: str) -> list[float]:
        value = self.get_parameter(name).value
        if not isinstance(value, Sequence) or not value:
            raise ValueError(f'{name} must contain at least one value')
        return [float(item) for item in value]

    def _fixed_vector_parameter(self, name: str, expected_length: int) -> list[float]:
        value = self.get_parameter(name).value
        if not isinstance(value, Sequence) or len(value) != expected_length:
            raise ValueError(f'{name} must contain {expected_length} values')
        return [float(item) for item in value]


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = OfflineTrajectoryNode()
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
