from orbinspect_safety.collision_checker import CollisionChecker
from orbinspect_safety.projection_filter import ProjectionSafetyFilter


def test_collision_checker_reports_positive_clearance_far_from_station() -> None:
    checker = CollisionChecker()

    assessment = checker.assess((0.0, -20.0, 6.0))

    assert assessment.minimum_distance > assessment.safety_margin
    assert assessment.is_safe


def test_collision_checker_reports_unsafe_inside_truss_keepout() -> None:
    checker = CollisionChecker()

    assessment = checker.assess((0.0, 0.0, 0.0))

    assert assessment.minimum_distance < 0.0
    assert not assessment.is_safe


def test_projection_filter_removes_inward_command_near_station() -> None:
    safety_filter = ProjectionSafetyFilter(max_acceleration=0.01)

    result = safety_filter.filter_command(
        position=(20.0, -4.5, 0.0),
        velocity=(0.0, 0.0, 0.0),
        command=(0.0, 0.005, 0.0),
    )

    assert result.modified
    assert result.command[1] <= 0.0


def test_projection_filter_limits_acceleration_norm() -> None:
    safety_filter = ProjectionSafetyFilter(max_acceleration=0.01)

    result = safety_filter.filter_command(
        position=(0.0, -20.0, 6.0),
        velocity=(0.0, 0.0, 0.0),
        command=(0.1, 0.0, 0.0),
    )

    assert abs(result.command[0] - 0.01) < 1.0e-12
