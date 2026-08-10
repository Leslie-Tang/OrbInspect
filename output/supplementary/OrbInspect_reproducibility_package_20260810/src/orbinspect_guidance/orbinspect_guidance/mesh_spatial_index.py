"""Dependency-free spatial queries over triangle meshes.

The index is intentionally implemented without SciPy, ``rtree``, or a graphics
engine so the offline paper experiments use the same deterministic geometry in
minimal Python and ROS environments.
"""

from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Iterable


Vector3 = tuple[float, float, float]
TriangleVertices = tuple[Vector3, Vector3, Vector3]


@dataclass(frozen=True, slots=True)
class _BvhNode:
    """One axis-aligned node in a triangle bounding-volume hierarchy."""

    bounds_min: Vector3
    bounds_max: Vector3
    left: int = -1
    right: int = -1
    triangle_indices: tuple[int, ...] = ()

    @property
    def is_leaf(self) -> bool:
        """Return whether this node stores triangles directly."""
        return self.left < 0


class TriangleSpatialIndex:
    """Accelerate full-mesh segment intersection and point-distance queries."""

    def __init__(
        self,
        triangles: Iterable[TriangleVertices],
        leaf_size: int = 12,
    ) -> None:
        """Build a deterministic median-split BVH for ``triangles``."""
        if leaf_size <= 0:
            raise ValueError('leaf_size must be positive')
        self.triangles = tuple(triangles)
        if not self.triangles:
            raise ValueError('at least one triangle is required')
        self._leaf_size = int(leaf_size)
        self._triangle_bounds = tuple(
            _triangle_bounds(vertices) for vertices in self.triangles
        )
        self._triangle_centroids = tuple(
            tuple(
                sum(vertex[axis] for vertex in vertices) / 3.0
                for axis in range(3)
            )
            for vertices in self.triangles
        )
        self._nodes: list[_BvhNode] = []
        self._root = self._build(list(range(len(self.triangles))))

    @property
    def triangle_count(self) -> int:
        """Return the number of indexed triangles."""
        return len(self.triangles)

    def intersects_segment(
        self,
        start: Vector3,
        end: Vector3,
        *,
        min_fraction: float = 0.0,
        max_fraction: float = 1.0,
    ) -> bool:
        """Return whether any mesh triangle intersects a segment interval.

        Fractions are expressed along ``end - start``.  Visibility checks can
        exclude both endpoints, while swept-safety checks can include them.
        """
        if not 0.0 <= min_fraction <= max_fraction <= 1.0:
            raise ValueError('segment fractions must satisfy 0 <= min <= max <= 1')
        direction = _subtract(end, start)
        if _dot(direction, direction) <= 1.0e-24:
            return False
        stack = [self._root]
        while stack:
            node_index = stack.pop()
            node = self._nodes[node_index]
            if not _segment_intersects_aabb(
                start,
                direction,
                node.bounds_min,
                node.bounds_max,
                min_fraction,
                max_fraction,
            ):
                continue
            if node.is_leaf:
                if any(
                    segment_triangle_intersection_fraction(
                        start,
                        end,
                        self.triangles[triangle_index],
                        min_fraction=min_fraction,
                        max_fraction=max_fraction,
                    ) is not None
                    for triangle_index in node.triangle_indices
                ):
                    return True
                continue
            stack.append(node.left)
            stack.append(node.right)
        return False

    def point_distance(self, point: Vector3) -> float:
        """Return the unsigned Euclidean distance to the closest triangle."""
        best_squared = math.inf
        queue: list[tuple[float, int]] = [(
            _point_aabb_distance_squared(
                point,
                self._nodes[self._root].bounds_min,
                self._nodes[self._root].bounds_max,
            ),
            self._root,
        )]
        while queue:
            lower_bound, node_index = heapq.heappop(queue)
            if lower_bound >= best_squared:
                break
            node = self._nodes[node_index]
            if node.is_leaf:
                for triangle_index in node.triangle_indices:
                    best_squared = min(
                        best_squared,
                        _point_triangle_distance_squared(
                            point,
                            self.triangles[triangle_index],
                        ),
                    )
                continue
            for child_index in (node.left, node.right):
                child = self._nodes[child_index]
                child_bound = _point_aabb_distance_squared(
                    point,
                    child.bounds_min,
                    child.bounds_max,
                )
                if child_bound < best_squared:
                    heapq.heappush(queue, (child_bound, child_index))
        return math.sqrt(best_squared)

    def _build(self, indices: list[int]) -> int:
        bounds_min, bounds_max = _combined_bounds(
            self._triangle_bounds[index] for index in indices
        )
        node_index = len(self._nodes)
        self._nodes.append(_BvhNode(bounds_min, bounds_max))
        if len(indices) <= self._leaf_size:
            self._nodes[node_index] = _BvhNode(
                bounds_min,
                bounds_max,
                triangle_indices=tuple(indices),
            )
            return node_index

        centroid_min, centroid_max = _combined_points(
            self._triangle_centroids[index] for index in indices
        )
        axis = max(range(3), key=lambda value: centroid_max[value] - centroid_min[value])
        indices.sort(key=lambda index: self._triangle_centroids[index][axis])
        midpoint = len(indices) // 2
        left = self._build(indices[:midpoint])
        right = self._build(indices[midpoint:])
        self._nodes[node_index] = _BvhNode(bounds_min, bounds_max, left, right)
        return node_index


