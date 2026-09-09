"""Tests for closed-loop observation credit gates."""

from orbinspect_guidance.verification_evaluator_node import evaluate_observation


def test_credits_observation_at_declared_limits() -> None:
    """Accept tracking exactly on both predeclared tolerances."""
    result = evaluate_observation(
        executed=(0.5, 0.0, 0.0, 0.05, 0.0, 0.0),
        planned=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        position_tolerance=0.5,
        velocity_tolerance=0.05,
    )

    assert result['credited']
    assert result['position_error'] == 0.5
    assert result['terminal_speed'] == 0.05


def test_rejects_observation_for_position_error() -> None:
    """Reject a terminal state outside the position gate."""
    result = evaluate_observation(
        executed=(0.5001, 0.0, 0.0, 0.0, 0.0, 0.0),
        planned=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        position_tolerance=0.5,
        velocity_tolerance=0.05,
    )

    assert not result['credited']


def test_rejects_observation_for_terminal_speed() -> None:
    """Reject a terminal state outside the speed gate."""
    result = evaluate_observation(
        executed=(0.0, 0.0, 0.0, 0.0, 0.0501, 0.0),
        planned=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        position_tolerance=0.5,
        velocity_tolerance=0.05,
    )

    assert not result['credited']
