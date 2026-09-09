"""Hill-Clohessy-Wiltshire relative orbital dynamics."""

from __future__ import annotations

from collections.abc import Sequence


StateVector = tuple[float, float, float, float, float, float]
ControlVector = tuple[float, float, float]


class HCWDynamics:
    """Propagate six-state LVLH relative motion with HCW dynamics."""

    def __init__(self, mean_motion: float) -> None:
        """Create an HCW model with mean motion in rad/s."""
        if mean_motion <= 0.0:
            raise ValueError('mean_motion must be positive')

        self.mean_motion = float(mean_motion)

    def derivative(
        self,
        state: Sequence[float],
        control: Sequence[float],
    ) -> StateVector:
        """Return x_dot for state [rx, ry, rz, vx, vy, vz]."""
        rx, _ry, rz, vx, vy, vz = self._as_state(state)
        ax, ay, az = self._as_control(control)
        n = self.mean_motion

        return (
            vx,
            vy,
            vz,
            3.0 * n * n * rx + 2.0 * n * vy + ax,
            -2.0 * n * vx + ay,
            -n * n * rz + az,
        )

    def rk4_step(
        self,
        state: Sequence[float],
        control: Sequence[float],
        dt: float,
    ) -> StateVector:
        """Advance the HCW state by one fixed RK4 step."""
        if dt <= 0.0:
            raise ValueError('dt must be positive')

        x = self._as_state(state)
        u = self._as_control(control)

        k1 = self.derivative(x, u)
        k2 = self.derivative(self._add_scaled(x, k1, 0.5 * dt), u)
        k3 = self.derivative(self._add_scaled(x, k2, 0.5 * dt), u)
        k4 = self.derivative(self._add_scaled(x, k3, dt), u)

        return tuple(
            x_i + dt / 6.0 * (k1_i + 2.0 * k2_i + 2.0 * k3_i + k4_i)
            for x_i, k1_i, k2_i, k3_i, k4_i in zip(x, k1, k2, k3, k4)
        )

    @staticmethod
    def _add_scaled(
        state: StateVector,
        derivative: StateVector,
        scale: float,
    ) -> StateVector:
        return tuple(x_i + scale * dx_i for x_i, dx_i in zip(state, derivative))

    @staticmethod
    def _as_state(state: Sequence[float]) -> StateVector:
        if len(state) != 6:
            raise ValueError('state must contain 6 elements')
        return tuple(float(value) for value in state)

    @staticmethod
    def _as_control(control: Sequence[float]) -> ControlVector:
        if len(control) != 3:
            raise ValueError('control must contain 3 elements')
        return tuple(float(value) for value in control)
