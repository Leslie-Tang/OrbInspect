#!/usr/bin/env python3
"""Draw Figure 3 at its final column size without changing frozen evidence.

The three panels show cost, runtime and screening workload across depths 1--6.
Depth three is the frozen setting, not an inferred optimum. This script only
reads the included diagnostic CSV and its original reference manifest.
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
import numpy as np

from figure_palette import BLACK, GREY, SLATE, TEAL

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/depth_diagnostic/raw/validation_depth_results.csv'
REFERENCE = ROOT / 'figures/fig03_depth_tradeoff/required_target_depth_figure_manifest.json'
WIDTH_MM, HEIGHT_MM = 26.6, 40.0


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_series() -> tuple[list[dict], dict]:
    reference = json.loads(REFERENCE.read_text())
    assert sha(SOURCE) == reference['source_sha256'], 'Frozen depth CSV changed'
    with SOURCE.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    groups = {depth: [r for r in rows if int(r['adaptive_rollout_depth']) == depth] for depth in range(1, 7)}
    assert len(rows) == 72 and all(len(g) == 12 for g in groups.values())
    ids = {r['scenario_id'] for r in groups[1]}
    assert len(ids) == 12 and all({r['scenario_id'] for r in g} == ids for g in groups.values())
    assert all(r['split'] == 'validation' and r['method'] == 'adaptive_rollout_adp' for r in rows)
    common = sorted(set.intersection(*[{r['scenario_id'] for r in g if r['success'].lower() == 'true'}
                                       for g in groups.values()]))
    assert common == reference['common_completed_scenarios'] and len(common) == 9
    series = []
    for depth, group in groups.items():
        row = {'depth': depth,
               'mean_graph_cost': float(np.mean([float(r['graph_cost']) for r in group if r['scenario_id'] in common])),
               'median_time_s': float(np.median([float(r['online_time_s']) for r in group])),
               'mean_safety_evaluations': float(np.mean([float(r['safe_action_evaluations']) for r in group]))}
        for key, value in row.items():
            assert value == reference['per_depth'][depth - 1][key], (depth, key)
        series.append(row)
    return series, reference


def generate(output: Path) -> None:
    series, reference = verified_series()
    mpl.rcParams.update({
        'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 7.0, 'axes.labelsize': 7.2, 'xtick.labelsize': 7.0, 'ytick.labelsize': 7.0,
        'axes.spines.top': False, 'axes.spines.right': False, 'axes.linewidth': 0.5,
        'pdf.fonttype': 42, 'svg.fonttype': 'none', 'svg.hashsalt': 'orbinspect-depth-readable',
        'figure.facecolor': 'white', 'savefig.facecolor': 'white', 'axes.unicode_minus': False,
    })
    output.mkdir(parents=True, exist_ok=True)
    exported = []
    for field, ylabel, suffix, logarithmic in (
        ('mean_graph_cost', 'Mean graph cost, $J$', 'a', False),
        ('median_time_s', 'Median time (s)', 'b', True),
        ('mean_safety_evaluations', 'Mean screen count', 'c', True),
    ):
        x = np.asarray([r['depth'] for r in series])
        y = np.asarray([r[field] for r in series])
        figure = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4))
        axis = figure.add_axes((9.7 / WIDTH_MM, 9.0 / HEIGHT_MM,
                                15.8 / WIDTH_MM, 23.4 / HEIGHT_MM))
        line, = axis.plot(x, y, color=TEAL, linewidth=0.7, marker='o', markersize=2.5,
                          markerfacecolor='white', markeredgewidth=0.65, zorder=2)
        axis.scatter([3], [y[2]], color=SLATE, marker='s', s=12,
                     edgecolor=BLACK, linewidth=0.25, zorder=3)
        if logarithmic:
            axis.set_yscale('log')
        axis.set_xticks(x)
        axis.set_xlabel('Depth, $d$', labelpad=2.0)
        axis.set_ylabel(ylabel, labelpad=1.8, linespacing=1.0)
        axis.tick_params(axis='both', which='major', length=2.0, width=0.5, pad=1.2)
        axis.tick_params(axis='y', which='minor', length=1.0, width=0.3)
        axis.grid(axis='y', which='both', color='#ECECEC', linewidth=0.4)
        note = 'common complete\n$n=9$' if suffix == 'a' else 'post-selection\ndiagnostic'
        figure.text(0.62, 0.96, note, ha='center', va='top', color=GREY,
                    fontsize=6.5, linespacing=1.05)
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        off_axis = set()
        for coordinate in (axis.xaxis, axis.yaxis):
            low, high = coordinate.get_view_interval()
            for tick in coordinate.get_major_ticks() + coordinate.get_minor_ticks():
                if not low <= tick.get_loc() <= high:
                    off_axis.update((tick.label1, tick.label2))
        outside = []
        for text in figure.findobj(mpl.text.Text):
            if text in off_axis or not text.get_visible() or not text.get_text():
                continue
            # Off-range log ticks are intentionally not drawn by the axes.
            box = text.get_window_extent(renderer)
            if box.x1 < 0 or box.y1 < 0 or box.x0 > figure.bbox.width or box.y0 > figure.bbox.height:
                continue
            if box.x0 < -0.5 or box.y0 < -0.5 or box.x1 > figure.bbox.width + 0.5 or box.y1 > figure.bbox.height + 0.5:
                outside.append((text.get_text(), tuple(round(v, 2) for v in box.extents)))
        assert not outside, f'Clipped text in panel {suffix}: {outside}'
        np.testing.assert_array_equal(line.get_xdata(), x)
        np.testing.assert_array_equal(line.get_ydata(), y)
        for extension in ('svg', 'pdf', 'png'):
            path = output / f'adp_depth_tradeoff_{suffix}.{extension}'
            figure.savefig(path, dpi=600)
            exported.append(path)
        plt.close(figure)
    report = {
        'status': 'passed', 'source_sha256': sha(SOURCE), 'reference_sha256': sha(REFERENCE),
        'script_sha256': sha(Path(__file__)), 'palette_sha256': sha(Path(__file__).with_name('figure_palette.py')),
        'panel_mm': [WIDTH_MM, HEIGHT_MM], 'axis_label_font_pt': 7.2, 'tick_font_pt': 7.0,
        'note_font_pt': 6.5, 'depths': list(range(1, 7)), 'common_complete_n': 9,
        'runtime_and_screen_n': 12, 'all_statistics_match_reference': True, 'plotted_series': series,
        'outputs_sha256': {p.name: sha(p) for p in exported},
    }
    (output / 'readable_typography_manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'passed', 'panels': 3, 'font_pt': [7.0, 7.2], 'output': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'build/figure3_readable_preview')
    generate(parser.parse_args().output_dir)
