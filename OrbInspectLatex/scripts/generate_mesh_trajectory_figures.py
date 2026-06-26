"""Generate mesh-overlaid trajectory figures for the OrbInspect manuscript."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import struct

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


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

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data' / 'offline_high_coverage_experiment' / 'raw'
MESH_PATH = ROOT / 'data' / 'iss_mesh' / 'ISS_stationary.glb'
FIGURE_DIR = ROOT / 'figures' / 'high_coverage'
ARCHIVED_FIGURE_DIR = ROOT / 'data' / 'offline_high_coverage_experiment' / 'figures'
MESH_SCALE = 1.065
MESH_EDGE_BUDGET = 60000
MESH_FACE_BUDGET = 90000
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
METHOD_PANEL_FILES = {
    'set_cover_cw_tour': 'trajectory_method_proposed',
    'proposed_safe_cw_nbv': 'trajectory_method_cw_nbv',
    'coverage_greedy': 'trajectory_method_coverage',
    'safe_coverage_greedy': 'trajectory_method_safe_coverage',
    'distance_greedy': 'trajectory_method_nearest',
    'fuel_greedy': 'trajectory_method_fuel',
    'random_safe': 'trajectory_method_random',
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


def main() -> None:
    """Regenerate trajectory figures from archived CSVs and the copied ISS GLB."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVED_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    trajectories = load_trajectories(DATA_DIR / 'trajectory.csv')
    viewpoints = load_viewpoints(DATA_DIR / 'viewpoints.csv')
    mesh_segments = load_mesh_segments(MESH_PATH, scale=MESH_SCALE, max_edges=MESH_EDGE_BUDGET)
    mesh_faces = load_mesh_faces(MESH_PATH, scale=MESH_SCALE, max_faces=MESH_FACE_BUDGET)

    plot_proposed_trajectory(
        FIGURE_DIR / 'proposed_trajectory_3d.png',
        mesh_segments,
        mesh_faces,
        trajectories['set_cover_cw_tour'],
        viewpoints['set_cover_cw_tour'],
    )
    plot_camera_model_frusta(
        FIGURE_DIR / 'camera_model_frusta.png',
        mesh_segments,
        mesh_faces,
        trajectories['set_cover_cw_tour'],
        viewpoints['set_cover_cw_tour'],
    )
    plot_camera_model_coverage(
        FIGURE_DIR / 'camera_model_coverage.png',
        viewpoints['set_cover_cw_tour'],
    )
    plot_method_comparison(
        FIGURE_DIR / 'trajectory_method_comparison.png',
        mesh_segments,
        mesh_faces,
        trajectories,
        viewpoints,
    )
    plot_offline_comparison_figures(DATA_DIR, (FIGURE_DIR, ARCHIVED_FIGURE_DIR))


def load_trajectories(path: Path) -> dict[str, list[tuple[float, float, float]]]:
    """Load method-indexed LVLH trajectory samples."""
    by_method: dict[str, list[tuple[float, float, float]]] = {}
    with path.open(newline='') as handle:
        for row in csv.DictReader(handle):
            by_method.setdefault(row['method'], []).append((
                float(row['rx']),
                float(row['ry']),
                float(row['rz']),
            ))
    return by_method


def load_viewpoints(path: Path) -> dict[str, list[dict[str, float]]]:
    """Load selected viewpoint positions and coverage values."""
    by_method: dict[str, list[dict[str, float]]] = {}
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


def load_method_rows(path: Path) -> list[dict[str, object]]:
    """Load method-level benchmark metrics in a fixed manuscript order."""
    rows: dict[str, dict[str, object]] = {}
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
            }
    return [rows[method] for method in METHOD_ORDER if method in rows]


def load_coverage_rows(path: Path) -> dict[str, list[tuple[float, float]]]:
    """Load coverage timelines by method."""
    rows: dict[str, list[tuple[float, float]]] = {}
    with path.open(newline='') as handle:
        for row in csv.DictReader(handle):
            rows.setdefault(row['method'], []).append((float(row['time']), float(row['coverage_ratio'])))
    return rows


