#!/usr/bin/env python3
"""Run a full closed-loop CW/MPC trajectory comparison offline."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path

from orbinspect_control.lqr_controller import LQRController
from orbinspect_dynamics.hcw_dynamics import HCWDynamics
from orbinspect_guidance.planned_trajectory_replay_node import _build_standoff_trajectory
from orbinspect_guidance.planned_trajectory_replay_node import _load_trajectory
from orbinspect_guidance.planned_trajectory_replay_node import _load_viewpoints
from orbinspect_safety.collision_checker import CollisionChecker
from orbinspect_safety.keepout_zones import KeepoutZoneModel
from orbinspect_safety.projection_filter import ProjectionSafetyFilter


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


def main() -> None:
    """Run full-mission closed-loop simulation and save paper outputs."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-result-dir', type=Path, default=Path('data/results/offline_high_coverage_experiment'))
    parser.add_argument('--method', default='set_cover_cw_tour')
    parser.add_argument('--output-root', type=Path, default=Path('data/results'))
    parser.add_argument('--run-id', default='')
    parser.add_argument('--dt', type=float, default=5.0)
    parser.add_argument('--mean-motion', type=float, default=0.0011313666536110225)
    parser.add_argument('--max-acceleration', type=float, default=0.03)
    parser.add_argument('--max-reference-speed', type=float, default=0.08)
    parser.add_argument('--max-reference-acceleration', type=float, default=0.01)
    parser.add_argument('--safe-shell-radius', type=float, default=110.0)
    parser.add_argument('--path-sample-spacing', type=float, default=0.75)
    parser.add_argument('--mpc-horizon', type=int, default=6)
    parser.add_argument('--mpc-max-iterations', type=int, default=20)
    args = parser.parse_args()

    reference = _reference_trajectory(args)
    result_dir = _make_result_dir(args.output_root, args.run_id)
    raw_dir = result_dir / 'raw'
    figures_dir = result_dir / 'figures'
    raw_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    trajectory_rows, control_rows, safety_rows, summary = _simulate(reference, args)
    _write_csv(raw_dir / 'trajectory.csv', TRAJECTORY_COLUMNS, trajectory_rows)
    _write_csv(raw_dir / 'control.csv', CONTROL_COLUMNS, control_rows)
    _write_csv(raw_dir / 'safety.csv', SAFETY_COLUMNS, safety_rows)
    _write_empty_csv(raw_dir / 'coverage.csv', ('time', 'total_targets', 'inspected_targets', 'coverage_ratio', 'new_targets_seen', 'visible_target_count'))
    _write_empty_csv(raw_dir / 'mission_events.csv', ('time', 'event', 'state', 'current_waypoint_id', 'current_waypoint_index', 'coverage_ratio'))
    _write_empty_csv(raw_dir / 'planner.csv', ('time', 'event', 'waypoint_id', 'x', 'y', 'z', 'score', 'coverage_gain', 'travel_distance', 'fuel_estimate', 'safety_margin', 'view_quality', 'evaluated_candidates', 'planning_time'))
    summary.update({
        'result_dir': str(result_dir),
        'source_result_dir': str(args.source_result_dir),
        'method': args.method,
        'controller': 'finite_horizon_cw_mpc',
        'dynamics_model': 'CW/HCW',
        'trajectory_samples': len(trajectory_rows),
        'control_samples': len(control_rows),
        'safety_samples': len(safety_rows),
    })
    with (result_dir / 'summary.json').open('w') as handle:
        json.dump(summary, handle, indent=2)
    (result_dir / 'summary.md').write_text(_summary_markdown(summary), encoding='utf-8')
    print(result_dir)


def _reference_trajectory(args) -> list[dict[str, float]]:
    csv_trajectory = _load_trajectory(args.source_result_dir, args.method)
    viewpoints = _load_viewpoints(args.source_result_dir, args.method)
    return _build_standoff_trajectory(
        csv_trajectory,
        viewpoints,
        args.safe_shell_radius,
        35.0,
        args.path_sample_spacing,
        args.max_reference_speed,
        args.max_reference_acceleration,
    )


