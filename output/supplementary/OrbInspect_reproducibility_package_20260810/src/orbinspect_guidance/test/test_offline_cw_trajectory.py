from orbinspect_guidance.offline_cw_trajectory import OfflineCWTrajectoryGenerator


def test_offline_generator_creates_safe_waypoints() -> None:
    generator = _generator()

    waypoints = generator.generate_waypoints(
        inspection_radius=24.0,
        z_levels=[8.0],
        station_x_extent=36.0,
        station_y_offset=18.0,
    )

    assert len(waypoints) == 10
    assert all(generator.keepout.assess(waypoint).is_safe for waypoint in waypoints)


def test_offline_rollout_uses_cw_dynamics() -> None:
    generator = _generator()
    waypoints = [(-10.0, -18.0, 8.0), (10.0, -18.0, 8.0)]

    plan = generator.rollout((0.0, -35.0, 10.0, 0.0, 0.0, 0.0), waypoints)

    assert len(plan) > 2
    assert plan[-1].time > plan[0].time
    assert plan[-1].reference == waypoints[-1]
    assert any(abs(point.state[3]) > 0.0 for point in plan)


def test_recording_waypoints_cover_full_station_extent() -> None:
    generator = _generator()

    waypoints = generator.generate_waypoints(
        inspection_radius=30.0,
        z_levels=[8.0, 16.0, 24.0],
        station_x_extent=46.0,
        station_y_offset=30.0,
    )

    xs = [waypoint[0] for waypoint in waypoints]
    ys = [waypoint[1] for waypoint in waypoints]
    zs = [waypoint[2] for waypoint in waypoints]
    assert min(xs) <= -46.0
    assert max(xs) >= 46.0
    assert min(ys) <= -30.0
    assert max(ys) >= 30.0
    assert min(zs) == 8.0
    assert max(zs) == 24.0


def _generator() -> OfflineCWTrajectoryGenerator:
    return OfflineCWTrajectoryGenerator(
        mean_motion=0.0011313666536110225,
        max_acceleration=0.01,
        position_gain=0.00055,
        velocity_gain=0.055,
        integration_dt=1.0,
        segment_duration=20.0,
        safety_margin=2.0,
    )
