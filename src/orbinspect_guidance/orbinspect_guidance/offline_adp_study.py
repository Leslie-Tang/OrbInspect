"""Run and archive the paper study for safety-shielded graph ADP."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, replace
from datetime import datetime
import json
from pathlib import Path
from time import perf_counter

from orbinspect_guidance.offline_planning_experiment import ExperimentConfig
from orbinspect_guidance.offline_planning_experiment import MethodResult
from orbinspect_guidance.offline_planning_experiment import OfflinePlanningExperiment
from orbinspect_guidance.offline_planning_experiment import _load_yaml_config


@dataclass(frozen=True)
class StudyCase:
    """One independently saved ADP study case."""

    case_id: str
    family: str
    label: str
    config: ExperimentConfig


def build_study_cases(
    base: ExperimentConfig,
    *,
    quick: bool = False,
) -> tuple[StudyCase, ...]:
    """Build primary, oracle, robustness, and compute-ablation cases."""
    primary = replace(
        base,
        run_id='primary',
        methods=(
            'safe_graph_adp',
            'set_cover_cw_tour',
            'safe_coverage_greedy',
            'fuel_greedy',
            'coverage_greedy',
        ),
        adp_branch_width=6,
        adp_candidate_pool_width=18,
        adp_lookahead_depth=2,
        adp_training_episodes=80,
    )
    cases = [
        StudyCase(
            case_id='primary',
            family='primary',
            label='ISS mesh, N=180',
            config=primary,
        ),
        StudyCase(
            case_id='component_ablation',
            family='components',
            label='Matched primary-graph component ablation',
            config=replace(
                primary,
                run_id='component_ablation',
                methods=(
                    'set_cover_cw_tour',
                    'safe_graph_adp_critic_only',
                    'safe_graph_adp_critic_safeguard',
                    'safe_graph_adp_rollout',
                    'safe_graph_adp_local_search',
                    'safe_graph_adp_no_local',
                    'safe_graph_adp',
                ),
            ),
        ),
    ]

    oracle_node_counts = (8, 10) if quick else (8, 10, 12)
    oracle_seeds = (7,) if quick else (3, 7, 11)
    for node_count in oracle_node_counts:
        for seed in oracle_seeds:
            case_id = f'oracle_n{node_count}_seed{seed}'
            cases.append(StudyCase(
                case_id=case_id,
                family='oracle',
                label=f'{node_count} nodes, seed {seed}',
                config=replace(
                    base,
                    run_id=case_id,
                    mesh_target_count=48,
                    mesh_occlusion_max_triangles=240,
                    candidate_stride=3,
                    coverage_threshold=0.35,
                    coverage_stop_ratio=0.35,
                    max_viewpoints=7,
                    methods=('safe_graph_adp',),
                    random_seed=seed,
                    adp_candidate_limit=node_count,
                    adp_branch_width=min(4, node_count),
                    adp_candidate_pool_width=node_count,
                    adp_lookahead_depth=2,
                    adp_training_episodes=50,
                    adp_oracle_node_limit=14,
                ),
            ))

    initial_states = (
        ('ic0', (0.0, -35.0, 10.0, 0.0, 0.0, 0.0)),
        ('ic1', (18.0, -42.0, 12.0, 0.0, 0.0, 0.0)),
        ('ic2', (-20.0, -32.0, 8.0, 0.0, 0.0, 0.0)),
    )
    if quick:
        initial_states = initial_states[:2]
    for label, initial_state in initial_states:
        case_id = f'robustness_{label}'
        cases.append(StudyCase(
            case_id=case_id,
            family='robustness',
            label=f'{label}: r0={initial_state[:3]} m',
            config=replace(
                primary,
                run_id=case_id,
                initial_state=initial_state,
                methods=('safe_graph_adp', 'set_cover_cw_tour'),
                adp_candidate_limit=72,
                adp_branch_width=5,
                adp_candidate_pool_width=15,
                adp_training_episodes=50,
            ),
        ))

    ablations = (
        ('critic_free', 0, 1),
        ('short_training', 20, 2),
        ('primary_compute', 80, 2),
        ('deeper_lookahead', 80, 3),
    )
    if quick:
        ablations = ablations[:3]
    for label, episodes, depth in ablations:
        case_id = f'compute_{label}'
        cases.append(StudyCase(
            case_id=case_id,
            family='compute',
            label=f'{episodes} episodes, depth {depth}',
            config=replace(
                base,
                run_id=case_id,
                mesh_target_count=90,
                mesh_occlusion_max_triangles=300,
                candidate_stride=2,
                coverage_threshold=0.70,
                coverage_stop_ratio=0.95,
                max_viewpoints=24,
                methods=('safe_graph_adp',),
                adp_candidate_limit=48,
                adp_branch_width=4,
                adp_candidate_pool_width=12,
                adp_lookahead_depth=depth,
                adp_training_episodes=episodes,
            ),
        ))
    return tuple(cases)


def run_study(
    base: ExperimentConfig,
    output_root: Path,
    run_id: str = '',
    *,
    quick: bool = False,
    families: tuple[str, ...] = (),
) -> Path:
    """Run every study case and write a cross-case result table."""
    study_id = run_id or f'adp_study_{datetime.now():%Y%m%d_%H%M%S}'
    study_dir = Path(output_root) / study_id
    cases_root = study_dir / 'cases'
    for directory in (
        study_dir / 'config_snapshot',
        study_dir / 'raw',
        study_dir / 'figures',
        study_dir / 'rosbag',
        study_dir / 'videos',
        cases_root,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    cases = build_study_cases(base, quick=quick)
    if families:
        cases = tuple(case for case in cases if case.family in families)
        unknown = set(families) - {case.family for case in build_study_cases(base)}
        if unknown:
            raise ValueError(
                f'unknown study families: {", ".join(sorted(unknown))}'
            )
    rows: list[dict[str, object]] = []
    completed_cases: list[dict[str, object]] = []
    study_start = perf_counter()
    for case in cases:
        case_config = replace(
            case.config,
            output_root=cases_root,
            run_id=case.case_id,
        )
        case_start = perf_counter()
        experiment = OfflinePlanningExperiment(case_config)
        results = experiment.run()
        case_dir = experiment.save(results)
        elapsed = perf_counter() - case_start
        rows.extend(_result_rows(case, case_dir, results, elapsed))
        completed_cases.append({
            'case_id': case.case_id,
            'family': case.family,
            'label': case.label,
            'run_dir': str(case_dir),
            'elapsed_s': elapsed,
        })
        _write_study_rows(study_dir / 'raw' / 'adp_study_runs.csv', rows)
        _write_json(study_dir / 'summary.json', {
            'status': 'running',
            'quick': quick,
            'families': list(families),
            'completed_cases': completed_cases,
            'planned_case_count': len(cases),
            'elapsed_s': perf_counter() - study_start,
        })

    summary = {
        'status': 'complete',
        'quick': quick,
        'completed_cases': completed_cases,
        'planned_case_count': len(cases),
        'elapsed_s': perf_counter() - study_start,
        'primary': [
            row for row in rows
            if row['family'] == 'primary'
        ],
    }
    _write_json(study_dir / 'summary.json', summary)
    _write_summary_md(study_dir / 'summary.md', rows)
    _write_json(
        study_dir / 'config_snapshot' / 'study_manifest.json',
        {
            'base_config': _config_dict(base),
            'quick': quick,
            'cases': [
                {
                    'case_id': case.case_id,
                    'family': case.family,
                    'label': case.label,
                    'config': _config_dict(case.config),
                }
                for case in cases
            ],
        },
    )
    return study_dir


def _result_rows(
    case: StudyCase,
    case_dir: Path,
    results: tuple[MethodResult, ...],
    elapsed_s: float,
) -> list[dict[str, object]]:
    rows = []
    for result in results:
        config = case.config
        summary = result.summary
        rows.append({
            'family': case.family,
            'case_id': case.case_id,
            'case_label': case.label,
            'run_dir': str(case_dir),
            'case_elapsed_s': elapsed_s,
            'method': result.method,
            'random_seed': config.random_seed,
            'initial_x': config.initial_state[0],
            'initial_y': config.initial_state[1],
            'initial_z': config.initial_state[2],
            'mesh_target_count': config.mesh_target_count,
            'candidate_limit': config.adp_candidate_limit,
            'branch_width': config.adp_branch_width,
            'candidate_pool_width': config.adp_candidate_pool_width,
            'lookahead_depth': config.adp_lookahead_depth,
            'training_episodes': config.adp_training_episodes,
            'coverage': summary['final_inspectable_coverage_ratio'],
            'raw_coverage': summary['final_coverage_ratio'],
            'coverage_success': summary.get(
                'adp_goal_reached',
                summary['coverage_success'],
            ),
            'feasible': summary['feasible'],
            'total_delta_v': summary['total_delta_v'],
            'min_clearance': summary['min_clearance'],
            'passive_margin': summary.get('passive_margin_min', ''),
            'peak_input': summary['peak_requested_input'],
            'selected_count': summary['selected_viewpoint_count'],
            'planning_time': summary['planning_time'],
            'graph_cost': summary.get('adp_graph_cost', ''),
            'policy_source': summary.get('adp_policy_source', ''),
            'learned_graph_cost': summary.get('adp_learned_graph_cost', ''),
            'rollout_graph_cost': summary.get('adp_rollout_graph_cost', ''),
            'reference_graph_cost': summary.get(
                'adp_reference_graph_cost',
                '',
            ),
            'improved_reference_graph_cost': summary.get(
                'adp_improved_reference_graph_cost',
                '',
            ),
            'incumbent_improvement': summary.get(
                'adp_incumbent_improvement',
                '',
            ),
            'exact_cost': summary.get('adp_exact_cost', ''),
            'optimality_gap': summary.get('adp_optimality_gap', ''),
            'exact_expansions': summary.get('adp_exact_expansions', ''),
            'td_updates': summary.get('adp_td_update_count', ''),
            'mean_absolute_td_error': summary.get(
                'adp_mean_absolute_td_error',
                '',
            ),
            'shield_rejections': summary.get('adp_shield_rejections', ''),
            'safe_action_evaluations': summary.get(
                'adp_safe_action_evaluations',
                '',
            ),
            'critic_enabled': summary.get('adp_critic_enabled', ''),
            'rollout_enabled': summary.get('adp_rollout_enabled', ''),
            'safeguard_enabled': summary.get('adp_safeguard_enabled', ''),
            'local_improvement_enabled': summary.get(
                'adp_local_improvement_enabled',
                '',
            ),
        })
    return rows


def _write_study_rows(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = list(rows[0]) if rows else []
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_summary_md(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        '# Safety-Shielded Graph ADP Study',
        '',
        '| Case | Method | Coverage | Delta-v | Clearance | Feasible | '
        'Plan time | Exact gap |',
        '| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |',
    ]
    for row in rows:
        exact_gap = row['optimality_gap']
        gap_text = (
            f'{float(exact_gap):.4f}'
            if exact_gap not in ('', None)
            else ''
        )
        lines.append(
            f"| {row['case_id']} | {row['method']} "
            f"| {float(row['coverage']):.4f} "
            f"| {float(row['total_delta_v']):.3f} "
            f"| {float(row['min_clearance']):.3f} "
            f"| {row['feasible']} "
            f"| {float(row['planning_time']):.3f} "
            f"| {gap_text} |"
        )
    path.write_text('\n'.join(lines) + '\n')


def _config_dict(config: ExperimentConfig) -> dict[str, object]:
    values = dict(config.__dict__)
    values['output_root'] = str(config.output_root)
    values['initial_state'] = list(config.initial_state)
    values['methods'] = list(config.methods)
    return values


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse study command arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--config',
        default='src/orbinspect_guidance/config/offline_planning_experiment.yaml',
    )
    parser.add_argument('--output-root', type=Path, default=Path('data/results'))
    parser.add_argument('--run-id', default='')
    parser.add_argument('--quick', action='store_true')
    parser.add_argument(
        '--families',
        default='',
        help=(
            'Comma-separated subset: primary, components, oracle, '
            'robustness, compute.'
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the saved-data ADP paper study."""
    args = parse_args(argv)
    values = _load_yaml_config(Path(args.config))
    if 'output_root' in values:
        values['output_root'] = Path(str(values['output_root']))
    if 'methods' in values:
        values['methods'] = tuple(str(method) for method in values['methods'])
    if 'initial_state' in values:
        values['initial_state'] = tuple(
            float(value)
            for value in values['initial_state']
        )
    base = ExperimentConfig(**values)
    study_dir = run_study(
        base,
        args.output_root,
        args.run_id,
        quick=args.quick,
        families=tuple(
            item.strip()
            for item in args.families.split(',')
            if item.strip()
        ),
    )
    print(json.dumps({'study_dir': str(study_dir)}, indent=2))


if __name__ == '__main__':
    main()
