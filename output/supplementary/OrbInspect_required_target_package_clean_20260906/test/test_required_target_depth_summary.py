"""Verify fixed-cohort statistics for the extended manuscript depth diagnostic."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'OrbInspectLatex/scripts'
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location('depth_figures', SCRIPTS/'generate_required_target_depth_figures.py')
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def rows() -> list[dict]:
    """Create deterministic nonexperimental records for aggregation tests."""
    return [dict(adaptive_rollout_depth=depth, scenario_id=f'case_{i:02}', split='validation',
                 success=i >= 3, graph_cost=100.+depth, total_delta_v=10.+depth,
                 penalized_cost=1000. if i < 3 else 100.+depth,
                 online_time_s=depth*(1. if i < 3 else 2.), safe_action_evaluations=depth*100)
            for depth in range(1, 7) for i in range(12)]


def test_depth_summary_keeps_all_outcomes_and_shared_success_cohort() -> None:
    summary, common = MODULE.summarize(rows())
    assert len(common) == 9
    assert all(r['n'] == 12 and r['success_n'] == 9 for r in summary)
    assert summary[2]['mean_graph_cost'] == 103.
    assert summary[2]['median_time_s'] == 6.
    assert summary[2]['min_time_s'] == 3.
    assert summary[2]['max_time_s'] == 6.
    assert summary[5]['time_ratio_vs_depth3'] == 2.
    assert summary[5]['screen_ratio_vs_depth3'] == 2.
    # Increasing realized cost is reported, not forced to be monotonic decreasing.
    assert summary[5]['cost_difference_vs_depth3_pct'] > 0


def test_common_success_is_intersection_across_every_depth() -> None:
    sample = rows()
    sample[-1]['success'] = False
    summary, common = MODULE.summarize(sample)
    assert len(common) == 8
    assert summary[0]['success_n'] == 9
    assert summary[-1]['success_n'] == 8
    assert all(r['common_success_n'] == 8 for r in summary)


@pytest.mark.parametrize('kind', ['missing_depth', 'missing_case', 'duplicate_case', 'test_split'])
def test_invalid_depth_matrix_is_rejected(kind: str) -> None:
    sample = rows()
    if kind == 'missing_depth':
        sample = [r for r in sample if r['adaptive_rollout_depth'] != 6]
    elif kind == 'missing_case':
        sample.pop()
    elif kind == 'duplicate_case':
        sample[-1]['scenario_id'] = sample[-2]['scenario_id']
    else:
        sample[0]['split'] = 'test'
    with pytest.raises(ValueError):
        MODULE.summarize(sample)


@pytest.mark.parametrize('field,bad', [('method', 'seeded_local_search'), ('profile_id', 'required12'),
                                    ('scenario_seed', 999999), ('required_target_count', 6)])
def test_reused_names_cannot_mix_campaigns_or_methods(field: str, bad: str | int) -> None:
    sample = rows()
    scenarios = [dict(scenario_id=f'case_{i:02}', profile_id='required09', seed=100+i) for i in range(12)]
    manifest = dict(scenario_ids=[s['scenario_id'] for s in scenarios],
                    primary_profile='required09', required_target_ids=list(range(9)))
    for row in sample:
        row.update(method='adaptive_rollout_adp', profile_id='required09',
                   scenario_seed=100+int(row['scenario_id'][-2:]), required_target_count=9)
    MODULE.validate_provenance(sample, manifest, scenarios)
    sample[-1][field] = bad
    with pytest.raises(ValueError):
        MODULE.validate_provenance(sample, manifest, scenarios)
