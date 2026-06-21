from orbinspect_eval.metrics import delta_v_increment
from orbinspect_eval.metrics import is_saturated
from orbinspect_eval.metrics import tracking_error_norm
from orbinspect_eval.metrics import vector_norm
import pytest


def test_vector_norm() -> None:
    assert vector_norm([3.0, 4.0, 0.0]) == pytest.approx(5.0)


def test_tracking_error_norm() -> None:
    assert tracking_error_norm([1.0, 2.0, 3.0], [4.0, 6.0, 3.0]) == pytest.approx(5.0)


def test_delta_v_increment() -> None:
    assert delta_v_increment(0.01, 2.5) == pytest.approx(0.025)


def test_is_saturated() -> None:
    assert is_saturated(0.01, 0.01)
    assert not is_saturated(0.005, 0.01)


def test_invalid_metrics_inputs_raise_value_error() -> None:
    with pytest.raises(ValueError):
        tracking_error_norm([0.0, 0.0], [0.0, 0.0, 0.0])
    with pytest.raises(ValueError):
        delta_v_increment(-1.0, 1.0)
    with pytest.raises(ValueError):
        is_saturated(0.0, 0.0)
