"""Projection-based command filter for keep-out zone avoidance."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from orbinspect_safety.collision_checker import CollisionChecker
from orbinspect_safety.primitive_geometry import add
from orbinspect_safety.primitive_geometry import dot
from orbinspect_safety.primitive_geometry import limit_norm
from orbinspect_safety.primitive_geometry import norm
from orbinspect_safety.primitive_geometry import scale
from orbinspect_safety.primitive_geometry import subtract
from orbinspect_safety.primitive_geometry import vector3


@dataclass(frozen=True)
class FilterResult:
    """Result of applying the projection safety filter."""

    command: tuple[float, float, float]
    modified: bool
    reason: str
    minimum_distance: float
    safety_margin: float
    clearance: float
    in_caution_zone: bool
    nearest_primitive: str


class ProjectionSafetyFilter:
    """Remove inward acceleration near keep-out zones and enforce limits."""

    def __init__(
        self,
        checker: CollisionChecker | None = None,
        max_acceleration: float = 0.01,
        max_speed: float = 0.25,
        repulsion_gain: float = 0.004,
        braking_time: float = 4.0,
    ) -> None:
        if max_acceleration <= 0.0:
            raise ValueError('max_acceleration must be positive')
        if max_speed <= 0.0:
            raise ValueError('max_speed must be positive')
        if repulsion_gain < 0.0:
            raise ValueError('repulsion_gain must be non-negative')
        if braking_time <= 0.0:
            raise ValueError('braking_time must be positive')
        self.checker = checker or CollisionChecker()
        self.max_acceleration = float(max_acceleration)
        self.max_speed = float(max_speed)
        self.repulsion_gain = float(repulsion_gain)
        self.braking_time = float(braking_time)

    def filter_command(
        self,
        position: Sequence[float],
        velocity: Sequence[float],
        command: Sequence[float],
    ) -> FilterResult:
        """Project unsafe acceleration away from the nearest keep-out primitive."""
        original = limit_norm(command, self.max_acceleration)
        filtered = original
        reasons: list[str] = []
        if norm(subtract(original, command)) > 1.0e-12:
            reasons.append('acceleration_limited')

        assessment = self.checker.assess(position)
        normal = assessment.surface_distance.direction
        velocity_vector = vector3(velocity)

        if assessment.in_caution_zone:
            inward_acceleration = dot(filtered, normal)
            if inward_acceleration < 0.0:
                filtered = subtract(filtered, scale(normal, inward_acceleration))
                reasons.append('inward_acceleration_projected')

            closing_speed = dot(velocity_vector, normal)
            if closing_speed < 0.0:
                filtered = add(filtered, scale(normal, -closing_speed / self.braking_time))
                reasons.append('closing_speed_braked')

        if not assessment.is_safe:
            filtered = add(filtered, scale(normal, -assessment.clearance * self.repulsion_gain))
            reasons.append('keepout_repulsion')

        speed = norm(velocity_vector)
        if speed > self.max_speed:
            filtered = add(filtered, scale(velocity_vector, -1.0 / self.braking_time))
            reasons.append('speed_limited')

        limited = limit_norm(filtered, self.max_acceleration)
        if norm(subtract(limited, filtered)) > 1.0e-12:
            reasons.append('filtered_acceleration_limited')
        filtered = limited

        modified = norm(subtract(filtered, command)) > 1.0e-9
        return FilterResult(
            command=filtered,
            modified=modified,
            reason=';'.join(reasons) if reasons else 'pass_through',
            minimum_distance=assessment.minimum_distance,
            safety_margin=assessment.safety_margin,
            clearance=assessment.clearance,
            in_caution_zone=assessment.in_caution_zone,
            nearest_primitive=assessment.surface_distance.primitive_name,
        )
