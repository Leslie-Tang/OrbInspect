"""Offline dynamics-aware inspection planning experiment runner."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Iterable

import matplotlib.pyplot as plt

from orbinspect_guidance.offline_coverage_planner import CandidateViewpoint
from orbinspect_guidance.offline_coverage_planner import ControlVector
from orbinspect_guidance.offline_coverage_planner import cross
from orbinspect_guidance.offline_coverage_planner import distance
from orbinspect_guidance.offline_coverage_planner import dot
from orbinspect_guidance.offline_coverage_planner import OfflineCoveragePlanner
from orbinspect_guidance.offline_coverage_planner import OfflinePlannerConfig
from orbinspect_guidance.offline_coverage_planner import scale
from orbinspect_guidance.offline_coverage_planner import StateVector
from orbinspect_guidance.offline_coverage_planner import TransferEstimate
from orbinspect_guidance.offline_coverage_planner import unit

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised on minimal macOS Python installs.
    yaml = None


plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['svg.fonttype'] = 'none'
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42
plt.rcParams['axes.linewidth'] = 1.0
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False
plt.rcParams['legend.frameon'] = False

METHOD_COLORS = {
    'set_cover_cw_tour': '#0F4D92',
    'certified_graph_search': '#1B6B5A',
    'proposed_safe_cw_nbv': '#7884B4',
    'coverage_greedy': '#B64342',
    'safe_coverage_greedy': '#E28E2C',
    'distance_greedy': '#7BAA5B',
    'fuel_greedy': '#9A4D8E',
    'random_safe': '#767676',
}
METHOD_LABELS_SHORT = {
    'set_cover_cw_tour': 'Proposed',
    'certified_graph_search': 'Certified',
    'proposed_safe_cw_nbv': 'CW-NBV',
    'coverage_greedy': 'Coverage',
    'safe_coverage_greedy': 'Safe cov.',
    'distance_greedy': 'Nearest',
    'fuel_greedy': 'Fuel',
    'random_safe': 'Random',
    'abl_no_transfer_cost': 'No transfer',
    'abl_no_clearance_filter': 'No clearance',
    'abl_no_input_check': 'No input',
    'abl_unweighted_coverage': 'Unweighted',
}

SET_COVER_METHODS = frozenset({
    'set_cover_cw_tour',
    'abl_no_transfer_cost',
    'abl_no_clearance_filter',
    'abl_no_input_check',
    'abl_unweighted_coverage',
})


@dataclass(frozen=True)
class ExperimentConfig:
    """Configuration for offline paper comparison experiments."""

    output_root: Path = Path('data/results')
    run_id: str = ''
    geometry_backend: str = 'mesh'
    mesh_target_count: int = 180
    mesh_occlusion_max_triangles: int = 800
    candidate_radius: float = 32.0
    candidate_stride: int = 2
    coverage_threshold: float = 0.35
    coverage_stop_ratio: float = 0.98
    max_viewpoints: int = 18
    min_new_targets: int = 1
    transfer_duration: float = 90.0
    integration_dt: float = 2.0
    max_acceleration: float = 0.018
    safety_margin: float = 2.0
    initial_state: StateVector = (0.0, -35.0, 10.0, 0.0, 0.0, 0.0)
    methods: tuple[str, ...] = (
        'set_cover_cw_tour',
        'proposed_safe_cw_nbv',
        'coverage_greedy',
        'safe_coverage_greedy',
        'distance_greedy',
        'fuel_greedy',
        'random_safe',
    )
    random_seed: int = 7
    proposed_beam_width: int = 6
    proposed_lookahead_depth: int = 2
    cw_energy_weight: float = 5.0
    cw_tracking_weight: float = 0.18
    cw_safety_weight: float = 120.0
    certified_candidate_limit: int = 18
    certified_time_limit_s: float = 8.0
    certified_max_expansions: int = 150000


@dataclass(frozen=True)
class MethodStep:
    """One selected viewpoint and transfer in a comparison method."""

    sequence: int
    candidate: CandidateViewpoint
    new_targets: frozenset[str]
    cumulative_coverage: float
    transfer: TransferEstimate
    score: float
    dynamic_cost: float


@dataclass(frozen=True)
class MethodResult:
    """Complete result for one offline planning method."""

    method: str
    steps: tuple[MethodStep, ...]
    trajectory: tuple[tuple[float, StateVector, ControlVector], ...]
    coverage_timeline: tuple[tuple[float, float, int], ...]
    summary: dict[str, float | int | str | bool]


class OfflinePlanningExperiment:
    """Compare dynamics-aware inspection planning against strong baselines."""

    def __init__(self, config: ExperimentConfig) -> None:
        """Create a comparison experiment with shared geometry and dynamics."""
        self.config = config
        self.base_planner = OfflineCoveragePlanner(_planner_config(config))
        self.targets = tuple(self.base_planner.load_targets())
        self.candidates = tuple(self.base_planner.generate_candidate_viewpoints(self.targets))
        self.visibility = self.base_planner.compute_visibility_matrix(
            self.targets,
            self.candidates,
        )
        self.inspectable_targets = self._inspectable_targets()
        self.inspectable_area = self._area_gain(self.inspectable_targets)
        self._transfer_cache: dict[
            tuple[tuple[float, ...], str],
            TransferEstimate,
        ] = {}

    def run(self) -> tuple[MethodResult, ...]:
        """Run all configured planning methods."""
        return tuple(self.run_method(method) for method in self.config.methods)

    def run_method(self, method: str) -> MethodResult:
        """Run a single planning method with shared visibility and CW evaluator."""
        start = perf_counter()
        covered: set[str] = set()
        remaining = {candidate.candidate_id: candidate for candidate in self.candidates}
        current_state = self.config.initial_state
        current_time = 0.0
        steps: list[MethodStep] = []

        if method == 'certified_graph_search':
            return self._run_certified_graph_search(start)

        if method in SET_COVER_METHODS:
            return self._run_set_cover_cw_tour(start, method)

        while (
            self._coverage_ratio(covered) < self.config.coverage_stop_ratio
            and remaining
            and len(steps) < self.config.max_viewpoints
        ):
            decision = self._select_candidate(method, current_state, covered, remaining)
            if decision is None:
                break
            candidate, new_targets, transfer, score = decision
            dynamic_cost = self._dynamic_transfer_cost(transfer)
            if len(new_targets) < self.config.min_new_targets:
                remaining.pop(candidate.candidate_id, None)
                continue
            covered.update(new_targets)
            current_state = transfer.next_state
            current_time += self.config.transfer_duration
            transfer = self.base_planner._offset_transfer_time(transfer, current_time)
            steps.append(MethodStep(
                sequence=len(steps),
                candidate=candidate,
                new_targets=new_targets,
                cumulative_coverage=self._coverage_ratio(covered),
                transfer=transfer,
                score=score,
                dynamic_cost=dynamic_cost,
            ))
            remaining.pop(candidate.candidate_id, None)

        trajectory = tuple(sample for step in steps for sample in step.transfer.trajectory)
        coverage_timeline = tuple(self._coverage_timeline(steps))
        summary = self._summary(
            method,
            steps,
            trajectory,
            coverage_timeline,
            planning_time=perf_counter() - start,
        )
        return MethodResult(
            method=method,
            steps=tuple(steps),
            trajectory=trajectory,
            coverage_timeline=coverage_timeline,
            summary=summary,
        )

    def _run_set_cover_cw_tour(self, start_time: float, method: str) -> MethodResult:
        selected_candidates = self._weighted_set_cover_candidates(method)
        ordered_candidates = self._order_candidates_by_cw_cost(selected_candidates, method)
        covered: set[str] = set()
        current_state = self.config.initial_state
        current_time = 0.0
        steps: list[MethodStep] = []

        for candidate in ordered_candidates[:self.config.max_viewpoints]:
            visible = self.visibility.visible_targets_by_candidate[candidate.candidate_id]
            new_targets = frozenset(visible - covered)
            if not new_targets:
                continue
            transfer = self._estimate_transfer(current_state, candidate)
            score = self._score(
                method,
                current_state,
                candidate,
                new_targets,
                transfer,
            )
            dynamic_cost = self._dynamic_transfer_cost(transfer)
            covered.update(new_targets)
            current_state = transfer.next_state
            current_time += self.config.transfer_duration
            transfer = self.base_planner._offset_transfer_time(transfer, current_time)
            steps.append(MethodStep(
                sequence=len(steps),
                candidate=candidate,
                new_targets=new_targets,
                cumulative_coverage=self._coverage_ratio(covered),
                transfer=transfer,
                score=score,
                dynamic_cost=dynamic_cost,
            ))
            if self._coverage_ratio(covered) >= self.config.coverage_stop_ratio:
                break

        trajectory = tuple(sample for step in steps for sample in step.transfer.trajectory)
        coverage_timeline = tuple(self._coverage_timeline(steps))
        summary = self._summary(
            method,
            steps,
            trajectory,
            coverage_timeline,
            planning_time=perf_counter() - start_time,
        )
        return MethodResult(
            method=method,
            steps=tuple(steps),
            trajectory=trajectory,
            coverage_timeline=coverage_timeline,
            summary=summary,
        )

    def _run_certified_graph_search(self, start_time: float) -> MethodResult:
        """Solve the reduced finite inspection graph exactly when limits permit."""
        candidates = tuple(self._certification_candidates())
        target_ids = tuple(sorted(
            {
                target_id
                for candidate in candidates
                for target_id in self.visibility.visible_targets_by_candidate[
                    candidate.candidate_id
                ]
            }
        ))
        target_index = {target_id: index for index, target_id in enumerate(target_ids)}
        target_weights = tuple(
            self.base_planner.target_area_by_id.get(target_id, 1.0)
            for target_id in target_ids
        )
        target_mask_by_candidate = tuple(
            _target_mask(
                self.visibility.visible_targets_by_candidate[candidate.candidate_id],
                target_index,
            )
            for candidate in candidates
        )
        required_area = self.config.coverage_stop_ratio * max(
            self.base_planner.total_inspection_area,
            1.0,
        )
        max_depth = min(self.config.max_viewpoints, len(candidates))
        edge_transfers = self._certified_edge_transfers(candidates)

        parent: dict[tuple[int, int], tuple[int, int] | None] = {(0, -1): None}
        costs: dict[tuple[int, int], float] = {(0, -1): 0.0}
        coverage_cache: dict[int, int] = {0: 0}
        area_cache: dict[int, float] = {0: 0.0}
        best_state: tuple[int, int] | None = None
        best_cost = math.inf
        expanded = 0
        timed_out = False
        max_expansions_hit = False

        def covered_target_mask(candidate_mask: int) -> int:
            cached = coverage_cache.get(candidate_mask)
            if cached is not None:
                return cached
            covered_mask = 0
            for index, candidate_target_mask in enumerate(target_mask_by_candidate):
                if candidate_mask & (1 << index):
                    covered_mask |= candidate_target_mask
            coverage_cache[candidate_mask] = covered_mask
            return covered_mask

        def covered_area(candidate_mask: int) -> float:
            cached = area_cache.get(candidate_mask)
            if cached is not None:
                return cached
            area = _target_mask_area(covered_target_mask(candidate_mask), target_weights)
            area_cache[candidate_mask] = area
            return area

        frontier = [(0, -1)]
        for _depth in range(max_depth):
            next_frontier: list[tuple[int, int]] = []
            for candidate_mask, last_index in frontier:
                if perf_counter() - start_time > self.config.certified_time_limit_s:
                    timed_out = True
                    break
                if expanded >= self.config.certified_max_expansions:
                    max_expansions_hit = True
                    break
                current_state = (candidate_mask, last_index)
                current_cost = costs[current_state]
                if covered_area(candidate_mask) >= required_area:
                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_state = current_state
                    continue

                current_target_mask = covered_target_mask(candidate_mask)
                for next_index in range(len(candidates)):
                    next_bit = 1 << next_index
                    if candidate_mask & next_bit:
                        continue
                    new_target_mask = (
                        target_mask_by_candidate[next_index] & ~current_target_mask
                    )
                    if _bit_count(new_target_mask) < self.config.min_new_targets:
                        continue
                    transfer = edge_transfers.get((last_index, next_index))
                    if transfer is None or not transfer.feasible:
                        continue
                    expanded += 1
                    next_cost = current_cost + self._dynamic_transfer_cost(transfer)
                    if next_cost >= best_cost:
                        continue
                    next_state = (candidate_mask | next_bit, next_index)
                    if next_cost < costs.get(next_state, math.inf):
                        costs[next_state] = next_cost
                        parent[next_state] = current_state
                        next_frontier.append(next_state)
                    if covered_area(next_state[0]) >= required_area and next_cost < best_cost:
                        best_cost = next_cost
                        best_state = next_state
            if timed_out or max_expansions_hit:
                break
            frontier = next_frontier
            if not frontier:
                break

        if best_state is None:
            sequence = tuple()
            certificate_status = 'infeasible_or_limit_reached'
        else:
            sequence = _reconstruct_candidate_sequence(best_state, parent, candidates)
            certificate_status = (
                'optimal'
                if not timed_out and not max_expansions_hit
                else 'incumbent'
            )
        return self._materialize_certified_sequence(
            'certified_graph_search',
            sequence,
            candidate_pool=candidates,
            edge_transfers=edge_transfers,
            planning_time=perf_counter() - start_time,
            extra_summary={
                'certificate_status': certificate_status,
                'certificate_expansions': expanded,
                'certificate_candidate_count': len(candidates),
                'certificate_target_count': len(target_ids),
                'certificate_objective_cost': (
                    best_cost if math.isfinite(best_cost) else ''
                ),
                'certificate_time_limit_s': self.config.certified_time_limit_s,
                'certificate_max_expansions': self.config.certified_max_expansions,
            },
        )

    def _certified_edge_transfers(
        self,
        candidates: tuple[CandidateViewpoint, ...],
    ) -> dict[tuple[int, int], TransferEstimate]:
        """Precompute canonical rest-to-rest HCW graph edges for certification."""
        transfers: dict[tuple[int, int], TransferEstimate] = {}
        for to_index, to_candidate in enumerate(candidates):
            transfers[(-1, to_index)] = self._estimate_transfer_from_state(
                self.config.initial_state,
                to_candidate,
            )
        for from_index, from_candidate in enumerate(candidates):
            from_state: StateVector = (
                from_candidate.position[0],
                from_candidate.position[1],
                from_candidate.position[2],
                0.0,
                0.0,
                0.0,
            )
            for to_index, to_candidate in enumerate(candidates):
                if from_index == to_index:
                    continue
                transfers[(from_index, to_index)] = self._estimate_transfer_from_state(
                    from_state,
                    to_candidate,
                )
        return transfers

    def _weighted_set_cover_candidates(self, method: str) -> list[CandidateViewpoint]:
        covered: set[str] = set()
        selected: list[CandidateViewpoint] = []
        remaining = {candidate.candidate_id: candidate for candidate in self.candidates}
        current_state = self.config.initial_state
        while (
            self._coverage_ratio(covered) < self.config.coverage_stop_ratio
            and remaining
            and len(selected) < self.config.max_viewpoints
        ):
            best = None
            for candidate in remaining.values():
                visible = self.visibility.visible_targets_by_candidate[candidate.candidate_id]
                new_targets = frozenset(visible - covered)
                if len(new_targets) < self.config.min_new_targets:
                    continue
                gain = self._area_gain(new_targets)
                transfer = self._estimate_transfer(current_state, candidate)
                if not self._transfer_acceptable(method, transfer):
                    continue
                gain_for_score = (
                    float(len(new_targets))
                    if method == 'abl_unweighted_coverage'
                    else gain
                )
                dynamic_cost = 0.0 if method == 'abl_no_transfer_cost' else self._dynamic_transfer_cost(transfer)
                safety_credit = (
                    0.0 if method == 'abl_no_clearance_filter'
                    else 0.2 * max(0.0, min(transfer.min_clearance, 10.0))
                )
                score = gain_for_score / max(1.0, 1.0 + dynamic_cost) + safety_credit
                if best is None or score > best[0]:
                    best = (score, candidate, new_targets, transfer)
            if best is None:
                break
            _score, candidate, new_targets, transfer = best
            selected.append(candidate)
            covered.update(new_targets)
            current_state = transfer.next_state
            remaining.pop(candidate.candidate_id, None)
        return selected

    def _certification_candidates(self) -> list[CandidateViewpoint]:
        """Return a reduced candidate graph for exact certification runs."""
        ranked = []
        for candidate in self.candidates:
            visible = self.visibility.visible_targets_by_candidate[candidate.candidate_id]
            if not visible:
                continue
            gain = self._area_gain(visible)
            clearance_score = max(0.0, min(candidate.safety_margin, 10.0))
            score = gain + 0.01 * clearance_score
            ranked.append((score, gain, candidate))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [
            candidate
            for _score, _gain, candidate in ranked[:max(1, self.config.certified_candidate_limit)]
        ]

    def _materialize_candidate_sequence(
        self,
        method: str,
        candidates: tuple[CandidateViewpoint, ...],
        planning_time: float,
        extra_summary: dict[str, float | int | str | bool] | None = None,
    ) -> MethodResult:
        """Roll out an ordered candidate sequence into standard result outputs."""
        covered: set[str] = set()
        current_state = self.config.initial_state
        current_time = 0.0
        steps: list[MethodStep] = []
        for candidate in candidates[:self.config.max_viewpoints]:
            visible = self.visibility.visible_targets_by_candidate[candidate.candidate_id]
            new_targets = frozenset(visible - covered)
            if not new_targets:
                continue
            transfer = self._estimate_transfer_from_state(current_state, candidate)
            dynamic_cost = self._dynamic_transfer_cost(transfer)
            score = self._score(
                method,
                current_state,
                candidate,
                new_targets,
                transfer,
            )
            covered.update(new_targets)
            current_state = transfer.next_state
            current_time += self.config.transfer_duration
            transfer = self.base_planner._offset_transfer_time(transfer, current_time)
            steps.append(MethodStep(
                sequence=len(steps),
                candidate=candidate,
                new_targets=new_targets,
                cumulative_coverage=self._coverage_ratio(covered),
                transfer=transfer,
                score=score,
                dynamic_cost=dynamic_cost,
            ))
            if self._coverage_ratio(covered) >= self.config.coverage_stop_ratio:
                break

        trajectory = tuple(sample for step in steps for sample in step.transfer.trajectory)
        coverage_timeline = tuple(self._coverage_timeline(steps))
        summary = self._summary(
            method,
            steps,
            trajectory,
            coverage_timeline,
            planning_time=planning_time,
        )
        if extra_summary:
            summary.update(extra_summary)
        return MethodResult(
            method=method,
            steps=tuple(steps),
            trajectory=trajectory,
            coverage_timeline=coverage_timeline,
            summary=summary,
        )

    def _materialize_certified_sequence(
        self,
        method: str,
        candidates: tuple[CandidateViewpoint, ...],
        candidate_pool: tuple[CandidateViewpoint, ...],
        edge_transfers: dict[tuple[int, int], TransferEstimate],
        planning_time: float,
        extra_summary: dict[str, float | int | str | bool] | None = None,
    ) -> MethodResult:
        """Roll out an exact graph-search sequence with canonical graph edges."""
        candidate_index_by_id = {
            candidate.candidate_id: index
            for index, candidate in enumerate(candidate_pool)
        }
        covered: set[str] = set()
        current_time = 0.0
        previous_index = -1
        steps: list[MethodStep] = []
        for candidate in candidates[:self.config.max_viewpoints]:
            candidate_index = candidate_index_by_id[candidate.candidate_id]
            visible = self.visibility.visible_targets_by_candidate[candidate.candidate_id]
            new_targets = frozenset(visible - covered)
            if not new_targets:
                previous_index = candidate_index
                continue
            transfer = edge_transfers[(previous_index, candidate_index)]
            dynamic_cost = self._dynamic_transfer_cost(transfer)
            covered.update(new_targets)
            current_time += self.config.transfer_duration
            transfer = self.base_planner._offset_transfer_time(transfer, current_time)
            steps.append(MethodStep(
                sequence=len(steps),
                candidate=candidate,
                new_targets=new_targets,
                cumulative_coverage=self._coverage_ratio(covered),
                transfer=transfer,
                score=-dynamic_cost,
                dynamic_cost=dynamic_cost,
            ))
            previous_index = candidate_index
            if self._coverage_ratio(covered) >= self.config.coverage_stop_ratio:
                break

        trajectory = tuple(sample for step in steps for sample in step.transfer.trajectory)
        coverage_timeline = tuple(self._coverage_timeline(steps))
        summary = self._summary(
            method,
            steps,
            trajectory,
            coverage_timeline,
            planning_time=planning_time,
        )
        if extra_summary:
            summary.update(extra_summary)
        return MethodResult(
            method=method,
            steps=tuple(steps),
            trajectory=trajectory,
            coverage_timeline=coverage_timeline,
            summary=summary,
        )

    def _order_candidates_by_cw_cost(
        self,
        candidates: list[CandidateViewpoint],
        method: str = 'set_cover_cw_tour',
    ) -> list[CandidateViewpoint]:
        ordered: list[CandidateViewpoint] = []
        remaining = list(candidates)
        current_state = self.config.initial_state
        while remaining:
            best = None
            for candidate in remaining:
                transfer = self._estimate_transfer(current_state, candidate)
                if not self._transfer_acceptable(method, transfer):
                    continue
                score = self._dynamic_transfer_cost(transfer)
                if best is None or score < best[0]:
                    best = (score, candidate, transfer)
            if best is None:
                break
            _score, candidate, transfer = best
            ordered.append(candidate)
            current_state = transfer.next_state
            remaining.remove(candidate)
        return ordered

    def save(self, results: tuple[MethodResult, ...]) -> Path:
        """Save paper-ready comparison CSV, JSON, and figures."""
        run_dir = self._run_dir()
        raw_dir = run_dir / 'raw'
        figures_dir = run_dir / 'figures'
        config_dir = run_dir / 'config_snapshot'
        output_dirs = (
            raw_dir, figures_dir, config_dir, run_dir / 'rosbag', run_dir / 'videos',
        )
        for directory in output_dirs:
            directory.mkdir(parents=True, exist_ok=True)

        self._write_method_comparison(raw_dir / 'method_comparison.csv', results)
        self._write_all_planner_rows(raw_dir / 'planner.csv', results)
        self._write_all_viewpoints(raw_dir / 'viewpoints.csv', results)
        self._write_all_trajectories(raw_dir / 'trajectory.csv', results)
        self._write_all_attitudes(raw_dir / 'attitude.csv', results)
        self._write_all_coverage(raw_dir / 'coverage.csv', results)
        self._write_summary(run_dir / 'summary.json', results)
        self._write_summary_md(run_dir / 'summary.md', results)
        _write_json(config_dir / 'offline_planning_experiment_config.json', self._config_dict())
        self._plot_coverage(figures_dir / 'coverage_comparison.png', results)
        self._plot_delta_v(figures_dir / 'delta_v_comparison.png', results)
        self._plot_energy_efficiency(figures_dir / 'energy_efficiency_comparison.png', results)
        self._plot_safety(figures_dir / 'safety_comparison.png', results)
        self._plot_peak_input(figures_dir / 'peak_input_comparison.png', results)
        return run_dir

    def _select_candidate(
        self,
        method: str,
        current_state: StateVector,
        covered: set[str],
        remaining: dict[str, CandidateViewpoint],
    ) -> tuple[CandidateViewpoint, frozenset[str], TransferEstimate, float] | None:
        if method == 'proposed_safe_cw_nbv':
            return self._select_proposed_lookahead(current_state, covered, remaining)

        scored = []
        for candidate in remaining.values():
            visible = self.visibility.visible_targets_by_candidate[candidate.candidate_id]
            new_targets = frozenset(visible - covered)
            if not new_targets:
                continue
            transfer = self._estimate_transfer(current_state, candidate)
            if method in {'safe_coverage_greedy', 'fuel_greedy'} and not transfer.feasible:
                continue
            score = self._score(method, current_state, candidate, new_targets, transfer)
            scored.append((score, candidate, new_targets, transfer))
        if not scored:
            return None
        if method == 'random_safe':
            feasible = [item for item in scored if item[3].feasible]
            pool = feasible or scored
            index = _deterministic_index(self.config.random_seed, len(covered), len(pool))
            score, candidate, new_targets, transfer = pool[index]
            return candidate, new_targets, transfer, score
        score, candidate, new_targets, transfer = max(scored, key=lambda item: item[0])
        return candidate, new_targets, transfer, score

    def _select_proposed_lookahead(
        self,
        current_state: StateVector,
        covered: set[str],
        remaining: dict[str, CandidateViewpoint],
    ) -> tuple[CandidateViewpoint, frozenset[str], TransferEstimate, float] | None:
        first_layer = self._rank_candidates(
            current_state,
            covered,
            remaining,
            method='proposed_safe_cw_nbv',
            limit=max(1, self.config.proposed_beam_width),
        )
        if not first_layer:
            return None

        best = None
        for first_score, first_candidate, first_targets, first_transfer in first_layer:
            future_covered = set(covered)
            future_covered.update(first_targets)
            future_remaining = dict(remaining)
            future_remaining.pop(first_candidate.candidate_id, None)
            lookahead_score = first_score
            lookahead_state = first_transfer.next_state

            depth = max(1, self.config.proposed_lookahead_depth)
            discount = 0.55
            for depth_index in range(1, depth):
                next_layer = self._rank_candidates(
                    lookahead_state,
                    future_covered,
                    future_remaining,
                    method='proposed_safe_cw_nbv',
                    limit=max(1, self.config.proposed_beam_width),
                )
                if not next_layer:
                    break
                next_score, next_candidate, next_targets, next_transfer = next_layer[0]
                lookahead_score += (discount ** depth_index) * next_score
                future_covered.update(next_targets)
                future_remaining.pop(next_candidate.candidate_id, None)
                lookahead_state = next_transfer.next_state

            if best is None or lookahead_score > best[0]:
                best = (
                    lookahead_score,
                    first_candidate,
                    first_targets,
                    first_transfer,
                )

        if best is None:
            return None
        score, candidate, new_targets, transfer = best
        return candidate, new_targets, transfer, score

    def _rank_candidates(
        self,
        current_state: StateVector,
        covered: set[str],
        remaining: dict[str, CandidateViewpoint],
        method: str,
        limit: int,
    ) -> list[tuple[float, CandidateViewpoint, frozenset[str], TransferEstimate]]:
        scored = []
        for candidate in remaining.values():
            visible = self.visibility.visible_targets_by_candidate[candidate.candidate_id]
            new_targets = frozenset(visible - covered)
            if not new_targets:
                continue
            transfer = self._estimate_transfer(current_state, candidate)
            if method == 'proposed_safe_cw_nbv' and not transfer.feasible:
                continue
            score = self._score(method, current_state, candidate, new_targets, transfer)
            scored.append((score, candidate, new_targets, transfer))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[:limit]

    def _score(
        self,
        method: str,
        current_state: StateVector,
        candidate: CandidateViewpoint,
        new_targets: frozenset[str],
        transfer: TransferEstimate,
    ) -> float:
        area_gain = self._area_gain(new_targets)
        normalized_gain = 100.0 * area_gain / max(self.base_planner.total_inspection_area, 1.0)
        travel_distance = distance(current_state[:3], candidate.position)
        infeasible_penalty = 80.0 if not transfer.feasible else 0.0
        keepout_penalty = 160.0 * max(0.0, -transfer.min_clearance)

        if method == 'proposed_safe_cw_nbv':
            clearance_reward = min(transfer.min_clearance, 8.0)
            return (
                8.0 * normalized_gain
                - 5.5 * transfer.delta_v
                - 0.22 * transfer.tracking_error
                + 1.1 * max(0.0, clearance_reward)
                - 2.0 * infeasible_penalty
                - keepout_penalty
            )
        if method == 'set_cover_cw_tour':
            return (
                10.0 * normalized_gain
                - 4.0 * transfer.delta_v
                - 0.2 * transfer.tracking_error
                - 2.0 * infeasible_penalty
                - keepout_penalty
            )
        if method in SET_COVER_METHODS:
            gain_term = (
                10.0 * float(len(new_targets))
                if method == 'abl_unweighted_coverage'
                else 10.0 * normalized_gain
            )
            delta_v_weight = 0.0 if method == 'abl_no_transfer_cost' else 4.0
            tracking_weight = 0.0 if method == 'abl_no_transfer_cost' else 0.2
            method_keepout_penalty = (
                0.0 if method == 'abl_no_clearance_filter' else keepout_penalty
            )
            method_infeasible_penalty = (
                0.0
                if method in {'abl_no_clearance_filter', 'abl_no_input_check'}
                else 2.0 * infeasible_penalty
            )
            return (
                gain_term
                - delta_v_weight * transfer.delta_v
                - tracking_weight * transfer.tracking_error
                - method_infeasible_penalty
                - method_keepout_penalty
            )
        if method == 'certified_graph_search':
            return (
                10.0 * normalized_gain
                - self._dynamic_transfer_cost(transfer)
                - keepout_penalty
                - infeasible_penalty
            )
        if method == 'coverage_greedy':
            return 10.0 * normalized_gain - 0.01 * travel_distance
        if method == 'distance_greedy':
            return 4.0 * normalized_gain - 0.8 * travel_distance
        if method == 'safe_coverage_greedy':
            return 10.0 * normalized_gain - infeasible_penalty - keepout_penalty
        if method == 'fuel_greedy':
            return (
                2.0 * normalized_gain
                - 14.0 * transfer.delta_v
                - 0.15 * transfer.tracking_error
                - infeasible_penalty
            )
        if method == 'random_safe':
            return normalized_gain
        raise ValueError(f'unknown method: {method}')

    def _transfer_acceptable(self, method: str, transfer: TransferEstimate) -> bool:
        """Return whether a transfer can be selected by a method.

        Ablation methods intentionally remove one planning check, but the
        resulting trajectory is still evaluated by the full feasibility metrics
        in the summary table.
        """
        if transfer.feasible:
            return True
        clearance_ok = transfer.min_clearance >= 0.0
        input_ok = transfer.peak_requested_input <= self.config.max_acceleration + 1.0e-9
        speed_ok = transfer.max_speed <= 2.0
        unclipped_ok = transfer.clipped_step_count == 0
        if method == 'abl_no_clearance_filter':
            return input_ok and speed_ok and unclipped_ok
        if method == 'abl_no_input_check':
            return clearance_ok and speed_ok
        return False

    def _estimate_transfer(
        self,
        current_state: StateVector,
        candidate: CandidateViewpoint,
    ) -> TransferEstimate:
        """Return a cached HCW transfer estimate for scoring repeated choices."""
        return self._estimate_transfer_from_state(current_state, candidate)

    def _estimate_transfer_from_state(
        self,
        current_state: StateVector,
        candidate: CandidateViewpoint,
    ) -> TransferEstimate:
        """Return a cached HCW transfer estimate from an arbitrary state."""
        state_key = tuple(round(value, 9) for value in current_state)
        key = (state_key, candidate.candidate_id)
        cached = self._transfer_cache.get(key)
        if cached is not None:
            return cached
        transfer = self.base_planner.estimate_transfer(current_state, candidate.position)
        self._transfer_cache[key] = transfer
        return transfer

    def _dynamic_transfer_cost(self, transfer: TransferEstimate) -> float:
        """Compute the CW-aware cost used to trade coverage against energy."""
        return (
            self.config.cw_energy_weight * transfer.delta_v
            + self.config.cw_tracking_weight * transfer.tracking_error
            + self.config.cw_safety_weight * max(0.0, -transfer.min_clearance)
        )

    def _summary(
        self,
        method: str,
        steps: list[MethodStep],
        trajectory: tuple[tuple[float, StateVector, ControlVector], ...],
        coverage_timeline: tuple[tuple[float, float, int], ...],
        planning_time: float,
    ) -> dict[str, float | int | str | bool]:
        final_coverage = coverage_timeline[-1][1] if coverage_timeline else 0.0
        total_delta_v = sum(step.transfer.delta_v for step in steps)
        total_dynamic_cost = sum(step.dynamic_cost for step in steps)
        peak_requested_input = max(
            (step.transfer.peak_requested_input for step in steps),
            default=0.0,
        )
        clipped_step_count = sum(step.transfer.clipped_step_count for step in steps)
        total_step_count = sum(step.transfer.sample_count for step in steps)
        min_clearance = min((step.transfer.min_clearance for step in steps), default=0.0)
        max_speed = max((step.transfer.max_speed for step in steps), default=0.0)
        rms_tracking_error = math.sqrt(
            sum(step.transfer.tracking_error**2 for step in steps)
            / max(1, len(steps))
        )
        feasible = bool(steps) and all(step.transfer.feasible for step in steps)
        return {
            'method': method,
            'geometry_backend': self.config.geometry_backend,
            'target_count': len(self.targets),
            'candidate_count': len(self.candidates),
            'inspectable_target_count': len(self.inspectable_targets),
            'inspectable_area_ratio': self._inspectable_area_ratio(),
            'selected_viewpoint_count': len(steps),
            'final_coverage_ratio': final_coverage,
            'final_inspectable_coverage_ratio': self._inspectable_coverage_ratio(
                _covered_targets_from_steps(steps)
            ),
            'coverage_threshold': self.config.coverage_threshold,
            'coverage_stop_ratio': self.config.coverage_stop_ratio,
            'coverage_success': final_coverage >= self.config.coverage_threshold,
            'total_delta_v': total_delta_v,
            'peak_requested_input': peak_requested_input,
            'input_limit': self.config.max_acceleration,
            'clipped_step_count': clipped_step_count,
            'clipped_step_ratio': clipped_step_count / max(1, total_step_count),
            'delta_v_per_raw_coverage': total_delta_v / max(final_coverage, 1.0e-12),
            'coverage_per_delta_v': final_coverage / max(total_delta_v, 1.0e-12),
            'total_dynamic_cost': total_dynamic_cost,
            'min_clearance': min_clearance,
            'max_speed': max_speed,
            'rms_tracking_error': rms_tracking_error,
            'mission_duration': trajectory[-1][0] if trajectory else 0.0,
            'planning_time': planning_time,
            'trajectory_sample_count': len(trajectory),
            'feasible': feasible,
            'dynamics_model': 'CW/HCW',
        }

    def _coverage_timeline(self, steps: Iterable[MethodStep]) -> list[tuple[float, float, int]]:
        timeline = [(0.0, 0.0, 0)]
        inspected = 0
        for step in steps:
            inspected += len(step.new_targets)
            timeline.append((
                (step.sequence + 1) * self.config.transfer_duration,
                step.cumulative_coverage,
                inspected,
            ))
        return timeline

    def _coverage_ratio(self, covered: set[str]) -> float:
        denominator = max(self.base_planner.total_inspection_area, 1.0)
        return self._area_gain(covered) / denominator

    def _inspectable_coverage_ratio(self, covered: set[str]) -> float:
        denominator = max(self.inspectable_area, 1.0)
        return self._area_gain(covered & self.inspectable_targets) / denominator

    def _inspectable_area_ratio(self) -> float:
        denominator = max(self.base_planner.total_inspection_area, 1.0)
        return self.inspectable_area / denominator

    def _inspectable_targets(self) -> set[str]:
        inspectable: set[str] = set()
        for visible_targets in self.visibility.visible_targets_by_candidate.values():
            inspectable.update(visible_targets)
        return inspectable

    def _area_gain(self, target_ids: Iterable[str]) -> float:
        return sum(
            self.base_planner.target_area_by_id.get(target_id, 1.0)
            for target_id in target_ids
        )

    def _run_dir(self) -> Path:
        run_id = self.config.run_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        return self.config.output_root / run_id

    def _config_dict(self) -> dict[str, object]:
        values = self.config.__dict__.copy()
        values['output_root'] = str(self.config.output_root)
        values['initial_state'] = list(self.config.initial_state)
        values['methods'] = list(self.config.methods)
        return values

    @staticmethod
    def _write_method_comparison(path: Path, results: tuple[MethodResult, ...]) -> None:
        fieldnames = [
            'method', 'final_coverage_ratio', 'final_inspectable_coverage_ratio',
            'inspectable_area_ratio', 'coverage_success', 'feasible',
            'total_delta_v', 'peak_requested_input', 'input_limit',
            'clipped_step_count', 'clipped_step_ratio',
            'min_clearance', 'max_speed', 'rms_tracking_error',
            'delta_v_per_raw_coverage', 'coverage_per_delta_v',
            'total_dynamic_cost', 'selected_viewpoint_count',
            'mission_duration', 'planning_time',
            'certificate_status', 'certificate_expansions',
            'certificate_candidate_count', 'certificate_target_count',
            'certificate_objective_cost',
        ]
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow({
                    key: result.summary.get(key, '')
                    for key in fieldnames
                })

    def _write_all_planner_rows(self, path: Path, results: tuple[MethodResult, ...]) -> None:
        fieldnames = [
            'method', 'sequence', 'candidate_id', 'viewpoint_x', 'viewpoint_y',
            'viewpoint_z', 'new_target_count', 'cumulative_coverage', 'score',
            'transfer_delta_v', 'transfer_min_clearance', 'transfer_tracking_error',
            'transfer_dynamic_cost', 'coverage_gain_area', 'coverage_per_delta_v',
            'transfer_feasible',
        ]
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                for step in result.steps:
                    coverage_gain_area = sum(
                        self.base_planner.target_area_by_id.get(target_id, 1.0)
                        for target_id in step.new_targets
                    )
                    writer.writerow({
                        'method': result.method,
                        'sequence': step.sequence,
                        'candidate_id': step.candidate.candidate_id,
                        'viewpoint_x': step.candidate.position[0],
                        'viewpoint_y': step.candidate.position[1],
                        'viewpoint_z': step.candidate.position[2],
                        'new_target_count': len(step.new_targets),
                        'cumulative_coverage': step.cumulative_coverage,
                        'score': step.score,
                        'transfer_delta_v': step.transfer.delta_v,
                        'transfer_min_clearance': step.transfer.min_clearance,
                        'transfer_tracking_error': step.transfer.tracking_error,
                        'transfer_dynamic_cost': step.dynamic_cost,
                        'coverage_gain_area': coverage_gain_area,
                        'coverage_per_delta_v': (
                            coverage_gain_area / max(step.transfer.delta_v, 1.0e-12)
                        ),
                        'transfer_feasible': step.transfer.feasible,
                    })

    def _write_all_viewpoints(self, path: Path, results: tuple[MethodResult, ...]) -> None:
        fieldnames = [
            'method', 'sequence', 'candidate_id', 'viewpoint_x', 'viewpoint_y',
            'viewpoint_z', 'boresight_x', 'boresight_y', 'boresight_z',
            'yaw_rad', 'pitch_rad', 'qx', 'qy', 'qz', 'qw',
            'new_target_count', 'cumulative_coverage',
        ]
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            target_by_id = {target.target_id: target for target in self.targets}
            for result in results:
                for step in result.steps:
                    source_target = target_by_id.get(step.candidate.source_target_id)
                    aim_position = (
                        source_target.position if source_target is not None else None
                    )
                    attitude = _camera_attitude(step.candidate.position, aim_position)
                    writer.writerow({
                        'method': result.method,
                        'sequence': step.sequence,
                        'candidate_id': step.candidate.candidate_id,
                        'viewpoint_x': step.candidate.position[0],
                        'viewpoint_y': step.candidate.position[1],
                        'viewpoint_z': step.candidate.position[2],
                        'boresight_x': attitude['boresight'][0],
                        'boresight_y': attitude['boresight'][1],
                        'boresight_z': attitude['boresight'][2],
                        'yaw_rad': attitude['yaw'],
                        'pitch_rad': attitude['pitch'],
                        'qx': attitude['quaternion'][0],
                        'qy': attitude['quaternion'][1],
                        'qz': attitude['quaternion'][2],
                        'qw': attitude['quaternion'][3],
                        'new_target_count': len(step.new_targets),
                        'cumulative_coverage': step.cumulative_coverage,
                    })

    @staticmethod
    def _write_all_trajectories(path: Path, results: tuple[MethodResult, ...]) -> None:
        fieldnames = ['method', 'time', 'rx', 'ry', 'rz', 'vx', 'vy', 'vz', 'ax', 'ay', 'az']
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                for time, state, command in result.trajectory:
                    writer.writerow({
                        'method': result.method,
                        'time': time,
                        'rx': state[0],
                        'ry': state[1],
                        'rz': state[2],
                        'vx': state[3],
                        'vy': state[4],
                        'vz': state[5],
                        'ax': command[0],
                        'ay': command[1],
                        'az': command[2],
                    })

    @staticmethod
    def _write_all_attitudes(path: Path, results: tuple[MethodResult, ...]) -> None:
        fieldnames = [
            'method', 'time', 'boresight_x', 'boresight_y', 'boresight_z',
            'yaw_rad', 'pitch_rad', 'qx', 'qy', 'qz', 'qw',
        ]
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                for time, state, _command in result.trajectory:
                    attitude = _camera_attitude(state[:3])
                    writer.writerow({
                        'method': result.method,
                        'time': time,
                        'boresight_x': attitude['boresight'][0],
                        'boresight_y': attitude['boresight'][1],
                        'boresight_z': attitude['boresight'][2],
                        'yaw_rad': attitude['yaw'],
                        'pitch_rad': attitude['pitch'],
                        'qx': attitude['quaternion'][0],
                        'qy': attitude['quaternion'][1],
                        'qz': attitude['quaternion'][2],
                        'qw': attitude['quaternion'][3],
                    })

    @staticmethod
    def _write_all_coverage(path: Path, results: tuple[MethodResult, ...]) -> None:
        fieldnames = ['method', 'time', 'coverage_ratio', 'inspected_targets']
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                for time, coverage, inspected in result.coverage_timeline:
                    writer.writerow({
                        'method': result.method,
                        'time': time,
                        'coverage_ratio': coverage,
                        'inspected_targets': inspected,
                    })

    @staticmethod
    def _write_summary(path: Path, results: tuple[MethodResult, ...]) -> None:
        _write_json(path, {
            'methods': [result.summary for result in results],
            'best_feasible_method': _best_feasible_method(results),
        })

    @staticmethod
    def _write_summary_md(path: Path, results: tuple[MethodResult, ...]) -> None:
        lines = ['# Offline Planning Experiment Summary', '']
        lines.append(
            '| Method | Raw coverage | Inspectable coverage | Delta-v | Peak input | '
            'Clipped steps | CW dynamic cost | Min clearance | Feasible | Certificate |'
        )
        lines.append('| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |')
        for result in results:
            summary = result.summary
            certificate = summary.get('certificate_status', '')
            lines.append(
                f"| {summary['method']} | {float(summary['final_coverage_ratio']):.3f} "
                f"| {float(summary['final_inspectable_coverage_ratio']):.3f} "
                f"| {float(summary['total_delta_v']):.3f} "
                f"| {float(summary['peak_requested_input']):.3f} "
                f"| {int(summary['clipped_step_count'])} "
                f"| {float(summary['total_dynamic_cost']):.3f} "
                f"| {float(summary['min_clearance']):.3f} "
                f"| {summary['feasible']} | {certificate} |"
            )
        path.write_text('\n'.join(lines) + '\n')

    @staticmethod
    def _plot_coverage(path: Path, results: tuple[MethodResult, ...]) -> None:
        figure, axis = plt.subplots(figsize=(7.0, 4.0))
        for result in results:
            final_raw = float(result.summary['final_coverage_ratio'])
            final_inspectable = float(result.summary['final_inspectable_coverage_ratio'])
            scale_factor = final_inspectable / max(final_raw, 1.0e-12)
            is_proposed = result.method == 'set_cover_cw_tour'
            axis.step(
                [row[0] for row in result.coverage_timeline],
                [min(1.0, row[1] * scale_factor) for row in result.coverage_timeline],
                where='post',
                linewidth=2.5 if is_proposed else 1.65,
                color=METHOD_COLORS.get(result.method, '#4D4D4D'),
                alpha=1.0 if is_proposed else 0.76,
                label=_method_label(result.method),
            )
        axis.axhline(0.98, color='#272727', linestyle='--', linewidth=0.9, alpha=0.55)
        axis.text(0.99, 0.955, '98% stop target', transform=axis.transAxes,
                  ha='right', va='center', fontsize=8, color='#272727')
        axis.set_xlabel('Mission time (s)')
        axis.set_ylabel('Inspectable area coverage')
        axis.set_ylim(0.0, 1.0)
        axis.grid(True, axis='y', color='#E1E1E1', linewidth=0.6)
        axis.spines['top'].set_visible(False)
        axis.spines['right'].set_visible(False)
        axis.legend(frameon=False, ncol=2, fontsize=8, loc='lower right')
        figure.tight_layout()
        _save_figure(figure, path)
        plt.close(figure)

    @staticmethod
    def _plot_delta_v(path: Path, results: tuple[MethodResult, ...]) -> None:
        _plot_bar(
            path,
            results,
            key='total_delta_v',
            ylabel=r'Total $\Delta v$ (m s$^{-1}$)',
            title='',
        )

    @staticmethod
    def _plot_energy_efficiency(path: Path, results: tuple[MethodResult, ...]) -> None:
        _plot_bar(
            path,
            results,
            key='delta_v_per_raw_coverage',
            ylabel=r'$\Delta v$ per covered area ratio (m s$^{-1}$)',
            title='',
        )

    @staticmethod
    def _plot_safety(path: Path, results: tuple[MethodResult, ...]) -> None:
        _plot_bar(
            path,
            results,
            key='min_clearance',
            ylabel='Minimum clearance (m)',
            title='',
            flag_infeasible=True,
        )

    @staticmethod
    def _plot_peak_input(path: Path, results: tuple[MethodResult, ...]) -> None:
        _plot_bar(
            path,
            results,
            key='peak_requested_input',
            ylabel='Peak requested input (m s$^{-2}$)',
            title='',
        )


def _planner_config(config: ExperimentConfig) -> OfflinePlannerConfig:
    return OfflinePlannerConfig(
        geometry_backend=config.geometry_backend,
        mesh_target_count=config.mesh_target_count,
        mesh_occlusion_max_triangles=config.mesh_occlusion_max_triangles,
        candidate_radius=config.candidate_radius,
        candidate_stride=config.candidate_stride,
        coverage_threshold=config.coverage_threshold,
        max_viewpoints=config.max_viewpoints,
        transfer_duration=config.transfer_duration,
        integration_dt=config.integration_dt,
        max_acceleration=config.max_acceleration,
        safety_margin=config.safety_margin,
        initial_state=config.initial_state,
        output_root=config.output_root,
        run_id=config.run_id,
    )


def _deterministic_index(seed: int, covered_count: int, pool_size: int) -> int:
    value = (1103515245 * (seed + 31 * covered_count) + 12345) & 0x7FFFFFFF
    return value % max(1, pool_size)


def _best_feasible_method(results: tuple[MethodResult, ...]) -> str:
    feasible = [result for result in results if bool(result.summary['feasible'])]
    pool = feasible or list(results)
    best = max(
        pool,
        key=lambda result: (
            float(result.summary['final_inspectable_coverage_ratio']),
            float(result.summary['final_coverage_ratio']),
            -float(result.summary['total_delta_v']),
        ),
    )
    return best.method


def _covered_targets_from_steps(steps: Iterable[MethodStep]) -> set[str]:
    covered: set[str] = set()
    for step in steps:
        covered.update(step.new_targets)
    return covered


def _target_mask(target_ids: Iterable[str], target_index: dict[str, int]) -> int:
    mask = 0
    for target_id in target_ids:
        index = target_index.get(target_id)
        if index is not None:
            mask |= 1 << index
    return mask


def _target_mask_area(mask: int, target_weights: tuple[float, ...]) -> float:
    return sum(
        weight
        for index, weight in enumerate(target_weights)
        if mask & (1 << index)
    )


def _bit_count(mask: int) -> int:
    return int(mask.bit_count())


def _reconstruct_candidate_sequence(
    state: tuple[int, int],
    parent: dict[tuple[int, int], tuple[int, int] | None],
    candidates: tuple[CandidateViewpoint, ...],
) -> tuple[CandidateViewpoint, ...]:
    sequence: list[CandidateViewpoint] = []
    current: tuple[int, int] | None = state
    while current is not None and current[1] >= 0:
        sequence.append(candidates[current[1]])
        current = parent.get(current)
    sequence.reverse()
    return tuple(sequence)


def _method_label(method: str) -> str:
    labels = {
        'set_cover_cw_tour': 'Proposed dynamics-aware tour',
        'certified_graph_search': 'Certified graph optimum',
        'proposed_safe_cw_nbv': 'CW-NBV baseline',
        'coverage_greedy': 'Coverage greedy',
        'safe_coverage_greedy': 'Safe coverage greedy',
        'distance_greedy': 'Nearest NBV',
        'fuel_greedy': 'Fuel greedy',
        'random_safe': 'Random safe',
    }
    return labels.get(method, method)


def _camera_attitude(
    position: StateVector | tuple[float, float, float],
    aim_position: tuple[float, float, float] | None = None,
) -> dict[str, object]:
    """Return camera attitude for a chaser position and optional aim point."""
    try:
        if aim_position is None:
            boresight = unit(scale(position[:3], -1.0))
        else:
            boresight = unit((
                aim_position[0] - position[0],
                aim_position[1] - position[1],
                aim_position[2] - position[2],
            ))
    except ValueError:
        boresight = (1.0, 0.0, 0.0)
    world_up = (0.0, 0.0, 1.0)
    if abs(dot(boresight, world_up)) > 0.95:
        world_up = (0.0, 1.0, 0.0)
    body_y = unit(cross(world_up, boresight))
    body_z = unit(cross(boresight, body_y))
    quaternion = _rotation_matrix_to_quaternion(boresight, body_y, body_z)
    yaw = math.atan2(boresight[1], boresight[0])
    pitch = math.atan2(
        -boresight[2],
        math.sqrt(boresight[0] * boresight[0] + boresight[1] * boresight[1]),
    )
    return {
        'boresight': boresight,
        'yaw': yaw,
        'pitch': pitch,
        'quaternion': quaternion,
    }


def _rotation_matrix_to_quaternion(
    body_x: tuple[float, float, float],
    body_y: tuple[float, float, float],
    body_z: tuple[float, float, float],
) -> tuple[float, float, float, float]:
    """Convert body axes in LVLH coordinates to quaternion x,y,z,w."""
    matrix = (
        (body_x[0], body_y[0], body_z[0]),
        (body_x[1], body_y[1], body_z[1]),
        (body_x[2], body_y[2], body_z[2]),
    )
    trace = matrix[0][0] + matrix[1][1] + matrix[2][2]
    if trace > 0.0:
        scale_value = math.sqrt(trace + 1.0) * 2.0
        qw = 0.25 * scale_value
        qx = (matrix[2][1] - matrix[1][2]) / scale_value
        qy = (matrix[0][2] - matrix[2][0]) / scale_value
        qz = (matrix[1][0] - matrix[0][1]) / scale_value
    elif matrix[0][0] > matrix[1][1] and matrix[0][0] > matrix[2][2]:
        scale_value = math.sqrt(1.0 + matrix[0][0] - matrix[1][1] - matrix[2][2]) * 2.0
        qw = (matrix[2][1] - matrix[1][2]) / scale_value
        qx = 0.25 * scale_value
        qy = (matrix[0][1] + matrix[1][0]) / scale_value
        qz = (matrix[0][2] + matrix[2][0]) / scale_value
    elif matrix[1][1] > matrix[2][2]:
        scale_value = math.sqrt(1.0 + matrix[1][1] - matrix[0][0] - matrix[2][2]) * 2.0
        qw = (matrix[0][2] - matrix[2][0]) / scale_value
        qx = (matrix[0][1] + matrix[1][0]) / scale_value
        qy = 0.25 * scale_value
        qz = (matrix[1][2] + matrix[2][1]) / scale_value
    else:
        scale_value = math.sqrt(1.0 + matrix[2][2] - matrix[0][0] - matrix[1][1]) * 2.0
        qw = (matrix[1][0] - matrix[0][1]) / scale_value
        qx = (matrix[0][2] + matrix[2][0]) / scale_value
        qy = (matrix[1][2] + matrix[2][1]) / scale_value
        qz = 0.25 * scale_value
    norm_value = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    return (qx / norm_value, qy / norm_value, qz / norm_value, qw / norm_value)


def _plot_bar(
    path: Path,
    results: tuple[MethodResult, ...],
    key: str,
    ylabel: str,
    title: str,
    flag_infeasible: bool = False,
) -> None:
    figure, axis = plt.subplots(figsize=(7.0, 3.15))
    labels = [METHOD_LABELS_SHORT.get(result.method, _method_label(result.method)) for result in results]
    values = [float(result.summary[key]) for result in results]
    y_positions = list(range(len(results)))
    colors = [METHOD_COLORS.get(result.method, '#767676') for result in results]
    edge_colors = [
        '#0F4D92' if result.method == 'set_cover_cw_tour' else '#4D4D4D'
        for result in results
    ]
    line_widths = [1.3 if result.method == 'set_cover_cw_tour' else 0.5 for result in results]
    axis.barh(
        y_positions,
        values,
        color=colors,
        edgecolor=edge_colors,
        linewidth=line_widths,
        alpha=0.96,
        height=0.64,
    )
    axis.invert_yaxis()
    axis.set_yticks(y_positions)
    axis.set_yticklabels(labels)
    axis.set_xlabel(ylabel)
    if title:
        axis.set_title(title)
    axis.grid(True, axis='x', color='#E1E1E1', linewidth=0.6)
    axis.set_axisbelow(True)
    x_min = min(values) if values else 0.0
    x_max = max(values) if values else 1.0
    span = max(x_max - min(0.0, x_min), 1.0e-9)
    left_limit = min(0.0, x_min - 0.14 * span)
    right_limit = x_max + 0.18 * span
    axis.set_xlim(left_limit, right_limit)
    if x_min < 0.0:
        axis.axvline(0.0, color='#272727', linewidth=0.9, alpha=0.65)
    for y_position, value, result in zip(y_positions, values, results):
        text = f'{value:.2f}' if value >= 1.0 else f'{value:.3f}'
        if value < 0.0:
            x_text = value - 0.018 * span
            ha = 'right'
        else:
            x_text = value + 0.018 * span
            ha = 'left'
        axis.text(
            x_text,
            y_position,
            text,
            va='center',
            ha=ha,
            fontsize=8,
            color='#272727',
            fontweight='bold' if result.method == 'set_cover_cw_tour' else 'normal',
        )
    if flag_infeasible and any(
        result.method == 'coverage_greedy' and not result.summary['feasible']
        for result in results
    ):
        for y_position, result in zip(y_positions, results):
            if result.method == 'coverage_greedy':
                axis.text(
                    right_limit - 0.01 * span,
                    y_position,
                    'keep-out violation',
                    va='center',
                    ha='right',
                    fontsize=7,
                    color='#B64342',
                )
    axis.spines['top'].set_visible(False)
    axis.spines['right'].set_visible(False)
    figure.tight_layout()
    _save_figure(figure, path)
    plt.close(figure)


def _save_figure(figure, path: Path) -> None:
    figure.savefig(path, dpi=360, bbox_inches='tight')
    figure.savefig(path.with_suffix('.pdf'), bbox_inches='tight')
    figure.savefig(path.with_suffix('.svg'), bbox_inches='tight')


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--config',
        default='src/orbinspect_guidance/config/offline_planning_experiment.yaml',
    )
    parser.add_argument('--run-id', default='')
    parser.add_argument('--output-root')
    parser.add_argument('--coverage-threshold', type=float)
    parser.add_argument('--coverage-stop-ratio', type=float)
    parser.add_argument('--mesh-target-count', type=int)
    parser.add_argument('--mesh-occlusion-max-triangles', type=int)
    parser.add_argument('--max-viewpoints', type=int)
    parser.add_argument('--candidate-radius', type=float)
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> ExperimentConfig:
    """Build experiment config from YAML and command-line overrides."""
    values = _load_yaml_config(Path(args.config))
    overrides = {
        'run_id': args.run_id,
        'output_root': args.output_root,
        'coverage_threshold': args.coverage_threshold,
        'coverage_stop_ratio': args.coverage_stop_ratio,
        'mesh_target_count': args.mesh_target_count,
        'mesh_occlusion_max_triangles': args.mesh_occlusion_max_triangles,
        'max_viewpoints': args.max_viewpoints,
        'candidate_radius': args.candidate_radius,
    }
    for key, value in overrides.items():
        if value not in (None, ''):
            values[key] = value
    if 'output_root' in values:
        values['output_root'] = Path(str(values['output_root']))
    if 'methods' in values:
        values['methods'] = tuple(str(method) for method in values['methods'])
    if 'initial_state' in values:
        values['initial_state'] = tuple(float(value) for value in values['initial_state'])
    return ExperimentConfig(**values)


def _load_yaml_config(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    raw = _safe_load_yaml_mapping(path)
    if 'offline_planning_experiment' in raw:
        raw = raw['offline_planning_experiment'].get('ros__parameters', {})
    if not isinstance(raw, dict):
        raise ValueError(f'experiment config must be a mapping: {path}')
    allowed = set(ExperimentConfig.__dataclass_fields__)
    return {str(key): value for key, value in raw.items() if str(key) in allowed}


def _safe_load_yaml_mapping(path: Path) -> dict[str, object]:
    """Load simple YAML mappings with a PyYAML fallback for offline macOS runs."""
    if yaml is not None:
        loaded = yaml.safe_load(path.read_text()) or {}
        return loaded if isinstance(loaded, dict) else {}
    return _load_simple_yaml_mapping(path.read_text())


def _load_simple_yaml_mapping(text: str) -> dict[str, object]:
    """Parse the small subset of YAML used by local planner config files."""
    root: dict[str, object] = {}
    stack: list[tuple[int, dict[str, object]]] = [(-1, root)]
    pending_list: tuple[int, str, list[object]] | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith('#'):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(' '))
        stripped = raw_line.strip()
        if pending_list is not None and indent > pending_list[0] and stripped.startswith('- '):
            pending_list[2].append(_parse_scalar(stripped[2:].strip()))
            continue
        pending_list = None
        while stack and indent <= stack[-1][0]:
            stack.pop()
        current = stack[-1][1]
        key, separator, value = stripped.partition(':')
        if not separator:
            continue
        key = key.strip()
        value = value.strip()
        if value == '':
            child: dict[str, object] = {}
            current[key] = child
            stack.append((indent, child))
        elif value == '[]':
            current[key] = []
        else:
            parsed = _parse_scalar(value)
            current[key] = parsed
            if isinstance(parsed, list):
                pending_list = (indent, key, parsed)
    return root


def _parse_scalar(value: str) -> object:
    if value.startswith('[') and value.endswith(']'):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in inner.split(',')]
    lowered = value.lower()
    if lowered in {'true', 'false'}:
        return lowered == 'true'
    try:
        if any(marker in value for marker in ('.', 'e', 'E')):
            return float(value)
        return int(value)
    except ValueError:
        return value.strip('"\'')


def main(argv: list[str] | None = None) -> None:
    """Run the offline planning comparison experiment."""
    config = config_from_args(parse_args(argv))
    experiment = OfflinePlanningExperiment(config)
    results = experiment.run()
    run_dir = experiment.save(results)
    print(json.dumps({
        'run_dir': str(run_dir),
        'best_feasible_method': _best_feasible_method(results),
        'methods': [result.summary for result in results],
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
