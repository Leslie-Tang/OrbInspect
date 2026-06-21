from orbinspect_perception.visibility_checker import CameraModel
from orbinspect_perception.visibility_checker import VisibilityChecker


def test_visible_target_in_front_of_camera() -> None:
    checker = VisibilityChecker(CameraModel(), occluders=())

    assert checker.is_visible((0.0, -20.0, 0.0), (0.0, 0.0, 0.0), (0.0, -1.0, 0.0))


def test_target_outside_range_is_not_visible() -> None:
    checker = VisibilityChecker(CameraModel(max_range=25.0), occluders=())

    assert not checker.is_visible((0.0, -40.0, 0.0), (0.0, 0.0, 0.0), (0.0, -1.0, 0.0))


def test_target_outside_fov_is_not_visible() -> None:
    checker = VisibilityChecker(CameraModel(horizontal_fov_deg=70.0), occluders=())

    assert not checker.is_visible((0.0, -20.0, 0.0), (20.0, 0.0, 0.0), (0.0, -1.0, 0.0))