def plot_offline_comparison_figures(data_dir: Path, output_dirs: tuple[Path, ...]) -> None:
    """Create paper-style comparison panels from archived benchmark CSV files."""
    method_rows = load_method_rows(data_dir / 'method_comparison.csv')
    coverage_rows = load_coverage_rows(data_dir / 'coverage.csv')
    for output_dir in output_dirs:
        output_dir.mkdir(parents=True, exist_ok=True)
        plot_coverage_comparison(output_dir / 'coverage_comparison.png', method_rows, coverage_rows)
        plot_metric_bar(
            output_dir / 'delta_v_comparison.png',
            method_rows,
            'total_delta_v',
            r'Total $\Delta v$ (m s$^{-1}$)',
        )
        plot_metric_bar(
            output_dir / 'energy_efficiency_comparison.png',
            method_rows,
            'delta_v_per_raw_coverage',
            r'$\Delta v$ per covered area ratio (m s$^{-1}$)',
        )
        plot_metric_bar(
            output_dir / 'safety_comparison.png',
            method_rows,
            'min_clearance',
            'Minimum clearance (m)',
            flag_infeasible=True,
        )
        plot_metric_bar(
            output_dir / 'peak_input_comparison.png',
            method_rows,
            'peak_requested_input',
            r'Peak requested input (m s$^{-2}$)',
        )


def plot_coverage_comparison(
    path: Path,
    method_rows: list[dict[str, object]],
    coverage_rows: dict[str, list[tuple[float, float]]],
) -> None:
    """Plot coverage progression with consistent method styling."""
    fig, ax = plt.subplots(figsize=(5.0, 4.0))
    for row in method_rows:
        method = str(row['method'])
        timeline = coverage_rows.get(method, [])
        if not timeline:
            continue
        final_raw = float(row['final_coverage_ratio'])
        final_inspectable = float(row['final_inspectable_coverage_ratio'])
        scale_factor = final_inspectable / max(final_raw, 1.0e-12)
        is_proposed = method == 'set_cover_cw_tour'
        ax.step(
            [item[0] for item in timeline],
            [min(1.0, item[1] * scale_factor) for item in timeline],
            where='post',
            linewidth=1.5,
            color=METHOD_COLORS.get(method, '#4D4D4D'),
            alpha=1.0 if is_proposed else 0.76,
            label=METHOD_LABELS.get(method, method),
        )
    ax.axhline(0.98, color='#272727', linestyle='--', linewidth=0.9, alpha=0.55)
    ax.text(0.29, 0.955, '98% stop target', transform=ax.transAxes,
            ha='right', va='center', fontsize=8, color='#272727')
    ax.set_xlabel('Mission time (s)')
    ax.set_ylabel('Inspectable area coverage')
    ax.set_ylim(0.0, 1.0)
    ax.grid(True, axis='y', color='#E1E1E1', linewidth=0.6)
    ax.legend(frameon=False, ncol=1, fontsize=8, loc='lower right')
    save_all(fig, path)


def plot_metric_bar(
    path: Path,
    method_rows: list[dict[str, object]],
    key: str,
    xlabel: str,
    flag_infeasible: bool = False,
) -> None:
    """Plot a compact horizontal comparison bar chart."""
    fig, ax = plt.subplots(figsize=(7.0, 3.15))
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


