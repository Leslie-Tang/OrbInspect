"""Metrics helpers for OrbInspect paper-grade logs."""

from __future__ import annotations

from collections.abc import Sequence
import math


def vector_norm(values: Sequence[float]) -> float:
    """Return the Euclidean norm of a vector."""
    return math.sqrt(sum(float(value) * float(value) for value in values))


def tracking_error_norm(
    position: Sequence[float],
    reference_position: Sequence[float],
) -> float:
    """Return Euclidean position tracking error."""
    if len(position) != 3:
        raise ValueError('position must contain 3 elements')
    if len(reference_position) != 3:
        raise ValueError('reference_position must contain 3 elements')
    return vector_norm(
        float(reference_value) - float(position_value)
        for position_value, reference_value in zip(position, reference_position)
    )


def delta_v_increment(acceleration_norm: float, dt: float) -> float:
    """Return delta-v increment from acceleration norm and elapsed time."""
    if acceleration_norm < 0.0:
        raise ValueError('acceleration_norm must be non-negative')
    if dt < 0.0:
        raise ValueError('dt must be non-negative')
    return float(acceleration_norm) * float(dt)


def is_saturated(acceleration_norm: float, max_acceleration: float) -> bool:
    """Return true when acceleration is at the configured limit."""
    if max_acceleration <= 0.0:
        raise ValueError('max_acceleration must be positive')
    tolerance = max(1.0e-9, 1.0e-6 * max_acceleration)
    return float(acceleration_norm) >= float(max_acceleration) - tolerance
