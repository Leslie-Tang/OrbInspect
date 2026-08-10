"""Candidate waypoint generation for greedy inspection planning."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math

from orbinspect_safety.collision_checker import CollisionChecker


Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class CandidateWaypoint:
    """A candidate LVLH viewpoint for inspection planning."""

    waypoint_id: str
    position: Vector3
    safety_margin: float


class WaypointGenerator:
    """Sample deterministic candidate viewpoints around the station proxy."""

    def __init__(
        self,
        radius_min: float = 10.0,
        radius_max: float = 28.0,
        radial_steps: int = 3,
        azimuth_steps: int = 16,
        elevation_steps: int = 5,
        checker: CollisionChecker | None = None,
    ) -> None:
        if radius_min <= 0.0 or radius_max <= 0.0:
            raise ValueError('candidate radii must be positive')
        if radius_max < radius_min:
            raise ValueError('radius_max must be greater than or equal to radius_min')
        if radial_steps <= 0 or azimuth_steps <= 0 or elevation_steps <= 0:
            raise ValueError('sampling step counts must be positive')
        self.radius_min = float(radius_min)
        self.radius_max = float(radius_max)
        self.radial_steps = int(radial_steps)
        self.azimuth_steps = int(azimuth_steps)
        self.elevation_steps = int(elevation_steps)
        self.checker = checker or CollisionChecker()

    def generate(self) -> list[CandidateWaypoint]:
        """Return safe candidate waypoints outside keep-out geometry."""
        candidates: list[CandidateWaypoint] = []
        for radius in self._radii():
            for elevation in self._elevations():
                for azimuth_index in range(self.azimuth_steps):
                    azimuth = 2.0 * math.pi * azimuth_index / self.azimuth_steps
                    position = (
                        radius * math.cos(elevation) * math.cos(azimuth),
                        radius * math.cos(elevation) * math.sin(azimuth),
                        radius * math.sin(elevation),
                    )
                    assessment = self.checker.assess(position)
                    if not assessment.is_safe:
                        continue
                    candidates.append(
                        CandidateWaypoint(
                            waypoint_id=f'nbv_{len(candidates):04d}',
                            position=position,
                            safety_margin=assessment.clearance,
                        )
                    )
        return candidates

    def _radii(self) -> list[float]:
        if self.radial_steps == 1:
            return [(self.radius_min + self.radius_max) / 2.0]
        step = (self.radius_max - self.radius_min) / float(self.radial_steps - 1)
        return [self.radius_min + step * index for index in range(self.radial_steps)]

    def _elevations(self) -> list[float]:
        if self.elevation_steps == 1:
            return [0.0]
        max_elevation = math.radians(35.0)
        step = 2.0 * max_elevation / float(self.elevation_steps - 1)
        return [-max_elevation + step * index for index in range(self.elevation_steps)]


def distance(left: Sequence[float], right: Sequence[float]) -> float:
    """Return Euclidean distance between two 3D points."""
    return math.sqrt(
        (float(left[0]) - float(right[0])) ** 2
        + (float(left[1]) - float(right[1])) ** 2
        + (float(left[2]) - float(right[2])) ** 2
    )
