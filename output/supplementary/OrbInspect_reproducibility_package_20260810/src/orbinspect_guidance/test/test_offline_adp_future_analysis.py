import pytest

from orbinspect_guidance.offline_adp_future_analysis import _apply_holm
from orbinspect_guidance.offline_adp_future_analysis import _two_sided_sign_test
from orbinspect_guidance.offline_adp_future_analysis import verify_reproducibility


def test_exact_sign_test_ignores_ties() -> None:
    assert _two_sided_sign_test(5, 0) == pytest.approx(0.0625)
    assert _two_sided_sign_test(0, 0) == 1.0


def test_holm_adjustment_is_monotone() -> None:
    comparisons = {
        'a': {'p': 0.001},
        'b': {'p': 0.02},
        'c': {'p': 0.04},
    }

    _apply_holm(comparisons, baselines=('a', 'b', 'c'), p_key='p')

    assert comparisons['a']['holm_adjusted_sign_test_p'] == pytest.approx(0.003)
    assert comparisons['b']['holm_adjusted_sign_test_p'] == pytest.approx(0.04)
    assert comparisons['c']['holm_adjusted_sign_test_p'] == pytest.approx(0.04)


def test_reproducibility_ignores_only_online_timing(tmp_path) -> None:
    original = tmp_path / 'original'
    rerun = tmp_path / 'rerun'
    for root, timing in ((original, '0.1'), (rerun, '0.2')):
        raw = root / 'raw'
        raw.mkdir(parents=True)
        (raw / 'heldout_results.csv').write_text(
            'split,scenario_id,method,success,online_time_s\n'
            f'test,s0,adaptive_rollout_adp,True,{timing}\n'
        )
        (raw / 'hcw_graph.json').write_text('{}')
        (raw / 'critic_checkpoint.json').write_text(
            '{"weights": [1.0], "training_time_s": 0.1}'
        )

    result = verify_reproducibility(original, rerun)

    assert result['verdict'] == 'REPRODUCIBLE'
    assert result['non_timing_cell_mismatches'] == 0
