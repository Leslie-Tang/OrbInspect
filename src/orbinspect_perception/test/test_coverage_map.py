from orbinspect_perception.coverage_map import CoverageMap
from orbinspect_perception.inspection_target_manager import InspectionTarget


def test_dwell_time_marks_target_inspected() -> None:
    target = InspectionTarget('target_1', (10.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    coverage = CoverageMap([target], dwell_time=1.0)

    visible_count, new_count = coverage.update({'target_1'}, 0.5)
    assert visible_count == 1
    assert new_count == 0
    assert coverage.coverage_ratio == 0.0

    visible_count, new_count = coverage.update({'target_1'}, 0.5)
    assert visible_count == 1
    assert new_count == 1
    assert coverage.coverage_ratio == 1.0
