#!/usr/bin/env python3
"""Generate the frozen ROS closed-loop evidence figure and provenance."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import shutil

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / 'data/results/ros_closed_loop_test_frozen_20260811'
RUN_PREFIX = ROOT / 'data/results/ros_closed_loop_test_frozen_20260811__test_002__'
METHODS = ('adaptive_rollout_adp', 'local_search')
LABELS = {'adaptive_rollout_adp': 'Rollout ADP', 'local_search': 'Local search'}
COLORS = {'adaptive_rollout_adp': '#0077BB', 'local_search': '#EE7733'}


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read one CSV as dictionaries."""
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def values(rows: list[dict[str, str]], key: str) -> np.ndarray:
    """Extract one floating-point column."""
    return np.asarray([float(row[key]) for row in rows], dtype=float)


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def style() -> None:
    """Apply compact IEEE-compatible figure styling."""
    mpl.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 7.6,
        'axes.labelsize': 8.0,
        'axes.titlesize': 8.2,
        'legend.fontsize': 7.2,
        'xtick.labelsize': 7.2,
        'ytick.labelsize': 7.2,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })


def panel(ax: mpl.axes.Axes, label: str) -> None:
    """Add a panel label."""
    ax.text(-0.13, 1.04, label, transform=ax.transAxes,
            fontweight='bold', fontsize=8.6)


