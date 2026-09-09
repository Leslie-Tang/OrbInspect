import csv
import json
from pathlib import Path

from orbinspect_guidance.offline_adp_validation_decision import (
    aggregate_validation_decision,
)
from orbinspect_guidance.offline_adp_validation_decision import ValidationCandidate


def test_validation_gate_withholds_test_for_losing_candidate(tmp_path: Path) -> None:
    source = tmp_path / 'source'
    raw = source / 'raw'
    raw.mkdir(parents=True)
    _write_csv(raw / 'heldout_results.csv', [
        _result_row('validation_000', 'frozen_adp', False, 120.0, 0.01),
        _result_row('validation_000', 'local_search', True, 70.0, 0.02),
        _result_row('validation_001', 'frozen_adp', True, 90.0, 0.01),
        _result_row('validation_001', 'local_search', True, 75.0, 0.02),
    ])
    _write_csv(raw / 'heldout_summary.csv', [
        _summary_row('frozen_adp', 0.5, 105.0, 0.01),
        _summary_row('local_search', 1.0, 72.5, 0.02),
    ])
    candidate = ValidationCandidate(
        candidate_id='losing_candidate',
        label='Losing candidate',
        regime='test regime',
        result_dir=source,
    )

    result_dir = aggregate_validation_decision(
        tmp_path,
        'decision',
        candidates=(candidate,),
    )

    summary = json.loads((result_dir / 'summary.json').read_text())
    assert summary['qualified_candidate_ids'] == []
    assert summary['test_evaluation_status'] == 'withheld_no_validation_candidate'
    assert not summary['superiority_demonstrated']
    assert (result_dir / 'raw' / 'validation_candidates.csv').is_file()
    assert (result_dir / 'raw' / 'full_graph_paired_costs.csv').is_file()
    assert (result_dir / 'raw' / 'full_graph_methods.csv').is_file()


def _result_row(
    scenario_id: str,
    method: str,
    success: bool,
    penalized_cost: float,
    online_time_s: float,
) -> dict[str, object]:
    return {
        'split': 'validation',
        'scenario_id': scenario_id,
        'method': method,
        'success': success,
        'penalized_cost': penalized_cost,
        'online_time_s': online_time_s,
    }


def _summary_row(
    method: str,
    success_rate: float,
    mean_penalized_cost: float,
    median_online_time_s: float,
) -> dict[str, object]:
    return {
        'split': 'validation',
        'method': method,
        'n': 2,
        'success_rate': success_rate,
        'mean_penalized_cost': mean_penalized_cost,
        'median_online_time_s': median_online_time_s,
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
