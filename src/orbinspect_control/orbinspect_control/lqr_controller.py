"""Baseline LVLH waypoint controller."""

from __future__ import annotations

from collections.abc import Sequence
import math


StateVector = tuple[float, float, float, float, float, float]
PositionVector = tuple[float, float, float]
ControlVector = tuple[float, float, float]


class LQRController:
    """PD fallback controller with the planned LQR interface."""

    def __init__(
        self,
        position_gain: float,
        velocity_gain: float,
        max_acceleration: float,
    ) -> None:
        """Create a saturated PD controller for HCW state tracking."""
        if position_gain < 0.0:
            raise ValueError('position_gain must be non-negative')
        if velocity_gain < 0.0:
            raise ValueError('velocity_gain must be non-negative')
        if max_acceleration <= 0.0:
            raise ValueError('max_acceleration must be positive')

        self.position_gain = float(position_gain)
        self.velocity_gain = float(velocity_gain)
        self.max_acceleration = float(max_acceleration)

    def compute_control(
        self,
        state: Sequence[float],
        reference_position: Sequence[float],
    ) -> ControlVector:
        """Return saturated acceleration command [ax, ay, az]."""
        rx, ry, rz, vx, vy, vz = self._as_state(state)
        ref_x, ref_y, ref_z = self._as_position(reference_position)

        command = (
            self.position_gain * (ref_x - rx) - self.velocity_gain * vx,
            self.position_gain * (ref_y - ry) - self.velocity_gain * vy,
            self.position_gain * (ref_z - rz) - self.velocity_gain * vz,
        )
        return self._limit_norm(command)

    def _limit_norm(self, command: ControlVector) -> ControlVector:
        norm = math.sqrt(sum(value * value for value in command))
        if norm <= self.max_acceleration:
            return command
        scale = self.max_acceleration / norm
        return tuple(scale * value for value in command)

    @staticmethod
    def _as_state(state: Sequence[float]) -> StateVector:
        if len(state) != 6:
            raise ValueError('state must contain 6 elements')
        return tuple(float(value) for value in state)

    @staticmethod
    def _as_position(position: Sequence[float]) -> PositionVector:
        if len(position) != 3:
            raise ValueError('reference_position must contain 3 elements')
        return tuple(float(value) for value in position)