def main() -> None:
    """Generate PDF/PNG figures and a source-hash manifest."""
    style()
    run_dirs = {method: Path(f'{RUN_PREFIX}{method}') for method in METHODS}
    trajectories = {
        method: read_csv(run_dirs[method] / 'raw/trajectory.csv')
        for method in METHODS
    }
    safety = {
        method: read_csv(run_dirs[method] / 'raw/safety.csv')
        for method in METHODS
    }
    controls = {
        method: read_csv(run_dirs[method] / 'raw/control.csv')
        for method in METHODS
    }
    aggregate = read_csv(CAMPAIGN / 'raw/closed_loop_results.csv')

    fig, axes = plt.subplots(2, 2, figsize=(7.15, 5.15))
    ax = axes[0, 0]
    for method in METHODS:
        rows = trajectories[method]
        color = COLORS[method]
        ax.plot(values(rows, 'planned_ry'), values(rows, 'planned_rz'),
                color=color, linestyle='--', linewidth=0.9, alpha=0.8)
        ax.plot(values(rows, 'ry'), values(rows, 'rz'), color=color,
                linewidth=1.1, label=LABELS[method])
    ax.set_xlabel('LVLH along-track $y$ [m]')
    ax.set_ylabel('LVLH cross-track $z$ [m]')
    ax.set_title('Test 002: planned (dashed) and executed')
    ax.grid(True, color='#E7E7E7', linewidth=0.45)
    ax.legend(frameon=False, loc='best')
    panel(ax, '(a)')

    ax = axes[0, 1]
    for method in METHODS:
        rows = trajectories[method]
        ax.plot(values(rows, 'time'), values(rows, 'position_tracking_error_norm'),
                color=COLORS[method], label=LABELS[method])
    ax.axhline(0.5, color='#555555', linestyle='--', linewidth=0.8,
               label='credit threshold')
    ax.set_xlabel('Simulated time [s]')
    ax.set_ylabel('Position error [m]')
    ax.set_yscale('log')
    ax.set_title('Closed-loop tracking')
    ax.grid(True, color='#E7E7E7', linewidth=0.45)
    ax.legend(frameon=True, facecolor='white', edgecolor='#CCCCCC',
              loc='lower right')
    panel(ax, '(b)')

    ax = axes[1, 0]
    for method in METHODS:
        rows = safety[method]
        ax.plot(values(rows, 'time'), values(rows, 'clearance'),
                color=COLORS[method], label=f"{LABELS[method]} clearance")
    ax.axhline(0.0, color='#555555', linestyle='--', linewidth=0.8)
    ax.set_xlabel('Simulated time [s]')
    ax.set_ylabel('Online proxy clearance [m]')
    ax.set_title('Safety-filter time history')
    ax.grid(True, color='#E7E7E7', linewidth=0.45)
    twin = ax.twinx()
    for method in METHODS:
        rows = controls[method]
        twin.plot(values(rows, 'time'), values(rows, 'acceleration_norm'),
                  color=COLORS[method], linewidth=0.55, alpha=0.32)
    twin.axhline(0.06, color='#AA3377', linestyle=':', linewidth=0.8)
    twin.set_ylabel('Acceleration [m/s$^2$]')
    ax.legend(frameon=True, facecolor='white', edgecolor='#CCCCCC',
              loc='lower right')
    panel(ax, '(c)')

    by_scenario: dict[str, dict[str, dict[str, str]]] = {}
    for row in aggregate:
        by_scenario.setdefault(row['scenario_id'], {})[row['method']] = row
    local = np.asarray([
        float(pair['local_search']['cumulative_delta_v'])
        for pair in by_scenario.values()
    ])
    adp = np.asarray([
        float(pair['adaptive_rollout_adp']['cumulative_delta_v'])
        for pair in by_scenario.values()
    ])
    ax = axes[1, 1]
    lower = min(local.min(), adp.min()) - 0.4
    upper = max(local.max(), adp.max()) + 0.4
    ax.plot([lower, upper], [lower, upper], color='#777777',
            linestyle='--', linewidth=0.8)
    ax.scatter(local, adp, s=19, color='#0077BB', edgecolor='#111111',
               linewidth=0.3, alpha=0.85)
    ax.set_xlim(lower, upper)
    ax.set_ylim(lower, upper)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel('Local-search realized $\\Delta v$ [m/s]')
    ax.set_ylabel('Rollout-ADP realized $\\Delta v$ [m/s]')
    ax.set_title('Frozen test pairs ($n=30$)')
    ax.grid(True, color='#E7E7E7', linewidth=0.45)
    ax.text(0.04, 0.96, 'mean difference: -1.679 m/s\n95% CI: [-2.237, -1.173]',
            transform=ax.transAxes, ha='left', va='top', fontsize=7.2,
            bbox={'facecolor': 'white', 'edgecolor': '#CCCCCC', 'pad': 2})
    panel(ax, '(d)')

    fig.tight_layout(pad=0.8)
    manuscript_dir = ROOT / 'OrbInspectLatex/figures'
    evidence_dir = CAMPAIGN / 'figures'
    manuscript_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    pdf = manuscript_dir / 'ros_closed_loop_evidence.pdf'
    png = manuscript_dir / 'ros_closed_loop_evidence.png'
    fig.savefig(pdf, bbox_inches='tight')
    fig.savefig(png, dpi=600, bbox_inches='tight')
    plt.close(fig)
    shutil.copy2(pdf, evidence_dir / pdf.name)
    shutil.copy2(png, evidence_dir / png.name)

    sources = [CAMPAIGN / 'summary.json', CAMPAIGN / 'raw/closed_loop_results.csv']
    for method in METHODS:
        for name in ('trajectory.csv', 'safety.csv', 'control.csv'):
            sources.append(run_dirs[method] / 'raw' / name)
    manifest = {
        'schema_version': 'orbinspect-ros-figure/v1',
        'illustrative_scenario': 'test_002',
        'selection_status': 'predeclared representative rosbag scenario',
        'sources_sha256': {
            str(path.relative_to(ROOT)): sha256(path) for path in sources
        },
        'script_sha256': sha256(Path(__file__)),
        'outputs_sha256': {pdf.name: sha256(pdf), png.name: sha256(png)},
    }
    (evidence_dir / 'ros_closed_loop_evidence_manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n'
    )


if __name__ == '__main__':
    main()
