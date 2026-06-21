"""Dwell-time coverage map for inspection targets."""

from __future__ import annotations

from dataclasses import dataclass

from orbinspect_perception.inspection_target_manager import InspectionTarget


@dataclass
class TargetCoverageState:
    """Coverage state for one inspection target."""

    target: InspectionTarget
    dwell_time: float = 0.0
    inspected: bool = False
    inspection_count: int = 0


class CoverageMap:
    """Maintain dwell accumulation and inspected state for targets."""

    def __init__(self, targets: list[InspectionTarget], dwell_time: float) -> None:
        if dwell_time <= 0.0:
            raise ValueError('dwell_time must be positive')
        self.required_dwell_time = float(dwell_time)
        self.states = [TargetCoverageState(target=target) for target in targets]

    @property
    def total_targets(self) -> int:
        """Return number of targets in the map."""
        return len(self.states)

    @property
    def inspected_targets(self) -> int:
        """Return number of targets that reached dwell time."""
        return sum(1 for state in self.states if state.inspected)

    @property
    def coverage_ratio(self) -> float:
        """Return inspected target fraction."""
        if not self.states:
            return 0.0
        return self.inspected_targets / float(len(self.states))

    def update(self, visible_target_ids: set[str], dt: float) -> tuple[int, int]:
        """Accumulate dwell for visible targets and return visible/new counts."""
        if dt < 0.0:
            raise ValueError('dt must be non-negative')
        new_targets_seen = 0
        for state in self.states:
            if state.target.target_id not in visible_target_ids:
                continue
            state.dwell_time += dt
            state.inspection_count += 1
            if not state.inspected and state.dwell_time >= self.required_dwell_time:
                state.inspected = True
                new_targets_seen += 1
        return len(visible_target_ids), new_targets_seen
