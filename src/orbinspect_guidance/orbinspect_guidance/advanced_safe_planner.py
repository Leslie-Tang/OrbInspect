"""Placeholder interfaces for future advanced safe inspection planners."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdvancedPlannerConfig:
    """Configuration placeholder for future MPC, CBF, or HJI planners."""

    method: str = 'placeholder'
    horizon_steps: int = 20
    time_step: float = 1.0
    safety_margin: float = 2.0


class AdvancedSafePlanner:
    """Explicit scaffold for future safety-constrained planning research."""

    def __init__(self, config: AdvancedPlannerConfig | None = None) -> None:
        self.config = config or AdvancedPlannerConfig()

    @property
    def available(self) -> bool:
        """Return false until an advanced solver backend is implemented."""
        return False

    def plan(self, *_args, **_kwargs):
        """Raise a clear placeholder error for future implementation."""
        raise NotImplementedError(
            'Advanced safe planner is a placeholder; use greedy NBV baseline for now'
        )
