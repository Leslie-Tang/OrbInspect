from orbinspect_perception.inspection_target_manager import InspectionTargetManager


def test_generate_targets_returns_station_surface_targets() -> None:
    targets = InspectionTargetManager(spacing=12.0).generate_targets()

    assert targets
    assert all(target.target_id for target in targets)
    assert any(target.position[0] > 30.0 for target in targets)
