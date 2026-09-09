#!/usr/bin/env python3
"""Stress-test high coverage goals with mandatory spatial sentinel targets."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, replace
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from orbinspect_guidance.advanced_safe_planner import AdvancedSafePlanner
from orbinspect_guidance.offline_adp_superiority_study import _method_config
from orbinspect_guidance.offline_adp_superiority_study import _problem_for_scenario
from orbinspect_guidance.offline_adp_superiority_study import load_archived_graph
from orbinspect_guidance.offline_adp_superiority_study import MissionScenario
from orbinspect_guidance.offline_adp_superiority_study import SuperiorityConfig
from orbinspect_guidance.offline_coverage_planner import OfflineCoveragePlanner
from orbinspect_guidance.offline_planning_experiment import ExperimentConfig
from orbinspect_guidance.offline_planning_experiment import (
    _planner_config as experiment_planner_config,
)


DEFAULT_STUDY_ROOT = Path(
    'data/results/adp_future_full_transform_radius080_20260812'
)
AXIS_EXTREMES = (
    ('min_x', 0, min),
    ('max_x', 0, max),
    ('min_y', 1, min),
    ('max_y', 1, max),
    ('min_z', 2, min),
    ('max_z', 2, max),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _load_scenarios(path: Path) -> tuple[MissionScenario, ...]:
    payload = json.loads(path.read_text())
    return tuple(
        MissionScenario(
            scenario_id=item['scenario_id'],
            split=item['split'],
            seed=int(item['seed']),
            available_node_ids=tuple(item['available_node_ids']),
            target_weights=tuple(float(value) for value in item['target_weights']),
            reference_node_ids=tuple(item['reference_node_ids']),
            goal_coverage=float(item['goal_coverage']),
            max_steps=int(item['max_steps']),
        )
        for item in payload
    )


def _load_target_positions(
    summary: dict[str, object],
) -> dict[str, tuple[float, float, float]]:
    values = dict(summary['base_experiment_config'])
    values['output_root'] = Path(str(values['output_root']))
    values['methods'] = tuple(values['methods'])
    values['initial_state'] = tuple(float(value) for value in values['initial_state'])
    config = ExperimentConfig(**values)
    planner = OfflineCoveragePlanner(experiment_planner_config(config))
    return {
        target.target_id: tuple(float(value) for value in target.position)
        for target in planner.load_targets()
    }


def _available_union(
    scenario: MissionScenario,
    node_masks: dict[str, int],
) -> int:
    mask = 0
    for node_id in scenario.available_node_ids:
        mask |= node_masks[node_id]
    return mask


def _weighted_coverage(mask: int, weights: tuple[float, ...]) -> float:
    total = max(sum(weights), 1.0e-12)
    return sum(
        weight
        for index, weight in enumerate(weights)
        if mask & (1 << index)
    ) / total


def _select_sentinels(
    graph,
    scenarios: tuple[MissionScenario, ...],
    positions: dict[str, tuple[float, float, float]],
    selection_splits: frozenset[str],
) -> tuple[dict[str, object], ...]:
    node_masks = dict(zip(graph.node_ids, graph.coverage_masks))
    robust_mask = (1 << len(graph.target_ids)) - 1
    selection = tuple(
        scenario for scenario in scenarios
        if scenario.split in selection_splits
    )
    if not selection:
        raise ValueError('sentinel selection requires at least one scenario')
    for scenario in selection:
        robust_mask &= _available_union(scenario, node_masks)
    robust_ids = tuple(
        target_id
        for index, target_id in enumerate(graph.target_ids)
        if robust_mask & (1 << index)
    )
    if not robust_ids:
        raise RuntimeError('no target remains observable in every selection scenario')

    selected = []
    selected_ids: set[str] = set()
    for label, axis, selector in AXIS_EXTREMES:
        target_id = selector(
            robust_ids,
            key=lambda item: positions[item][axis],
        )
        if target_id in selected_ids:
            raise RuntimeError(
                'axis-extreme selection produced duplicate sentinels; '
                'use an explicit spatial-spread fallback'
            )
        selected_ids.add(target_id)
        visible_node_count = sum(
            bool(mask & (1 << graph.target_ids.index(target_id)))
            for mask in graph.coverage_masks
        )
        selected.append({
            'criterion': label,
            'target_id': target_id,
            'position_x': positions[target_id][0],
            'position_y': positions[target_id][1],
            'position_z': positions[target_id][2],
            'visible_node_count': visible_node_count,
            'observable_in_selection_scenarios': len(selection),
        })
    return tuple(selected)


def _covered_mask(problem, node_ids: tuple[str, ...]) -> int:
    masks = {node.node_id: node.coverage_mask for node in problem.nodes}
    mask = 0
    for node_id in node_ids:
        mask |= masks[node_id]
    return mask


def _evaluate_case(
    graph,
    scenario: MissionScenario,
    study_config: SuperiorityConfig,
    goal: float,
    enforced_target_mask: int,
    sentinel_target_mask: int,
    requirement: str,
    mesh_target_count: int,
) -> dict[str, object]:
    node_masks = dict(zip(graph.node_ids, graph.coverage_masks))
    available_union = _available_union(scenario, node_masks)
    upper_bound = _weighted_coverage(available_union, scenario.target_weights)
    required_available = (
        available_union & enforced_target_mask
    ) == enforced_target_mask
    sentinels_available = (
        available_union & sentinel_target_mask
    ) == sentinel_target_mask
    structurally_feasible = (
        upper_bound + 1.0e-12 >= goal and required_available
    )
    base = {
        'goal_coverage': goal,
        'requirement': requirement,
        'scenario_id': scenario.scenario_id,
        'scenario_seed': scenario.seed,
        'available_node_count': len(scenario.available_node_ids),
        'static_upper_bound': upper_bound,
        'static_visible_target_count': available_union.bit_count(),
        'required_target_count': enforced_target_mask.bit_count(),
        'required_targets_available': required_available,
        'sentinel_target_count': sentinel_target_mask.bit_count(),
        'sentinels_available': sentinels_available,
        'structurally_feasible': structurally_feasible,
    }
    if not structurally_feasible:
        return {
            **base,
            'status': 'structurally_infeasible',
            'success': False,
            'coverage': math.nan,
            'unweighted_inspectable_coverage': math.nan,
            'whole_surface_coverage': math.nan,
            'required_targets_covered': False,
            'required_targets_covered_count': 0,
            'sentinels_covered': False,
            'sentinels_covered_count': 0,
            'selected_count': 0,
            'graph_cost': math.nan,
            'total_delta_v': math.nan,
            'min_clearance': math.nan,
            'peak_input': math.nan,
            'online_time_s': 0.0,
            'safe_action_evaluations': 0,
            'shield_rejections': 0,
            'route_node_ids': '',
        }

    elevated_scenario = replace(
        scenario,
        goal_coverage=goal,
        max_steps=study_config.max_steps,
    )
    problem = replace(
        _problem_for_scenario(graph, elevated_scenario),
        required_target_mask=enforced_target_mask,
    )
    planner_config, _checkpoint = _method_config(
        'adaptive_rollout_adp',
        study_config,
        (),
    )
    start = perf_counter()
    plan = AdvancedSafePlanner(planner_config).plan(problem)
    elapsed = perf_counter() - start
    covered = _covered_mask(problem, plan.node_ids)
    required_covered_count = (
        covered & enforced_target_mask
    ).bit_count()
    required_covered = (
        covered & enforced_target_mask
    ) == enforced_target_mask
    sentinels_covered_count = (
        covered & sentinel_target_mask
    ).bit_count()
    sentinels_covered = (
        covered & sentinel_target_mask
    ) == sentinel_target_mask
    route_edges = []
    source_id = None
    for node_id in plan.node_ids:
        route_edges.append(problem.edge_evaluator(source_id, node_id))
        source_id = node_id
    return {
        **base,
        'status': 'success' if plan.success else 'no_viable_completion',
        'success': plan.success,
        'coverage': plan.coverage_ratio,
        'unweighted_inspectable_coverage': (
            covered.bit_count() / len(graph.target_ids)
        ),
        'whole_surface_coverage': covered.bit_count() / mesh_target_count,
        'required_targets_covered': required_covered,
        'required_targets_covered_count': required_covered_count,
        'sentinels_covered': sentinels_covered,
        'sentinels_covered_count': sentinels_covered_count,
        'selected_count': len(plan.node_ids),
        'graph_cost': plan.total_cost,
        'total_delta_v': sum(edge.delta_v for edge in route_edges),
        'min_clearance': min(
            (edge.min_clearance for edge in route_edges),
            default=math.nan,
        ),
        'peak_input': max(
            (edge.peak_input for edge in route_edges),
            default=math.nan,
        ),
        'online_time_s': elapsed,
        'safe_action_evaluations': plan.safe_action_evaluations,
        'shield_rejections': plan.shield_rejections,
        'route_node_ids': ';'.join(plan.node_ids),
    }


def _aggregate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    aggregates = []
    keys = sorted({
        (float(row['goal_coverage']), str(row['requirement']))
        for row in rows
    })
    for goal, requirement in keys:
        subset = [
            row for row in rows
            if row['goal_coverage'] == goal
            and row['requirement'] == requirement
        ]
        structural = [row for row in subset if row['structurally_feasible']]
        successful = [row for row in subset if row['success']]
        aggregates.append({
            'goal_coverage': goal,
            'requirement': requirement,
            'scenario_count': len(subset),
            'structurally_feasible_count': len(structural),
            'structurally_feasible_rate': len(structural) / len(subset),
            'success_count': len(successful),
            'success_rate_all': len(successful) / len(subset),
            'success_rate_structurally_feasible': (
                len(successful) / len(structural) if structural else 0.0
            ),
            'mean_successful_coverage': _mean(successful, 'coverage'),
            'mean_successful_unweighted_inspectable_coverage': _mean(
                successful,
                'unweighted_inspectable_coverage',
            ),
            'mean_successful_whole_surface_coverage': _mean(
                successful,
                'whole_surface_coverage',
            ),
            'mean_successful_selected_count': _mean(
                successful,
                'selected_count',
            ),
            'mean_successful_graph_cost': _mean(successful, 'graph_cost'),
            'mean_successful_delta_v': _mean(successful, 'total_delta_v'),
            'median_online_time_s': _median(structural, 'online_time_s'),
            'mean_safe_action_evaluations': _mean(
                structural,
                'safe_action_evaluations',
            ),
            'required_compliance_count': sum(
                bool(row['required_targets_covered']) for row in successful
            ),
            'sentinel_compliance_count': sum(
                bool(row['sentinels_covered']) for row in successful
            ),
            'sentinel_compliance_rate_successful': (
                sum(bool(row['sentinels_covered']) for row in successful)
                / len(successful)
                if successful else 0.0
            ),
            'structural_failure_count': sum(
                row['status'] == 'structurally_infeasible' for row in subset
            ),
            'planner_failure_count': sum(
                row['status'] == 'no_viable_completion' for row in subset
            ),
        })
    return aggregates


def _mean(rows: list[dict[str, object]], key: str) -> float:
    values = [float(row[key]) for row in rows]
    return mean(values) if values else math.nan


def _median(rows: list[dict[str, object]], key: str) -> float:
    values = [float(row[key]) for row in rows]
    return median(values) if values else math.nan


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f'cannot write empty result table: {path}')
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=tuple(rows[0]),
            lineterminator='\n',
        )
        writer.writeheader()
        writer.writerows(rows)


def _summary_markdown(
    aggregates: list[dict[str, object]],
    sentinels: tuple[dict[str, object], ...],
    inspectable_target_count: int,
    mesh_target_count: int,
) -> str:
    lines = [
        '# High-coverage and mandatory-target stress test',
        '',
        'The original frozen scenarios are retained. Structural infeasibility '
        'means the available candidate nodes cannot meet the requested weighted '
        'coverage even before dynamics-aware route search.',
        '',
        f'The stopping goal is weighted over the {inspectable_target_count} '
        f'candidate-observable targets, not all {mesh_target_count} mesh '
        'samples. Whole-surface coverage is reported separately.',
        '',
        '## Selected spatial sentinels',
        '',
        'The six sentinels are robust coordinate extremes that remain observable '
        'in every frozen test and OOD scenario. They are spatial proxies because '
        'the mesh targets do not carry semantic ISS component labels.',
        '',
        '| Criterion | Target | Position (m) | Visible graph nodes |',
        '|---|---|---:|---:|',
    ]
    for item in sentinels:
        lines.append(
            f"| {item['criterion']} | {item['target_id']} | "
            f"({item['position_x']:.3f}, {item['position_y']:.3f}, "
            f"{item['position_z']:.3f}) | {item['visible_node_count']} |"
        )
    lines.extend([
        '',
        '## Results',
        '',
        '| Goal | Requirement | Structural | Success (all) | Success '
        '(structural) | All sentinels | Weighted inspectable | Unweighted '
        'inspectable | Whole mesh | Mean SOOAs | Mean delta-v (m/s) |',
        '|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ])
    for row in aggregates:
        lines.append(
            f"| {100 * row['goal_coverage']:.0f}% | "
            f"{row['requirement']} | "
            f"{row['structurally_feasible_count']}/{row['scenario_count']} | "
            f"{row['success_count']}/{row['scenario_count']} | "
            f"{100 * row['success_rate_structurally_feasible']:.1f}% | "
            f"{row['sentinel_compliance_count']}/{row['success_count']} | "
            f"{100 * row['mean_successful_coverage']:.2f}% | "
            f"{100 * row['mean_successful_unweighted_inspectable_coverage']:.2f}% | "
            f"{100 * row['mean_successful_whole_surface_coverage']:.2f}% | "
            f"{row['mean_successful_selected_count']:.2f} | "
            f"{row['mean_successful_delta_v']:.3f} |"
        )
    return '\n'.join(lines) + '\n'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study-root', type=Path, default=DEFAULT_STUDY_ROOT)
    parser.add_argument('--output-root', type=Path, default=Path('data/results'))
    parser.add_argument('--run-id', default='')
    parser.add_argument('--goals', default='0.95,0.98')
    parser.add_argument('--splits', default='test')
    parser.add_argument('--sentinel-selection-splits', default='test,ood')
    parser.add_argument('--max-steps', type=int, default=14)
    parser.add_argument('--adaptive-rollout-depth', type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    goals = tuple(float(item) for item in args.goals.split(',') if item)
    splits = frozenset(item for item in args.splits.split(',') if item)
    selection_splits = frozenset(
        item for item in args.sentinel_selection_splits.split(',') if item
    )
    if not goals or any(not 0.0 < goal <= 1.0 for goal in goals):
        raise ValueError('goals must lie in (0, 1]')
    if args.max_steps <= 0:
        raise ValueError('max-steps must be positive')

    graph_path = args.study_root / 'raw' / 'hcw_graph.json'
    scenario_path = args.study_root / 'raw' / 'scenarios.json'
    summary_path = args.study_root / 'summary.json'
    graph = load_archived_graph(graph_path)
    scenarios = _load_scenarios(scenario_path)
    summary = json.loads(summary_path.read_text())
    positions = _load_target_positions(summary)
    sentinels = _select_sentinels(
        graph,
        scenarios,
        positions,
        selection_splits,
    )
    target_index = {
        target_id: index for index, target_id in enumerate(graph.target_ids)
    }
    required_target_mask = sum(
        1 << target_index[item['target_id']] for item in sentinels
    )

    source_config = SuperiorityConfig(**summary['superiority_config'])
    study_scenarios = tuple(
        scenario for scenario in scenarios if scenario.split in splits
    )
    if not study_scenarios:
        raise ValueError('no scenarios match the requested splits')
    mesh_target_count = int(
        summary['base_experiment_config']['mesh_target_count']
    )
    rows = []
    for goal in goals:
        study_config = replace(
            source_config,
            goal_coverage=goal,
            max_steps=args.max_steps,
            adaptive_rollout_depth=args.adaptive_rollout_depth,
        )
        for scenario in study_scenarios:
            for requirement, mask in (
                ('coverage_only', 0),
                ('six_spatial_sentinels', required_target_mask),
            ):
                row = _evaluate_case(
                    graph,
                    scenario,
                    study_config,
                    goal,
                    mask,
                    required_target_mask,
                    requirement,
                    mesh_target_count,
                )
                rows.append(row)
                print(
                    f"goal={goal:.2f} requirement={requirement} "
                    f"scenario={scenario.scenario_id} status={row['status']} "
                    f"coverage={row['coverage']}"
                )

    aggregates = _aggregate(rows)
    run_id = args.run_id or (
        f'high_coverage_key_targets_{datetime.now():%Y%m%d_%H%M%S}'
    )
    result_dir = args.output_root / run_id
    raw_dir = result_dir / 'raw'
    config_dir = result_dir / 'config_snapshot'
    for directory in (
        raw_dir,
        config_dir,
        result_dir / 'figures',
        result_dir / 'rosbag',
        result_dir / 'videos',
    ):
        directory.mkdir(parents=True, exist_ok=True)
    _write_csv(raw_dir / 'scenario_results.csv', rows)
    _write_csv(raw_dir / 'key_targets.csv', list(sentinels))
    manifest = {
        'schema_version': 'orbinspect-high-coverage-key-targets/v1',
        'source_study_root': str(args.study_root),
        'source_graph_sha256': _sha256(graph_path),
        'source_scenarios_sha256': _sha256(scenario_path),
        'goals': goals,
        'evaluation_splits': sorted(splits),
        'sentinel_selection_splits': sorted(selection_splits),
        'max_steps': args.max_steps,
        'adaptive_rollout_depth': args.adaptive_rollout_depth,
        'node_count': len(graph.node_ids),
        'inspectable_target_count': len(graph.target_ids),
        'mesh_target_count': mesh_target_count,
        'sentinels': sentinels,
        'aggregates': aggregates,
    }
    rendered = json.dumps(manifest, indent=2, sort_keys=True)
    (config_dir / 'study_manifest.json').write_text(rendered + '\n')
    (result_dir / 'summary.json').write_text(rendered + '\n')
    (result_dir / 'summary.md').write_text(
        _summary_markdown(
            aggregates,
            sentinels,
            len(graph.target_ids),
            mesh_target_count,
        )
    )
    print(json.dumps({'result_dir': str(result_dir)}, indent=2))


if __name__ == '__main__':
    main()
