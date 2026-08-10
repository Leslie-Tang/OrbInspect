import math

from orbinspect_guidance.mesh_spatial_index import TriangleSpatialIndex
from orbinspect_guidance.mesh_spatial_index import (
    segment_triangle_intersection_fraction,
)


TRIANGLE = ((0.0, -1.0, -1.0), (0.0, 1.0, -1.0), (0.0, 0.0, 1.0))


def test_intersection_parameter_is_segment_fraction() -> None:
    fraction = segment_triangle_intersection_fraction(
        (-10.0, 0.0, 0.0),
        (10.0, 0.0, 0.0),
        TRIANGLE,
    )

    assert fraction is not None
    assert math.isclose(fraction, 0.5)


def test_open_segment_excludes_target_endpoint() -> None:
    index = TriangleSpatialIndex((TRIANGLE,))

    assert not index.intersects_segment(
        (-10.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        min_fraction=1.0e-5,
        max_fraction=1.0 - 1.0e-5,
    )
    assert index.intersects_segment(
        (-10.0, 0.0, 0.0),
        (10.0, 0.0, 0.0),
        min_fraction=1.0e-5,
        max_fraction=1.0 - 1.0e-5,
    )


def test_point_distance_uses_nearest_triangle_surface() -> None:
    index = TriangleSpatialIndex((TRIANGLE,))

    assert math.isclose(index.point_distance((3.0, 0.0, 0.0)), 3.0)
    assert math.isclose(index.point_distance((0.0, 0.0, 0.0)), 0.0)
