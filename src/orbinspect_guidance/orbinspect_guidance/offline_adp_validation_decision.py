"""Aggregate frozen-ADP validation runs without inspecting held-out tests."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import math
from pathlib import Path
import random
from statistics import mean, median


@dataclass(frozen=True)
class ValidationCandidate:
    """One frozen-critic configuration evaluated during model selection."""

    candidate_id: str
    label: str
    regime: str
    result_dir: Path


DEFAULT_CANDIDATES = (
    ValidationCandidate(
        candidate_id='rollout_mlp',
        label='Rollout targets',
        regime='90% goal, full graph',
        result_dir=Path('data/results/adp_superiority_mlp_2_20260801'),
    ),
    ValidationCandidate(
        candidate_id='exact_value_mlp',
        label='Exact value targets',
        regime='55% goal, 12 nodes',
        result_dir=Path(
            'data/results/adp_superiority_exact_features_retry_20260801'
        ),
    ),
    ValidationCandidate(
        candidate_id='exact_advantage_mlp',
        label='Exact advantage targets',
        regime='55% goal, 12 nodes',
        result_dir=Path(
            'data/results/adp_superiority_exact_advantage_20260801'
        ),
    ),
    ValidationCandidate(
        candidate_id='hard_exact_advantage_mlp',
        label='Exact advantage, harder goal',
        regime='70% goal, 12 nodes',
        result_dir=Path(
            'data/results/adp_superiority_hard_validation_20260801'
        ),
    ),
)


def aggregate_validation_decision(
    output_root: Path,
    run_id: str = '',
    candidates: tuple[ValidationCandidate, ...] = DEFAULT_CANDIDATES,
) -> Path:
    """Write a reproducible validation-gate decision from archived CSV rows."""
    study_id = run_id or f'adp_validation_decision_{datetime.now():%Y%m%d_%H%M%S}'
    result_dir = Path(output_root) / study_id
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

    candidate_rows = []
    for candidate in candidates:
        rows = _read_csv(candidate.result_dir / 'raw' / 'heldout_results.csv')
        validation_rows = [row for row in rows if row['split'] == 'validation']
        by_key = {
            (row['scenario_id'], row['method']): row
            for row in validation_rows
        }
        scenario_ids = sorted({row['scenario_id'] for row in validation_rows})
        differences = [
            float(by_key[(scenario_id, 'frozen_adp')]['penalized_cost'])
            - float(by_key[(scenario_id, 'local_search')]['penalized_cost'])
            for scenario_id in scenario_ids
        ]
        lower, upper = _paired_bootstrap_interval(differences)
        adp_rows = [
            by_key[(scenario_id, 'frozen_adp')]
            for scenario_id in scenario_ids
        ]
        local_rows = [
            by_key[(scenario_id, 'local_search')]
            for scenario_id in scenario_ids
        ]
        adp_success = mean(_as_bool(row['success']) for row in adp_rows)
        local_success = mean(_as_bool(row['success']) for row in local_rows)
        adp_latency = median(float(row['online_time_s']) for row in adp_rows)
        local_latency = median(float(row['online_time_s']) for row in local_rows)
        passes = bool(
            adp_success >= local_success
            and upper < 0.0
            and adp_latency < local_latency
        )
        candidate_rows.append({
            'candidate_id': candidate.candidate_id,
            'label': candidate.label,
            'regime': candidate.regime,
            'n': len(scenario_ids),
            'adp_success_rate': adp_success,
            'local_success_rate': local_success,
            'mean_paired_penalized_cost_difference': mean(differences),
            'paired_cost_ci_lower': lower,
            'paired_cost_ci_upper': upper,
            'adp_win_rate': mean(value < 0.0 for value in differences),
            'adp_median_online_time_s': adp_latency,
            'local_median_online_time_s': local_latency,
            'latency_ratio_adp_to_local': adp_latency / local_latency,
            'passes_validation_gate': passes,
            'source_result_dir': str(candidate.result_dir),
        })

    _write_rows(raw_dir / 'validation_candidates.csv', candidate_rows)
    _write_full_graph_pairs(candidates[0], raw_dir)
    _write_full_graph_methods(candidates[0], raw_dir)
    selected = [row for row in candidate_rows if row['passes_validation_gate']]
    summary = {
        'criterion': (
            'A frozen critic qualifies for test evaluation only if it matches '
            'local-search success, has an upper paired-bootstrap 95% cost '
            'bound below zero, and has lower median online latency.'
        ),
        'validation_candidate_count': len(candidate_rows),
        'qualified_candidate_ids': [row['candidate_id'] for row in selected],
        'test_evaluation_status': (
            'eligible_candidate_available'
            if selected else 'withheld_no_validation_candidate'
        ),
        'superiority_demonstrated': False,
        'candidate_results': candidate_rows,
    }
    (config_dir / 'source_manifest.json').write_text(json.dumps(
        {'candidates': [_jsonable(asdict(candidate)) for candidate in candidates]},
        indent=2,
        sort_keys=True,
    ))
    (result_dir / 'summary.json').write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    (result_dir / 'summary.md').write_text(_summary_markdown(summary))
    return result_dir


def _write_full_graph_pairs(candidate: ValidationCandidate, raw_dir: Path) -> None:
    rows = _read_csv(candidate.result_dir / 'raw' / 'heldout_results.csv')
    rows = [row for row in rows if row['split'] == 'validation']
    by_key = {(row['scenario_id'], row['method']): row for row in rows}
    output = []
    for sequence, scenario_id in enumerate(sorted({row['scenario_id'] for row in rows})):
        adp = by_key[(scenario_id, 'frozen_adp')]
        local = by_key[(scenario_id, 'local_search')]
        output.append({
            'sequence': sequence + 1,
            'scenario_id': scenario_id,
            'adp_success': _as_bool(adp['success']),
            'local_success': _as_bool(local['success']),
            'adp_penalized_cost': float(adp['penalized_cost']),
            'local_penalized_cost': float(local['penalized_cost']),
            'paired_penalized_cost_difference': (
                float(adp['penalized_cost']) - float(local['penalized_cost'])
            ),
        })
    _write_rows(raw_dir / 'full_graph_paired_costs.csv', output)


def _write_full_graph_methods(candidate: ValidationCandidate, raw_dir: Path) -> None:
    rows = _read_csv(candidate.result_dir / 'raw' / 'heldout_summary.csv')
    output = []
    for row in rows:
        if row['split'] != 'validation':
            continue
        output.append({
            'method': row['method'],
            'n': int(row['n']),
            'success_rate': float(row['success_rate']),
            'mean_penalized_cost': float(row['mean_penalized_cost']),
            'median_online_time_s': float(row['median_online_time_s']),
        })
    _write_rows(raw_dir / 'full_graph_methods.csv', output)


def _paired_bootstrap_interval(
    values: list[float],
    draws: int = 4000,
) -> tuple[float, float]:
    generator = random.Random(99173)
    means = sorted(
        mean(values[generator.randrange(len(values))] for _ in values)
        for _draw in range(draws)
    )
    return (
        means[math.floor(0.025 * (draws - 1))],
        means[math.ceil(0.975 * (draws - 1))],
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {'1', 'true', 'yes'}


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _summary_markdown(summary: dict[str, object]) -> str:
    lines = [
        '# Frozen ADP validation decision',
        '',
        f"- Criterion: {summary['criterion']}",
        f"- Test status: {summary['test_evaluation_status']}",
        f"- Superiority demonstrated: {summary['superiority_demonstrated']}",
        '',
        '| Candidate | Regime | Success (ADP/local) | '
        'Paired cost difference (95% CI) | Latency ratio | Pass |',
        '|---|---|---:|---:|---:|---:|',
    ]
    for row in summary['candidate_results']:
        lines.append(
            f"| {row['label']} | {row['regime']} | "
            f"{row['adp_success_rate']:.3f}/{row['local_success_rate']:.3f} | "
            f"{row['mean_paired_penalized_cost_difference']:.3f} "
            f"[{row['paired_cost_ci_lower']:.3f}, "
            f"{row['paired_cost_ci_upper']:.3f}] | "
            f"{row['latency_ratio_adp_to_local']:.2f} | "
            f"{row['passes_validation_gate']} |"
        )
    return '\n'.join(lines) + '\n'


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=Path('data/results'))
    parser.add_argument('--run-id', default='')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result_dir = aggregate_validation_decision(
        args.output_root,
        args.run_id,
    )
    print(json.dumps({'result_dir': str(result_dir)}, indent=2))


if __name__ == '__main__':
    main()
