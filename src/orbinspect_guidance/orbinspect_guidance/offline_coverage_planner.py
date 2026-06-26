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

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Line3DCollection

from orbinspect_dynamics.hcw_dynamics import HCWDynamics
from orbinspect_perception.inspection_target_manager import InspectionTarget
from orbinspect_perception.inspection_target_manager import InspectionTargetManager
from orbinspect_perception.visibility_checker import CameraModel
from orbinspect_perception.visibility_checker import VisibilityChecker
from orbinspect_safety.keepout_zones import KeepoutZoneModel

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - minimal offline Python fallback.
    yaml = None

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
    terminal_position_tolerance: float = 0.5
    terminal_velocity_tolerance: float = 0.05
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
    mesh_preview_max_edges: int = 60000
    mesh_target_count: int = 240
    mesh_occlusion_max_triangles: int = 1200


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
    peak_requested_input: float
    clipped_step_count: int
    sample_count: int
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
class MeshTriangle:
    """A transformed mesh triangle with surface area and normal."""

    vertices: tuple[Vector3, Vector3, Vector3]
    centroid: Vector3
    normal: Vector3
    area: float


@dataclass(frozen=True)
class MeshTargetSet:
    """Area-weighted inspection targets sampled from a mesh."""

    targets: tuple[InspectionTarget, ...]
    target_area_by_id: dict[str, float]
    total_area: float


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
            colors='#6F6F6F',
            linewidths=0.22,
            alpha=0.28,
            zorder=1,
        )
        axis.add_collection3d(collection)


