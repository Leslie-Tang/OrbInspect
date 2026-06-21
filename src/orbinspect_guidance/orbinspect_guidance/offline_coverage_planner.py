"""Offline coverage and dynamics-aware inspection trajectory planner."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
import json
import math
from pathlib import Path
import struct
from time import perf_counter
from typing import Iterable

from mpl_toolkits.mplot3d.art3d import Line3DCollection
import matplotlib.pyplot as plt

from orbinspect_dynamics.hcw_dynamics import HCWDynamics
from orbinspect_perception.inspection_target_manager import InspectionTarget
from orbinspect_perception.inspection_target_manager import InspectionTargetManager
from orbinspect_perception.visibility_checker import CameraModel
from orbinspect_perception.visibility_checker import VisibilityChecker
from orbinspect_safety.keepout_zones import KeepoutZoneModel
import yaml

plt.switch_backend('Agg')
plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 9,
    'axes.labelsize': 9,
    'axes.titlesize': 10,
    'legend.fontsize': 8,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'figure.dpi': 160,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
})


Vector3 = tuple[float, float, float]
StateVector = tuple[float, float, float, float, float, float]
ControlVector = tuple[float, float, float]


@dataclass(frozen=True)
class OfflinePlannerConfig:
    """Configuration for the offline coverage planner."""

    target_spacing: float = 12.0
    candidate_radius: float = 18.0
    candidate_shell_offsets: tuple[float, ...] = (0.0, 8.0)
    candidate_stride: int = 2
    coverage_threshold: float = 0.85
    max_viewpoints: int = 40
    mean_motion: float = 0.0011313666536110225
    transfer_duration: float = 80.0
    integration_dt: float = 1.0
    max_acceleration: float = 0.012
    position_gain: float = 0.0008
    velocity_gain: float = 0.08
    safety_margin: float = 2.0
    initial_state: StateVector = (0.0, -35.0, 10.0, 0.0, 0.0, 0.0)
    output_root: Path = Path('data/results')
    run_id: str = ''
    method_name: str = 'dynamics_aware_greedy'
    geometry_backend: str = 'proxy'
    iss_mesh_path: Path = Path(
        'src/orbinspect_description/models/iss_real/meshes/ISS_stationary.glb'
    )
    iss_mesh_scale: float = 1.065
    mesh_preview_max_edges: int = 12000


@dataclass(frozen=True)
class CandidateViewpoint:
    """A safe camera viewpoint candidate."""

    candidate_id: str
    position: Vector3
    source_target_id: str
    safety_margin: float


@dataclass(frozen=True)
class VisibilityMatrix:
    """Target visibility data for each candidate viewpoint."""

    target_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    visible_targets_by_candidate: dict[str, frozenset[str]]


@dataclass(frozen=True)
class TransferEstimate:
    """Predicted transfer cost and feasibility for one candidate."""

    next_state: StateVector
    trajectory: tuple[tuple[float, StateVector, ControlVector], ...]
    delta_v: float
    max_speed: float
    min_clearance: float
    tracking_error: float
    feasible: bool


@dataclass(frozen=True)
class SelectedViewpoint:
    """A selected viewpoint and planner bookkeeping."""

    sequence: int
    candidate: CandidateViewpoint
    new_targets: frozenset[str]
    cumulative_coverage: float
    transfer: TransferEstimate
    score: float


@dataclass(frozen=True)
class OfflinePlan:
    """Complete offline plan and derived metrics."""

    targets: tuple[InspectionTarget, ...]
    candidates: tuple[CandidateViewpoint, ...]
    visibility: VisibilityMatrix
    selected_viewpoints: tuple[SelectedViewpoint, ...]
    planned_trajectory: tuple[tuple[float, StateVector, ControlVector], ...]
    coverage_timeline: tuple[tuple[float, float, int], ...]
    summary: dict[str, float | int | str | bool]


@dataclass(frozen=True)
class IssMeshPreview:
    """Downsampled line preview of the NASA ISS GLB for paper figures."""

    segments: tuple[tuple[Vector3, Vector3], ...]

    @classmethod
    def load(
        cls,
        path: Path,
        scale: float,
        max_edges: int,
    ) -> IssMeshPreview | None:
        """Load a downsampled GLB wire preview without optional mesh packages."""
        if not path.is_file() or max_edges <= 0:
            return None
        try:
            json_doc, binary = _read_glb(path)
            segments = _mesh_segments_from_gltf(json_doc, binary, scale, max_edges)
        except (OSError, KeyError, ValueError, struct.error, json.JSONDecodeError):
            return None
        if not segments:
            return None
        return cls(tuple(segments))

    def draw(self, axis) -> None:
        """Draw the ISS preview as a light wireframe."""
        collection = Line3DCollection(
            self.segments,
            colors='#8A8A8A',
            linewidths=0.18,
            alpha=0.18,
            zorder=1,
        )
        axis.add_collection3d(collection)


class OfflineCoveragePlanner:
    """Plan coverage-aware viewpoint sequences with CW transfer costs."""

    def __init__(self, config: OfflinePlannerConfig) -> None:
        """Create planner with deterministic geometry and dynamics settings."""
        self.config = config
        self.keepout = KeepoutZoneModel(safety_margin=config.safety_margin)
        self.visibility_checker = VisibilityChecker(
            CameraModel(max_range=max(config.candidate_radius + 20.0, 35.0))
        )
        self.dynamics = HCWDynamics(config.mean_motion)
        self.mesh_preview = IssMeshPreview.load(
            config.iss_mesh_path,
            scale=config.iss_mesh_scale,
            max_edges=config.mesh_preview_max_edges,
        )

    def plan(self) -> OfflinePlan:
        """Generate targets, select viewpoints, roll out trajectory, and score metrics."""
        start = perf_counter()
        targets = tuple(self.load_targets())
        candidates = tuple(self.generate_candidate_viewpoints(targets))
        visibility = self.compute_visibility_matrix(targets, candidates)
        selected = tuple(self.select_viewpoints(targets, candidates, visibility))
        planned_trajectory = tuple(
            sample
            for item in selected
            for sample in item.transfer.trajectory
        )
        coverage_timeline = tuple(self._coverage_timeline(selected))
        summary = self.evaluate_plan(
            targets,
            candidates,
            selected,
            planned_trajectory,
            coverage_timeline,
            planning_time=perf_counter() - start,
        )
        return OfflinePlan(
            targets=targets,
            candidates=candidates,
            visibility=visibility,
            selected_viewpoints=selected,
            planned_trajectory=planned_trajectory,
            coverage_timeline=coverage_timeline,
            summary=summary,
        )

    def load_targets(self) -> list[InspectionTarget]:
        """Load or generate inspection targets for the selected geometry backend."""
        if self.config.geometry_backend != 'proxy':
            raise NotImplementedError(
                'mesh target sampling is planned; use geometry_backend=proxy for now'
            )
        return InspectionTargetManager(self.config.target_spacing).generate_targets()

    def generate_candidate_viewpoints(
        self,
        targets: Iterable[InspectionTarget],
    ) -> list[CandidateViewpoint]:
        """Generate safe candidate viewpoints offset along target normals."""
        candidates: list[CandidateViewpoint] = []
        seen_positions: set[tuple[int, int, int]] = set()
        stride = max(1, self.config.candidate_stride)
        for target_index, target in enumerate(targets):
            if target_index % stride != 0:
                continue
            for shell_index, shell_offset in enumerate(self.config.candidate_shell_offsets):
                radius = self.config.candidate_radius + shell_offset
                position = add(target.position, scale(unit(target.normal), radius))
                key = tuple(round(value * 10.0) for value in position)
                if key in seen_positions:
                    continue
                assessment = self.keepout.assess(position)
                if not assessment.is_safe:
                    continue
                seen_positions.add(key)
                candidates.append(
                    CandidateViewpoint(
                        candidate_id=f'cand_{len(candidates):04d}',
                        position=position,
                        source_target_id=target.target_id,
                        safety_margin=assessment.clearance,
                    )
                )
        if not candidates:
            raise RuntimeError('no safe candidate viewpoints generated')
        return candidates

    def compute_visibility_matrix(
        self,
        targets: Iterable[InspectionTarget],
        candidates: Iterable[CandidateViewpoint],
    ) -> VisibilityMatrix:
        """Compute the set of targets visible from each candidate."""
        target_list = tuple(targets)
        candidate_list = tuple(candidates)
        visible_by_candidate: dict[str, frozenset[str]] = {}
        for candidate in candidate_list:
            visible = frozenset(
                target.target_id
                for target in target_list
                if self.visibility_checker.is_visible(
                    candidate.position,
                    target.position,
                    target.normal,
                )
            )
            visible_by_candidate[candidate.candidate_id] = visible
        return VisibilityMatrix(
            target_ids=tuple(target.target_id for target in target_list),
            candidate_ids=tuple(candidate.candidate_id for candidate in candidate_list),
            visible_targets_by_candidate=visible_by_candidate,
        )

    def select_viewpoints(
        self,
        targets: tuple[InspectionTarget, ...],
        candidates: tuple[CandidateViewpoint, ...],
        visibility: VisibilityMatrix,
    ) -> list[SelectedViewpoint]:
        """Select viewpoints with greedy coverage gain per CW transfer cost."""
        target_ids = {target.target_id for target in targets}
        covered: set[str] = set()
        selected: list[SelectedViewpoint] = []
        current_state = self.config.initial_state
        current_time = 0.0
        remaining = {candidate.candidate_id: candidate for candidate in candidates}

        while (
            len(covered) / float(len(target_ids)) < self.config.coverage_threshold
            and remaining
            and len(selected) < self.config.max_viewpoints
        ):
            best = None
            for candidate in remaining.values():
                visible = visibility.visible_targets_by_candidate[candidate.candidate_id]
                new_targets = visible - covered
                if not new_targets:
                    continue
                transfer = self.estimate_transfer(current_state, candidate.position)
                score = self._candidate_score(len(new_targets), candidate, transfer)
                if best is None or score > best[0]:
                    best = (score, candidate, frozenset(new_targets), transfer)
            if best is None:
                break

            score, candidate, new_targets, transfer = best
            covered.update(new_targets)
            current_state = transfer.next_state
            sequence = len(selected)
            current_time += self.config.transfer_duration
            selected.append(
                SelectedViewpoint(
                    sequence=sequence,
                    candidate=candidate,
                    new_targets=new_targets,
                    cumulative_coverage=len(covered) / float(len(target_ids)),
                    transfer=self._offset_transfer_time(transfer, current_time),
                    score=score,
                )
            )
            remaining.pop(candidate.candidate_id, None)
        return selected

    def estimate_transfer(
        self,
        initial_state: StateVector,
        target_position: Vector3,
    ) -> TransferEstimate:
        """Roll out a saturated CW transfer to one viewpoint."""
        state = initial_state
        dt = self.config.integration_dt
        steps = max(1, int(round(self.config.transfer_duration / dt)))
        trajectory: list[tuple[float, StateVector, ControlVector]] = []
        delta_v = 0.0
        max_speed = 0.0
        min_clearance = math.inf
        tracking_error_sum = 0.0

        for step in range(steps):
            command = self._control_to_target(state, target_position)
            state = self.dynamics.rk4_step(state, command, dt)
            speed = norm(state[3:6])
            clearance = self.keepout.assess(state[:3]).clearance
            error = distance(state[:3], target_position)
            delta_v += norm(command) * dt
            max_speed = max(max_speed, speed)
            min_clearance = min(min_clearance, clearance)
            tracking_error_sum += error * error
            trajectory.append(((step + 1) * dt, state, command))

        tracking_error = math.sqrt(tracking_error_sum / float(steps))
        feasible = (
            min_clearance >= 0.0
            and max_speed <= 2.0
            and norm(trajectory[-1][2]) <= self.config.max_acceleration + 1.0e-9
        )
        return TransferEstimate(
            next_state=state,
            trajectory=tuple(trajectory),
            delta_v=delta_v,
            max_speed=max_speed,
            min_clearance=min_clearance,
            tracking_error=tracking_error,
            feasible=feasible,
        )

    def save_plan(self, plan: OfflinePlan) -> Path:
        """Save CSV, JSON, and figure outputs for the planned trajectory."""
        run_dir = self._run_dir()
        raw_dir = run_dir / 'raw'
        figures_dir = run_dir / 'figures'
        config_dir = run_dir / 'config_snapshot'
        output_dirs = (
            raw_dir, figures_dir, config_dir, run_dir / 'videos', run_dir / 'rosbag',
        )
        for directory in output_dirs:
            directory.mkdir(parents=True, exist_ok=True)

        self._write_targets(raw_dir / 'targets.csv', plan.targets)
        self._write_candidates(
            raw_dir / 'candidate_viewpoints.csv',
            plan.candidates,
            plan.visibility,
        )
        self._write_selected(raw_dir / 'selected_viewpoints.csv', plan.selected_viewpoints)
        self._write_planner_log(raw_dir / 'planner.csv', plan.selected_viewpoints)
        self._write_trajectory(raw_dir / 'planned_trajectory.csv', plan.planned_trajectory)
        self._write_coverage(raw_dir / 'coverage_over_time.csv', plan.coverage_timeline)
        self._write_coverage(raw_dir / 'coverage.csv', plan.coverage_timeline)
        self._write_json(run_dir / 'summary.json', plan.summary)
        self._write_json(config_dir / 'offline_planner_config.json', self._config_dict())
        self._write_summary_md(run_dir / 'summary.md', plan.summary)
        self._plot_targets(figures_dir / 'targets_3d.png', plan.targets, plan.selected_viewpoints)
        self._plot_trajectory(figures_dir / 'planned_trajectory_3d.png', plan.planned_trajectory)
        self._plot_coverage(figures_dir / 'coverage_over_time.png', plan.coverage_timeline)
        return run_dir

    def evaluate_plan(
        self,
        targets: tuple[InspectionTarget, ...],
        candidates: tuple[CandidateViewpoint, ...],
        selected: tuple[SelectedViewpoint, ...],
        planned_trajectory: tuple[tuple[float, StateVector, ControlVector], ...],
        coverage_timeline: tuple[tuple[float, float, int], ...],
        planning_time: float,
    ) -> dict[str, float | int | str | bool]:
        """Compute paper-facing summary metrics for a plan."""
        final_coverage = coverage_timeline[-1][1] if coverage_timeline else 0.0
        total_delta_v = sum(item.transfer.delta_v for item in selected)
        min_clearance = min(
            (item.transfer.min_clearance for item in selected),
            default=0.0,
        )
        max_speed = max((item.transfer.max_speed for item in selected), default=0.0)
        rms_tracking_error = math.sqrt(
            sum(item.transfer.tracking_error**2 for item in selected)
            / max(1, len(selected))
        )
        feasible = all(item.transfer.feasible for item in selected)
        return {
            'method': self.config.method_name,
            'geometry_backend': self.config.geometry_backend,
            'target_count': len(targets),
            'candidate_count': len(candidates),
            'selected_viewpoint_count': len(selected),
            'trajectory_sample_count': len(planned_trajectory),
            'final_coverage_ratio': final_coverage,
            'coverage_threshold': self.config.coverage_threshold,
            'coverage_success': final_coverage >= self.config.coverage_threshold,
            'total_delta_v': total_delta_v,
            'min_clearance': min_clearance,
            'max_speed': max_speed,
            'rms_tracking_error': rms_tracking_error,
            'mission_duration': (
                planned_trajectory[-1][0] if planned_trajectory else 0.0
            ),
            'planning_time': planning_time,
            'dynamics_model': 'CW/HCW',
            'feasible': feasible,
        }

    def _candidate_score(
        self,
        new_target_count: int,
        candidate: CandidateViewpoint,
        transfer: TransferEstimate,
    ) -> float:
        feasibility_penalty = 0.0 if transfer.feasible else 25.0
        return (
            8.0 * float(new_target_count)
            + 0.05 * candidate.safety_margin
            - 2.0 * transfer.delta_v
            - 0.2 * transfer.tracking_error
            - feasibility_penalty
        )

    def _control_to_target(
        self,
        state: StateVector,
        target_position: Vector3,
    ) -> ControlVector:
        command = (
            self.config.position_gain * (target_position[0] - state[0])
            - self.config.velocity_gain * state[3],
            self.config.position_gain * (target_position[1] - state[1])
            - self.config.velocity_gain * state[4],
            self.config.position_gain * (target_position[2] - state[2])
            - self.config.velocity_gain * state[5],
        )
        command_norm = norm(command)
        if command_norm <= self.config.max_acceleration:
            return command
        return scale(command, self.config.max_acceleration / command_norm)

    def _offset_transfer_time(
        self,
        transfer: TransferEstimate,
        segment_end_time: float,
    ) -> TransferEstimate:
        segment_start_time = segment_end_time - self.config.transfer_duration
        trajectory = tuple(
            (segment_start_time + sample_time, state, command)
            for sample_time, state, command in transfer.trajectory
        )
        return TransferEstimate(
            next_state=transfer.next_state,
            trajectory=trajectory,
            delta_v=transfer.delta_v,
            max_speed=transfer.max_speed,
            min_clearance=transfer.min_clearance,
            tracking_error=transfer.tracking_error,
            feasible=transfer.feasible,
        )

    def _coverage_timeline(
        self,
        selected: tuple[SelectedViewpoint, ...] | list[SelectedViewpoint],
    ) -> list[tuple[float, float, int]]:
        timeline = [(0.0, 0.0, 0)]
        inspected = 0
        for item in selected:
            inspected += len(item.new_targets)
            time = (item.sequence + 1) * self.config.transfer_duration
            timeline.append((time, item.cumulative_coverage, inspected))
        return timeline

    def _run_dir(self) -> Path:
        run_id = self.config.run_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        return self.config.output_root / run_id

    def _config_dict(self) -> dict[str, object]:
        values = self.config.__dict__.copy()
        values['output_root'] = str(self.config.output_root)
        values['iss_mesh_path'] = str(self.config.iss_mesh_path)
        values['candidate_shell_offsets'] = list(self.config.candidate_shell_offsets)
        values['initial_state'] = list(self.config.initial_state)
        return values

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')

    @staticmethod
    def _write_targets(path: Path, targets: tuple[InspectionTarget, ...]) -> None:
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                'target_id', 'px', 'py', 'pz', 'nx', 'ny', 'nz',
            ])
            writer.writeheader()
            for target in targets:
                writer.writerow({
                    'target_id': target.target_id,
                    'px': target.position[0],
                    'py': target.position[1],
                    'pz': target.position[2],
                    'nx': target.normal[0],
                    'ny': target.normal[1],
                    'nz': target.normal[2],
                })

    @staticmethod
    def _write_candidates(
        path: Path,
        candidates: tuple[CandidateViewpoint, ...],
        visibility: VisibilityMatrix,
    ) -> None:
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                'candidate_id', 'source_target_id', 'x', 'y', 'z',
                'safety_margin', 'visible_target_count',
            ])
            writer.writeheader()
            for candidate in candidates:
                writer.writerow({
                    'candidate_id': candidate.candidate_id,
                    'source_target_id': candidate.source_target_id,
                    'x': candidate.position[0],
                    'y': candidate.position[1],
                    'z': candidate.position[2],
                    'safety_margin': candidate.safety_margin,
                    'visible_target_count': len(
                        visibility.visible_targets_by_candidate[candidate.candidate_id]
                    ),
                })

    @staticmethod
    def _write_selected(path: Path, selected: tuple[SelectedViewpoint, ...]) -> None:
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                'sequence', 'candidate_id', 'x', 'y', 'z', 'new_targets',
                'coverage_ratio', 'score', 'delta_v', 'max_speed',
                'min_clearance', 'tracking_error', 'feasible',
            ])
            writer.writeheader()
            for item in selected:
                writer.writerow({
                    'sequence': item.sequence,
                    'candidate_id': item.candidate.candidate_id,
                    'x': item.candidate.position[0],
                    'y': item.candidate.position[1],
                    'z': item.candidate.position[2],
                    'new_targets': len(item.new_targets),
                    'coverage_ratio': item.cumulative_coverage,
                    'score': item.score,
                    'delta_v': item.transfer.delta_v,
                    'max_speed': item.transfer.max_speed,
                    'min_clearance': item.transfer.min_clearance,
                    'tracking_error': item.transfer.tracking_error,
                    'feasible': item.transfer.feasible,
                })

    @staticmethod
    def _write_planner_log(path: Path, selected: tuple[SelectedViewpoint, ...]) -> None:
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                'sequence', 'candidate_id', 'viewpoint_x', 'viewpoint_y',
                'viewpoint_z', 'new_target_count', 'cumulative_coverage',
                'score', 'transfer_delta_v', 'transfer_max_speed',
                'transfer_min_clearance', 'transfer_tracking_error',
                'transfer_feasible',
            ])
            writer.writeheader()
            for item in selected:
                writer.writerow({
                    'sequence': item.sequence,
                    'candidate_id': item.candidate.candidate_id,
                    'viewpoint_x': item.candidate.position[0],
                    'viewpoint_y': item.candidate.position[1],
                    'viewpoint_z': item.candidate.position[2],
                    'new_target_count': len(item.new_targets),
                    'cumulative_coverage': item.cumulative_coverage,
                    'score': item.score,
                    'transfer_delta_v': item.transfer.delta_v,
                    'transfer_max_speed': item.transfer.max_speed,
                    'transfer_min_clearance': item.transfer.min_clearance,
                    'transfer_tracking_error': item.transfer.tracking_error,
                    'transfer_feasible': item.transfer.feasible,
                })

    @staticmethod
    def _write_trajectory(
        path: Path,
        samples: tuple[tuple[float, StateVector, ControlVector], ...],
    ) -> None:
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                'time', 'rx', 'ry', 'rz', 'vx', 'vy', 'vz', 'ax', 'ay', 'az',
            ])
            writer.writeheader()
            for time, state, command in samples:
                writer.writerow({
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
    def _write_coverage(path: Path, timeline: tuple[tuple[float, float, int], ...]) -> None:
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                'time', 'coverage_ratio', 'inspected_targets',
            ])
            writer.writeheader()
            for time, coverage, inspected in timeline:
                writer.writerow({
                    'time': time,
                    'coverage_ratio': coverage,
                    'inspected_targets': inspected,
                })

    @staticmethod
    def _write_summary_md(path: Path, summary: dict[str, object]) -> None:
        lines = ['# Offline Coverage Planner Summary', '']
        for key, value in summary.items():
            lines.append(f'- {key}: {value}')
        path.write_text('\n'.join(lines) + '\n')

    def _plot_targets(
        self,
        path: Path,
        targets: tuple[InspectionTarget, ...],
        selected: tuple[SelectedViewpoint, ...],
    ) -> None:
        figure = plt.figure(figsize=(7.2, 5.2))
        axis = figure.add_subplot(111, projection='3d')
        self._draw_mesh_preview(axis)
        axis.scatter(
            [target.position[0] for target in targets],
            [target.position[1] for target in targets],
            [target.position[2] for target in targets],
            s=5,
            alpha=0.55,
            c='#0072B2',
            depthshade=False,
            label='inspection targets',
        )
        if selected:
            axis.scatter(
                [item.candidate.position[0] for item in selected],
                [item.candidate.position[1] for item in selected],
                [item.candidate.position[2] for item in selected],
                s=22,
                c='#D55E00',
                edgecolors='black',
                linewidths=0.25,
                depthshade=False,
                label='selected viewpoints',
            )
        _style_3d_axis(axis, 'Inspection targets and selected viewpoints')
        _set_equal_3d_axes(axis, targets, selected)
        axis.legend(loc='upper left', frameon=False)
        figure.tight_layout()
        _save_publishable_figure(figure, path)
        plt.close(figure)

    def _plot_trajectory(
        self,
        path: Path,
        samples: tuple[tuple[float, StateVector, ControlVector], ...],
    ) -> None:
        figure = plt.figure(figsize=(7.2, 5.2))
        axis = figure.add_subplot(111, projection='3d')
        self._draw_mesh_preview(axis)
        if samples:
            times = [time for time, _state, _command in samples]
            colors = _normalized_values(times)
            axis.plot(
                [state[0] for _time, state, _command in samples],
                [state[1] for _time, state, _command in samples],
                [state[2] for _time, state, _command in samples],
                color='#D55E00',
                linewidth=1.8,
                label='CW-feasible trajectory',
                zorder=5,
            )
            scatter = axis.scatter(
                [state[0] for _time, state, _command in samples[::max(1, len(samples)//120)]],
                [state[1] for _time, state, _command in samples[::max(1, len(samples)//120)]],
                [state[2] for _time, state, _command in samples[::max(1, len(samples)//120)]],
                c=colors[::max(1, len(colors)//120)],
                cmap='viridis',
                s=10,
                depthshade=False,
                label='time samples',
            )
            colorbar = figure.colorbar(scatter, ax=axis, shrink=0.62, pad=0.08)
            colorbar.set_label('normalized time')
        _style_3d_axis(axis, 'Offline CW trajectory on NASA ISS mesh')
        _set_equal_3d_axes(axis, [sample[1] for sample in samples])
        axis.legend(loc='upper left', frameon=False)
        figure.tight_layout()
        _save_publishable_figure(figure, path)
        plt.close(figure)

    @staticmethod
    def _plot_coverage(path: Path, timeline: tuple[tuple[float, float, int], ...]) -> None:
        figure, axis = plt.subplots(figsize=(6.8, 3.6))
        if timeline:
            axis.step(
                [row[0] for row in timeline],
                [row[1] for row in timeline],
                where='post',
                color='#0072B2',
                linewidth=2.0,
            )
            axis.scatter(
                [row[0] for row in timeline],
                [row[1] for row in timeline],
                s=14,
                color='#0072B2',
                zorder=3,
            )
        axis.set_xlabel('mission time [s]')
        axis.set_ylabel('coverage ratio')
        axis.set_ylim(0.0, 1.05)
        axis.spines['top'].set_visible(False)
        axis.spines['right'].set_visible(False)
        axis.grid(True, axis='y', color='#D9D9D9', linewidth=0.6)
        figure.tight_layout()
        _save_publishable_figure(figure, path)
        plt.close(figure)

    def _draw_mesh_preview(self, axis) -> None:
        if self.mesh_preview is None:
            _draw_proxy_wireframe(axis)
            return
        self.mesh_preview.draw(axis)


def add(left: Vector3, right: Vector3) -> Vector3:
    """Return vector addition."""
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def scale(values: Iterable[float], factor: float) -> Vector3:
    """Return a scaled three-vector."""
    vector = tuple(float(value) for value in values)
    return (vector[0] * factor, vector[1] * factor, vector[2] * factor)


def norm(values: Iterable[float]) -> float:
    """Return Euclidean norm."""
    return math.sqrt(sum(float(value) * float(value) for value in values))


def unit(values: Iterable[float]) -> Vector3:
    """Return unit vector, or +x for degenerate inputs."""
    vector = tuple(float(value) for value in values)
    value_norm = norm(vector)
    if value_norm <= 1.0e-12:
        return (1.0, 0.0, 0.0)
    return scale(vector, 1.0 / value_norm)


def distance(left: Iterable[float], right: Iterable[float]) -> float:
    """Return Euclidean distance between two vectors."""
    left_vector = tuple(float(value) for value in left)
    right_vector = tuple(float(value) for value in right)
    return norm((
        left_vector[0] - right_vector[0],
        left_vector[1] - right_vector[1],
        left_vector[2] - right_vector[2],
    ))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--config',
        default='src/orbinspect_guidance/config/offline_coverage_planner.yaml',
        help='YAML planner config file.',
    )
    parser.add_argument('--geometry', default='proxy', choices=['proxy'])
    parser.add_argument('--target-spacing', type=float)
    parser.add_argument('--candidate-radius', type=float)
    parser.add_argument('--candidate-stride', type=int)
    parser.add_argument('--coverage-threshold', type=float)
    parser.add_argument('--max-viewpoints', type=int)
    parser.add_argument('--transfer-duration', type=float)
    parser.add_argument('--integration-dt', type=float)
    parser.add_argument('--max-acceleration', type=float)
    parser.add_argument('--output-root')
    parser.add_argument('--run-id', default='')
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> OfflinePlannerConfig:
    """Create planner config from command-line arguments."""
    config_values = _load_yaml_config(Path(args.config))
    overrides = {
        'geometry_backend': args.geometry,
        'target_spacing': args.target_spacing,
        'candidate_radius': args.candidate_radius,
        'candidate_stride': args.candidate_stride,
        'coverage_threshold': args.coverage_threshold,
        'max_viewpoints': args.max_viewpoints,
        'transfer_duration': args.transfer_duration,
        'integration_dt': args.integration_dt,
        'max_acceleration': args.max_acceleration,
        'output_root': args.output_root,
        'run_id': args.run_id,
    }
    for key, value in overrides.items():
        if value not in (None, ''):
            config_values[key] = value

    if 'output_root' in config_values:
        config_values['output_root'] = Path(str(config_values['output_root']))
    if 'candidate_shell_offsets' in config_values:
        config_values['candidate_shell_offsets'] = tuple(
            float(value) for value in config_values['candidate_shell_offsets']
        )
    if 'initial_state' in config_values:
        config_values['initial_state'] = tuple(
            float(value) for value in config_values['initial_state']
        )
    return OfflinePlannerConfig(**config_values)


def _load_yaml_config(path: Path) -> dict[str, object]:
    """Load offline planner config values from YAML if the file exists."""
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text()) or {}
    if 'offline_coverage_planner' in raw:
        raw = raw['offline_coverage_planner'].get('ros__parameters', {})
    if not isinstance(raw, dict):
        raise ValueError(f'offline planner config must be a mapping: {path}')
    allowed_keys = set(OfflinePlannerConfig.__dataclass_fields__)
    return {
        str(key): value
        for key, value in raw.items()
        if str(key) in allowed_keys
    }


def main(argv: list[str] | None = None) -> None:
    """Run the offline planner and save paper-grade outputs."""
    config = config_from_args(parse_args(argv))
    planner = OfflineCoveragePlanner(config)
    plan = planner.plan()
    run_dir = planner.save_plan(plan)
    print(json.dumps({'run_dir': str(run_dir), **plan.summary}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
