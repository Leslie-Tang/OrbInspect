"""Create standalone frozen-ADP validation figures from archived CSV files."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402


plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['svg.fonttype'] = 'none'
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['font.size'] = 7
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['axes.spines.right'] = False
plt.rcParams['axes.spines.top'] = False
plt.rcParams['legend.frameon'] = False

ADP_COLOR = '#B64342'
BASELINE_COLOR = '#0F4D92'
ROLLOUT_COLOR = '#42949E'
NEUTRAL_COLOR = '#767676'
GRID_COLOR = '#D8D8D8'


def plot_paired_penalized_cost(decision_dir: Path) -> tuple[Path, ...]:
    """Plot scenario-wise penalized-cost differences against local search."""
    rows = _read_csv(
        Path(decision_dir) / 'raw' / 'full_graph_paired_costs.csv'
    )
    x = [int(row['sequence']) for row in rows]
    values = [float(row['paired_penalized_cost_difference']) for row in rows]
    fig, ax = plt.subplots(figsize=(3.5, 2.35))
    ax.bar(x, values, width=0.68, color=ADP_COLOR, edgecolor='white', linewidth=0.4)
    ax.axhline(0.0, color=NEUTRAL_COLOR, linestyle='--', linewidth=0.9)
    ax.set_xlabel('Validation scenario')
    ax.set_ylabel(r'Penalized cost difference, ADP $-$ L+S')
    ax.set_xticks(x)
    ax.grid(axis='y', color=GRID_COLOR, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    return _save_figure(
        fig,
        Path(decision_dir) / 'figures' / 'validation_paired_penalized_cost',
    )


def plot_quality_latency_tradeoff(decision_dir: Path) -> tuple[Path, ...]:
    """Plot full-graph validation quality against online decision latency."""
    rows = _read_csv(Path(decision_dir) / 'raw' / 'full_graph_methods.csv')
    display = {
        'frozen_adp': ('Frozen ADP', ADP_COLOR, 'o'),
        'incumbent': ('Incumbent', NEUTRAL_COLOR, 's'),
        'rollout': ('Rollout', ROLLOUT_COLOR, '^'),
        'local_search': ('L+S', BASELINE_COLOR, 'D'),
    }
    offsets = {
        'frozen_adp': (-4, 5, 'right'),
        'incumbent': (4, 5, 'left'),
        'rollout': (-5, 8, 'right'),
        'local_search': (5, -2, 'left'),
    }
    fig, ax = plt.subplots(figsize=(3.5, 2.55))
    for row in rows:
        method = row['method']
        if method not in display:
            continue
        label, color, marker = display[method]
        latency = float(row['median_online_time_s'])
        cost = float(row['mean_penalized_cost'])
        success = float(row['success_rate'])
        ax.scatter(
            latency,
            cost,
            s=42,
            marker=marker,
            color=color,
            edgecolor='white',
            linewidth=0.5,
            zorder=3,
        )
        dx, dy, horizontal_alignment = offsets[method]
        ax.annotate(
            f'{label} ({success:.0%})',
            (latency, cost),
            xytext=(dx, dy),
            textcoords='offset points',
            fontsize=6.5,
            ha=horizontal_alignment,
        )
    ax.set_xscale('log')
    ax.set_xlim(3.0e-4, 1.2e-1)
    ax.set_ylim(128.0, 250.0)
    ax.set_xlabel('Median online planning time (s)')
    ax.set_ylabel('Mean penalized graph cost')
    ax.grid(color=GRID_COLOR, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    return _save_figure(
        fig,
        Path(decision_dir) / 'figures' / 'validation_quality_latency',
    )


def plot_validation_gate(decision_dir: Path) -> tuple[Path, ...]:
    """Plot paired bootstrap intervals for every validation candidate."""
    rows = _read_csv(Path(decision_dir) / 'raw' / 'validation_candidates.csv')
    labels = [
        f"{row['label']}\n{row['regime']}"
        for row in rows
    ]
    estimates = [
        float(row['mean_paired_penalized_cost_difference']) for row in rows
    ]
    lower = [float(row['paired_cost_ci_lower']) for row in rows]
    upper = [float(row['paired_cost_ci_upper']) for row in rows]
    y = list(reversed(range(len(rows))))
    fig, ax = plt.subplots(figsize=(3.5, 2.75))
    for position, estimate, low, high in zip(y, estimates, lower, upper):
        ax.plot([low, high], [position, position], color=ADP_COLOR, linewidth=1.4)
        ax.plot(estimate, position, 'o', color=ADP_COLOR, markersize=4.5)
    ax.axvline(0.0, color=NEUTRAL_COLOR, linestyle='--', linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel(r'Mean paired penalized cost, ADP $-$ L+S (95% CI)')
    ax.grid(axis='x', color=GRID_COLOR, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    return _save_figure(
        fig,
        Path(decision_dir) / 'figures' / 'validation_gate',
    )


def plot_all(decision_dir: Path) -> tuple[Path, ...]:
    """Generate every standalone figure from the same archived decision data."""
    outputs = []
    outputs.extend(plot_paired_penalized_cost(decision_dir))
    outputs.extend(plot_quality_latency_tradeoff(decision_dir))
    outputs.extend(plot_validation_gate(decision_dir))
    return tuple(outputs)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def _save_figure(fig: plt.Figure, path: Path) -> tuple[Path, ...]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.7)
    outputs = tuple(path.with_suffix(f'.{suffix}') for suffix in ('svg', 'pdf', 'png'))
    fig.savefig(outputs[0], bbox_inches='tight')
    fig.savefig(outputs[1], bbox_inches='tight')
    fig.savefig(outputs[2], dpi=600, bbox_inches='tight')
    plt.close(fig)
    return outputs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decision_dir', type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    for output in plot_all(args.decision_dir):
        print(output)


if __name__ == '__main__':
    main()
