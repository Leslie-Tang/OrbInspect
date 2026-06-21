"""Collision and keep-out checks for OrbInspect station geometry."""

from __future__ import annotations

from collections.abc import Sequence

from orbinspect_safety.keepout_zones import KeepoutZoneModel
from orbinspect_safety.keepout_zones import SafetyAssessment


class CollisionChecker:
    """Compute clearance from the chaser to station keep-out zones."""

    def __init__(self, keepout_model: KeepoutZoneModel | None = None) -> None:
        self.keepout_model = keepout_model or KeepoutZoneModel()

    def assess(self, position: Sequence[float]) -> SafetyAssessment:
        """Return minimum-distance safety status for a position."""
        return self.keepout_model.assess(position)

    def is_safe(self, position: Sequence[float]) -> bool:
        """Return true when the position is outside keep-out margins."""
        return self.assess(position).is_safe
