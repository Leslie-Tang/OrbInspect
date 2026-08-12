"""Credit frozen observations only when closed-loop execution gates pass."""

from __future__ import annotations

from collections.abc import Sequence
import csv
import json
import math
from pathlib import Path

from nav_msgs.msg import Odometry
from orbinspect_interfaces.msg import CoverageMap
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String


class VerificationEvaluatorNode(Node):
    """Evaluate terminal tracking gates for one frozen scenario and method."""

    def __init__(self) -> None:
        """Load the selected route and create evidence publishers."""
        super().__init__('verification_evaluator_node')
        self.declare_parameter('result_dir', '')
        self.declare_parameter('scenario_id', '')
        self.declare_parameter('method', '')
        self.declare_parameter('position_tolerance', 0.5)
        self.declare_parameter('velocity_tolerance', 0.05)
        self.declare_parameter('goal_coverage', 0.80)
        self.declare_parameter('max_sooas', 14)
        self.declare_parameter('publish_rate', 20.0)
        self.declare_parameter('frame_id', 'lvlh')

        self.result_dir = Path(str(self.get_parameter('result_dir').value))
        self.scenario_id = str(self.get_parameter('scenario_id').value)
        self.method = str(self.get_parameter('method').value)
        if not self.scenario_id or not self.method:
            raise ValueError('scenario_id and method are required')
        self.position_tolerance = self._positive('position_tolerance')
        self.velocity_tolerance = self._positive('velocity_tolerance')
        self.goal_coverage = self._positive('goal_coverage')
        self.max_sooas = int(self.get_parameter('max_sooas').value)
        if self.max_sooas <= 0:
            raise ValueError('max_sooas must be positive')
        publish_rate = self._positive('publish_rate')
        self.frame_id = str(self.get_parameter('frame_id').value)

        self.observations = _load_observations(
            self.result_dir,
            self.scenario_id,
            self.method,
        )
        self.latest_state: tuple[float, ...] | None = None
        self.start_time = self.get_clock().now()
        self.next_observation = 0
        self.coverage = 0.0
        self.credited_actions = 0
        self.failed_actions = 0
        self.finished = False

        self.coverage_pub = self.create_publisher(
            CoverageMap,
            '/inspection/coverage_map',
            10,
        )
        self.event_pub = self.create_publisher(String, '/mission/event', 10)
        self.status_pub = self.create_publisher(
            String,
            '/verification/status',
            10,
        )
        self.create_subscription(Odometry, '/chaser/odom', self._odom, 10)
        self.create_timer(1.0 / publish_rate, self._tick)

    def _odom(self, msg: Odometry) -> None:
        self.latest_state = (
            float(msg.pose.pose.position.x),
            float(msg.pose.pose.position.y),
            float(msg.pose.pose.position.z),
            float(msg.twist.twist.linear.x),
            float(msg.twist.twist.linear.y),
            float(msg.twist.twist.linear.z),
        )

    def _tick(self) -> None:
        if self.finished or self.latest_state is None:
            return
        elapsed = (
            self.get_clock().now() - self.start_time
        ).nanoseconds * 1.0e-9
        if self.next_observation >= len(self.observations):
            self._finish(elapsed)
            return
        observation = self.observations[self.next_observation]
        if elapsed + 1.0e-9 < float(observation['time']):
            return

        result = evaluate_observation(
            self.latest_state,
            observation['state'],
            self.position_tolerance,
            self.velocity_tolerance,
        )
        credited = bool(result['credited'])
        if credited:
            self.coverage = max(
                self.coverage,
                float(observation['weighted_coverage']),
            )
            self.credited_actions += 1
        else:
            self.failed_actions += 1
        self.next_observation += 1
        self._publish_coverage(observation, credited)
        event = {
            'time': elapsed,
            'event': 'observation_credited' if credited else 'observation_rejected',
            'state': 'executing',
            'current_waypoint_id': observation['candidate_id'],
            'current_waypoint_index': int(observation['action']),
            'coverage_ratio': self.coverage,
            **result,
        }
        self.event_pub.publish(String(data=json.dumps(event, sort_keys=True)))
        self.status_pub.publish(String(data=json.dumps(event, sort_keys=True)))
        if self.next_observation >= len(self.observations):
            self._finish(elapsed)

    def _publish_coverage(
        self,
        observation: dict[str, object],
        credited: bool,
    ) -> None:
        msg = CoverageMap()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.total_targets = int(observation['total_targets'])
        msg.inspected_targets = int(observation['covered_targets'])
        msg.coverage_ratio = self.coverage
        msg.visible_target_count = int(observation['visible_target_count'])
        msg.new_targets_seen = (
            int(observation['visible_target_count']) if credited else 0
        )
        self.coverage_pub.publish(msg)

    def _finish(self, elapsed: float) -> None:
        if self.finished:
            return
        self.finished = True
        success = (
            self.coverage >= self.goal_coverage
            and self.credited_actions <= self.max_sooas
            and self.failed_actions == 0
        )
        payload = {
            'time': elapsed,
            'event': 'mission_complete' if success else 'mission_failed',
            'state': 'complete' if success else 'failed',
            'current_waypoint_id': '',
            'current_waypoint_index': self.next_observation,
            'coverage_ratio': self.coverage,
            'credited_actions': self.credited_actions,
            'failed_actions': self.failed_actions,
            'success': success,
            'reason': (
                'all_execution_gates_passed'
                if success else 'terminal_tracking_or_coverage_gate_failed'
            ),
        }
        message = String(data=json.dumps(payload, sort_keys=True))
        self.event_pub.publish(message)
        self.status_pub.publish(message)

    def _positive(self, name: str) -> float:
        value = float(self.get_parameter(name).value)
        if value <= 0.0:
            raise ValueError(f'{name} must be positive')
        return value


