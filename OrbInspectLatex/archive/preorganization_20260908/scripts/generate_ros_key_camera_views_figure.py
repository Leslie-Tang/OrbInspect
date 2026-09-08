#!/usr/bin/env python3
"""Generate a trajectory-linked camera-view figure for the accepted ROS run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

import cv2
import matplotlib as mpl

mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.collections import PolyCollection
from matplotlib.patches import ConnectionPatch
from matplotlib.patches import Rectangle
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for package in (
    'orbinspect_guidance',
    'orbinspect_dynamics',
    'orbinspect_perception',
    'orbinspect_safety',
):
    sys.path.insert(0, str(ROOT / 'src' / package))

from orbinspect_guidance.offline_coverage_planner import IssMeshGeometry


DEFAULT_RUN_DIR = (
    ROOT / 'data/results/'
    'ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812'
)
MESH_PATH = (
    ROOT / 'src/orbinspect_description/models/iss_real/meshes/'
    'ISS_stationary.glb'
)
COLORS = (
    '#3B4CC0', '#526ED3', '#3E8ABF', '#20A486', '#5DC863',
    '#AADC32', '#DCE319', '#F4C430', '#F8961E', '#D1495B',
)
DISPLAY_TRIANGLES = 14_000
VEHICLE_RADIUS_M = 0.80
SAFETY_MARGIN_M = 2.00


def parse_args() -> argparse.Namespace:
    """Parse the accepted-run override."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=DEFAULT_RUN_DIR)
    return parser.parse_args()


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read one CSV file into dictionaries."""
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def validate_run(run_dir: Path) -> tuple[dict[str, object], dict[str, object]]:
    """Require the accepted complete mission and finite-body mesh audit."""
    summary = json.loads((run_dir / 'summary.json').read_text(encoding='utf-8'))
    audit = json.loads(
        (run_dir / 'mesh_execution_audit.json').read_text(encoding='utf-8')
    )
    verification = summary.get('verification', {})
    if not verification.get('success', False):
        raise ValueError('source ROS task did not complete successfully')
    if verification.get('credited_actions') != 10:
        raise ValueError('source ROS task did not credit all 10 observations')
    if not audit.get('passed', False):
        raise ValueError('source finite-body full-mesh audit did not pass')
    return summary, audit


def synchronized_camera_frames(
    video_path: Path,
    timing: dict[str, object],
    events: list[dict[str, str]],
) -> tuple[list[np.ndarray], list[dict[str, object]]]:
    """Extract frames using the same wall-clock synchronization as the video."""
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f'failed to open {video_path}')
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if frame_count < 2:
        raise ValueError('camera stream must contain multiple frames')
    mission_start = float(timing['mission_process_start_wall_epoch_s'])
    camera_start = float(timing['camera_first_frame_wall_epoch_s'])
    camera_end = float(timing['camera_last_frame_wall_epoch_s'])
    time_scale = float(timing['mission_time_scale'])
    frames: list[np.ndarray] = []
    records: list[dict[str, object]] = []
    for sequence, event in enumerate(events, start=1):
        mission_time = float(event['time'])
        wall_time = mission_start + mission_time / time_scale
        fraction = (wall_time - camera_start) / (camera_end - camera_start)
        fraction = min(max(fraction, 0.0), 1.0)
        frame_index = int(round(fraction * (frame_count - 1)))
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            capture.release()
            raise RuntimeError(f'failed to decode camera frame {frame_index}')
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        records.append({
            'sequence': sequence,
            'waypoint_id': event['current_waypoint_id'],
            'mission_time_s': mission_time,
            'camera_frame_index': frame_index,
            'camera_frame_fraction': fraction,
            'cumulative_coverage': float(event['coverage_ratio']),
        })
    capture.release()
    return frames, records


def trajectory_arrays(
    rows: list[dict[str, str]],
    records: list[dict[str, object]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, object]]]:
    """Return planned/executed paths and exact event-aligned trajectory rows."""
    times = np.asarray([float(row['time']) for row in rows], dtype=float)
    executed = np.asarray([
        [float(row['rx']), float(row['ry']), float(row['rz'])]
        for row in rows
    ])
    planned = np.asarray([
        [float(row['planned_rx']), float(row['planned_ry']),
         float(row['planned_rz'])]
        for row in rows
    ])
    event_points = []
    for record in records:
        mission_time = float(record['mission_time_s'])
        index = int(np.argmin(np.abs(times - mission_time)))
        discrepancy = abs(float(times[index]) - mission_time)
        if discrepancy > 1.0e-6:
            raise ValueError(
                f'no exact trajectory row for event at {mission_time:.9f} s'
            )
        point = executed[index]
        event_points.append(point)
        record['trajectory_row_index'] = index
        record['trajectory_time_s'] = float(times[index])
        record['executed_position_lvlh_m'] = point.tolist()
        record['planned_position_lvlh_m'] = planned[index].tolist()
    return planned, executed, np.asarray(event_points), records


def style() -> None:
    """Apply compact IEEE-compatible typography and vector-font settings."""
    mpl.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 7.4,
        'axes.labelsize': 7.6,
        'xtick.labelsize': 6.8,
        'ytick.labelsize': 6.8,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
        'figure.facecolor': 'white',
        'savefig.facecolor': 'white',
    })


def add_camera_panel(
    axis: mpl.axes.Axes,
    frame: np.ndarray,
    record: dict[str, object],
    color: str,
) -> None:
    """Draw one synchronized view with a stable numbered identity."""
    axis.imshow(frame, interpolation='lanczos')
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_color(color)
        spine.set_linewidth(1.35)
    axis.add_patch(Rectangle(
        (0.0, 0.0), 0.178, 0.22,
        transform=axis.transAxes,
        facecolor='white', edgecolor='none', alpha=0.90, zorder=5,
    ))
    axis.text(
        0.027, 0.046, str(record['sequence']),
        transform=axis.transAxes, ha='left', va='bottom',
        fontsize=8.1, fontweight='bold', color=color, zorder=6,
    )
    axis.text(
        0.97, 0.05,
        f"{float(record['mission_time_s']):.0f} s  |  "
        f"{100.0 * float(record['cumulative_coverage']):.1f}%",
        transform=axis.transAxes, ha='right', va='bottom',
        fontsize=5.8, color='white', zorder=6,
        bbox={
            'facecolor': '#111820', 'edgecolor': 'none',
            'alpha': 0.78, 'pad': 1.1,
        },
    )


def add_projection_leader(
    figure: mpl.figure.Figure,
    projection_axis: mpl.axes.Axes,
    image_axis: mpl.axes.Axes,
    point: np.ndarray,
    color: str,
    camera_on_left: bool,
) -> None:
    """Connect one camera panel only to its assigned 2-D projection."""
    connection = ConnectionPatch(
        xyA=(1.0 if camera_on_left else 0.0, 0.50),
        coordsA=image_axis.transAxes,
        xyB=tuple(point),
        coordsB=projection_axis.transData,
        axesA=image_axis,
        axesB=projection_axis,
        color=color,
        linewidth=0.62,
        alpha=0.72,
        zorder=35,
        arrowstyle='-',
        connectionstyle=(
            'angle,angleA=0,angleB=90,rad=2.0'
            if camera_on_left
            else 'angle,angleA=180,angleB=90,rad=2.0'
        ),
        clip_on=False,
    )
    figure.add_artist(connection)


def add_projected_mesh(
    axis: mpl.axes.Axes,
    mesh: IssMeshGeometry,
    horizontal_index: int,
) -> None:
    """Draw a deterministic vector projection of the transformed ISS mesh."""
    indices = np.linspace(
        0, len(mesh.triangles) - 1, DISPLAY_TRIANGLES, dtype=int,
    )
    faces = [
        np.asarray(triangle.vertices, dtype=float)[:, (horizontal_index, 2)]
        for triangle in (mesh.triangles[int(index)] for index in indices)
    ]
    axis.add_collection(PolyCollection(
        faces,
        facecolor='#C9D0D7', edgecolor='#6F7983',
        linewidth=0.035, alpha=0.55, zorder=0,
    ))


def draw_projection(
    axis: mpl.axes.Axes,
    mesh: IssMeshGeometry,
    planned: np.ndarray,
    executed: np.ndarray,
    event_points: np.ndarray,
    horizontal_index: int,
    active_indices: range,
    title: str,
    horizontal_label: str,
) -> tuple[Line2D, Line2D]:
    """Draw one orthogonal path projection with active and context markers."""
    add_projected_mesh(axis, mesh, horizontal_index)
    planned_line, = axis.plot(
        planned[:, horizontal_index], planned[:, 2],
        color='#70777E', linestyle=(0, (3, 2)), linewidth=0.82,
        alpha=0.92, label='Planned', zorder=7,
    )
    executed_line, = axis.plot(
        executed[:, horizontal_index], executed[:, 2],
        color='#005F84', linewidth=1.38,
        label='Executed', zorder=9,
    )
    axis.scatter(
        executed[0, horizontal_index], executed[0, 2],
        marker='*', s=58, facecolor='white', edgecolor='#111820',
        linewidth=0.72, zorder=28,
    )
    active = set(active_indices)
    for index, (point, color) in enumerate(
        zip(event_points, COLORS, strict=True),
    ):
        is_active = index in active
        axis.scatter(
            point[horizontal_index], point[2],
            s=47 if is_active else 26,
            marker='o',
            facecolor=color if is_active else 'white',
            edgecolor='white' if is_active else '#8A939C',
            linewidth=1.0 if is_active else 0.65,
            alpha=1.0 if is_active else 0.72,
            zorder=29 if is_active else 25,
        )
        axis.text(
            point[horizontal_index], point[2], str(index + 1),
            ha='center', va='center',
            fontsize=5.3 if is_active else 4.6,
            fontweight='bold',
            color='#111820' if is_active else '#6F7880',
            alpha=1.0 if is_active else 0.78,
            zorder=31,
        )

    axis.set_xlim((-40.0, 55.0) if horizontal_index == 0 else (-42.0, 48.0))
    axis.set_ylim(-65.0, 65.0)
    axis.set_aspect('equal', adjustable='box')
    axis.set_title(title, fontsize=7.3, fontweight='bold', pad=3.0)
    axis.set_xlabel(horizontal_label, labelpad=1.5)
    axis.grid(True, color='#D7DDE2', linewidth=0.38, alpha=0.82)
    axis.set_axisbelow(True)
    axis.tick_params(direction='out', length=2.2, width=0.55, pad=1.5)
    for spine in axis.spines.values():
        spine.set_color('#7E8790')
        spine.set_linewidth(0.55)
    return planned_line, executed_line


def save_individual_camera_views(
    frames: list[np.ndarray],
    records: list[dict[str, object]],
    manuscript_dir: Path,
    evidence_dir: Path,
) -> list[Path]:
    """Save each annotated camera subfigure as PDF and 600-dpi PNG."""
    manuscript_view_dir = manuscript_dir / 'ros_key_camera_views'
    evidence_view_dir = evidence_dir / 'ros_key_camera_views'
    manuscript_view_dir.mkdir(parents=True, exist_ok=True)
    evidence_view_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for frame, record, color in zip(frames, records, COLORS, strict=True):
        sequence = int(record['sequence'])
        waypoint_id = str(record['waypoint_id'])
        mission_second = int(round(float(record['mission_time_s'])))
        stem = (
            f'view_{sequence:02d}_{waypoint_id}_t{mission_second:04d}s'
        )
        height_in = 3.5 * float(frame.shape[0]) / float(frame.shape[1])
        figure = plt.figure(figsize=(3.5, height_in))
        axis = figure.add_axes((0.006, 0.009, 0.988, 0.982))
        add_camera_panel(axis, frame, record, color)
        pdf = manuscript_view_dir / f'{stem}.pdf'
        png = manuscript_view_dir / f'{stem}.png'
        figure.savefig(pdf, dpi=600, pad_inches=0)
        figure.savefig(png, dpi=600, pad_inches=0)
        plt.close(figure)
        for output in (pdf, png):
            mirror = evidence_view_dir / output.name
            shutil.copy2(output, mirror)
            if sha256(output) != sha256(mirror):
                raise RuntimeError(f'individual-view mirror mismatch: {output}')
            outputs.append(output)
        record['individual_outputs'] = {
            'pdf': str(pdf.relative_to(ROOT)),
            'png': str(png.relative_to(ROOT)),
            'pdf_sha256': sha256(pdf),
            'png_sha256': sha256(png),
            'export_dpi': 600,
            'source_width_px': int(frame.shape[1]),
            'source_height_px': int(frame.shape[0]),
        }
    return outputs


def generate_figure(
    frames: list[np.ndarray],
    records: list[dict[str, object]],
    planned: np.ndarray,
    executed: np.ndarray,
    event_points: np.ndarray,
) -> mpl.figure.Figure:
    """Render local camera links around two orthogonal path projections."""
    style()
    figure = plt.figure(figsize=(7.15, 4.48))
    grid = figure.add_gridspec(
        5, 4,
        width_ratios=(1.31, 1.86, 1.86, 1.31),
        left=0.010, right=0.990, bottom=0.075, top=0.982,
        hspace=0.035, wspace=0.105,
    )
    left_camera_axes = [figure.add_subplot(grid[row, 0]) for row in range(5)]
    right_camera_axes = [figure.add_subplot(grid[row, 3]) for row in range(5)]
    image_axes = left_camera_axes + right_camera_axes
    for axis, frame, record, color in zip(
        image_axes, frames, records, COLORS, strict=True,
    ):
        add_camera_panel(axis, frame, record, color)

    mesh = IssMeshGeometry.load(MESH_PATH, 1.065, 0)
    for point, record in zip(event_points, records, strict=True):
        center_distance = mesh.surface_distance(tuple(point))
        record['mesh_center_distance_m'] = center_distance
        record['body_clearance_above_required_margin_m'] = (
            center_distance - VEHICLE_RADIUS_M - SAFETY_MARGIN_M
        )

    xz_axis = figure.add_subplot(grid[:, 1])
    yz_axis = figure.add_subplot(grid[:, 2])
    planned_line, executed_line = draw_projection(
        xz_axis,
        mesh,
        planned,
        executed,
        event_points,
        horizontal_index=0,
        active_indices=range(0, 5),
        title='(a) Radial $x$–cross-track $z$',
        horizontal_label='Radial $x$ [m]',
    )
    draw_projection(
        yz_axis,
        mesh,
        planned,
        executed,
        event_points,
        horizontal_index=1,
        active_indices=range(5, 10),
        title='(b) Along-track $y$–cross-track $z$',
        horizontal_label='Along-track $y$ [m]',
    )
    xz_axis.text(
        0.50, 0.015,
        'Full 3-D margin: $c_2=+11.36$ m; $c_3=+9.84$ m',
        transform=xz_axis.transAxes, ha='center', va='bottom',
        fontsize=5.25, color='#26313A', zorder=40,
        bbox={
            'facecolor': 'white', 'edgecolor': '#AEB7BF',
            'alpha': 0.92, 'linewidth': 0.45, 'pad': 1.4,
        },
    )
    start_handle = Line2D(
        [0], [0], marker='*', markersize=8.5, markerfacecolor='white',
        markeredgecolor='#111820', linewidth=0, label='Start',
    )
    figure.legend(
        handles=(planned_line, executed_line, start_handle),
        frameon=True, facecolor='white', edgecolor='#C5CBD1',
        framealpha=0.94, loc='lower center', bbox_to_anchor=(0.50, 0.006),
        ncol=3, fontsize=6.25, handlelength=1.8,
        columnspacing=1.25, borderpad=0.26,
    )
    figure.canvas.draw()

    # Both projections use the same vertical coordinate.  A single label in
    # the clear gutter beside the projection pair avoids colliding with the
    # camera panels or duplicating the label between the two axes.
    camera_right = max(axis.get_position().x1 for axis in left_camera_axes)
    projection_left = xz_axis.get_position().x0
    projection_center_y = (
        xz_axis.get_position().y0 + xz_axis.get_position().y1
    ) / 2.0
    figure.text(
        camera_right + 0.18 * (projection_left - camera_right),
        projection_center_y,
        'Cross-track $z$ [m]',
        ha='center', va='center', rotation='vertical',
        fontsize=7.6, zorder=100,
        bbox={
            'facecolor': 'white', 'edgecolor': 'none',
            'alpha': 0.96, 'pad': 1.6,
        },
    )

    for point, color, axis in zip(
        event_points[:5], COLORS[:5], left_camera_axes, strict=True,
    ):
        add_projection_leader(
            figure,
            xz_axis,
            axis,
            point[[0, 2]],
            color,
            camera_on_left=True,
        )
    for point, color, axis in zip(
        event_points[5:], COLORS[5:], right_camera_axes, strict=True,
    ):
        add_projection_leader(
            figure,
            yz_axis,
            axis,
            point[[1, 2]],
            color,
            camera_on_left=False,
        )
    return figure


def main() -> None:
    """Validate sources, generate manuscript outputs, and record provenance."""
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    summary, audit = validate_run(run_dir)
    timing_path = run_dir / 'config_snapshot/video_timing.json'
    timing = json.loads(timing_path.read_text(encoding='utf-8'))
    event_path = run_dir / 'raw/mission_events.csv'
    events = [
        row for row in read_csv(event_path)
        if row['event'] == 'observation_credited'
    ]
    if len(events) != 10:
        raise ValueError(f'expected 10 credited events, found {len(events)}')
    camera_path = run_dir / 'raw/camera_sensor_raw.mp4'
    frames, records = synchronized_camera_frames(
        camera_path, timing, events,
    )
    trajectory_path = run_dir / 'raw/trajectory.csv'
    planned, executed, event_points, records = trajectory_arrays(
        read_csv(trajectory_path), records,
    )
    figure = generate_figure(
        frames, records, planned, executed, event_points,
    )

    manuscript_dir = ROOT / 'OrbInspectLatex/figures'
    evidence_dir = run_dir / 'figures'
    manuscript_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    pdf = manuscript_dir / 'ros_key_camera_views_trajectory.pdf'
    png = manuscript_dir / 'ros_key_camera_views_trajectory.png'
    figure.savefig(pdf, dpi=600)
    figure.savefig(png, dpi=600)
    plt.close(figure)
    for output in (pdf, png):
        shutil.copy2(output, evidence_dir / output.name)
    individual_outputs = save_individual_camera_views(
        frames, records, manuscript_dir, evidence_dir,
    )

    source_paths = (
        camera_path,
        timing_path,
        event_path,
        trajectory_path,
        run_dir / 'summary.json',
        run_dir / 'mesh_execution_audit.json',
        MESH_PATH,
    )
    provenance = {
        'schema_version': 'orbinspect-ros-key-camera-views-figure/v3',
        'source_run': str(run_dir.relative_to(ROOT)),
        'scenario_id': timing['scenario_id'],
        'method': timing['method'],
        'synchronization': (
            'event mission time -> mission wall time -> normalized retained '
            'camera stream frame, matching the accepted video compositor'
        ),
        'state_source_of_truth': 'ROS-native HCW dynamics node',
        'gazebo_role': 'visualization and chaser camera only',
        'mesh_transform': audit['mesh_transform'],
        'mesh_audit_passed': audit['passed'],
        'mesh_display': {
            'source_triangle_count': 247_525,
            'display_triangle_count': DISPLAY_TRIANGLES,
            'selection': 'deterministic uniformly spaced triangle indices',
            'interpretation': (
                'Display decimation affects rendering only; the accepted '
                'version-2 safety audit evaluated all source triangles.'
            ),
        },
        'composite_layout': {
            'left_camera_views': [1, 2, 3, 4, 5],
            'left_projection': 'radial-cross-track (x-z)',
            'right_camera_views': [6, 7, 8, 9, 10],
            'right_projection': 'along-track-cross-track (y-z)',
            'leader_policy': (
                'one local leader per camera view; all other projection '
                'markers remain as hollow gray context'
            ),
        },
        'verification': summary['verification'],
        'camera_views': records,
        'sources_sha256': {
            str(path.relative_to(ROOT)): sha256(path) for path in source_paths
        },
        'outputs_sha256': {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (pdf, png, *individual_outputs)
        },
        'script_sha256': sha256(Path(__file__)),
        'interpretation': (
            'Camera frames document the rendered field of view at each '
            'credited terminal event. Coverage credit comes from the frozen '
            'geometric visibility masks, not image-pixel processing.'
        ),
    }
    manifest_path = evidence_dir / 'ros_key_camera_views_trajectory_manifest.json'
    manifest_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )
    print(pdf)
    print(png)
    print(manuscript_dir / 'ros_key_camera_views')
    print(manifest_path)


if __name__ == '__main__':
    main()