def segment_triangle_intersection_fraction(
    start: Vector3,
    end: Vector3,
    vertices: TriangleVertices,
    *,
    min_fraction: float = 0.0,
    max_fraction: float = 1.0,
) -> float | None:
    """Return the segment fraction of a Moller-Trumbore intersection.

    The Moller-Trumbore parameter is already a fraction because the ray
    direction is ``end - start``.  It must not be divided by segment length.
    """
    direction = _subtract(end, start)
    if _dot(direction, direction) <= 1.0e-24:
        return None
    edge_a = _subtract(vertices[1], vertices[0])
    edge_b = _subtract(vertices[2], vertices[0])
    p_vector = _cross(direction, edge_b)
    determinant = _dot(edge_a, p_vector)
    if abs(determinant) <= 1.0e-12:
        return None
    inv_determinant = 1.0 / determinant
    t_vector = _subtract(start, vertices[0])
    u_value = _dot(t_vector, p_vector) * inv_determinant
    if u_value < -1.0e-10 or u_value > 1.0 + 1.0e-10:
        return None
    q_vector = _cross(t_vector, edge_a)
    v_value = _dot(direction, q_vector) * inv_determinant
    if v_value < -1.0e-10 or u_value + v_value > 1.0 + 1.0e-10:
        return None
    fraction = _dot(edge_b, q_vector) * inv_determinant
    tolerance = 1.0e-10
    if fraction < min_fraction - tolerance or fraction > max_fraction + tolerance:
        return None
    return max(min_fraction, min(max_fraction, fraction))


def _triangle_bounds(vertices: TriangleVertices) -> tuple[Vector3, Vector3]:
    return (
        tuple(min(vertex[axis] for vertex in vertices) for axis in range(3)),
        tuple(max(vertex[axis] for vertex in vertices) for axis in range(3)),
    )


def _combined_bounds(
    bounds: Iterable[tuple[Vector3, Vector3]],
) -> tuple[Vector3, Vector3]:
    bounds_list = tuple(bounds)
    return (
        tuple(min(item[0][axis] for item in bounds_list) for axis in range(3)),
        tuple(max(item[1][axis] for item in bounds_list) for axis in range(3)),
    )


def _combined_points(points: Iterable[Vector3]) -> tuple[Vector3, Vector3]:
    point_list = tuple(points)
    return (
        tuple(min(point[axis] for point in point_list) for axis in range(3)),
        tuple(max(point[axis] for point in point_list) for axis in range(3)),
    )


def _segment_intersects_aabb(
    start: Vector3,
    direction: Vector3,
    bounds_min: Vector3,
    bounds_max: Vector3,
    min_fraction: float,
    max_fraction: float,
) -> bool:
    lower = min_fraction
    upper = max_fraction
    for axis in range(3):
        if abs(direction[axis]) <= 1.0e-15:
            if start[axis] < bounds_min[axis] or start[axis] > bounds_max[axis]:
                return False
            continue
        inverse = 1.0 / direction[axis]
        near = (bounds_min[axis] - start[axis]) * inverse
        far = (bounds_max[axis] - start[axis]) * inverse
        if near > far:
            near, far = far, near
        lower = max(lower, near)
        upper = min(upper, far)
        if lower > upper:
            return False
    return True


def _point_aabb_distance_squared(
    point: Vector3,
    bounds_min: Vector3,
    bounds_max: Vector3,
) -> float:
    squared = 0.0
    for axis in range(3):
        if point[axis] < bounds_min[axis]:
            difference = bounds_min[axis] - point[axis]
            squared += difference * difference
        elif point[axis] > bounds_max[axis]:
            difference = point[axis] - bounds_max[axis]
            squared += difference * difference
    return squared


def _point_triangle_distance_squared(
    point: Vector3,
    vertices: TriangleVertices,
) -> float:
    """Return squared point-triangle distance (Ericson region tests)."""
    a, b, c = vertices
    ab = _subtract(b, a)
    ac = _subtract(c, a)
    ap = _subtract(point, a)
    d1 = _dot(ab, ap)
    d2 = _dot(ac, ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return _dot(ap, ap)

    bp = _subtract(point, b)
    d3 = _dot(ab, bp)
    d4 = _dot(ac, bp)
    if d3 >= 0.0 and d4 <= d3:
        return _dot(bp, bp)

    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        fraction = d1 / (d1 - d3)
        projection = _add(a, _scale(ab, fraction))
        difference = _subtract(point, projection)
        return _dot(difference, difference)

    cp = _subtract(point, c)
    d5 = _dot(ab, cp)
    d6 = _dot(ac, cp)
    if d6 >= 0.0 and d5 <= d6:
        return _dot(cp, cp)

    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        fraction = d2 / (d2 - d6)
        projection = _add(a, _scale(ac, fraction))
        difference = _subtract(point, projection)
        return _dot(difference, difference)

    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        edge = _subtract(c, b)
        fraction = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        projection = _add(b, _scale(edge, fraction))
        difference = _subtract(point, projection)
        return _dot(difference, difference)

    denominator = va + vb + vc
    if abs(denominator) <= 1.0e-24:
        return min(_dot(ap, ap), _dot(bp, bp), _dot(cp, cp))
    inverse = 1.0 / denominator
    v_value = vb * inverse
    w_value = vc * inverse
    projection = _add(a, _add(_scale(ab, v_value), _scale(ac, w_value)))
    difference = _subtract(point, projection)
    return _dot(difference, difference)


def _add(left: Vector3, right: Vector3) -> Vector3:
    return tuple(left[index] + right[index] for index in range(3))


def _subtract(left: Vector3, right: Vector3) -> Vector3:
    return tuple(left[index] - right[index] for index in range(3))


def _scale(vector: Vector3, factor: float) -> Vector3:
    return tuple(value * factor for value in vector)


def _dot(left: Vector3, right: Vector3) -> float:
    return sum(left[index] * right[index] for index in range(3))


def _cross(left: Vector3, right: Vector3) -> Vector3:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )
