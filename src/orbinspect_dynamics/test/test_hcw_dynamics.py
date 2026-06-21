import math

from orbinspect_dynamics.hcw_dynamics import HCWDynamics
import pytest


MEAN_MOTION = math.sqrt(3.986004418e14 / (6378137.0 + 400000.0) ** 3)


def test_derivative_dimensions() -> None:
    dynamics = HCWDynamics(MEAN_MOTION)

    derivative = dynamics.derivative(
        [1.0, 2.0, 3.0, 0.1, 0.2, 0.3],
        [0.01, 0.02, 0.03],
    )

    assert len(derivative) == 6
    assert all(isinstance(value, float) for value in derivative)


def test_zero_input_stationary_in_plane_state_remains_stationary() -> None:
    dynamics = HCWDynamics(MEAN_MOTION)

    next_state = dynamics.rk4_step(
        [0.0, -35.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        1.0,
    )

    assert next_state == pytest.approx(
        (0.0, -35.0, 0.0, 0.0, 0.0, 0.0),
        abs=1.0e-12,
    )


def test_zero_input_propagation_is_bounded_over_short_horizon() -> None:
    dynamics = HCWDynamics(MEAN_MOTION)
    state = (0.0, -35.0, 10.0, 0.0, 0.0, 0.0)

    for _ in range(200):
        state = dynamics.rk4_step(state, [0.0, 0.0, 0.0], 0.1)

    position_norm = math.sqrt(state[0] ** 2 + state[1] ** 2 + state[2] ** 2)
    velocity_norm = math.sqrt(state[3] ** 2 + state[4] ** 2 + state[5] ** 2)

    assert position_norm < 40.0
    assert velocity_norm < 0.02


def test_invalid_dimensions_raise_value_error() -> None:
    dynamics = HCWDynamics(MEAN_MOTION)

    with pytest.raises(ValueError):
        dynamics.derivative([0.0] * 5, [0.0, 0.0, 0.0])

    with pytest.raises(ValueError):
        dynamics.derivative([0.0] * 6, [0.0, 0.0])
