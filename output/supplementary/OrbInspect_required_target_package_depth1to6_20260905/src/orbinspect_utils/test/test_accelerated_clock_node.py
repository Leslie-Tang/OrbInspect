from orbinspect_utils.accelerated_clock_node import _clock_fields


def test_clock_fields_normalize_nanosecond_rounding() -> None:
    assert _clock_fields(12.25) == (12, 250_000_000)
    assert _clock_fields(1.9999999996) == (2, 0)
