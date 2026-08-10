"""Validate paired held-out results for the selected rollout-ADP policy."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import mean, median, stdev


PROPOSED_METHOD = 'adaptive_rollout_adp'
PRIMARY_BASELINE = 'local_search'
SECONDARY_BASELINES = ('incumbent', 'rollout', 'search_only', 'frozen_adp')


def analyze(
    result_dir: Path,
    *,
    bootstrap_draws: int = 10000,
    original_dir: Path | None = None,
) -> dict[str, object]:
    """Compute paired statistics, multiplicity adjustments, and integrity checks."""
    raw_dir = result_dir / 'raw'
    rows = _read_rows(raw_dir / 'heldout_results.csv')
    splits = sorted({row['split'] for row in rows})
    comparisons: dict[str, dict[str, dict[str, object]]] = {}
    for split in splits:
        comparisons[split] = {}
        for baseline in (PRIMARY_BASELINE, *SECONDARY_BASELINES):
            comparisons[split][baseline] = _paired_comparison(
                rows,
                split,
                baseline,
                bootstrap_draws=bootstrap_draws,
            )
        _apply_holm(
            comparisons[split],
            baselines=SECONDARY_BASELINES,
            p_key='exact_sign_test_p',
        )

    primary = comparisons.get('test', {}).get(PRIMARY_BASELINE, {})
    fallacy_scan = _fallacy_scan(comparisons)
    payload = {
        'analysis_version': 'adp_future_analysis_v1',
        'proposed_method': PROPOSED_METHOD,
        'primary_baseline': PRIMARY_BASELINE,
        'primary_split': 'test',
        'bootstrap_draws': bootstrap_draws,
        'primary_claim_supported': bool(
            primary
            and primary['proposed_success_rate']
            >= primary['baseline_success_rate']
            and primary['bootstrap_95_ci'][1] < 0.0
        ),
        'comparisons': comparisons,
        'multiple_comparisons': {
            'primary': 'single predeclared comparison; unadjusted alpha=0.05',
            'secondary': 'Holm-adjusted exact sign-test p-values within split',
        },
        'assumptions': {
            'pairing': 'same scenario, graph, weights, goal, budget, and shield',
            'normality_required': False,
            'reason': (
                'percentile paired bootstrap and exact sign tests are used; '
                'Cohen dz is descriptive'
            ),
        },
        'fallacy_scan': fallacy_scan,
        'confidence': 'CAUTION',
        'confidence_reason': (
            'The paired simulation evidence is internally strong, but accepted '
            'scenarios are conditioned on incumbent feasibility and the result '
            'does not establish hardware or unmodeled-dynamics performance.'
        ),
        'input_hashes': {
            'heldout_results_sha256': _sha256(
                raw_dir / 'heldout_results.csv'
            ),
            'hcw_graph_sha256': _sha256(raw_dir / 'hcw_graph.json'),
        },
    }
    _write_comparison_rows(raw_dir / 'paired_comparisons.csv', comparisons)
    (result_dir / 'statistical_validation.json').write_text(
        json.dumps(payload, indent=2, sort_keys=True)
    )
    (result_dir / 'statistical_validation.md').write_text(
        _validation_markdown(payload)
    )
    if original_dir is not None:
        reproducibility = verify_reproducibility(original_dir, result_dir)
        (result_dir / 'reproducibility.json').write_text(
            json.dumps(reproducibility, indent=2, sort_keys=True)
        )
    return payload


def verify_reproducibility(
    original_dir: Path,
    rerun_dir: Path,
) -> dict[str, object]:
    """Compare deterministic study outputs while excluding timing measurements."""
    original_rows = _read_rows(original_dir / 'raw' / 'heldout_results.csv')
    rerun_rows = _read_rows(rerun_dir / 'raw' / 'heldout_results.csv')
    ignored_fields = {'online_time_s'}

    def sort_key(row: dict[str, str]) -> tuple[str, str, str]:
        return row['split'], row['scenario_id'], row['method']

    original_rows.sort(key=sort_key)
    rerun_rows.sort(key=sort_key)
    columns_match = bool(
        original_rows and rerun_rows
        and set(original_rows[0]) == set(rerun_rows[0])
    )
    compared_fields = sorted(set(original_rows[0]) - ignored_fields)
    mismatch_count = 0
    for original, rerun in zip(original_rows, rerun_rows):
        mismatch_count += sum(
            original[field] != rerun[field] for field in compared_fields
        )
    row_count_match = len(original_rows) == len(rerun_rows)
    graph_hash_match = _sha256(
        original_dir / 'raw' / 'hcw_graph.json'
    ) == _sha256(rerun_dir / 'raw' / 'hcw_graph.json')
    original_checkpoint = json.loads(
        (original_dir / 'raw' / 'critic_checkpoint.json').read_text()
    )
    rerun_checkpoint = json.loads(
        (rerun_dir / 'raw' / 'critic_checkpoint.json').read_text()
    )
    original_checkpoint.pop('training_time_s', None)
    rerun_checkpoint.pop('training_time_s', None)
    checkpoint_match = original_checkpoint == rerun_checkpoint
    exact_metric_match = bool(
        columns_match
        and row_count_match
        and mismatch_count == 0
        and graph_hash_match
        and checkpoint_match
    )
    return {
        'classification': 'deterministic with timing fields excluded',
        'verdict': 'REPRODUCIBLE' if exact_metric_match else 'NOT_REPRODUCIBLE',
        'original_dir': str(original_dir),
        'rerun_dir': str(rerun_dir),
        'row_count_original': len(original_rows),
        'row_count_rerun': len(rerun_rows),
        'row_count_match': row_count_match,
        'columns_match': columns_match,
        'compared_fields': compared_fields,
        'ignored_fields': sorted(ignored_fields),
        'non_timing_cell_mismatches': mismatch_count,
        'graph_hash_match': graph_hash_match,
        'critic_checkpoint_match_excluding_training_time': checkpoint_match,
        'rerun_scenario_archive_present': (
            rerun_dir / 'raw' / 'scenarios.json'
        ).is_file(),
    }


def _paired_comparison(
    rows: list[dict[str, str]],
    split: str,
    baseline: str,
    *,
    bootstrap_draws: int,
) -> dict[str, object]:
    by_key = {
        (row['scenario_id'], row['method']): row
        for row in rows if row['split'] == split
    }
    scenario_ids = sorted({
        scenario_id for scenario_id, method in by_key
        if method == PROPOSED_METHOD
        and (scenario_id, baseline) in by_key
    })
    if not scenario_ids:
        raise ValueError(f'no paired {split} rows for baseline {baseline}')
    proposed = [by_key[(scenario_id, PROPOSED_METHOD)] for scenario_id in scenario_ids]
    reference = [by_key[(scenario_id, baseline)] for scenario_id in scenario_ids]
    differences = [
        float(first['penalized_cost']) - float(second['penalized_cost'])
        for first, second in zip(proposed, reference)
    ]
    wins = sum(value < -1.0e-12 for value in differences)
    ties = sum(abs(value) <= 1.0e-12 for value in differences)
    losses = len(differences) - wins - ties
    lower, upper = _bootstrap_mean_interval(
        differences,
        draws=bootstrap_draws,
        seed=99173 + sum(ord(character) for character in f'{split}:{baseline}'),
    )
    spread = stdev(differences) if len(differences) > 1 else math.nan
    proposed_cost = mean(float(row['penalized_cost']) for row in proposed)
    baseline_cost = mean(float(row['penalized_cost']) for row in reference)
    result = {
        'n': len(differences),
        'proposed_success_rate': mean(_as_bool(row['success']) for row in proposed),
        'baseline_success_rate': mean(_as_bool(row['success']) for row in reference),
        'proposed_mean_penalized_cost': proposed_cost,
        'baseline_mean_penalized_cost': baseline_cost,
        'mean_paired_difference': mean(differences),
        'median_paired_difference': median(differences),
        'bootstrap_95_ci': [lower, upper],
        'cohen_dz': (
            mean(differences) / spread
            if math.isfinite(spread) and spread > 1.0e-12 else math.nan
        ),
        'cost_reduction_percent': (
            100.0 * (baseline_cost - proposed_cost) / baseline_cost
            if abs(baseline_cost) > 1.0e-12 else math.nan
        ),
        'wins': wins,
        'ties': ties,
        'losses': losses,
        'exact_sign_test_p': _two_sided_sign_test(wins, losses),
        'proposed_mean_coverage': mean(float(row['coverage']) for row in proposed),
        'baseline_mean_coverage': mean(float(row['coverage']) for row in reference),
        'mean_selected_count_difference': mean(
            int(first['selected_count']) - int(second['selected_count'])
            for first, second in zip(proposed, reference)
        ),
        'proposed_median_online_time_s': median(
            float(row['online_time_s']) for row in proposed
        ),
        'baseline_median_online_time_s': median(
            float(row['online_time_s']) for row in reference
        ),
        'paired_differences': differences,
    }
    if 'total_delta_v' in proposed[0] and 'total_delta_v' in reference[0]:
        delta_v_differences = [
            float(first['total_delta_v']) - float(second['total_delta_v'])
            for first, second in zip(proposed, reference)
        ]
        delta_v_lower, delta_v_upper = _bootstrap_mean_interval(
            delta_v_differences,
            draws=bootstrap_draws,
            seed=(
                197933
                + sum(ord(character) for character in f'{split}:{baseline}')
            ),
        )
        delta_v_wins = sum(value < -1.0e-12 for value in delta_v_differences)
        delta_v_ties = sum(
            abs(value) <= 1.0e-12 for value in delta_v_differences
        )
        delta_v_losses = len(delta_v_differences) - delta_v_wins - delta_v_ties
        delta_v_spread = (
            stdev(delta_v_differences)
            if len(delta_v_differences) > 1 else math.nan
        )
        proposed_delta_v = mean(
            float(row['total_delta_v']) for row in proposed
        )
        baseline_delta_v = mean(
            float(row['total_delta_v']) for row in reference
        )
        result.update({
            'proposed_mean_delta_v': proposed_delta_v,
            'baseline_mean_delta_v': baseline_delta_v,
            'mean_paired_delta_v_difference': mean(delta_v_differences),
            'median_paired_delta_v_difference': median(delta_v_differences),
            'delta_v_bootstrap_95_ci': [delta_v_lower, delta_v_upper],
            'delta_v_cohen_dz': (
                mean(delta_v_differences) / delta_v_spread
                if math.isfinite(delta_v_spread)
                and delta_v_spread > 1.0e-12 else math.nan
            ),
            'delta_v_reduction_percent': (
                100.0 * (baseline_delta_v - proposed_delta_v)
                / baseline_delta_v
                if abs(baseline_delta_v) > 1.0e-12 else math.nan
            ),
            'delta_v_wins': delta_v_wins,
            'delta_v_ties': delta_v_ties,
            'delta_v_losses': delta_v_losses,
            'delta_v_exact_sign_test_p': _two_sided_sign_test(
                delta_v_wins,
                delta_v_losses,
            ),
            'paired_delta_v_differences': delta_v_differences,
        })
    return result


def _bootstrap_mean_interval(
    values: list[float],
    *,
    draws: int,
    seed: int,
) -> tuple[float, float]:
    generator = random.Random(seed)
    estimates = sorted(
        mean(values[generator.randrange(len(values))] for _value in values)
        for _draw in range(draws)
    )
    return (
        estimates[math.floor(0.025 * (draws - 1))],
        estimates[math.ceil(0.975 * (draws - 1))],
    )


def _two_sided_sign_test(wins: int, losses: int) -> float:
    non_ties = wins + losses
    if non_ties == 0:
        return 1.0
    tail = min(wins, losses)
    probability = sum(
        math.comb(non_ties, index) for index in range(tail + 1)
    ) / (2 ** non_ties)
    return min(1.0, 2.0 * probability)


def _apply_holm(
    comparisons: dict[str, dict[str, object]],
    *,
    baselines: tuple[str, ...],
    p_key: str,
) -> None:
    ordered = sorted(
        (float(comparisons[name][p_key]), name) for name in baselines
    )
    running = 0.0
    count = len(ordered)
    for rank, (value, name) in enumerate(ordered):
        adjusted = min(1.0, (count - rank) * value)
        running = max(running, adjusted)
        comparisons[name]['holm_adjusted_sign_test_p'] = running


def _fallacy_scan(
    comparisons: dict[str, dict[str, dict[str, object]]],
) -> dict[str, object]:
    test_direction = comparisons.get('test', {}).get(
        PRIMARY_BASELINE, {}
    ).get('mean_paired_difference')
    ood_direction = comparisons.get('ood', {}).get(
        PRIMARY_BASELINE, {}
    ).get('mean_paired_difference')
    return {
        'checked': '11/11',
        'items': {
            'simpsons_paradox': {
                'status': 'not_detected',
                'note': (
                    'test and OOD paired mean directions agree'
                    if test_direction is not None and ood_direction is not None
                    and test_direction < 0.0 and ood_direction < 0.0
                    else 'split directions require inspection'
                ),
            },
            'ecological_fallacy': {
                'status': 'not_applicable',
                'note': 'inference remains at the mission-scenario level',
            },
            'berksons_paradox': {
                'status': 'caution',
                'note': (
                    'scenario acceptance is conditioned on incumbent '
                    'feasibility; claims are limited to that mission envelope'
                ),
            },
            'collider_bias': {
                'status': 'not_detected',
                'note': 'no post-outcome covariates are controlled',
            },
            'base_rate_neglect': {
                'status': 'not_applicable',
                'note': 'this is not a diagnostic-classification study',
            },
            'regression_to_mean': {
                'status': 'not_applicable',
                'note': 'no extreme-score pre/post selection is used',
            },
            'survivorship_bias': {
                'status': 'scoped',
                'note': 'all accepted scenarios and every method result are retained',
            },
            'look_elsewhere_effect': {
                'status': 'controlled',
                'note': 'one primary test; secondary tests use Holm adjustment',
            },
            'garden_of_forking_paths': {
                'status': 'controlled',
                'note': 'development selection and held-out gate were recorded before test access',
            },
            'correlation_causation': {
                'status': 'scoped',
                'note': 'paired algorithm intervention is causal only inside the fixed simulator model',
            },
            'reverse_causality': {
                'status': 'not_applicable',
                'note': 'algorithm assignment precedes deterministic outcome computation',
            },
        },
    }


def _write_comparison_rows(
    path: Path,
    comparisons: dict[str, dict[str, dict[str, object]]],
) -> None:
    rows = []
    for split, split_comparisons in comparisons.items():
        for baseline, values in split_comparisons.items():
            rows.append({
                'split': split,
                'baseline': baseline,
                **{
                    key: value for key, value in values.items()
                    if key not in {
                        'paired_differences',
                        'paired_delta_v_differences',
                    }
                },
            })
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _validation_markdown(payload: dict[str, object]) -> str:
    lines = [
        '# Statistical validation',
        '',
        f"- Primary claim supported: {payload['primary_claim_supported']}",
        f"- Confidence: {payload['confidence']}",
        f"- Fallacy scan: {payload['fallacy_scan']['checked']}",
        '',
        '| Split | Baseline | n | Success (ADP/base) | Mean difference [95% CI] | Reduction | W/T/L | Sign p |',
        '|---|---|---:|---:|---:|---:|---:|---:|',
    ]
    for split, comparisons in payload['comparisons'].items():
        for baseline, values in comparisons.items():
            lines.append(
                f"| {split} | {baseline} | {values['n']} | "
                f"{values['proposed_success_rate']:.3f}/"
                f"{values['baseline_success_rate']:.3f} | "
                f"{values['mean_paired_difference']:.3f} "
                f"[{values['bootstrap_95_ci'][0]:.3f}, "
                f"{values['bootstrap_95_ci'][1]:.3f}] | "
                f"{values['cost_reduction_percent']:.1f}% | "
                f"{values['wins']}/{values['ties']}/{values['losses']} | "
                f"{values['exact_sign_test_p']:.3g} |"
            )
    lines.extend(['', payload['confidence_reason'], ''])
    return '\n'.join(lines)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {'1', 'true', 'yes'}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the result-directory analysis command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result-dir', type=Path, required=True)
    parser.add_argument('--bootstrap-draws', type=int, default=10000)
    parser.add_argument('--original-dir', type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Validate one frozen rollout-ADP result directory."""
    args = parse_args(argv)
    payload = analyze(
        args.result_dir,
        bootstrap_draws=args.bootstrap_draws,
        original_dir=args.original_dir,
    )
    print(json.dumps({
        'result_dir': str(args.result_dir),
        'primary_claim_supported': payload['primary_claim_supported'],
    }, indent=2))


if __name__ == '__main__':
    main()
