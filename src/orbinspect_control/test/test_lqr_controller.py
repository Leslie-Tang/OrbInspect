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
