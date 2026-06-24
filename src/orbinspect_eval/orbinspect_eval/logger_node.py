"""ROS 2 CSV logger for the ROS-only OrbInspect demo."""

from __future__ import annotations

from collections.abc import Sequence
import csv
import json
import math
from pathlib import Path
import signal

from geometry_msgs.msg import AccelStamped, PointStamped, PoseStamped
from nav_msgs.msg import Odometry
from orbinspect_eval.metrics import delta_v_increment
from orbinspect_eval.metrics import is_saturated
from orbinspect_eval.metrics import vector_norm
from orbinspect_eval.plot_results import generate_figures
from orbinspect_interfaces.msg import CoverageMap
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String


TRAJECTORY_COLUMNS = (
    'time',
    'rx',
    'ry',
    'rz',
    'vx',
    'vy',
    'vz',
    'qx',
    'qy',
    'qz',
    'qw',
    'tracking_error_norm',
    'planned_rx',
    'planned_ry',
    'planned_rz',
    'planned_vx',
    'planned_vy',
    'planned_vz',
    'planned_ax',
    'planned_ay',
    'planned_az',
    'position_tracking_error_norm',
    'velocity_tracking_error_norm',
    'state_tracking_error_norm',
    'boresight_x',
    'boresight_y',
    'boresight_z',
)

CONTROL_COLUMNS = (
    'time',
    'ax_nom',
    'ay_nom',
    'az_nom',
    'ax_safe',
    'ay_safe',
    'az_safe',
    'control_norm',
    'acceleration_norm',
    'delta_v_increment',
    'cumulative_delta_v',
    'is_saturated',
)

COVERAGE_COLUMNS = (
    'time',
    'total_targets',
    'inspected_targets',
    'coverage_ratio',
    'new_targets_seen',
    'visible_target_count',
)

MISSION_EVENT_COLUMNS = (
    'time',
    'event',
    'state',
    'current_waypoint_id',
    'current_waypoint_index',
    'coverage_ratio',
)

SAFETY_COLUMNS = (
    'time',
    'minimum_distance',
    'safety_margin',
    'clearance',
    'is_safe',
    'in_caution_zone',
    'nearest_primitive',
    'filter_active',
    'filter_reason',
    'ax_nom',
    'ay_nom',
    'az_nom',
    'ax_safe',
    'ay_safe',
    'az_safe',
)

PLANNER_COLUMNS = (
    'time',
    'event',
    'waypoint_id',
    'x',
    'y',
    'z',
    'score',
    'coverage_gain',
    'travel_distance',
    'fuel_estimate',
    'safety_margin',
    'view_quality',
    'evaluated_candidates',
    'planning_time',
)


