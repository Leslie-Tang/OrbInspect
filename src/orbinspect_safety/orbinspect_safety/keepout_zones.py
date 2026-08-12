"""Default keep-out geometry for the simplified OrbInspect station proxy."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from orbinspect_safety.primitive_geometry import BoxPrimitive
from orbinspect_safety.primitive_geometry import CylinderPrimitive
from orbinspect_safety.primitive_geometry import OrientedBoxPrimitive
from orbinspect_safety.primitive_geometry import StationPrimitive
from orbinspect_safety.primitive_geometry import SurfaceDistance


ARRAY_AXES = (
    (0.0, 0.0, -1.0),
    (0.866025403784, 0.5, 0.0),
    (0.5, -0.866025403784, 0.0),
)
ARRAY_SIZE = (13.0, 1.5, 40.0)


DEFAULT_STATION_PRIMITIVES: tuple[StationPrimitive, ...] = (
    BoxPrimitive('main_truss', (0.0, 0.0, 0.0), (80.0, 4.0, 4.0)),
    BoxPrimitive('left_solar_array', (-25.0, 0.0, 12.0), (30.0, 1.0, 12.0)),
    BoxPrimitive('right_solar_array', (25.0, 0.0, 12.0), (30.0, 1.0, 12.0)),
    OrientedBoxPrimitive(
        's4_array_starboard', (16.634071, -13.226793, 36.775400),
        ARRAY_SIZE, ARRAY_AXES,
    ),
    OrientedBoxPrimitive(
        's4_array_port', (-6.050227, 23.155261, 36.775388),
        ARRAY_SIZE, ARRAY_AXES,
    ),
    OrientedBoxPrimitive(
        's6_array_starboard', (16.637144, -13.234794, 53.201946),
        ARRAY_SIZE, ARRAY_AXES,
    ),
    OrientedBoxPrimitive(
        's6_array_port', (-6.047151, 23.147255, 53.201936),
        ARRAY_SIZE, ARRAY_AXES,
    ),
    OrientedBoxPrimitive(
        'p4_array_starboard', (14.957572, -13.231314, -36.775384),
        ARRAY_SIZE, ARRAY_AXES,
    ),
    OrientedBoxPrimitive(
        'p4_array_port', (-5.208061, 24.604892, -36.775403),
        ARRAY_SIZE, ARRAY_AXES,
    ),
    OrientedBoxPrimitive(
        'p6_array_starboard', (14.952176, -13.224648, -53.201932),
        ARRAY_SIZE, ARRAY_AXES,
    ),
    OrientedBoxPrimitive(
        'p6_array_port', (-5.213454, 24.611553, -53.201949),
        ARRAY_SIZE, ARRAY_AXES,
    ),
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
    vehicle_radius: float = 0.0

    @property
    def minimum_distance(self) -> float:
        """Return signed distance to the closest station primitive surface."""
        return self.surface_distance.distance

    @property
    def clearance(self) -> float:
        """Return body-surface clearance above the required safety margin."""
        return self.minimum_distance - self.vehicle_radius - self.safety_margin

    @property
    def body_clearance(self) -> float:
        """Return conservative vehicle-body distance from station geometry."""
        return self.minimum_distance - self.vehicle_radius

    @property
    def required_center_distance(self) -> float:
        """Return the center-distance threshold including vehicle radius."""
        return self.safety_margin + self.vehicle_radius

    @property
    def is_safe(self) -> bool:
        """Return true when the chaser is outside the keep-out margin."""
        return self.clearance >= 0.0

    @property
    def in_caution_zone(self) -> bool:
        """Return true when close enough to start conservative filtering."""
        return self.body_clearance < self.caution_margin


class KeepoutZoneModel:
    """Evaluate minimum distance to station keep-out geometry."""

    def __init__(
        self,
        primitives: Sequence[StationPrimitive] = DEFAULT_STATION_PRIMITIVES,
        safety_margin: float = 2.0,
        caution_margin: float = 6.0,
        vehicle_radius: float = 0.80,
    ) -> None:
        if safety_margin <= 0.0:
            raise ValueError('safety_margin must be positive')
        if caution_margin < safety_margin:
            raise ValueError('caution_margin must be greater than or equal to safety_margin')
        if vehicle_radius < 0.0:
            raise ValueError('vehicle_radius must be non-negative')
        if not primitives:
            raise ValueError('at least one station primitive is required')
        self.primitives = tuple(primitives)
        self.safety_margin = float(safety_margin)
        self.caution_margin = float(caution_margin)
        self.vehicle_radius = float(vehicle_radius)

    def assess(self, position: Sequence[float]) -> SafetyAssessment:
        """Return the closest-primitive safety assessment for a position."""
        closest = min(
            (primitive.distance_to(position) for primitive in self.primitives),
            key=lambda distance: distance.distance,
        )
        return SafetyAssessment(
            closest,
            self.safety_margin,
            self.caution_margin,
            self.vehicle_radius,
        )