def _simulate(reference: list[dict[str, float]], args) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    dynamics = HCWDynamics(args.mean_motion)
    controller = LQRController(
        position_gain=0.0015,
        velocity_gain=0.10,
        max_acceleration=args.max_acceleration,
        controller_type='mpc',
        mean_motion=args.mean_motion,
        control_dt=args.dt,
        state_weights=[1.0, 1.0, 1.0, 120.0, 120.0, 120.0],
        control_weights=[1800.0, 1800.0, 1800.0],
        mpc_horizon=args.mpc_horizon,
        mpc_max_iterations=args.mpc_max_iterations,
    )
    safety = ProjectionSafetyFilter(
        checker=CollisionChecker(KeepoutZoneModel(safety_margin=2.0, caution_margin=8.0)),
        max_acceleration=args.max_acceleration,
        max_speed=0.35,
        repulsion_gain=0.004,
        braking_time=4.0,
    )
    first = reference[0]
    state = (
        first['rx'],
        first['ry'],
        first['rz'],
        first['vx'],
        first['vy'],
        first['vz'],
    )
    final_time = reference[-1]['time']
    steps = int(final_time / args.dt) + 1
    trajectory_rows: list[dict[str, object]] = []
    control_rows: list[dict[str, object]] = []
    safety_rows: list[dict[str, object]] = []
    cumulative_delta_v = 0.0

    for step in range(steps + 1):
        time_value = min(step * args.dt, final_time)
        ref = _interpolate_reference(reference, time_value)
        nominal = controller.compute_control(
            state,
            (ref['rx'], ref['ry'], ref['rz']),
            (ref['vx'], ref['vy'], ref['vz']),
            (ref.get('ax', 0.0), ref.get('ay', 0.0), ref.get('az', 0.0)),
        )
        safe_result = safety.filter_command(state[:3], state[3:6], nominal)
        safe = safe_result.command
        pos_error = _norm(_subtract(state[:3], (ref['rx'], ref['ry'], ref['rz'])))
        vel_error = _norm(_subtract(state[3:6], (ref['vx'], ref['vy'], ref['vz'])))
        trajectory_rows.append({
            'time': time_value,
            'rx': state[0],
            'ry': state[1],
            'rz': state[2],
            'vx': state[3],
            'vy': state[4],
            'vz': state[5],
            'qx': 0.0,
            'qy': 0.0,
            'qz': 0.0,
            'qw': 1.0,
            'tracking_error_norm': pos_error,
            'planned_rx': ref['rx'],
            'planned_ry': ref['ry'],
            'planned_rz': ref['rz'],
            'planned_vx': ref['vx'],
            'planned_vy': ref['vy'],
            'planned_vz': ref['vz'],
            'planned_ax': ref.get('ax', 0.0),
            'planned_ay': ref.get('ay', 0.0),
            'planned_az': ref.get('az', 0.0),
            'position_tracking_error_norm': pos_error,
            'velocity_tracking_error_norm': vel_error,
            'state_tracking_error_norm': (pos_error * pos_error + vel_error * vel_error) ** 0.5,
            'boresight_x': 0.0,
            'boresight_y': 0.0,
            'boresight_z': 0.0,
        })
        acceleration_norm = _norm(safe)
        cumulative_delta_v += acceleration_norm * args.dt
        control_rows.append({
            'time': time_value,
            'ax_nom': nominal[0],
            'ay_nom': nominal[1],
            'az_nom': nominal[2],
            'ax_safe': safe[0],
            'ay_safe': safe[1],
            'az_safe': safe[2],
            'control_norm': _norm(nominal),
            'acceleration_norm': acceleration_norm,
            'delta_v_increment': acceleration_norm * args.dt,
            'cumulative_delta_v': cumulative_delta_v,
            'is_saturated': acceleration_norm >= args.max_acceleration - 1.0e-9,
        })
        safety_rows.append({
            'time': time_value,
            'minimum_distance': safe_result.minimum_distance,
            'safety_margin': safe_result.safety_margin,
            'clearance': safe_result.clearance,
            'is_safe': safe_result.clearance >= 0.0,
            'in_caution_zone': safe_result.in_caution_zone,
            'nearest_primitive': safe_result.nearest_primitive,
            'filter_active': safe_result.modified,
            'filter_reason': safe_result.reason,
            'ax_nom': nominal[0],
            'ay_nom': nominal[1],
            'az_nom': nominal[2],
            'ax_safe': safe[0],
            'ay_safe': safe[1],
            'az_safe': safe[2],
        })
        if time_value >= final_time:
            break
        state = dynamics.rk4_step(state, safe, min(args.dt, final_time - time_value))

    pos_errors = [float(row['position_tracking_error_norm']) for row in trajectory_rows]
    vel_errors = [float(row['velocity_tracking_error_norm']) for row in trajectory_rows]
    summary = {
        'mission_duration': final_time,
        'mean_position_tracking_error': sum(pos_errors) / len(pos_errors),
        'max_position_tracking_error': max(pos_errors),
        'mean_velocity_tracking_error': sum(vel_errors) / len(vel_errors),
        'max_velocity_tracking_error': max(vel_errors),
        'cumulative_delta_v': cumulative_delta_v,
        'min_clearance': min(float(row['clearance']) for row in safety_rows),
    }
    return trajectory_rows, control_rows, safety_rows, summary


def _interpolate_reference(reference: list[dict[str, float]], time_value: float) -> dict[str, float]:
    if time_value <= reference[0]['time']:
        return dict(reference[0])
    for index, current in enumerate(reference[1:], start=1):
        if current['time'] >= time_value:
            previous = reference[index - 1]
            ratio = (time_value - previous['time']) / max(current['time'] - previous['time'], 1.0e-9)
            return {
                key: previous[key] + ratio * (current[key] - previous[key])
                for key in ('time', 'rx', 'ry', 'rz', 'vx', 'vy', 'vz', 'ax', 'ay', 'az')
                if key in previous and key in current
            }
    return dict(reference[-1])


def _make_result_dir(output_root: Path, run_id: str) -> Path:
    name = run_id or f"full_mpc_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    result_dir = output_root / name
    counter = 1
    while result_dir.exists():
        result_dir = output_root / f'{name}_{counter:02d}'
        counter += 1
    result_dir.mkdir(parents=True)
    return result_dir


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_empty_csv(path: Path, columns: tuple[str, ...]) -> None:
    _write_csv(path, columns, [])


def _summary_markdown(summary: dict[str, object]) -> str:
    return (
        '# Full Closed-Loop MPC Validation\n\n'
        f"- Mission duration: {float(summary['mission_duration']):.3f} s\n"
        f"- Mean position tracking error: {float(summary['mean_position_tracking_error']):.6f} m\n"
        f"- Max position tracking error: {float(summary['max_position_tracking_error']):.6f} m\n"
        f"- Mean velocity tracking error: {float(summary['mean_velocity_tracking_error']):.6f} m/s\n"
        f"- Cumulative delta-v: {float(summary['cumulative_delta_v']):.6f} m/s\n"
        f"- Minimum clearance: {float(summary['min_clearance']):.6f} m\n"
    )


def _subtract(left, right) -> tuple[float, float, float]:
    return tuple(float(a) - float(b) for a, b in zip(left, right))


def _norm(values) -> float:
    return sum(float(value) * float(value) for value in values) ** 0.5


if __name__ == '__main__':
    main()
