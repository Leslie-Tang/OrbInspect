"""Run and aggregate the frozen paired ROS closed-loop campaign."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
from typing import Sequence

from orbinspect_guidance.ros_evidence_audit import audit_run


METHODS = ('adaptive_rollout_adp', 'local_search')


def run_campaign(
    input_dir: Path,
    campaign_id: str,
    splits: tuple[str, ...],
    methods: tuple[str, ...] = METHODS,
    time_scale: float = 10.0,
    resume: bool = True,
    fail_fast: bool = False,
    bag_runs: frozenset[str] = frozenset(),
) -> Path:
    """Execute selected routes sequentially and persist aggregate evidence."""
    input_dir = input_dir.resolve()
    manifest = json.loads((input_dir / 'manifest.json').read_text())
    routes = [
        route for route in manifest['routes']
        if route['split'] in splits and route['method'] in methods
    ]
    routes.sort(key=lambda route: (
        str(route['split']),
        str(route['scenario_id']),
        str(route['method']),
    ))
    if not routes:
        raise ValueError('campaign selection contains no routes')
    campaign_dir = Path('data/results').resolve() / campaign_id
    _create_campaign_layout(campaign_dir)
    shutil.copy2(
        input_dir / 'manifest.json',
        campaign_dir / 'config_snapshot' / 'input_manifest.json',
    )
    verification_config = (
        Path(__file__).resolve().parents[1] / 'config' / 'ros_verification.yaml'
    )
    if verification_config.is_file():
        shutil.copy2(
            verification_config,
            campaign_dir / 'config_snapshot' / 'ros_verification.yaml',
        )
    rows: list[dict[str, object]] = []
    for route in routes:
        scenario_id = str(route['scenario_id'])
        method = str(route['method'])
        run_id = f'{campaign_id}__{scenario_id}__{method}'
        result_dir = Path('data/results').resolve() / run_id
        audit_path = result_dir / 'mesh_execution_audit.json'
        if resume and audit_path.is_file():
            audit = json.loads(audit_path.read_text())
        else:
            if result_dir.exists():
                raise RuntimeError(
                    f'incomplete existing run blocks deterministic resume: {result_dir}'
                )
            command = [
                'ros2', 'launch', 'orbinspect_bringup',
                'ros_verification.launch.py',
                f'result_dir:={input_dir}',
                f'scenario_id:={scenario_id}',
                f'method:={method}',
                'publish_mode:=closed_loop',
                'record:=true',
                f'record_bag:={str(run_id in bag_runs).lower()}',
                'headless:=true',
                'save_figures:=false',
                f'time_scale:={time_scale}',
                f'run_id:={run_id}',
            ]
            completed = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            launch_output = completed.stdout or ''
            (result_dir / 'launch.log').write_text(launch_output)
            print(launch_output, end='')
            child_process_died = 'process has died' in launch_output
            if completed.returncode != 0 or child_process_died:
                raise RuntimeError(
                    f'ROS launch integrity failed '
                    f'(return={completed.returncode}, child_died={child_process_died}): '
                    f'{run_id}'
                )
            audit = audit_run(result_dir)
        rows.append(_campaign_row(route, result_dir, audit))
        _write_campaign_outputs(campaign_dir, manifest, rows, len(routes))
        if fail_fast and not bool(audit['passed']):
            raise RuntimeError(f'evidence gate failed: {run_id}')
    return campaign_dir


def _campaign_row(
    route: dict[str, object],
    result_dir: Path,
    audit: dict[str, object],
) -> dict[str, object]:
    summary = json.loads((result_dir / 'summary.json').read_text())
    verification = summary.get('verification', {})
    run_manifest = summary.get('run_manifest', {})
    execution = _execution_metrics(result_dir)
    return {
        'scenario_id': route['scenario_id'],
        'split': route['split'],
        'scenario_seed': route['scenario_seed'],
        'method': route['method'],
        'success': bool(audit['passed']),
        'terminal_success': bool(verification.get('success', False)),
        'coverage': float(verification.get('coverage_ratio', 0.0)),
        'credited_actions': int(verification.get('credited_actions', 0)),
        'failed_actions': int(verification.get('failed_actions', 0)),
        'cumulative_delta_v': float(summary['cumulative_delta_v']),
        'mean_position_tracking_error': float(
            summary['mean_position_tracking_error']
        ),
        'max_position_tracking_error': float(
            summary['max_position_tracking_error']
        ),
        'rms_position_tracking_error': execution['rms_tracking_error'],
        'filter_intervention_samples': execution['filter_interventions'],
        'minimum_mesh_clearance': float(audit['minimum_mesh_clearance_m']),
        'peak_safe_acceleration': float(audit['peak_safe_acceleration_mps2']),
        'surface_crossings': len(audit['surface_crossing_segment_indices']),
        'configuration_sha256': run_manifest.get('configuration_sha256', ''),
        'result_dir': str(result_dir),
    }


def _write_campaign_outputs(
    campaign_dir: Path,
    manifest: dict[str, object],
    rows: list[dict[str, object]],
    expected_runs: int,
) -> None:
    raw_path = campaign_dir / 'raw' / 'closed_loop_results.csv'
    with raw_path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    aggregates = _aggregate(rows)
    claim_gate = _claim_gate(aggregates, len(rows) == expected_runs)
    payload = {
        'schema_version': 'orbinspect-ros-verification-campaign/v1',
        'expected_runs': expected_runs,
        'completed_runs': len(rows),
        'complete': len(rows) == expected_runs,
        'all_gates_passed': (
            len(rows) == expected_runs
            and all(bool(row['success']) for row in rows)
        ),
        'claim_gate': claim_gate,
        'source_files_sha256': manifest['source_files_sha256'],
        'input_output_files_sha256': manifest['output_files_sha256'],
        'mesh_sha256': manifest['mesh_sha256'],
        'configuration_hashes': sorted({
            str(row['configuration_sha256']) for row in rows
            if row['configuration_sha256']
        }),
        'runtime_provenance': _runtime_provenance(),
        'aggregates': aggregates,
    }
    (campaign_dir / 'summary.json').write_text(
        json.dumps(payload, indent=2, sort_keys=True) + '\n'
    )
    lines = [
        '# Frozen ROS closed-loop campaign',
        '',
        f'- Completed runs: {len(rows)} / {expected_runs}',
        f"- All gates passed: {payload['all_gates_passed']}",
        '',
        '| Split | Method | n | Success | Mean coverage | Mean delta-v | '
        'Mean tracking error | Min clearance |',
        '|---|---|---:|---:|---:|---:|---:|---:|',
    ]
    for key, item in sorted(aggregates['by_split_method'].items()):
        split, method = key.split('/', 1)
        lines.append(
            f"| {split} | {method} | {item['n']} | "
            f"{item['success_count']} | {item['mean_coverage']:.6f} | "
            f"{item['mean_delta_v']:.6f} | "
            f"{item['mean_tracking_error']:.6f} | "
            f"{item['minimum_clearance']:.6f} |"
        )
    (campaign_dir / 'summary.md').write_text('\n'.join(lines) + '\n')


def _aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    by_scenario: dict[tuple[str, str], dict[str, dict[str, object]]] = defaultdict(dict)
    for row in rows:
        grouped[(str(row['split']), str(row['method']))].append(row)
        by_scenario[(str(row['split']), str(row['scenario_id']))][
            str(row['method'])
        ] = row
    by_split_method = {}
    for (split, method), items in grouped.items():
        successes = sum(bool(item['success']) for item in items)
        by_split_method[f'{split}/{method}'] = {
            'n': len(items),
            'success_count': successes,
            'success_rate': successes / len(items),
            'success_rate_wilson_95': _wilson(successes, len(items)),
            'mean_coverage': _mean(items, 'coverage'),
            'mean_delta_v': _mean(items, 'cumulative_delta_v'),
            'mean_tracking_error': _mean(
                items, 'mean_position_tracking_error'
            ),
            'mean_rms_tracking_error': _mean(
                items, 'rms_position_tracking_error'
            ),
            'mean_filter_interventions': _mean(
                items, 'filter_intervention_samples'
            ),
            'minimum_clearance': min(
                float(item['minimum_mesh_clearance']) for item in items
            ),
            'peak_safe_acceleration': max(
                float(item['peak_safe_acceleration']) for item in items
            ),
        }
    paired: dict[str, object] = {}
    for split in sorted({str(row['split']) for row in rows}):
        pairs = [
            methods for (item_split, _scenario), methods in by_scenario.items()
            if item_split == split and set(METHODS).issubset(methods)
        ]
        paired[split] = {
            'n': len(pairs),
            'mean_adp_minus_local_coverage': _paired_mean(
                pairs, 'coverage'
            ),
            'mean_adp_minus_local_delta_v': _paired_mean(
                pairs, 'cumulative_delta_v'
            ),
            'adp_success_count': sum(
                bool(pair[METHODS[0]]['success']) for pair in pairs
            ),
            'local_success_count': sum(
                bool(pair[METHODS[1]]['success']) for pair in pairs
            ),
            'delta_v_inference': _paired_inference(
                pairs,
                'cumulative_delta_v',
                9100 + sum(ord(character) for character in split),
            ),
            'tracking_error_inference': _paired_inference(
                pairs,
                'mean_position_tracking_error',
                9200 + sum(ord(character) for character in split),
            ),
        }
    return {'by_split_method': by_split_method, 'paired': paired}


def _claim_gate(
    aggregates: dict[str, object],
    complete: bool,
) -> dict[str, object]:
    paired = aggregates['paired'].get('test')
    if paired is None:
        return {
            'evaluated': False,
            'passed': False,
            'reason': 'complete test split required',
        }
    inference = paired['delta_v_inference']
    no_lower_success = (
        paired['adp_success_count'] >= paired['local_success_count']
    )
    upper_bound_below_zero = (
        inference is not None
        and float(inference['bootstrap_95_ci'][1]) < 0.0
    )
    return {
        'evaluated': complete,
        'passed': complete and no_lower_success and upper_bound_below_zero,
        'no_lower_adp_success': no_lower_success,
        'delta_v_bootstrap_upper_below_zero': upper_bound_below_zero,
    }


def _mean(rows: list[dict[str, object]], key: str) -> float:
    return sum(float(row[key]) for row in rows) / len(rows)


def _execution_metrics(result_dir: Path) -> dict[str, float | int]:
    with (result_dir / 'raw' / 'trajectory.csv').open(newline='') as handle:
        trajectory = list(csv.DictReader(handle))
    with (result_dir / 'raw' / 'safety.csv').open(newline='') as handle:
        safety = list(csv.DictReader(handle))
    errors = [
        float(row['position_tracking_error_norm']) for row in trajectory
    ]
    return {
        'rms_tracking_error': math.sqrt(
            sum(value * value for value in errors) / len(errors)
        ) if errors else 0.0,
        'filter_interventions': sum(
            row.get('filter_active') == 'True' for row in safety
        ),
    }


def _paired_mean(
    pairs: list[dict[str, dict[str, object]]],
    key: str,
) -> float | None:
    if not pairs:
        return None
    return sum(
        float(pair[METHODS[0]][key]) - float(pair[METHODS[1]][key])
        for pair in pairs
    ) / len(pairs)


def _wilson(successes: int, count: int) -> tuple[float, float]:
    z_value = 1.959963984540054
    proportion = successes / count
    denominator = 1.0 + z_value * z_value / count
    center = (
        proportion + z_value * z_value / (2.0 * count)
    ) / denominator
    radius = z_value / denominator * math.sqrt(
        proportion * (1.0 - proportion) / count
        + z_value * z_value / (4.0 * count * count)
    )
    return (center - radius, center + radius)


def _paired_inference(
    pairs: list[dict[str, dict[str, object]]],
    key: str,
    seed: int,
    draws: int = 10000,
) -> dict[str, object] | None:
    if not pairs:
        return None
    differences = [
        float(pair[METHODS[0]][key]) - float(pair[METHODS[1]][key])
        for pair in pairs
    ]
    mean_difference = sum(differences) / len(differences)
    generator = random.Random(seed)
    bootstrap = sorted(
        sum(generator.choice(differences) for _ in differences) / len(differences)
        for _ in range(draws)
    )
    tolerance = 1.0e-9
    wins = sum(value < -tolerance for value in differences)
    losses = sum(value > tolerance for value in differences)
    ties = len(differences) - wins - losses
    return {
        'mean_difference': mean_difference,
        'bootstrap_95_ci': (
            _percentile(bootstrap, 0.025),
            _percentile(bootstrap, 0.975),
        ),
        'wins_ties_losses': (wins, ties, losses),
        'exact_two_sided_sign_test_p': _sign_test(wins, losses),
        'bootstrap_draws': draws,
        'bootstrap_seed': seed,
    }


def _percentile(values: list[float], probability: float) -> float:
    position = probability * (len(values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction


def _sign_test(wins: int, losses: int) -> float:
    count = wins + losses
    if count == 0:
        return 1.0
    smaller = min(wins, losses)
    tail = sum(math.comb(count, index) for index in range(smaller + 1))
    return min(1.0, 2.0 * tail / (2**count))


def _create_campaign_layout(path: Path) -> None:
    for name in ('config_snapshot', 'raw', 'rosbag', 'figures', 'videos'):
        (path / name).mkdir(parents=True, exist_ok=True)


def _runtime_provenance() -> dict[str, object]:
    workspace = Path(__file__).resolve().parents[3]
    relative_files = (
        'src/orbinspect_bringup/launch/ros_verification.launch.py',
        'src/orbinspect_control/orbinspect_control/controller_node.py',
        'src/orbinspect_dynamics/orbinspect_dynamics/dynamics_node.py',
        'src/orbinspect_eval/orbinspect_eval/logger_node.py',
        'src/orbinspect_eval/orbinspect_eval/rosbag_manager.py',
        'src/orbinspect_guidance/config/ros_verification.yaml',
        'src/orbinspect_guidance/orbinspect_guidance/'
        'planned_trajectory_replay_node.py',
        'src/orbinspect_guidance/orbinspect_guidance/'
        'verification_evaluator_node.py',
        'src/orbinspect_guidance/orbinspect_guidance/ros_evidence_audit.py',
        'src/orbinspect_utils/orbinspect_utils/accelerated_clock_node.py',
    )
    source_hashes = {
        name: _sha256(workspace / name)
        for name in relative_files
        if (workspace / name).is_file()
    }
    return {
        'platform': platform.platform(),
        'python': sys.version,
        'ros_distro': os.environ.get('ROS_DISTRO', ''),
        'ros_version': os.environ.get('ROS_VERSION', ''),
        'cpu': platform.processor() or _cpu_model(),
        'git_revision': _command_output(('git', 'rev-parse', 'HEAD'), workspace),
        'git_status': _command_output(('git', 'status', '--short'), workspace),
        'source_sha256': source_hashes,
    }


def _cpu_model() -> str:
    path = Path('/proc/cpuinfo')
    if not path.is_file():
        return ''
    for line in path.read_text().splitlines():
        if line.lower().startswith('model name'):
            return line.split(':', 1)[1].strip()
    return ''


def _command_output(command: tuple[str, ...], cwd: Path) -> str:
    try:
        return subprocess.check_output(
            command,
            cwd=cwd,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return 'unknown'


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse campaign arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('input_dir', type=Path)
    parser.add_argument('--campaign-id', required=True)
    parser.add_argument('--split', action='append', required=True)
    parser.add_argument('--method', action='append', choices=METHODS)
    parser.add_argument('--time-scale', type=float, default=10.0)
    parser.add_argument('--no-resume', action='store_true')
    parser.add_argument('--fail-fast', action='store_true')
    parser.add_argument('--bag-run', action='append', default=[])
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the frozen campaign."""
    args = parse_args(argv)
    result = run_campaign(
        args.input_dir,
        args.campaign_id,
        tuple(args.split),
        tuple(args.method or METHODS),
        args.time_scale,
        not args.no_resume,
        args.fail_fast,
        frozenset(args.bag_run),
    )
    print(result)


if __name__ == '__main__':
    main()
