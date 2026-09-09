"""Method comparison plotting helpers."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use('Agg')
from matplotlib import pyplot as plt  # noqa: E402


def plot_method_comparison(rows: list[dict[str, object]], path: Path) -> Path:
    """Save a method comparison bar chart."""
    methods = [str(row['method']) for row in rows]
    success_rates = [float(row['success_rate']) for row in rows]
    coverage = [float(row['mean_coverage']) for row in rows]

    figure, axis = plt.subplots(figsize=(8, 4))
    positions = range(len(methods))
    axis.bar([pos - 0.18 for pos in positions], success_rates, width=0.36, label='success')
    axis.bar([pos + 0.18 for pos in positions], coverage, width=0.36, label='coverage')
    axis.set_xticks(list(positions))
    axis.set_xticklabels(methods, rotation=20, ha='right')
    axis.set_ylim(0.0, 1.0)
    axis.set_ylabel('ratio')
    axis.grid(True, axis='y', alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path
