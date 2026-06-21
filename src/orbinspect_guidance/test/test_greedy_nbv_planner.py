from orbinspect_guidance.greedy_nbv_planner import GreedyNBVPlanner
from orbinspect_guidance.waypoint_generator import CandidateWaypoint
from orbinspect_guidance.waypoint_generator import WaypointGenerator
from orbinspect_interfaces.msg import CoverageMap
from orbinspect_interfaces.msg import InspectionTarget


def test_waypoint_generator_returns_safe_candidates() -> None:
    generator = WaypointGenerator(
        radius_min=12.0,
        radius_max=16.0,
        radial_steps=2,
        azimuth_steps=8,
        elevation_steps=3,
    )

    candidates = generator.generate()

    assert candidates
    assert all(candidate.safety_margin >= 0.0 for candidate in candidates)


def test_greedy_planner_prefers_visible_gain() -> None:
    candidates = [
        CandidateWaypoint('near_target', (12.0, 0.0, 0.0), 10.0),
        CandidateWaypoint('away_from_target', (-12.0, 0.0, 0.0), 10.0),
    ]
    planner = GreedyNBVPlanner(candidates, sensor_range=25.0)
    coverage = CoverageMap()
    coverage.targets = [_target('target_001', (20.0, 0.0, 0.0), (-1.0, 0.0, 0.0))]

    decision = planner.select_next((0.0, 0.0, 0.0), coverage)

    assert decision.selected is not None
    assert decision.selected.candidate.waypoint_id == 'near_target'
    assert decision.selected.coverage_gain == 1


def test_greedy_planner_skips_visited_candidates() -> None:
    candidates = [
        CandidateWaypoint('first', (12.0, 0.0, 0.0), 10.0),
        CandidateWaypoint('second', (0.0, 12.0, 0.0), 10.0),
    ]
    planner = GreedyNBVPlanner(candidates, sensor_range=25.0)
    coverage = CoverageMap()

    decision = planner.select_next((0.0, 0.0, 0.0), coverage, {'first'})

    assert decision.selected is not None
    assert decision.selected.candidate.waypoint_id == 'second'


def _target(target_id: str, position, normal) -> InspectionTarget:
    msg = InspectionTarget()
    msg.target_id = target_id
    msg.position.x, msg.position.y, msg.position.z = position
    msg.normal.x, msg.normal.y, msg.normal.z = normal
    msg.inspected = False
    return msg
