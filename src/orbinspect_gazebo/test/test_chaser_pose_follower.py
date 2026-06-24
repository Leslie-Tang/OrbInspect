from orbinspect_gazebo.chaser_pose_follower import ChaserPoseFollower


def test_format_values_returns_compact_float_strings() -> None:
    assert ChaserPoseFollower._format_values([1, -2.5, 0.000123456789]) == [
        '1',
        '-2.5',
        '0.000123456789',
    ]


def test_pose_request_text_contains_entity_pose() -> None:
    request = ChaserPoseFollower._pose_request_text(
        'chaser',
        [1.0, -2.0, 3.5],
        [0.0, 0.0, 0.0, 1.0],
    )

    assert 'name: "chaser"' in request
    assert 'position { x: 1 y: -2 z: 3.5 }' in request
    assert 'orientation { x: 0 y: 0 z: 0 w: 1 }' in request


def test_nonnegative_parameter_rejects_negative_values() -> None:
    follower = ChaserPoseFollower.__new__(ChaserPoseFollower)
    follower.get_parameter = lambda _name: type('Parameter', (), {'value': -1.0})()

    try:
        follower._nonnegative_parameter('startup_delay')
    except ValueError as error:
        assert 'startup_delay' in str(error)
    else:
        raise AssertionError('negative startup_delay should be rejected')
