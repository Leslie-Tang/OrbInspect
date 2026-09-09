"""Visibility checks for station inspection targets."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math


Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class CameraModel:
    """Camera visibility parameters."""

    horizontal_fov_deg: float = 70.0
    vertical_fov_deg: float = 50.0
    min_range: float = 2.0
    max_range: float = 25.0
    max_view_angle_deg: float = 60.0


@dataclass(frozen=True)
class StationPrimitive:
    """Axis-aligned box primitive used for line-of-sight blocking."""

    center: Vector3
    size: Vector3


DEFAULT_OCCLUDERS = (
    StationPrimitive((0.0, 0.0, 0.0), (80.0, 4.0, 4.0)),
    StationPrimitive((-25.0, 0.0, 12.0), (30.0, 1.0, 12.0)),
    StationPrimitive((25.0, 0.0, 12.0), (30.0, 1.0, 12.0)),
    StationPrimitive((0.0, 8.0, 0.0), (15.0, 6.0, 6.0)),
    StationPrimitive((0.0, -8.0, 0.0), (15.0, 6.0, 6.0)),
    StationPrimitive((0.0, 0.0, -6.0), (4.0, 4.0, 6.0)),
)


class VisibilityChecker:
    """Evaluate camera range, FOV, view angle, and occlusion constraints."""

    def __init__(
        self,
        camera: CameraModel,
        occluders: Sequence[StationPrimitive] = DEFAULT_OCCLUDERS,
    ) -> None:
        self.camera = camera
        self.occluders = tuple(occluders)

    def is_visible(
        self,
        chaser_position: Sequence[float],
        target_position: Sequence[float],
        target_normal: Sequence[float],
    ) -> bool:
        """Return true when a target satisfies Phase 6 visibility constraints."""
        relative = _subtract(target_position, chaser_position)
        distance = _norm(relative)
        if distance < self.camera.min_range or distance > self.camera.max_range:
            return False
        if not self._inside_fov(chaser_position, relative):
            return False
        if not self._inside_view_angle(chaser_position, target_position, target_normal):
            return False
        return not self._line_of_sight_blocked(chaser_position, target_position)

    def _inside_fov(self, chaser_position: Sequence[float], relative: Vector3) -> bool:
        # Phase 6 has no attitude controller yet, so model the camera as
        # station-facing: its boresight points from the chaser toward LVLH origin.
        boresight = _unit(tuple(-float(value) for value in chaser_position))
        right, up = _camera_basis(boresight)
        forward = _dot(relative, boresight)
        if forward <= 0.0:
            return False
        horizontal_angle = math.atan2(abs(_dot(relative, right)), forward)
        vertical_angle = math.atan2(abs(_dot(relative, up)), forward)
        return (
            horizontal_angle <= math.radians(self.camera.horizontal_fov_deg) / 2.0
            and vertical_angle <= math.radians(self.camera.vertical_fov_deg) / 2.0
        )

    def _inside_view_angle(
        self,
        chaser_position: Sequence[float],
        target_position: Sequence[float],
        target_normal: Sequence[float],
    ) -> bool:
        target_to_chaser = _subtract(chaser_position, target_position)
        cosine = _dot(_unit(target_to_chaser), _unit(target_normal))
        cosine = max(-1.0, min(1.0, cosine))
        angle = math.degrees(math.acos(cosine))
        return angle <= self.camera.max_view_angle_deg

    def _line_of_sight_blocked(
        self,
        chaser_position: Sequence[float],
        target_position: Sequence[float],
    ) -> bool:
        start = tuple(float(value) for value in chaser_position)
        end = tuple(float(value) for value in target_position)
        for primitive in self.occluders:
            intersection = _segment_box_intersection(start, end, primitive)
            if intersection is not None and 1.0e-4 < intersection < 1.0 - 1.0e-4:
                return True
        return False


def _segment_box_intersection(
    start: Vector3,
    end: Vector3,
    primitive: StationPrimitive,
) -> float | None:
    direction = _subtract(end, start)
    t_min = 0.0
    t_max = 1.0
    for axis in range(3):
        low = primitive.center[axis] - primitive.size[axis] / 2.0
        high = primitive.center[axis] + primitive.size[axis] / 2.0
        if abs(direction[axis]) < 1.0e-12:
            if start[axis] < low or start[axis] > high:
                return None
            continue
        inv_direction = 1.0 / direction[axis]
        t1 = (low - start[axis]) * inv_direction
        t2 = (high - start[axis]) * inv_direction
        t_near = min(t1, t2)
        t_far = max(t1, t2)
        t_min = max(t_min, t_near)
        t_max = min(t_max, t_far)
        if t_min > t_max:
            return None
    return t_min


def _subtract(left: Sequence[float], right: Sequence[float]) -> Vector3:
    return (
        float(left[0]) - float(right[0]),
        float(left[1]) - float(right[1]),
        float(left[2]) - float(right[2]),
    )


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return (
        float(left[0]) * float(right[0])
        + float(left[1]) * float(right[1])
        + float(left[2]) * float(right[2])
    )


def _norm(values: Sequence[float]) -> float:
    return math.sqrt(_dot(values, values))


def _unit(values: Sequence[float]) -> Vector3:
    norm = _norm(values)
    if norm <= 0.0:
        raise ValueError('cannot normalize zero-length vector')
    return (float(values[0]) / norm, float(values[1]) / norm, float(values[2]) / norm)


def _camera_basis(boresight: Sequence[float]) -> tuple[Vector3, Vector3]:
    world_up = (0.0, 0.0, 1.0)
    if abs(_dot(boresight, world_up)) > 0.95:
        world_up = (0.0, 1.0, 0.0)
    right = _unit(_cross(world_up, boresight))
    up = _unit(_cross(boresight, right))
    return right, up


def _cross(left: Sequence[float], right: Sequence[float]) -> Vector3:
    return (
        float(left[1]) * float(right[2]) - float(left[2]) * float(right[1]),
        float(left[2]) * float(right[0]) - float(left[0]) * float(right[2]),
        float(left[0]) * float(right[1]) - float(left[1]) * float(right[0]),
    )
