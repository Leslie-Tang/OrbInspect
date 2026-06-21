"""Default keep-out geometry for the simplified OrbInspect station proxy."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from orbinspect_safety.primitive_geometry import BoxPrimitive
from orbinspect_safety.primitive_geometry import CylinderPrimitive
from orbinspect_safety.primitive_geometry import StationPrimitive
from orbinspect_safety.primitive_geometry import SurfaceDistance


DEFAULT_STATION_PRIMITIVES: tuple[StationPrimitive, ...] = (
    BoxPrimitive('main_truss', (0.0, 0.0, 0.0), (80.0, 4.0, 4.0)),
    BoxPrimitive('left_solar_array', (-25.0, 0.0, 12.0), (30.0, 1.0, 12.0)),
    BoxPrimitive('right_solar_array', (25.0, 0.0, 12.0), (30.0, 1.0, 12.0)),
    CylinderPrimitive('module_1', (0.0, 8.0, 0.0), 3.0, 15.0, 'x'),
    CylinderPrimitive('module_2', (0.0, -8.0, 0.0), 3.0, 15.0, 'x'),
    CylinderPrimitive('docking_node', (0.0, 0.0, -6.0), 2.0, 6.0, 'z'),
)


@dataclass(frozen=True)
class SafetyAssessment:
    """Distance and safety-state result for a chaser position."""

    surface_distance: SurfaceDistance
    safety_margin: float
    caution_margin: float

    @property
    def minimum_distance(self) -> float:
        """Return signed distance to the closest station primitive surface."""
        return self.surface_distance.distance

    @property
    def clearance(self) -> float:
        """Return signed distance above the required safety margin."""
        return self.minimum_distance - self.safety_margin

    @property
    def is_safe(self) -> bool:
        """Return true when the chaser is outside the keep-out margin."""
        return self.clearance >= 0.0

    @property
    def in_caution_zone(self) -> bool:
        """Return true when close enough to start conservative filtering."""
        return self.minimum_distance < self.caution_margin


class KeepoutZoneModel:
    """Evaluate minimum distance to station keep-out geometry."""

    def __init__(
        self,
        primitives: Sequence[StationPrimitive] = DEFAULT_STATION_PRIMITIVES,
        safety_margin: float = 2.0,
        caution_margin: float = 6.0,
    ) -> None:
        if safety_margin <= 0.0:
            raise ValueError('safety_margin must be positive')
        if caution_margin < safety_margin:
            raise ValueError('caution_margin must be greater than or equal to safety_margin')
        if not primitives:
            raise ValueError('at least one station primitive is required')
        self.primitives = tuple(primitives)
        self.safety_margin = float(safety_margin)
        self.caution_margin = float(caution_margin)

    def assess(self, position: Sequence[float]) -> SafetyAssessment:
        """Return the closest-primitive safety assessment for a position."""
        closest = min(
            (primitive.distance_to(position) for primitive in self.primitives),
            key=lambda distance: distance.distance,
        )
        return SafetyAssessment(closest, self.safety_margin, self.caution_margin)
