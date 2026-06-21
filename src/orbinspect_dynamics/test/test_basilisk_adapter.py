from orbinspect_dynamics.basilisk_adapter import basilisk_available


def test_basilisk_availability_check_returns_bool() -> None:
    assert isinstance(basilisk_available(), bool)
