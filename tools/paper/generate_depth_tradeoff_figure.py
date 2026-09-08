#!/usr/bin/env python3
"""Generate the manuscript rollout-depth cost--computation sensitivity figure."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = (
    REPO_ROOT
    / 'data'
    / 'results'
)
PAPER_FIGURE_DIR = REPO_ROOT / 'OrbInspectLatex' / 'figures' / 'adp_future'
PAPER_DATA_DIR = REPO_ROOT / 'OrbInspectLatex' / 'data'

DEPTH_RUNS = {
    depth: f'adp_depth_corrected_postselection_d{depth}_20260905'
    for depth in range(1, 7)
}

RED = '#750014'
BLUE = '#587E92'
PURPLE = '#7F3F98'
GREY = '#6B7280'
LIGHT_GREY = '#D9DEE3'
BLACK = '#1E293B'


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _style() -> None:
    mpl.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 8.8,
        'axes.labelsize': 9.1,
        'xtick.labelsize': 8.3,
        'ytick.labelsize': 8.3,
        'figure.dpi': 160,
        'savefig.dpi': 600,
        'savefig.bbox': 'tight',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.linewidth': 0.7,
        'lines.linewidth': 1.25,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
        'axes.unicode_minus': False,
    })


def _summary_row(depth: int) -> dict[str, float | int]:
    path = RESULT_ROOT / DEPTH_RUNS[depth] / 'raw' / 'heldout_summary.csv'
    with path.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    row = next(
        item for item in rows
        if item['split'] == 'validation'
        and item['method'] == 'adaptive_rollout_adp'
    )
    return {
        'depth': depth,
        'mean_cost': float(row['mean_penalized_cost']),
        'median_time_s': float(row['median_online_time_s']),
        'mean_safety_screen_evaluations': float(row['mean_safe_action_evaluations']),
        'success_count': int(round(float(row['success_rate']) * int(row['n']))),
        'scenario_count': int(row['n']),
        'source': str(path.relative_to(REPO_ROOT)),
    }


def _save(fig: plt.Figure, name: str) -> list[Path]:
    PAPER_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for suffix in ('pdf', 'png', 'svg'):
        path = PAPER_FIGURE_DIR / f'{name}.{suffix}'
        fig.savefig(path)
        paths.append(path)
    plt.close(fig)
    return paths


def _plot_series(
    depths: list[int],
    values: list[float],
    ylabel: str,
    name: str,
    log_scale: bool = False,
) -> list[Path]:
    fig, ax = plt.subplots(figsize=(2.18, 2.45))
    ax.plot(depths, values, color=BLUE, marker='o', markersize=4.6,
            markerfacecolor='white', markeredgewidth=1.05, zorder=2)
    selected = depths.index(3)
    ax.scatter([3], [values[selected]], color=RED, marker='s', s=38,
               edgecolor=BLACK, linewidth=0.35, zorder=3)
    if log_scale:
        ax.set_yscale('log')
    ax.set_xticks(depths)
    ax.set_xlabel('Rollout depth, $d$')
    ax.set_ylabel(ylabel)
    ax.grid(axis='y', which='both', color='#ECECEC', linewidth=0.6)
    ax.text(0.98, 0.04, 'post-selection diagnostic', transform=ax.transAxes,
            ha='right', va='bottom', color=GREY, fontsize=7.0)
    fig.tight_layout(pad=0.35)
    return _save(fig, name)


def main() -> None:
    _style()
    rows = [_summary_row(depth) for depth in sorted(DEPTH_RUNS)]
    depths = [int(row['depth']) for row in rows]
    generated = []
    generated.extend(_plot_series(
        depths, [float(row['mean_cost']) for row in rows],
        'Mean graph cost, $J$ (cost units)', 'adp_depth_tradeoff_a',
    ))
    generated.extend(_plot_series(
        depths, [float(row['median_time_s']) for row in rows],
        'Median online time (s, log scale)', 'adp_depth_tradeoff_b', True,
    ))
    generated.extend(_plot_series(
        depths, [float(row['mean_safety_screen_evaluations']) for row in rows],
        'Mean safety-screen evaluations (log scale)', 'adp_depth_tradeoff_c', True,
    ))

    PAPER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    source_table = PAPER_DATA_DIR / 'adp_depth_sensitivity_corrected_20260905.csv'
    with source_table.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        'artifact_id': 'fig-adp-depth-sensitivity',
        'source_table': str(source_table.relative_to(REPO_ROOT)),
        'source_files': [row['source'] for row in rows],
        'script': str(Path(__file__).relative_to(REPO_ROOT)),
        'script_sha256': _sha256(Path(__file__)),
        'generated_files': [str(path.relative_to(REPO_ROOT)) for path in generated],
        'caption_claim': (
            'On the corrected validation graph, mean cost decreases with '
            'deeper lookahead while platform-specific time and safety-screen '
            'evaluations increase; depth three is the frozen policy setting, '
            'not a choice made from this post-selection sweep.'
        ),
        'limitations': [
            'All depths are post-selection, validation-only diagnostic evidence.',
            'The sweep did not select depth three or alter the frozen primary comparison.',
            'Wall-clock time is environment-sensitive and is not a real-time benchmark.',
        ],
    }
    manifest_path = PAPER_FIGURE_DIR / 'adp_depth_tradeoff_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
