"""Fixed waypoint planner for the first closed-loop inspection mission."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class InspectionWaypoint:
    """A fixed LVLH inspection waypoint."""

    waypoint_id: str
    position: Vector3


class FixedWaypointPlanner:
    """Load and validate a fixed sequence of inspection waypoints."""

    def __init__(self, waypoints: Sequence[Sequence[float]]) -> None:
        if not waypoints:
            raise ValueError('at least one waypoint is required')
        self._waypoints = [
            InspectionWaypoint(
                waypoint_id=f'wp_{index:03d}',
                position=self._vector3(waypoint),
            )
            for index, waypoint in enumerate(waypoints)
        ]

    @property
    def waypoints(self) -> list[InspectionWaypoint]:
        """Return a copy of the fixed waypoint sequence."""
        return list(self._waypoints)

    @staticmethod
    def default_waypoints() -> list[InspectionWaypoint]:
        """Return a conservative station-facing waypoint loop."""
        return FixedWaypointPlanner([
            [0.0, -22.0, 6.0],
            [12.0, -20.0, 8.0],
            [24.0, -14.0, 12.0],
            [30.0, 0.0, 14.0],
            [12.0, 18.0, 8.0],
            [0.0, 22.0, 6.0],
            [-12.0, 18.0, 8.0],
            [-24.0, 0.0, 12.0],
            [-12.0, -20.0, 8.0],
        ]).waypoints

    @staticmethod
    def _vector3(values: Sequence[float]) -> Vector3:
        if len(values) != 3:
            raise ValueError('waypoint must contain 3 elements')
        return (float(values[0]), float(values[1]), float(values[2]))
