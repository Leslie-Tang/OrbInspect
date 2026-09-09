#!/usr/bin/env python3
"""Plot required-target ADP evidence using the established manuscript style.

Contract: retain the existing quantitative-panel dimensions and encodings;
show all-required success independently of resource costs on matched successes.
Input rows and all displayed statistics are retained in the figure manifest.
This is a Python-only extension of the existing IEEE figure workflow.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import generate_adp_future_figures as legacy


ROOT = Path(__file__).resolve().parents[2]
METHODS = ('incumbent', 'one_step_adp', 'seeded_local_search', 'adaptive_rollout_adp')
ADP, LOCAL = 'adaptive_rollout_adp', 'seeded_local_search'


def read_rows(path: Path) -> list[dict]:
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def success(row: dict) -> bool:
    return str(row['success']).lower() in ('true', '1')


def paired(rows: list[dict], split: str) -> list[tuple[dict, dict]]:
    groups = {
        method: {r['scenario_id']: r for r in rows
                 if r['split'] == split and r['method'] == method}
        for method in (ADP, LOCAL)
    }
    if groups[ADP].keys() != groups[LOCAL].keys():
        raise ValueError('ADP and local-search scenario sets differ')
    return [(groups[ADP][key], groups[LOCAL][key])
            for key in sorted(groups[ADP])
            if success(groups[ADP][key]) and success(groups[LOCAL][key])]


def interval(values, seed=60935) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if not len(values):
        return float('nan'), float('nan')
    rng = np.random.default_rng(seed)
    means = values[rng.integers(0, len(values), (10000, len(values)))].mean(axis=1)
    return tuple(float(x) for x in np.quantile(means, (0.025, 0.975)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    args = parser.parse_args()
    study = args.study.resolve()
    paper = ROOT / 'OrbInspectLatex' / 'figures' / 'required_target'
    paper.mkdir(parents=True, exist_ok=True)
    (study / 'figures').mkdir(exist_ok=True)
    source = study / 'raw' / 'scenario_results.csv'
    if not source.exists():
        source = study / 'raw' / 'heldout_results.csv'
    inventory = read_rows(source)
    frozen = json.loads((study / 'config_snapshot/freeze_manifest.json').read_text())
    primary = frozen['primary_profile']
    rows = [r for r in inventory if r['profile_id'] == primary]
    legacy._style()
    plt.rcParams['svg.fonttype'] = 'none'
    manifest = {'source': str(source.relative_to(ROOT)), 'primary_profile': primary,
                'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'style': 'existing IEEE manuscript Python style and panel dimensions',
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'bootstrap_seed': 60935, 'bootstrap_replicates': 10000,
                'cohorts': {}, 'generated_files': []}

    def save(fig, name, *_unused):
        paths = []
        for suffix in ('pdf', 'png', 'svg'):
            path = study / 'figures' / f'{name}.{suffix}'
            fig.savefig(path)
            shutil.copy2(path, paper / path.name)
            paths.append(path)
            manifest['generated_files'].append(str(path.relative_to(ROOT)))
        plt.close(fig)
        return paths

    legacy._save = save
    legacy.plot_rollout_architecture(study, ROOT / 'OrbInspectLatex', required_targets=True)

    for index, (split, color, marker) in enumerate((
        ('test', legacy.RED, 'o'), ('ood', legacy.PURPLE, 's'),
    )):
        pairs = paired(rows, split)
        if not pairs:
            raise ValueError(f'No jointly successful {split} pairs for a cost plot')
        adp = np.array([float(a['total_delta_v']) for a, b in pairs])
        local = np.array([float(b['total_delta_v']) for a, b in pairs])
        differences = np.array([float(a['graph_cost']) - float(b['graph_cost']) for a, b in pairs])
        lower, upper = interval(differences)
        manifest['cohorts'][split] = {
            'joint_success_n': len(pairs), 'joint_scenario_ids': [a['scenario_id'] for a, b in pairs],
            'mean_graph_cost_difference': float(differences.mean()),
            'bootstrap_95_ci': [lower, upper],
            'mean_delta_v_difference': float((adp - local).mean()),
            'delta_v_bootstrap_95_ci': interval(adp - local),
        }
        fig, ax = plt.subplots(figsize=(3.32, 2.50))
        lo, hi = min(adp.min(), local.min()) - .3, max(adp.max(), local.max()) + .3
        ax.plot((lo, hi), (lo, hi), '--', color=legacy.GREY, linewidth=.8)
        ax.scatter(local, adp, color=color, marker=marker, s=20, alpha=.84,
                   edgecolors=legacy.BLACK, linewidth=.35)
        ax.set(xlim=(lo, hi), ylim=(lo, hi), xlabel=r'Local-search $\Delta v$ (m/s)',
               ylabel=r'Rollout-ADP $\Delta v$ (m/s)')
        ax.set_aspect('equal', adjustable='box')
        ax.grid(color='#ECECEC', linewidth=.6)
        fig.tight_layout(pad=.35)
        save(fig, f'adp_heldout_performance_{"a" if index == 0 else "c"}')
        fig, ax = plt.subplots(figsize=(3.32, 2.50))
        ax.scatter(np.arange(1, len(pairs) + 1), np.sort(differences), color=color,
                   s=16, edgecolors=legacy.BLACK, linewidth=.25)
        ax.axhline(0, color=legacy.GREY, linestyle='--', linewidth=.8)
        ax.axhspan(lower, upper, color=legacy.ROSE, alpha=.55)
        ax.axhline(differences.mean(), color=legacy.RED, linewidth=1.4)
        ax.text(.03, .95, f'n = {len(pairs)}; mean {differences.mean():.2f}\n95% CI [{lower:.2f}, {upper:.2f}]',
                transform=ax.transAxes, ha='left', va='top', color=legacy.BLACK,
                bbox={'facecolor': 'white', 'edgecolor': 'none', 'alpha': .82})
        ax.set(xlabel=f'{"Test" if split == "test" else "Shifted"} complete pairs, ordered',
               ylabel=r'$J_{\mathrm{ADP}}-J_{\mathrm{local}}$ (cost units)')
        ax.grid(axis='y', color='#ECECEC', linewidth=.6)
        fig.tight_layout(pad=.35)
        save(fig, f'adp_heldout_performance_{"b" if index == 0 else "d"}')

    # Resource comparison uses the common-success intersection of all methods.
    groups = {method: {r['scenario_id']: r for r in rows
                      if r['split'] == 'test' and r['method'] == method}
              for method in METHODS}
    common = sorted(set.intersection(*[set(g) for g in groups.values()]))
    common = [key for key in common if all(success(groups[m][key]) for m in METHODS[1:])]
    if not common:
        raise ValueError('No common-success cases for the three completion-capable method resource panel')
    values = [[float(groups[m][key]['total_delta_v']) for key in common] for m in METHODS[1:]]
    means = np.array([np.mean(v) for v in values])
    intervals = np.array([interval(v) for v in values])
    fig, ax = plt.subplots(figsize=(3.32, 2.45))
    bars = ax.bar(np.arange(3), means,
                  yerr=np.vstack((means-intervals[:, 0], intervals[:, 1]-means)), capsize=3,
                  color=(legacy.PURPLE, legacy.BLUE, legacy.RED),
                  edgecolor=legacy.BLACK, linewidth=.55)
    for i, (bar, hatch, vals) in enumerate(zip(bars, ('..', '//', '\\\\', 'xx'), values)):
        bar.set_hatch(hatch)
        ax.scatter(i + np.linspace(-.12, .12, len(vals)), vals, s=7, color=legacy.BLACK, alpha=.28)
    ax.set_xticks(np.arange(3), ('ADP, d=1', 'Seeded local', 'ADP, d=3'))
    ax.set_ylabel(r'Test mission $\Delta v$ (m/s)')
    ax.grid(axis='y', color='#ECECEC', linewidth=.6)
    fig.tight_layout(pad=.35)
    save(fig, 'adp_ablation_safety_a')
    manifest['four_method_cost_n'] = len(common)

    fig, ax = plt.subplots(figsize=(3.32, 2.45))
    x, width = np.arange(4), .36
    for offset, split, color, hatch in ((-width/2, 'test', legacy.RED, ''),
                                      (width/2, 'ood', legacy.PURPLE, '//')):
        values = [np.mean([success(r) for r in rows if r['split'] == split and r['method'] == m])
                  for m in METHODS]
        ax.bar(x + offset, values, width, color=color, hatch=hatch,
               edgecolor=legacy.BLACK, linewidth=.5, label='Test' if split == 'test' else 'Shifted')
    ax.set_xticks(x, ('Incumbent', 'ADP, d=1', 'Seeded\nlocal', 'ADP, d=3'))
    ax.set(ylim=(0, 1.18), ylabel='All-required mission success')
    ax.legend(frameon=False, loc='upper center', ncol=2)
    ax.grid(axis='y', color='#ECECEC', linewidth=.6)
    fig.tight_layout(pad=.35)
    save(fig, 'adp_ablation_safety_b')

    for field, suffix, xlabel, ylabel in (
        ('min_clearance', 'c', 'Local minimum clearance above margin (m)', 'ADP minimum clearance above margin (m)'),
        ('peak_input', 'd', r'Local peak input (m/s$^2$)', r'ADP peak input (m/s$^2$)'),
    ):
        fig, ax = plt.subplots(figsize=(3.32, 2.45))
        for split, marker, color in (('test', 'o', legacy.RED), ('ood', 's', legacy.PURPLE)):
            pairs = paired(rows, split)
            ax.scatter([float(b[field]) for a, b in pairs], [float(a[field]) for a, b in pairs],
                       marker=marker, color=color, s=17, alpha=.78, edgecolors=legacy.BLACK,
                       linewidth=.25, label='Test' if split == 'test' else 'Shifted')
        lo, hi = min(ax.get_xlim()[0], ax.get_ylim()[0]), max(ax.get_xlim()[1], ax.get_ylim()[1])
        ax.plot((lo, hi), (lo, hi), '--', color=legacy.GREY, linewidth=.8)
        ax.axhline(0 if field == 'min_clearance' else .06,
                   color=legacy.RED if field == 'min_clearance' else legacy.ORANGE, linewidth=.9)
        ax.set(xlabel=xlabel, ylabel=ylabel)
        ax.legend(frameon=False, loc='upper right' if field == 'min_clearance' else 'upper left', fontsize=7.4)
        ax.grid(color='#ECECEC', linewidth=.6)
        fig.tight_layout(pad=.35)
        save(fig, f'adp_ablation_safety_{suffix}')

    path = study / 'figures' / 'required_target_figure_manifest.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    shutil.copy2(path, paper / path.name)
    print(json.dumps({'manifest': str(path), 'cohorts': manifest['cohorts'],
                      'four_method_cost_n': len(common)}, indent=2))


if __name__ == '__main__':
    main()
