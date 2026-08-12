from orbinspect_guidance.ros_verification_campaign import _aggregate


def test_aggregate_preserves_pairing_and_success_intervals() -> None:
    rows = [
        _row('test_000', 'adaptive_rollout_adp', True, 0.82, 10.0),
        _row('test_000', 'local_search', True, 0.81, 11.0),
        _row('test_001', 'adaptive_rollout_adp', False, 0.70, 12.0),
        _row('test_001', 'local_search', True, 0.80, 13.0),
    ]

    result = _aggregate(rows)

    adp = result['by_split_method']['test/adaptive_rollout_adp']
    assert adp['n'] == 2
    assert adp['success_rate'] == 0.5
    assert 0.0 < adp['success_rate_wilson_95'][0] < 0.5
    assert result['paired']['test']['n'] == 2
    assert result['paired']['test']['mean_adp_minus_local_delta_v'] == -1.0
    inference = result['paired']['test']['delta_v_inference']
    assert inference['mean_difference'] == -1.0
    assert inference['bootstrap_95_ci'] == (-1.0, -1.0)
    assert inference['wins_ties_losses'] == (2, 0, 0)
    assert inference['exact_two_sided_sign_test_p'] == 0.5


def _row(scenario, method, success, coverage, delta_v):
    return {
        'scenario_id': scenario,
        'split': 'test',
        'method': method,
        'success': success,
        'coverage': coverage,
        'cumulative_delta_v': delta_v,
        'mean_position_tracking_error': 0.1,
        'rms_position_tracking_error': 0.2,
        'filter_intervention_samples': 3,
        'minimum_mesh_clearance': 0.05,
        'peak_safe_acceleration': 0.06,
    }
