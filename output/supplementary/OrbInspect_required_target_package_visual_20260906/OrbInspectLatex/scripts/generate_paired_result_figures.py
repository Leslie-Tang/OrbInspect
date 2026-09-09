#!/usr/bin/env python3
"""Generate publication figures for the current paired sequence study.

The script reads only the saved current-schema study records.  It writes vector
PDFs for the manuscript, high-resolution PNG previews, and a provenance manifest
that links each figure to its source files and transformation script.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


INCUMBENT = "set_cover_cw_tour"
LOCAL = "safe_graph_adp_local_search"
BLUE = "#0077BB"
ORANGE = "#EE7733"
GREY = "#777777"
LIGHT_GREY = "#D4D4D4"
BLACK = "#111111"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _as_float(rows: list[dict[str, str]], key: str) -> np.ndarray:
    return np.asarray([float(row[key]) for row in rows], dtype=float)


def _as_int(rows: list[dict[str, str]], key: str) -> np.ndarray:
    return np.asarray([int(float(row[key])) for row in rows], dtype=int)


def _style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8.2,
            "axes.labelsize": 8.5,
            "axes.titlesize": 8.7,
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "legend.fontsize": 8.0,
            "axes.linewidth": 0.7,
            "lines.linewidth": 1.0,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "figure.dpi": 150,
            "savefig.dpi": 600,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.unicode_minus": False,
        }
    )


def _panel_label(ax: mpl.axes.Axes, label: str) -> None:
    ax.text(
        -0.16,
        1.05,
        label,
        transform=ax.transAxes,
        fontsize=9.2,
        fontweight="bold",
        ha="left",
        va="bottom",
    )


def _parity_panel(
    ax: mpl.axes.Axes,
    incumbent: np.ndarray,
    local: np.ndarray,
    axis_label: str,
    mean_difference: float,
    ci: tuple[float, float],
) -> None:
    lower = min(float(incumbent.min()), float(local.min()))
    upper = max(float(incumbent.max()), float(local.max()))
    padding = max(0.08 * (upper - lower), 0.08)
    limits = (lower - padding, upper + padding)

    ax.plot(limits, limits, color=GREY, linestyle=(0, (3, 2)), linewidth=0.9, zorder=1)
    ax.scatter(
        incumbent,
        local,
        s=24,
        marker="o",
        facecolor=BLUE,
        edgecolor=BLACK,
        linewidth=0.35,
        alpha=0.88,
        zorder=2,
    )
    mean_x = float(incumbent.mean())
    mean_y = float(local.mean())
    ax.scatter(
        [mean_x],
        [mean_y],
        s=43,
        marker="D",
        facecolor=ORANGE,
        edgecolor=BLACK,
        linewidth=0.45,
        zorder=3,
    )
    ax.annotate(
        "mean",
        (mean_x, mean_y),
        xytext=(5, -8),
        textcoords="offset points",
        ha="left",
        va="top",
        fontsize=8.0,
        color=BLACK,
    )
    ax.set_xlim(*limits)
    ax.set_ylim(*limits)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(f"Two-stage incumbent {axis_label}")
    ax.set_ylabel(f"Sequence improvement {axis_label}")
    ax.grid(True, color="#E8E8E8", linewidth=0.45, zorder=0)
    ax.text(
        0.04,
        0.96,
        "Mean paired difference\n"
        f"{mean_difference:.3f}; 95% CI [{ci[0]:.3f}, {ci[1]:.3f}]",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.0,
        linespacing=1.2,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": LIGHT_GREY},
    )


def _save_figure(fig: mpl.figure.Figure, stem: str, paper_dir: Path, result_dir: Path) -> None:
    metadata = {"Creator": "OrbInspect paired-study figure generator", "CreationDate": None}
    pdf_path = paper_dir / f"{stem}.pdf"
    png_path = paper_dir / f"{stem}.png"
    fig.savefig(pdf_path, format="pdf", bbox_inches="tight", pad_inches=0.02, metadata=metadata)
    fig.savefig(png_path, format="png", bbox_inches="tight", pad_inches=0.02, facecolor="white")
    shutil.copyfile(pdf_path, result_dir / pdf_path.name)
    shutil.copyfile(png_path, result_dir / png_path.name)


def _plot_performance(
    paired: list[dict[str, str]],
    methods: dict[str, list[dict[str, str]]],
    summary: dict[str, Any],
    paper_dir: Path,
    result_dir: Path,
) -> None:
    incumbent_dv = _as_float(paired, "incumbent_total_delta_v")
    local_dv = _as_float(paired, "local_total_delta_v")
    incumbent_cost = _as_float(paired, "incumbent_total_dynamic_cost")
    local_cost = _as_float(paired, "local_total_dynamic_cost")
    incumbent_actions = _as_int(methods[INCUMBENT], "selected_viewpoint_count")
    local_actions = _as_int(methods[LOCAL], "selected_viewpoint_count")

    dv_summary = summary["summary"]["delta_v"]
    cost_summary = summary["summary"]["dynamic_cost"]
    dv_ci = tuple(float(value) for value in dv_summary["bootstrap_95_percent_ci_for_mean"])
    cost_ci = tuple(float(value) for value in cost_summary["bootstrap_95_percent_ci_for_mean"])

    fig, axes = plt.subplots(1, 3, figsize=(7.05, 2.55), constrained_layout=True)
    _parity_panel(
        axes[0],
        incumbent_dv,
        local_dv,
        r"$\Delta v$ (m s$^{-1}$)",
        float(dv_summary["mean_difference"]),
        dv_ci,
    )
    _panel_label(axes[0], "A")

    _parity_panel(
        axes[1],
        incumbent_cost,
        local_cost,
        r"graph cost $J$",
        float(cost_summary["mean_difference"]),
        cost_ci,
    )
    _panel_label(axes[1], "B")

    ax = axes[2]
    transitions, counts = np.unique(
        np.column_stack([incumbent_actions, local_actions]), axis=0, return_counts=True
    )
    for (incumbent, local), count in zip(transitions, counts):
        ax.plot(
            [0, 1],
            [incumbent, local],
            color="#AFAFAF",
            linewidth=0.7 + 0.11 * int(count),
            alpha=0.85,
            zorder=1,
        )
        ax.scatter(
            [0],
            [incumbent],
            s=22 + 1.3 * int(count),
            marker="o",
            facecolor="white",
            edgecolor=GREY,
            linewidth=0.8,
            zorder=2,
        )
        ax.scatter(
            [1],
            [local],
            s=24 + 1.3 * int(count),
            marker="D",
            facecolor=BLUE,
            edgecolor=BLACK,
            linewidth=0.35,
            alpha=0.9,
            zorder=3,
        )
        label_x = 0.62 if incumbent == local else 0.38
        label_y = incumbent + label_x * (local - incumbent)
        ax.annotate(
            f"n={int(count)}",
            (label_x, label_y),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8.0,
            color="#555555",
        )
    means = [float(incumbent_actions.mean()), float(local_actions.mean())]
    ax.plot([0, 1], means, color=ORANGE, linewidth=1.5, zorder=4)
    ax.scatter([0, 1], means, s=45, marker="s", facecolor=ORANGE, edgecolor=BLACK, linewidth=0.45, zorder=5)
    for x_value, mean in zip([0, 1], means):
        ax.annotate(
            f"mean {mean:.1f}",
            (x_value, mean),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8.0,
        )
    ax.set_xlim(-0.25, 1.25)
    ax.set_ylim(8.5, 13.5)
    ax.set_xticks([0, 1], ["Two-stage\nincumbent", "Sequence\nimprovement"])
    ax.set_yticks(np.arange(9, 14, 1))
    ax.set_ylabel("Selected SOOAs (count)")
    ax.grid(axis="y", color="#E8E8E8", linewidth=0.45, zorder=0)
    _panel_label(ax, "C")
    _save_figure(fig, "paired_performance", paper_dir, result_dir)
    plt.close(fig)


def _plot_safety(
    methods: dict[str, list[dict[str, str]]], paper_dir: Path, result_dir: Path
) -> None:
    incumbent = methods[INCUMBENT]
    local = methods[LOCAL]
    scenarios = np.arange(1, len(incumbent) + 1)
    incumbent_clearance = _as_float(incumbent, "min_clearance")
    local_clearance = _as_float(local, "min_clearance")
    incumbent_input = _as_float(incumbent, "peak_requested_input")
    local_input = _as_float(local, "peak_requested_input")

    fig, axes = plt.subplots(1, 2, figsize=(7.05, 2.35), constrained_layout=True)
    marker_size = 23
    offset = 0.12

    ax = axes[0]
    ax.axhline(0.0, color=ORANGE, linestyle=(0, (4, 2)), linewidth=1.0, label="Required minimum")
    ax.scatter(
        scenarios - offset,
        incumbent_clearance,
        s=marker_size,
        marker="o",
        facecolor="white",
        edgecolor=GREY,
        linewidth=0.8,
        label="Two-stage incumbent",
        zorder=2,
    )
    ax.scatter(
        scenarios + offset,
        local_clearance,
        s=marker_size,
        marker="D",
        facecolor=BLUE,
        edgecolor=BLACK,
        linewidth=0.35,
        label="Sequence improvement",
        zorder=3,
    )
    ax.set_xlim(0.3, len(scenarios) + 0.7)
    ax.set_ylim(-0.005, 0.19)
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Minimum excess mesh clearance (m)")
    ax.grid(axis="y", color="#E8E8E8", linewidth=0.45, zorder=0)
    ax.legend(
        frameon=False,
        loc="center right",
        bbox_to_anchor=(0.99, 0.52),
        ncol=1,
        handletextpad=0.35,
        borderpad=0.15,
    )
    _panel_label(ax, "A")

    ax = axes[1]
    ax.axhline(0.060, color=ORANGE, linestyle=(0, (4, 2)), linewidth=1.0, label=r"Limit: 0.060 m s$^{-2}$")
    ax.scatter(
        scenarios - offset,
        incumbent_input,
        s=marker_size,
        marker="o",
        facecolor="white",
        edgecolor=GREY,
        linewidth=0.8,
        label="Two-stage incumbent",
        zorder=2,
    )
    ax.scatter(
        scenarios + offset,
        local_input,
        s=marker_size,
        marker="D",
        facecolor=BLUE,
        edgecolor=BLACK,
        linewidth=0.35,
        label="Sequence improvement",
        zorder=3,
    )
    ax.set_xlim(0.3, len(scenarios) + 0.7)
    ax.set_ylim(0.0, 0.063)
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.set_yticks([0.00, 0.02, 0.04, 0.06])
    ax.set_xlabel("Scenario")
    ax.set_ylabel(r"Peak requested input (m s$^{-2}$)")
    ax.grid(axis="y", color="#E8E8E8", linewidth=0.45, zorder=0)
    ax.legend(frameon=False, loc="lower right", handletextpad=0.35, borderpad=0.15)
    _panel_label(ax, "B")
    _save_figure(fig, "paired_safety_audit", paper_dir, result_dir)
    plt.close(fig)


def _write_manifest(
    repo_root: Path,
    study_dir: Path,
    paper_dir: Path,
    result_dir: Path,
    pair_count: int,
) -> None:
    script_path = Path(__file__).resolve()
    source_files = [
        study_dir / "raw" / "paired_results.csv",
        study_dir / "raw" / "method_results.csv",
        study_dir / "summary.json",
        study_dir / "config_snapshot" / "result_manifest.json",
    ]
    artifact_files = [
        paper_dir / "paired_performance.pdf",
        paper_dir / "paired_performance.png",
        paper_dir / "paired_safety_audit.pdf",
        paper_dir / "paired_safety_audit.png",
    ]
    relative = lambda path: path.resolve().relative_to(repo_root.resolve()).as_posix()
    manifest = {
        "figure_schema_version": "orbinspect-paper-figures/v1",
        "study_schema_version": "paired-sequence-improvement/v1",
        "pair_count": pair_count,
        "source_files": {relative(path): _sha256(path) for path in source_files},
        "transformation": {"script": relative(script_path), "sha256": _sha256(script_path)},
        "artifacts": {relative(path): _sha256(path) for path in artifact_files},
        "figure_table_trace": [
            {
                "artifact_id": "fig:paired-performance",
                "source_data": {
                    "dataset_id": "paper_sequence_study_20260807",
                    "files": [
                        relative(study_dir / "raw" / "paired_results.csv"),
                        relative(study_dir / "raw" / "method_results.csv"),
                        relative(study_dir / "summary.json"),
                    ],
                },
                "transformation": {"script": relative(script_path), "sha256": _sha256(script_path)},
                "caption_claim": (
                    "All 20 paired outcomes favor sequence improvement in delta-v and graph cost, "
                    "and the improved sequences use fewer SOOAs on average."
                ),
                "supported_manuscript_claims": [
                    {
                        "claim": (
                            "Sequence improvement lowered graph cost and delta-v in all 20 scenarios "
                            "and reduced mean selected SOOAs from 11.4 to 10.0."
                        ),
                        "locator": "Results, Paired Success and Paired Effect Estimates",
                    }
                ],
                "limitations": [
                    "The 20 Latin-hypercube initial states are a designed stress set, not an operational probability sample.",
                    "The comparison is conditional on the fixed mesh-derived candidate graph and common success; all 20 scenarios are common successes.",
                ],
            },
            {
                "artifact_id": "fig:paired-safety",
                "source_data": {
                    "dataset_id": "paper_sequence_study_20260807",
                    "files": [relative(study_dir / "raw" / "method_results.csv")],
                },
                "transformation": {"script": relative(script_path), "sha256": _sha256(script_path)},
                "caption_claim": (
                    "Every recorded sampled clearance remains above the two-meter mesh margin, and "
                    "every peak requested input remains below the configured acceleration limit."
                ),
                "supported_manuscript_claims": [
                    {
                        "claim": (
                            "Both methods satisfy the recorded full-mesh sampled-clearance and requested-input audits in every paired scenario."
                        ),
                        "locator": "Results, Paired Success, Coverage, and Safety",
                    }
                ],
                "limitations": [
                    "Clearance values are deterministic sampled minima above the configured two-meter mesh margin.",
                    "The paired study disables the optional passive-drift audit and does not support a passive-safety claim.",
                    "The audit does not include navigation error, actuator uncertainty, target rotation, or delayed commands.",
                ],
            },
        ],
    }
    manifest_path = paper_dir / "figure_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.copyfile(manifest_path, result_dir / manifest_path.name)


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--study-dir",
        type=Path,
        default=repo_root / "data" / "results" / "paper_sequence_study_20260807",
    )
    parser.add_argument(
        "--paper-output-dir",
        type=Path,
        default=repo_root / "OrbInspectLatex" / "figures" / "paired_study",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    study_dir = args.study_dir.resolve()
    paper_dir = args.paper_output_dir.resolve()
    result_dir = study_dir / "figures"
    paper_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    paired = _read_csv(study_dir / "raw" / "paired_results.csv")
    method_rows = _read_csv(study_dir / "raw" / "method_results.csv")
    summary = json.loads((study_dir / "summary.json").read_text(encoding="utf-8"))
    if not paired or not all(row["common_success"].lower() == "true" for row in paired):
        raise ValueError("Figures require a nonempty all-common-success paired study.")
    if int(summary["summary"]["scenario_count"]) != len(paired):
        raise ValueError("Summary scenario count does not match paired_results.csv.")

    methods: dict[str, list[dict[str, str]]] = {}
    for method in (INCUMBENT, LOCAL):
        rows = [row for row in method_rows if row["method"] == method]
        rows.sort(key=lambda row: int(row["scenario"]))
        if len(rows) != len(paired):
            raise ValueError(f"Method {method} does not contain one row per paired scenario.")
        methods[method] = rows
    paired.sort(key=lambda row: int(row["scenario"]))

    _style()
    _plot_performance(paired, methods, summary, paper_dir, result_dir)
    _plot_safety(methods, paper_dir, result_dir)
    _write_manifest(repo_root, study_dir, paper_dir, result_dir, len(paired))
    print(f"Wrote paired-study figures to {paper_dir}")


if __name__ == "__main__":
    main()