def plot_proposed_trajectory(
    path: Path,
    mesh_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    mesh_faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
    trajectory: list[tuple[float, float, float]],
    viewpoints: list[dict[str, float]],
) -> None:
    """Plot the proposed trajectory in the same frame as the ISS mesh."""
    fig = plt.figure(figsize=(5.4, 4.7))
    ax = fig.add_axes((0.00, 0.00, 1.00, 1.00), projection='3d')
    draw_mesh(ax, mesh_segments, mesh_faces)

    xs, ys, zs = unzip_points(trajectory)
    ax.plot(xs, ys, zs, color=NMI_PASTEL['baseline_dark'], linewidth=1.5, label='Trajectory', zorder=8)
    ax.scatter([xs[0]], [ys[0]], [zs[0]], s=72, c=NMI_PASTEL['delta_up'], marker='o', label='Start', depthshade=False)
    ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], s=88, c=NMI_PASTEL['delta_down'], marker='X', label='End', depthshade=False)

    if viewpoints:
        view_colors = [item['coverage'] for item in viewpoints]
        scatter = ax.scatter(
            [item['x'] for item in viewpoints],
            [item['y'] for item in viewpoints],
            [item['z'] for item in viewpoints],
            c=view_colors,
            cmap='viridis',
            s=58,
            marker='^',
            edgecolors='#222222',
            linewidths=0.3,
            depthshade=False,
            label='Selected viewpoints',
            zorder=9,
        )
        colorbar = fig.colorbar(scatter, ax=ax, shrink=0.62, pad=0.07)
        colorbar.set_label('Cumulative coverage')

    style_axis(ax)
    set_equal_axes(ax, mesh_segments, trajectory)
    ax.legend(loc='upper left', frameon=True, framealpha=0.92, fontsize=9)
    save_all(fig, path)


def plot_method_comparison(
    path: Path,
    mesh_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    mesh_faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
    trajectories: dict[str, list[tuple[float, float, float]]],
    viewpoints: dict[str, list[dict[str, float]]],
) -> None:
    """Plot method-wise trajectories and a separate effort-clearance summary."""
    method_rows = load_method_rows(DATA_DIR / 'method_comparison.csv')
    figure_methods = [method for method in METHOD_ORDER if method in trajectories]
    all_points = [point for method in figure_methods for point in trajectories.get(method, [])]
    light_segments = _stride_sequence(mesh_segments, 10, 7000)
    light_faces = _stride_sequence(mesh_faces, 14, 4500)

    fig = plt.figure(figsize=(8.4, 2.95))
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
        trajectory = trajectories.get(method, [])
        draw_mesh_method_context(ax, light_segments, light_faces)
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
            ax.scatter([xs[0]], [ys[0]], [zs[0]], s=24, c='#2E9E44', marker='o', depthshade=False, zorder=10)
            ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], s=30, c='#E53935', marker='X', depthshade=False, zorder=10)
        method_viewpoints = viewpoints.get(method, [])
        if method_viewpoints:
            ax.scatter(
                [item['x'] for item in method_viewpoints],
                [item['y'] for item in method_viewpoints],
                [item['z'] for item in method_viewpoints],
                c=[item['coverage'] for item in method_viewpoints],
                cmap='viridis',
                s=18,
                marker='^',
                edgecolors='#222222',
                linewidths=0.18,
                depthshade=False,
                zorder=10,
            )
        style_method_comparison_axis(ax, zoom=1.0)
        set_equal_axes(ax, [], all_points)
        title = METHOD_LABELS_SHORT.get(method, METHOD_LABELS.get(method, method))
        if method == 'coverage_greedy':
            title += ' (infeasible)'
        ax.set_title(title, fontsize=8.1, color=METHOD_COLORS.get(method, '#333333'), pad=0.5)

    save_all(fig, path, tight=False)

    for method in figure_methods:
        panel_name = METHOD_PANEL_FILES.get(method, f'trajectory_method_{method}')
        plot_single_method_trajectory_panel(
            path.with_name(panel_name),
            method,
            trajectories.get(method, []),
            light_segments,
            light_faces,
            all_points,
            viewpoints.get(method, []),
        )

    summary_fig, ax_summary = plt.subplots(figsize=(3.65, 3.12))
    plot_coverage_effort_summary(ax_summary, method_rows)
    save_all(summary_fig, path.with_name('trajectory_tradeoff_summary'))


