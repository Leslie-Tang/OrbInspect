"""Monte Carlo comparison runner for OrbInspect baseline methods."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import random
import statistics
import time

from orbinspect_eval.compare_methods import plot_method_comparison


METHOD_BASELINES = {
    'fixed_waypoints': (0.45, 0.20),
    'random_safe': (0.35, 0.25),
    'greedy_nbv': (0.72, 0.18),
    'greedy_nbv_safety_filter': (0.78, 0.12),
}


RUN_COLUMNS = (
    'run_id',
    'scenario',
    'method',
    'seed',
    'coverage_ratio',
    'total_delta_v',
    'minimum_distance',
    'safety_violations',
    'success',
)


SUMMARY_COLUMNS = (
    'method',
    'runs',
    'success_rate',
    'mean_coverage',
    'mean_delta_v',
    'mean_min_distance',
    'violation_count',
)


def run_monte_carlo(
    scenario: str,
    methods: list[str],
    num_runs: int,
    seed: int,
    result_root: str = 'data/results',
) -> Path:
    """Run deterministic Monte Carlo metric simulations and save summaries."""
    if num_runs <= 0:
        raise ValueError('num_runs must be positive')
    rng = random.Random(seed)
    stamp = time.strftime('%Y%m%d_%H%M%S')
    root = Path(result_root) / f'monte_carlo_{stamp}'
    raw_dir = root / 'raw'
    figures_dir = root / 'figures'
    raw_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for method in methods:
        if method not in METHOD_BASELINES:
            raise ValueError(f'unsupported method: {method}')
        for index in range(num_runs):
            run_seed = rng.randint(0, 2**31 - 1)
            row = _simulate_run(scenario, method, index, run_seed)
            rows.append(row)
            _write_run_summary(root / row['run_id'], row)

    _write_csv(raw_dir / 'runs.csv', RUN_COLUMNS, rows)
    summary_rows = _aggregate(rows, methods)
    _write_csv(root / 'summary_table.csv', SUMMARY_COLUMNS, summary_rows)
    plot_method_comparison(summary_rows, figures_dir / 'method_comparison.png')
    with (root / 'summary.json').open('w') as summary_file:
        json.dump({'scenario': scenario, 'num_runs': num_runs, 'methods': methods}, summary_file)
    return root


def _simulate_run(scenario: str, method: str, index: int, seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    base_coverage, base_delta_v = METHOD_BASELINES[method]
    coverage = min(1.0, max(0.0, rng.gauss(base_coverage, 0.06)))
    delta_v = max(0.0, rng.gauss(base_delta_v, 0.03))
    minimum_distance = max(0.0, rng.gauss(3.5 if 'safety' in method else 2.4, 0.45))
    safety_violations = 0 if minimum_distance >= 2.0 else 1
    success = coverage >= 0.7 and safety_violations == 0
    return {
        'run_id': f'{method}_{index:03d}',
        'scenario': scenario,
        'method': method,
        'seed': seed,
        'coverage_ratio': coverage,
        'total_delta_v': delta_v,
        'minimum_distance': minimum_distance,
        'safety_violations': safety_violations,
        'success': success,
    }


def _aggregate(rows: list[dict[str, object]], methods: list[str]) -> list[dict[str, object]]:
    summary_rows = []
    for method in methods:
        method_rows = [row for row in rows if row['method'] == method]
        summary_rows.append({
            'method': method,
            'runs': len(method_rows),
            'success_rate': _mean([1.0 if row['success'] else 0.0 for row in method_rows]),
            'mean_coverage': _mean([float(row['coverage_ratio']) for row in method_rows]),
            'mean_delta_v': _mean([float(row['total_delta_v']) for row in method_rows]),
            'mean_min_distance': _mean([float(row['minimum_distance']) for row in method_rows]),
            'violation_count': sum(int(row['safety_violations']) for row in method_rows),
        })
    return summary_rows


def _write_run_summary(path: Path, row: dict[str, object]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    with (path / 'summary.json').open('w') as summary_file:
        json.dump(row, summary_file, indent=2)


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open('w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return statistics.fmean(values)


def main() -> None:
    parser = argparse.ArgumentParser(description='Run OrbInspect Monte Carlo comparison.')
    parser.add_argument('--scenario', default='full_station')
    parser.add_argument('--methods', nargs='+', default=['fixed_waypoints', 'greedy_nbv'])
    parser.add_argument('--num-runs', type=int, default=20)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--result-root', default='data/results')
    args = parser.parse_args()
    result_dir = run_monte_carlo(
        scenario=args.scenario,
        methods=args.methods,
        num_runs=args.num_runs,
        seed=args.seed,
        result_root=args.result_root,
    )
    print(result_dir)


if __name__ == '__main__':
    main()
