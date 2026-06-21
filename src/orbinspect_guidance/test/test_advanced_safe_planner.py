from orbinspect_guidance.advanced_safe_planner import AdvancedSafePlanner
import pytest


def test_advanced_safe_planner_placeholder_is_unavailable() -> None:
    planner = AdvancedSafePlanner()

    assert not planner.available
    with pytest.raises(NotImplementedError):
        planner.plan()
