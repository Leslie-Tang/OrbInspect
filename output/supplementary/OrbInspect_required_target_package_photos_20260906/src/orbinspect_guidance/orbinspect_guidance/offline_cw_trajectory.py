"""Offline CW-aware inspection trajectory generation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math

from orbinspect_dynamics.hcw_dynamics import HCWDynamics
from orbinspect_safety.keepout_zones import KeepoutZoneModel


Vector3 = tuple[float, float, float]
StateVector = tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class TrajectoryPoint:
    """A planned LVLH trajectory sample."""

    time: float
    state: StateVector
    reference: Vector3


class OfflineCWTrajectoryGenerator:
    """Generate a waypoint-following inspection trajectory using CW dynamics."""

    def __init__(
        self,
        mean_motion: float,
        max_acceleration: float,
        position_gain: float,
        velocity_gain: float,
        integration_dt: float,
        segment_duration: float,
        safety_margin: float = 2.0,
    ) -> None:
        """Create a deterministic CW rollout generator."""
        if mean_motion <= 0.0:
            raise ValueError('mean_motion must be positive')
        if max_acceleration <= 0.0:
            raise ValueError('max_acceleration must be positive')
        if position_gain < 0.0:
            raise ValueError('position_gain must be non-negative')
        if velocity_gain < 0.0:
            raise ValueError('velocity_gain must be non-negative')
        if integration_dt <= 0.0:
            raise ValueError('integration_dt must be positive')
        if segment_duration <= integration_dt:
            raise ValueError('segment_duration must be greater than integration_dt')

        self.dynamics = HCWDynamics(mean_motion)
        self.max_acceleration = float(max_acceleration)
        self.position_gain = float(position_gain)
        self.velocity_gain = float(velocity_gain)
        self.integration_dt = float(integration_dt)
        self.segment_duration = float(segment_duration)
        self.keepout = KeepoutZoneModel(safety_margin=safety_margin)

    def generate_waypoints(
        self,
        inspection_radius: float,
        z_levels: Sequence[float],
        station_x_extent: float,
        station_y_offset: float,
    ) -> list[Vector3]:
        """Return a conservative inspection loop around the station proxy."""
        if inspection_radius <= 0.0:
            raise ValueError('inspection_radius must be positive')
        if station_x_extent <= 0.0:
            raise ValueError('station_x_extent must be positive')
        if station_y_offset <= 0.0:
            raise ValueError('station_y_offset must be positive')
        if not z_levels:
            raise ValueError('at least one z level is required')

        x_values = (-station_x_extent, -0.5 * station_x_extent, 0.0,
                    0.5 * station_x_extent, station_x_extent)
        y_values = (-station_y_offset, station_y_offset)
        waypoints: list[Vector3] = []
        for z_index, z_value in enumerate(z_levels):
            if z_index % 2 == 0:
                path = [(x, y_values[0], z_value) for x in x_values]
                path += [(x, y_values[1], z_value) for x in reversed(x_values)]
            else:
                path = [(x, y_values[1], z_value) for x in x_values]
                path += [(x, y_values[0], z_value) for x in reversed(x_values)]
            waypoints.extend(self._safe_waypoint(point, inspection_radius) for point in path)
        return self._remove_consecutive_duplicates(waypoints)

    def rollout(
        self,
        initial_state: Sequence[float],
        waypoints: Sequence[Sequence[float]],
        dwell_samples: int = 0,
    ) -> list[TrajectoryPoint]:
        """Roll out a saturated waypoint controller through CW dynamics."""
        if not waypoints:
            raise ValueError('at least one waypoint is required')
        if dwell_samples < 0:
            raise ValueError('dwell_samples must be non-negative')

        state = self._state(initial_state)
        plan: list[TrajectoryPoint] = [TrajectoryPoint(0.0, state, self._vector3(waypoints[0]))]
        time = 0.0
        for waypoint_values in waypoints:
            waypoint = self._vector3(waypoint_values)
            steps = max(1, int(round(self.segment_duration / self.integration_dt)))
            for _ in range(steps):
                command = self._pd_command(state, waypoint)
                state = self.dynamics.rk4_step(state, command, self.integration_dt)
                time += self.integration_dt
                plan.append(TrajectoryPoint(time, state, waypoint))
            for _ in range(dwell_samples):
                command = self._pd_command(state, waypoint)
                state = self.dynamics.rk4_step(state, command, self.integration_dt)
                time += self.integration_dt
                plan.append(TrajectoryPoint(time, state, waypoint))
        return plan

    def _pd_command(self, state: StateVector, waypoint: Vector3) -> Vector3:
        rx, ry, rz, vx, vy, vz = state
        command = (
            self.position_gain * (waypoint[0] - rx) - self.velocity_gain * vx,
            self.position_gain * (waypoint[1] - ry) - self.velocity_gain * vy,
            self.position_gain * (waypoint[2] - rz) - self.velocity_gain * vz,
        )
        norm = math.sqrt(sum(value * value for value in command))
        if norm <= self.max_acceleration:
            return command
        scale = self.max_acceleration / norm
        return tuple(scale * value for value in command)

    def _safe_waypoint(self, point: Vector3, inspection_radius: float) -> Vector3:
        assessment = self.keepout.assess(point)
        if assessment.clearance >= 0.0:
            return point
        push_distance = abs(assessment.clearance) + inspection_radius * 0.05
        direction = assessment.surface_distance.direction
        return (
            point[0] + direction[0] * push_distance,
            point[1] + direction[1] * push_distance,
            point[2] + direction[2] * push_distance,
        )

    @staticmethod
    def _remove_consecutive_duplicates(waypoints: Sequence[Vector3]) -> list[Vector3]:
        unique: list[Vector3] = []
        for waypoint in waypoints:
            if not unique or waypoint != unique[-1]:
                unique.append(waypoint)
        return unique

    @staticmethod
    def _state(values: Sequence[float]) -> StateVector:
        if len(values) != 6:
            raise ValueError('initial_state must contain 6 elements')
        return tuple(float(value) for value in values)

    @staticmethod
    def _vector3(values: Sequence[float]) -> Vector3:
        if len(values) != 3:
            raise ValueError('waypoint must contain 3 elements')
        return (float(values[0]), float(values[1]), float(values[2]))