def evaluate_observation(
    executed: Sequence[float],
    planned: Sequence[float],
    position_tolerance: float,
    velocity_tolerance: float,
) -> dict[str, float | bool]:
    """Return position/speed errors and whether the observation is creditable."""
    position_error = math.sqrt(sum(
        (float(executed[index]) - float(planned[index])) ** 2
        for index in range(3)
    ))
    terminal_speed = math.sqrt(sum(
        float(executed[index]) ** 2 for index in range(3, 6)
    ))
    return {
        'position_error': position_error,
        'terminal_speed': terminal_speed,
        'credited': (
            position_error <= position_tolerance
            and terminal_speed <= velocity_tolerance
        ),
    }


def _load_observations(
    result_dir: Path,
    scenario_id: str,
    method: str,
) -> tuple[dict[str, object], ...]:
    raw_dir = result_dir / 'raw'
    trajectory = _selected_csv(
        raw_dir / 'trajectory.csv',
        scenario_id,
        method,
    )
    viewpoints = _selected_csv(
        raw_dir / 'viewpoints.csv',
        scenario_id,
        method,
    )
    terminal_by_action = {}
    for row in trajectory:
        terminal_by_action[int(row['action'])] = row
    observations = []
    for row in viewpoints:
        action = int(row['action'])
        terminal = terminal_by_action[action]
        visible = {
            item for item in row.get('visible_target_ids', '').split(';')
            if item
        }
        observations.append({
            'action': action,
            'candidate_id': row['candidate_id'],
            'time': float(row['time']),
            'state': tuple(
                float(terminal[name])
                for name in ('rx', 'ry', 'rz', 'vx', 'vy', 'vz')
            ),
            'weighted_coverage': float(row['weighted_coverage']),
            'visible_target_count': len(visible),
            'covered_targets': int(row['covered_target_count']),
            'total_targets': int(row['total_target_count']),
        })
    return tuple(sorted(observations, key=lambda item: int(item['action'])))


def _selected_csv(
    path: Path,
    scenario_id: str,
    method: str,
) -> list[dict[str, str]]:
    with path.open(newline='') as handle:
        rows = [
            row for row in csv.DictReader(handle)
            if row.get('scenario_id') == scenario_id
            and row.get('method') == method
        ]
    if not rows:
        raise ValueError(f'no rows for {scenario_id}/{method} in {path}')
    return rows


def main(args: list[str] | None = None) -> None:
    """Run the verification evaluator node."""
    rclpy.init(args=args)
    node = VerificationEvaluatorNode()
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
