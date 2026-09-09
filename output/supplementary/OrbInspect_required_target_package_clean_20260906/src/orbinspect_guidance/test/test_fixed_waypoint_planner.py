from orbinspect_guidance.fixed_waypoint_planner import FixedWaypointPlanner


def test_fixed_waypoint_planner_loads_waypoints() -> None:
    planner = FixedWaypointPlanner([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

    assert len(planner.waypoints) == 2
    assert planner.waypoints[0].waypoint_id == 'wp_000'
    assert planner.waypoints[1].position == (4.0, 5.0, 6.0)
