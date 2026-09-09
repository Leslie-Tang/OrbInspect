"""Generate all OrbInspect manuscript figures from archived simulation results.

The simulation writes CSV files under ``data/offline_high_coverage_experiment``.
This script only loads those saved results and plots them. Each exported figure
has one public ``plot_*`` function so that its layout can be edited in isolation.
Shared colors, sizes, camera angles, and export settings are collected below.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


# ---------------------------------------------------------------------------
# Manual figure settings
# ---------------------------------------------------------------------------

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['svg.fonttype'] = 'none'
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False
plt.rcParams['axes.linewidth'] = 1.1
plt.rcParams['legend.frameon'] = False
plt.rcParams['savefig.facecolor'] = 'white'
plt.rcParams['font.size'] = 9
plt.rcParams['axes.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 8
plt.rcParams['xtick.labelsize'] = 8
plt.rcParams['ytick.labelsize'] = 8
plt.rcParams['figure.dpi'] = 180
plt.rcParams['savefig.dpi'] = 360
plt.rcParams['svg.hashsalt'] = 'orbinspect-paper'

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data' / 'offline_high_coverage_experiment' / 'raw'
VALIDATION_PATH = ROOT / 'data' / 'validation_matrix' / 'validation_matrix_summary.csv'
MESH_PATH = ROOT / 'data' / 'iss_mesh' / 'ISS_stationary.glb'
FIGURE_DIR = ROOT / 'figures' / 'high_coverage'
ARCHIVED_FIGURE_DIR = ROOT / 'data' / 'offline_high_coverage_experiment' / 'figures'
MESH_SCALE = 1.065
MESH_EDGE_BUDGET = 60000
MESH_FACE_BUDGET = 90000
EXPORT_DPI = 360
EXPORT_FORMATS = ('.png', '.pdf', '.svg')
VIEW_ELEVATION = 20.0
VIEW_AZIMUTH = -54.0
FIGURE_SIZES = {
    'proposed_trajectory': (3.5, 3.8),
    'method_comparison': (8.4, 2.95),
    'method_panel': (1.30, 1.22),
    'tradeoff_summary': (5.6, 3.8),
    'camera_frusta': (3.5, 4.8),
    'camera_coverage': (6.0, 3.8),
    'camera_summary': (7.1, 3.2),
    'coverage_comparison': (3.5, 3.25),
    'metric_bar': (7.0, 3.15),
    'target_density': (3.5, 3.15),
    'candidate_density': (5.9, 3.75),
    'initial_condition': (3.5, 3.15),
    'transfer_duration': (5.9, 3.75),
    'ablation': (5.9, 3.75),
}
METHOD_ORDER = (
    'set_cover_cw_tour',
    'proposed_safe_cw_nbv',
    'coverage_greedy',
    'safe_coverage_greedy',
    'distance_greedy',
    'fuel_greedy',
    'random_safe',
)
METHOD_COLORS = {
    'set_cover_cw_tour': '#0F4D92',
    'proposed_safe_cw_nbv': '#7884B4',
    'coverage_greedy': '#B64342',
    'safe_coverage_greedy': '#E28E2C',
    'distance_greedy': '#7BAA5B',
    'fuel_greedy': '#9A4D8E',
    'random_safe': '#767676',
}
METHOD_LABELS = {
    'set_cover_cw_tour': 'Proposed dynamics-aware tour',
    'proposed_safe_cw_nbv': 'CW-NBV baseline',
    'coverage_greedy': 'Coverage greedy',
    'safe_coverage_greedy': 'Safe coverage greedy',
    'distance_greedy': 'Nearest NBV',
    'fuel_greedy': 'Fuel greedy',
    'random_safe': 'Random safe',
}
METHOD_LABELS_SHORT = {
    'set_cover_cw_tour': 'Proposed',
    'proposed_safe_cw_nbv': 'CW-NBV',
    'coverage_greedy': 'Coverage',
    'safe_coverage_greedy': 'Safe cov.',
    'distance_greedy': 'Nearest',
    'fuel_greedy': 'Fuel',
    'random_safe': 'Random',
}
NMI_PASTEL = {
    'baseline_dark': '#484878',
    'baseline_mid': '#7884B4',
    'baseline_soft': '#B4C0E4',
    'ours_tiny': '#E4E4F0',
    'ours_base': '#E4CCD8',
    'ours_large': '#F0C0CC',
    'delta_up': '#2E9E44',
    'delta_down': '#E53935',
}
REPRESENTATIVE_VIEW_COLORS = ('#526CA8', '#9C6A8F', '#D47A8D')
REPRESENTATIVE_VIEW_LABELS = ('Early', 'Middle', 'Final')

Point3 = tuple[float, float, float]
MeshSegment = tuple[Point3, Point3]
MeshFace = tuple[Point3, Point3, Point3]
Viewpoint = dict[str, float]
MethodRow = dict[str, object]


@dataclass(frozen=True)
class FigureData:
    """All saved simulation results and mesh geometry needed by the figures."""

    trajectories: dict[str, list[Point3]]
    viewpoints: dict[str, list[Viewpoint]]
    method_rows: list[MethodRow]
    coverage_rows: dict[str, list[tuple[float, float]]]
    mesh_segments: list[MeshSegment]
    mesh_faces: list[MeshFace]
    comparison_segments: list[MeshSegment]
    comparison_faces: list[MeshFace]
    comparison_points: list[Point3]


# ---------------------------------------------------------------------------
# Entry point and saved-result loading
# ---------------------------------------------------------------------------

def main() -> None:
    """Regenerate every paper figure from one read-only data bundle."""
    for output_dir in (FIGURE_DIR, ARCHIVED_FIGURE_DIR):
        output_dir.mkdir(parents=True, exist_ok=True)
    data = load_figure_data()

    # Main trajectory and camera figures.
    plot_proposed_trajectory(FIGURE_DIR / 'proposed_trajectory_3d', data)
    plot_camera_model_frusta(FIGURE_DIR / 'camera_model_frusta', data)
    plot_camera_model_coverage(FIGURE_DIR / 'camera_model_coverage', data)

    # Method trajectory figures. Each call creates exactly one exported figure.
    plot_proposed_method_trajectory(FIGURE_DIR / 'trajectory_method_proposed', data)
    plot_cw_nbv_trajectory(FIGURE_DIR / 'trajectory_method_cw_nbv', data)
    plot_coverage_greedy_trajectory(FIGURE_DIR / 'trajectory_method_coverage', data)
    plot_safe_coverage_trajectory(FIGURE_DIR / 'trajectory_method_safe_coverage', data)
    plot_nearest_trajectory(FIGURE_DIR / 'trajectory_method_nearest', data)
    plot_fuel_trajectory(FIGURE_DIR / 'trajectory_method_fuel', data)
    plot_random_trajectory(FIGURE_DIR / 'trajectory_method_random', data)
    plot_trajectory_tradeoff_summary(FIGURE_DIR / 'trajectory_tradeoff_summary', data)
    # Sensitivity figures retained in the manuscript.
    plot_target_density_sensitivity(FIGURE_DIR / 'target_density_sensitivity')
    plot_initial_condition_robustness(FIGURE_DIR / 'initial_condition_robustness')

    # Optional diagnostic exports. Their numerical results are summarized in
    # the manuscript, but the sparse plots are not included as main figures.
    plot_candidate_density_sensitivity(FIGURE_DIR / 'candidate_density_sensitivity')
    plot_transfer_duration_sensitivity(FIGURE_DIR / 'transfer_duration_sensitivity')
    plot_ablation_comparison(FIGURE_DIR / 'ablation_comparison')

    # Quantitative comparisons are mirrored into the archived result directory.
    for output_dir in (FIGURE_DIR, ARCHIVED_FIGURE_DIR):
        plot_coverage_comparison(output_dir / 'coverage_comparison', data)
        plot_delta_v_comparison(output_dir / 'delta_v_comparison', data)
        plot_energy_efficiency_comparison(output_dir / 'energy_efficiency_comparison', data)
        plot_safety_comparison(output_dir / 'safety_comparison', data)
        plot_peak_input_comparison(output_dir / 'peak_input_comparison', data)


def load_figure_data() -> FigureData:
    """Load saved experiment results and prepare reusable plotting geometry."""
    trajectories = load_trajectories(DATA_DIR / 'trajectory.csv')
    viewpoints = load_viewpoints(DATA_DIR / 'viewpoints.csv')
    method_rows = load_method_rows(DATA_DIR / 'method_comparison.csv')
    coverage_rows = load_coverage_rows(DATA_DIR / 'coverage.csv')
    mesh_segments = load_mesh_segments(MESH_PATH, scale=MESH_SCALE, max_edges=MESH_EDGE_BUDGET)
    mesh_faces = load_mesh_faces(MESH_PATH, scale=MESH_SCALE, max_faces=MESH_FACE_BUDGET)
    figure_methods = [method for method in METHOD_ORDER if method in trajectories]
    comparison_points = [
        point
        for method in figure_methods
        for point in trajectories.get(method, [])
    ]
    return FigureData(
        trajectories=trajectories,
        viewpoints=viewpoints,
        method_rows=method_rows,
        coverage_rows=coverage_rows,
        mesh_segments=mesh_segments,
        mesh_faces=mesh_faces,
        comparison_segments=_stride_sequence(mesh_segments, 10, 7000),
        comparison_faces=_stride_sequence(mesh_faces, 14, 4500),
        comparison_points=comparison_points,
    )


def load_trajectories(path: Path) -> dict[str, list[Point3]]:
    """Load method-indexed LVLH trajectory samples."""
    by_method: dict[str, list[Point3]] = {}
    with path.open(newline='') as handle:
        for row in csv.DictReader(handle):
            by_method.setdefault(row['method'], []).append((
                float(row['rx']),
                float(row['ry']),
                float(row['rz']),
            ))
    return by_method


def load_viewpoints(path: Path) -> dict[str, list[Viewpoint]]:
    """Load selected viewpoint positions and coverage values."""
    by_method: dict[str, list[Viewpoint]] = {}
    with path.open(newline='') as handle:
        for row in csv.DictReader(handle):
            by_method.setdefault(row['method'], []).append({
                'sequence': float(row['sequence']),
                'x': float(row['viewpoint_x']),
                'y': float(row['viewpoint_y']),
                'z': float(row['viewpoint_z']),
                'boresight_x': float(row['boresight_x']),
                'boresight_y': float(row['boresight_y']),
                'boresight_z': float(row['boresight_z']),
                'coverage': float(row['cumulative_coverage']),
            })
    return by_method


def load_method_rows(path: Path) -> list[MethodRow]:
    """Load method-level benchmark metrics in a fixed manuscript order."""
    rows: dict[str, MethodRow] = {}
    with path.open(newline='') as handle:
        for row in csv.DictReader(handle):
            rows[row['method']] = {
                'method': row['method'],
                'final_coverage_ratio': float(row['final_coverage_ratio']),
                'final_inspectable_coverage_ratio': float(row['final_inspectable_coverage_ratio']),
                'coverage_success': row['coverage_success'].lower() == 'true',
                'feasible': row['feasible'].lower() == 'true',
                'total_delta_v': float(row['total_delta_v']),
                'peak_requested_input': float(row['peak_requested_input']),
                'min_clearance': float(row['min_clearance']),
                'delta_v_per_raw_coverage': float(row['delta_v_per_raw_coverage']),
                'coverage_per_delta_v': float(row['coverage_per_delta_v']),
                'selected_viewpoint_count': float(row['selected_viewpoint_count']),
                'mission_duration': float(row['mission_duration']),
                'planning_time': float(row['planning_time']),
            }
    return [rows[method] for method in METHOD_ORDER if method in rows]


def load_coverage_rows(path: Path) -> dict[str, list[tuple[float, float]]]:
    """Load coverage timelines by method."""
    rows: dict[str, list[tuple[float, float]]] = {}
    with path.open(newline='') as handle:
        for row in csv.DictReader(handle):
            rows.setdefault(row['method'], []).append((float(row['time']), float(row['coverage_ratio'])))
    return rows


def load_validation_rows(path: Path) -> list[MethodRow]:
    """Load the archived validation matrix without rerunning any simulation."""
    numeric_fields = {
        'mesh_target_count',
        'candidate_stride',
        'candidate_radius',
        'safety_margin',
        'transfer_duration',
        'max_acceleration',
        'candidate_count',
        'selected_viewpoint_count',
        'final_coverage_ratio',
        'final_inspectable_coverage_ratio',
        'total_delta_v',
        'peak_requested_input',
        'min_clearance',
        'mission_duration',
        'planning_time',
    }
    rows: list[MethodRow] = []
    with path.open(newline='') as handle:
        for source_row in csv.DictReader(handle):
            row: MethodRow = dict(source_row)
            for field in numeric_fields:
                row[field] = float(source_row[field])
            row['coverage_success'] = source_row['coverage_success'].lower() == 'true'
            row['feasible'] = source_row['feasible'].lower() == 'true'
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Quantitative comparison figures
# ---------------------------------------------------------------------------

def plot_coverage_comparison(
    path: Path,
    data: FigureData,
) -> None:
    """Plot coverage progression with consistent method styling."""
    fig, ax = plt.subplots(figsize=FIGURE_SIZES['coverage_comparison'])
    _draw_coverage_progress(ax, data)
    save_all(fig, path)


def _draw_coverage_progress(ax, data: FigureData) -> None:
    """Draw coverage histories with final performance and feasibility visible."""
    for row in data.method_rows:
        method = str(row['method'])
        timeline = data.coverage_rows.get(method, [])
        if not timeline:
            continue
        final_raw = float(row['final_coverage_ratio'])
        final_inspectable = float(row['final_inspectable_coverage_ratio'])
        scale_factor = final_inspectable / max(final_raw, 1.0e-12)
        is_proposed = method == 'set_cover_cw_tour'
        times = [item[0] for item in timeline]
        coverages = [min(1.0, item[1] * scale_factor) for item in timeline]
        feasible = bool(row['feasible'])
        ax.step(
            times,
            coverages,
            where='post',
            linewidth=2.2 if is_proposed else 1.15,
            color=METHOD_COLORS.get(method, '#4D4D4D'),
            linestyle='--' if not feasible else '-',
            alpha=1.0 if is_proposed else 0.76,
            label=(
                f"{METHOD_LABELS_SHORT.get(method, method)} "
                f"{100.0 * final_inspectable:.1f}%"
                f"{' [X]' if not feasible else ''}"
            ),
            zorder=4 if is_proposed else 2,
        )
        ax.scatter(
            times[-1],
            coverages[-1],
            s=30 if is_proposed else 19,
            marker='X' if not feasible else ('*' if is_proposed else 'o'),
            color=METHOD_COLORS.get(method, '#4D4D4D'),
            edgecolor='white',
            linewidth=0.45,
            zorder=6,
        )
    ax.axhline(0.70, color='#A0A6AD', linestyle='--', linewidth=0.8, alpha=0.9)
    ax.text(
        0.985,
        0.685,
        '70% success',
        transform=ax.get_yaxis_transform(),
        ha='right',
        va='top',
        fontsize=6.0,
        color='#626971',
    )
    ax.axhline(0.98, color='#555555', linestyle=':', linewidth=0.9, alpha=0.8)
    ax.text(
        0.985,
        0.972,
        '98% target',
        transform=ax.get_yaxis_transform(),
        ha='right',
        va='top',
        fontsize=6.0,
        color='#444444',
    )
    ax.text(
        0.025,
        0.955,
        'Proposed: 21 SOOAs\n'
        r'$\Delta v=21.59$ m s$^{-1}$; $d_{\min}=9.91$ m',
        transform=ax.transAxes,
        ha='left',
        va='top',
        fontsize=6.4,
        color=METHOD_COLORS['set_cover_cw_tour'],
        fontweight='bold',
    )
    ax.set_xlabel('Mission time (s)', fontsize=7.5)
    ax.set_ylabel('Inspectable coverage', fontsize=7.5)
    ax.set_xlim(-40.0, 3340.0)
    ax.set_ylim(0.0, 1.015)
    ax.grid(True, axis='y', color='#E4E7EA', linewidth=0.55)
    ax.tick_params(labelsize=6.8)
    ax.legend(
        frameon=False,
        ncol=2,
        fontsize=5.8,
        loc='lower right',
        columnspacing=0.65,
        handlelength=1.55,
        handletextpad=0.32,
        borderaxespad=0.35,
    )


def plot_delta_v_comparison(
    path: Path,
    data: FigureData,
) -> None:
    """Plot the saved total delta-v comparison."""
    _plot_metric_bar(
        path,
        data.method_rows,
        'total_delta_v',
        r'Total $\Delta v$ (m s$^{-1}$)',
    )


def plot_energy_efficiency_comparison(
    path: Path,
    data: FigureData,
) -> None:
    """Plot the saved energy-efficiency comparison."""
    _plot_metric_bar(
        path,
        data.method_rows,
        'delta_v_per_raw_coverage',
        r'$\Delta v$ per covered area ratio (m s$^{-1}$)',
    )


def plot_safety_comparison(
    path: Path,
    data: FigureData,
) -> None:
    """Plot the saved minimum-clearance comparison."""
    _plot_metric_bar(
        path,
        data.method_rows,
        'min_clearance',
        'Minimum clearance (m)',
        flag_infeasible=True,
    )


def plot_peak_input_comparison(
    path: Path,
    data: FigureData,
) -> None:
    """Plot the saved peak-input comparison."""
    _plot_metric_bar(
        path,
        data.method_rows,
        'peak_requested_input',
        r'Peak requested input (m s$^{-2}$)',
    )


def _plot_metric_bar(
    path: Path,
    method_rows: list[MethodRow],
    key: str,
    xlabel: str,
    flag_infeasible: bool = False,
) -> None:
    """Shared implementation for one compact horizontal metric figure."""
    fig, ax = plt.subplots(figsize=FIGURE_SIZES['metric_bar'])
    values = [float(row[key]) for row in method_rows]
    y_positions = list(range(len(method_rows)))
    labels = [METHOD_LABELS_SHORT.get(str(row['method']), str(row['method'])) for row in method_rows]
    colors = [METHOD_COLORS.get(str(row['method']), '#767676') for row in method_rows]
    edge_colors = ['#0F4D92' if row['method'] == 'set_cover_cw_tour' else '#4D4D4D' for row in method_rows]
    line_widths = [1.3 if row['method'] == 'set_cover_cw_tour' else 0.5 for row in method_rows]

    ax.barh(
        y_positions,
        values,
        color=colors,
        edgecolor=edge_colors,
        linewidth=line_widths,
        alpha=0.96,
        height=0.64,
    )
    ax.invert_yaxis()
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    ax.set_xlabel(xlabel)
    ax.grid(True, axis='x', color='#E1E1E1', linewidth=0.6)
    ax.set_axisbelow(True)
    x_min = min(values) if values else 0.0
    x_max = max(values) if values else 1.0
    span = max(x_max - min(0.0, x_min), 1.0e-9)
    left_limit = min(0.0, x_min - 0.14 * span)
    right_limit = x_max + 0.18 * span
    ax.set_xlim(left_limit, right_limit)
    if x_min < 0.0:
        ax.axvline(0.0, color='#272727', linewidth=0.9, alpha=0.65)
    for y_position, value, row in zip(y_positions, values, method_rows):
        text = f'{value:.2f}' if value >= 1.0 else f'{value:.3f}'
        if value < 0.0:
            x_text = value - 0.018 * span
            ha = 'right'
        else:
            x_text = value + 0.018 * span
            ha = 'left'
        ax.text(
            x_text,
            y_position,
            text,
            va='center',
            ha=ha,
            fontsize=8,
            color='#272727',
            fontweight='bold' if row['method'] == 'set_cover_cw_tour' else 'normal',
        )
        if flag_infeasible and row['method'] == 'coverage_greedy' and not bool(row['feasible']):
            ax.text(
                right_limit - 0.01 * span,
                y_position,
                'keep-out violation',
                va='center',
                ha='right',
                fontsize=7,
                color='#B64342',
            )
    save_all(fig, path)


# ---------------------------------------------------------------------------
# Trajectory figures
# ---------------------------------------------------------------------------

def plot_proposed_trajectory(
    path: Path,
    data: FigureData,
) -> None:
    """Plot the proposed trajectory in the same frame as the ISS mesh."""
    trajectory = data.trajectories['set_cover_cw_tour']
    viewpoints = data.viewpoints['set_cover_cw_tour']
    fig = plt.figure(figsize=FIGURE_SIZES['proposed_trajectory'])
    ax = fig.add_axes((0.07, 0.15, 0.85, 0.74), projection='3d')
    draw_mesh_method_context(ax, data.comparison_segments, data.comparison_faces)

    xs, ys, zs = unzip_points(trajectory)
    ax.plot(xs, ys, zs, color=METHOD_COLORS['set_cover_cw_tour'], linewidth=2.0, label='HCW transfer sequence', zorder=8)
    ax.scatter([xs[0]], [ys[0]], [zs[0]], s=62, c=NMI_PASTEL['delta_up'], edgecolors='white', linewidths=0.6, marker='o', label='Start', depthshade=False, zorder=10)
    ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], s=82, c=NMI_PASTEL['delta_down'], edgecolors='white', linewidths=0.6, marker='X', label='End', depthshade=False, zorder=10)

    if viewpoints:
        ax.scatter(
            [item['x'] for item in viewpoints],
            [item['y'] for item in viewpoints],
            [item['z'] for item in viewpoints],
            c='#78A6D8',
            s=48,
            marker='^',
            edgecolors='#17365D',
            linewidths=0.45,
            depthshade=False,
            label='Selected SOOA dwell poses',
            zorder=9,
        )

    style_axis(ax)
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_zlabel('')
    ax.tick_params(axis='both', labelsize=6.3, pad=0)
    set_equal_axes(ax, data.comparison_segments, trajectory)
    ax.legend(
        loc='upper left',
        frameon=False,
        fontsize=6.0,
        handlelength=1.6,
        handletextpad=0.35,
        labelspacing=0.25,
    )
    ax.text2D(
        0.985,
        0.965,
        '21 SOOAs | 1,890 s\n'
        r'$\Delta v=21.59$ m s$^{-1}$',
        transform=ax.transAxes,
        ha='right',
        va='top',
        fontsize=6.2,
        color='#243247',
        fontweight='bold',
    )
    fig.text(
        0.5,
        0.025,
        'LVLH axes: x radial; y along-track; z cross-track (m)',
        ha='center',
        va='bottom',
        fontsize=6.2,
        color='#444444',
    )
    save_all(fig, path, tight=False)


def plot_method_comparison(
    path: Path,
    data: FigureData,
) -> None:
    """Plot all method trajectories as one optional overview figure."""
    figure_methods = [method for method in METHOD_ORDER if method in data.trajectories]
    fig = plt.figure(figsize=FIGURE_SIZES['method_comparison'])
    panel_boxes = (
        (0.000, 0.492, 0.335, 0.475),
        (0.332, 0.492, 0.335, 0.475),
        (0.665, 0.492, 0.335, 0.475),
        (0.000, 0.000, 0.262, 0.465),
        (0.246, 0.000, 0.262, 0.465),
        (0.492, 0.000, 0.262, 0.465),
        (0.738, 0.000, 0.262, 0.465),
    )

    for panel_index, method in enumerate(figure_methods):
        ax = fig.add_axes(panel_boxes[panel_index], projection='3d')
        draw_mesh_method_context(ax, data.comparison_segments, data.comparison_faces)
        _draw_method_trajectory(
            ax,
            method,
            data.trajectories.get(method, []),
            data.viewpoints.get(method, []),
            start_size=24,
            end_size=30,
            viewpoint_size=18,
        )
        style_method_comparison_axis(ax, zoom=1.0)
        set_equal_axes(ax, [], data.comparison_points)
        title = METHOD_LABELS_SHORT.get(method, METHOD_LABELS.get(method, method))
        if method == 'coverage_greedy':
            title += ' (infeasible)'
        ax.set_title(title, fontsize=8.1, color=METHOD_COLORS.get(method, '#333333'), pad=0.5)

    save_all(fig, path, tight=False)


def plot_proposed_method_trajectory(path: Path, data: FigureData) -> None:
    """Plot the compact proposed-method trajectory panel."""
    _plot_method_trajectory_panel(path, 'set_cover_cw_tour', data)


def plot_cw_nbv_trajectory(path: Path, data: FigureData) -> None:
    """Plot the compact CW-NBV baseline trajectory panel."""
    _plot_method_trajectory_panel(path, 'proposed_safe_cw_nbv', data)


def plot_coverage_greedy_trajectory(path: Path, data: FigureData) -> None:
    """Plot the compact coverage-greedy trajectory panel."""
    _plot_method_trajectory_panel(path, 'coverage_greedy', data)


def plot_safe_coverage_trajectory(path: Path, data: FigureData) -> None:
    """Plot the compact safe-coverage trajectory panel."""
    _plot_method_trajectory_panel(path, 'safe_coverage_greedy', data)


def plot_nearest_trajectory(path: Path, data: FigureData) -> None:
    """Plot the compact nearest-NBV trajectory panel."""
    _plot_method_trajectory_panel(path, 'distance_greedy', data)


def plot_fuel_trajectory(path: Path, data: FigureData) -> None:
    """Plot the compact fuel-greedy trajectory panel."""
    _plot_method_trajectory_panel(path, 'fuel_greedy', data)


def plot_random_trajectory(path: Path, data: FigureData) -> None:
    """Plot the compact random-safe trajectory panel."""
    _plot_method_trajectory_panel(path, 'random_safe', data)


def plot_trajectory_tradeoff_summary(path: Path, data: FigureData) -> None:
    """Plot the coverage-effort-feasibility trade-off summary."""
    fig, ax = plt.subplots(figsize=FIGURE_SIZES['tradeoff_summary'])
    _draw_coverage_effort_summary(ax, data.method_rows)
    save_all(fig, path)


def plot_target_density_sensitivity(path: Path) -> None:
    """Plot effort at matched coverage across target-density cases."""
    rows = [row for row in load_validation_rows(VALIDATION_PATH) if row['study'] == 'target_density']
    fig, ax = plt.subplots(figsize=FIGURE_SIZES['target_density'])
    methods = ('set_cover_cw_tour', 'safe_coverage_greedy', 'coverage_greedy')
    for method in methods:
        method_rows = [
            row
            for row in rows
            if row['method'] == method and float(row['mesh_target_count']) <= 500.0
        ]
        method_rows.sort(key=lambda row: float(row['mesh_target_count']))
        x_values = [float(row['mesh_target_count']) for row in method_rows]
        y_values = [float(row['total_delta_v']) for row in method_rows]
        ax.plot(
            x_values,
            y_values,
            color=METHOD_COLORS[method],
            linewidth=1.8 if method == 'set_cover_cw_tour' else 1.25,
            linestyle='--' if method == 'coverage_greedy' else '-',
            label=METHOD_LABELS_SHORT[method],
            zorder=3,
        )
        for row, x_value, y_value in zip(method_rows, x_values, y_values):
            is_feasible = bool(row['feasible'])
            ax.scatter(
                x_value,
                y_value,
                s=68 if method == 'set_cover_cw_tour' else 44,
                marker='X' if not is_feasible else ('*' if method == 'set_cover_cw_tour' else 'o'),
                color=METHOD_COLORS[method],
                edgecolor='white',
                linewidth=0.55,
                zorder=5,
            )
            coverage = 100.0 * float(row['final_inspectable_coverage_ratio'])
            action_count = int(round(float(row['selected_viewpoint_count'])))
            dy = -10 if method == 'set_cover_cw_tour' else (4 if method == 'safe_coverage_greedy' else 6)
            va = 'top' if method == 'set_cover_cw_tour' else 'bottom'
            ax.annotate(
                f'{coverage:.1f}%, {action_count}',
                (x_value, y_value),
                xytext=(0, dy),
                textcoords='offset points',
                ha='center',
                va=va,
                fontsize=5.7,
                color=METHOD_COLORS[method],
            )

    stress = next(
        row
        for row in rows
        if row['method'] == 'set_cover_cw_tour' and float(row['mesh_target_count']) == 1000.0
    )
    stress_x = float(stress['mesh_target_count'])
    stress_y = float(stress['total_delta_v'])
    ax.axvspan(735, 1065, color='#EFF2F5', alpha=0.90, zorder=0)
    ax.scatter(
        stress_x,
        stress_y,
        s=58,
        marker='o',
        facecolor='white',
        edgecolor=METHOD_COLORS['set_cover_cw_tour'],
        linewidth=1.2,
        zorder=5,
    )
    ax.annotate(
        '77.1%, 21*',
        xy=(stress_x, stress_y),
        xytext=(-2, -12),
        textcoords='offset points',
        ha='right',
        va='top',
        fontsize=5.8,
        color=METHOD_COLORS['set_cover_cw_tour'],
    )
    ax.text(
        900,
        55.8,
        'Coarsened-library\nstress case',
        ha='center',
        va='top',
        fontsize=5.8,
        color='#666666',
    )
    ax.text(
        0.02,
        0.98,
        'Point labels: inspectable coverage, SOOA count; X = infeasible.',
        transform=ax.transAxes,
        ha='left',
        va='top',
        fontsize=5.7,
        color='#555555',
    )
    ax.set_xlabel('Surface-target count and accepted candidates', fontsize=7.2)
    ax.set_ylabel(r'Total $\Delta v$ (m s$^{-1}$)', fontsize=7.2)
    ax.set_xticks([180, 500, 1000])
    ax.set_xticklabels(['180\n357 candidates', '500\n981 candidates', '1000*\n491 candidates'])
    ax.set_xlim(115, 1065)
    ax.set_ylim(15.0, 58.0)
    ax.grid(True, axis='y', color='#E4E7EA', linewidth=0.6)
    ax.legend(
        loc='center',
        bbox_to_anchor=(0.5, 0.50),
        ncol=3,
        fontsize=5.9,
        columnspacing=0.7,
        handlelength=1.5,
        handletextpad=0.35,
        frameon=False,
    )
    save_all(fig, path)


def plot_candidate_density_sensitivity(path: Path) -> None:
    """Plot coverage and safety behavior as the candidate library is thinned."""
    rows = [row for row in load_validation_rows(VALIDATION_PATH) if row['study'] == 'candidate_density']
    fig, ax = plt.subplots(figsize=FIGURE_SIZES['candidate_density'])
    x_offsets = {'coverage_greedy': -3.0, 'safe_coverage_greedy': 0.0, 'set_cover_cw_tour': 3.0}
    for method in ('coverage_greedy', 'safe_coverage_greedy', 'set_cover_cw_tour'):
        method_rows = [row for row in rows if row['method'] == method]
        method_rows.sort(key=lambda row: float(row['candidate_count']))
        x_values = [float(row['candidate_count']) + x_offsets[method] for row in method_rows]
        y_values = [float(row['final_inspectable_coverage_ratio']) for row in method_rows]
        ax.plot(
            x_values,
            y_values,
            color=METHOD_COLORS[method],
            linewidth=1.7 if method == 'set_cover_cw_tour' else 1.25,
            linestyle='--' if method == 'coverage_greedy' else '-',
            label=METHOD_LABELS_SHORT[method],
        )
        for row, x_value, y_value in zip(method_rows, x_values, y_values):
            ax.scatter(
                x_value,
                y_value,
                s=70 if method == 'set_cover_cw_tour' else 48,
                marker='X' if not bool(row['feasible']) else ('*' if method == 'set_cover_cw_tour' else 'o'),
                color=METHOD_COLORS[method],
                edgecolor='white',
                linewidth=0.55,
                zorder=5,
            )
            if method == 'set_cover_cw_tour':
                if float(row['candidate_count']) == 120.0:
                    annotation = (8, -14, 'left', 'top')
                elif float(row['candidate_count']) == 357.0:
                    annotation = (-4, 9, 'right', 'bottom')
                else:
                    annotation = (0, -14, 'center', 'top')
                dx, dy, ha, va = annotation
                ax.annotate(
                    rf"$\Delta v={float(row['total_delta_v']):.1f}$, "
                    rf"$d_{{\min}}={float(row['min_clearance']):.2f}$ m",
                    (x_value, y_value),
                    xytext=(dx, dy),
                    textcoords='offset points',
                    ha=ha,
                    va=va,
                    fontsize=6.2,
                    color=METHOD_COLORS[method],
                )
    ax.axhline(0.98, color='#555555', linestyle=':', linewidth=0.9)
    ax.text(365, 0.9792, '98% target', ha='right', va='top', fontsize=6.5, color='#444444')
    ax.set_xlabel('Available camera candidates')
    ax.set_ylabel('Final inspectable coverage')
    ax.set_xticks([120, 180, 357])
    ax.set_xticklabels(['120\n(stride 3)', '180\n(stride 2)', '357\n(stride 1)'])
    ax.set_xlim(102, 375)
    ax.set_ylim(0.976, 0.997)
    ax.grid(True, axis='y', color='#E4E7EA', linewidth=0.6)
    handles, labels = ax.get_legend_handles_labels()
    order = [2, 1, 0]
    ax.legend(
        [handles[index] for index in order],
        [labels[index] for index in order],
        loc='lower center',
        ncol=3,
        fontsize=6.7,
        frameon=False,
    )
    ax.text(
        0.02,
        0.97,
        'X markers are infeasible despite high inspectable coverage.',
        transform=ax.transAxes,
        ha='left',
        va='top',
        fontsize=6.4,
        color='#555555',
    )
    save_all(fig, path)


def plot_initial_condition_robustness(path: Path) -> None:
    """Plot effort ordering across the three archived initial states."""
    rows = [row for row in load_validation_rows(VALIDATION_PATH) if row['study'] == 'initial_condition']
    fig, ax = plt.subplots(figsize=FIGURE_SIZES['initial_condition'])
    case_order = ('ic0', 'ic1', 'ic2')
    x_values = list(range(len(case_order)))
    safe_by_case = {
        str(row['case_id']): row
        for row in rows
        if row['method'] == 'safe_coverage_greedy'
    }
    for method in ('set_cover_cw_tour', 'safe_coverage_greedy', 'coverage_greedy'):
        row_by_case = {
            str(row['case_id']): row
            for row in rows
            if row['method'] == method
        }
        method_rows = [row_by_case[case_id] for case_id in case_order]
        delta_v = [float(row['total_delta_v']) for row in method_rows]
        ax.plot(
            x_values,
            delta_v,
            color=METHOD_COLORS[method],
            linewidth=1.8 if method == 'set_cover_cw_tour' else 1.3,
            linestyle='--' if method == 'coverage_greedy' else '-',
            label=METHOD_LABELS_SHORT[method],
        )
        for x_value, value, row in zip(x_values, delta_v, method_rows):
            ax.scatter(
                x_value,
                value,
                s=72 if method == 'set_cover_cw_tour' else 50,
                marker='X' if not bool(row['feasible']) else ('*' if method == 'set_cover_cw_tour' else 'o'),
                color=METHOD_COLORS[method],
                edgecolor='white',
                linewidth=0.55,
                zorder=5,
            )
            if method == 'set_cover_cw_tour':
                safe_delta_v = float(safe_by_case[str(row['case_id'])]['total_delta_v'])
                reduction = 100.0 * (1.0 - value / safe_delta_v)
                dx = 6 if x_value == 0 else (-6 if x_value == 2 else 0)
                ha = 'left' if x_value == 0 else ('right' if x_value == 2 else 'center')
                ax.annotate(
                    f'{reduction:.1f}% less than safe\n'
                    rf"$d_{{\min}}={float(row['min_clearance']):.2f}$ m",
                    (x_value, value),
                    xytext=(dx, 8),
                    textcoords='offset points',
                    ha=ha,
                    va='bottom',
                    fontsize=5.7,
                    color=METHOD_COLORS[method],
                )
    ax.set_xlabel(r'Initial LVLH position $\mathbf{r}_0$ (m); $\mathbf{v}_0=\mathbf{0}$', fontsize=7.1)
    ax.set_ylabel(r'Total $\Delta v$ (m s$^{-1}$)', fontsize=7.1)
    ax.set_xticks(x_values)
    ax.set_xticklabels([
        'IC-0\n[0, -35, 10]',
        'IC-1\n[18, -42, 12]',
        'IC-2\n[-20, -32, 8]',
    ])
    ax.set_xlim(-0.18, 2.18)
    ax.set_ylim(16.0, 54.0)
    ax.tick_params(labelsize=6.2)
    ax.grid(True, axis='y', color='#E4E7EA', linewidth=0.6)
    ax.legend(loc='center right', fontsize=6.0, frameon=False)
    ax.text(
        0.02,
        0.96,
        'All methods reach 98.33% coverage; X marks infeasible coverage greedy.',
        transform=ax.transAxes,
        ha='left',
        va='top',
        fontsize=5.8,
        color='#444444',
    )
    save_all(fig, path)


def plot_transfer_duration_sensitivity(path: Path) -> None:
    """Plot the input-feasibility boundary and achieved coverage versus duration."""
    rows = [row for row in load_validation_rows(VALIDATION_PATH) if row['study'] == 'transfer_duration']
    fig, ax = plt.subplots(figsize=FIGURE_SIZES['transfer_duration'])
    for method in ('set_cover_cw_tour', 'safe_coverage_greedy', 'coverage_greedy'):
        method_rows = [row for row in rows if row['method'] == method]
        method_rows.sort(key=lambda row: float(row['transfer_duration']))
        durations = [float(row['transfer_duration']) for row in method_rows]
        peaks = [float(row['peak_requested_input']) for row in method_rows]
        ax.plot(
            durations,
            peaks,
            color=METHOD_COLORS[method],
            linewidth=1.8 if method == 'set_cover_cw_tour' else 1.3,
            linestyle='--' if method == 'coverage_greedy' else '-',
            label=METHOD_LABELS_SHORT[method],
        )
        for duration, peak, row in zip(durations, peaks, method_rows):
            ax.scatter(
                duration,
                peak,
                s=72 if method == 'set_cover_cw_tour' else 50,
                marker='X' if not bool(row['feasible']) else ('*' if method == 'set_cover_cw_tour' else 'o'),
                color=METHOD_COLORS[method],
                edgecolor='white',
                linewidth=0.55,
                zorder=5,
            )
            if method == 'set_cover_cw_tour':
                ax.annotate(
                    f"{100.0 * float(row['final_inspectable_coverage_ratio']):.1f}% cov.",
                    (duration, peak),
                    xytext=(0, -13 if duration != 70 else 9),
                    textcoords='offset points',
                    ha='center',
                    va='top' if duration != 70 else 'bottom',
                    fontsize=6.3,
                    color=METHOD_COLORS[method],
                )
    ax.axhspan(0.06, 0.15, color='#F7E2E0', alpha=0.55, zorder=0)
    ax.axhline(0.06, color='#555555', linestyle=':', linewidth=1.0)
    ax.text(119.5, 0.0615, r'input limit $u_{\max}=0.060$ m s$^{-2}$', ha='right', va='bottom', fontsize=6.5, color='#444444')
    ax.set_xlabel('Transfer-segment duration (s)')
    ax.set_ylabel(r'Peak requested input (m s$^{-2}$)')
    ax.set_xticks([70, 90, 120])
    ax.set_xlim(66, 124)
    ax.set_ylim(0.032, 0.145)
    ax.grid(True, axis='y', color='#E4E7EA', linewidth=0.6)
    ax.legend(loc='center right', fontsize=6.8, frameon=False)
    ax.text(
        0.98,
        0.96,
        'X denotes any mission-constraint violation, not only input saturation.',
        transform=ax.transAxes,
        ha='right',
        va='top',
        fontsize=6.4,
        color='#555555',
    )
    save_all(fig, path)


def plot_ablation_comparison(path: Path) -> None:
    """Plot coverage-effort-feasibility changes after component removal."""
    rows = [row for row in load_validation_rows(VALIDATION_PATH) if row['study'] == 'ablation']
    labels = {
        'set_cover_cw_tour': 'Full SOOA planner',
        'abl_no_transfer_cost': 'No transfer cost',
        'abl_no_clearance_filter': 'No clearance filter',
        'abl_no_input_check': 'No input check',
        'abl_unweighted_coverage': 'Unweighted coverage',
    }
    colors = {
        'set_cover_cw_tour': METHOD_COLORS['set_cover_cw_tour'],
        'abl_no_transfer_cost': '#7884B4',
        'abl_no_clearance_filter': '#7BAA5B',
        'abl_no_input_check': '#B64342',
        'abl_unweighted_coverage': '#767676',
    }
    offsets = {
        'set_cover_cw_tour': (0, 12, 'center', 'bottom'),
        'abl_no_transfer_cost': (5, -4, 'left', 'center'),
        'abl_no_clearance_filter': (5, 2, 'left', 'center'),
        'abl_no_input_check': (-8, 8, 'right', 'bottom'),
        'abl_unweighted_coverage': (-3, -14, 'right', 'top'),
    }
    fig, ax = plt.subplots(figsize=FIGURE_SIZES['ablation'])
    for row in rows:
        method = str(row['method'])
        delta_v = float(row['total_delta_v'])
        coverage = float(row['final_inspectable_coverage_ratio'])
        feasible = bool(row['feasible'])
        ax.scatter(
            delta_v,
            coverage,
            s=92 if method == 'set_cover_cw_tour' else 62,
            marker='*' if method == 'set_cover_cw_tour' else ('X' if not feasible else 'o'),
            color=colors[method],
            edgecolor='#222222',
            linewidth=0.55,
            zorder=4,
        )
        dx, dy, ha, va = offsets[method]
        ax.annotate(
            labels[method],
            (delta_v, coverage),
            xytext=(dx, dy),
            textcoords='offset points',
            ha=ha,
            va=va,
            fontsize=6.6,
            color=colors[method],
            fontweight='bold' if method == 'set_cover_cw_tour' else 'normal',
        )
    ax.axhline(0.98, color='#555555', linestyle=':', linewidth=0.9)
    ax.text(24.0, 0.978, '98% target', ha='right', va='top', fontsize=6.5, color='#444444')
    ax.annotate(
        r'peak input $0.0693>0.060$ m s$^{-2}$',
        xy=(22.1327, 0.9889),
        xytext=(-74, -43),
        textcoords='offset points',
        fontsize=6.4,
        color=colors['abl_no_input_check'],
        arrowprops={'arrowstyle': '-', 'color': colors['abl_no_input_check'], 'linewidth': 0.7},
    )
    ax.set_xlabel(r'Total $\Delta v$ (m s$^{-1}$)')
    ax.set_ylabel('Final inspectable coverage')
    ax.set_xlim(16.4, 24.2)
    ax.set_ylim(0.885, 1.002)
    ax.grid(True, color='#E4E7EA', linewidth=0.6)
    ax.text(
        0.02,
        0.05,
        'Removing clearance filtering changes the selected set and stops at 90% coverage.',
        transform=ax.transAxes,
        ha='left',
        va='bottom',
        fontsize=6.4,
        color='#555555',
    )
    save_all(fig, path)


def _plot_method_trajectory_panel(
    path: Path,
    method: str,
    data: FigureData,
) -> None:
    """Shared renderer for one compact LaTeX trajectory panel."""
    fig = plt.figure(figsize=FIGURE_SIZES['method_panel'])
    ax = fig.add_axes((-0.12, -0.13, 1.24, 1.24), projection='3d')
    draw_mesh_method_context(ax, data.comparison_segments, data.comparison_faces)
    _draw_method_trajectory(
        ax,
        method,
        data.trajectories.get(method, []),
        data.viewpoints.get(method, []),
        start_size=22,
        end_size=28,
        viewpoint_size=16,
    )
    style_method_comparison_axis(ax, zoom=1.26)
    set_equal_axes(ax, [], data.comparison_points)
    save_all(fig, path, tight=False, bbox_inches='tight')


def _draw_method_trajectory(
    ax,
    method: str,
    trajectory: list[Point3],
    viewpoints: list[Viewpoint],
    *,
    start_size: float,
    end_size: float,
    viewpoint_size: float,
) -> None:
    """Draw one method trajectory and its selected viewpoints on an axes."""
    if trajectory:
        xs, ys, zs = unzip_points(trajectory)
        ax.plot(
            xs,
            ys,
            zs,
            color=METHOD_COLORS.get(method, '#333333'),
            linewidth=1.5,
            alpha=0.98,
            zorder=9,
        )
        ax.scatter(
            [xs[0]],
            [ys[0]],
            [zs[0]],
            s=start_size,
            c='#2E9E44',
            marker='o',
            depthshade=False,
            zorder=10,
        )
        ax.scatter(
            [xs[-1]],
            [ys[-1]],
            [zs[-1]],
            s=end_size,
            c='#E53935',
            marker='X',
            depthshade=False,
            zorder=10,
        )
    if viewpoints:
        ax.scatter(
            [item['x'] for item in viewpoints],
            [item['y'] for item in viewpoints],
            [item['z'] for item in viewpoints],
            c=[item['coverage'] for item in viewpoints],
            cmap='viridis',
            s=viewpoint_size,
            marker='^',
            edgecolors='#222222',
            linewidths=0.18,
            depthshade=False,
            zorder=9,
        )


def draw_mesh_method_context(
    ax,
    segments: list[MeshSegment],
    faces: list[MeshFace],
) -> None:
    """Draw the ISS mesh with visibility tuned for compact trajectory panels."""
    if faces:
        surface = Poly3DCollection(
            faces,
            facecolors='#C9D0D8',
            edgecolors='none',
            alpha=0.40,
            zorder=0,
        )
        ax.add_collection3d(surface)
    if segments:
        collection = Line3DCollection(
            segments,
            colors='#48515B',
            linewidths=0.10,
            alpha=0.52,
            zorder=1,
        )
        ax.add_collection3d(collection)


def _draw_coverage_effort_summary(ax, method_rows: list[MethodRow]) -> None:
    """Plot final coverage, effort, action count, and feasibility."""
    label_offsets = {
        'set_cover_cw_tour': (-4, 6, 'right', 'bottom'),
        'fuel_greedy': (0, -7, 'center', 'top'),
        'distance_greedy': (0, 6, 'center', 'bottom'),
        'proposed_safe_cw_nbv': (5, -2, 'left', 'center'),
        'safe_coverage_greedy': (-4, 6, 'right', 'bottom'),
        'coverage_greedy': (4, -7, 'left', 'top'),
        'random_safe': (-3, 6, 'right', 'bottom'),
    }
    for row in method_rows:
        method = str(row['method'])
        delta_v = float(row['total_delta_v'])
        coverage = float(row['final_inspectable_coverage_ratio'])
        feasible = bool(row['feasible'])
        is_proposed = method == 'set_cover_cw_tour'
        action_count = float(row['selected_viewpoint_count'])
        ax.scatter(
            delta_v,
            coverage,
            s=(78.0 + 2.0 * action_count) if is_proposed else (38.0 + 1.6 * action_count),
            marker='*' if is_proposed else ('X' if not feasible else 'o'),
            color=METHOD_COLORS.get(method, '#767676'),
            edgecolor='#222222',
            linewidth=0.55,
            alpha=0.95,
            zorder=4 if is_proposed else 3,
        )
        label = METHOD_LABELS_SHORT.get(method, method)
        offset_x, offset_y, ha, va = label_offsets.get(
            method,
            (8, 8, 'left', 'bottom'),
        )
        ax.annotate(
            label,
            xy=(delta_v, coverage),
            xytext=(offset_x, offset_y),
            textcoords='offset points',
            fontsize=6.2,
            color=METHOD_COLORS.get(method, '#333333'),
            ha=ha,
            va=va,
            fontweight='bold' if is_proposed else 'normal',
            zorder=5,
        )
    ax.axhline(0.98, color='#555555', linewidth=0.85, linestyle=':', alpha=0.8)
    ax.text(
        18.8,
        0.9805,
        '98% target',
        ha='left',
        va='bottom',
        fontsize=5.8,
        color='#272727',
    )
    ax.set_xlabel(r'Total $\Delta v$ (m s$^{-1}$)', fontsize=8.0, labelpad=2.0)
    ax.set_ylabel('Inspectable coverage', fontsize=8.0, labelpad=3.0)
    ax.tick_params(axis='both', labelsize=7.2, length=3.0, width=0.8)
    ax.grid(True, color='#E4E7EA', linewidth=0.55)
    ax.set_axisbelow(True)
    ax.set_xlim(18.0, 66.0)
    ax.set_ylim(0.962, 1.002)
    symbol_legend = [
        Line2D([0], [0], marker='o', color='none', markerfacecolor='#8B929A', markeredgecolor='#222222', markersize=6.0, label='Feasible'),
        Line2D([0], [0], marker='X', color='none', markerfacecolor='#B64342', markeredgecolor='#222222', markersize=6.0, label='Infeasible'),
    ]
    ax.legend(
        handles=symbol_legend,
        loc='lower right',
        frameon=False,
        fontsize=6.4,
        handletextpad=0.4,
        borderaxespad=0.4,
    )
    ax.text(
        0.985,
        0.965,
        'Marker area scales with selected SOOA count.',
        transform=ax.transAxes,
        ha='right',
        va='top',
        fontsize=6.0,
        color='#555555',
    )
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)


def _panel_label(ax, letter: str, title: str) -> None:
    """Apply a consistent panel letter and short evidence title."""
    text_method = ax.text2D if hasattr(ax, 'text2D') else ax.text
    text_method(
        -0.12,
        1.055,
        letter,
        transform=ax.transAxes,
        fontsize=9.0,
        fontweight='bold',
        ha='left',
        va='bottom',
    )
    ax.set_title(title, loc='left', fontsize=7.7, fontweight='bold', pad=7.0)


def _stride_sequence(items: list, stride: int, max_items: int) -> list:
    """Downsample a sequence for lightweight repeated rendering."""
    if not items:
        return []
    sampled = items[::max(1, stride)]
    return sampled[:max_items]


# ---------------------------------------------------------------------------
# Camera-model figures
# ---------------------------------------------------------------------------

def plot_camera_model_frusta(
    path: Path,
    data: FigureData,
) -> None:
    """Overlay reconstructed camera frusta on the proposed ISS-mesh tour."""
    trajectory = data.trajectories['set_cover_cw_tour']
    viewpoints = data.viewpoints['set_cover_cw_tour']
    if not trajectory or not viewpoints:
        return
    fig = plt.figure(figsize=FIGURE_SIZES['camera_frusta'])
    ax = fig.add_axes((0.01, 0.02, 0.98, 0.96), projection='3d')
    draw_mesh_method_context(ax, data.comparison_segments, data.comparison_faces)

    xs, ys, zs = unzip_points(trajectory)
    ax.plot(
        xs,
        ys,
        zs,
        color=NMI_PASTEL['baseline_dark'],
        linewidth=1.35,
        alpha=0.92,
        zorder=7,
    )
    ax.scatter(
        [xs[0]],
        [ys[0]],
        [zs[0]],
        s=64,
        c=NMI_PASTEL['delta_up'],
        marker='o',
        depthshade=False,
        zorder=9,
    )
    ax.scatter(
        [xs[-1]],
        [ys[-1]],
        [zs[-1]],
        s=78,
        c=NMI_PASTEL['delta_down'],
        marker='X',
        depthshade=False,
        zorder=9,
    )

    sample_indices = [0, len(viewpoints) // 2, len(viewpoints) - 1]
    sample_indices = sorted(set(sample_indices))
    selected = [viewpoints[index] for index in sample_indices]
    frustum_records = []
    representative_origins = set()
    for idx, row in enumerate(selected):
        origin = (row['x'], row['y'], row['z'])
        boresight = _unit((row['boresight_x'], row['boresight_y'], row['boresight_z']))
        frustum = _fov_corners(origin, boresight, 70.0, 50.0, 18.0)
        color = REPRESENTATIVE_VIEW_COLORS[idx % len(REPRESENTATIVE_VIEW_COLORS)]
        label = REPRESENTATIVE_VIEW_LABELS[idx % len(REPRESENTATIVE_VIEW_LABELS)]
        boresight_end = _add(origin, _scale(boresight, 23.0))
        representative_origins.add(tuple(round(value, 6) for value in origin))
        frustum_records.append((origin, boresight_end, frustum, color, label))

    non_representative = [
        row for row in viewpoints
        if tuple(round(row[key], 6) for key in ('x', 'y', 'z')) not in representative_origins
    ]
    if non_representative:
        ax.scatter(
            [item['x'] for item in non_representative],
            [item['y'] for item in non_representative],
            [item['z'] for item in non_representative],
            s=28,
            marker='^',
            color='#2F2448',
            alpha=0.52,
            edgecolors='#222222',
            linewidths=0.18,
            depthshade=False,
            zorder=8,
        )

    for origin, boresight_end, frustum, color, label in frustum_records:
        frustum_surface = Poly3DCollection(
            [frustum],
            facecolors=color,
            edgecolors='none',
            alpha=0.075,
            zorder=5,
        )
        frustum_surface.set_clip_on(False)
        ax.add_collection3d(frustum_surface)
        ax.scatter(
            [origin[0]],
            [origin[1]],
            [origin[2]],
            s=72,
            marker='^',
            color=color,
            edgecolors='#222222',
            linewidths=0.45,
            depthshade=False,
            zorder=10,
            clip_on=False,
        )
        boresight_line = ax.plot(
            [origin[0], boresight_end[0]],
            [origin[1], boresight_end[1]],
            [origin[2], boresight_end[2]],
            color=color,
            linewidth=1.8,
            alpha=0.95,
            zorder=8,
        )
        for artist in boresight_line:
            artist.set_clip_on(False)
        for corner in frustum:
            corner_line = ax.plot(
                [origin[0], corner[0]],
                [origin[1], corner[1]],
                [origin[2], corner[2]],
                color=color,
                linewidth=1.0,
                alpha=0.76,
                zorder=6,
            )
            for artist in corner_line:
                artist.set_clip_on(False)
        for start, end in zip(frustum, frustum[1:] + frustum[:1]):
            edge_line = ax.plot(
                [start[0], end[0]],
                [start[1], end[1]],
                [start[2], end[2]],
                color=color,
                linewidth=1.25,
                alpha=0.86,
                zorder=6,
            )
            for artist in edge_line:
                artist.set_clip_on(False)
        label_anchor = _add(origin, (2.4, 2.4, 3.8))
        ax.text(
            label_anchor[0],
            label_anchor[1],
            label_anchor[2],
            label,
            color=color,
            fontsize=7.2,
            fontweight='bold',
            zorder=12,
            clip_on=False,
        )

    style_camera_overlay_axis(ax, zoom=1.24)
    set_equal_axes(ax, data.comparison_segments, trajectory)
    ax.text2D(
        0.03,
        0.94,
        r'Reconstructed $70^\circ\times50^\circ$ camera field of view',
        transform=ax.transAxes,
        fontsize=8.0,
        color='#243247',
        fontweight='bold',
    )
    ax.text2D(
        0.03,
        0.05,
        'Early, middle, and final dwell poses use the archived boresight stream.',
        transform=ax.transAxes,
        fontsize=7.0,
        color='#555555',
    )
    save_all(fig, path, tight=False, bbox_inches='tight')


def plot_camera_model_coverage(
    path: Path,
    data: FigureData,
) -> None:
    """Plot incremental and cumulative coverage for every selected SOOA."""
    viewpoints = data.viewpoints['set_cover_cw_tour']
    if not viewpoints:
        return
    fig, ax = plt.subplots(figsize=FIGURE_SIZES['camera_coverage'])
    sequences = [int(item['sequence']) + 1 for item in viewpoints]
    cumulative = [100.0 * float(item['coverage']) for item in viewpoints]
    increments = [cumulative[0]] + [max(0.0, cumulative[index] - cumulative[index - 1]) for index in range(1, len(cumulative))]
    sample_indices = [0, len(viewpoints) // 2, len(viewpoints) - 1]
    sample_indices = sorted(set(sample_indices))
    bar_colors = ['#C8D3E7'] * len(viewpoints)
    for color, index in zip(REPRESENTATIVE_VIEW_COLORS, sample_indices):
        bar_colors[index] = color
    bars = ax.bar(
        sequences,
        increments,
        color=bar_colors,
        edgecolor='white',
        linewidth=0.45,
        width=0.78,
    )
    selected_sequences = [sequences[index] for index in sample_indices]
    selected_increments = [increments[index] for index in sample_indices]
    ax.scatter(
        selected_sequences,
        selected_increments,
        s=24,
        color=REPRESENTATIVE_VIEW_COLORS,
        edgecolor='#222222',
        linewidth=0.35,
        zorder=5,
    )
    label_offsets = [(0.35, 0.6, 'left'), (0.35, 0.6, 'left'), (-0.35, 0.6, 'right')]
    for label, x_value, y_value, (dx, dy, ha), color in zip(
        REPRESENTATIVE_VIEW_LABELS,
        selected_sequences,
        selected_increments,
        label_offsets,
        REPRESENTATIVE_VIEW_COLORS,
    ):
        ax.text(
            x_value + dx,
            y_value + dy,
            label,
            fontsize=7.0,
            color=color,
            ha=ha,
            va='bottom',
            fontweight='bold',
        )
    cumulative_ax = ax.twinx()
    cumulative_line, = cumulative_ax.step(
        sequences,
        cumulative,
        where='mid',
        color=METHOD_COLORS['set_cover_cw_tour'],
        linewidth=2.0,
        label='Cumulative coverage',
        zorder=6,
    )
    cumulative_ax.scatter(
        selected_sequences,
        [cumulative[index] for index in sample_indices],
        s=30,
        color=REPRESENTATIVE_VIEW_COLORS,
        edgecolor='white',
        linewidth=0.45,
        zorder=7,
    )
    cumulative_ax.axhline(70.0, color='#9DA3AA', linestyle='--', linewidth=0.8)
    cumulative_ax.axhline(98.0, color='#555555', linestyle=':', linewidth=0.9)
    cumulative_ax.text(18.7, 69.0, '70% success', ha='right', va='top', fontsize=6.2, color='#666666')
    cumulative_ax.text(18.7, 97.0, '98% target', ha='right', va='top', fontsize=6.2, color='#444444')
    cumulative_ax.annotate(
        f'{cumulative[-1]:.1f}% final',
        xy=(sequences[-1], cumulative[-1]),
        xytext=(-8, -1),
        textcoords='offset points',
        ha='right',
        va='center',
        fontsize=7.2,
        color=METHOD_COLORS['set_cover_cw_tour'],
        fontweight='bold',
    )
    ax.set_xlabel('Selected view index', fontsize=7.5)
    ax.set_ylabel('Incremental coverage (percentage points)', fontsize=7.5)
    cumulative_ax.set_ylabel('Cumulative inspectable coverage (%)', fontsize=7.5, color=METHOD_COLORS['set_cover_cw_tour'])
    ax.tick_params(axis='both', labelsize=7.0, length=3.0, width=0.8)
    cumulative_ax.tick_params(axis='y', labelsize=7.0, colors=METHOD_COLORS['set_cover_cw_tour'], length=3.0, width=0.8)
    ax.grid(True, axis='y', color='#E1E1E1', linewidth=0.55)
    ax.set_axisbelow(True)
    ax.set_xlim(0.2, max(sequences) + 0.8)
    ax.set_ylim(0.0, max(increments) * 1.18)
    cumulative_ax.set_ylim(0.0, 102.0)
    ax.set_xticks([1, 5, 10, 15, 20, max(sequences)])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    cumulative_ax.spines['top'].set_visible(False)
    cumulative_ax.spines['right'].set_color(METHOD_COLORS['set_cover_cw_tour'])
    ax.legend(
        handles=[bars, cumulative_line],
        labels=['Incremental contribution', 'Cumulative coverage'],
        loc='center right',
        bbox_to_anchor=(0.98, 0.42),
        fontsize=6.6,
        frameon=False,
    )
    fig.subplots_adjust(left=0.13, right=0.87, bottom=0.16, top=0.98)
    save_all(fig, path, tight=False)


def plot_camera_verification_summary(path: Path, data: FigureData) -> None:
    """Combine camera geometry and per-view coverage evidence in one figure."""
    trajectory = data.trajectories['set_cover_cw_tour']
    viewpoints = data.viewpoints['set_cover_cw_tour']
    if not trajectory or not viewpoints:
        return

    fig = plt.figure(figsize=FIGURE_SIZES['camera_summary'])
    grid = fig.add_gridspec(
        1,
        2,
        width_ratios=(1.42, 1.0),
        left=0.015,
        right=0.99,
        bottom=0.18,
        top=0.94,
        wspace=0.28,
    )
    geometry_ax = fig.add_subplot(grid[0, 0], projection='3d')
    draw_mesh_method_context(
        geometry_ax,
        data.comparison_segments,
        data.comparison_faces,
    )
    xs, ys, zs = unzip_points(trajectory)
    geometry_ax.plot(
        xs,
        ys,
        zs,
        color=METHOD_COLORS['set_cover_cw_tour'],
        linewidth=1.25,
        alpha=0.86,
        zorder=7,
    )

    sample_indices = sorted(set((0, len(viewpoints) // 2, len(viewpoints) - 1)))
    selected = [viewpoints[index] for index in sample_indices]
    for index, row in enumerate(selected):
        origin = (row['x'], row['y'], row['z'])
        boresight = _unit((
            row['boresight_x'],
            row['boresight_y'],
            row['boresight_z'],
        ))
        frustum = _fov_corners(origin, boresight, 70.0, 50.0, 18.0)
        color = REPRESENTATIVE_VIEW_COLORS[index]
        footprint = Poly3DCollection(
            [frustum],
            facecolors=color,
            edgecolors=color,
            linewidths=0.45,
            alpha=0.10,
            zorder=5,
        )
        geometry_ax.add_collection3d(footprint)
        geometry_ax.scatter(
            [origin[0]],
            [origin[1]],
            [origin[2]],
            s=43,
            marker='^',
            color=color,
            edgecolors='#222222',
            linewidths=0.4,
            depthshade=False,
            zorder=9,
        )
        boresight_end = _add(origin, _scale(boresight, 23.0))
        geometry_ax.plot(
            [origin[0], boresight_end[0]],
            [origin[1], boresight_end[1]],
            [origin[2], boresight_end[2]],
            color=color,
            linewidth=1.35,
            zorder=7,
        )
        for corner in frustum:
            geometry_ax.plot(
                [origin[0], corner[0]],
                [origin[1], corner[1]],
                [origin[2], corner[2]],
                color=color,
                linewidth=0.72,
                alpha=0.78,
                zorder=6,
            )
        for start, end in zip(frustum, frustum[1:] + frustum[:1]):
            geometry_ax.plot(
                [start[0], end[0]],
                [start[1], end[1]],
                [start[2], end[2]],
                color=color,
                linewidth=0.85,
                alpha=0.86,
                zorder=6,
            )
        label_anchor = _add(origin, (2.2, 1.8, 3.2))
        geometry_ax.text(
            label_anchor[0],
            label_anchor[1],
            label_anchor[2],
            REPRESENTATIVE_VIEW_LABELS[index],
            color=color,
            fontsize=6.1,
            fontweight='bold',
            zorder=10,
        )
    style_camera_overlay_axis(geometry_ax, zoom=1.15)
    set_equal_axes(geometry_ax, data.comparison_segments, trajectory)
    geometry_ax.text2D(
        0.04,
        0.04,
        r'$70^\circ \times 50^\circ$ camera FOV',
        transform=geometry_ax.transAxes,
        fontsize=6.3,
        color='#243247',
    )
    _panel_label(geometry_ax, 'a', 'Representative camera frusta')

    coverage_ax = fig.add_subplot(grid[0, 1])
    sequences = [int(item['sequence']) + 1 for item in viewpoints]
    cumulative = [float(item['coverage']) for item in viewpoints]
    increments = [
        cumulative[0],
        *[
            max(0.0, cumulative[index] - cumulative[index - 1])
            for index in range(1, len(cumulative))
        ],
    ]
    bar_colors = ['#C8D3E7'] * len(viewpoints)
    for color, index in zip(REPRESENTATIVE_VIEW_COLORS, sample_indices):
        bar_colors[index] = color
    coverage_ax.bar(
        sequences,
        increments,
        width=0.78,
        color=bar_colors,
        edgecolor='white',
        linewidth=0.4,
    )
    for color, index, label in zip(
        REPRESENTATIVE_VIEW_COLORS,
        sample_indices,
        REPRESENTATIVE_VIEW_LABELS,
    ):
        coverage_ax.scatter(
            sequences[index],
            increments[index],
            s=24,
            color=color,
            edgecolor='#222222',
            linewidth=0.35,
            zorder=4,
        )
        coverage_ax.annotate(
            label,
            (sequences[index], increments[index]),
            xytext=(0, 6),
            textcoords='offset points',
            ha='center',
            va='bottom',
            color=color,
            fontsize=6.0,
            fontweight='bold',
        )
    coverage_ax.text(
        0.98,
        0.96,
        f'{cumulative[-1] * 100:.1f}% final coverage',
        transform=coverage_ax.transAxes,
        ha='right',
        va='top',
        fontsize=6.4,
        color='#243247',
        fontweight='bold',
    )
    coverage_ax.set_xlabel('Selected SOOA index', fontsize=7.5)
    coverage_ax.set_ylabel('Incremental coverage', fontsize=7.5)
    coverage_ax.set_xlim(0.2, max(sequences) + 0.8)
    coverage_ax.set_ylim(0.0, max(increments) * 1.22)
    coverage_ax.set_xticks([1, 5, 10, 15, 20, max(sequences)])
    coverage_ax.tick_params(labelsize=7.0)
    coverage_ax.grid(True, axis='y', color='#E4E7EA', linewidth=0.55)
    coverage_ax.set_axisbelow(True)
    _panel_label(coverage_ax, 'b', 'Coverage contributed by each view')

    save_all(fig, path, tight=False, bbox_inches='tight')


# ---------------------------------------------------------------------------
# Shared style, geometry, and export helpers
# ---------------------------------------------------------------------------

def style_camera_overlay_axis(ax, zoom: float = 1.10) -> None:
    """Use the proposed-tour viewpoint without visible 3D axes."""
    _set_orthographic_view(ax, zoom)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_zlabel('')
    ax.grid(False)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        try:
            axis.line.set_color((1.0, 1.0, 1.0, 0.0))
            axis.line.set_linewidth(0.0)
        except Exception:
            pass
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor((1.0, 1.0, 1.0, 0.0))
        pane.set_edgecolor((1.0, 1.0, 1.0, 0.0))


def style_method_comparison_axis(ax, zoom: float = 1.0) -> None:
    """Use the main trajectory figure's 3D grid grammar in compact panels."""
    _set_orthographic_view(ax, zoom)
    ax.set_xticks([-40, 0, 40])
    ax.set_yticks([-40, 0, 40])
    ax.set_zticks([-40, 0, 40])
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_zticklabels([])
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_zlabel('')
    ax.tick_params(axis='both', which='major', length=0, pad=-5)
    ax.grid(True, color='#D3D7DC', linewidth=0.26)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        try:
            axis.line.set_color('#CFD4DA')
            axis.line.set_linewidth(0.38)
        except Exception:
            pass
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor((1.0, 1.0, 1.0, 0.0))
        pane.set_edgecolor('#E6E6E6')


