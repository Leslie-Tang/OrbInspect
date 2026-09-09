#!/usr/bin/env python3
"""Render Figure 6 from frozen trajectories, without planning or propagation.

The same illustrative test case, route samples, required targets, projection,
palette and display faces are retained. Native panel widths match the LaTeX
inclusion widths so all labels print at the shared eight-point size.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from figure_palette import BLACK, GREEN, GREY, LIGHT_GREY, ORANGE, PURPLE, TEAL
from figure_typography import COLUMN_WIDTH_PT, TEXT_PT, register_fonts

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/confirmation'
ADP, LOCAL = 'adaptive_rollout_adp', 'seeded_local_search'
STYLES = ((ADP, TEAL, 'o', '-', 'Rollout ADP'),
          (LOCAL, PURPLE, 's', '--', 'Seeded local'))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(name: str) -> list[dict]:
    with (DATA / 'raw' / name).open(newline='') as stream:
        return list(csv.DictReader(stream))


def load_evidence() -> dict:
    """Verify archived inputs and each route's completion and final totals."""
    provenance = json.loads((DATA / 'figure6/provenance.json').read_text())
    for name, expected in provenance['frozen_inputs_sha256'].items():
        assert sha(DATA / name) == expected, f'Frozen input changed: {name}'
    mesh_path = DATA / 'figure6/display_mesh.npz'
    assert sha(mesh_path) == provenance['display_mesh_sha256']
    case = json.loads((DATA / 'raw/representative_case_manifest.json').read_text())
    graph = json.loads((DATA / 'raw/hcw_graph.json').read_text())
    config = json.loads((DATA / 'config_snapshot/base_experiment_config.json').read_text())
    trajectories, progress = rows('representative_case_trajectory.csv'), rows('representative_case_progress.csv')
    targets = np.asarray([[float(r[f'position_{axis}']) for axis in 'xyz']
                          for r in rows('target_positions.csv') if r['target_id'] in case['required_target_ids']])
    assert len(targets) == len(case['required_target_ids']) == 9
    coords, endpoints, traces = {}, {}, {}
    for method, *_ in STYLES:
        selected = case['methods'][method]
        route = selected['route_node_ids'].split(';')
        coords[method] = np.asarray([[float(r[f'r{axis}']) for axis in 'xyz']
                                    for r in trajectories if r['method'] == method])
        endpoints[method] = np.asarray([graph['node_positions'][graph['node_ids'].index(node)] for node in route])
        traces[method] = [r for r in progress if r['method'] == method]
        assert [r['candidate_id'] for r in traces[method][1:]] == route
        assert [int(r['action']) for r in traces[method]] == list(range(len(route) + 1))
        assert float(traces[method][-1]['required_coverage']) == 1.0
        for field, archived in (('cumulative_delta_v', 'total_delta_v'), ('cumulative_graph_cost', 'graph_cost')):
            np.testing.assert_allclose(float(traces[method][-1][field]), float(selected[archived]), rtol=1e-10, atol=1e-10)
    with np.load(mesh_path) as data:
        triangles = data['triangles'].copy()
    return dict(case=case, provenance=provenance, coords=coords, endpoints=endpoints,
                traces=traces, targets=targets, initial=config['initial_state'][:3], triangles=triangles)


def style() -> None:
    mpl.rcParams.update({
        'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': TEXT_PT, 'axes.labelsize': TEXT_PT, 'axes.titlesize': TEXT_PT,
        'xtick.labelsize': TEXT_PT, 'ytick.labelsize': TEXT_PT, 'legend.fontsize': TEXT_PT,
        'axes.spines.top': False, 'axes.spines.right': False, 'axes.unicode_minus': False,
        'axes.linewidth': .7 * .614, 'lines.linewidth': 1.15 * .614,
        'figure.facecolor': 'white', 'text.color': BLACK,
        'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
        'svg.hashsalt': 'orbinspect-trajectory-uniform-type', 'savefig.dpi': 600,
        'savefig.bbox': None,
    })


