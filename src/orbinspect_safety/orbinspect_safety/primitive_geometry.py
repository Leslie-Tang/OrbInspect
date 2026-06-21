"""Primitive geometry helpers for OrbInspect station safety checks."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math


Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class SurfaceDistance:
    """Signed distance from a point to a station primitive surface."""

    primitive_name: str
    distance: float
    direction: Vector3
    closest_point: Vector3


@dataclass(frozen=True)
class BoxPrimitive:
    """Axis-aligned solid box primitive."""

    name: str
    center: Vector3
    size: Vector3

    def distance_to(self, point: Sequence[float]) -> SurfaceDistance:
        """Return signed distance and outward direction from this box."""
        point_vector = vector3(point)
        half = tuple(float(value) / 2.0 for value in self.size)
        low = tuple(self.center[index] - half[index] for index in range(3))
        high = tuple(self.center[index] + half[index] for index in range(3))
        closest = tuple(
            min(max(point_vector[index], low[index]), high[index])
            for index in range(3)
        )
        delta = subtract(point_vector, closest)
        outside_distance = norm(delta)
        if outside_distance > 0.0:
            return SurfaceDistance(
                self.name,
                outside_distance,
                scale(delta, 1.0 / outside_distance),
                closest,
            )

        face_distances = (
            (
                high[0] - point_vector[0],
                (1.0, 0.0, 0.0),
                (high[0], point_vector[1], point_vector[2]),
            ),
            (
                point_vector[0] - low[0],
                (-1.0, 0.0, 0.0),
                (low[0], point_vector[1], point_vector[2]),
            ),
            (
                high[1] - point_vector[1],
                (0.0, 1.0, 0.0),
                (point_vector[0], high[1], point_vector[2]),
            ),
            (
                point_vector[1] - low[1],
                (0.0, -1.0, 0.0),
                (point_vector[0], low[1], point_vector[2]),
            ),
            (
                high[2] - point_vector[2],
                (0.0, 0.0, 1.0),
                (point_vector[0], point_vector[1], high[2]),
            ),
            (
                point_vector[2] - low[2],
                (0.0, 0.0, -1.0),
                (point_vector[0], point_vector[1], low[2]),
            ),
        )
        penetration, direction, closest_face = min(face_distances, key=lambda item: item[0])
        return SurfaceDistance(self.name, -penetration, direction, closest_face)


@dataclass(frozen=True)
class CylinderPrimitive:
    """Finite solid cylinder primitive aligned to one world axis."""

    name: str
    center: Vector3
    radius: float
    length: float
    axis: str = 'z'

    def distance_to(self, point: Sequence[float]) -> SurfaceDistance:
        """Return signed distance and outward direction from this cylinder."""
        point_vector = vector3(point)
        axis_index = {'x': 0, 'y': 1, 'z': 2}[self.axis]
        radial_indices = tuple(index for index in range(3) if index != axis_index)
        local = subtract(point_vector, self.center)
        axial = local[axis_index]
        radial = (local[radial_indices[0]], local[radial_indices[1]])
        radial_norm = math.hypot(radial[0], radial[1])
        half_length = self.length / 2.0

        radial_excess = max(radial_norm - self.radius, 0.0)
        axial_excess = max(abs(axial) - half_length, 0.0)
        if radial_excess > 0.0 or axial_excess > 0.0:
            distance = math.hypot(radial_excess, axial_excess)
            direction = self._outside_direction(
                radial,
                radial_norm,
                axial,
                radial_excess,
                axial_excess,
            )
            closest = self._closest_point(point_vector)
            return SurfaceDistance(self.name, distance, direction, closest)

        side_clearance = self.radius - radial_norm
        cap_clearance = half_length - abs(axial)
        if side_clearance <= cap_clearance:
            direction = self._radial_direction(radial, radial_norm, radial_indices)
            closest = self._side_point(point_vector, radial, radial_norm, radial_indices)
            return SurfaceDistance(self.name, -side_clearance, direction, closest)

        direction_values = [0.0, 0.0, 0.0]
        direction_values[axis_index] = 1.0 if axial >= 0.0 else -1.0
        closest_values = list(point_vector)
        closest_values[axis_index] = (
            self.center[axis_index] + direction_values[axis_index] * half_length
        )
        return SurfaceDistance(
            self.name,
            -cap_clearance,
            tuple(direction_values),
            tuple(closest_values),
        )

    def _outside_direction(
        self,
        radial: tuple[float, float],
        radial_norm: float,
        axial: float,
        radial_excess: float,
        axial_excess: float,
    ) -> Vector3:
        axis_index = {'x': 0, 'y': 1, 'z': 2}[self.axis]
        radial_indices = tuple(index for index in range(3) if index != axis_index)
        values = [0.0, 0.0, 0.0]
        if radial_excess > 0.0:
            radial_direction = self._radial_pair(radial, radial_norm)
            values[radial_indices[0]] = radial_direction[0] * radial_excess
            values[radial_indices[1]] = radial_direction[1] * radial_excess
        if axial_excess > 0.0:
            values[axis_index] = (1.0 if axial >= 0.0 else -1.0) * axial_excess
        return unit(values)

    def _closest_point(self, point: Vector3) -> Vector3:
        axis_index = {'x': 0, 'y': 1, 'z': 2}[self.axis]
        radial_indices = tuple(index for index in range(3) if index != axis_index)
        local = subtract(point, self.center)
        axial = min(max(local[axis_index], -self.length / 2.0), self.length / 2.0)
        radial = (local[radial_indices[0]], local[radial_indices[1]])
        radial_norm = math.hypot(radial[0], radial[1])
        radial_direction = self._radial_pair(radial, radial_norm)
        radial_radius = min(radial_norm, self.radius)
        values = list(self.center)
        values[axis_index] += axial
        values[radial_indices[0]] += radial_direction[0] * radial_radius
        values[radial_indices[1]] += radial_direction[1] * radial_radius
        return tuple(values)

    def _side_point(
        self,
        point: Vector3,
        radial: tuple[float, float],
        radial_norm: float,
        radial_indices: tuple[int, int],
    ) -> Vector3:
        radial_direction = self._radial_pair(radial, radial_norm)
        values = list(point)
        values[radial_indices[0]] = (
            self.center[radial_indices[0]] + radial_direction[0] * self.radius
        )
        values[radial_indices[1]] = (
            self.center[radial_indices[1]] + radial_direction[1] * self.radius
        )
        return tuple(values)

    def _radial_direction(
        self,
        radial: tuple[float, float],
        radial_norm: float,
        radial_indices: tuple[int, int],
    ) -> Vector3:
        pair = self._radial_pair(radial, radial_norm)
        values = [0.0, 0.0, 0.0]
        values[radial_indices[0]] = pair[0]
        values[radial_indices[1]] = pair[1]
        return tuple(values)

    @staticmethod
    def _radial_pair(radial: tuple[float, float], radial_norm: float) -> tuple[float, float]:
        if radial_norm <= 1.0e-12:
            return (1.0, 0.0)
        return (radial[0] / radial_norm, radial[1] / radial_norm)


StationPrimitive = BoxPrimitive | CylinderPrimitive


def vector3(values: Sequence[float]) -> Vector3:
    """Return the first three values as floats."""
    if len(values) != 3:
        raise ValueError('expected exactly three values')
    return (float(values[0]), float(values[1]), float(values[2]))


def add(left: Sequence[float], right: Sequence[float]) -> Vector3:
    """Add two 3D vectors."""
    return (
        float(left[0]) + float(right[0]),
        float(left[1]) + float(right[1]),
        float(left[2]) + float(right[2]),
    )


def subtract(left: Sequence[float], right: Sequence[float]) -> Vector3:
    """Subtract two 3D vectors."""
    return (
        float(left[0]) - float(right[0]),
        float(left[1]) - float(right[1]),
        float(left[2]) - float(right[2]),
    )


def dot(left: Sequence[float], right: Sequence[float]) -> float:
    """Return the dot product of two 3D vectors."""
    return (
        float(left[0]) * float(right[0])
        + float(left[1]) * float(right[1])
        + float(left[2]) * float(right[2])
    )


def norm(values: Sequence[float]) -> float:
    """Return the Euclidean norm of a 3D vector."""
    return math.sqrt(dot(values, values))


def scale(values: Sequence[float], factor: float) -> Vector3:
    """Scale a 3D vector."""
    return (
        float(values[0]) * factor,
        float(values[1]) * factor,
        float(values[2]) * factor,
    )


def unit(values: Sequence[float]) -> Vector3:
    """Normalize a 3D vector."""
    value_norm = norm(values)
    if value_norm <= 1.0e-12:
        raise ValueError('cannot normalize zero-length vector')
    return scale(values, 1.0 / value_norm)


def limit_norm(values: Sequence[float], maximum: float) -> Vector3:
    """Limit a 3D vector magnitude without changing its direction."""
    value_norm = norm(values)
    if value_norm <= maximum or value_norm <= 1.0e-12:
        return vector3(values)
    return scale(values, maximum / value_norm)
