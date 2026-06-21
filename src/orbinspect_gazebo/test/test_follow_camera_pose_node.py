from orbinspect_gazebo.follow_camera_pose_node import look_at_quaternion


def test_look_at_quaternion_returns_unit_quaternion() -> None:
    qx, qy, qz, qw = look_at_quaternion((-1.0, 0.0, 0.0), (0.0, 0.0, 0.0))

    norm = (qx * qx + qy * qy + qz * qz + qw * qw) ** 0.5

    assert abs(norm - 1.0) < 1.0e-9
