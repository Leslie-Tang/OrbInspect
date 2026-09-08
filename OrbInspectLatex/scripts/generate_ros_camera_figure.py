#!/usr/bin/env python3
"""Render compact, double-column Figure 7 from the included frozen snapshot."""
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
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/historical_ros/figure7'
STEM = 'ros_key_camera_views_trajectory'
# Retain the approved observation identities, colors, paths and mesh treatment.
COLORS = ('#3B4CC0', '#526ED3', '#3E8ABF', '#20A486', '#5DC863',
          '#AADC32', '#DCE319', '#F4C430', '#F8961E', '#D1495B')
WIDTH_MM, HEIGHT_MM = 170.0, 74.0


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
                f"{record['mission_time_s']:.0f} s\n{record['cumulative_coverage'] * 100:.1f}%",
                ha='center', va='top', fontsize=7.1, linespacing=1.03, color='#111820')
    return axis


def projection(axis: mpl.axes.Axes, arrays: dict, horizontal: int,
               active_indices: range, title: str) -> tuple[Line2D, Line2D]:
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
    for index, (point, color) in enumerate(zip(points, COLORS, strict=True)):
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


def generate(output: Path) -> dict:
    snapshot = json.loads((DATA / 'snapshot.json').read_text())
    assert sha(DATA / snapshot['arrays_file']) == snapshot['arrays_sha256']
    records = snapshot['camera_views']
    assert [r['sequence'] for r in records] == list(range(1, 11))
    arrays = dict(np.load(DATA / snapshot['arrays_file'], allow_pickle=False))
    frames = []
    for record in records:
        path = DATA / record['snapshot_image']
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
    width = 17.8
    for start, left in ((0, 0.7), (5, 132.8)):
        for local in range(5):
            row, col = divmod(local, 2)
            x = left + col * 18.7 if local < 4 else left + 9.35
            y = 57.8 - row * 21.4
            camera_axes.append(camera_panel(figure, frames[start + local], records[start + local], x, y, width))

    # Both rectangles have the same mm-per-m scale: 34.2/95 = 32.4/90.
    xz = add_axes_mm(figure, 48.0, 19.4, 34.2, 46.8)
    yz = add_axes_mm(figure, 94.0, 19.4, 32.4, 46.8)
    planned_line, executed_line = projection(xz, arrays, 0, range(5), '(a) $x$-$z$ projection')
    projection(yz, arrays, 1, range(5, 10), '(b) $y$-$z$ projection')
    xz.set_ylabel('Cross-track $z$ (m)', labelpad=2)
    handles = (planned_line, executed_line,
               Line2D([0], [0], marker='*', markersize=7.5, markerfacecolor='white',
                      markeredgecolor='#111820', linewidth=0))
    figure.legend(handles, ('Planned', 'Executed', 'Start'), loc='lower center',
                  bbox_to_anchor=(0.515, 0.005), ncol=3, frameon=False, fontsize=7.2,
                  handlelength=1.7, columnspacing=1.0, borderpad=0.2)
    c2, c3 = (record['body_clearance_above_required_margin_m'] for record in records[1:3])
    assert (round(c2, 2), round(c3, 2)) == (11.36, 9.84)
    figure.text(0.515, 9.0 / HEIGHT_MM,
                f'Full 3-D margin: $c_2={c2:+.2f}$ m; $c_3={c3:+.2f}$ m',
                ha='center', va='center', fontsize=7.0, color='#26313A')
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    outside = []
    for text in figure.findobj(mpl.text.Text):
        if not text.get_visible() or not text.get_text():
            continue
        box = text.get_window_extent(renderer)
        if box.x0 < -0.5 or box.y0 < -0.5 or box.x1 > figure.bbox.width + 0.5 or box.y1 > figure.bbox.height + 0.5:
            outside.append(text.get_text())
    assert not outside, f'Text outside canvas: {outside}'
    for axis, frame in zip(camera_axes, frames, strict=True):
        np.testing.assert_array_equal(np.asarray(axis.images[0].get_array()), frame)
    for axis, horizontal in ((xz, 0), (yz, 1)):
        for line, key in zip(axis.lines[:2], ('planned', 'executed'), strict=True):
            np.testing.assert_array_equal(line.get_xdata(), arrays[key][:, horizontal])
            np.testing.assert_array_equal(line.get_ydata(), arrays[key][:, 2])
        dx = np.linalg.norm(axis.transData.transform((1, 0)) - axis.transData.transform((0, 0)))
        dy = np.linalg.norm(axis.transData.transform((0, 1)) - axis.transData.transform((0, 0)))
        assert abs(dx - dy) < 1e-8, 'Spatial scaling must be equal'
    output.mkdir(parents=True, exist_ok=True)
    for extension in ('svg', 'pdf', 'png'):
        figure.savefig(output / f'{STEM}.{extension}', dpi=600)
    plt.close(figure)
    report = {
        'status': 'passed', 'figure_mm': [WIDTH_MM, HEIGHT_MM],
        'camera_views': 10, 'trajectory_rows': len(arrays['executed']),
        'image_pixels_unchanged': True, 'trajectory_coordinates_unchanged': True,
        'equal_spatial_scaling': True, 'text_within_canvas': True,
        'layout': 'Two columns plus a centered fifth view on each side; two central projections',
        'correspondence': 'Matching observation numbers; active 1-5 left and 6-10 right; inactive hollow markers retained',
        'minimum_annotation_font_pt': 7.0,
        'snapshot_sha256': sha(DATA / 'snapshot.json'), 'script_sha256': sha(Path(__file__)),
        'output_sha256': {f'{STEM}.{ext}': sha(output / f'{STEM}.{ext}') for ext in ('svg', 'pdf', 'png')},
    }
    (output / 'compact_layout_manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'build/figure7_compact_preview')
    generate(parser.parse_args().output_dir)
