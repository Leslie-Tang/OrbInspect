"""Paired robustness study for shielded candidate-graph sequence improvement."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, replace
from datetime import datetime
import json
import math
from pathlib import Path
import random
import statistics
from typing import Iterable

from orbinspect_guidance.offline_planning_experiment import _planner_config
from orbinspect_guidance.offline_planning_experiment import (
    _safe_load_yaml_mapping_from_text,
)
from orbinspect_guidance.offline_planning_experiment import ExperimentConfig
from orbinspect_guidance.offline_planning_experiment import MethodResult
from orbinspect_guidance.offline_planning_experiment import OfflinePlanningExperiment
from orbinspect_guidance.result_provenance import collect_result_provenance
from orbinspect_guidance.result_provenance import write_result_manifest


LOCAL_METHOD = 'safe_graph_adp_local_search'
REFERENCE_METHOD = 'set_cover_cw_tour'
STUDY_SCHEMA_VERSION = 'paired-sequence-improvement/v1'


@dataclass(frozen=True)
class PairedStudyConfig:
    """Design parameters fixed before running the paired study."""

    output_root: Path = Path('data/results')
    run_id: str = ''
    scenario_count: int = 20
    scenario_seed: int = 20260807
    bootstrap_samples: int = 10000
    position_half_width: tuple[float, float, float] = (8.0, 6.0, 6.0)
    velocity_half_width: tuple[float, float, float] = (0.012, 0.012, 0.012)


class PairedSequenceImprovementStudy:
    """Compare local sequence improvement with its paired safe incumbent."""

    def __init__(
        self,
        experiment_config: ExperimentConfig,
        study_config: PairedStudyConfig,
    ) -> None:
        """Build shared targets, candidates, visibility, and transfer cache once."""
        if study_config.scenario_count < 2:
            raise ValueError('scenario_count must be at least two')
        if study_config.bootstrap_samples <= 0:
            raise ValueError('bootstrap_samples must be positive')
        self.study_config = study_config
        self.experiment_config = replace(
            experiment_config,
            methods=(LOCAL_METHOD, REFERENCE_METHOD),
            passive_safety_horizon=0.0,
        )
        self.experiment = OfflinePlanningExperiment(self.experiment_config)
        self.scenarios = _latin_hypercube_initial_states(
            nominal=self.experiment_config.initial_state,
            count=study_config.scenario_count,
            seed=study_config.scenario_seed,
            position_half_width=study_config.position_half_width,
            velocity_half_width=study_config.velocity_half_width,
        )

    def run(self) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        """Run both algorithms for every predeclared initial condition."""
        method_rows: list[dict[str, object]] = []
        paired_rows: list[dict[str, object]] = []
        for scenario_index, initial_state in enumerate(self.scenarios):
            scenario_config = replace(
                self.experiment_config,
                initial_state=initial_state,
                random_seed=self.experiment_config.random_seed + scenario_index,
            )
            self.experiment.config = scenario_config
            self.experiment.base_planner.config = _planner_config(scenario_config)
            results: dict[str, MethodResult] = {}
            for method in (REFERENCE_METHOD, LOCAL_METHOD):
                result = self.experiment.run_method(method)
                results[method] = result
                method_rows.append(_method_row(scenario_index, initial_state, result))
            paired_rows.append(_paired_row(
                scenario_index,
                initial_state,
                results[LOCAL_METHOD],
                results[REFERENCE_METHOD],
            ))
        return method_rows, paired_rows

    def save(
        self,
        method_rows: list[dict[str, object]],
        paired_rows: list[dict[str, object]],
    ) -> Path:
        """Save the study design, raw paired outcomes, and uncertainty summary."""
        run_id = self.study_config.run_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        run_dir = self.study_config.output_root / run_id
        raw_dir = run_dir / 'raw'
        config_dir = run_dir / 'config_snapshot'
        for directory in (
            raw_dir,
            config_dir,
            run_dir / 'figures',
            run_dir / 'videos',
            run_dir / 'rosbag',
        ):
            directory.mkdir(parents=True, exist_ok=True)

        _write_rows(raw_dir / 'method_results.csv', method_rows)
        _write_rows(raw_dir / 'paired_results.csv', paired_rows)
        design = self._design_payload()
        summary = _summarize_pairs(
            paired_rows,
            bootstrap_samples=self.study_config.bootstrap_samples,
            seed=self.study_config.scenario_seed + 991,
        )
        provenance = collect_result_provenance(
            result_kind='paired_sequence_improvement_study',
            config=design,
            mesh_path=self.experiment.base_planner.config.iss_mesh_path,
        )
        payload = {
            'study_schema_version': STUDY_SCHEMA_VERSION,
            'design': design,
            'summary': summary,
            'provenance': provenance,
        }
        (run_dir / 'summary.json').write_text(
            json.dumps(payload, indent=2, sort_keys=True) + '\n',
            encoding='utf-8',
        )
        (run_dir / 'summary.md').write_text(
            _summary_markdown(summary),
            encoding='utf-8',
        )
        (config_dir / 'study_design.json').write_text(
            json.dumps(design, indent=2, sort_keys=True) + '\n',
            encoding='utf-8',
        )
        write_result_manifest(config_dir / 'result_manifest.json', provenance)
        return run_dir

    def _design_payload(self) -> dict[str, object]:
        experiment = asdict(self.experiment_config)
        experiment['output_root'] = str(experiment['output_root'])
        experiment['methods'] = list(experiment['methods'])
        experiment['initial_state'] = list(experiment['initial_state'])
        study = asdict(self.study_config)
        study['output_root'] = str(study['output_root'])
        study['position_half_width'] = list(study['position_half_width'])
        study['velocity_half_width'] = list(study['velocity_half_width'])
        return {
            'study_schema_version': STUDY_SCHEMA_VERSION,
            'primary_endpoint': 'paired total_dynamic_cost difference (local - incumbent)',
            'secondary_endpoints': [
                'paired total_delta_v difference (local - incumbent)',
                'paired final inspectable coverage difference (local - incumbent)',
                'paired feasibility and coverage-success rates',
            ],
            'methods': {
                'local': LOCAL_METHOD,
                'incumbent': REFERENCE_METHOD,
            },
            'experiment': experiment,
            'study': study,
            'initial_states': [list(state) for state in self.scenarios],
        }


def _method_row(
    scenario_index: int,
    initial_state: tuple[float, ...],
    result: MethodResult,
) -> dict[str, object]:
    summary = result.summary
    return {
        'scenario': scenario_index,
        'method': result.method,
        **{f'x0_{index}': value for index, value in enumerate(initial_state)},
        'feasible': summary['feasible'],
        'coverage_success': summary['inspectable_coverage_success'],
        'final_coverage_ratio': summary['final_coverage_ratio'],
        'final_inspectable_coverage_ratio': summary['final_inspectable_coverage_ratio'],
        'total_delta_v': summary['total_delta_v'],
        'total_dynamic_cost': summary['total_dynamic_cost'],
        'min_clearance': summary['min_clearance'],
        'peak_requested_input': summary['peak_requested_input'],
        'selected_viewpoint_count': summary['selected_viewpoint_count'],
        'planning_time': summary['planning_time'],
        'candidate_sequence': ';'.join(step.candidate.candidate_id for step in result.steps),
    }


def _paired_row(
    scenario_index: int,
    initial_state: tuple[float, ...],
    local: MethodResult,
    reference: MethodResult,
) -> dict[str, object]:
    local_summary = local.summary
    reference_summary = reference.summary
    local_success = bool(local_summary['feasible']) and bool(
        local_summary['inspectable_coverage_success']
    )
    reference_success = bool(reference_summary['feasible']) and bool(
        reference_summary['inspectable_coverage_success']
    )
    return {
        'scenario': scenario_index,
        **{f'x0_{index}': value for index, value in enumerate(initial_state)},
        'local_success': local_success,
        'incumbent_success': reference_success,
        'common_success': local_success and reference_success,
        'local_total_dynamic_cost': local_summary['total_dynamic_cost'],
        'incumbent_total_dynamic_cost': reference_summary['total_dynamic_cost'],
        'dynamic_cost_difference': (
            float(local_summary['total_dynamic_cost'])
            - float(reference_summary['total_dynamic_cost'])
        ),
        'local_total_delta_v': local_summary['total_delta_v'],
        'incumbent_total_delta_v': reference_summary['total_delta_v'],
        'delta_v_difference': (
            float(local_summary['total_delta_v'])
            - float(reference_summary['total_delta_v'])
        ),
        'local_inspectable_coverage': local_summary['final_inspectable_coverage_ratio'],
        'incumbent_inspectable_coverage': (
            reference_summary['final_inspectable_coverage_ratio']
        ),
        'inspectable_coverage_difference': (
            float(local_summary['final_inspectable_coverage_ratio'])
            - float(reference_summary['final_inspectable_coverage_ratio'])
        ),
        'local_min_clearance': local_summary['min_clearance'],
        'incumbent_min_clearance': reference_summary['min_clearance'],
        'local_planning_time': local_summary['planning_time'],
        'incumbent_planning_time': reference_summary['planning_time'],
    }


def _summarize_pairs(
    rows: list[dict[str, object]],
    *,
    bootstrap_samples: int,
    seed: int,
) -> dict[str, object]:
    common = [row for row in rows if bool(row['common_success'])]
    dynamic = [float(row['dynamic_cost_difference']) for row in common]
    delta_v = [float(row['delta_v_difference']) for row in common]
    coverage = [float(row['inspectable_coverage_difference']) for row in common]
    method_means = {
        'local_total_dynamic_cost': _mean_field(common, 'local_total_dynamic_cost'),
        'incumbent_total_dynamic_cost': _mean_field(
            common, 'incumbent_total_dynamic_cost'
        ),
        'local_total_delta_v': _mean_field(common, 'local_total_delta_v'),
        'incumbent_total_delta_v': _mean_field(common, 'incumbent_total_delta_v'),
        'local_inspectable_coverage': _mean_field(
            common, 'local_inspectable_coverage'
        ),
        'incumbent_inspectable_coverage': _mean_field(
            common, 'incumbent_inspectable_coverage'
        ),
        'local_planning_time': _mean_field(common, 'local_planning_time'),
        'incumbent_planning_time': _mean_field(common, 'incumbent_planning_time'),
    }
    method_means['dynamic_cost_reduction_percent'] = _reduction_percent(
        method_means['local_total_dynamic_cost'],
        method_means['incumbent_total_dynamic_cost'],
    )
    method_means['delta_v_reduction_percent'] = _reduction_percent(
        method_means['local_total_delta_v'],
        method_means['incumbent_total_delta_v'],
    )
    return {
        'scenario_count': len(rows),
        'common_success_count': len(common),
        'local_success_count': sum(bool(row['local_success']) for row in rows),
        'incumbent_success_count': sum(bool(row['incumbent_success']) for row in rows),
        'method_means_over_common_successes': method_means,
        'minimum_clearance_over_all_scenarios': {
            'local': min(float(row['local_min_clearance']) for row in rows),
            'incumbent': min(float(row['incumbent_min_clearance']) for row in rows),
        },
        'dynamic_cost': _paired_endpoint(dynamic, bootstrap_samples, seed),
        'delta_v': _paired_endpoint(delta_v, bootstrap_samples, seed + 1),
        'inspectable_coverage': _paired_endpoint(
            coverage,
            bootstrap_samples,
            seed + 2,
        ),
    }


def _mean_field(rows: list[dict[str, object]], field: str) -> float | None:
    if not rows:
        return None
    return statistics.fmean(float(row[field]) for row in rows)


def _reduction_percent(local: float | None, incumbent: float | None) -> float | None:
    if local is None or incumbent is None or abs(incumbent) <= 1.0e-12:
        return None
    return 100.0 * (incumbent - local) / incumbent


def _paired_endpoint(
    differences: list[float],
    bootstrap_samples: int,
    seed: int,
) -> dict[str, object]:
    if not differences:
        return {'pair_count': 0}
    tolerance = 1.0e-10
    wins = sum(value < -tolerance for value in differences)
    losses = sum(value > tolerance for value in differences)
    ties = len(differences) - wins - losses
    lower, upper = _bootstrap_mean_interval(
        differences,
        bootstrap_samples,
        seed,
    )
    return {
        'pair_count': len(differences),
        'mean_difference': statistics.fmean(differences),
        'median_difference': statistics.median(differences),
        'bootstrap_95_percent_ci_for_mean': [lower, upper],
        'local_better_count': wins,
        'incumbent_better_count': losses,
        'tie_count': ties,
        'exact_two_sided_sign_test_p': _two_sided_sign_test(wins, losses),
    }


def _bootstrap_mean_interval(
    values: list[float],
    samples: int,
    seed: int,
) -> tuple[float, float]:
    generator = random.Random(seed)
    count = len(values)
    means = sorted(
        statistics.fmean(values[generator.randrange(count)] for _ in range(count))
        for _sample in range(samples)
    )
    return (
        _percentile(means, 0.025),
        _percentile(means, 0.975),
    )


def _percentile(sorted_values: list[float], probability: float) -> float:
    position = probability * (len(sorted_values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sorted_values[lower]
    fraction = position - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def _two_sided_sign_test(wins: int, losses: int) -> float:
    non_ties = wins + losses
    if non_ties == 0:
        return 1.0
    tail = sum(
        math.comb(non_ties, index)
        for index in range(min(wins, losses) + 1)
    ) / (2.0 ** non_ties)
    return min(1.0, 2.0 * tail)


def _latin_hypercube_initial_states(
    *,
    nominal: tuple[float, ...],
    count: int,
    seed: int,
    position_half_width: tuple[float, float, float],
    velocity_half_width: tuple[float, float, float],
) -> tuple[tuple[float, ...], ...]:
    widths = position_half_width + velocity_half_width
    columns: list[list[float]] = []
    for dimension, half_width in enumerate(widths):
        order = list(range(count))
        random.Random(seed + 104729 * (dimension + 1)).shuffle(order)
        columns.append([
            nominal[dimension]
            + half_width * (2.0 * (bin_index + 0.5) / count - 1.0)
            for bin_index in order
        ])
    return tuple(
        tuple(columns[dimension][scenario] for dimension in range(6))
        for scenario in range(count)
    )


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f'cannot write empty result table: {path}')
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _summary_markdown(summary: dict[str, object]) -> str:
    dynamic = summary['dynamic_cost']
    delta_v = summary['delta_v']
    coverage = summary['inspectable_coverage']
    means = summary['method_means_over_common_successes']
    lines = [
        '# Paired Shielded Sequence-Improvement Study',
        '',
        f"- Scenarios: {summary['scenario_count']}",
        f"- Common successful pairs: {summary['common_success_count']}",
        f"- Local-search successes: {summary['local_success_count']}",
        f"- Incumbent successes: {summary['incumbent_success_count']}",
        '- Mean dynamic-cost reduction: '
        f"{_format_percent(means['dynamic_cost_reduction_percent'])}",
        '- Mean delta-v reduction: '
        f"{_format_percent(means['delta_v_reduction_percent'])}",
        '',
        '| Endpoint (local - incumbent) | Mean | 95% paired bootstrap CI | '
        'Local better / tie / incumbent better | Sign-test p |',
        '| --- | ---: | ---: | ---: | ---: |',
    ]
    for label, endpoint in (
        ('Dynamic cost', dynamic),
        ('Delta-v', delta_v),
        ('Inspectable coverage', coverage),
    ):
        if not isinstance(endpoint, dict) or endpoint.get('pair_count', 0) == 0:
            lines.append(f'| {label} | n/a | n/a | n/a | n/a |')
            continue
        interval = endpoint['bootstrap_95_percent_ci_for_mean']
        lines.append(
            f"| {label} | {float(endpoint['mean_difference']):.6g} | "
            f'[{float(interval[0]):.6g}, {float(interval[1]):.6g}] | '
            f"{endpoint['local_better_count']} / {endpoint['tie_count']} / "
            f"{endpoint['incumbent_better_count']} | "
            f"{float(endpoint['exact_two_sided_sign_test_p']):.6g} |"
        )
    return '\n'.join(lines) + '\n'


def _format_percent(value: object) -> str:
    if value is None:
        return 'n/a'
    return f'{float(value):.3f}%'


def _load_configs(path: Path) -> tuple[ExperimentConfig, PairedStudyConfig]:
    raw = _safe_load_yaml_mapping_from_text(path.read_text(encoding='utf-8'))
    parameters = raw.get('paired_sequence_improvement_study', {})
    if isinstance(parameters, dict):
        parameters = parameters.get('ros__parameters', parameters)
    if not isinstance(parameters, dict):
        raise ValueError(f'study config must be a mapping: {path}')
    experiment_fields = set(ExperimentConfig.__dataclass_fields__)
    study_fields = set(PairedStudyConfig.__dataclass_fields__)
    experiment_values = {
        key: value for key, value in parameters.items() if key in experiment_fields
    }
    study_values = {
        key: value for key, value in parameters.items() if key in study_fields
    }
    for values in (experiment_values, study_values):
        if 'output_root' in values:
            values['output_root'] = Path(str(values['output_root']))
    if 'initial_state' in experiment_values:
        experiment_values['initial_state'] = tuple(
            float(value) for value in experiment_values['initial_state']
        )
    for key in ('position_half_width', 'velocity_half_width'):
        if key in study_values:
            study_values[key] = tuple(float(value) for value in study_values[key])
    return ExperimentConfig(**experiment_values), PairedStudyConfig(**study_values)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse the paired-study command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--config',
        default=(
            'src/orbinspect_guidance/config/'
            'paired_sequence_improvement_study.yaml'
        ),
    )
    parser.add_argument('--run-id', default='')
    parser.add_argument('--scenario-count', type=int)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    """Run and save the paired sequence-improvement study."""
    args = parse_args(argv)
    experiment_config, study_config = _load_configs(Path(args.config))
    if args.run_id:
        study_config = replace(study_config, run_id=args.run_id)
    if args.scenario_count is not None:
        study_config = replace(study_config, scenario_count=args.scenario_count)
    study = PairedSequenceImprovementStudy(experiment_config, study_config)
    method_rows, paired_rows = study.run()
    run_dir = study.save(method_rows, paired_rows)
    print(run_dir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
