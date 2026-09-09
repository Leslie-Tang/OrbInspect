"""ROS node coordinating the fixed waypoint inspection mission."""

from __future__ import annotations

from collections.abc import Sequence
import json
import math

from geometry_msgs.msg import PointStamped
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from nav_msgs.msg import Path
from orbinspect_guidance.fixed_waypoint_planner import FixedWaypointPlanner
from orbinspect_guidance.fixed_waypoint_planner import InspectionWaypoint
from orbinspect_interfaces.msg import CoverageMap
from orbinspect_mission.state_machine import MissionStateMachine
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String


class MissionManagerNode(Node):
    """Publish waypoints and stop the fixed waypoint inspection mission."""

    def __init__(self) -> None:
        super().__init__('mission_manager_node')

        self.declare_parameter('waypoints_flat', self._default_waypoint_parameters())
        self.declare_parameter('waypoint_tolerance', 1.5)
        self.declare_parameter('coverage_threshold', 0.1)
        self.declare_parameter('publish_rate', 2.0)
        self.declare_parameter('frame_id', 'lvlh')

        self.frame_id = str(self.get_parameter('frame_id').value)
        self.waypoint_tolerance = self._positive_parameter('waypoint_tolerance')
        self.coverage_threshold = self._positive_parameter('coverage_threshold')
        publish_rate = self._positive_parameter('publish_rate')
        waypoint_values = self._waypoint_vectors_from_flat_parameter('waypoints_flat')
        self.waypoints = FixedWaypointPlanner(waypoint_values).waypoints
        self.current_waypoint_index = 0
        self.latest_position: tuple[float, float, float] | None = None
        self.coverage_ratio = 0.0
        self.state_machine = MissionStateMachine()
        self.mission_complete = False

        self.reference_pub = self.create_publisher(PointStamped, '/chaser/reference', 10)
        self.current_waypoint_pub = self.create_publisher(
            PointStamped,
            '/inspection/current_waypoint',
            10,
        )
        self.waypoints_pub = self.create_publisher(Path, '/inspection/waypoints', 10)
        self.status_pub = self.create_publisher(String, '/mission/status', 10)
        self.event_pub = self.create_publisher(String, '/mission/event', 10)

        self.create_subscription(Odometry, '/chaser/odom', self._odom_callback, 10)
        self.create_subscription(
            CoverageMap,
            '/inspection/coverage_map',
            self._coverage_callback,
            10,
        )
        self.state_machine.start()
        self._publish_event('mission_started')
        self.create_timer(1.0 / publish_rate, self._tick)

    def _odom_callback(self, msg: Odometry) -> None:
        self.latest_position = (
            float(msg.pose.pose.position.x),
            float(msg.pose.pose.position.y),
            float(msg.pose.pose.position.z),
        )

    def _coverage_callback(self, msg: CoverageMap) -> None:
        self.coverage_ratio = float(msg.coverage_ratio)

    def _tick(self) -> None:
        self._publish_waypoint_path()
        self._publish_status()
        if self.mission_complete:
            return
        if self.coverage_ratio >= self.coverage_threshold:
            self.state_machine.coverage_complete()
            self._publish_event('coverage_threshold_reached')
            self._finish_mission()
            return
        active_waypoint = self.waypoints[self.current_waypoint_index]
        self._publish_active_waypoint(active_waypoint)
        if self.latest_position is None:
            return
        distance_to_waypoint = self._distance(
            self.latest_position,
            active_waypoint.position,
        )
        if distance_to_waypoint > self.waypoint_tolerance:
            return
        self.state_machine.waypoint_reached()
        self._publish_event('waypoint_reached')
        self.current_waypoint_index += 1
        if self.current_waypoint_index >= len(self.waypoints):
            self.state_machine.waypoints_complete()
            self._publish_event('waypoints_complete')
            self._finish_mission()
        else:
            self.state_machine.resume()
            self._publish_event('waypoint_selected')

    def _publish_active_waypoint(self, waypoint: InspectionWaypoint) -> None:
        msg = PointStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.point.x, msg.point.y, msg.point.z = waypoint.position
        self.reference_pub.publish(msg)
        self.current_waypoint_pub.publish(msg)

    def _publish_waypoint_path(self) -> None:
        path = Path()
        path.header.stamp = self.get_clock().now().to_msg()
        path.header.frame_id = self.frame_id
        for waypoint in self.waypoints:
            pose = PoseStamped()
            pose.header = path.header
            pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = waypoint.position
            pose.pose.orientation.w = 1.0
            path.poses.append(pose)
        self.waypoints_pub.publish(path)

    def _publish_status(self) -> None:
        self.status_pub.publish(String(data=self.state_machine.state.value))

    def _publish_event(self, event_type: str) -> None:
        waypoint = self.waypoints[min(self.current_waypoint_index, len(self.waypoints) - 1)]
        event = {
            'time': self.get_clock().now().nanoseconds * 1.0e-9,
            'event': event_type,
            'state': self.state_machine.state.value,
            'current_waypoint_id': waypoint.waypoint_id,
            'current_waypoint_index': self.current_waypoint_index,
            'coverage_ratio': self.coverage_ratio,
        }
        self.event_pub.publish(String(data=json.dumps(event, sort_keys=True)))

    def _finish_mission(self) -> None:
        self.state_machine.complete()
        self.mission_complete = True
        self._publish_event('mission_complete')
        self._publish_status()

    def _positive_parameter(self, name: str) -> float:
        value = float(self.get_parameter(name).value)
        if value <= 0.0:
            raise ValueError(f'{name} must be positive')
        return value

    @staticmethod
    def _distance(left: Sequence[float], right: Sequence[float]) -> float:
        return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(left, right)))

    @staticmethod
    def _default_waypoint_parameters() -> list[float]:
        return [
            coordinate
            for waypoint in FixedWaypointPlanner.default_waypoints()
            for coordinate in waypoint.position
        ]

    def _waypoint_vectors_from_flat_parameter(self, name: str) -> list[list[float]]:
        values = self.get_parameter(name).value
        if len(values) % 3 != 0:
            raise ValueError(f'{name} length must be divisible by 3')
        return [
            [float(values[index]), float(values[index + 1]), float(values[index + 2])]
            for index in range(0, len(values), 3)
        ]


def main(args: Sequence[str] | None = None) -> None:
    rclpy.init(args=args)
    node = MissionManagerNode()
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