def route_panel(evidence: dict):
    width, height = .675 * COLUMN_WIDTH_PT, 142.1
    fig = plt.figure(figsize=(width / 72, height / 72))
    ax = fig.add_axes((6/width, 18/height, 130/width, 108/height), projection='3d')
    scale = .795
    ax.add_collection3d(Poly3DCollection(evidence['triangles'], facecolor=LIGHT_GREY, edgecolor='none', alpha=.10))
    for method, color, _, line, label in STYLES:
        points = evidence['coords'][method]
        artist, = ax.plot(*points.T, color=color, linestyle=line, linewidth=1.15*scale, label=label)
        np.testing.assert_array_equal(np.asarray(artist.get_data_3d()).T, points)
        ax.scatter(*evidence['endpoints'][method].T, color=color, s=10*scale**2, depthshade=False)
    targets = evidence['targets']
    ax.scatter(*targets.T, marker='D', s=9*scale**2, facecolors='none', edgecolors=ORANGE,
               linewidths=.5*scale, depthshade=False, label='Required samples')
    ax.scatter(*evidence['initial'], marker='*', s=48*scale**2, color=GREEN,
               edgecolor=BLACK, linewidth=.3*scale, label='Initial state')
    points = np.vstack([*evidence['coords'].values(), targets])
    center = (points.min(axis=0) + points.max(axis=0)) / 2
    radius = max(points.max(axis=0) - points.min(axis=0)) / 2
    for setter, value in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), center):
        setter(value - radius, value + radius)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel('$x$ (m)', labelpad=-4)
    ax.set_ylabel('$y$ (m)', labelpad=-4)
    ax.set_zlabel('')
    ax.text2D(1.19, .52, '$z$ (m)', transform=ax.transAxes, rotation=90, ha='center', va='center')
    ax.tick_params(axis='both', which='major', labelsize=TEXT_PT, pad=-1.5)
    # Retain every grid plane; label alternate horizontal ticks to avoid
    # collisions at eight points in the unchanged oblique camera view.
    ax.set_xticks([-40, -20, 0, 20, 40], labels=['-40', '', '0', '', '40'])
    ax.set_yticks([-40, -20, 0, 20, 40, 60], labels=['-40', '', '0', '', '40', ''])
    ax.set_zticks([-60, -40, -20, 0, 20, 40])
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis._axinfo['grid']['linewidth'] = .8 * scale
    ax.view_init(elev=24, azim=-56)
    # One shared method legend leaves the small progress panels unobstructed.
    fig.legend(*ax.get_legend_handles_labels(), frameon=False, loc='upper center',
               bbox_to_anchor=(.5, 1.015), ncol=2, handlelength=1.1,
               handletextpad=.35, columnspacing=.7, labelspacing=.25, borderpad=.1)
    return fig


def progress_panel(evidence: dict, suffix: str):
    width, height = .435 * COLUMN_WIDTH_PT, 112.9
    fig = plt.figure(figsize=(width / 72, height / 72))
    ax = fig.add_axes((31/width, 27/height, 70/width, 76/height))
    field = 'required_coverage' if suffix == 'b' else 'cumulative_delta_v'
    factor = 100 if suffix == 'b' else 1
    for method, color, marker, line, label in STYLES:
        trace = evidence['traces'][method]
        x = np.asarray([int(r['action']) for r in trace])
        y = np.asarray([float(r[field])*factor for r in trace])
        artist, = ax.plot(x, y, marker=marker, markersize=3.2*.614, color=color, linestyle=line, label=label)
        np.testing.assert_array_equal(artist.get_xdata(), x)
        np.testing.assert_array_equal(artist.get_ydata(), y)
    if suffix == 'b':
        goal = ax.axhline(100, color=GREY, linestyle=':', linewidth=.9*.614, label='Required goal')
        ax.set_ylim(0, 110)
        ax.set_yticks([0, 20, 40, 60, 80, 100])
        ax.legend(handles=[goal], frameon=False, loc='lower left', bbox_to_anchor=(0, 1.01),
                  handlelength=1.1, handletextpad=.35, borderaxespad=0, borderpad=0)
    else:
        ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
    ax.set_xticks([0, 2.5, 5, 7.5])
    ax.set_xlabel('Executed SOOA count', labelpad=2)
    ax.xaxis.set_label_coords((width/2 - 31)/70, -.15)
    ylabel = 'Required-target completion (%)' if suffix == 'b' else r'Cumulative $\Delta v$ (m/s)'
    # Center the long ordinate label on the canvas, retaining the compact height.
    fig.text(8/width, .5, ylabel, rotation=90, ha='center', va='center')
    ax.tick_params(length=2, width=.5, pad=1.2)
    ax.grid(color='#ECECEC', linewidth=.6*.614)
    return fig


def generate(output: Path, font_dir: Path | None = None) -> None:
    register_fonts(font_dir)
    style()
    evidence = load_evidence()
    output.mkdir(parents=True, exist_ok=True)
    exported, panels = {}, {}
    for suffix in 'abc':
        fig = route_panel(evidence) if suffix == 'a' else progress_panel(evidence, suffix)
        fig.canvas.draw()
        panels[suffix] = {'width_pt': fig.get_figwidth()*72, 'height_pt': fig.get_figheight()*72,
                          'text_size_pt': TEXT_PT}
        for extension in ('svg', 'pdf', 'png'):
            path = output / f'adp_representative_trajectory_{suffix}.{extension}'
            fig.savefig(path, bbox_inches=None)
            exported[path.name] = sha(path)
        plt.close(fig)
    manifest = {
        'status': 'passed', 'scenario_id': evidence['case']['scenario_id'],
        'selection_rule': evidence['case']['selection_rule'], 'panels': panels,
        'camera': {'elevation_deg': 24, 'azimuth_deg': -56},
        'shared_method_legend': 'panel a', 'input_provenance': evidence['provenance'],
        'trajectory_samples': {method: len(points) for method, points in evidence['coords'].items()},
        'required_target_ids': evidence['case']['required_target_ids'],
        'plotted_progress': evidence['traces'], 'frozen_final_totals_match': True,
        'generator_sha256': sha(Path(__file__)),
        'palette_sha256': sha(Path(__file__).with_name('figure_palette.py')),
        'typography_sha256': sha(Path(__file__).with_name('figure_typography.py')),
        'outputs_sha256': exported,
    }
    (output / 'uniform_typography_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'status': 'passed', 'panels': 3, 'font_pt': TEXT_PT, 'output': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'build/figure6_uniform_preview')
    parser.add_argument('--font-dir', type=Path, help='Optional local Arial font directory')
    args = parser.parse_args()
    generate(args.output_dir, args.font_dir)
