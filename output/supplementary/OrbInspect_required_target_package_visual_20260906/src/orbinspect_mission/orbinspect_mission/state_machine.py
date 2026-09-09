"""Mission state machine for fixed waypoint inspection."""

from __future__ import annotations

from enum import Enum


class MissionState(str, Enum):
    """High-level fixed waypoint mission states."""

    IDLE = 'IDLE'
    RUNNING = 'RUNNING'
    WAYPOINT_REACHED = 'WAYPOINT_REACHED'
    COVERAGE_COMPLETE = 'COVERAGE_COMPLETE'
    WAYPOINTS_COMPLETE = 'WAYPOINTS_COMPLETE'
    COMPLETE = 'COMPLETE'


class MissionStateMachine:
    """Track mission state transitions."""

    def __init__(self) -> None:
        self.state = MissionState.IDLE

    def start(self) -> MissionState:
        """Transition from idle to running."""
        self.state = MissionState.RUNNING
        return self.state

    def waypoint_reached(self) -> MissionState:
        """Record that the active waypoint was reached."""
        self.state = MissionState.WAYPOINT_REACHED
        return self.state

    def resume(self) -> MissionState:
        """Resume tracking after selecting another waypoint."""
        self.state = MissionState.RUNNING
        return self.state

    def coverage_complete(self) -> MissionState:
        """Stop because coverage threshold was reached."""
        self.state = MissionState.COVERAGE_COMPLETE
        return self.state

    def waypoints_complete(self) -> MissionState:
        """Stop because no waypoints remain."""
        self.state = MissionState.WAYPOINTS_COMPLETE
        return self.state

    def complete(self) -> MissionState:
        """Mark the mission complete."""
        self.state = MissionState.COMPLETE
        return self.state