def _set_orthographic_view(ax, zoom: float) -> None:
    """Apply the shared manuscript camera angle and equal 3D aspect."""
    ax.view_init(elev=VIEW_ELEVATION, azim=VIEW_AZIMUTH)
    try:
        ax.set_proj_type('ortho')
    except Exception:
        pass
    try:
        ax.set_box_aspect((1.0, 1.0, 1.0), zoom=zoom)
    except Exception:
        try:
            ax.set_box_aspect((1.0, 1.0, 1.0))
        except Exception:
            pass


def draw_mesh(
    ax,
    segments: list[MeshSegment],
    faces: list[MeshFace],
) -> None:
    """Draw the ISS mesh as a dense wireframe with a subtle surface layer."""
    if faces:
        surface = Poly3DCollection(
            faces,
            facecolors='#E3E7EC',
            edgecolors='none',
            alpha=0.16,
            zorder=0,
        )
        ax.add_collection3d(surface)
    collection = Line3DCollection(
        segments,
        colors='#787878',
        linewidths=0.045,
        alpha=0.06,
        zorder=1,
    )
    ax.add_collection3d(collection)
    ax.plot([], [], [], color='#4A4A4A', linewidth=1.2, alpha=0.70, label='ISS mesh')


def style_axis(ax) -> None:
    """Apply journal-friendly 3D axis styling."""
    ax.set_xlabel('Radial x (m)', labelpad=10)
    ax.set_ylabel('Along-track y (m)', labelpad=10)
    ax.set_zlabel('Cross-track z (m)', labelpad=10)
    ax.view_init(elev=VIEW_ELEVATION, azim=VIEW_AZIMUTH)
    ax.grid(True, color='#D9D9D9', linewidth=0.45)
    try:
        ax.set_box_aspect((1.0, 1.0, 1.0))
    except Exception:
        pass
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor((1.0, 1.0, 1.0, 0.0))
        pane.set_edgecolor('#E6E6E6')


