#!/usr/bin/env python3
"""Generate a publication-ready planned-vs-executed trajectory figure."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.gridspec import GridSpec  # noqa: E402
import numpy as np  # noqa: E402


REQUIRED_COLUMNS = {
    'time',
    'rx',
    'ry',
    'rz',
    'planned_rx',
    'planned_ry',
    'planned_rz',
    'position_tracking_error_norm',
    'velocity_tracking_error_norm',
}


def main() -> None:
    """Run the plotting command."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--result-dir',
        type=Path,
        default=None,
        help='Result directory containing raw/trajectory.csv.',
    )
    parser.add_argument(
        '--workspace',
        type=Path,
        default=Path.cwd(),
        help='OrbInspect workspace root.',
    )
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    result_dir = args.result_dir or _latest_result_dir(workspace / 'data' / 'results')
    rows = _read_trajectory(result_dir / 'raw' / 'trajectory.csv')
    output_base = result_dir / 'figures' / 'planned_vs_executed_trajectory'
    output_base.parent.mkdir(parents=True, exist_ok=True)

    planned = _array(rows, ('planned_rx', 'planned_ry', 'planned_rz'))
    executed = _array(rows, ('rx', 'ry', 'rz'))
    time = np.asarray([float(row['time']) for row in rows])
    position_error = np.asarray([
        float(row['position_tracking_error_norm'])
        for row in rows
    ])
    velocity_error = np.asarray([
        float(row['velocity_tracking_error_norm'])
        for row in rows
    ])

    _configure_style()
    figure = plt.figure(figsize=(7.45, 4.85), constrained_layout=True)
    grid = GridSpec(2, 2, figure=figure, width_ratios=[1.18, 1.0], height_ratios=[1.0, 1.0])
    axis_3d = figure.add_subplot(grid[:, 0], projection='3d')
    axis_error = figure.add_subplot(grid[0, 1])
    axis_projection = figure.add_subplot(grid[1, 1])

    _plot_station_mesh(axis_3d, workspace)
    _plot_trajectory_overlay(axis_3d, planned, executed)
    _set_equal_3d(axis_3d, np.vstack([planned, executed]))

    axis_error.plot(time, position_error, color='#b23a48', linewidth=1.7, label='position')
    axis_error.set_ylabel('Position error [m]')
    axis_error.grid(True, linewidth=0.45, alpha=0.35)
    axis_error_twin = axis_error.twinx()
    axis_error_twin.plot(time, velocity_error, color='#2f6f9f', linewidth=1.4, label='velocity')
    axis_error_twin.set_ylabel('Velocity error [m/s]')
    axis_error.set_xlabel('Time [s]')
    _combined_legend(axis_error, axis_error_twin, loc='upper right')

    axis_projection.plot(
        executed[:, 0],
        executed[:, 2],
        color='#d17a22',
        linewidth=2.2,
        alpha=0.86,
        label='simulated',
    )
    axis_projection.plot(
        planned[:, 0],
        planned[:, 2],
        color='#1f4e79',
        linewidth=1.7,
        linestyle=(0, (3, 2)),
        label='designed',
        zorder=4,
    )
    axis_projection.scatter(planned[0, 0], planned[0, 2], s=24, color='#1f4e79', zorder=4)
    axis_projection.scatter(executed[-1, 0], executed[-1, 2], s=28, color='#d17a22', zorder=4)
    axis_projection.set_xlabel('$r_x$ [m]')
    axis_projection.set_ylabel('$r_z$ [m]')
    axis_projection.grid(True, linewidth=0.45, alpha=0.35)
    axis_projection.legend(frameon=False, loc='best')
    axis_projection.margins(x=0.08, y=0.08)

    stats = (
        f"mean $e_r$ = {position_error.mean():.2f} m\n"
        f"max $e_r$ = {position_error.max():.2f} m\n"
        f"mean $e_v$ = {velocity_error.mean():.3f} m/s"
    )
    axis_3d.text2D(
        0.03,
        0.96,
        stats,
        transform=axis_3d.transAxes,
        va='top',
        ha='left',
        fontsize=8.2,
        bbox={'facecolor': 'white', 'edgecolor': '0.75', 'alpha': 0.92, 'pad': 3.0},
    )

    for suffix in ('png', 'pdf', 'svg'):
        figure.savefig(output_base.with_suffix(f'.{suffix}'), dpi=450 if suffix == 'png' else None)
    plt.close(figure)
    print(output_base.with_suffix('.png'))
    print(output_base.with_suffix('.pdf'))
    print(output_base.with_suffix('.svg'))


