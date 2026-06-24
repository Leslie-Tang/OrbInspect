import math

from orbinspect_control.lqr_controller import LQRController
import pytest


def test_controller_drives_toward_reference() -> None:
    controller = LQRController(
        position_gain=0.1,
        velocity_gain=0.2,
        max_acceleration=1.0,
    )

    command = controller.compute_control(
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [1.0, -2.0, 0.5],
    )

    assert command == pytest.approx((0.1, -0.2, 0.05))


def test_controller_damps_velocity() -> None:
    controller = LQRController(
        position_gain=0.0,
        velocity_gain=0.5,
        max_acceleration=1.0,
    )

    command = controller.compute_control(
        [0.0, 0.0, 0.0, 1.0, -1.0, 0.5],
        [0.0, 0.0, 0.0],
    )

    assert command == pytest.approx((-0.5, 0.5, -0.25))


def test_controller_tracks_reference_velocity_and_feedforward() -> None:
    controller = LQRController(
        position_gain=0.1,
        velocity_gain=0.5,
        max_acceleration=10.0,
    )

    command = controller.compute_control(
        [1.0, 0.0, 0.0, 0.2, 0.0, -0.1],
        [2.0, 0.0, 0.0],
        [0.6, 0.0, 0.1],
        [0.01, -0.02, 0.03],
    )

    assert command == pytest.approx((0.31, -0.02, 0.13))


def test_discrete_cw_lqr_drives_error_toward_zero() -> None:
    controller = LQRController(
        position_gain=0.1,
        velocity_gain=0.5,
        max_acceleration=1.0,
        controller_type='lqr',
        mean_motion=0.0011313666536110225,
        control_dt=0.1,
        state_weights=[1.0, 1.0, 1.0, 80.0, 80.0, 80.0],
        control_weights=[4000.0, 4000.0, 4000.0],
    )

    command = controller.compute_control(
        [10.0, -5.0, 2.0, 0.1, -0.2, 0.05],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
    )

    assert command[0] < 0.0
    assert command[1] > 0.0
    assert command[2] < 0.0


def test_discrete_cw_lqr_keeps_feedforward_acceleration() -> None:
    controller = LQRController(
        position_gain=0.0,
        velocity_gain=0.0,
        max_acceleration=1.0,
        controller_type='lqr',
        mean_motion=0.0011313666536110225,
        control_dt=0.1,
    )

    command = controller.compute_control(
        [1.0, 2.0, 3.0, 0.1, 0.2, 0.3],
        [1.0, 2.0, 3.0],
        [0.1, 0.2, 0.3],
        [0.01, 0.02, 0.03],
    )

    assert command == pytest.approx((0.01, 0.02, 0.03), abs=1.0e-10)


def test_discrete_cw_mpc_respects_acceleration_bound() -> None:
    controller = LQRController(
        position_gain=0.1,
        velocity_gain=0.5,
        max_acceleration=0.05,
        controller_type='mpc',
        mean_motion=0.0011313666536110225,
        control_dt=0.1,
        state_weights=[1.0, 1.0, 1.0, 80.0, 80.0, 80.0],
        control_weights=[400.0, 400.0, 400.0],
        mpc_horizon=4,
        mpc_max_iterations=20,
    )

    command = controller.compute_control(
        [20.0, -10.0, 5.0, 0.2, -0.1, 0.05],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
    )

    assert math.sqrt(sum(value * value for value in command)) <= 0.05 + 1.0e-9


def test_discrete_cw_mpc_keeps_zero_error_feedforward() -> None:
    controller = LQRController(
        position_gain=0.0,
        velocity_gain=0.0,
        max_acceleration=0.5,
        controller_type='mpc',
        mean_motion=0.0011313666536110225,
        control_dt=0.1,
        mpc_horizon=3,
        mpc_max_iterations=12,
    )

    command = controller.compute_control(
        [1.0, 2.0, 3.0, 0.1, 0.2, 0.3],
        [1.0, 2.0, 3.0],
        [0.1, 0.2, 0.3],
        [0.01, -0.02, 0.03],
    )

    assert command == pytest.approx((0.01, -0.02, 0.03), abs=1.0e-7)


def test_controller_enforces_max_acceleration() -> None:
    controller = LQRController(
        position_gain=10.0,
        velocity_gain=0.0,
        max_acceleration=0.01,
    )

    command = controller.compute_control(
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
    )
    norm = math.sqrt(sum(value * value for value in command))

    assert norm == pytest.approx(0.01)


def test_invalid_dimensions_raise_value_error() -> None:
    controller = LQRController(
        position_gain=0.1,
        velocity_gain=0.1,
        max_acceleration=1.0,
    )

    with pytest.raises(ValueError):
        controller.compute_control([0.0] * 5, [0.0, 0.0, 0.0])

    with pytest.raises(ValueError):
        controller.compute_control([0.0] * 6, [0.0, 0.0])
