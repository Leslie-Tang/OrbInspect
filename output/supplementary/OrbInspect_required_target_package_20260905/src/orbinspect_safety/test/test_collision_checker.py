from orbinspect_safety.collision_checker import CollisionChecker
from orbinspect_safety.keepout_zones import KeepoutZoneModel
from orbinspect_safety.primitive_geometry import OrientedBoxPrimitive
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


def test_oriented_box_distance_respects_rotated_axes() -> None:
    box = OrientedBoxPrimitive(
        'rotated',
        (1.0, 2.0, 3.0),
        (2.0, 4.0, 6.0),
        ((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    )

    assessment = box.distance_to((1.0, 4.0, 3.0))

    assert abs(assessment.distance - 1.0) < 1.0e-12
    assert assessment.direction == (0.0, 1.0, 0.0)
    assert assessment.closest_point == (1.0, 3.0, 3.0)


def test_rotated_s4_array_covers_previously_missed_collision() -> None:
    assessment = KeepoutZoneModel().assess(
        (-2.7532443751, 17.4497723870, 40.5217144738)
    )

    assert assessment.surface_distance.primitive_name == 's4_array_port'
    assert assessment.minimum_distance < 0.0
    assert not assessment.is_safe


def test_vehicle_radius_is_included_in_clearance() -> None:
    model = KeepoutZoneModel(
        primitives=(
            OrientedBoxPrimitive(
                'box',
                (0.0, 0.0, 0.0),
                (2.0, 2.0, 2.0),
                ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            ),
        ),
        safety_margin=2.0,
        caution_margin=8.0,
        vehicle_radius=0.75,
    )

    assessment = model.assess((4.0, 0.0, 0.0))

    assert assessment.minimum_distance == 3.0
    assert assessment.body_clearance == 2.25
    assert assessment.clearance == 0.25