def _configure_style() -> None:
    plt.rcParams.update({
        'font.family': 'DejaVu Serif',
        'font.size': 9,
        'axes.labelsize': 9,
        'legend.fontsize': 8.2,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'axes.linewidth': 0.75,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
        'svg.fonttype': 'none',
    })


def _latest_result_dir(results_root: Path) -> Path:
    for result_dir in sorted(results_root.glob('*'), key=lambda path: path.stat().st_mtime, reverse=True):
        trajectory = result_dir / 'raw' / 'trajectory.csv'
        if not trajectory.is_file():
            continue
        with trajectory.open('r', newline='') as csv_file:
            header = set(next(csv.reader(csv_file), []))
        if REQUIRED_COLUMNS <= header:
            return result_dir
    raise FileNotFoundError('no result directory with planned-vs-executed trajectory.csv found')


def _read_trajectory(path: Path) -> list[dict[str, str]]:
    with path.open('r', newline='') as csv_file:
        rows = list(csv.DictReader(csv_file))
    if not rows:
        raise ValueError(f'{path} contains no trajectory rows')
    missing = REQUIRED_COLUMNS - set(rows[0])
    if missing:
        raise ValueError(f'{path} is missing columns: {sorted(missing)}')
    return rows


def _array(rows: list[dict[str, str]], columns: tuple[str, str, str]) -> np.ndarray:
    return np.asarray([[float(row[column]) for column in columns] for row in rows], dtype=float)


def _plot_trajectory_overlay(axis, planned: np.ndarray, executed: np.ndarray) -> None:
    axis.plot(
        executed[:, 0],
        executed[:, 1],
        executed[:, 2],
        color='#d17a22',
        linewidth=2.35,
        alpha=0.86,
        label='simulated trajectory',
    )
    axis.plot(
        planned[:, 0],
        planned[:, 1],
        planned[:, 2],
        color='#1f4e79',
        linewidth=1.75,
        linestyle=(0, (3, 2)),
        label='designed trajectory',
        zorder=5,
    )
    axis.scatter(planned[0, 0], planned[0, 1], planned[0, 2], s=26, color='#1f4e79')
    axis.scatter(executed[-1, 0], executed[-1, 1], executed[-1, 2], s=30, color='#d17a22')
    axis.set_xlabel('$r_x$ [m]', labelpad=2)
    axis.set_ylabel('$r_y$ [m]', labelpad=2)
    axis.set_zlabel('$r_z$ [m]', labelpad=2)
    axis.view_init(elev=23, azim=-48)
    axis.set_box_aspect((1.0, 1.0, 0.9))
    axis.grid(True, linewidth=0.35, alpha=0.25)
    axis.legend(
        frameon=False,
        loc='upper center',
        bbox_to_anchor=(0.48, -0.04),
        ncol=1,
        borderaxespad=0.0,
    )


def _plot_station_mesh(axis, workspace: Path) -> None:
    mesh_path = (
        workspace
        / 'src'
        / 'orbinspect_description'
        / 'models'
        / 'iss_real'
        / 'meshes'
        / 'ISS_stationary_rviz.stl'
    )
    if not mesh_path.is_file():
        return
    try:
        import trimesh
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except ImportError:
        return
    mesh = trimesh.load(mesh_path, force='mesh')
    if len(mesh.faces) == 0:
        return
    max_faces = 900
    step = max(1, len(mesh.faces) // max_faces)
    faces = mesh.faces[::step]
    vertices = np.asarray(mesh.vertices)
    triangles = vertices[faces]
    # Match the RViz marker orientation: 90 deg about Y, then scale.
    scale = 1.065
    rotated = np.empty_like(triangles)
    rotated[..., 0] = scale * triangles[..., 2]
    rotated[..., 1] = scale * triangles[..., 1]
    rotated[..., 2] = -scale * triangles[..., 0]
    collection = Poly3DCollection(
        rotated,
        facecolor=(0.68, 0.70, 0.74, 0.075),
        edgecolor=(0.45, 0.47, 0.50, 0.045),
        linewidth=0.08,
    )
    axis.add_collection3d(collection)


def _set_equal_3d(axis, points: np.ndarray) -> None:
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    center = 0.5 * (mins + maxs)
    radius = 0.5 * max(maxs - mins)
    radius = max(radius, 1.0)
    axis.set_xlim(center[0] - radius, center[0] + radius)
    axis.set_ylim(center[1] - radius, center[1] + radius)
    axis.set_zlim(center[2] - radius, center[2] + radius)


def _combined_legend(axis, twin, loc: str) -> None:
    handles, labels = axis.get_legend_handles_labels()
    twin_handles, twin_labels = twin.get_legend_handles_labels()
    axis.legend(handles + twin_handles, labels + twin_labels, frameon=False, loc=loc)


if __name__ == '__main__':
    main()