def set_equal_axes(
    ax,
    mesh_segments: list[MeshSegment],
    points: list[Point3],
) -> None:
    """Use one equal-scale 3D box containing both mesh and trajectories."""
    all_points = list(points)
    for first, second in mesh_segments:
        all_points.extend((first, second))
    xs, ys, zs = unzip_points(all_points)
    center = (
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0,
        (min(zs) + max(zs)) / 2.0,
    )
    radius = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) * 0.54
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)


def save_all(fig, path: Path, tight: bool = True, bbox_inches: str | None = 'tight') -> None:
    """Save PNG, PDF, and SVG versions of a figure."""
    if tight:
        fig.tight_layout()
    for suffix in EXPORT_FORMATS:
        metadata = None
        if suffix == '.svg':
            metadata = {'Date': None}
        elif suffix == '.pdf':
            metadata = {'CreationDate': None, 'ModDate': None}
        fig.savefig(
            path.with_suffix(suffix),
            dpi=EXPORT_DPI,
            bbox_inches=bbox_inches,
            pad_inches=0.0,
            metadata=metadata,
        )
    plt.close(fig)


def unzip_points(points: list[Point3]) -> tuple[list[float], list[float], list[float]]:
    """Split a list of 3D points into x, y, and z coordinate lists."""
    return (
        [point[0] for point in points],
        [point[1] for point in points],
        [point[2] for point in points],
    )


