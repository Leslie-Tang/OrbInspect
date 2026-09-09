"""Discrete CW trajectory controller."""

from __future__ import annotations

from collections.abc import Sequence
import math

import numpy as np
from scipy.optimize import minimize


StateVector = tuple[float, float, float, float, float, float]
PositionVector = tuple[float, float, float]
ControlVector = tuple[float, float, float]


class LQRController:
    """Saturated trajectory tracker with discrete CW LQR or PD fallback."""

    def __init__(
        self,
        position_gain: float,
        velocity_gain: float,
        max_acceleration: float,
        *,
        controller_type: str = 'pd',
        mean_motion: float = 0.0011313666536110225,
        control_dt: float = 0.1,
        state_weights: Sequence[float] | None = None,
        control_weights: Sequence[float] | None = None,
        riccati_iterations: int = 200,
        mpc_horizon: int = 8,
        mpc_max_iterations: int = 35,
    ) -> None:
        """Create a saturated controller for CW relative-motion tracking."""
        if position_gain < 0.0:
            raise ValueError('position_gain must be non-negative')
        if velocity_gain < 0.0:
            raise ValueError('velocity_gain must be non-negative')
        if max_acceleration <= 0.0:
            raise ValueError('max_acceleration must be positive')
        if mean_motion <= 0.0:
            raise ValueError('mean_motion must be positive')
        if control_dt <= 0.0:
            raise ValueError('control_dt must be positive')
        if riccati_iterations <= 0:
            raise ValueError('riccati_iterations must be positive')
        if mpc_horizon <= 0:
            raise ValueError('mpc_horizon must be positive')
        if mpc_max_iterations <= 0:
            raise ValueError('mpc_max_iterations must be positive')

        self.position_gain = float(position_gain)
        self.velocity_gain = float(velocity_gain)
        self.max_acceleration = float(max_acceleration)
        self.controller_type = str(controller_type).lower()
        self.mean_motion = float(mean_motion)
        self.control_dt = float(control_dt)
        self.state_weights = tuple(state_weights or (1.0, 1.0, 1.0, 80.0, 80.0, 80.0))
        self.control_weights = tuple(control_weights or (4000.0, 4000.0, 4000.0))
        self.riccati_iterations = int(riccati_iterations)
        self.mpc_horizon = int(mpc_horizon)
        self.mpc_max_iterations = int(mpc_max_iterations)
        if self.controller_type not in ('pd', 'lqr', 'mpc'):
            raise ValueError('controller_type must be pd, lqr, or mpc')
        self.a_d, self.b_d = self._discrete_cw_matrices()
        self.q = _positive_diagonal(self.state_weights, 6, 'state_weights')
        self.r = _positive_diagonal(self.control_weights, 3, 'control_weights')
        self.lqr_gain = self._build_lqr_gain() if self.controller_type in ('lqr', 'mpc') else None
        self._mpc_guess = np.zeros(3 * self.mpc_horizon, dtype=float)

    def compute_control(
        self,
        state: Sequence[float],
        reference_position: Sequence[float],
        reference_velocity: Sequence[float] | None = None,
        feedforward_acceleration: Sequence[float] | None = None,
    ) -> ControlVector:
        """
        Return saturated acceleration command [ax, ay, az].

        The controller is a PD trajectory tracker with an optional acceleration
        feed-forward term. It keeps the original waypoint interface while
        allowing offline CW trajectory samples to provide velocity and nominal
        acceleration references.
        """
        state_vector = self._as_state(state)
        reference_state = self._reference_state(reference_position, reference_velocity)
        feedforward = (
            self._as_position(feedforward_acceleration)
            if feedforward_acceleration is not None
            else (0.0, 0.0, 0.0)
        )
        error = tuple(value - reference for value, reference in zip(state_vector, reference_state))
        if self.controller_type == 'mpc':
            correction = self._mpc_feedback(error)
        elif self.controller_type == 'lqr':
            correction = self._lqr_feedback(error)
        else:
            correction = self._pd_feedback(error)
        command = tuple(feedforward[index] + correction[index] for index in range(3))
        return self._limit_norm(command)

    def _pd_feedback(self, error: StateVector) -> ControlVector:
        rx_error, ry_error, rz_error, vx_error, vy_error, vz_error = error
        return (
            -self.position_gain * rx_error - self.velocity_gain * vx_error,
            -self.position_gain * ry_error - self.velocity_gain * vy_error,
            -self.position_gain * rz_error - self.velocity_gain * vz_error,
        )

    def _lqr_feedback(self, error: StateVector) -> ControlVector:
        if self.lqr_gain is None:
            raise RuntimeError('lqr_gain is not initialized')
        control = -self.lqr_gain @ np.asarray(error, dtype=float)
        return (float(control[0]), float(control[1]), float(control[2]))

    def _build_lqr_gain(self) -> np.ndarray:
        p = self.q.copy()
        for _ in range(self.riccati_iterations):
            gain_denominator = self.r + self.b_d.T @ p @ self.b_d
            gain_numerator = self.b_d.T @ p @ self.a_d
            gain = np.linalg.solve(gain_denominator, gain_numerator)
            p = self.q + self.a_d.T @ p @ self.a_d - self.a_d.T @ p @ self.b_d @ gain
        return np.linalg.solve(self.r + self.b_d.T @ p @ self.b_d, self.b_d.T @ p @ self.a_d)

    def _mpc_feedback(self, error: StateVector) -> ControlVector:
        error_array = np.asarray(error, dtype=float)
        warm_start = self._warm_start_guess(error_array)
        bounds = [(-self.max_acceleration, self.max_acceleration)] * (3 * self.mpc_horizon)
        result = minimize(
            self._mpc_cost,
            warm_start,
            args=(error_array,),
            method='SLSQP',
            bounds=bounds,
            options={
                'maxiter': self.mpc_max_iterations,
                'ftol': 1.0e-5,
                'disp': False,
            },
        )
        if not result.success:
            return self._lqr_feedback(error)
        solution = np.asarray(result.x, dtype=float)
        self._mpc_guess = self._shift_mpc_solution(solution)
        command = solution[:3]
        return tuple(float(value) for value in command)

    def _mpc_cost(self, flattened_controls: np.ndarray, initial_error: np.ndarray) -> float:
        state = initial_error.copy()
        controls = flattened_controls.reshape(self.mpc_horizon, 3)
        total = 0.0
        for control in controls:
            state = self.a_d @ state + self.b_d @ control
            total += float(state.T @ self.q @ state + control.T @ self.r @ control)
            excess = max(0.0, np.linalg.norm(control) - self.max_acceleration)
            total += 1.0e6 * excess * excess
        total += float(2.0 * state.T @ self.q @ state)
        return total

    def _warm_start_guess(self, error: np.ndarray) -> np.ndarray:
        if np.linalg.norm(self._mpc_guess) > 0.0:
            return self._mpc_guess.copy()
        if self.lqr_gain is None:
            return self._mpc_guess.copy()
        guess = []
        state = error.copy()
        for _ in range(self.mpc_horizon):
            control = -self.lqr_gain @ state
            control = np.clip(control, -self.max_acceleration, self.max_acceleration)
            guess.append(control)
            state = self.a_d @ state + self.b_d @ control
        return np.asarray(guess, dtype=float).reshape(-1)

    def _shift_mpc_solution(self, solution: np.ndarray) -> np.ndarray:
        controls = solution.reshape(self.mpc_horizon, 3)
        shifted = np.vstack([controls[1:], controls[-1:]])
        return shifted.reshape(-1)

    def _discrete_cw_matrices(self) -> tuple[np.ndarray, np.ndarray]:
        a_c, b_c = _cw_continuous_matrices(self.mean_motion)
        return np.eye(6) + self.control_dt * a_c, self.control_dt * b_c

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

    @staticmethod
    def _reference_state(
        reference_position: Sequence[float],
        reference_velocity: Sequence[float] | None,
    ) -> StateVector:
        position = LQRController._as_position(reference_position)
        velocity = (
            LQRController._as_position(reference_velocity)
            if reference_velocity is not None
            else (0.0, 0.0, 0.0)
        )
        return position + velocity


def _cw_continuous_matrices(mean_motion: float) -> tuple[np.ndarray, np.ndarray]:
    """Return continuous-time CW matrices for x=[r, v], u=acceleration."""
    n = float(mean_motion)
    a = np.zeros((6, 6), dtype=float)
    a[0, 3] = 1.0
    a[1, 4] = 1.0
    a[2, 5] = 1.0
    a[3, 0] = 3.0 * n * n
    a[3, 4] = 2.0 * n
    a[4, 3] = -2.0 * n
    a[5, 2] = -n * n
    b = np.zeros((6, 3), dtype=float)
    b[3, 0] = 1.0
    b[4, 1] = 1.0
    b[5, 2] = 1.0
    return a, b


def _positive_diagonal(
    values: Sequence[float],
    expected_length: int,
    name: str,
) -> np.ndarray:
    if len(values) != expected_length:
        raise ValueError(f'{name} must contain {expected_length} elements')
    diagonal = np.asarray([float(value) for value in values], dtype=float)
    if np.any(diagonal <= 0.0):
        raise ValueError(f'{name} entries must be positive')
    return np.diag(diagonal)
