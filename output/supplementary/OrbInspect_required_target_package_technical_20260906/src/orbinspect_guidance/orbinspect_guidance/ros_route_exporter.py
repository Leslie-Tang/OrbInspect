"""Export frozen held-out routes into deterministic ROS replay CSV files."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

from orbinspect_guidance.advanced_safe_planner import AdvancedSafePlanner
from orbinspect_guidance.offline_adp_superiority_study import _method_config
from orbinspect_guidance.offline_adp_superiority_study import _problem_for_scenario
from orbinspect_guidance.offline_adp_superiority_study import load_archived_graph
from orbinspect_guidance.offline_adp_superiority_study import MissionScenario
from orbinspect_guidance.offline_adp_superiority_study import SuperiorityConfig
from orbinspect_guidance.offline_planning_experiment import _load_yaml_config
from orbinspect_guidance.offline_planning_experiment import ExperimentConfig
from orbinspect_guidance.offline_planning_experiment import OfflinePlanningExperiment
from orbinspect_guidance.observation_credit import ObservationMission
from orbinspect_guidance.observation_credit import coverage_metrics


METHODS = ('adaptive_rollout_adp', 'local_search')
MESH_SHA256 = '26dba905b4b7555edbcb0c5f5a61b5c18659f5166076ab27dbb0e64025759fca'
METRIC_TOLERANCE = 1.0e-9


def export_routes(
    source_dir: Path,
    output_root: Path,
    config_path: Path,
    *,
    scenario_ids: tuple[str, ...] = (),
    splits: tuple[str, ...] = ('validation', 'test', 'ood'),
    methods: tuple[str, ...] = METHODS,
    run_id: str = '',
) -> Path:
    """Reconstruct selected frozen routes and emit one normalized replay bundle."""
    source_dir = source_dir.resolve()
    raw_source = source_dir / 'raw'
    required = (
        raw_source / 'hcw_graph.json',
        raw_source / 'scenarios.json',
        raw_source / 'heldout_results.csv',
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f'missing frozen source files: {missing}')

    graph = load_archived_graph(required[0])
    scenarios = _load_scenarios(required[1])
    scenario_metadata = {
        item['scenario_id']: item for item in json.loads(required[1].read_text())
    }
    if len(scenario_metadata) != len(scenarios):
        raise ValueError('scenario identifiers must be unique')
    archived_rows = _read_archived_rows(required[2])
    selected = tuple(
        scenario for scenario in scenarios
        if (not scenario_ids and scenario.split in splits)
        or scenario.scenario_id in scenario_ids
    )
    if scenario_ids:
        found = {scenario.scenario_id for scenario in selected}
        absent = sorted(set(scenario_ids) - found)
        if absent:
            raise ValueError(f'unknown scenario_id values: {absent}')
    if not selected:
        raise ValueError('scenario selection is empty')
    unsupported = sorted(set(methods) - set(METHODS))
    if unsupported:
        raise ValueError(f'unsupported methods: {unsupported}')

    values = _load_yaml_config(config_path)
    base_snapshot = source_dir / 'config_snapshot/base_experiment_config.json'
    if base_snapshot.is_file():
        values = json.loads(base_snapshot.read_text())
    values.update({
        'output_root': output_root,
        'methods': (),
        'adp_candidate_limit': 24,
        'coverage_stop_ratio': 0.80,
        'max_viewpoints': 14,
    })
    experiment = OfflinePlanningExperiment(ExperimentConfig(**values))
    _assert_mesh_hash(experiment.base_planner.config.iss_mesh_path)
    candidate_by_id = {
        candidate.candidate_id: candidate for candidate in experiment.candidates
    }
    target_by_id = {target.target_id: target for target in experiment.targets}
    graph_node_index = {
        node_id: index for index, node_id in enumerate(graph.node_ids)
    }
    superiority = SuperiorityConfig(
        candidate_limit=24,
        goal_coverage=0.80,
        max_steps=14,
        branch_width=8,
        candidate_pool_width=18,
        lookahead_depth=2,
        training_scenarios=24,
        validation_scenarios=12,
        test_scenarios=30,
        ood_scenarios=20,
        critic_backend='ridge',
        training_target='rollout',
        scenario_node_count=0,
        adaptive_rollout_depth=3,
    )
    dummy_checkpoint = AdvancedSafePlanner().critic_weights
    summary_path = source_dir / 'summary.json'
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text())
        if 'superiority_config' in summary:
            superiority = SuperiorityConfig(**summary['superiority_config'])

    run_name = run_id or f'ros_verification_inputs_{datetime.now():%Y%m%d_%H%M%S}'
    result_dir = output_root.resolve() / run_name
    if result_dir.exists():
        raise FileExistsError(result_dir)
    raw_dir = result_dir / 'raw'
    config_dir = result_dir / 'config_snapshot'
    for directory in (
        raw_dir,
        config_dir,
        result_dir / 'rosbag',
        result_dir / 'figures',
        result_dir / 'videos',
    ):
        directory.mkdir(parents=True, exist_ok=False)

    trajectory_rows: list[dict[str, object]] = []
    attitude_rows: list[dict[str, object]] = []
    viewpoint_rows: list[dict[str, object]] = []
    safety_rows: list[dict[str, object]] = []
    planner_rows: list[dict[str, object]] = []
    event_rows: list[dict[str, object]] = []
    route_manifest: list[dict[str, object]] = []
    for scenario in selected:
        problem = _problem_for_scenario(graph, scenario)
        mission = _mission_for_scenario(graph, scenario_metadata[scenario.scenario_id])
        if mission.goal_mode != 'coverage' or mission.required_target_ids:
            required_mask = sum(
                1 << index for index, target_id in enumerate(graph.target_ids)
                if target_id in mission.required_target_ids
            )
            problem = replace(
                problem, goal_mode=mission.goal_mode,
                required_target_mask=required_mask,
            )
        for method in methods:
            key = (scenario.scenario_id, method)
            if key not in archived_rows and scenario.split != 'validation':
                raise ValueError(f'frozen row missing for {key}')
            archived = archived_rows.get(key)
            if archived is not None and 'route_node_ids' in archived:
                plan = _audit_archived_route(
                    problem, mission, archived,
                    action_cost=superiority.action_cost,
                    target_ids=graph.target_ids,
                )
            else:
                planner_config, checkpoint = _method_config(
                    method, superiority, dummy_checkpoint,
                )
                plan = AdvancedSafePlanner(
                    planner_config, critic_weights=checkpoint,
                ).plan(problem)
            metrics_archived = archived is not None
            if archived is None:
                archived = _plan_metrics(plan, problem)
            else:
                _assert_plan_metrics(plan, problem, archived)

            current_state = experiment.config.initial_state
            time_offset = 0.0
            cumulative_delta_v = 0.0
            cumulative_cost = 0.0
            covered_mask = 0
            route_nodes = []
            route_min_clearance = math.inf
            route_peak_input = 0.0
            for action_index, node_id in enumerate(plan.node_ids, start=1):
                candidate = candidate_by_id[node_id]
                transfer = experiment._estimate_transfer_from_state(
                    current_state,
                    candidate,
                )
                cumulative_delta_v += transfer.delta_v
                cumulative_cost += experiment._dynamic_transfer_cost(transfer) + superiority.action_cost
                route_min_clearance = min(route_min_clearance, transfer.min_clearance)
                route_peak_input = max(route_peak_input, transfer.peak_requested_input)
                covered_mask |= graph.coverage_masks[graph_node_index[node_id]]
                coverage = _mask_weight(
                    covered_mask,
                    scenario.target_weights,
                ) / sum(scenario.target_weights)
                accepted_target_ids = frozenset(
                    target_id for index, target_id in enumerate(graph.target_ids)
                    if covered_mask & (1 << index)
                )
                planned_metrics = coverage_metrics(accepted_target_ids, mission)
                endpoint = {
                    'scenario_id': scenario.scenario_id, 'method': method,
                    'action': action_index, 'candidate_id': node_id,
                    'time': time_offset + experiment.config.transfer_duration,
                    'record_basis': 'planned_graph_and_transfer_not_execution',
                }
                safety_rows.append({
                    **endpoint, 'feasible': transfer.feasible,
                    'min_clearance': transfer.min_clearance,
                    'peak_input': transfer.peak_requested_input,
                    'max_speed': transfer.max_speed,
                    'terminal_error': transfer.terminal_error,
                })
                planner_rows.append({
                    **endpoint, 'stage_cost': experiment._dynamic_transfer_cost(transfer) + superiority.action_cost,
                    'cumulative_cost': cumulative_cost,
                    'cumulative_delta_v': cumulative_delta_v,
                    'coverage_ratio': coverage,
                    'required_coverage_ratio': planned_metrics['required_coverage_ratio'],
                    'required_covered_count': planned_metrics['required_covered_count'],
                    'missing_required_target_ids': ';'.join(planned_metrics['missing_required_target_ids']),
                })
                aim = target_by_id[candidate.source_target_id].position
                for sample_index, (local_time, state, control) in enumerate(
                    transfer.trajectory
                ):
                    time_value = time_offset + local_time
                    boresight = _unit(tuple(
                        aim[index] - state[index] for index in range(3)
                    ))
                    common = {
                        'scenario_id': scenario.scenario_id,
                        'split': scenario.split,
                        'scenario_seed': scenario.seed,
                        'method': method,
                        'action': action_index,
                        'candidate_id': node_id,
                        'sample': sample_index,
                        'time': time_value,
                    }
                    trajectory_rows.append({
                        **common,
                        'rx': state[0],
                        'ry': state[1],
                        'rz': state[2],
                        'vx': state[3],
                        'vy': state[4],
                        'vz': state[5],
                        'ax': control[0],
                        'ay': control[1],
                        'az': control[2],
                    })
                    attitude_rows.append({
                        **common,
                        'boresight_x': boresight[0],
                        'boresight_y': boresight[1],
                        'boresight_z': boresight[2],
                    })
                terminal_boresight = _unit(tuple(
                    aim[index] - transfer.next_state[index] for index in range(3)
                ))
                viewpoint_rows.append({
                    'scenario_id': scenario.scenario_id,
                    'split': scenario.split,
                    'scenario_seed': scenario.seed,
                    'method': method,
                    'action': action_index,
                    'candidate_id': node_id,
                    'time': time_offset + experiment.config.transfer_duration,
                    'viewpoint_x': candidate.position[0],
                    'viewpoint_y': candidate.position[1],
                    'viewpoint_z': candidate.position[2],
                    'boresight_x': terminal_boresight[0],
                    'boresight_y': terminal_boresight[1],
                    'boresight_z': terminal_boresight[2],
                    'weighted_coverage': coverage,
                    'covered_target_count': covered_mask.bit_count(),
                    'total_target_count': len(graph.target_ids),
                    'goal_mode': mission.goal_mode,
                    'required_target_count': len(mission.required_target_ids),
                    'required_covered_count': planned_metrics['required_covered_count'],
                    'required_coverage': planned_metrics['required_coverage_ratio'],
                    'covered_target_ids': ';'.join(sorted(accepted_target_ids)),
                    'required_target_ids': ';'.join(sorted(mission.required_target_ids)),
                    'visible_target_ids': ';'.join(
                        sorted(experiment.visibility.visible_targets_by_candidate[node_id])
                    ),
                })
                route_nodes.append(node_id)
                time_offset += experiment.config.transfer_duration
                current_state = transfer.next_state

            _assert_close('materialized delta_v', cumulative_delta_v, archived['total_delta_v'])
            _assert_close('materialized graph_cost', cumulative_cost, archived['graph_cost'])
            _assert_close(
                'materialized min_clearance', route_min_clearance, archived['min_clearance']
            )
            _assert_close('materialized peak_input', route_peak_input, archived['peak_input'])
            route_manifest.append({
                'scenario_id': scenario.scenario_id,
                'split': scenario.split,
                'scenario_seed': scenario.seed,
                'method': method,
                'metrics_archived': metrics_archived,
                'route_node_ids': route_nodes,
                'success': bool(plan.success),
                'planned_coverage': float(plan.coverage_ratio),
                'planned_graph_cost': float(plan.total_cost),
                'planned_delta_v': cumulative_delta_v,
                'planned_min_clearance': route_min_clearance,
                'planned_peak_input': route_peak_input,
                'action_count': len(route_nodes),
                'duration_s': time_offset,
                'initial_state': list(experiment.config.initial_state),
                'mission': mission.metadata(),
            })
            event_rows.append({
                'scenario_id': scenario.scenario_id, 'method': method,
                'time': time_offset,
                'event': 'planned_mission_complete' if plan.success else 'planned_mission_incomplete',
                'state': 'planned', 'execution_performed': False,
                'planned_success': bool(plan.success),
                'coverage_ratio': plan.coverage_ratio,
                'required_coverage_ratio': planned_metrics['required_coverage_ratio'],
                'mission_sha256': mission.mission_sha256,
            })

    output_files = {
        'trajectory.csv': trajectory_rows,
        'attitude.csv': attitude_rows,
        'viewpoints.csv': viewpoint_rows,
        'control.csv': [{
            key: row[key] for key in (
                'scenario_id', 'method', 'action', 'candidate_id', 'sample', 'time', 'ax', 'ay', 'az',
            )
        } | {'record_basis': 'planned_command_not_execution'} for row in trajectory_rows],
        'coverage.csv': [{
            'scenario_id': row['scenario_id'], 'method': row['method'],
            'time': row['time'], 'candidate_id': row['candidate_id'],
            'coverage_ratio': row['weighted_coverage'],
            'inspected_targets': row['covered_target_count'],
            'total_targets': row['total_target_count'],
            'required_covered_count': row['required_covered_count'],
            'required_target_count': row['required_target_count'],
            'required_coverage_ratio': row['required_coverage'],
            'covered_target_ids': row['covered_target_ids'],
            'record_basis': 'planned_visibility_not_execution_credit',
        } for row in viewpoint_rows],
        'safety.csv': safety_rows,
        'planner.csv': planner_rows,
        'mission_events.csv': event_rows,
    }
    for name, rows in output_files.items():
        _write_rows(raw_dir / name, rows)
    shutil.copy2(config_path, config_dir / config_path.name)
    if base_snapshot.is_file():
        shutil.copy2(base_snapshot, config_dir / 'base_experiment_config.json')
    manifest = {
        'schema_version': 'orbinspect-ros-verification-input/v3',
        'source_result_root': str(source_dir),
        'source_files_sha256': {
            path.name: _sha256(path) for path in required
        },
        'base_experiment_snapshot_sha256': (
            _sha256(base_snapshot) if base_snapshot.is_file() else None
        ),
        'exporter_sha256': _sha256(Path(__file__)),
        'mesh_sha256': MESH_SHA256,
        'git_revision': _git_revision(),
        'methods': list(methods),
        'splits': list(splits),
        'scenario_count': len(selected),
        'route_count': len(route_manifest),
        'mean_motion': experiment.base_planner.config.mean_motion,
        'safety_margin': experiment.config.safety_margin,
        'vehicle_bounding_radius': experiment.config.vehicle_radius,
        'mesh_transform': 'full_gltf_scene_hierarchy_then_sdf_pitch_90_scale',
        'max_acceleration': experiment.config.max_acceleration,
        'integration_dt': experiment.config.integration_dt,
        'transfer_duration': experiment.config.transfer_duration,
        'routes': route_manifest,
    }
    manifest['output_files_sha256'] = {
        name: _sha256(raw_dir / name) for name in output_files
    }
    (result_dir / 'manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )
    _write_export_summary(result_dir, manifest)
    return result_dir


def _write_export_summary(result_dir: Path, manifest: dict[str, object]) -> None:
    """Record replay-input generation separately from unperformed ROS execution."""
    summary = {
        'result_kind': 'frozen_ros_replay_inputs',
        'execution_performed': False,
        'route_count': manifest['route_count'],
        'scenario_count': manifest['scenario_count'],
        'source_result_root': manifest['source_result_root'],
        'manifest_sha256': _sha256(result_dir / 'manifest.json'),
        'routes': manifest['routes'],
    }
    (result_dir / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    lines = [
        '# Frozen ROS replay inputs', '',
        'These files contain reconstructed and audited planned routes. '
        'No new ROS execution, closed-loop verification, images, or rosbag is claimed.', '',
        '| Scenario | Method | Goal | Required targets | Actions | Planned background coverage |',
        '|---|---|---|---:|---:|---:|',
    ]
    for route in manifest['routes']:
        mission = route['mission']
        lines.append(
            f"| {route['scenario_id']} | {route['method']} | {mission['goal_mode']} | "
            f"{len(mission['required_target_ids'])} | {route['action_count']} | "
            f"{100.0 * route['planned_coverage']:.3f}% |"
        )
    lines += ['', 'Run the documented Jazzy verification launch to generate execution evidence.']
    (result_dir / 'summary.md').write_text('\n'.join(lines) + '\n')


def _mission_for_scenario(graph, payload: dict[str, object]) -> ObservationMission:
    """Bind explicit scenario requirements to unchanged graph target identities."""
    target_ids = tuple(graph.target_ids)
    weights = tuple(payload['target_weights'])
    if len(target_ids) != len(weights):
        raise ValueError('target IDs and weights have different lengths')
    required_ids = frozenset(payload.get('required_target_ids', ()))
    if 'required_target_mask' in payload:
        raw_mask = payload['required_target_mask']
        mask = int(raw_mask, 0) if isinstance(raw_mask, str) else int(raw_mask)
        if mask < 0 or mask >> len(target_ids):
            raise ValueError('required target mask is outside the graph universe')
        mask_ids = frozenset(
            target_id for index, target_id in enumerate(target_ids)
            if mask & (1 << index)
        )
        if 'required_target_ids' in payload and mask_ids != required_ids:
            raise ValueError('required target mask and IDs disagree')
        required_ids = mask_ids
    identity = {
        'goal_mode': str(payload.get('goal_mode', 'coverage')),
        'goal_coverage': float(payload['goal_coverage']),
        'required_target_ids': sorted(required_ids),
        'target_weights': dict(zip(target_ids, weights)),
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return ObservationMission(
        **identity, mission_sha256=digest,
    )


def _audit_archived_route(
    problem, mission: ObservationMission, archived: dict[str, object], *, action_cost: float,
    target_ids: tuple[str, ...],
):
    """Validate the frozen route itself without silently replanning a new route."""
    node_ids = tuple(item for item in str(archived['route_node_ids']).split(';') if item)
    if not node_ids:
        raise ValueError('cannot export an empty route for closed-loop replay')
    if len(set(node_ids)) != len(node_ids) or len(node_ids) > problem.max_steps:
        raise ValueError('archived route violates the no-revisit rule or action budget')
    nodes = {node.node_id: node for node in problem.nodes}
    source_id = None
    covered_mask = 0
    total_cost = 0.0
    for node_id in node_ids:
        if node_id not in nodes:
            raise ValueError('archived route includes an unavailable node')
        edge = problem.edge_evaluator(source_id, node_id)
        if not (
            edge.feasible and edge.min_clearance >= 0.0
            and edge.peak_input <= edge.input_limit + 1.0e-12
            and (edge.passive_margin is None or edge.passive_margin >= 0.0)
        ):
            raise ValueError('archived route contains a shield-rejected edge')
        covered_mask |= nodes[node_id].coverage_mask
        total_cost += edge.stage_cost + action_cost
        source_id = node_id
    if len(target_ids) != len(problem.target_weights) or set(target_ids) != set(mission.target_weights):
        raise ValueError('graph target index and mission universe disagree')
    covered_ids = frozenset(
        target_id for index, target_id in enumerate(target_ids)
        if covered_mask & (1 << index)
    )
    metrics = coverage_metrics(covered_ids, mission)
    if 'covered_target_mask' in archived:
        raw_mask = archived['covered_target_mask']
        expected_mask = int(raw_mask, 0) if isinstance(raw_mask, str) else int(raw_mask)
        if covered_mask != expected_mask:
            raise ValueError('reconstructed credited mask differs from archived route')
    if 'required_coverage' in archived and mission.required_target_ids:
        _assert_close(
            'required coverage', metrics['required_coverage_ratio'], archived['required_coverage'],
        )
    plan = SimpleNamespace(
        node_ids=node_ids, total_cost=total_cost,
        coverage_ratio=metrics['coverage_ratio'], success=metrics['mission_goal_reached'],
    )
    _assert_plan_metrics(plan, problem, archived)
    return plan


def _load_scenarios(path: Path) -> tuple[MissionScenario, ...]:
    payload = json.loads(path.read_text())
    return tuple(MissionScenario(
        scenario_id=item['scenario_id'],
        split=item['split'],
        seed=int(item['seed']),
        available_node_ids=tuple(item['available_node_ids']),
        target_weights=tuple(float(value) for value in item['target_weights']),
        reference_node_ids=tuple(item['reference_node_ids']),
        goal_coverage=float(item['goal_coverage']),
        max_steps=int(item['max_steps']),
    ) for item in payload)


def _read_archived_rows(path: Path) -> dict[tuple[str, str], dict[str, object]]:
    with path.open(newline='') as handle:
        return {
            (row['scenario_id'], row['method']): {
                **row,
                'success': row['success'].lower() == 'true',
                **{
                    name: float(row[name])
                    for name in (
                        'coverage',
                        'graph_cost',
                        'total_delta_v',
                        'min_clearance',
                        'peak_input',
                    )
                },
                'selected_count': int(row['selected_count']),
            }
            for row in csv.DictReader(handle)
        }


def _plan_metrics(plan, problem) -> dict[str, object]:
    edges = []
    source_id = None
    for node_id in plan.node_ids:
        edges.append(problem.edge_evaluator(source_id, node_id))
        source_id = node_id
    return {
        'success': bool(plan.success),
        'selected_count': len(plan.node_ids),
        'coverage': float(plan.coverage_ratio),
        'graph_cost': float(plan.total_cost),
        'total_delta_v': sum(edge.delta_v for edge in edges),
        'min_clearance': min(edge.min_clearance for edge in edges),
        'peak_input': max(edge.peak_input for edge in edges),
    }


def _assert_plan_metrics(plan, problem, archived: dict[str, object]) -> None:
    reconstructed = _plan_metrics(plan, problem)
    if reconstructed['success'] != archived['success']:
        raise RuntimeError('reconstructed success differs from frozen row')
    if reconstructed['selected_count'] != archived['selected_count']:
        raise RuntimeError('reconstructed action count differs from frozen row')
    _assert_close('coverage', reconstructed['coverage'], archived['coverage'])
    _assert_close('graph_cost', reconstructed['graph_cost'], archived['graph_cost'])
    _assert_close(
        'delta_v',
        reconstructed['total_delta_v'],
        archived['total_delta_v'],
    )
    _assert_close(
        'min_clearance',
        reconstructed['min_clearance'],
        archived['min_clearance'],
    )
    _assert_close(
        'peak_input',
        reconstructed['peak_input'],
        archived['peak_input'],
    )


def _assert_close(label: str, actual: float, expected: object) -> None:
    if not math.isclose(
        float(actual),
        float(expected),
        rel_tol=METRIC_TOLERANCE,
        abs_tol=METRIC_TOLERANCE,
    ):
        raise RuntimeError(f'{label} mismatch: {actual} != {expected}')


def _assert_mesh_hash(configured_path: Path) -> None:
    mesh_path = configured_path
    if not mesh_path.is_absolute() and not mesh_path.is_file():
        mesh_path = Path(__file__).resolve().parents[3] / mesh_path
    actual = _sha256(mesh_path)
    if actual.lower() != MESH_SHA256:
        raise RuntimeError(f'ISS mesh hash mismatch: {actual}')


def _mask_weight(mask: int, weights: tuple[float, ...]) -> float:
    return sum(
        weight for index, weight in enumerate(weights)
        if mask & (1 << index)
    )


def _unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 1.0e-12:
        return (1.0, 0.0, 0.0)
    return tuple(value / norm for value in vector)


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f'cannot write empty CSV: {path}')
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _git_revision() -> str:
    try:
        return subprocess.check_output(
            ('git', 'rev-parse', 'HEAD'),
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return 'unknown'


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse frozen-route exporter arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--source-dir',
        type=Path,
        default=Path('data/results/adp_future_physical_heldout_20260810'),
    )
    parser.add_argument('--output-root', type=Path, default=Path('data/results'))
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('src/orbinspect_guidance/config/adp_future_study.yaml'),
    )
    parser.add_argument('--scenario-id', action='append', default=[])
    parser.add_argument('--splits', default='validation,test,ood')
    parser.add_argument('--methods', default=','.join(METHODS))
    parser.add_argument('--run-id', default='')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Export selected frozen routes for ROS replay."""
    args = parse_args(argv)
    result_dir = export_routes(
        args.source_dir,
        args.output_root,
        args.config,
        scenario_ids=tuple(args.scenario_id),
        splits=tuple(item for item in args.splits.split(',') if item),
        methods=tuple(item for item in args.methods.split(',') if item),
        run_id=args.run_id,
    )
    print(result_dir)


if __name__ == '__main__':
    main()
