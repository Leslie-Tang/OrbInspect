"""Greedy next-best-view planner for inspection coverage."""

from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Sequence
from dataclasses import dataclass
import math
import time

from orbinspect_guidance.waypoint_generator import CandidateWaypoint
from orbinspect_guidance.waypoint_generator import distance
from orbinspect_interfaces.msg import CoverageMap


Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class PlannerWeights:
    """Weights used by the greedy NBV scoring function."""

    coverage: float = 10.0
    distance: float = 0.08
    fuel: float = 0.4
    safety: float = 0.08
    view_quality: float = 1.0


@dataclass(frozen=True)
class ScoredWaypoint:
    """Candidate score and estimated inspection utility."""

    candidate: CandidateWaypoint
    score: float
    coverage_gain: int
    travel_distance: float
    fuel_estimate: float
    view_quality: float
    safety_margin: float


@dataclass(frozen=True)
class PlannerDecision:
    """Selected waypoint and planner bookkeeping."""

    selected: ScoredWaypoint | None
    evaluated_candidates: int
    planning_time: float


class GreedyNBVPlanner:
    """Select the candidate with the best immediate coverage-aware score."""

    def __init__(
        self,
        candidates: Sequence[CandidateWaypoint],
        weights: PlannerWeights | None = None,
        sensor_range: float = 25.0,
    ) -> None:
        if not candidates:
            raise ValueError('at least one candidate waypoint is required')
        if sensor_range <= 0.0:
            raise ValueError('sensor_range must be positive')
        self.candidates = list(candidates)
        self.weights = weights or PlannerWeights()
        self.sensor_range = float(sensor_range)

    def select_next(
        self,
        current_position: Sequence[float],
        coverage_map: CoverageMap,
        visited_waypoints: Iterable[str] = (),
    ) -> PlannerDecision:
        """Return the highest-scoring unvisited safe waypoint."""
        start = time.monotonic()
        visited = set(visited_waypoints)
        scored = [
            self.score_candidate(candidate, current_position, coverage_map)
            for candidate in self.candidates
            if candidate.waypoint_id not in visited
        ]
        selected = max(scored, key=lambda item: item.score) if scored else None
        return PlannerDecision(
            selected=selected,
            evaluated_candidates=len(scored),
            planning_time=time.monotonic() - start,
        )

    def score_candidate(
        self,
        candidate: CandidateWaypoint,
        current_position: Sequence[float],
        coverage_map: CoverageMap,
    ) -> ScoredWaypoint:
        """Compute the weighted greedy NBV score for one candidate."""
        coverage_gain, view_quality = self._coverage_gain(candidate, coverage_map)
        travel_distance = distance(current_position, candidate.position)
        fuel_estimate = travel_distance * 0.001
        score = (
            self.weights.coverage * coverage_gain
            - self.weights.distance * travel_distance
            - self.weights.fuel * fuel_estimate
            + self.weights.safety * candidate.safety_margin
            + self.weights.view_quality * view_quality
        )
        return ScoredWaypoint(
            candidate=candidate,
            score=score,
            coverage_gain=coverage_gain,
            travel_distance=travel_distance,
            fuel_estimate=fuel_estimate,
            view_quality=view_quality,
            safety_margin=candidate.safety_margin,
        )

    def _coverage_gain(
        self,
        candidate: CandidateWaypoint,
        coverage_map: CoverageMap,
    ) -> tuple[int, float]:
        gain = 0
        quality_sum = 0.0
        for target in coverage_map.targets:
            if target.inspected:
                continue
            target_position = (
                float(target.position.x),
                float(target.position.y),
                float(target.position.z),
            )
            target_normal = (
                float(target.normal.x),
                float(target.normal.y),
                float(target.normal.z),
            )
            relative = _subtract(candidate.position, target_position)
            range_to_target = _norm(relative)
            if range_to_target <= 1.0e-9 or range_to_target > self.sensor_range:
                continue
            view_direction = _unit(relative)
            normal_quality = max(0.0, _dot(view_direction, _unit(target_normal)))
            if normal_quality <= 0.25:
                continue
            range_quality = max(0.0, 1.0 - range_to_target / self.sensor_range)
            gain += 1
            quality_sum += 0.5 * normal_quality + 0.5 * range_quality
        if gain == 0:
            return 0, 0.0
        return gain, quality_sum / float(gain)


def _subtract(left: Sequence[float], right: Sequence[float]) -> Vector3:
    return (
        float(left[0]) - float(right[0]),
        float(left[1]) - float(right[1]),
        float(left[2]) - float(right[2]),
    )


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return (
        float(left[0]) * float(right[0])
        + float(left[1]) * float(right[1])
        + float(left[2]) * float(right[2])
    )


def _norm(values: Sequence[float]) -> float:
    return math.sqrt(_dot(values, values))


def _unit(values: Sequence[float]) -> Vector3:
    value_norm = _norm(values)
    if value_norm <= 1.0e-12:
        return (0.0, 0.0, 0.0)
    return (
        float(values[0]) / value_norm,
        float(values[1]) / value_norm,
        float(values[2]) / value_norm,
    )
