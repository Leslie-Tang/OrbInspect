#!/usr/bin/env python3
"""Render compact Figure 7 from a verified historical or required-target snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.transforms import Bbox
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/historical_ros/figure7'
STEM = 'ros_key_camera_views_trajectory'
# Retain the approved observation identities, colors, paths and mesh treatment.
COLORS = ('#3B4CC0', '#526ED3', '#3E8ABF', '#20A486', '#5DC863',
          '#AADC32', '#DCE319', '#F4C430', '#F8961E', '#D1495B',
          '#B83B73', '#7E4A9E')
WIDTH_MM, HEIGHT_MM = 170.0, 47.0
CAMERA_WIDTH_MM = 20.8
CAMERA_GAP_MM = 0.8
CAMERA_ROW_PITCH_MM = 21.5
CAMERA_LEFT_MM = 62.1
PROJECTION_SCALE = 0.66
RIGHT_MARKER_PADDING_MM = 0.6


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configure_style() -> None:
    mpl.rcParams.update({
        'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 7.2, 'axes.labelsize': 7.5, 'xtick.labelsize': 7, 'ytick.labelsize': 7,
        'svg.fonttype': 'none', 'pdf.fonttype': 42, 'ps.fonttype': 42,
        'figure.facecolor': 'white', 'savefig.facecolor': 'white', 'svg.hashsalt': 'orbinspect-fig7-compact',
    })


def add_axes_mm(figure: mpl.figure.Figure, x: float, y: float, w: float, h: float) -> mpl.axes.Axes:
    return figure.add_axes((x / WIDTH_MM, y / HEIGHT_MM, w / WIDTH_MM, h / HEIGHT_MM))


def camera_panel(figure: mpl.figure.Figure, frame: np.ndarray, record: dict,
                 x: float, y: float, width: float) -> mpl.axes.Axes:
    """Place an uncropped image and readable metadata outside its field of view."""
    height = width * frame.shape[0] / frame.shape[1]
    axis = add_axes_mm(figure, x, y, width, height)
    axis.imshow(frame, interpolation='lanczos', aspect='equal')
    axis.set_xticks([])
    axis.set_yticks([])
    color = COLORS[record['sequence'] - 1]
    for spine in axis.spines.values():
        spine.set_color(color)
        spine.set_linewidth(0.9)
    # Badge remains inside the image; metadata has two lines below, without
    # covering the inspected structure or reducing its contrast.
    axis.text(0.03, 0.97, str(record['sequence']), transform=axis.transAxes,
              va='top', ha='left', fontsize=7.5, fontweight='bold', color='#111820',
              bbox={'facecolor': 'white', 'edgecolor': color, 'linewidth': 0.7, 'pad': 1.1})
    figure.text((x + width / 2) / WIDTH_MM, (y - 0.6) / HEIGHT_MM,
                camera_label(record, compact=width < 20),
                ha='center', va='top', fontsize=7.1, linespacing=1.03, color='#111820')
    return axis


def camera_label(record: dict, compact: bool = False) -> str:
    """Distinguish required completion from weighted background coverage."""
    time = f"{record['mission_time_s']:.0f} s"
    coverage = f"{record['cumulative_coverage'] * 100:.1f}%"
    if 'required_target_count' in record:
        separator = "\n" if compact else " · "
        return (f"{time}{separator}Req {record['accepted_required_count']}/"
                f"{record['required_target_count']}\nBg {coverage}")
    return f'{time}\n{coverage}'


def projection(axis: mpl.axes.Axes, arrays: dict, horizontal: int,
               active_indices: range, title: str,
               limits: dict | None = None) -> tuple[Line2D, Line2D]:
    """Keep exact path coordinates and equal metric scaling in both projections."""
    faces = arrays['display_triangles'][:, :, (horizontal, 2)]
    axis.add_collection(PolyCollection(faces, facecolor='#C9D0D7', edgecolor='#6F7983',
                                       linewidth=0.035, alpha=0.55, zorder=0))
    planned, executed, points = (arrays[key] for key in ('planned', 'executed', 'event_points'))
    planned_line, = axis.plot(planned[:, horizontal], planned[:, 2], color='#70777E',
                             linestyle=(0, (3, 2)), linewidth=0.82, alpha=0.92, zorder=7)
    executed_line, = axis.plot(executed[:, horizontal], executed[:, 2], color='#005F84',
                              linewidth=1.38, zorder=9)
    axis.scatter(executed[0, horizontal], executed[0, 2], marker='*', s=58,
                 facecolor='white', edgecolor='#111820', linewidth=0.72, zorder=28)
    active = set(active_indices)
    for index, (point, color) in enumerate(zip(points, COLORS[:len(points)], strict=True)):
        is_active = index in active
        axis.scatter(point[horizontal], point[2], s=57 if is_active else 26,
                     facecolor=color if is_active else 'white',
                     edgecolor='white' if is_active else '#8A939C',
                     linewidth=0.9 if is_active else 0.65,
                     alpha=1.0 if is_active else 0.72, zorder=29 if is_active else 25)
        # Active views retain their number; hollow inactive markers provide
        # context without duplicating ten tiny numbers in each projection.
        if is_active:
            axis.annotate(str(index + 1), xy=(point[horizontal], point[2]),
                          ha='center', va='center', fontsize=7.0, fontweight='bold',
                          color='#111820', zorder=32)
    axis.set_xlim((-40, 55) if horizontal == 0 else (-42, 48))
    axis.set_ylim(-65, 65)
    if limits is not None:
        axis.set_xlim(limits['x' if horizontal == 0 else 'y'])
        axis.set_ylim(limits['z'])
    axis.set_aspect('equal', adjustable='box')
    axis.set_title(title, fontsize=8.0, fontweight='bold', pad=5)
    axis.set_xlabel('Radial $x$ (m)' if horizontal == 0 else 'Along-track $y$ (m)', labelpad=2)
    axis.set_xticks([-40, 0, 40])
    axis.set_yticks([-60, -40, -20, 0, 20, 40, 60])
    axis.grid(True, color='#D7DDE2', linewidth=0.38, alpha=0.82)
    axis.set_axisbelow(True)
    axis.tick_params(direction='out', length=2.2, width=0.55, pad=1.5)
    for spine in axis.spines.values():
        spine.set_color('#7E8790')
        spine.set_linewidth(0.55)
    return planned_line, executed_line


def generate(output: Path, data: Path = DATA, font_dir: Path | None = None) -> dict:
    if font_dir is not None:
        for path in sorted(font_dir.glob('*.[tT][tT][fF]')):
            mpl.font_manager.fontManager.addfont(str(path))
    snapshot = json.loads((data / 'snapshot.json').read_text())
    assert sha(data / snapshot['arrays_file']) == snapshot['arrays_sha256']
    records = snapshot['camera_views']
    count = len(records)
    if count not in (9, 10, 12):
        raise ValueError('The approved compact layout supports nine, ten or twelve observations')
    assert [r['sequence'] for r in records] == list(range(1, count + 1))
    if snapshot.get('goal_mode') in ('required', 'hybrid'):
        assert snapshot['execution_audit_passed'] and snapshot['camera_audit_passed']
        assert all(r['credited'] for r in records)
        assert records[-1]['accepted_required_count'] == records[-1]['required_target_count']
        if snapshot['goal_mode'] == 'hybrid':
            assert records[-1]['cumulative_coverage'] + 1e-12 >= snapshot['goal_coverage']
    arrays = dict(np.load(data / snapshot['arrays_file'], allow_pickle=False))
    assert len(arrays['event_points']) == count
    frames = []
    for record in records:
        path = data / record['snapshot_image']
        assert sha(path) == record['snapshot_image_sha256']
        with Image.open(path) as image:
            frame = np.asarray(image.convert('RGB'))
        assert hashlib.sha256(frame.tobytes()).hexdigest() == record['snapshot_pixel_sha256']
        frames.append(frame)
        np.testing.assert_array_equal(arrays['executed'][record['trajectory_row_index']],
                                      record['executed_position_lvlh_m'])
    assert len(arrays['executed']) == snapshot['trajectory_rows']
    configure_style()
    figure = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4))
    camera_axes = []
    columns = 6 if count == 12 else 5
    width = 18.1 if count == 12 else CAMERA_WIDTH_MM
    camera_left = 56.8 if count == 12 else CAMERA_LEFT_MM
    row_pitch = CAMERA_ROW_PITCH_MM
    projection_scale = 0.60 if count == 12 else PROJECTION_SCALE
    column_pitch = width + CAMERA_GAP_MM
    for index, (frame, record) in enumerate(zip(frames, records, strict=True)):
        row, col = divmod(index, columns)
        x = camera_left + col * column_pitch
        image_height = width * frame.shape[0] / frame.shape[1]
        y = HEIGHT_MM - 1.0 - image_height - row * row_pitch
        camera_axes.append(camera_panel(figure, frame, record, x, y, width))

    # Shrink both projections at one physical scale. A narrow extra strip at
    # the right keeps marker 9 fully visible at its unchanged printed size.
    source_limits = snapshot.get('projection_limits_m',
                                 {'x': [-40, 55], 'y': [-42, 48], 'z': [-65, 65]})
    limits = {key: list(value) for key, value in source_limits.items()}
    projection_height = 46.8 * projection_scale
    mm_per_m = projection_height / (limits['z'][1] - limits['z'][0])
    limits['y'][1] += RIGHT_MARKER_PADDING_MM / mm_per_m
    xz_rect = [10.2 if count == 12 else 10.6, 13.5 if count == 12 else 11.0, (limits['x'][1] - limits['x'][0]) * mm_per_m, projection_height]
    yz_rect = [34.0 if count == 12 else 37.0, 13.5 if count == 12 else 11.0, (limits['y'][1] - limits['y'][0]) * mm_per_m, projection_height]
    xz = add_axes_mm(figure, *xz_rect)
    yz = add_axes_mm(figure, *yz_rect)
    planned_line, executed_line = projection(
        xz, arrays, 0, range(0, count, 2) if count == 12 else range(columns), '(a) $x$-$z$' if count == 12 else '(a) $x$-$z$ projection', limits)
    projection(yz, arrays, 1, range(1, count, 2) if count == 12 else range(columns, count), '(b) $y$-$z$' if count == 12 else '(b) $y$-$z$ projection', limits)
    xz.set_ylabel('Cross-track $z$ (m)', labelpad=2)
    # Identical vertical limits, ticks and scale allow one shared set of labels.
    yz.tick_params(labelleft=False)
    handles = (planned_line, executed_line,
               Line2D([0], [0], marker='*', markersize=7.5, markerfacecolor='white',
                      markeredgecolor='#111820', linewidth=0))
    key_cell_x = CAMERA_LEFT_MM + 4 * column_pitch
    if count == 9:
        figure.legend(handles, ('Planned', 'Executed', 'Start'), loc='upper left',
                      bbox_to_anchor=(key_cell_x / WIDTH_MM, 24.5 / HEIGHT_MM),
                      ncol=1, frameon=False, fontsize=7.2, handlelength=1.7,
                      columnspacing=1.0, borderpad=0.2, borderaxespad=0.0)
    else:
        figure.legend(handles, ('Planned', 'Executed', 'Start'), loc='lower center',
                      bbox_to_anchor=(31.0 / WIDTH_MM, 0.0), ncol=3, frameon=False,
                      fontsize=7.2, handlelength=1.7, columnspacing=1.0,
                      borderpad=0.2, borderaxespad=0.0)
    if 'minimum_body_clearance_m' in snapshot:
        margin = float(snapshot['minimum_body_clearance_m'])
        assert np.isfinite(margin) and margin >= 0.0
        margin_label = (f'Min. full 3-D\nbody margin\n{margin:+.2f} m' if count == 9
                        else f'Min. full 3-D body margin: {margin:+.2f} m')
    else:
        c2, c3 = (record['body_clearance_above_required_margin_m'] for record in records[1:3])
        margin_label = f'Full 3-D margin: $c_2={c2:+.2f}$ m; $c_3={c3:+.2f}$ m'
    figure.text((key_cell_x + width / 2) / WIDTH_MM if count == 9 else 115.0 / WIDTH_MM,
                8.7 / HEIGHT_MM if count == 9 else 1.7 / HEIGHT_MM,
                margin_label,
                ha='center', va='center', fontsize=7.0, color='#26313A')
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    # Trim only unused canvas below the nine-view composition; camera fields
    # of view and all plotted data stay intact. The ten-view footer needs it.
    blank_bottom_mm = 3.0 if count == 9 else 0.0
    export_bottom_px = blank_bottom_mm / 25.4 * figure.dpi
    outside = []
    for text in figure.findobj(mpl.text.Text):
        if not text.get_visible() or not text.get_text():
            continue
        box = text.get_window_extent(renderer)
        if box.x0 < -0.5 or box.y0 < export_bottom_px - 0.5 or box.x1 > figure.bbox.width + 0.5 or box.y1 > figure.bbox.height + 0.5:
            outside.append(text.get_text())
    assert not outside, f'Text outside canvas: {outside}'
    # Metadata must remain separate from plot labels and adjacent camera labels.
    metadata = [text for text in figure.texts if text.get_visible()]
    plot_labels = [text for axis in (xz, yz) for text in
                   (axis.title, axis.xaxis.label, axis.yaxis.label)
                   if text.get_visible() and text.get_text()]
    for i, text in enumerate(metadata):
        box = text.get_window_extent(renderer)
        for axis in camera_axes:
            assert not box.overlaps(axis.bbox), f'Metadata overlaps camera image: {text.get_text()}'
        for other in metadata[i+1:] + plot_labels:
            assert not box.overlaps(other.get_window_extent(renderer)), (
                f'Overlapping metadata: {text.get_text()} / {other.get_text()}')
    for axis, frame in zip(camera_axes, frames, strict=True):
        np.testing.assert_array_equal(np.asarray(axis.images[0].get_array()), frame)
    scales = []
    for axis, horizontal in ((xz, 0), (yz, 1)):
        for line, key in zip(axis.lines[:2], ('planned', 'executed'), strict=True):
            np.testing.assert_array_equal(line.get_xdata(), arrays[key][:, horizontal])
            np.testing.assert_array_equal(line.get_ydata(), arrays[key][:, 2])
        dx = np.linalg.norm(axis.transData.transform((1, 0)) - axis.transData.transform((0, 0)))
        dy = np.linalg.norm(axis.transData.transform((0, 1)) - axis.transData.transform((0, 0)))
        assert abs(dx - dy) < 1e-8, 'Spatial scaling must be equal'
        scales.append(dx)
        for marker in axis.collections[1:]:
            center = marker.get_offset_transform().transform(marker.get_offsets())[0]
            radius = (np.sqrt(marker.get_sizes()[0]) + marker.get_linewidths()[0]) * figure.dpi / 144
            assert (center[0] - radius >= axis.bbox.x0 and
                    center[0] + radius <= axis.bbox.x1 and
                    center[1] - radius >= axis.bbox.y0 and
                    center[1] + radius <= axis.bbox.y1), 'Clipped observation or start marker'
        for key in ('planned', 'executed', 'event_points'):
            points = arrays[key]
            assert np.all((points[:, horizontal] >= axis.get_xlim()[0]) &
                          (points[:, horizontal] <= axis.get_xlim()[1])), 'Clipped trajectory'
            assert np.all((points[:, 2] >= axis.get_ylim()[0]) &
                          (points[:, 2] <= axis.get_ylim()[1])), 'Clipped trajectory'
    assert abs(scales[0] - scales[1]) < 1e-8, 'Both projections must use the same spatial scale'
    output.mkdir(parents=True, exist_ok=True)
    export_box = Bbox.from_bounds(0, blank_bottom_mm / 25.4,
                                 WIDTH_MM / 25.4, (HEIGHT_MM - blank_bottom_mm) / 25.4)
    figure.savefig(output / f'{STEM}.svg', dpi=600, bbox_inches=export_box, pad_inches=0)
    figure.savefig(output / f'{STEM}.pdf', dpi=600, bbox_inches=export_box, pad_inches=0)
    figure.savefig(output / f'{STEM}.png', dpi=600, bbox_inches=export_box, pad_inches=0)
    plt.close(figure)
    report = {
        'status': 'passed', 'figure_mm': [WIDTH_MM, HEIGHT_MM - blank_bottom_mm],
        'layout_canvas_mm': [WIDTH_MM, HEIGHT_MM], 'blank_bottom_trim_mm': blank_bottom_mm,
        'camera_views': count, 'trajectory_rows': len(arrays['executed']),
        'image_pixels_unchanged': True, 'trajectory_coordinates_unchanged': True,
        'equal_spatial_scaling': True, 'text_within_canvas': True, 'markers_within_axes': True,
        'layout': f'Two shared-axis projections on the left; {columns} camera columns in two rows on the right; legend in the spare tenth cell when nine views are present',
        'camera_width_mm': width,
        'camera_column_gap_mm': CAMERA_GAP_MM,
        'camera_row_pitch_mm': row_pitch,
        'projection_spatial_scale_relative_to_original_74mm_layout': projection_scale,
        'projection_rectangles_mm': {'xz': xz_rect, 'yz': yz_rect},
        'right_marker_padding_mm': RIGHT_MARKER_PADDING_MM,
        'projection_view_limits_m': limits,
        'correspondence': ('Odd-numbered views highlighted in projection (a), even-numbered views in (b); camera rows remain chronological 1-6 and 7-12; inactive hollow markers retained' if count == 12 else f'Camera top row 1-{columns} matches projection (a); camera bottom row {columns+1}-{count} matches projection (b); inactive hollow markers retained'),
        'minimum_annotation_font_pt': 7.0,
        'snapshot_sha256': sha(data / 'snapshot.json'), 'script_sha256': sha(Path(__file__)),
        'output_sha256': {f'{STEM}.{ext}': sha(output / f'{STEM}.{ext}') for ext in ('svg', 'pdf', 'png')},
    }
    (output / 'compact_layout_manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'build/figure7_compact_preview')
    parser.add_argument('--snapshot-dir', type=Path, default=DATA)
    parser.add_argument('--font-dir', type=Path, help='Optional local Arial font directory')
    args = parser.parse_args()
    generate(args.output_dir, args.snapshot_dir, args.font_dir)