@dataclass(frozen=True)
class IssMeshGeometry:
    """Triangle geometry for mesh target sampling and visibility checks."""

    triangles: tuple[MeshTriangle, ...]
    occluders: tuple[MeshTriangle, ...]
    total_area: float

    @classmethod
    def load(
        cls,
        path: Path,
        scale: float,
        occlusion_max_triangles: int,
    ) -> IssMeshGeometry:
        """Load transformed NASA ISS mesh triangles from a GLB file."""
        json_doc, binary = _read_glb(path)
        triangles = tuple(_mesh_triangles_from_gltf(json_doc, binary, scale))
        if not triangles:
            raise RuntimeError(f'no triangles loaded from mesh: {path}')
        total_area = sum(triangle.area for triangle in triangles)
        return cls(
            triangles=triangles,
            occluders=tuple(_downsample_triangles(triangles, occlusion_max_triangles)),
            total_area=total_area,
        )

    def sample_targets(self, target_count: int) -> MeshTargetSet:
        """Return deterministic area-weighted target samples on the mesh."""
        if target_count <= 0:
            raise ValueError('mesh_target_count must be positive')
        selected = _sample_triangles_by_area(self.triangles, target_count)
        sample_area = self.total_area / float(len(selected))
        targets: list[InspectionTarget] = []
        target_area_by_id: dict[str, float] = {}
        for index, triangle in enumerate(selected):
            target_id = f'mesh_{index:05d}'
            targets.append(InspectionTarget(
                target_id=target_id,
                position=triangle.centroid,
                normal=triangle.normal,
            ))
            target_area_by_id[target_id] = sample_area
        return MeshTargetSet(tuple(targets), target_area_by_id, self.total_area)

    def line_of_sight_blocked(
        self,
        start: Vector3,
        end: Vector3,
    ) -> bool:
        """Return true when the segment intersects the downsampled mesh."""
        for triangle in self.occluders:
            if _segment_triangle_intersection(start, end, triangle.vertices):
                return True
        return False


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
        self.mesh_geometry: IssMeshGeometry | None = None
        self.target_area_by_id: dict[str, float] = {}
        self.total_inspection_area = 0.0
        self.mesh_preview = IssMeshPreview.load(
            config.iss_mesh_path,
            scale=config.iss_mesh_scale,
            max_edges=config.mesh_preview_max_edges,
        )
        self._terminal_map_cache: dict[
            tuple[int, float],
            tuple[tuple[StateVector, ...], tuple[StateVector, ...]],
        ] = {}

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
        if self.config.geometry_backend == 'proxy':
            targets = InspectionTargetManager(self.config.target_spacing).generate_targets()
            self.target_area_by_id = {target.target_id: 1.0 for target in targets}
            self.total_inspection_area = float(len(targets))
            return targets
        if self.config.geometry_backend == 'mesh':
            self.mesh_geometry = IssMeshGeometry.load(
                self.config.iss_mesh_path,
                self.config.iss_mesh_scale,
                self.config.mesh_occlusion_max_triangles,
            )
            target_set = self.mesh_geometry.sample_targets(self.config.mesh_target_count)
            self.target_area_by_id = target_set.target_area_by_id
            self.total_inspection_area = target_set.total_area
            return list(target_set.targets)
        raise ValueError(f'unsupported geometry_backend: {self.config.geometry_backend}')

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
        target_by_id = {target.target_id: target for target in target_list}
        visible_by_candidate: dict[str, frozenset[str]] = {}
        for candidate in candidate_list:
            aim_target = target_by_id.get(candidate.source_target_id)
            aim_position = aim_target.position if aim_target is not None else None
            visible = frozenset(
                target.target_id
                for target in target_list
                if self._target_visible(candidate.position, target, aim_position)
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
            self._coverage_ratio(covered, len(target_ids)) < self.config.coverage_threshold
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
                if not transfer.feasible:
                    continue
                score = self._candidate_score(
                    self._target_area(new_targets),
                    candidate,
                    transfer,
                )
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
                    cumulative_coverage=self._coverage_ratio(covered, len(target_ids)),
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
        """Roll out a rest-to-rest terminal HCW transfer to one viewpoint.

        The transfer solves the discrete HCW map for the minimum-energy
        piecewise-constant acceleration sequence that reaches
        ``target_position`` with zero relative velocity at the end of the
        transfer. This keeps selected viewpoints as stabilized inspection
        states rather than fly-through points; feasibility then checks whether
        the required input respects the configured acceleration limit.
        """
        dt = self.config.integration_dt
        steps = max(1, int(round(self.config.transfer_duration / dt)))
        requested_commands = self._terminal_minimum_energy_controls(
            initial_state,
            target_position,
            dt,
            steps,
        )
        trajectory: list[tuple[float, StateVector, ControlVector]] = []
        delta_v = 0.0
        max_speed = 0.0
        min_clearance = math.inf
        tracking_error_sum = 0.0
        peak_requested_input = 0.0
        clipped_step_count = 0
        state = initial_state

        for step, command in enumerate(requested_commands):
            requested_input = norm(command)
            peak_requested_input = max(peak_requested_input, requested_input)
            if requested_input > self.config.max_acceleration + 1.0e-12:
                clipped_step_count += 1
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
        terminal_error = distance(state[:3], target_position)
        terminal_speed = norm(state[3:6])
        feasible = (
            min_clearance >= 0.0
            and max_speed <= 2.0
            and peak_requested_input <= self.config.max_acceleration + 1.0e-9
            and terminal_error <= self.config.terminal_position_tolerance
            and terminal_speed <= self.config.terminal_velocity_tolerance
        )
        return TransferEstimate(
            next_state=state,
            trajectory=tuple(trajectory),
            delta_v=delta_v,
            max_speed=max_speed,
            min_clearance=min_clearance,
            tracking_error=tracking_error,
            peak_requested_input=peak_requested_input,
            clipped_step_count=clipped_step_count,
            sample_count=steps,
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

        self._write_targets(raw_dir / 'targets.csv', plan.targets, self.target_area_by_id)
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
        feasible = bool(selected) and all(item.transfer.feasible for item in selected)
        return {
            'method': self.config.method_name,
            'geometry_backend': self.config.geometry_backend,
            'target_count': len(targets),
            'total_inspection_area': self.total_inspection_area,
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
        new_target_gain: float,
        candidate: CandidateViewpoint,
        transfer: TransferEstimate,
    ) -> float:
        feasibility_penalty = 0.0 if transfer.feasible else 25.0
        if self.config.geometry_backend == 'mesh':
            denominator = max(self.total_inspection_area, 1.0e-12)
            new_target_gain = 100.0 * new_target_gain / denominator
        return (
            8.0 * float(new_target_gain)
            + 0.05 * candidate.safety_margin
            - 2.0 * transfer.delta_v
            - 0.2 * transfer.tracking_error
            - feasibility_penalty
        )

    def _target_visible(
        self,
        chaser_position: Vector3,
        target: InspectionTarget,
        aim_position: Vector3 | None = None,
    ) -> bool:
        if self.config.geometry_backend == 'mesh' and self.mesh_geometry is not None:
            return self._mesh_target_visible(chaser_position, target, aim_position)
        return self.visibility_checker.is_visible(
            chaser_position,
            target.position,
            target.normal,
        )

    def _mesh_target_visible(
        self,
        chaser_position: Vector3,
        target: InspectionTarget,
        aim_position: Vector3 | None = None,
    ) -> bool:
        relative = subtract(target.position, chaser_position)
        target_distance = norm(relative)
        camera = self.visibility_checker.camera
        if target_distance < camera.min_range or target_distance > camera.max_range:
            return False
        if not _inside_camera_fov(chaser_position, relative, camera, aim_position):
            return False
        target_to_chaser = subtract(chaser_position, target.position)
        cosine = dot(unit(target_to_chaser), unit(target.normal))
        cosine = max(-1.0, min(1.0, cosine))
        if math.degrees(math.acos(cosine)) > camera.max_view_angle_deg:
            return False
        if self.mesh_geometry is None:
            return True
        return not self.mesh_geometry.line_of_sight_blocked(
            tuple(float(value) for value in chaser_position),
            target.position,
        )

    def _target_area(self, target_ids: Iterable[str]) -> float:
        return sum(self.target_area_by_id.get(target_id, 1.0) for target_id in target_ids)

    def _coverage_ratio(self, covered: set[str], target_count: int) -> float:
        if self.config.geometry_backend == 'mesh':
            denominator = max(self.total_inspection_area, 1.0e-12)
            return self._target_area(covered) / denominator
        return len(covered) / float(max(1, target_count))

    def _desired_control(
        self,
        state: StateVector,
        target_position: Vector3,
    ) -> ControlVector:
        return (
            self.config.position_gain * (target_position[0] - state[0])
            - self.config.velocity_gain * state[3],
            self.config.position_gain * (target_position[1] - state[1])
            - self.config.velocity_gain * state[4],
            self.config.position_gain * (target_position[2] - state[2])
            - self.config.velocity_gain * state[5],
        )

    def _control_to_target(
        self,
        state: StateVector,
        target_position: Vector3,
    ) -> ControlVector:
        return self._limit_command(self._desired_control(state, target_position))

    def _terminal_minimum_energy_controls(
        self,
        initial_state: StateVector,
        target_position: Vector3,
        dt: float,
        steps: int,
    ) -> tuple[ControlVector, ...]:
        """Solve minimum-energy controls that reach and stabilize at a view."""
        zero_final = self._propagate_constant_control(
            initial_state,
            (0.0, 0.0, 0.0),
            dt,
            steps,
        )
        columns, gram = self._terminal_influence_map(dt, steps)
        target_state: StateVector = (
            target_position[0],
            target_position[1],
            target_position[2],
            0.0,
            0.0,
            0.0,
        )
        rhs = tuple(target_state[index] - zero_final[index] for index in range(6))
        multiplier = _solve_linear_system(gram, rhs)
        controls: list[ControlVector] = []
        for column_index in range(0, len(columns), 3):
            controls.append((
                dot(columns[column_index], multiplier),
                dot(columns[column_index + 1], multiplier),
                dot(columns[column_index + 2], multiplier),
            ))
        return tuple(controls)

    def _terminal_influence_map(
        self,
        dt: float,
        steps: int,
    ) -> tuple[tuple[StateVector, ...], tuple[StateVector, ...]]:
        """Return cached final-state influence columns and Gram matrix."""
        key = (steps, float(dt))
        if key in self._terminal_map_cache:
            return self._terminal_map_cache[key]

        columns: list[StateVector] = []
        zero_command: ControlVector = (0.0, 0.0, 0.0)
        for control_step in range(steps):
            for axis in range(3):
                state: StateVector = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
                basis: ControlVector = (
                    1.0 if axis == 0 else 0.0,
                    1.0 if axis == 1 else 0.0,
                    1.0 if axis == 2 else 0.0,
                )
                for step in range(steps):
                    command = basis if step == control_step else zero_command
                    state = self.dynamics.rk4_step(state, command, dt)
                columns.append(state)

        gram = tuple(
            tuple(
                sum(column[row] * column[column_index] for column in columns)
                for column_index in range(6)
            )
            for row in range(6)
        )
        terminal_map = (tuple(columns), gram)
        self._terminal_map_cache[key] = terminal_map
        return terminal_map

    def _propagate_constant_control(
        self,
        initial_state: StateVector,
        command: ControlVector,
        dt: float,
        steps: int,
    ) -> StateVector:
        """Propagate HCW dynamics with a constant control for ``steps`` samples."""
        state = initial_state
        for _step in range(steps):
            state = self.dynamics.rk4_step(state, command, dt)
        return state

    def _limit_command(self, command: Sequence[float]) -> ControlVector:
        command_norm = norm(command)
        if command_norm <= self.config.max_acceleration:
            return (float(command[0]), float(command[1]), float(command[2]))
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
            peak_requested_input=transfer.peak_requested_input,
            clipped_step_count=transfer.clipped_step_count,
            sample_count=transfer.sample_count,
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
    def _write_targets(
        path: Path,
        targets: tuple[InspectionTarget, ...],
        target_area_by_id: dict[str, float],
    ) -> None:
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                'target_id', 'px', 'py', 'pz', 'nx', 'ny', 'nz',
                'surface_area_weight',
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
                    'surface_area_weight': target_area_by_id.get(target.target_id, 1.0),
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
        _style_3d_axis(axis)
        _set_equal_3d_axes(axis, targets, selected)
        axis.legend(
            loc='upper center',
            bbox_to_anchor=(0.5, 1.02),
            ncol=2,
            frameon=False,
            handlelength=1.4,
        )
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
        _style_3d_axis(axis)
        _set_equal_3d_axes(axis, [sample[1] for sample in samples])
        axis.legend(
            loc='upper center',
            bbox_to_anchor=(0.5, 1.02),
            ncol=2,
            frameon=False,
            handlelength=1.4,
        )
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


def subtract(left: Iterable[float], right: Iterable[float]) -> Vector3:
    """Return vector subtraction."""
    left_vector = tuple(float(value) for value in left)
    right_vector = tuple(float(value) for value in right)
    return (
        left_vector[0] - right_vector[0],
        left_vector[1] - right_vector[1],
        left_vector[2] - right_vector[2],
    )


def scale(values: Iterable[float], factor: float) -> Vector3:
    """Return a scaled three-vector."""
    vector = tuple(float(value) for value in values)
    return (vector[0] * factor, vector[1] * factor, vector[2] * factor)


def dot(left: Iterable[float], right: Iterable[float]) -> float:
    """Return dot product."""
    left_vector = tuple(float(value) for value in left)
    right_vector = tuple(float(value) for value in right)
    return sum(
        left_value * right_value
        for left_value, right_value in zip(left_vector, right_vector)
    )


def cross(left: Iterable[float], right: Iterable[float]) -> Vector3:
    """Return cross product."""
    left_vector = tuple(float(value) for value in left)
    right_vector = tuple(float(value) for value in right)
    return (
        left_vector[1] * right_vector[2] - left_vector[2] * right_vector[1],
        left_vector[2] * right_vector[0] - left_vector[0] * right_vector[2],
        left_vector[0] * right_vector[1] - left_vector[1] * right_vector[0],
    )


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
    return norm(subtract(left, right))


def _solve_3x3(
    matrix: tuple[Vector3, Vector3, Vector3],
    rhs: Vector3,
) -> ControlVector:
    """Solve a 3-by-3 linear system with Gaussian elimination."""
    augmented = [
        [float(matrix[row][0]), float(matrix[row][1]), float(matrix[row][2]), float(rhs[row])]
        for row in range(3)
    ]
    for pivot_index in range(3):
        pivot_row = max(
            range(pivot_index, 3),
            key=lambda row: abs(augmented[row][pivot_index]),
        )
        if abs(augmented[pivot_row][pivot_index]) <= 1.0e-12:
            raise ValueError('singular terminal transfer map')
        if pivot_row != pivot_index:
            augmented[pivot_index], augmented[pivot_row] = (
                augmented[pivot_row],
                augmented[pivot_index],
            )
        pivot = augmented[pivot_index][pivot_index]
        for column in range(pivot_index, 4):
            augmented[pivot_index][column] /= pivot
        for row in range(3):
            if row == pivot_index:
                continue
            factor = augmented[row][pivot_index]
            for column in range(pivot_index, 4):
                augmented[row][column] -= factor * augmented[pivot_index][column]
    return (
        augmented[0][3],
        augmented[1][3],
        augmented[2][3],
    )


def _solve_linear_system(
    matrix: tuple[tuple[float, ...], ...],
    rhs: tuple[float, ...],
) -> tuple[float, ...]:
    """Solve a small dense linear system with partial pivoting."""
    size = len(rhs)
    augmented = [
        [float(matrix[row][column]) for column in range(size)] + [float(rhs[row])]
        for row in range(size)
    ]
    for pivot_index in range(size):
        pivot_row = max(
            range(pivot_index, size),
            key=lambda row: abs(augmented[row][pivot_index]),
        )
        if abs(augmented[pivot_row][pivot_index]) <= 1.0e-12:
            raise ValueError('singular terminal transfer map')
        if pivot_row != pivot_index:
            augmented[pivot_index], augmented[pivot_row] = (
                augmented[pivot_row],
                augmented[pivot_index],
            )
        pivot = augmented[pivot_index][pivot_index]
        for column in range(pivot_index, size + 1):
            augmented[pivot_index][column] /= pivot
        for row in range(size):
            if row == pivot_index:
                continue
            factor = augmented[row][pivot_index]
            for column in range(pivot_index, size + 1):
                augmented[row][column] -= factor * augmented[pivot_index][column]
    return tuple(augmented[row][size] for row in range(size))


def _read_glb(path: Path) -> tuple[dict[str, object], bytes]:
    with path.open('rb') as handle:
        magic, version, _length = struct.unpack('<4sII', handle.read(12))
        if magic != b'glTF' or version != 2:
            raise ValueError('expected glTF 2.0 binary file')
        json_length, json_type = struct.unpack('<I4s', handle.read(8))
        if json_type != b'JSON':
            raise ValueError('first GLB chunk must be JSON')
        json_doc = json.loads(handle.read(json_length).decode('utf-8'))
        binary = b''
        while True:
            chunk_header = handle.read(8)
            if not chunk_header:
                break
            chunk_length, chunk_type = struct.unpack('<I4s', chunk_header)
            chunk_data = handle.read(chunk_length)
            if chunk_type == b'BIN\x00':
                binary = chunk_data
                break
        if not binary:
            raise ValueError('GLB does not contain a binary buffer')
        return json_doc, binary


def _mesh_segments_from_gltf(
    json_doc: dict[str, object],
    binary: bytes,
    scale: float,
    max_edges: int,
) -> list[tuple[Vector3, Vector3]]:
    nodes = json_doc.get('nodes', [])
    meshes = json_doc.get('meshes', [])
    if not isinstance(nodes, list) or not isinstance(meshes, list):
        return []

    node_transforms = _node_translations(json_doc)
    segments: list[tuple[Vector3, Vector3]] = []
    stride = 1
    edge_budget = max_edges
    primitive_total = sum(
        len(mesh.get('primitives', []))
        for mesh in meshes
        if isinstance(mesh, dict)
    )
    if primitive_total > 0:
        edge_budget = max(1, max_edges // primitive_total)

    for node in nodes:
        if not isinstance(node, dict) or 'mesh' not in node:
            continue
        mesh_index = int(node['mesh'])
        if mesh_index >= len(meshes) or not isinstance(meshes[mesh_index], dict):
            continue
        translation = node_transforms.get(id(node), (0.0, 0.0, 0.0))
        mesh = meshes[mesh_index]
        primitives = mesh.get('primitives', [])
        if not isinstance(primitives, list):
            continue
        for primitive in primitives:
            if not isinstance(primitive, dict):
                continue
            if primitive.get('mode', 4) != 4:
                continue
            attributes = primitive.get('attributes', {})
            if not isinstance(attributes, dict) or 'POSITION' not in attributes:
                continue
            positions = _read_accessor_vec3(json_doc, binary, int(attributes['POSITION']))
            indices = _read_accessor_indices(json_doc, binary, primitive.get('indices'))
            if len(positions) < 3:
                continue
            triangle_count = len(indices) // 3 if indices else len(positions) // 3
            stride = max(1, math.ceil((triangle_count * 3) / max(1, edge_budget)))
            for tri_start in range(0, triangle_count * 3, 3 * stride):
                if indices:
                    triangle = indices[tri_start:tri_start + 3]
                    if len(triangle) < 3 or max(triangle) >= len(positions):
                        continue
                    points = [positions[index] for index in triangle]
                else:
                    points = positions[tri_start:tri_start + 3]
                    if len(points) < 3:
                        continue
                transformed = [
                    _transform_iss_vertex(point, translation, scale)
                    for point in points
                ]
                segments.extend((
                    (transformed[0], transformed[1]),
                    (transformed[1], transformed[2]),
                    (transformed[2], transformed[0]),
                ))
                if len(segments) >= max_edges:
                    return segments
    return segments


def _mesh_triangles_from_gltf(
    json_doc: dict[str, object],
    binary: bytes,
    scale: float,
) -> list[MeshTriangle]:
    nodes = json_doc.get('nodes', [])
    meshes = json_doc.get('meshes', [])
    if not isinstance(nodes, list) or not isinstance(meshes, list):
        return []

    node_transforms = _node_translations(json_doc)
    triangles: list[MeshTriangle] = []
    for node in nodes:
        if not isinstance(node, dict) or 'mesh' not in node:
            continue
        mesh_index = int(node['mesh'])
        if mesh_index >= len(meshes) or not isinstance(meshes[mesh_index], dict):
            continue
        translation = node_transforms.get(id(node), (0.0, 0.0, 0.0))
        mesh = meshes[mesh_index]
        primitives = mesh.get('primitives', [])
        if not isinstance(primitives, list):
            continue
        for primitive in primitives:
            if not isinstance(primitive, dict) or primitive.get('mode', 4) != 4:
                continue
            attributes = primitive.get('attributes', {})
            if not isinstance(attributes, dict) or 'POSITION' not in attributes:
                continue
            positions = _read_accessor_vec3(json_doc, binary, int(attributes['POSITION']))
            indices = _read_accessor_indices(json_doc, binary, primitive.get('indices'))
            if indices:
                triangles.extend(_triangles_from_indexed_positions(
                    positions,
                    indices,
                    translation,
                    scale,
                ))
            else:
                triangles.extend(_triangles_from_positions(positions, translation, scale))
    return _orient_triangles_outward(triangles)


def _triangles_from_indexed_positions(
    positions: list[Vector3],
    indices: list[int],
    translation: Vector3,
    scale_factor: float,
) -> list[MeshTriangle]:
    triangles: list[MeshTriangle] = []
    for start in range(0, len(indices) - 2, 3):
        triangle_indices = indices[start:start + 3]
        if max(triangle_indices) >= len(positions):
            continue
        vertices = tuple(
            _transform_iss_vertex(positions[index], translation, scale_factor)
            for index in triangle_indices
        )
        triangle = _make_mesh_triangle(vertices)
        if triangle is not None:
            triangles.append(triangle)
    return triangles


def _triangles_from_positions(
    positions: list[Vector3],
    translation: Vector3,
    scale_factor: float,
) -> list[MeshTriangle]:
    triangles: list[MeshTriangle] = []
    for start in range(0, len(positions) - 2, 3):
        vertices = tuple(
            _transform_iss_vertex(point, translation, scale_factor)
            for point in positions[start:start + 3]
        )
        triangle = _make_mesh_triangle(vertices)
        if triangle is not None:
            triangles.append(triangle)
    return triangles


def _make_mesh_triangle(vertices: tuple[Vector3, Vector3, Vector3]) -> MeshTriangle | None:
    edge_a = subtract(vertices[1], vertices[0])
    edge_b = subtract(vertices[2], vertices[0])
    normal_area = cross(edge_a, edge_b)
    double_area = norm(normal_area)
    if double_area <= 1.0e-10:
        return None
    area = 0.5 * double_area
    normal = scale(normal_area, 1.0 / double_area)
    centroid = (
        (vertices[0][0] + vertices[1][0] + vertices[2][0]) / 3.0,
        (vertices[0][1] + vertices[1][1] + vertices[2][1]) / 3.0,
        (vertices[0][2] + vertices[1][2] + vertices[2][2]) / 3.0,
    )
    return MeshTriangle(vertices=vertices, centroid=centroid, normal=normal, area=area)


def _orient_triangles_outward(triangles: list[MeshTriangle]) -> list[MeshTriangle]:
    if not triangles:
        return []
    total_area = sum(triangle.area for triangle in triangles)
    if total_area <= 0.0:
        return triangles
    center = (
        sum(triangle.centroid[0] * triangle.area for triangle in triangles) / total_area,
        sum(triangle.centroid[1] * triangle.area for triangle in triangles) / total_area,
        sum(triangle.centroid[2] * triangle.area for triangle in triangles) / total_area,
    )
    oriented: list[MeshTriangle] = []
    for triangle in triangles:
        outward = subtract(triangle.centroid, center)
        if dot(triangle.normal, outward) >= 0.0:
            oriented.append(triangle)
            continue
        oriented.append(MeshTriangle(
            vertices=triangle.vertices,
            centroid=triangle.centroid,
            normal=scale(triangle.normal, -1.0),
            area=triangle.area,
        ))
    return oriented


def _sample_triangles_by_area(
    triangles: tuple[MeshTriangle, ...],
    sample_count: int,
) -> list[MeshTriangle]:
    if not triangles:
        return []
    total_area = sum(triangle.area for triangle in triangles)
    if total_area <= 0.0:
        return list(triangles[:sample_count])
    selected: list[MeshTriangle] = []
    step = total_area / float(sample_count)
    threshold = 0.5 * step
    cumulative = 0.0
    for triangle in triangles:
        cumulative += triangle.area
        while cumulative >= threshold and len(selected) < sample_count:
            selected.append(triangle)
            threshold += step
        if len(selected) >= sample_count:
            break
    return selected


def _downsample_triangles(
    triangles: tuple[MeshTriangle, ...],
    max_triangles: int,
) -> list[MeshTriangle]:
    if max_triangles <= 0:
        return []
    if len(triangles) <= max_triangles:
        return list(triangles)
    stride = max(1, math.ceil(len(triangles) / float(max_triangles)))
    return list(triangles[::stride][:max_triangles])


def _segment_triangle_intersection(
    start: Vector3,
    end: Vector3,
    vertices: tuple[Vector3, Vector3, Vector3],
) -> bool:
    direction = subtract(end, start)
    length = norm(direction)
    if length <= 1.0e-12:
        return False
    edge_a = subtract(vertices[1], vertices[0])
    edge_b = subtract(vertices[2], vertices[0])
    p_vector = cross(direction, edge_b)
    determinant = dot(edge_a, p_vector)
    if abs(determinant) <= 1.0e-10:
        return False
    inv_determinant = 1.0 / determinant
    t_vector = subtract(start, vertices[0])
    u_value = dot(t_vector, p_vector) * inv_determinant
    if u_value < 0.0 or u_value > 1.0:
        return False
    q_vector = cross(t_vector, edge_a)
    v_value = dot(direction, q_vector) * inv_determinant
    if v_value < 0.0 or u_value + v_value > 1.0:
        return False
    distance_along_ray = dot(edge_b, q_vector) * inv_determinant
    segment_fraction = distance_along_ray / length
    return 1.0e-4 < segment_fraction < 1.0 - 1.0e-4


def _inside_camera_fov(
    chaser_position: Vector3,
    relative: Vector3,
    camera: CameraModel,
    aim_position: Vector3 | None = None,
) -> bool:
    if aim_position is None:
        try:
            boresight = unit(tuple(-float(value) for value in chaser_position))
        except ValueError:
            boresight = unit(relative)
    else:
        try:
            boresight = unit(subtract(aim_position, chaser_position))
        except ValueError:
            boresight = unit(relative)
    right, up = _camera_basis(boresight)
    forward = dot(relative, boresight)
    if forward <= 0.0:
        return False
    horizontal_angle = math.atan2(abs(dot(relative, right)), forward)
    vertical_angle = math.atan2(abs(dot(relative, up)), forward)
    return (
        horizontal_angle <= math.radians(camera.horizontal_fov_deg) / 2.0
        and vertical_angle <= math.radians(camera.vertical_fov_deg) / 2.0
    )


def _camera_basis(boresight: Vector3) -> tuple[Vector3, Vector3]:
    world_up = (0.0, 0.0, 1.0)
    if abs(dot(boresight, world_up)) > 0.95:
        world_up = (0.0, 1.0, 0.0)
    right = unit(cross(world_up, boresight))
    up = unit(cross(boresight, right))
    return right, up


def _node_translations(json_doc: dict[str, object]) -> dict[int, Vector3]:
    nodes = json_doc.get('nodes', [])
    if not isinstance(nodes, list):
        return {}
    scene_index = int(json_doc.get('scene', 0))
    scenes = json_doc.get('scenes', [])
    root_indices: list[int]
    if isinstance(scenes, list) and scene_index < len(scenes):
        scene = scenes[scene_index]
        root_indices = list(scene.get('nodes', [])) if isinstance(scene, dict) else []
    else:
        root_indices = list(range(len(nodes)))

    transforms: dict[int, Vector3] = {}

    def visit(node_index: int, parent_translation: Vector3) -> None:
        if node_index >= len(nodes) or not isinstance(nodes[node_index], dict):
            return
        node = nodes[node_index]
        translation_values = node.get('translation', (0.0, 0.0, 0.0))
        local_translation = _vector3_from_values(translation_values)
        translation = add(parent_translation, local_translation)
        transforms[id(node)] = translation
        for child_index in node.get('children', []):
            visit(int(child_index), translation)

    for root_index in root_indices:
        visit(int(root_index), (0.0, 0.0, 0.0))
    return transforms


def _read_accessor_vec3(
    json_doc: dict[str, object],
    binary: bytes,
    accessor_index: int,
) -> list[Vector3]:
    accessor, offset, stride = _accessor_buffer(json_doc, accessor_index)
    if accessor.get('componentType') != 5126 or accessor.get('type') != 'VEC3':
        return []
    count = int(accessor.get('count', 0))
    values: list[Vector3] = []
    for index in range(count):
        start = offset + index * stride
        values.append(struct.unpack_from('<fff', binary, start))
    return values


def _read_accessor_indices(
    json_doc: dict[str, object],
    binary: bytes,
    accessor_index: object,
) -> list[int]:
    if accessor_index is None:
        return []
    accessor, offset, stride = _accessor_buffer(json_doc, int(accessor_index))
    component_type = int(accessor.get('componentType', 0))
    count = int(accessor.get('count', 0))
    if component_type == 5123:
        fmt = '<H'
        default_stride = 2
    elif component_type == 5125:
        fmt = '<I'
        default_stride = 4
    else:
        return []
    stride = max(stride, default_stride)
    return [
        int(struct.unpack_from(fmt, binary, offset + index * stride)[0])
        for index in range(count)
    ]


def _accessor_buffer(
    json_doc: dict[str, object],
    accessor_index: int,
) -> tuple[dict[str, object], int, int]:
    accessors = json_doc['accessors']
    buffer_views = json_doc['bufferViews']
    accessor = accessors[accessor_index]
    buffer_view = buffer_views[int(accessor['bufferView'])]
    offset = int(buffer_view.get('byteOffset', 0)) + int(accessor.get('byteOffset', 0))
    stride = int(buffer_view.get('byteStride', 0))
    if stride <= 0:
        component_type = int(accessor.get('componentType', 5126))
        component_size = 2 if component_type == 5123 else 4
        component_count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}.get(
            accessor.get('type', 'SCALAR'),
            1,
        )
        stride = component_size * component_count
    return accessor, offset, stride


def _transform_iss_vertex(point: Vector3, translation: Vector3, scale_factor: float) -> Vector3:
    translated = add(point, translation)
    # Match the SDF visual pose: roll=0, pitch=90 deg, yaw=0, then scale.
    return (
        scale_factor * translated[2],
        scale_factor * translated[1],
        -scale_factor * translated[0],
    )


def _vector3_from_values(values: object) -> Vector3:
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        return (0.0, 0.0, 0.0)
    return (float(values[0]), float(values[1]), float(values[2]))


def _draw_proxy_wireframe(axis) -> None:
    boxes = (
        ((0.0, 0.0, 0.0), (80.0, 4.0, 4.0)),
        ((-25.0, 0.0, 12.0), (30.0, 1.0, 12.0)),
        ((25.0, 0.0, 12.0), (30.0, 1.0, 12.0)),
    )
    for center, size in boxes:
        axis.add_collection3d(Line3DCollection(
            _box_edges(center, size),
            colors='#9A9A9A',
            linewidths=0.45,
            alpha=0.25,
        ))


def _box_edges(center: Vector3, size: Vector3) -> list[tuple[Vector3, Vector3]]:
    cx, cy, cz = center
    sx, sy, sz = (size[0] / 2.0, size[1] / 2.0, size[2] / 2.0)
    corners = [
        (cx + dx * sx, cy + dy * sy, cz + dz * sz)
        for dx in (-1.0, 1.0)
        for dy in (-1.0, 1.0)
        for dz in (-1.0, 1.0)
    ]
    edges = []
    for i, first in enumerate(corners):
        for second in corners[i + 1:]:
            differences = sum(
                1 for axis in range(3)
                if abs(first[axis] - second[axis]) > 1.0e-9
            )
            if differences == 1:
                edges.append((first, second))
    return edges


def _style_3d_axis(axis) -> None:
    axis.set_xlabel('$x_{LVLH}$ [m]', labelpad=7)
    axis.set_ylabel('$y_{LVLH}$ [m]', labelpad=7)
    axis.set_zlabel('$z_{LVLH}$ [m]', labelpad=7)
    axis.view_init(elev=22.0, azim=-58.0)
    axis.grid(True, color='#ECECEC', linewidth=0.45)
    for pane in (axis.xaxis.pane, axis.yaxis.pane, axis.zaxis.pane):
        pane.set_facecolor((1.0, 1.0, 1.0, 0.0))
        pane.set_edgecolor('#E6E6E6')


def _set_equal_3d_axes(axis, *point_sets: Iterable[object]) -> None:
    points: list[Vector3] = []
    for point_set in point_sets:
        for item in point_set:
            if isinstance(item, InspectionTarget):
                points.append(item.position)
            elif isinstance(item, SelectedViewpoint):
                points.append(item.candidate.position)
            elif isinstance(item, (tuple, list)) and len(item) >= 3:
                points.append((float(item[0]), float(item[1]), float(item[2])))
    points.extend(((-45.0, -25.0, -18.0), (45.0, 25.0, 22.0)))
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    centers = (
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0,
        (min(zs) + max(zs)) / 2.0,
    )
    radius = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) / 2.0
    radius = max(radius, 1.0) * 1.04
    axis.set_xlim(centers[0] - radius, centers[0] + radius)
    axis.set_ylim(centers[1] - radius, centers[1] + radius)
    axis.set_zlim(centers[2] - radius, centers[2] + radius)


def _normalized_values(values: list[float]) -> list[float]:
    if not values:
        return []
    minimum = min(values)
    maximum = max(values)
    span = max(maximum - minimum, 1.0e-12)
    return [(value - minimum) / span for value in values]


def _save_publishable_figure(figure, path: Path) -> None:
    figure.savefig(path)
    for suffix in ('.pdf', '.svg'):
        figure.savefig(path.with_suffix(suffix))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--config',
        default='src/orbinspect_guidance/config/offline_coverage_planner.yaml',
        help='YAML planner config file.',
    )
    parser.add_argument('--geometry', choices=['proxy', 'mesh'])
    parser.add_argument('--target-spacing', type=float)
    parser.add_argument('--candidate-radius', type=float)
    parser.add_argument('--candidate-stride', type=int)
    parser.add_argument('--coverage-threshold', type=float)
    parser.add_argument('--max-viewpoints', type=int)
    parser.add_argument('--transfer-duration', type=float)
    parser.add_argument('--integration-dt', type=float)
    parser.add_argument('--max-acceleration', type=float)
    parser.add_argument('--mesh-target-count', type=int)
    parser.add_argument('--mesh-occlusion-max-triangles', type=int)
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
        'mesh_target_count': args.mesh_target_count,
        'mesh_occlusion_max_triangles': args.mesh_occlusion_max_triangles,
        'output_root': args.output_root,
        'run_id': args.run_id,
    }
    for key, value in overrides.items():
        if value not in (None, ''):
            config_values[key] = value

    if 'output_root' in config_values:
        config_values['output_root'] = Path(str(config_values['output_root']))
    if 'iss_mesh_path' in config_values:
        config_values['iss_mesh_path'] = Path(str(config_values['iss_mesh_path']))
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
    raw = _safe_load_yaml_mapping(path)
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
    """Run the offline planner and save paper-grade outputs."""
    config = config_from_args(parse_args(argv))
    planner = OfflineCoveragePlanner(config)
    plan = planner.plan()
    run_dir = planner.save_plan(plan)
    print(json.dumps({'run_dir': str(run_dir), **plan.summary}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