def plot_single_method_trajectory_panel(
    path: Path,
    method: str,
    trajectory: list[tuple[float, float, float]],
    mesh_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    mesh_faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
    all_points: list[tuple[float, float, float]],
    viewpoints: list[dict[str, float]],
) -> None:
    """Save one compact trajectory panel for LaTeX-side subfigure packing."""
    fig = plt.figure(figsize=(1.30, 1.22))
    ax = fig.add_axes((-0.12, -0.13, 1.24, 1.24), projection='3d')
    draw_mesh_method_context(ax, mesh_segments, mesh_faces)
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
            s=22,
            c='#2E9E44',
            marker='o',
            depthshade=False,
            zorder=10,
        )
        ax.scatter(
            [xs[-1]],
            [ys[-1]],
            [zs[-1]],
            s=28,
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
            s=16,
            marker='^',
            edgecolors='#222222',
            linewidths=0.18,
            depthshade=False,
            zorder=9,
        )
    style_method_comparison_axis(ax, zoom=1.26)
    set_equal_axes(ax, [], all_points)
    save_all(fig, path, tight=False, bbox_inches='tight')


def draw_mesh_light(
    ax,
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
) -> None:
    """Draw a lightweight mesh background for small-multiple panels."""
    if faces:
        surface = Poly3DCollection(
            faces,
            facecolors='#AEBBC8',
            edgecolors='none',
            alpha=0.52,
            zorder=0,
        )
        ax.add_collection3d(surface)
    if segments:
        collection = Line3DCollection(
            segments,
            colors='#3E4852',
            linewidths=0.075,
            alpha=0.48,
            zorder=1,
        )
        ax.add_collection3d(collection)


def draw_mesh_camera_context(
    ax,
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
) -> None:
    """Draw the ISS mesh strongly enough to anchor camera frustum geometry."""
    if faces:
        surface = Poly3DCollection(
            faces,
            facecolors='#9FAAB5',
            edgecolors='none',
            alpha=0.34,
            zorder=0,
        )
        ax.add_collection3d(surface)
    if segments:
        collection = Line3DCollection(
            segments,
            colors='#4D5660',
            linewidths=0.11,
            alpha=0.58,
            zorder=1,
        )
        ax.add_collection3d(collection)


def draw_mesh_method_context(
    ax,
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
) -> None:
    """Draw the ISS mesh with visibility tuned for compact trajectory panels."""
    if faces:
        surface = Poly3DCollection(
            faces,
            facecolors='#E3E7EC',
            edgecolors='none',
            alpha=0.12,
            zorder=0,
        )
        ax.add_collection3d(surface)
    if segments:
        collection = Line3DCollection(
            segments,
            colors='#5F6872',
            linewidths=0.055,
            alpha=0.18,
            zorder=1,
        )
        ax.add_collection3d(collection)


def style_small_3d_axis(ax, zoom: float = 1.94) -> None:
    """Apply compact 3D styling for small multiples."""
    ax.view_init(elev=20.0, azim=-54.0)
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
        except Exception:
            pass
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor((1.0, 1.0, 1.0, 0.0))
        pane.set_edgecolor((1.0, 1.0, 1.0, 0.0))


def plot_coverage_effort_summary(ax, method_rows: list[dict[str, object]]) -> None:
    """Plot coverage, effort, and feasibility in one compact summary panel."""
    label_offsets = {
        'set_cover_cw_tour': (-5, -7, 'right', 'top'),
        'fuel_greedy': (0, -7, 'center', 'top'),
        'distance_greedy': (-3, 6, 'right', 'bottom'),
        'proposed_safe_cw_nbv': (6, -1, 'left', 'center'),
        'safe_coverage_greedy': (0, -7, 'center', 'top'),
        'coverage_greedy': (-3, 6, 'right', 'bottom'),
        'random_safe': (-3, 6, 'right', 'bottom'),
    }
    for row in method_rows:
        method = str(row['method'])
        delta_v = float(row['total_delta_v'])
        coverage = float(row['final_inspectable_coverage_ratio'])
        feasible = bool(row['feasible'])
        is_proposed = method == 'set_cover_cw_tour'
        ax.scatter(
            delta_v,
            coverage,
            s=94 if is_proposed else 58,
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
            bbox={
                'facecolor': 'white',
                'edgecolor': '#DADADA',
                'linewidth': 0.35,
                'alpha': 0.88,
                'boxstyle': 'round,pad=0.18',
            },
            zorder=5,
        )
    ax.axhline(0.98, color='#272727', linewidth=0.9, linestyle='--', alpha=0.62)
    ax.text(
        2.0,
        0.9992,
        '98% stop target',
        ha='left',
        va='bottom',
        fontsize=6.2,
        color='#272727',
    )
    ax.set_xlabel(r'Total $\Delta v$ (m s$^{-1}$)', fontsize=8.0, labelpad=2.0)
    ax.set_ylabel('Inspectable coverage', fontsize=8.0, labelpad=3.0)
    ax.tick_params(axis='both', labelsize=7.2, length=3.0, width=0.8)
    ax.grid(True, color='#E0E0E0', linewidth=0.55)
    ax.set_axisbelow(True)
    ax.set_xlim(0.0, 68.0)
    ax.set_ylim(0.952, 1.002)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)


