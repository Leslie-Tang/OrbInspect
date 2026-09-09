#!/usr/bin/env python3
"""Render independent panels for LaTeX assembly of Figures 4/5.

Contract: four panels per figure, frozen cohorts and unchanged statistics;
test/shift rows in Fig. 4 and performance/safety rows in Fig. 5. Use the
shared framework palette, explicit units, embedded PDF fonts and editable SVG text.
LaTeX owns panel lettering and subcaptions; no labels are burned into exports.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.legend_handler import HandlerTuple
from matplotlib.patches import Patch
import numpy as np
from figure_palette import (ALERT, BLACK, GREY, ONE_STEP_COLOR, ORANGE,
                            PURPLE, TEAL, TEAL_LIGHT)

ROOT = Path(__file__).resolve().parents[1]
WIDTH_PT = 240 * 72 / 72.27
PERFORMANCE_PANEL_FRACTION = .49
SAFETY_PANEL_FRACTIONS = (.46, .54)
METHODS = ('incumbent', 'one_step_adp', 'seeded_local_search', 'adaptive_rollout_adp')
ADP, LOCAL = METHODS[3], METHODS[2]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def success(row: dict) -> bool:
    return str(row['success']).lower() in ('true', '1')


def interval(values: list | np.ndarray) -> list[float]:
    """Retain the original seed and 10,000 paired-bootstrap resamples."""
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(60935)
    means = values[rng.integers(0, len(values), (10000, len(values)))].mean(axis=1)
    return np.quantile(means, (.025, .975)).tolist()


def load_evidence() -> dict:
    """Read immutable scenario results and check original cohort/statistic identity."""
    source = ROOT / 'data/confirmation/raw/scenario_results.csv'
    reference = json.loads((ROOT / 'data/confirmation/figure_reference.json').read_text())
    assert sha(source) == reference['source_sha256'], 'Frozen CSV hash changed'
    with source.open(newline='') as handle:
        rows = [r for r in csv.DictReader(handle) if r['profile_id'] == reference['primary_profile']]
    out = {'source': str(source.relative_to(ROOT)), 'source_sha256': sha(source),
           'primary_profile': reference['primary_profile'], 'bootstrap_seed': 60935,
           'bootstrap_replicates': 10000, 'cohorts': {}, 'success': {}}
    for split in ('test', 'ood'):
        groups = {m: {r['scenario_id']: r for r in rows if r['split'] == split and r['method'] == m}
                  for m in METHODS}
        assert all(groups[m].keys() == groups[ADP].keys() for m in METHODS)
        ids = [k for k in sorted(groups[ADP]) if success(groups[ADP][k]) and success(groups[LOCAL][k])]
        pairs = []
        for key in ids:
            a, b = groups[ADP][key], groups[LOCAL][key]
            pairs.append({'scenario_id': key, **{
                method: {field: float(row[field]) for field in ('total_delta_v', 'graph_cost', 'min_clearance', 'peak_input')}
                for method, row in (('adp', a), ('local', b))}})
        differences = [p['adp']['graph_cost'] - p['local']['graph_cost'] for p in pairs]
        dv_differences = [p['adp']['total_delta_v'] - p['local']['total_delta_v'] for p in pairs]
        record = {'joint_success_n': len(ids), 'joint_scenario_ids': ids,
                  'mean_graph_cost_difference': float(np.mean(differences)),
                  'bootstrap_95_ci': interval(differences),
                  'mean_delta_v_difference': float(np.mean(dv_differences)),
                  'delta_v_bootstrap_95_ci': interval(dv_differences), 'pairs': pairs}
        for key, expected in reference['cohorts'][split].items():
            assert record[key] == expected, f'Original statistic changed: {split}/{key}'
        out['cohorts'][split] = record
        out['success'][split] = {m: {'complete': sum(success(r) for r in groups[m].values()),
                                     'total': len(groups[m])} for m in METHODS}
        if split == 'test':
            common = [k for k in sorted(groups[ADP]) if all(success(groups[m][k]) for m in METHODS[1:])]
            assert len(common) == reference['four_method_cost_n']
            out['matched_effort'] = {'n': len(common), 'scenario_ids': common, 'methods': {}}
            for m in METHODS[1:]:
                values = [float(groups[m][key]['total_delta_v']) for key in common]
                out['matched_effort']['methods'][m] = {'values': values, 'mean': float(np.mean(values)),
                                                       'bootstrap_95_ci': interval(values)}
    return out


def style() -> None:
    plt.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
                        'font.size': 9, 'axes.labelsize': 9, 'axes.titlesize': 9,
                        'xtick.labelsize': 9, 'ytick.labelsize': 9, 'legend.fontsize': 9,
                        'axes.spines.top': False, 'axes.spines.right': False,
                        'axes.linewidth': .65, 'axes.unicode_minus': False,
                        'xtick.major.size': 2, 'ytick.major.size': 2,
                        'xtick.major.pad': 2, 'ytick.major.pad': 2,
                        'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
                        'savefig.dpi': 600, 'savefig.bbox': None,
                        'figure.facecolor': 'white', 'text.color': BLACK,
                        'axes.labelcolor': BLACK, 'xtick.color': BLACK, 'ytick.color': BLACK})


def canvas(height_pt: float, safety: bool = False):
    """Fixed canvas makes PDF, SVG and PNG agree at the final printed width."""
    fig = plt.figure(figsize=(WIDTH_PT / 72, height_pt / 72))
    # Explicit physical margins keep labels and panels consistent across exports.
    if safety:
        rectangles = [(35, 168, 77, 80), (157, 168, 77, 80),
                      (35, 39, 77, 80), (157, 39, 77, 80)]
    else:
        rectangles = [(35, 164, 77, 77), (157, 164, 77, 77),
                      (35, 42, 77, 77), (157, 42, 77, 77)]
    axes = [fig.add_axes((x/WIDTH_PT, y/height_pt, w/WIDTH_PT, h/height_pt))
            for x, y, w, h in rectangles]
    for ax in axes:
        ax.set_axisbelow(True)
        ax.grid(color='#ECECEC', linewidth=.5)
        ax.xaxis.labelpad = 3
        ax.yaxis.labelpad = 3
    return fig, axes


def label(ax, value: str) -> None:
    ax.set_title(value, loc='left', pad=5, fontweight='normal')


def plot_performance(evidence: dict):
    """Keep test/shift comparisons and every ordered difference visible."""
    fig, axes = canvas(266)
    for index, (split, color, marker, name) in enumerate((
            ('test', TEAL, 'o', 'Test'), ('ood', PURPLE, 's', 'Shifted'))):
        cohort = evidence['cohorts'][split]
        a, b = axes[2*index:2*index+2]
        adp = np.array([p['adp']['total_delta_v'] for p in cohort['pairs']])
        local = np.array([p['local']['total_delta_v'] for p in cohort['pairs']])
        lo, hi = min(adp.min(), local.min()) - .3, max(adp.max(), local.max()) + .3
        a.plot((lo, hi), (lo, hi), '--', color=GREY, linewidth=.7)
        a.scatter(local, adp, color=color, marker=marker, s=9, alpha=.84,
                  edgecolors=BLACK, linewidth=.3)
        a.set(xlim=(lo, hi), ylim=(lo, hi), xticks=[14, 15, 16], yticks=[14, 15, 16],
              xlabel=r'Local $\Delta v$ (m/s)', ylabel=r'ADP $\Delta v$ (m/s)')
        a.set_aspect('equal', adjustable='box')
        label(a, f'({"a" if index == 0 else "c"}) {name}: effort')
        diffs = np.sort([p['adp']['graph_cost'] - p['local']['graph_cost'] for p in cohort['pairs']])
        b.scatter(np.arange(1, len(diffs)+1), diffs, color=color, s=6,
                  edgecolors=BLACK, linewidth=.25)
        b.axhline(0, color=GREY, linestyle='--', linewidth=.7)
        b.axhspan(*cohort['bootstrap_95_ci'], color=TEAL_LIGHT, alpha=.55)
        b.axhline(cohort['mean_graph_cost_difference'], color=TEAL, linewidth=1)
        b.grid(False, axis='x')
        b.set(xlabel='Ordered pairs', ylabel=r'$J_{\mathrm{ADP}}-J_{\mathrm{local}}$',
              xticks=([1, 20, 40] if split == 'test' else [1, 4, 8]), yticks=[-15, -5, 5])
        label(b, f'({"b" if index == 0 else "d"}) {name}: cost')
    return fig


def plot_safety(evidence: dict):
    """Keep original success denominators and matched safety/effort samples."""
    fig, axes = canvas(278, safety=True)
    a, b, c, d = axes
    effort = evidence['matched_effort']['methods']
    records = [effort[m] for m in METHODS[1:]]
    means = np.array([r['mean'] for r in records])
    ci = np.array([r['bootstrap_95_ci'] for r in records])
    bars = a.bar(np.arange(3), means, yerr=np.vstack((means-ci[:,0], ci[:,1]-means)),
                 capsize=2, color=(ONE_STEP_COLOR, PURPLE, TEAL), edgecolor=BLACK, linewidth=.5,
                 error_kw={'elinewidth': .7, 'capthick': .7})
    for i, (bar, hatch, record) in enumerate(zip(bars, ('..', '//', '\\\\'), records)):
        bar.set_hatch(hatch)
        a.scatter(i+np.linspace(-.12,.12,len(record['values'])), record['values'], s=3.5,
                  color=BLACK, alpha=.28)
    a.set(xticks=np.arange(3), xticklabels=[r'$d=1$', 'Local', r'$d=3$'],
          ylabel=r'$\Delta v$ (m/s)', yticks=[0, 5, 10, 15])
    label(a, '(a) Matched effort')
    a.grid(False, axis='x')
    x, width = np.arange(4), .36
    for offset, split, color, hatch in ((-width/2,'test',TEAL,''), (width/2,'ood',PURPLE,'//')):
        values = [evidence['success'][split][m]['complete']/evidence['success'][split][m]['total'] for m in METHODS]
        b.barh(x+offset, values, width, color=color, hatch=hatch, edgecolor=BLACK, linewidth=.5)
    b.set(yticks=x, yticklabels=['Base', r'$d=1$', 'Local', r'$d=3$'],
          xlim=(0,1.05), xticks=[0,.5,1])
    b.invert_yaxis()
    label(b, '(b) Task success')
    b.grid(False, axis='y')
    for ax, field in ((c, 'min_clearance'), (d, 'peak_input')):
        for split, marker, color in (('test', 'o', TEAL), ('ood', 's', PURPLE)):
            pairs = evidence['cohorts'][split]['pairs']
            ax.scatter([p['local'][field] for p in pairs], [p['adp'][field] for p in pairs],
                       marker=marker, color=color, s=8, alpha=.78, edgecolors=BLACK, linewidth=.25)
        lo, hi = min(ax.get_xlim()[0],ax.get_ylim()[0]), max(ax.get_xlim()[1],ax.get_ylim()[1])
        ax.plot((lo,hi),(lo,hi),'--', color=GREY, linewidth=.7)
        ax.axhline(0 if field == 'min_clearance' else .06,
                   color=ALERT if field == 'min_clearance' else ORANGE, linewidth=.8)
    c.set(xlabel='Local (m)', ylabel='ADP (m)', xticks=[0,1.5,3], yticks=[0,1.5,3])
    label(c, '(c) Clearance')
    # Same SI values, fewer tick marks; no transformation of the plotted data.
    d.set(xlabel=r'Local (m/s$^2$)', ylabel=r'ADP (m/s$^2$)',
          xticks=[.058,.060], yticks=[.058,.060], xlim=(.0568,.0604), ylim=(.0568,.0604))
    label(d, '(d) Peak input')
    add_split_legend(fig, (.5, .515))
    return fig


def add_split_legend(fig, anchor: tuple[float, float]) -> None:
    """Share the exact bar hatches and point markers across safety panels."""
    handles = [(Patch(facecolor=color, hatch=hatch, edgecolor=BLACK, linewidth=.5),
                Line2D([], [], linestyle='none', marker=marker, markersize=3,
                       markerfacecolor=color, markeredgecolor=BLACK, markeredgewidth=.3))
               for color, hatch, marker in ((TEAL, '', 'o'), (PURPLE, '//', 's'))]
    fig.legend(handles, ['Test', 'Shifted'], handler_map={tuple: HandlerTuple(ndivide=None)},
               loc='center', bbox_to_anchor=anchor, ncol=2, frameon=False,
               handlelength=2.1, handletextpad=.4, columnspacing=1.4)


def separate_panel(evidence: dict, builder, index: int):
    """Re-render one native vector axes, retaining its data and 77-point width.

    Remove the other axes before export, rather than cropping a composite image.
    Unequal outer widths in Figure 5 accommodate the SI decimal tick labels;
    the plotted axes remain equal in size and the font stays at nine points.
    """
    assert index in range(4)
    fig = builder(evidence)
    selected = fig.axes[index]
    for ax in list(fig.axes):
        if ax is not selected:
            fig.delaxes(ax)
    for legend in list(fig.legends):
        legend.remove()
    selected.set_title('', loc='left')
    safety = builder is plot_safety
    fraction = SAFETY_PANEL_FRACTIONS[index % 2] if safety else PERFORMANCE_PANEL_FRACTION
    width = WIDTH_PT * fraction
    height = (101 if index < 2 else 116) if safety else 112
    left = (31 if index % 2 == 0 else 46) if safety else 35
    bottom = (17 if index < 2 else 32) if safety else 31
    axis_height = 80 if safety else 77
    fig.set_size_inches(width / 72, height / 72, forward=True)
    selected.set_position((left/width, bottom/height, 77/width, axis_height/height))
    return fig


def split_legend():
    """Unnumbered vector legend strip included separately by LaTeX."""
    fig = plt.figure(figsize=(WIDTH_PT / 72, 18 / 72))
    add_split_legend(fig, (.5, .5))
    return fig


def export(fig, destination: Path, stem: str) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    for suffix in ('svg', 'pdf', 'png'):
        fig.savefig(destination/f'{stem}.{suffix}', bbox_inches=None)
    report = {'width_pt': float(fig.get_figwidth()*72), 'height_pt': float(fig.get_figheight()*72),
              'axes': len(fig.axes), 'text_size_pt': 9}
    plt.close(fig)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=ROOT/'figures')
    args = parser.parse_args()
    evidence = load_evidence()
    style()
    outputs = []
    for number, directory, stem, builder in (
        (4, 'fig04_heldout_performance', 'adp_heldout_performance', plot_performance),
        (5, 'fig05_ablation_safety', 'adp_ablation_safety', plot_safety)):
        destination = args.output_root/directory
        reports = {}
        for index, letter in enumerate('abcd'):
            report = export(separate_panel(evidence, builder, index), destination, f'{stem}_{letter}')
            reports[letter] = {'stem': f'{stem}_{letter}', **report}
        if number == 5:
            reports['legend'] = {'stem': f'{stem}_legend',
                                 **export(split_legend(), destination, f'{stem}_legend')}
        manifest = {'number': number, 'layout': 'LaTeX subfloat; single-column 2x2',
                    'panel_labels': 'LaTeX-generated; absent from image exports', 'panels': reports,
                    'generator_sha256': sha(Path(__file__)),
                    'palette_sha256': sha(Path(__file__).with_name('figure_palette.py')),
                    'evidence': evidence}
        (destination/'single_column_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        outputs.append({'figure': number, 'panels': reports})
    print(json.dumps(outputs, indent=2))


if __name__ == '__main__':
    main()
