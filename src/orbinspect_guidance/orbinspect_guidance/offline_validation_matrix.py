"""Run sensitivity and ablation studies for the offline inspection planner."""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import json
from pathlib import Path
from time import perf_counter

from orbinspect_guidance.offline_planning_experiment import ExperimentConfig
from orbinspect_guidance.offline_planning_experiment import OfflinePlanningExperiment
from orbinspect_guidance.offline_planning_experiment import config_from_args
from orbinspect_guidance.offline_planning_experiment import parse_args as parse_base_args


SUMMARY_FIELDS = [
    'study',
    'case_id',
    'method',
    'mesh_target_count',
    'candidate_stride',
    'candidate_radius',
    'initial_state',
    'safety_margin',
    'transfer_duration',
    'max_acceleration',
    'candidate_count',
    'selected_viewpoint_count',
    'final_coverage_ratio',
    'final_inspectable_coverage_ratio',
    'coverage_success',
    'feasible',
    'total_delta_v',
    'peak_requested_input',
    'min_clearance',
    'mission_duration',
    'planning_time',
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse validation-matrix command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--config',
        default='src/orbinspect_guidance/config/offline_planning_experiment.yaml',
    )
    parser.add_argument('--output-root', default='data/results/validation_matrix')
    parser.add_argument('--run-id', default='')
    parser.add_argument('--quick', action='store_true')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the validation matrix and write summary CSV/JSON files."""
    args = parse_args(argv)
    base_args = parse_base_args(['--config', args.config])
    base = config_from_args(base_args)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    cases = _quick_cases(base) if args.quick else _paper_cases(base)
    started = perf_counter()
    rows: list[dict[str, object]] = []
    csv_path = output_root / 'validation_matrix_summary.csv'
    with csv_path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()

    for case_index, (study, case_id, config) in enumerate(cases):
        run_id = args.run_id or f'{case_index:03d}_{study}_{case_id}'
        case_config = replace(config, output_root=output_root, run_id=run_id)
        experiment = OfflinePlanningExperiment(case_config)
        results = experiment.run()
        case_rows = []
        for result in results:
            row = _summary_row(study, case_id, case_config, result.summary)
            rows.append(row)
            case_rows.append(row)
        with csv_path.open('a', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
            writer.writerows(case_rows)

    with csv_path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    json_path = output_root / 'validation_matrix_summary.json'
    json_path.write_text(json.dumps({
        'case_count': len(cases),
        'row_count': len(rows),
        'elapsed_s': perf_counter() - started,
        'summary_csv': str(csv_path),
        'rows': rows,
    }, indent=2, sort_keys=True) + '\n')
    print(json.dumps({
        'case_count': len(cases),
        'row_count': len(rows),
        'summary_csv': str(csv_path),
        'summary_json': str(json_path),
    }, indent=2, sort_keys=True))


def _paper_cases(base: ExperimentConfig) -> list[tuple[str, str, ExperimentConfig]]:
    """Return the manuscript validation matrix."""
    methods = (
        'set_cover_cw_tour',
        'coverage_greedy',
        'safe_coverage_greedy',
    )
    ablation_methods = (
        'set_cover_cw_tour',
        'abl_no_transfer_cost',
        'abl_no_clearance_filter',
        'abl_no_input_check',
        'abl_unweighted_coverage',
    )
    base = replace(
        base,
        methods=methods,
        run_id='matrix_lean_base',
        mesh_occlusion_max_triangles=min(base.mesh_occlusion_max_triangles, 80),
    )
    cases: list[tuple[str, str, ExperimentConfig]] = []
    for target_count in (180, 500):
        cases.append((
            'target_density',
            f'N{target_count}',
            replace(base, mesh_target_count=target_count, run_id=f'matrix_lean_N{target_count}'),
        ))
    cases.append((
        'target_density',
        'N1000_proposed',
        replace(
            base,
            mesh_target_count=1000,
            methods=('set_cover_cw_tour',),
            candidate_stride=4,
            max_viewpoints=min(base.max_viewpoints, 24),
            run_id='matrix_lean_N1000_proposed',
        ),
    ))
    for stride in (1, 2, 3):
        cases.append((
            'candidate_density',
            f'stride{stride}',
            replace(base, candidate_stride=stride, run_id=f'matrix_lean_stride{stride}'),
        ))
    initial_states = (
        (0.0, -35.0, 10.0, 0.0, 0.0, 0.0),
        (18.0, -42.0, 12.0, 0.0, 0.0, 0.0),
        (-20.0, -32.0, 8.0, 0.0, 0.0, 0.0),
    )
    for index, state in enumerate(initial_states):
        cases.append((
            'initial_condition',
            f'ic{index}',
            replace(base, initial_state=state, run_id=f'matrix_lean_ic{index}'),
        ))
    for safety_margin in (1.0, 2.0, 4.0):
        cases.append((
            'safety_margin',
            f'keepout{safety_margin:g}',
            replace(base, safety_margin=safety_margin, run_id=f'matrix_lean_keepout{safety_margin:g}'),
        ))
    for duration in (70.0, 90.0, 120.0):
        cases.append((
            'transfer_duration',
            f'T{int(duration)}',
            replace(base, transfer_duration=duration, run_id=f'matrix_lean_T{int(duration)}'),
        ))
    cases.append((
        'ablation',
        'component_removal',
        replace(base, methods=ablation_methods, run_id='matrix_lean_ablation'),
    ))
    return cases


def _quick_cases(base: ExperimentConfig) -> list[tuple[str, str, ExperimentConfig]]:
    """Return a lightweight matrix for tests and smoke validation."""
    base = replace(
        base,
        mesh_target_count=48,
        mesh_occlusion_max_triangles=0,
        max_viewpoints=5,
        transfer_duration=16.0,
        integration_dt=4.0,
        methods=('set_cover_cw_tour', 'coverage_greedy', 'abl_no_transfer_cost'),
    )
    return [
        ('target_density', 'N48', base),
        ('candidate_density', 'stride3', replace(base, candidate_stride=3)),
        ('ablation', 'component_removal', base),
    ]


def _summary_row(
    study: str,
    case_id: str,
    config: ExperimentConfig,
    summary: dict[str, float | int | str | bool],
) -> dict[str, object]:
    return {
        'study': study,
        'case_id': case_id,
        'method': summary['method'],
        'mesh_target_count': config.mesh_target_count,
        'candidate_stride': config.candidate_stride,
        'candidate_radius': config.candidate_radius,
        'initial_state': json.dumps(list(config.initial_state)),
        'safety_margin': config.safety_margin,
        'transfer_duration': config.transfer_duration,
        'max_acceleration': config.max_acceleration,
        'candidate_count': summary['candidate_count'],
        'selected_viewpoint_count': summary['selected_viewpoint_count'],
        'final_coverage_ratio': summary['final_coverage_ratio'],
        'final_inspectable_coverage_ratio': summary['final_inspectable_coverage_ratio'],
        'coverage_success': summary['coverage_success'],
        'feasible': summary['feasible'],
        'total_delta_v': summary['total_delta_v'],
        'peak_requested_input': summary['peak_requested_input'],
        'min_clearance': summary['min_clearance'],
        'mission_duration': summary['mission_duration'],
        'planning_time': summary['planning_time'],
    }


if __name__ == '__main__':
    main()
