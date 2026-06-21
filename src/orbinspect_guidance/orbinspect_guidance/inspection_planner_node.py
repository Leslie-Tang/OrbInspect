"""ROS node for greedy next-best-view inspection planning."""

from __future__ import annotations

from collections.abc import Sequence
import json

from geometry_msgs.msg import PointStamped
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from nav_msgs.msg import Path
from orbinspect_guidance.greedy_nbv_planner import GreedyNBVPlanner
from orbinspect_guidance.greedy_nbv_planner import PlannerWeights
from orbinspect_guidance.waypoint_generator import distance
from orbinspect_guidance.waypoint_generator import WaypointGenerator
from orbinspect_interfaces.msg import CoverageMap
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String
from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray


class InspectionPlannerNode(Node):
    """Publish greedy NBV waypoints for the existing controller."""

    def __init__(self) -> None:
        super().__init__('inspection_planner_node')

        self.declare_parameter('coverage_threshold', 0.8)
        self.declare_parameter('max_waypoints', 40)
        self.declare_parameter('waypoint_tolerance', 2.0)
        self.declare_parameter('publish_rate', 1.0)
        self.declare_parameter('candidate_radius_min', 10.0)
        self.declare_parameter('candidate_radius_max', 28.0)
        self.declare_parameter('candidate_radial_steps', 3)
        self.declare_parameter('candidate_azimuth_steps', 16)
        self.declare_parameter('candidate_elevation_steps', 5)
        self.declare_parameter('sensor_range', 25.0)
        self.declare_parameter('weight_coverage', 10.0)
        self.declare_parameter('weight_distance', 0.08)
        self.declare_parameter('weight_fuel', 0.4)
        self.declare_parameter('weight_safety', 0.08)
        self.declare_parameter('weight_view_quality', 1.0)
        self.declare_parameter('frame_id', 'lvlh')

        self.frame_id = str(self.get_parameter('frame_id').value)
        self.coverage_threshold = self._positive_parameter('coverage_threshold')
        self.max_waypoints = self._positive_int_parameter('max_waypoints')
        self.waypoint_tolerance = self._positive_parameter('waypoint_tolerance')
        publish_rate = self._positive_parameter('publish_rate')
        self.latest_position: tuple[float, float, float] | None = None
        self.latest_coverage: CoverageMap | None = None
        self.current_waypoint = None
        self.completed = False
        self.visited_waypoints: set[str] = set()
        self.path_positions: list[tuple[float, float, float]] = []

        candidates = WaypointGenerator(
            radius_min=self._positive_parameter('candidate_radius_min'),
            radius_max=self._positive_parameter('candidate_radius_max'),
            radial_steps=self._positive_int_parameter('candidate_radial_steps'),
            azimuth_steps=self._positive_int_parameter('candidate_azimuth_steps'),
            elevation_steps=self._positive_int_parameter('candidate_elevation_steps'),
        ).generate()
        weights = PlannerWeights(
            coverage=self._positive_parameter('weight_coverage'),
            distance=self._nonnegative_parameter('weight_distance'),
            fuel=self._nonnegative_parameter('weight_fuel'),
            safety=self._nonnegative_parameter('weight_safety'),
            view_quality=self._nonnegative_parameter('weight_view_quality'),
        )
        self.planner = GreedyNBVPlanner(
            candidates,
            weights,
            sensor_range=self._positive_parameter('sensor_range'),
        )

        self.reference_pub = self.create_publisher(PointStamped, '/chaser/reference', 10)
        self.current_waypoint_pub = self.create_publisher(
            PointStamped,
            '/inspection/current_waypoint',
            10,
        )
        self.waypoints_pub = self.create_publisher(Path, '/inspection/waypoints', 10)
        self.path_pub = self.create_publisher(Path, '/inspection/planned_path', 10)
        self.status_pub = self.create_publisher(String, '/planner/status', 10)
        self.event_pub = self.create_publisher(String, '/planner/event', 10)
        self.marker_pub = self.create_publisher(
            MarkerArray,
            '/visualization/planner_markers',
            10,
        )
        self.create_subscription(Odometry, '/chaser/odom', self._odom_callback, 10)
        self.create_subscription(
            CoverageMap,
            '/inspection/coverage_map',
            self._coverage_callback,
            10,
        )
        self.create_timer(1.0 / publish_rate, self._tick)
        self.get_logger().info(f'generated {len(candidates)} safe NBV candidates')

    def _odom_callback(self, msg: Odometry) -> None:
        self.latest_position = (
            float(msg.pose.pose.position.x),
            float(msg.pose.pose.position.y),
            float(msg.pose.pose.position.z),
        )

    def _coverage_callback(self, msg: CoverageMap) -> None:
        self.latest_coverage = msg

    def _tick(self) -> None:
        self._publish_path()
        self._publish_markers()
        if self.completed or self.latest_position is None or self.latest_coverage is None:
            self._publish_status('waiting_for_inputs')
            return
        if self.latest_coverage.coverage_ratio >= self.coverage_threshold:
            self.completed = True
            self._publish_status('coverage_complete')
            self._publish_event('coverage_complete', None)
            return
        if len(self.visited_waypoints) >= self.max_waypoints:
            self.completed = True
            self._publish_status('max_waypoints_reached')
            self._publish_event('max_waypoints_reached', None)
            return
        if self.current_waypoint is None or self._active_waypoint_reached():
            self._select_next_waypoint()
        if self.current_waypoint is not None:
            self._publish_current_waypoint()
            self._publish_status('tracking')

    def _active_waypoint_reached(self) -> bool:
        return (
            self.current_waypoint is not None
            and distance(self.latest_position, self.current_waypoint.candidate.position)
            <= self.waypoint_tolerance
        )

    def _select_next_waypoint(self) -> None:
        if self.current_waypoint is not None:
            self.visited_waypoints.add(self.current_waypoint.candidate.waypoint_id)
        decision = self.planner.select_next(
            self.latest_position,
            self.latest_coverage,
            self.visited_waypoints,
        )
        if decision.selected is None:
            self.completed = True
            self._publish_status('no_candidate_available')
            self._publish_event('no_candidate_available', None)
            return
        self.current_waypoint = decision.selected
        self.path_positions.append(decision.selected.candidate.position)
        self._publish_event('waypoint_selected', decision)

    def _publish_current_waypoint(self) -> None:
        point = self.current_waypoint.candidate.position
        msg = PointStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.point.x, msg.point.y, msg.point.z = point
        self.reference_pub.publish(msg)
        self.current_waypoint_pub.publish(msg)

    def _publish_path(self) -> None:
        path = Path()
        path.header.stamp = self.get_clock().now().to_msg()
        path.header.frame_id = self.frame_id
        for position in self.path_positions:
            pose = PoseStamped()
            pose.header = path.header
            pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = position
            pose.pose.orientation.w = 1.0
            path.poses.append(pose)
        self.path_pub.publish(path)
        self.waypoints_pub.publish(path)

    def _publish_status(self, state: str) -> None:
        status = {
            'time': self.get_clock().now().nanoseconds * 1.0e-9,
            'state': state,
            'coverage_ratio': (
                float(self.latest_coverage.coverage_ratio)
                if self.latest_coverage is not None
                else 0.0
            ),
            'selected_waypoints': len(self.path_positions),
            'current_waypoint_id': (
                self.current_waypoint.candidate.waypoint_id
                if self.current_waypoint is not None
                else ''
            ),
        }
        self.status_pub.publish(String(data=json.dumps(status, sort_keys=True)))

    def _publish_event(self, event: str, decision) -> None:
        selected = decision.selected if decision is not None else None
        payload = {
            'time': self.get_clock().now().nanoseconds * 1.0e-9,
            'event': event,
            'waypoint_id': selected.candidate.waypoint_id if selected else '',
            'x': selected.candidate.position[0] if selected else 0.0,
            'y': selected.candidate.position[1] if selected else 0.0,
            'z': selected.candidate.position[2] if selected else 0.0,
            'score': selected.score if selected else 0.0,
            'coverage_gain': selected.coverage_gain if selected else 0,
            'travel_distance': selected.travel_distance if selected else 0.0,
            'fuel_estimate': selected.fuel_estimate if selected else 0.0,
            'safety_margin': selected.safety_margin if selected else 0.0,
            'view_quality': selected.view_quality if selected else 0.0,
            'evaluated_candidates': decision.evaluated_candidates if decision else 0,
            'planning_time': decision.planning_time if decision else 0.0,
        }
        self.event_pub.publish(String(data=json.dumps(payload, sort_keys=True)))

    def _publish_markers(self) -> None:
        markers = MarkerArray()
        if self.current_waypoint is not None:
            marker = Marker()
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.header.frame_id = self.frame_id
            marker.ns = 'planner'
            marker.id = 0
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            position = self.current_waypoint.candidate.position
            marker.pose.position.x = position[0]
            marker.pose.position.y = position[1]
            marker.pose.position.z = position[2]
            marker.pose.orientation.w = 1.0
            marker.scale.x = 1.0
            marker.scale.y = 1.0
            marker.scale.z = 1.0
            marker.color.r = 0.1
            marker.color.g = 0.4
            marker.color.b = 1.0
            marker.color.a = 0.9
            markers.markers.append(marker)
        self.marker_pub.publish(markers)

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

    def _positive_int_parameter(self, name: str) -> int:
        value = int(self.get_parameter(name).value)
        if value <= 0:
            raise ValueError(f'{name} must be positive')
        return value


def main(args: Sequence[str] | None = None) -> None:
    rclpy.init(args=args)
    node = InspectionPlannerNode()
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