class CsvLoggerNode(Node):
    """Record trajectory and control topics to paper-ready CSV files."""

    def __init__(self) -> None:
        super().__init__('csv_logger_node')

        self.declare_parameter('result_root', 'data/results')
        self.declare_parameter('run_id', '')
        self.declare_parameter('reuse_run_id', False)
        self.declare_parameter('save_figures', True)
        self.declare_parameter('max_acceleration', 0.01)
        self.declare_parameter('default_reference', [8.0, -20.0, 6.0])

        self.workspace_root = Path.cwd()
        self.result_root = self._resolve_workspace_path(
            str(self.get_parameter('result_root').value)
        )
        self.run_id = str(self.get_parameter('run_id').value)
        self.reuse_run_id = bool(self.get_parameter('reuse_run_id').value)
        self.save_figures = bool(self.get_parameter('save_figures').value)
        self.max_acceleration = self._positive_parameter('max_acceleration')
        self.reference = tuple(self._vector_parameter('default_reference', 3))
        self.reference_velocity = (0.0, 0.0, 0.0)
        self.reference_acceleration = (0.0, 0.0, 0.0)
        self.boresight = (1.0, 0.0, 0.0)

        self.result_dir = self._create_result_dir()
        self.raw_dir = self.result_dir / 'raw'
        self.figures_dir = self.result_dir / 'figures'
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)

        self.start_time = self.get_clock().now()
        self.last_control_time: float | None = None
        self.latest_nominal = (0.0, 0.0, 0.0)
        self.latest_safe = (0.0, 0.0, 0.0)
        self.received_safe_command = False
        self.pending_nominal: dict[tuple[int, int], tuple[float, float, float]] = {}
        self.control_row_by_stamp: dict[tuple[int, int], int] = {}
        self.cumulative_delta_v = 0.0
        self.trajectory_rows: list[dict[str, object]] = []
        self.control_rows: list[dict[str, object]] = []
        self.coverage_rows: list[dict[str, object]] = []
        self.mission_event_rows: list[dict[str, object]] = []
        self.safety_rows: list[dict[str, object]] = []
        self.planner_rows: list[dict[str, object]] = []
        self.finalized = False

        self.create_subscription(Odometry, '/chaser/odom', self._odom_callback, 10)
        self.create_subscription(
            AccelStamped,
            '/chaser/control_command',
            self._control_callback,
            10,
        )
        self.create_subscription(
            AccelStamped,
            '/chaser/safe_control_command',
            self._safe_control_callback,
            10,
        )
        self.create_subscription(
            PointStamped,
            '/chaser/reference',
            self._reference_callback,
            10,
        )
        self.create_subscription(
            Odometry,
            '/chaser/reference_state',
            self._reference_state_callback,
            10,
        )
        self.create_subscription(
            PoseStamped,
            '/chaser/attitude_reference',
            self._attitude_reference_callback,
            10,
        )
        self.create_subscription(
            CoverageMap,
            '/inspection/coverage_map',
            self._coverage_callback,
            10,
        )
        self.create_subscription(
            String,
            '/mission/event',
            self._mission_event_callback,
            10,
        )
        self.create_subscription(
            String,
            '/chaser/safety_status',
            self._safety_status_callback,
            10,
        )
        self.create_subscription(
            String,
            '/planner/event',
            self._planner_event_callback,
            10,
        )
        self.get_logger().info(f'logging results to {self.result_dir}')

    def _odom_callback(self, msg: Odometry) -> None:
        position = (
            float(msg.pose.pose.position.x),
            float(msg.pose.pose.position.y),
            float(msg.pose.pose.position.z),
        )
        velocity = (
            float(msg.twist.twist.linear.x),
            float(msg.twist.twist.linear.y),
            float(msg.twist.twist.linear.z),
        )
        orientation = msg.pose.pose.orientation
        position_error = tuple(
            position[index] - self.reference[index]
            for index in range(3)
        )
        velocity_error = tuple(
            velocity[index] - self.reference_velocity[index]
            for index in range(3)
        )
        position_error_norm = vector_norm(position_error)
        velocity_error_norm = vector_norm(velocity_error)
        self.trajectory_rows.append({
            'time': self._elapsed_time(),
            'rx': position[0],
            'ry': position[1],
            'rz': position[2],
            'vx': velocity[0],
            'vy': velocity[1],
            'vz': velocity[2],
            'qx': float(orientation.x),
            'qy': float(orientation.y),
            'qz': float(orientation.z),
            'qw': float(orientation.w),
            'tracking_error_norm': position_error_norm,
            'planned_rx': self.reference[0],
            'planned_ry': self.reference[1],
            'planned_rz': self.reference[2],
            'planned_vx': self.reference_velocity[0],
            'planned_vy': self.reference_velocity[1],
            'planned_vz': self.reference_velocity[2],
            'planned_ax': self.reference_acceleration[0],
            'planned_ay': self.reference_acceleration[1],
            'planned_az': self.reference_acceleration[2],
            'position_tracking_error_norm': position_error_norm,
            'velocity_tracking_error_norm': velocity_error_norm,
            'state_tracking_error_norm': math.sqrt(
                position_error_norm * position_error_norm
                + velocity_error_norm * velocity_error_norm
            ),
            'boresight_x': self.boresight[0],
            'boresight_y': self.boresight[1],
            'boresight_z': self.boresight[2],
        })

    def _control_callback(self, msg: AccelStamped) -> None:
        stamp_key = self._stamp_key(msg)
        nominal = self._acceleration_from_msg(msg)
        self.latest_nominal = nominal
        if stamp_key in self.control_row_by_stamp:
            self._update_nominal_control_sample(stamp_key, nominal)
            return
        if not self.received_safe_command:
            self.latest_safe = nominal
            self._record_control_sample(stamp_key, nominal, nominal)
            return
        self.pending_nominal[stamp_key] = nominal

    def _safe_control_callback(self, msg: AccelStamped) -> None:
        stamp_key = self._stamp_key(msg)
        safe = self._acceleration_from_msg(msg)
        nominal = self.pending_nominal.pop(stamp_key, safe)
        self.latest_safe = safe
        self.received_safe_command = True
        if stamp_key in self.control_row_by_stamp:
            self._update_safe_control_sample(stamp_key, safe)
            return
        self._record_control_sample(stamp_key, nominal, safe)

    def _reference_callback(self, msg: PointStamped) -> None:
        self.reference = (
            float(msg.point.x),
            float(msg.point.y),
            float(msg.point.z),
        )
        self.reference_velocity = (0.0, 0.0, 0.0)
        self.reference_acceleration = (0.0, 0.0, 0.0)

    def _reference_state_callback(self, msg: Odometry) -> None:
        self.reference = (
            float(msg.pose.pose.position.x),
            float(msg.pose.pose.position.y),
            float(msg.pose.pose.position.z),
        )
        self.reference_velocity = (
            float(msg.twist.twist.linear.x),
            float(msg.twist.twist.linear.y),
            float(msg.twist.twist.linear.z),
        )
        self.reference_acceleration = (
            float(msg.twist.twist.angular.x),
            float(msg.twist.twist.angular.y),
            float(msg.twist.twist.angular.z),
        )

    def _attitude_reference_callback(self, msg: PoseStamped) -> None:
        orientation = msg.pose.orientation
        self.boresight = _boresight_from_quaternion(
            float(orientation.x),
            float(orientation.y),
            float(orientation.z),
            float(orientation.w),
        )

    def _coverage_callback(self, msg: CoverageMap) -> None:
        self.coverage_rows.append({
            'time': self._elapsed_time(),
            'total_targets': int(msg.total_targets),
            'inspected_targets': int(msg.inspected_targets),
            'coverage_ratio': float(msg.coverage_ratio),
            'new_targets_seen': int(msg.new_targets_seen),
            'visible_target_count': int(msg.visible_target_count),
        })

    def _mission_event_callback(self, msg: String) -> None:
        try:
            event = json.loads(msg.data)
        except json.JSONDecodeError:
            event = {'event': msg.data}
        self.mission_event_rows.append({
            'time': float(event.get('time', self._elapsed_time())),
            'event': str(event.get('event', 'unknown')),
            'state': str(event.get('state', 'unknown')),
            'current_waypoint_id': str(event.get('current_waypoint_id', '')),
            'current_waypoint_index': int(event.get('current_waypoint_index', -1)),
            'coverage_ratio': float(event.get('coverage_ratio', 0.0)),
        })

    def _safety_status_callback(self, msg: String) -> None:
        try:
            status = json.loads(msg.data)
        except json.JSONDecodeError:
            status = {}
        self.safety_rows.append({
            'time': float(status.get('time', self._elapsed_time())),
            'minimum_distance': float(status.get('minimum_distance', 0.0)),
            'safety_margin': float(status.get('safety_margin', 0.0)),
            'clearance': float(status.get('clearance', 0.0)),
            'is_safe': bool(status.get('is_safe', False)),
            'in_caution_zone': bool(status.get('in_caution_zone', False)),
            'nearest_primitive': str(status.get('nearest_primitive', '')),
            'filter_active': bool(status.get('filter_active', False)),
            'filter_reason': str(status.get('filter_reason', '')),
            'ax_nom': float(status.get('ax_nom', 0.0)),
            'ay_nom': float(status.get('ay_nom', 0.0)),
            'az_nom': float(status.get('az_nom', 0.0)),
            'ax_safe': float(status.get('ax_safe', 0.0)),
            'ay_safe': float(status.get('ay_safe', 0.0)),
            'az_safe': float(status.get('az_safe', 0.0)),
        })

    def _planner_event_callback(self, msg: String) -> None:
        try:
            event = json.loads(msg.data)
        except json.JSONDecodeError:
            event = {'event': msg.data}
        self.planner_rows.append({
            'time': float(event.get('time', self._elapsed_time())),
            'event': str(event.get('event', 'unknown')),
            'waypoint_id': str(event.get('waypoint_id', '')),
            'x': float(event.get('x', 0.0)),
            'y': float(event.get('y', 0.0)),
            'z': float(event.get('z', 0.0)),
            'score': float(event.get('score', 0.0)),
            'coverage_gain': int(event.get('coverage_gain', 0)),
            'travel_distance': float(event.get('travel_distance', 0.0)),
            'fuel_estimate': float(event.get('fuel_estimate', 0.0)),
            'safety_margin': float(event.get('safety_margin', 0.0)),
            'view_quality': float(event.get('view_quality', 0.0)),
            'evaluated_candidates': int(event.get('evaluated_candidates', 0)),
            'planning_time': float(event.get('planning_time', 0.0)),
        })

    def _record_control_sample(
        self,
        stamp_key: tuple[int, int],
        nominal: tuple[float, float, float],
        safe: tuple[float, float, float],
    ) -> None:
        now = self._elapsed_time()
        dt = 0.0 if self.last_control_time is None else max(0.0, now - self.last_control_time)
        self.last_control_time = now

        control_norm = vector_norm(nominal)
        acceleration_norm = vector_norm(safe)
        increment = delta_v_increment(acceleration_norm, dt)
        self.cumulative_delta_v += increment
        self.control_rows.append({
            'time': now,
            'ax_nom': nominal[0],
            'ay_nom': nominal[1],
            'az_nom': nominal[2],
            'ax_safe': safe[0],
            'ay_safe': safe[1],
            'az_safe': safe[2],
            'control_norm': control_norm,
            'acceleration_norm': acceleration_norm,
            'delta_v_increment': increment,
            'cumulative_delta_v': self.cumulative_delta_v,
            'is_saturated': is_saturated(acceleration_norm, self.max_acceleration),
        })
        self.control_row_by_stamp[stamp_key] = len(self.control_rows) - 1

    def _update_nominal_control_sample(
        self,
        stamp_key: tuple[int, int],
        nominal: tuple[float, float, float],
    ) -> None:
        row = self.control_rows[self.control_row_by_stamp[stamp_key]]
        row['ax_nom'] = nominal[0]
        row['ay_nom'] = nominal[1]
        row['az_nom'] = nominal[2]
        row['control_norm'] = vector_norm(nominal)

    def _update_safe_control_sample(
        self,
        stamp_key: tuple[int, int],
        safe: tuple[float, float, float],
    ) -> None:
        row = self.control_rows[self.control_row_by_stamp[stamp_key]]
        row['ax_safe'] = safe[0]
        row['ay_safe'] = safe[1]
        row['az_safe'] = safe[2]
        row['acceleration_norm'] = vector_norm(safe)

    def finalize(self) -> None:
        """Write CSV files, summary JSON, and figures once."""
        if self.finalized:
            return
        self.finalized = True
        self._write_csv(self.raw_dir / 'trajectory.csv', TRAJECTORY_COLUMNS, self.trajectory_rows)
        self._write_csv(self.raw_dir / 'control.csv', CONTROL_COLUMNS, self.control_rows)
        self._write_csv(self.raw_dir / 'coverage.csv', COVERAGE_COLUMNS, self.coverage_rows)
        self._write_csv(
            self.raw_dir / 'mission_events.csv',
            MISSION_EVENT_COLUMNS,
            self.mission_event_rows,
        )
        self._write_csv(self.raw_dir / 'safety.csv', SAFETY_COLUMNS, self.safety_rows)
        self._write_csv(self.raw_dir / 'planner.csv', PLANNER_COLUMNS, self.planner_rows)
        figures = []
        if self.save_figures:
            try:
                figures = generate_figures(self.result_dir)
            except (OSError, ValueError) as exc:
                self.get_logger().warning(f'failed to generate figures: {exc}')
        self._write_summary(figures)
        self._write_summary_markdown()

    def _write_summary(self, figure_paths: list[Path]) -> None:
        position_errors = [
            float(row['position_tracking_error_norm'])
            for row in self.trajectory_rows
        ]
        velocity_errors = [
            float(row['velocity_tracking_error_norm'])
            for row in self.trajectory_rows
        ]
        summary = {
            'result_dir': str(self.result_dir),
            'trajectory_samples': len(self.trajectory_rows),
            'control_samples': len(self.control_rows),
            'coverage_samples': len(self.coverage_rows),
            'mission_event_samples': len(self.mission_event_rows),
            'safety_samples': len(self.safety_rows),
            'planner_samples': len(self.planner_rows),
            'cumulative_delta_v': self.cumulative_delta_v,
            'mean_position_tracking_error': _mean(position_errors),
            'max_position_tracking_error': max(position_errors) if position_errors else 0.0,
            'mean_velocity_tracking_error': _mean(velocity_errors),
            'max_velocity_tracking_error': max(velocity_errors) if velocity_errors else 0.0,
            'figures': [path.name for path in figure_paths],
            'topics': [
                '/chaser/odom',
                '/chaser/reference_state',
                '/chaser/control_command',
                '/chaser/safe_control_command',
                '/inspection/coverage_map',
                '/mission/event',
                '/chaser/safety_status',
                '/planner/event',
            ],
        }
        with (self.result_dir / 'summary.json').open('w') as summary_file:
            json.dump(summary, summary_file, indent=2)

    def _write_summary_markdown(self) -> None:
        lines = [
            '# OrbInspect Run Summary',
            '',
            f'- Trajectory samples: {len(self.trajectory_rows)}',
            f'- Control samples: {len(self.control_rows)}',
            f'- Coverage samples: {len(self.coverage_rows)}',
            f'- Mission events: {len(self.mission_event_rows)}',
            f'- Safety samples: {len(self.safety_rows)}',
            f'- Planner samples: {len(self.planner_rows)}',
            f'- Cumulative delta-v: {self.cumulative_delta_v:.6f} m/s',
        ]
        position_errors = [
            float(row['position_tracking_error_norm'])
            for row in self.trajectory_rows
        ]
        if position_errors:
            lines.append(f'- Mean position tracking error: {_mean(position_errors):.6f} m')
            lines.append(f'- Max position tracking error: {max(position_errors):.6f} m')
        if self.coverage_rows:
            final_coverage = self.coverage_rows[-1]['coverage_ratio']
            lines.append(f'- Final coverage ratio: {final_coverage:.6f}')
        with (self.result_dir / 'summary.md').open('w') as summary_file:
            summary_file.write('\n'.join(lines) + '\n')

    @staticmethod
    def _write_csv(
        path: Path,
        columns: tuple[str, ...],
        rows: list[dict[str, object]],
    ) -> None:
        sorted_rows = sorted(rows, key=lambda row: float(row.get('time', 0.0)))
        with path.open('w', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(sorted_rows)

    def _create_result_dir(self) -> Path:
        if self.run_id:
            run_name = self.run_id
        else:
            stamp = self.get_clock().now().to_msg()
            run_name = f'{stamp.sec}_{stamp.nanosec:09d}'
        result_dir = self.result_root / run_name
        if self.run_id and self.reuse_run_id:
            result_dir.mkdir(parents=True, exist_ok=True)
            return result_dir
        counter = 1
        while result_dir.exists():
            result_dir = self.result_root / f'{run_name}_{counter:02d}'
            counter += 1
        result_dir.mkdir(parents=True)
        return result_dir

    def _resolve_workspace_path(self, path_text: str) -> Path:
        path = Path(path_text).expanduser()
        if path.is_absolute():
            return path
        return self.workspace_root / path

    def _elapsed_time(self) -> float:
        return (self.get_clock().now() - self.start_time).nanoseconds * 1.0e-9

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

    @staticmethod
    def _acceleration_from_msg(msg: AccelStamped) -> tuple[float, float, float]:
        return (
            float(msg.accel.linear.x),
            float(msg.accel.linear.y),
            float(msg.accel.linear.z),
        )

    @staticmethod
    def _stamp_key(msg: AccelStamped) -> tuple[int, int]:
        return (int(msg.header.stamp.sec), int(msg.header.stamp.nanosec))


def _boresight_from_quaternion(
    qx: float,
    qy: float,
    qz: float,
    qw: float,
) -> tuple[float, float, float]:
    """Return body +X axis expressed in the parent frame."""
    norm = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    if norm <= 0.0:
        return (1.0, 0.0, 0.0)
    qx /= norm
    qy /= norm
    qz /= norm
    qw /= norm
    return (
        1.0 - 2.0 * (qy * qy + qz * qz),
        2.0 * (qx * qy + qz * qw),
        2.0 * (qx * qz - qy * qw),
    )


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(float(value) for value in values) / len(values)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = CsvLoggerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            node.finalize()
        finally:
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass
        finally:
            if rclpy.ok():
                rclpy.shutdown()


if __name__ == '__main__':
    main()