def _unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    """Normalize a 3-vector."""
    length = math.sqrt(sum(value * value for value in vector))
    if length <= 1.0e-12:
        return (1.0, 0.0, 0.0)
    return tuple(value / length for value in vector)


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _scale(vector: tuple[float, float, float], value: float) -> tuple[float, float, float]:
    return (vector[0] * value, vector[1] * value, vector[2] * value)


def _add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def load_mesh_segments(
    path: Path,
    scale: float,
    max_edges: int,
) -> list[MeshSegment]:
    """Load a downsampled GLB wireframe in the planner's LVLH convention."""
    json_doc, binary = read_glb(path)
    nodes = json_doc.get('nodes', [])
    meshes = json_doc.get('meshes', [])
    if not isinstance(nodes, list) or not isinstance(meshes, list):
        return []

    transforms = node_translations(json_doc)
    primitive_count = sum(
        len(mesh.get('primitives', []))
        for mesh in meshes
        if isinstance(mesh, dict)
    )
    edge_budget = max(1, max_edges // max(1, primitive_count))
    segments: list[MeshSegment] = []

    for node in nodes:
        if not isinstance(node, dict) or 'mesh' not in node:
            continue
        mesh_index = int(node['mesh'])
        if mesh_index >= len(meshes) or not isinstance(meshes[mesh_index], dict):
            continue
        translation = transforms.get(id(node), (0.0, 0.0, 0.0))
        for primitive in meshes[mesh_index].get('primitives', []):
            if not isinstance(primitive, dict) or primitive.get('mode', 4) != 4:
                continue
            attributes = primitive.get('attributes', {})
            if not isinstance(attributes, dict) or 'POSITION' not in attributes:
                continue
            positions = read_accessor_vec3(json_doc, binary, int(attributes['POSITION']))
            indices = read_accessor_indices(json_doc, binary, primitive.get('indices'))
            triangle_count = len(indices) // 3 if indices else len(positions) // 3
            stride = max(1, math.ceil((triangle_count * 3) / edge_budget))
            for start in range(0, triangle_count * 3, 3 * stride):
                if indices:
                    tri = indices[start:start + 3]
                    if len(tri) < 3 or max(tri) >= len(positions):
                        continue
                    raw_points = [positions[index] for index in tri]
                else:
                    raw_points = positions[start:start + 3]
                    if len(raw_points) < 3:
                        continue
                vertices = [transform_iss_vertex(point, translation, scale) for point in raw_points]
                segments.extend(((vertices[0], vertices[1]), (vertices[1], vertices[2]), (vertices[2], vertices[0])))
                if len(segments) >= max_edges:
                    return segments
    return segments


def load_mesh_faces(
    path: Path,
    scale: float,
    max_faces: int,
) -> list[MeshFace]:
    """Load a downsampled GLB triangle surface in the planner's LVLH convention."""
    json_doc, binary = read_glb(path)
    nodes = json_doc.get('nodes', [])
    meshes = json_doc.get('meshes', [])
    if not isinstance(nodes, list) or not isinstance(meshes, list) or max_faces <= 0:
        return []

    transforms = node_translations(json_doc)
    primitive_count = sum(
        len(mesh.get('primitives', []))
        for mesh in meshes
        if isinstance(mesh, dict)
    )
    face_budget = max(1, max_faces // max(1, primitive_count))
    faces: list[MeshFace] = []

    for node in nodes:
        if not isinstance(node, dict) or 'mesh' not in node:
            continue
        mesh_index = int(node['mesh'])
        if mesh_index >= len(meshes) or not isinstance(meshes[mesh_index], dict):
            continue
        translation = transforms.get(id(node), (0.0, 0.0, 0.0))
        for primitive in meshes[mesh_index].get('primitives', []):
            if not isinstance(primitive, dict) or primitive.get('mode', 4) != 4:
                continue
            attributes = primitive.get('attributes', {})
            if not isinstance(attributes, dict) or 'POSITION' not in attributes:
                continue
            positions = read_accessor_vec3(json_doc, binary, int(attributes['POSITION']))
            indices = read_accessor_indices(json_doc, binary, primitive.get('indices'))
            triangle_count = len(indices) // 3 if indices else len(positions) // 3
            stride = max(1, math.ceil(triangle_count / face_budget))
            for triangle_index in range(0, triangle_count, stride):
                start = triangle_index * 3
                if indices:
                    tri = indices[start:start + 3]
                    if len(tri) < 3 or max(tri) >= len(positions):
                        continue
                    raw_points = [positions[index] for index in tri]
                else:
                    raw_points = positions[start:start + 3]
                    if len(raw_points) < 3:
                        continue
                vertices = tuple(
                    transform_iss_vertex(point, translation, scale)
                    for point in raw_points
                )
                faces.append(vertices)
                if len(faces) >= max_faces:
                    return faces
    return faces


def read_glb(path: Path) -> tuple[dict[str, object], bytes]:
    """Read a binary glTF 2.0 file."""
    with path.open('rb') as handle:
        magic, version, _length = struct.unpack('<4sII', handle.read(12))
        if magic != b'glTF' or version != 2:
            raise ValueError(f'expected GLB v2 file: {path}')
        json_length, json_type = struct.unpack('<I4s', handle.read(8))
        if json_type != b'JSON':
            raise ValueError('first GLB chunk must be JSON')
        json_doc = json.loads(handle.read(json_length).decode('utf-8'))
        binary = b''
        while True:
            header = handle.read(8)
            if not header:
                break
            chunk_length, chunk_type = struct.unpack('<I4s', header)
            chunk_data = handle.read(chunk_length)
            if chunk_type == b'BIN\x00':
                binary = chunk_data
                break
    if not binary:
        raise ValueError('GLB does not contain a binary buffer')
    return json_doc, binary


def node_translations(json_doc: dict[str, object]) -> dict[int, tuple[float, float, float]]:
    """Return accumulated node translations keyed by object identity."""
    nodes = json_doc.get('nodes', [])
    if not isinstance(nodes, list):
        return {}
    scene_index = int(json_doc.get('scene', 0))
    scenes = json_doc.get('scenes', [])
    if isinstance(scenes, list) and scene_index < len(scenes) and isinstance(scenes[scene_index], dict):
        roots = [int(item) for item in scenes[scene_index].get('nodes', [])]
    else:
        roots = list(range(len(nodes)))

    transforms: dict[int, tuple[float, float, float]] = {}

    def visit(node_index: int, parent: tuple[float, float, float]) -> None:
        if node_index >= len(nodes) or not isinstance(nodes[node_index], dict):
            return
        node = nodes[node_index]
        local = vector3(node.get('translation', (0.0, 0.0, 0.0)))
        translation = (parent[0] + local[0], parent[1] + local[1], parent[2] + local[2])
        transforms[id(node)] = translation
        for child in node.get('children', []):
            visit(int(child), translation)

    for root in roots:
        visit(root, (0.0, 0.0, 0.0))
    return transforms


def read_accessor_vec3(
    json_doc: dict[str, object],
    binary: bytes,
    accessor_index: int,
) -> list[tuple[float, float, float]]:
    """Read a float VEC3 accessor."""
    accessor, offset, stride = accessor_buffer(json_doc, accessor_index)
    if accessor.get('componentType') != 5126 or accessor.get('type') != 'VEC3':
        return []
    return [
        struct.unpack_from('<fff', binary, offset + index * stride)
        for index in range(int(accessor.get('count', 0)))
    ]


def read_accessor_indices(json_doc: dict[str, object], binary: bytes, accessor_index: object) -> list[int]:
    """Read unsigned triangle indices from a glTF accessor."""
    if accessor_index is None:
        return []
    accessor, offset, stride = accessor_buffer(json_doc, int(accessor_index))
    component_type = int(accessor.get('componentType', 0))
    if component_type == 5123:
        fmt, default_stride = '<H', 2
    elif component_type == 5125:
        fmt, default_stride = '<I', 4
    else:
        return []
    stride = max(stride, default_stride)
    return [
        int(struct.unpack_from(fmt, binary, offset + index * stride)[0])
        for index in range(int(accessor.get('count', 0)))
    ]


def accessor_buffer(
    json_doc: dict[str, object],
    accessor_index: int,
) -> tuple[dict[str, object], int, int]:
    """Return accessor metadata, byte offset, and byte stride."""
    accessors = json_doc['accessors']
    buffer_views = json_doc['bufferViews']
    accessor = accessors[accessor_index]
    buffer_view = buffer_views[int(accessor['bufferView'])]
    offset = int(buffer_view.get('byteOffset', 0)) + int(accessor.get('byteOffset', 0))
    stride = int(buffer_view.get('byteStride', 0))
    if stride <= 0:
        component_size = 2 if int(accessor.get('componentType', 5126)) == 5123 else 4
        component_count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}.get(accessor.get('type', 'SCALAR'), 1)
        stride = component_size * component_count
    return accessor, offset, stride


def transform_iss_vertex(
    point: tuple[float, float, float],
    translation: tuple[float, float, float],
    scale: float,
) -> tuple[float, float, float]:
    """Match the planner and SDF ISS visual pose in LVLH coordinates."""
    translated = (
        point[0] + translation[0],
        point[1] + translation[1],
        point[2] + translation[2],
    )
    return (
        scale * translated[2],
        scale * translated[1],
        -scale * translated[0],
    )


def _camera_basis(boresight: tuple[float, float, float]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Construct a stable camera basis around a boresight vector."""
    world_up = (0.0, 0.0, 1.0)
    if abs(_dot(boresight, world_up)) > 0.95:
        world_up = (0.0, 1.0, 0.0)
    right = _unit(_cross(world_up, boresight))
    up = _unit(_cross(boresight, right))
    return right, up


def _fov_corners(
    origin: tuple[float, float, float],
    boresight: tuple[float, float, float],
    horizontal_fov_deg: float,
    vertical_fov_deg: float,
    fov_range: float,
) -> list[tuple[float, float, float]]:
    """Create a frustum footprint for a camera pose."""
    forward = _unit(boresight)
    right, up = _camera_basis(forward)
    half_width = fov_range * math.tan(math.radians(horizontal_fov_deg / 2.0))
    half_height = fov_range * math.tan(math.radians(vertical_fov_deg / 2.0))
    center = _add(origin, _scale(forward, fov_range))
    offsets = [
        _add(_scale(right, -half_width), _scale(up, -half_height)),
        _add(_scale(right, half_width), _scale(up, -half_height)),
        _add(_scale(right, half_width), _scale(up, half_height)),
        _add(_scale(right, -half_width), _scale(up, half_height)),
    ]
    return [_add(center, offset) for offset in offsets]


def vector3(values: object) -> tuple[float, float, float]:
    """Convert a glTF translation field into a 3-vector."""
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        return (0.0, 0.0, 0.0)
    return (float(values[0]), float(values[1]), float(values[2]))


if __name__ == '__main__':
    main()
