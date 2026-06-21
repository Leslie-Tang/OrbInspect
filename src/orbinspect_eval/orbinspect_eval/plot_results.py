"""Plot helpers for OrbInspect CSV log outputs."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
from matplotlib import pyplot as plt  # noqa: E402


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV file as dictionaries."""
    with path.open('r', newline='') as csv_file:
        return list(csv.DictReader(csv_file))


def generate_figures(result_dir: Path) -> list[Path]:
    """Generate Phase 4 trajectory and control figures."""
    raw_dir = result_dir / 'raw'
    figures_dir = result_dir / 'figures'
    figures_dir.mkdir(parents=True, exist_ok=True)

    generated = []
    trajectory_rows = read_csv_rows(raw_dir / 'trajectory.csv')
    control_rows = read_csv_rows(raw_dir / 'control.csv')

    if trajectory_rows:
        generated.append(_plot_trajectory_3d(trajectory_rows, figures_dir))
    if control_rows:
        generated.append(_plot_control_effort(control_rows, figures_dir))
    return generated


def _plot_trajectory_3d(rows: list[dict[str, str]], figures_dir: Path) -> Path:
    path = figures_dir / 'trajectory_3d.png'
    rx = [float(row['rx']) for row in rows]
    ry = [float(row['ry']) for row in rows]
    rz = [float(row['rz']) for row in rows]

    figure = plt.figure(figsize=(7, 5))
    axis = figure.add_subplot(111, projection='3d')
    axis.plot(rx, ry, rz, color='tab:blue', linewidth=1.5)
    axis.scatter(rx[0], ry[0], rz[0], color='tab:green', label='start')
    axis.scatter(rx[-1], ry[-1], rz[-1], color='tab:red', label='end')
    axis.set_xlabel('rx [m]')
    axis.set_ylabel('ry [m]')
    axis.set_zlabel('rz [m]')
    axis.set_title('Chaser LVLH trajectory')
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path


def _plot_control_effort(rows: list[dict[str, str]], figures_dir: Path) -> Path:
    path = figures_dir / 'control_effort_over_time.png'
    time = [float(row['time']) for row in rows]
    effort = [float(row['control_norm']) for row in rows]
    cumulative_delta_v = [float(row['cumulative_delta_v']) for row in rows]

    figure, axis = plt.subplots(figsize=(7, 4))
    axis.plot(time, effort, label='control norm', color='tab:orange')
    axis.set_xlabel('time [s]')
    axis.set_ylabel('acceleration [m/s^2]')
    axis.grid(True, alpha=0.3)
    twin = axis.twinx()
    twin.plot(time, cumulative_delta_v, label='cumulative delta-v', color='tab:blue')
    twin.set_ylabel('delta-v [m/s]')
    axis.set_title('Control effort over time')
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path