def _stride_sequence(items: list, stride: int, max_items: int) -> list:
    """Downsample a sequence for lightweight repeated rendering."""
    if not items:
        return []
    sampled = items[::max(1, stride)]
    return sampled[:max_items]


def plot_camera_model_frusta(
    path: Path,
    mesh_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    mesh_faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
    trajectory: list[tuple[float, float, float]],
    viewpoints: list[dict[str, float]],
) -> None:
    """Overlay reconstructed camera frusta on the proposed ISS-mesh tour."""
    if not trajectory or not viewpoints:
        return
    fig = plt.figure(figsize=(7.2, 6.0))
    ax = fig.add_subplot(111, projection='3d')
    draw_mesh(ax, mesh_segments, mesh_faces)

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

    style_camera_overlay_axis(ax)
    set_equal_axes(ax, mesh_segments, trajectory)
    save_all(fig, path, tight=False, bbox_inches='tight')


def plot_camera_model_coverage(
    path: Path,
    viewpoints: list[dict[str, float]],
) -> None:
    """Plot incremental coverage contribution for representative selected views."""
    if not viewpoints:
        return
    fig, ax = plt.subplots(figsize=(4.65, 3.35))
    sequences = [int(item['sequence']) + 1 for item in viewpoints]
    gains = [float(item['coverage']) for item in viewpoints]
    increments = [gains[0]] + [max(0.0, gains[index] - gains[index - 1]) for index in range(1, len(gains))]
    sample_indices = [0, len(viewpoints) // 2, len(viewpoints) - 1]
    sample_indices = sorted(set(sample_indices))
    bar_colors = ['#C8D3E7'] * len(viewpoints)
    for color, index in zip(REPRESENTATIVE_VIEW_COLORS, sample_indices):
        bar_colors[index] = color
    ax.bar(
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
    label_offsets = [(0.35, 0.0025, 'left'), (0.35, 0.0025, 'left'), (-0.35, 0.0025, 'right')]
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
    ax.text(
        0.98,
        0.97,
        f'final coverage {gains[-1] * 100:.1f}%',
        transform=ax.transAxes,
        ha='right',
        va='top',
        fontsize=7.0,
        color='#333333',
    )
    ax.set_xlabel('Selected view index', fontsize=7.5)
    ax.set_ylabel('Incremental coverage', fontsize=7.5)
    ax.tick_params(axis='both', labelsize=7.0, length=3.0, width=0.8)
    ax.grid(True, axis='y', color='#E1E1E1', linewidth=0.55)
    ax.set_axisbelow(True)
    ax.set_xlim(0.2, max(sequences) + 0.8)
    ax.set_ylim(0.0, max(increments) * 1.18)
    ax.set_xticks([1, 5, 10, 15, 20, max(sequences)])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.subplots_adjust(left=0.18, right=0.98, bottom=0.16, top=0.98)
    save_all(fig, path, tight=False)


def style_camera_axis(ax, zoom: float = 2.12) -> None:
    """Apply compact 3D styling for the camera verification panel."""
    ax.view_init(elev=20.0, azim=-54.0)
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
        except Exception:
            pass
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor((1.0, 1.0, 1.0, 0.0))
        pane.set_edgecolor((1.0, 1.0, 1.0, 0.0))


def style_camera_overlay_axis(ax, zoom: float = 1.10) -> None:
    """Use the proposed-tour viewpoint without visible 3D axes."""
    ax.view_init(elev=20.0, azim=-54.0)
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
    ax.view_init(elev=20.0, azim=-54.0)
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


def draw_mesh(
    ax,
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
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
    ax.view_init(elev=20.0, azim=-54.0)
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
    mesh_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    points: list[tuple[float, float, float]],
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


def set_axes_from_points(
    ax,
    points: list[tuple[float, float, float]],
    pad: float = 0.12,
) -> None:
    """Use an equal 3D box focused on the supplied geometry points."""
    xs, ys, zs = unzip_points(points)
    center = (
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0,
        (min(zs) + max(zs)) / 2.0,
    )
    radius = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) * (0.5 + pad)
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)


def bounds_from_points(
    points: list[tuple[float, float, float]],
    pad: float = 0.12,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """Return an equal 3D bounding box around the supplied points."""
    xs, ys, zs = unzip_points(points)
    center = (
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0,
        (min(zs) + max(zs)) / 2.0,
    )
    radius = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) * (0.5 + pad)
    return (
        (center[0] - radius, center[0] + radius),
        (center[1] - radius, center[1] + radius),
        (center[2] - radius, center[2] + radius),
    )


def set_axes_from_bounds(
    ax,
    bounds: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
) -> None:
    """Apply explicit 3D axis limits from precomputed bounds."""
    ax.set_xlim(*bounds[0])
    ax.set_ylim(*bounds[1])
    ax.set_zlim(*bounds[2])


def filter_segments_to_bounds(
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    bounds: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
    max_items: int,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    """Keep mesh segments near the focused camera-frustum region."""
    selected = [
        segment
        for segment in segments
        if point_in_bounds(segment[0], bounds) or point_in_bounds(segment[1], bounds)
    ]
    if len(selected) <= max_items:
        return selected
    stride = max(1, math.ceil(len(selected) / max_items))
    return selected[::stride]


def filter_faces_to_bounds(
    faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
    bounds: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
    max_items: int,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    """Keep mesh faces near the focused camera-frustum region."""
    selected = [
        face
        for face in faces
        if any(point_in_bounds(point, bounds) for point in face)
    ]
    if len(selected) <= max_items:
        return selected
    stride = max(1, math.ceil(len(selected) / max_items))
    return selected[::stride]


def point_in_bounds(
    point: tuple[float, float, float],
    bounds: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
) -> bool:
    """Return true when a point lies inside an axis-aligned 3D box."""
    return (
        bounds[0][0] <= point[0] <= bounds[0][1]
        and bounds[1][0] <= point[1] <= bounds[1][1]
        and bounds[2][0] <= point[2] <= bounds[2][1]
    )


def save_all(fig, path: Path, tight: bool = True, bbox_inches: str | None = 'tight') -> None:
    """Save PNG, PDF, and SVG versions of a figure."""
    if tight:
        fig.tight_layout()
    for suffix in ('.png', '.pdf', '.svg'):
        fig.savefig(path.with_suffix(suffix), dpi=360, bbox_inches=bbox_inches, pad_inches=0.0)
    plt.close(fig)


def unzip_points(points: list[tuple[float, float, float]]) -> tuple[list[float], list[float], list[float]]:
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


def _subtract(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def load_mesh_segments(
    path: Path,
    scale: float,
    max_edges: int,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
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
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []

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
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
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
    faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []

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
    plt.switch_backend('Agg')
    plt.rcParams.update({
        'font.family': 'DejaVu Sans',
        'font.size': 9,
        'axes.labelsize': 9,
        'legend.fontsize': 8,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'figure.dpi': 180,
        'savefig.dpi': 360,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })
    main()
