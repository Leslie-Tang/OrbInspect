#!/usr/bin/env python3
"""Reconstruct and plot an outcome-independent paired-study case.

The representative scenario is selected using only the predeclared initial-state
design: it is the Latin-hypercube point with the smallest normalized Euclidean
distance to the nominal initial state.  The script then reruns both current
full-mesh methods, verifies their sequences and primary metrics against the
archived paired-study rows, writes paper-grade case records, and renders two
publication figures from those saved records.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
for package_name in (
    "orbinspect_guidance",
    "orbinspect_dynamics",
    "orbinspect_perception",
    "orbinspect_safety",
):
    sys.path.insert(0, str(REPO_ROOT / "src" / package_name))

from orbinspect_guidance.offline_planning_experiment import ExperimentConfig
from orbinspect_guidance.offline_planning_experiment import MethodResult
from orbinspect_guidance.offline_planning_experiment import OfflinePlanningExperiment


INCUMBENT = "set_cover_cw_tour"
LOCAL = "safe_graph_adp_local_search"
METHODS = (INCUMBENT, LOCAL)
DISPLAY_NAMES = {
    INCUMBENT: "Two-stage incumbent",
    LOCAL: "Sequence improvement",
}
BLUE = "#0077BB"
ORANGE = "#EE7733"
GREY = "#777777"
LIGHT_GREY = "#D4D4D4"
MESH_FACE = "#C9D0D8"
BLACK = "#111111"
START = "#009988"
DISPLAY_TRIANGLE_LIMIT = 2400


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path: Path, rows: Iterable[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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
            "lines.linewidth": 1.15,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "figure.dpi": 150,
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.unicode_minus": False,
        }
    )


def _select_center_nearest_scenario(design: dict[str, Any]) -> tuple[int, float]:
    """Select the design point nearest nominal without reading outcomes."""
    nominal = np.asarray(design["experiment"]["initial_state"], dtype=float)
    half_width = np.asarray(
        design["study"]["position_half_width"]
        + design["study"]["velocity_half_width"],
        dtype=float,
    )
    states = np.asarray(design["initial_states"], dtype=float)
    normalized_distances = np.linalg.norm((states - nominal) / half_width, axis=1)
    scenario = int(np.argmin(normalized_distances))
    return scenario, float(normalized_distances[scenario])


def _experiment_config(
    design: dict[str, Any], study_dir: Path, scenario: int
) -> ExperimentConfig:
    values = dict(design["experiment"])
    values["output_root"] = study_dir
    values["run_id"] = "case_study_center_nearest"
    values["methods"] = METHODS
    values["initial_state"] = tuple(float(value) for value in design["initial_states"][scenario])
    values["random_seed"] = int(values["random_seed"]) + scenario
    return ExperimentConfig(**values)


def _archive_rows(
    study_dir: Path, scenario: int
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    methods = {
        row["method"]: row
        for row in _read_csv(study_dir / "raw" / "method_results.csv")
        if int(row["scenario"]) == scenario
    }
    paired = next(
        row
        for row in _read_csv(study_dir / "raw" / "paired_results.csv")
        if int(row["scenario"]) == scenario
    )
    if set(methods) != set(METHODS):
        raise ValueError("Selected scenario does not contain both paired methods.")
    return methods, paired


def _verify_reconstruction(
    results: tuple[MethodResult, ...], archived: dict[str, dict[str, str]]
) -> None:
    """Fail closed if the current reconstruction differs from the paired archive."""
    for result in results:
        archive = archived[result.method]
        sequence = ";".join(step.candidate.candidate_id for step in result.steps)
        if sequence != archive["candidate_sequence"]:
            raise RuntimeError(
                f"Reconstructed {result.method} sequence differs from the paired archive."
            )
        checks = {
            "total_delta_v": float(result.summary["total_delta_v"]),
            "total_dynamic_cost": float(result.summary["total_dynamic_cost"]),
            "final_inspectable_coverage_ratio": float(
                result.summary["final_inspectable_coverage_ratio"]
            ),
            "min_clearance": float(result.summary["min_clearance"]),
        }
        for field, actual in checks.items():
            expected = float(archive[field])
            if not math.isclose(actual, expected, rel_tol=1.0e-11, abs_tol=1.0e-11):
                raise RuntimeError(
                    f"Reconstructed {result.method} {field}={actual} differs "
                    f"from archived value {expected}."
                )


def _write_case_progress(
    path: Path,
    experiment: OfflinePlanningExperiment,
    results: tuple[MethodResult, ...],
) -> None:
    rows: list[dict[str, object]] = []
    for result in results:
        covered: set[str] = set()
        cumulative_delta_v = 0.0
        cumulative_dynamic_cost = 0.0
        rows.append(
            {
                "method": result.method,
                "action": 0,
                "candidate_id": "initial_state",
                "inspectable_coverage_ratio": 0.0,
                "edge_delta_v": 0.0,
                "cumulative_delta_v": 0.0,
                "edge_dynamic_cost": 0.0,
                "cumulative_dynamic_cost": 0.0,
                "edge_min_clearance": "",
                "edge_peak_requested_input": "",
            }
        )
        for action, step in enumerate(result.steps, start=1):
            covered.update(step.new_targets)
            cumulative_delta_v += step.transfer.delta_v
            cumulative_dynamic_cost += step.dynamic_cost
            rows.append(
                {
                    "method": result.method,
                    "action": action,
                    "candidate_id": step.candidate.candidate_id,
                    "inspectable_coverage_ratio": experiment._inspectable_coverage_ratio(
                        covered
                    ),
                    "edge_delta_v": step.transfer.delta_v,
                    "cumulative_delta_v": cumulative_delta_v,
                    "edge_dynamic_cost": step.dynamic_cost,
                    "cumulative_dynamic_cost": cumulative_dynamic_cost,
                    "edge_min_clearance": step.transfer.min_clearance,
                    "edge_peak_requested_input": step.transfer.peak_requested_input,
                }
            )
    _write_csv(
        path,
        rows,
        [
            "method",
            "action",
            "candidate_id",
            "inspectable_coverage_ratio",
            "edge_delta_v",
            "cumulative_delta_v",
            "edge_dynamic_cost",
            "cumulative_dynamic_cost",
            "edge_min_clearance",
            "edge_peak_requested_input",
        ],
    )


def _sample_mesh_triangles(
    experiment: OfflinePlanningExperiment,
) -> tuple[list[tuple[tuple[float, float, float], ...]], int]:
    mesh = experiment.base_planner.mesh_geometry
    if mesh is None:
        raise RuntimeError("Representative case requires the mesh geometry backend.")
    full_count = len(mesh.triangles)
    sample_count = min(DISPLAY_TRIANGLE_LIMIT, full_count)
    indices = np.linspace(0, full_count - 1, sample_count, dtype=int)
    faces = [mesh.triangles[int(index)].vertices for index in indices]
    return faces, full_count


def _group_rows(
    rows: list[dict[str, str]], key: str = "method"
) -> dict[str, list[dict[str, str]]]:
    grouped = {method: [] for method in METHODS}
    for row in rows:
        if row[key] in grouped:
            grouped[row[key]].append(row)
    return grouped


def _trajectory_points(rows: list[dict[str, str]]) -> np.ndarray:
    rows = sorted(rows, key=lambda row: float(row["time"]))
    return np.asarray(
        [[float(row["rx"]), float(row["ry"]), float(row["rz"])] for row in rows],
        dtype=float,
    )


def _viewpoint_points(rows: list[dict[str, str]]) -> dict[str, tuple[int, np.ndarray]]:
    return {
        row["candidate_id"]: (
            int(row["sequence"]) + 1,
            np.asarray(
                [float(row["viewpoint_x"]), float(row["viewpoint_y"]), float(row["viewpoint_z"])],
                dtype=float,
            ),
        )
        for row in rows
    }


def _panel_label(ax: mpl.axes.Axes, label: str, *, is_3d: bool = False) -> None:
    x = -0.08 if is_3d else -0.13
    ax.text2D(x, 1.02, label, transform=ax.transAxes, fontsize=9.2, fontweight="bold") \
        if is_3d else ax.text(
            x,
            1.03,
            label,
            transform=ax.transAxes,
            fontsize=9.2,
            fontweight="bold",
            ha="left",
            va="bottom",
        )


def _set_equal_3d_axes(
    ax: mpl.axes.Axes,
    faces: list[tuple[tuple[float, float, float], ...]],
    trajectories: dict[str, np.ndarray],
) -> None:
    mesh_points = np.asarray([vertex for face in faces for vertex in face], dtype=float)
    all_points = np.vstack([mesh_points, *trajectories.values()])
    lower = all_points.min(axis=0)
    upper = all_points.max(axis=0)
    center = 0.5 * (lower + upper)
    radius = 0.53 * float(np.max(upper - lower))
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    try:
        ax.set_box_aspect((1.0, 1.0, 1.0), zoom=0.9)
    except TypeError:
        ax.set_box_aspect((1.0, 1.0, 1.0))


def _plot_geometry(
    paper_dir: Path,
    result_dir: Path,
    case_dir: Path,
    mesh_faces: list[tuple[tuple[float, float, float], ...]],
) -> None:
    trajectories_by_method = _group_rows(_read_csv(case_dir / "raw" / "trajectory.csv"))
    viewpoints_by_method = _group_rows(_read_csv(case_dir / "raw" / "viewpoints.csv"))
    trajectories = {
        method: _trajectory_points(trajectories_by_method[method]) for method in METHODS
    }
    viewpoints = {
        method: _viewpoint_points(viewpoints_by_method[method]) for method in METHODS
    }

    fig = plt.figure(figsize=(7.05, 3.35))
    grid = fig.add_gridspec(1, 2, width_ratios=(1.06, 1.0), wspace=0.20)
    ax3d = fig.add_subplot(grid[0], projection="3d")
    surface = Poly3DCollection(
        mesh_faces,
        facecolors="#B8C1CB",
        edgecolors="none",
        alpha=0.34,
        zorder=0,
    )
    ax3d.add_collection3d(surface)
    mesh_edges = [
        (face[index], face[(index + 1) % 3])
        for face in mesh_faces
        for index in range(3)
    ]
    wireframe = Line3DCollection(
        mesh_edges, colors="#66717C", linewidths=0.08, alpha=0.16, zorder=1
    )
    ax3d.add_collection3d(wireframe)
    for method, color, linestyle, marker in (
        (INCUMBENT, ORANGE, (0, (4, 2)), "^"),
        (LOCAL, BLUE, "-", "o"),
    ):
        points = trajectories[method]
        ax3d.plot(
            points[:, 0],
            points[:, 1],
            points[:, 2],
            color=color,
            linestyle=linestyle,
            linewidth=1.25,
            alpha=0.96,
            label=DISPLAY_NAMES[method],
            zorder=5,
        )
        terminal = np.asarray([item[1] for item in viewpoints[method].values()])
        ax3d.scatter(
            terminal[:, 0],
            terminal[:, 1],
            terminal[:, 2],
            s=18 if method == LOCAL else 29,
            marker=marker,
            facecolor=color if method == LOCAL else "white",
            edgecolor=BLACK if method == LOCAL else color,
            linewidth=0.45 if method == LOCAL else 0.8,
            depthshade=False,
            zorder=7,
        )
    start = trajectories[INCUMBENT][0]
    ax3d.scatter(
        [start[0]], [start[1]], [start[2]], s=58, marker="*", facecolor=START,
        edgecolor=BLACK, linewidth=0.45, depthshade=False, zorder=9,
    )
    ax3d.set_xlabel("Radial x (m)", labelpad=5)
    ax3d.set_ylabel("Along-track y (m)", labelpad=5)
    ax3d.set_zlabel("Cross-track z (m)", labelpad=5)
    ax3d.view_init(elev=24, azim=-53)
    ax3d.grid(True, color="#E4E4E4", linewidth=0.35)
    for pane in (ax3d.xaxis.pane, ax3d.yaxis.pane, ax3d.zaxis.pane):
        pane.set_facecolor((1.0, 1.0, 1.0, 0.0))
        pane.set_edgecolor("#E7E7E7")
    _set_equal_3d_axes(ax3d, mesh_faces, trajectories)
    _panel_label(ax3d, "A", is_3d=True)

    ax = fig.add_subplot(grid[1])
    projected_faces = [[(vertex[1], vertex[2]) for vertex in face] for face in mesh_faces]
    ax.add_collection(
        PolyCollection(
            projected_faces,
            facecolors="#B8C1CB",
            edgecolors="#66717C",
            linewidths=0.08,
            alpha=0.28,
            zorder=0,
        )
    )
    for method, color, linestyle, marker in (
        (INCUMBENT, ORANGE, (0, (4, 2)), "^"),
        (LOCAL, BLUE, "-", "o"),
    ):
        points = trajectories[method]
        ax.plot(
            points[:, 1],
            points[:, 2],
            color=color,
            linestyle=linestyle,
            linewidth=1.25,
            alpha=0.97,
            label=DISPLAY_NAMES[method],
            zorder=4,
        )
        terminal = np.asarray([item[1] for item in viewpoints[method].values()])
        ax.scatter(
            terminal[:, 1],
            terminal[:, 2],
            s=18 if method == LOCAL else 30,
            marker=marker,
            facecolor=color if method == LOCAL else "white",
            edgecolor=BLACK if method == LOCAL else color,
            linewidth=0.45 if method == LOCAL else 0.8,
            zorder=6,
        )
    ax.scatter(
        [start[1]], [start[2]], s=58, marker="*", facecolor=START,
        edgecolor=BLACK, linewidth=0.45, label="Initial position", zorder=8,
    )
    incumbent_order = viewpoints[INCUMBENT]
    local_order = viewpoints[LOCAL]
    changed_ids = [
        candidate_id
        for candidate_id in incumbent_order
        if incumbent_order[candidate_id][0] != local_order[candidate_id][0]
    ]
    offsets = ((-38, 11), (4, -19), (-40, -11), (4, 5))
    for candidate_id, offset in zip(changed_ids, offsets):
        incumbent_action, point = incumbent_order[candidate_id]
        local_action = local_order[candidate_id][0]
        ax.annotate(
            f"I{incumbent_action}/L{local_action}",
            (point[1], point[2]),
            xytext=offset,
            textcoords="offset points",
            fontsize=8.0,
            ha="left",
            va="bottom",
            bbox={"boxstyle": "round,pad=0.16", "facecolor": "white", "edgecolor": LIGHT_GREY},
            zorder=9,
        )
    combined = np.vstack([np.asarray([[v[1], v[2]] for v in face]) for face in mesh_faces]
                          + [points[:, 1:3] for points in trajectories.values()])
    lower = combined.min(axis=0)
    upper = combined.max(axis=0)
    padding = 0.055 * (upper - lower)
    ax.set_xlim(lower[0] - padding[0], upper[0] + padding[0])
    ax.set_ylim(lower[1] - padding[1], upper[1] + padding[1])
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Along-track y (m)")
    ax.set_ylabel("Cross-track z (m)")
    ax.grid(True, color="#E8E8E8", linewidth=0.4, zorder=0)
    handles, labels = ax.get_legend_handles_labels()
    handles.append(Patch(facecolor=MESH_FACE, edgecolor="none", alpha=0.45))
    labels.append("ISS mesh (display)")
    ax.legend(
        handles,
        labels,
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.17),
        ncol=2,
        handlelength=2.0,
        handletextpad=0.45,
        borderpad=0.15,
        columnspacing=0.9,
    )
    _panel_label(ax, "B")

    fig.subplots_adjust(left=0.045, right=0.995, bottom=0.24, top=0.97)
    _save_figure(fig, "representative_case_trajectory", paper_dir, result_dir)
    plt.close(fig)


def _plot_progress(paper_dir: Path, result_dir: Path, case_dir: Path) -> None:
    progress = _group_rows(_read_csv(case_dir / "raw" / "case_progress.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(7.05, 2.48), constrained_layout=True)
    styles = {
        INCUMBENT: (ORANGE, (0, (4, 2)), "^"),
        LOCAL: (BLUE, "-", "o"),
    }

    ax = axes[0]
    ax.axhline(80.0, color=GREY, linestyle=(0, (2, 2)), linewidth=0.9, label="Stop target: 80%")
    for method in METHODS:
        rows = sorted(progress[method], key=lambda row: int(row["action"]))
        actions = np.asarray([int(row["action"]) for row in rows])
        coverage = 100.0 * np.asarray(
            [float(row["inspectable_coverage_ratio"]) for row in rows]
        )
        color, linestyle, marker = styles[method]
        ax.step(
            actions,
            coverage,
            where="post",
            color=color,
            linestyle=linestyle,
            marker=marker,
            markersize=3.8,
            markerfacecolor=color if method == LOCAL else "white",
            markeredgewidth=0.7,
            label=DISPLAY_NAMES[method],
            zorder=3,
        )
    ax.set_xlim(0, 11.55)
    ax.set_ylim(0, 86)
    ax.set_xticks(np.arange(0, 12, 2))
    ax.set_yticks(np.arange(0, 81, 20))
    ax.set_xlabel("Accepted SOOA (count)")
    ax.set_ylabel(r"Inspectable coverage $C^{\mathrm{insp}}$ (%)")
    ax.grid(axis="y", color="#E8E8E8", linewidth=0.45, zorder=0)
    ax.legend(frameon=False, loc="lower right", handlelength=2.3, borderpad=0.15)
    _panel_label(ax, "A")

    ax = axes[1]
    finals: dict[str, float] = {}
    for method in METHODS:
        rows = sorted(progress[method], key=lambda row: int(row["action"]))
        actions = np.asarray([int(row["action"]) for row in rows])
        cumulative = np.asarray([float(row["cumulative_delta_v"]) for row in rows])
        finals[method] = float(cumulative[-1])
        color, linestyle, marker = styles[method]
        ax.plot(
            actions,
            cumulative,
            color=color,
            linestyle=linestyle,
            marker=marker,
            markersize=3.8,
            markerfacecolor=color if method == LOCAL else "white",
            markeredgewidth=0.7,
            label=DISPLAY_NAMES[method],
            zorder=3,
        )
    difference = finals[LOCAL] - finals[INCUMBENT]
    reduction = -100.0 * difference / finals[INCUMBENT]
    ax.set_xlim(0, 11.55)
    ax.set_ylim(0, 12.7)
    ax.set_xticks(np.arange(0, 12, 2))
    ax.set_yticks(np.arange(0, 13, 2))
    ax.set_xlabel("Accepted SOOA (count)")
    ax.set_ylabel(r"Cumulative $\Delta v$ (m s$^{-1}$)")
    ax.grid(axis="y", color="#E8E8E8", linewidth=0.45, zorder=0)
    ax.text(
        0.045,
        0.95,
        f"Final local minus incumbent\n{difference:.3f} m s$^{{-1}}$ ({reduction:.2f}% reduction)",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.0,
        linespacing=1.2,
        bbox={"boxstyle": "round,pad=0.22", "facecolor": "white", "edgecolor": LIGHT_GREY},
    )
    ax.annotate(
        f"{finals[INCUMBENT]:.3f}",
        (11, finals[INCUMBENT]),
        xytext=(-5, 7),
        textcoords="offset points",
        ha="right",
        va="bottom",
        color=ORANGE,
        fontsize=8.0,
    )
    ax.annotate(
        f"{finals[LOCAL]:.3f}",
        (11, finals[LOCAL]),
        xytext=(-5, -8),
        textcoords="offset points",
        ha="right",
        va="top",
        color=BLUE,
        fontsize=8.0,
    )
    ax.legend(frameon=False, loc="lower right", handlelength=2.3, borderpad=0.15)
    _panel_label(ax, "B")

    _save_figure(fig, "representative_case_progress", paper_dir, result_dir)
    plt.close(fig)


def _save_figure(
    fig: mpl.figure.Figure, stem: str, paper_dir: Path, result_dir: Path
) -> None:
    metadata = {"Creator": "OrbInspect representative-case figure generator", "CreationDate": None}
    pdf_path = paper_dir / f"{stem}.pdf"
    png_path = paper_dir / f"{stem}.png"
    fig.savefig(pdf_path, format="pdf", pad_inches=0.02, metadata=metadata)
    fig.savefig(png_path, format="png", pad_inches=0.02, facecolor="white")
    shutil.copyfile(pdf_path, result_dir / pdf_path.name)
    shutil.copyfile(png_path, result_dir / png_path.name)


def _write_selection_manifest(
    path: Path,
    study_dir: Path,
    scenario: int,
    normalized_distance: float,
    design: dict[str, Any],
    archived: dict[str, dict[str, str]],
    paired: dict[str, str],
    mesh_triangle_count: int,
) -> None:
    payload = {
        "case_study_schema_version": "orbinspect-representative-case/v1",
        "selection_rule": (
            "Minimize Euclidean distance from the nominal six-state initial condition "
            "after scaling each coordinate by its predeclared Latin-hypercube half-width."
        ),
        "selection_uses_method_outcomes": False,
        "selected_scenario_zero_based": scenario,
        "selected_scenario_paper_label": scenario + 1,
        "normalized_distance": normalized_distance,
        "nominal_initial_state": design["experiment"]["initial_state"],
        "selected_initial_state": design["initial_states"][scenario],
        "position_half_width": design["study"]["position_half_width"],
        "velocity_half_width": design["study"]["velocity_half_width"],
        "reconstruction_verification": {
            "candidate_sequences_match_paired_archive": True,
            "primary_metrics_match_paired_archive": True,
            "archived_candidate_sequences": {
                method: archived[method]["candidate_sequence"] for method in METHODS
            },
        },
        "selected_paired_outcome": {
            "inspectable_coverage_ratio": float(paired["local_inspectable_coverage"]),
            "local_total_delta_v": float(paired["local_total_delta_v"]),
            "incumbent_total_delta_v": float(paired["incumbent_total_delta_v"]),
            "delta_v_difference": float(paired["delta_v_difference"]),
            "local_total_dynamic_cost": float(paired["local_total_dynamic_cost"]),
            "incumbent_total_dynamic_cost": float(paired["incumbent_total_dynamic_cost"]),
            "dynamic_cost_difference": float(paired["dynamic_cost_difference"]),
        },
        "mesh_computation_triangle_count": mesh_triangle_count,
        "mesh_display_triangle_count": min(DISPLAY_TRIANGLE_LIMIT, mesh_triangle_count),
        "source_files": {
            str((study_dir / "config_snapshot" / "study_design.json").relative_to(REPO_ROOT)).replace("\\", "/"): _sha256(
                study_dir / "config_snapshot" / "study_design.json"
            ),
            str((study_dir / "raw" / "method_results.csv").relative_to(REPO_ROOT)).replace("\\", "/"): _sha256(
                study_dir / "raw" / "method_results.csv"
            ),
            str((study_dir / "raw" / "paired_results.csv").relative_to(REPO_ROOT)).replace("\\", "/"): _sha256(
                study_dir / "raw" / "paired_results.csv"
            ),
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_figure_manifest(
    paper_dir: Path,
    result_dir: Path,
    study_dir: Path,
    case_dir: Path,
    scenario: int,
    mesh_triangle_count: int,
) -> None:
    script_path = Path(__file__).resolve()
    selection_path = case_dir / "config_snapshot" / "case_study_selection.json"
    source_files = [
        study_dir / "raw" / "paired_results.csv",
        case_dir / "raw" / "trajectory.csv",
        case_dir / "raw" / "viewpoints.csv",
        case_dir / "raw" / "case_progress.csv",
        case_dir / "raw" / "method_comparison.csv",
        selection_path,
    ]
    artifact_files = [
        paper_dir / "representative_case_trajectory.pdf",
        paper_dir / "representative_case_trajectory.png",
        paper_dir / "representative_case_progress.pdf",
        paper_dir / "representative_case_progress.png",
    ]
    relative = lambda path: path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    transformation = {"script": relative(script_path), "sha256": _sha256(script_path)}
    manifest = {
        "figure_schema_version": "orbinspect-paper-figures/v1",
        "case_study_schema_version": "orbinspect-representative-case/v1",
        "selected_scenario_zero_based": scenario,
        "selected_scenario_paper_label": scenario + 1,
        "selection_uses_method_outcomes": False,
        "source_files": {relative(path): _sha256(path) for path in source_files},
        "transformation": transformation,
        "artifacts": {relative(path): _sha256(path) for path in artifact_files},
        "figure_table_trace": [
            {
                "artifact_id": "fig:representative-trajectory",
                "source_data": {
                    "dataset_id": "paper_sequence_study_20260807_center_nearest_case",
                    "files": [
                        relative(case_dir / "raw" / "trajectory.csv"),
                        relative(case_dir / "raw" / "viewpoints.csv"),
                        relative(selection_path),
                    ],
                },
                "transformation": transformation,
                "caption_claim": (
                    "The outcome-independent center-nearest case differs through two local "
                    "viewpoint-order exchanges while both methods retain the same observation set."
                ),
                "supported_manuscript_claims": [
                    {
                        "claim": (
                            "In the representative center-nearest design case, local search changes "
                            "the route by exchanging observation-order pairs 4/5 and 7/8."
                        ),
                        "locator": "Results, Outcome-Independent Trajectory Case Study",
                    }
                ],
                "limitations": [
                    "The case is illustrative; paired inference comes from all 20 scenarios, not this route alone.",
                    (
                        f"The display uses {min(DISPLAY_TRIANGLE_LIMIT, mesh_triangle_count):,} "
                        f"of {mesh_triangle_count:,} mesh triangles for legibility; all planning, "
                        "visibility, clearance, and swept-intersection queries use the complete mesh."
                    ),
                    "Trajectories are deterministic HCW rollouts and do not include navigation or actuator uncertainty.",
                ],
            },
            {
                "artifact_id": "fig:representative-progress",
                "source_data": {
                    "dataset_id": "paper_sequence_study_20260807_center_nearest_case",
                    "files": [
                        relative(case_dir / "raw" / "case_progress.csv"),
                        relative(case_dir / "raw" / "method_comparison.csv"),
                        relative(selection_path),
                    ],
                },
                "transformation": transformation,
                "caption_claim": (
                    "Both routes reach 80.49 percent inspectable coverage in 11 actions, while the "
                    "locally improved route reduces cumulative delta-v by 0.0524 meters per second."
                ),
                "supported_manuscript_claims": [
                    {
                        "claim": (
                            "The center-nearest case preserves final inspectable coverage and action "
                            "count while reducing total delta-v from 11.955 to 11.902 meters per second."
                        ),
                        "locator": "Results, Outcome-Independent Trajectory Case Study",
                    }
                ],
                "limitations": [
                    "The action-indexed curves describe one design-selected case and are not uncertainty intervals.",
                    "Coverage is credited only at accepted observation endpoints; transfer-time image acquisition is not modeled.",
                ],
            },
        ],
    }
    manifest_path = paper_dir / "representative_case_figure_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    shutil.copyfile(manifest_path, result_dir / manifest_path.name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--study-dir",
        type=Path,
        default=REPO_ROOT / "data" / "results" / "paper_sequence_study_20260807",
    )
    parser.add_argument(
        "--paper-output-dir",
        type=Path,
        default=REPO_ROOT / "OrbInspectLatex" / "figures" / "paired_study",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    study_dir = args.study_dir.resolve()
    paper_dir = args.paper_output_dir.resolve()
    os.chdir(REPO_ROOT)
    design = json.loads(
        (study_dir / "config_snapshot" / "study_design.json").read_text(encoding="utf-8")
    )
    scenario, normalized_distance = _select_center_nearest_scenario(design)
    archived, paired = _archive_rows(study_dir, scenario)

    config = _experiment_config(design, study_dir, scenario)
    experiment = OfflinePlanningExperiment(config)
    results = tuple(experiment.run_method(method) for method in METHODS)
    _verify_reconstruction(results, archived)
    case_dir = experiment.save(results)
    _write_case_progress(case_dir / "raw" / "case_progress.csv", experiment, results)
    mesh_faces, mesh_triangle_count = _sample_mesh_triangles(experiment)
    _write_selection_manifest(
        case_dir / "config_snapshot" / "case_study_selection.json",
        study_dir,
        scenario,
        normalized_distance,
        design,
        archived,
        paired,
        mesh_triangle_count,
    )

    paper_dir.mkdir(parents=True, exist_ok=True)
    result_dir = case_dir / "figures"
    result_dir.mkdir(parents=True, exist_ok=True)
    _style()
    _plot_geometry(paper_dir, result_dir, case_dir, mesh_faces)
    _plot_progress(paper_dir, result_dir, case_dir)
    _write_figure_manifest(
        paper_dir,
        result_dir,
        study_dir,
        case_dir,
        scenario,
        mesh_triangle_count,
    )
    print(
        f"Wrote representative case for scenario {scenario} "
        f"(paper label {scenario + 1}) to {paper_dir}"
    )


if __name__ == "__main__":
    main()
