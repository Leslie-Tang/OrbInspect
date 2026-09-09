import math

from orbinspect_guidance.offline_sequence_improvement_study import (
    _latin_hypercube_initial_states,
)
from orbinspect_guidance.offline_sequence_improvement_study import _paired_endpoint
from orbinspect_guidance.offline_sequence_improvement_study import (
    _two_sided_sign_test,
)


def test_latin_hypercube_is_deterministic_and_bounded() -> None:
    arguments = {
        'nominal': (0.0, -35.0, 10.0, 0.0, 0.0, 0.0),
        'count': 20,
        'seed': 20260807,
        'position_half_width': (8.0, 6.0, 6.0),
        'velocity_half_width': (0.012, 0.012, 0.012),
    }

    first = _latin_hypercube_initial_states(**arguments)
    second = _latin_hypercube_initial_states(**arguments)

    assert first == second
    assert len(first) == 20
    assert all(len(state) == 6 for state in first)
    assert all(-8.0 < state[0] < 8.0 for state in first)
    assert len({state[0] for state in first}) == 20


def test_exact_sign_test_for_twenty_same_direction_pairs() -> None:
    assert math.isclose(
        _two_sided_sign_test(20, 0),
        2.0 / (2.0 ** 20),
    )


def test_paired_endpoint_preserves_pairing_and_direction() -> None:
    result = _paired_endpoint([-1.0, -2.0, -3.0], 1000, 42)

    assert result['pair_count'] == 3
    assert result['local_better_count'] == 3
    assert result['incumbent_better_count'] == 0
    assert result['mean_difference'] == -2.0
    lower, upper = result['bootstrap_95_percent_ci_for_mean']
    assert lower <= -2.0 <= upper
