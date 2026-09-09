#!/usr/bin/env python3
"""Generate traceable paper figures for the frozen rollout-ADP study."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from matplotlib.patches import FancyBboxPatch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
for package in (
    'orbinspect_guidance',
    'orbinspect_dynamics',
    'orbinspect_perception',
    'orbinspect_safety',
):
    sys.path.insert(0, str(REPO_ROOT / 'src' / package))

from orbinspect_guidance.advanced_safe_planner import AdvancedSafePlanner
from orbinspect_guidance.offline_adp_superiority_study import SuperiorityConfig
from orbinspect_guidance.offline_adp_superiority_study import _method_config
from orbinspect_guidance.offline_adp_superiority_study import _problem_for_scenario
from orbinspect_guidance.offline_adp_superiority_study import load_archived_graph
from orbinspect_guidance.offline_planning_experiment import ExperimentConfig
from orbinspect_guidance.offline_planning_experiment import OfflinePlanningExperiment
from orbinspect_guidance.offline_planning_experiment import _load_yaml_config


# Manuscript-wide palette supplied by the authors.  Color is never the sole
# categorical encoding: plots also use marker, hatch, or line-style changes.
RED = '#750014'
ROSE = '#E3CCD0'
MINT = '#CCECDB'
PURPLE = '#7F3F98'
YELLOW = '#FFDE17'
BLUE = '#587E92'
GREEN = '#37A537'
ORANGE = '#E46240'
GREY = '#6B7280'
LIGHT_GREY = '#D9DEE3'
BLACK = '#1E293B'
TEST_COLOR = RED
OOD_COLOR = PURPLE
PROPOSED_COLOR = RED
LOCAL_COLOR = BLUE
PROPOSED = 'adaptive_rollout_adp'
LOCAL = 'local_search'
DISPLAY = {
    PROPOSED: 'Rollout ADP (depth 3)',
    LOCAL: 'Audited local search',
    'incumbent': 'Greedy incumbent',
    'rollout': 'Fixed-suffix rollout',
    'frozen_adp': 'Frozen fitted critic',
    'search_only': 'Heuristic search',
}


def _style() -> None:
    mpl.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 8.8,
        'axes.titlesize': 9.5,
        'axes.labelsize': 9.1,
        'xtick.labelsize': 8.3,
        'ytick.labelsize': 8.3,
        'legend.fontsize': 8.2,
        'figure.dpi': 160,
        'savefig.dpi': 600,
        'savefig.bbox': 'tight',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.linewidth': 0.7,
        'lines.linewidth': 1.15,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
        'axes.unicode_minus': False,
    })


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _save(fig, name: str, result_dir: Path, paper_dir: Path) -> list[Path]:
    result_figure_dir = result_dir / 'figures'
    paper_figure_dir = paper_dir / 'figures' / 'adp_future'
    result_figure_dir.mkdir(parents=True, exist_ok=True)
    paper_figure_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for suffix in ('pdf', 'svg', 'png'):
        path = result_figure_dir / f'{name}.{suffix}'
        fig.savefig(path)
        shutil.copy2(path, paper_figure_dir / path.name)
        paths.append(path)
    plt.close(fig)
    return paths


def plot_rollout_architecture(result_dir: Path, paper_dir: Path) -> list[Path]:
    """Render the selected ADP mechanism as a vector workflow."""
    fig, ax = plt.subplots(figsize=(6.9, 2.85))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    boxes = [
        (0.02, 0.25, 0.17, 0.50, 'Markov state',
         '$s_k=(j_k,m_k,$\n$b_k,h_k)$\nmasks + budget', BLUE),
        (0.23, 0.25, 0.18, 0.50, 'Safety shield',
         'HCW/input bounds\nterminal condition\nmesh/sweep audits', GREEN),
        (0.45, 0.14, 0.28, 0.72, 'Depth-3 rollout ADP',
         '$\\widehat Q_d(s,a)$\n'
         '$=\\ell_{ja}+\\widehat V_{d-1}(s\prime)$\n'
         '$\\widehat V_0$: adaptive safe-greedy\nfeasible completion', RED),
        (0.78, 0.25, 0.19, 0.50, 'Policy update',
         '$a_k=\\arg\\min_a$\n$\\widehat Q_3(s_k,a)$\nexecute first SOOA\nupdate + repeat', PURPLE),
    ]
    for x, y, width, height, title, body, color in boxes:
        patch = FancyBboxPatch(
            (x, y), width, height,
            boxstyle='round,pad=0.012,rounding_size=0.018',
            facecolor='white', edgecolor=color, linewidth=1.5,
        )
        ax.add_patch(patch)
        ax.text(x + width / 2, y + height * 0.72, title,
                ha='center', va='center', fontweight='bold', color=color,
                fontsize=9.0)
        ax.text(x + width / 2, y + height * 0.39, body,
                ha='center', va='center', linespacing=1.28, fontsize=8.2)
    for start, end in ((0.19, 0.23), (0.41, 0.45), (0.73, 0.78)):
        ax.add_patch(FancyArrowPatch(
            (start, 0.5), (end, 0.5), arrowstyle='-|>',
            mutation_scale=11, linewidth=1.0, color=BLACK,
        ))
    ax.add_patch(FancyArrowPatch(
        (0.88, 0.24), (0.11, 0.20),
        connectionstyle='arc3,rad=-0.19', arrowstyle='-|>',
        mutation_scale=10, linewidth=0.9, color=GREY,
    ))
    ax.text(0.51, 0.015, 'next decision state after the audited SOOA',
            ha='center', va='bottom', color=GREY, fontsize=8.2,
            bbox={'facecolor': 'white', 'edgecolor': 'none', 'pad': 0.8})
    ax.text(0.59, 0.93, 'unsafe or non-viable branches are never expanded',
            ha='center', va='center', color=ORANGE, fontstyle='italic', fontsize=8.2)
    return _save(fig, 'adp_rollout_architecture', result_dir, paper_dir)


def _dev_rows(path: Path) -> list[dict[str, str]]:
    return _read_rows(path / 'raw' / 'heldout_results.csv')


def plot_development_selection(
    dev_dirs: dict[int, Path],
    result_dir: Path,
    paper_dir: Path,
) -> list[Path]:
    """Save each validation-only depth-selection panel independently."""
    rows_by_depth = {depth: _dev_rows(path) for depth, path in dev_dirs.items()}
    scenario_ids = sorted({
        row['scenario_id'] for row in rows_by_depth[1]
        if row['method'] == PROPOSED
    })
    local = {
        row['scenario_id']: float(row['graph_cost'])
        for row in rows_by_depth[1] if row['method'] == LOCAL
    }
    cost_by_depth = {
        depth: {
            row['scenario_id']: float(row['graph_cost'])
            for row in rows if row['method'] == PROPOSED
        }
        for depth, rows in rows_by_depth.items()
    }
    time_by_depth = {
        depth: [
            float(row['online_time_s']) for row in rows
            if row['method'] == PROPOSED
        ]
        for depth, rows in rows_by_depth.items()
    }
    paths = []
    x = np.arange(4)
    labels = ['Local', '$d=1$', '$d=2$', '$d=3$']

    fig, ax = plt.subplots(figsize=(2.18, 2.45))
    for scenario_id in scenario_ids:
        values = [local[scenario_id]] + [
            cost_by_depth[depth][scenario_id] for depth in (1, 2, 3)
        ]
        ax.plot(x, values, color=LIGHT_GREY, linewidth=0.65, zorder=1)
        ax.scatter(x, values, color=GREY, s=9, alpha=0.72, zorder=2)
    means = [np.mean(list(local.values()))] + [
        np.mean(list(cost_by_depth[depth].values())) for depth in (1, 2, 3)
    ]
    ax.plot(x, means, color=RED, marker='D', markersize=4.8,
            linewidth=1.6, label='Mean')
    ax.set_xticks(x, labels)
    ax.set_ylabel('Graph cost, $J$ (cost units)')
    ax.legend(frameon=False, loc='upper right')
    ax.grid(axis='y', color='#ECECEC', linewidth=0.6)
    fig.tight_layout(pad=0.35)
    paths.extend(_save(fig, 'adp_development_selection_a', result_dir, paper_dir))

    fig, ax = plt.subplots(figsize=(2.18, 2.45))
    for depth in (1, 2, 3):
        differences = np.array([
            cost_by_depth[depth][scenario_id] - local[scenario_id]
            for scenario_id in scenario_ids
        ])
        jitter = np.linspace(-0.08, 0.08, len(differences))
        ax.scatter(
            np.full(len(differences), depth) + jitter,
            differences,
            color=[BLUE, PURPLE, RED][depth - 1],
            s=14,
            alpha=0.78,
            edgecolors='white',
            linewidth=0.25,
        )
        ax.scatter(depth, differences.mean(), marker='D', s=35,
                   color=BLACK, zorder=4)
    ax.axhline(0, color=GREY, linestyle='--', linewidth=0.8)
    ax.set_xticks((1, 2, 3), ('$d=1$', '$d=2$', '$d=3$'))
    ax.set_ylabel('$J_{\mathrm{ADP}}-J_{\mathrm{local}}$\n(cost units)')
    ax.grid(axis='y', color='#ECECEC', linewidth=0.6)
    fig.tight_layout(pad=0.35)
    paths.extend(_save(fig, 'adp_development_selection_b', result_dir, paper_dir))

    fig, ax = plt.subplots(figsize=(2.18, 2.45))
    medians = [np.median(time_by_depth[depth]) for depth in (1, 2, 3)]
    bars = ax.bar((1, 2, 3), medians, color=(BLUE, PURPLE, RED),
                  edgecolor=BLACK, linewidth=0.55)
    for bar, hatch in zip(bars, ('', '//', 'xx')):
        bar.set_hatch(hatch)
    for depth, value in zip((1, 2, 3), medians):
        ax.text(depth, value * 1.16, f'{value:.3f}', ha='center', va='bottom')
    ax.set_yscale('log')
    ax.set_ylim(min(medians) * 0.72, max(medians) * 1.75)
    ax.set_xticks((1, 2, 3), ('$d=1$', '$d=2$', '$d=3$'))
    ax.set_ylabel('Median online time\n(s, log scale)')
    ax.grid(axis='y', which='both', color='#ECECEC', linewidth=0.6)
    fig.tight_layout(pad=0.35)
    paths.extend(_save(fig, 'adp_development_selection_c', result_dir, paper_dir))
    return paths


def _method_rows(rows, split: str, method: str) -> dict[str, dict[str, str]]:
    return {
        row['scenario_id']: row for row in rows
        if row['split'] == split and row['method'] == method
    }


def plot_heldout_performance(
    rows: list[dict[str, str]],
    validation: dict[str, object],
    result_dir: Path,
    paper_dir: Path,
) -> list[Path]:
    """Save the four held-out comparison panels as separate figure files."""
    paths = []
    for row_index, split in enumerate(('test', 'ood')):
        proposed = _method_rows(rows, split, PROPOSED)
        local = _method_rows(rows, split, LOCAL)
        scenario_ids = sorted(proposed)
        x = np.array([float(local[key]['total_delta_v']) for key in scenario_ids])
        y = np.array([float(proposed[key]['total_delta_v']) for key in scenario_ids])
        lo = min(x.min(), y.min()) - 0.3
        hi = max(x.max(), y.max()) + 0.3
        panel_left = 'a' if row_index == 0 else 'c'
        fig, ax = plt.subplots(figsize=(3.32, 2.50))
        ax.plot((lo, hi), (lo, hi), '--', color=GREY, linewidth=0.8)
        ax.scatter(
            x, y,
            color=TEST_COLOR if split == 'test' else OOD_COLOR,
            marker='o' if split == 'test' else 's',
            s=20, alpha=0.84, edgecolors=BLACK, linewidth=0.35,
        )
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_aspect('equal', adjustable='box')
        ax.set_xlabel('Local-search $\Delta v$ (m/s)')
        ax.set_ylabel('Rollout-ADP $\Delta v$ (m/s)')
        ax.grid(color='#ECECEC', linewidth=0.6)
        fig.tight_layout(pad=0.35)
        paths.extend(_save(
            fig, f'adp_heldout_performance_{panel_left}', result_dir, paper_dir,
        ))

        differences = np.array([
            float(proposed[key]['graph_cost']) - float(local[key]['graph_cost'])
            for key in scenario_ids
        ])
        ordered = np.sort(differences)
        color = TEST_COLOR if split == 'test' else OOD_COLOR
        panel_right = 'b' if row_index == 0 else 'd'
        fig, ax = plt.subplots(figsize=(3.32, 2.50))
        ax.scatter(np.arange(1, len(ordered) + 1), ordered,
                   color=color, s=16, edgecolors=BLACK, linewidth=0.25)
        ax.axhline(0, color=GREY, linestyle='--', linewidth=0.8)
        comparison = validation['comparisons'][split][LOCAL]
        mean_difference = comparison['mean_paired_difference']
        lower, upper = comparison['bootstrap_95_ci']
        ax.axhspan(lower, upper, color=ROSE, alpha=0.55)
        ax.axhline(mean_difference, color=RED, linewidth=1.4)
        ax.text(
            0.98, 0.05,
            f'mean {mean_difference:.2f}\n95% CI [{lower:.2f}, {upper:.2f}]',
            transform=ax.transAxes,
            ha='right', va='bottom', color=BLACK,
            bbox={'facecolor': 'white', 'edgecolor': 'none', 'alpha': 0.82},
        )
        split_label = 'Test' if split == 'test' else 'Shifted'
        ax.set_xlabel(f'{split_label} scenarios, ordered')
        ax.set_ylabel('$J_{\mathrm{ADP}}-J_{\mathrm{local}}$ (cost units)')
        ax.grid(axis='y', color='#ECECEC', linewidth=0.6)
        fig.tight_layout(pad=0.35)
        paths.extend(_save(
            fig, f'adp_heldout_performance_{panel_right}', result_dir, paper_dir,
        ))
    return paths


def _bootstrap_ci(values: list[float], seed: int) -> tuple[float, float]:
    generator = random.Random(seed)
    estimates = sorted(
        np.mean([values[generator.randrange(len(values))] for _ in values])
        for _draw in range(5000)
    )
    return estimates[124], estimates[4874]


def plot_ablation_safety(
    rows: list[dict[str, str]],
    result_dir: Path,
    paper_dir: Path,
) -> list[Path]:
    """Save component-attribution and safety panels independently."""
    methods = ('incumbent', 'rollout', LOCAL, PROPOSED)
    paths = []
    colors = (ROSE, PURPLE, LOCAL_COLOR, PROPOSED_COLOR)
    test_values = [
        [float(row['total_delta_v']) for row in rows
         if row['split'] == 'test' and row['method'] == method]
        for method in methods
    ]
    means = [np.mean(values) for values in test_values]
    intervals = [_bootstrap_ci(values, 6400 + index) for index, values in enumerate(test_values)]
    yerr = np.array([
        [value - lower for value, (lower, _upper) in zip(means, intervals)],
        [upper - value for value, (_lower, upper) in zip(means, intervals)],
    ])
    fig, ax = plt.subplots(figsize=(3.32, 2.45))
    bars = ax.bar(np.arange(4), means, yerr=yerr, capsize=3,
                  color=colors, edgecolor=BLACK, linewidth=0.55)
    for bar, hatch in zip(bars, ('..', '//', '\\\\', 'xx')):
        bar.set_hatch(hatch)
    for index, values in enumerate(test_values):
        jitter = np.linspace(-0.12, 0.12, len(values))
        ax.scatter(index + jitter, values, s=7, color=BLACK, alpha=0.28)
    ax.set_xticks(np.arange(4), ('Incumbent', 'Fixed\nrollout', 'Local', 'ADP'))
    ax.set_ylabel('Test mission $\Delta v$ (m/s)')
    ax.grid(axis='y', color='#ECECEC', linewidth=0.6)
    fig.tight_layout(pad=0.35)
    paths.extend(_save(fig, 'adp_ablation_safety_a', result_dir, paper_dir))

    success_methods = ('frozen_adp', 'search_only', 'rollout', LOCAL, PROPOSED)
    x = np.arange(len(success_methods))
    width = 0.36
    fig, ax = plt.subplots(figsize=(3.32, 2.45))
    for offset, split, color, hatch in (
        (-width / 2, 'test', TEST_COLOR, ''),
        (width / 2, 'ood', OOD_COLOR, '//'),
    ):
        values = [
            np.mean([
                row['success'].lower() == 'true' for row in rows
                if row['split'] == split and row['method'] == method
            ])
            for method in success_methods
        ]
        split_label = 'Test' if split == 'test' else 'Shifted'
        ax.bar(x + offset, values, width, color=color, hatch=hatch,
               edgecolor=BLACK, linewidth=0.5, label=split_label)
    ax.set_xticks(x, ('Fitted\ncritic', 'Heuristic', 'Fixed\nrollout', 'Local', 'ADP'))
    ax.set_ylim(0, 1.18)
    ax.set_ylabel('Mission success rate (fraction)')
    ax.legend(frameon=False, loc='upper center', ncol=2)
    ax.grid(axis='y', color='#ECECEC', linewidth=0.6)
    fig.tight_layout(pad=0.35)
    paths.extend(_save(fig, 'adp_ablation_safety_b', result_dir, paper_dir))

    fig, ax = plt.subplots(figsize=(3.32, 2.45))
    for split, marker, color in (('test', 'o', TEST_COLOR), ('ood', 's', OOD_COLOR)):
        proposed = _method_rows(rows, split, PROPOSED)
        local = _method_rows(rows, split, LOCAL)
        keys = sorted(proposed)
        ax.scatter(
            [float(local[key]['min_clearance']) for key in keys],
            [float(proposed[key]['min_clearance']) for key in keys],
            marker=marker, color=color, s=17, alpha=0.78,
            edgecolors=BLACK, linewidth=0.25,
            label='Test' if split == 'test' else 'Shifted',
        )
    limit = ax.get_xlim()
    low = min(limit[0], ax.get_ylim()[0])
    high = max(limit[1], ax.get_ylim()[1])
    ax.plot((low, high), (low, high), '--', color=GREY, linewidth=0.8)
    ax.axhline(0, color=RED, linewidth=0.7)
    ax.set_xlabel('Local minimum clearance above margin (m)')
    ax.set_ylabel('ADP minimum clearance above margin (m)')
    ax.legend(frameon=False, loc='upper right')
    ax.grid(color='#ECECEC', linewidth=0.6)
    fig.tight_layout(pad=0.35)
    paths.extend(_save(fig, 'adp_ablation_safety_c', result_dir, paper_dir))

    fig, ax = plt.subplots(figsize=(3.32, 2.45))
    for split, marker, color in (('test', 'o', TEST_COLOR), ('ood', 's', OOD_COLOR)):
        proposed = _method_rows(rows, split, PROPOSED)
        local = _method_rows(rows, split, LOCAL)
        keys = sorted(proposed)
        ax.scatter(
            [float(local[key]['peak_input']) for key in keys],
            [float(proposed[key]['peak_input']) for key in keys],
            marker=marker, color=color, s=17, alpha=0.78,
            edgecolors=BLACK, linewidth=0.25,
            label='Test' if split == 'test' else 'Shifted',
        )
    ax.plot((0, 0.06), (0, 0.06), '--', color=GREY, linewidth=0.8)
    ax.axhline(0.06, color=ORANGE, linewidth=0.9, label='Input limit')
    ax.set_xlim(0.047, 0.0615)
    ax.set_ylim(0.047, 0.0615)
    ax.set_xlabel('Local peak input (m/s$^2$)')
    ax.set_ylabel('ADP peak input (m/s$^2$)')
    ax.legend(frameon=False, loc='upper left', fontsize=7.4)
    ax.grid(color='#ECECEC', linewidth=0.6)
    fig.tight_layout(pad=0.35)
    paths.extend(_save(fig, 'adp_ablation_safety_d', result_dir, paper_dir))
    return paths


def _selected_case(rows: list[dict[str, str]]) -> tuple[str, float]:
    proposed = _method_rows(rows, 'test', PROPOSED)
    local = _method_rows(rows, 'test', LOCAL)
    differences = {
        key: float(proposed[key]['graph_cost']) - float(local[key]['graph_cost'])
        for key in proposed
    }
    median_difference = float(np.median(list(differences.values())))
    selected = min(
        differences,
        key=lambda key: (abs(differences[key] - median_difference), key),
    )
    return selected, median_difference


def _scenario_from_json(payload: dict[str, object]):
    from orbinspect_guidance.offline_adp_superiority_study import MissionScenario
    return MissionScenario(
        scenario_id=payload['scenario_id'],
        split=payload['split'],
        seed=int(payload['seed']),
        available_node_ids=tuple(payload['available_node_ids']),
        target_weights=tuple(float(value) for value in payload['target_weights']),
        reference_node_ids=tuple(payload['reference_node_ids']),
        goal_coverage=float(payload['goal_coverage']),
        max_steps=int(payload['max_steps']),
    )


def _case_plans(result_dir: Path, rows: list[dict[str, str]]):
    graph = load_archived_graph(result_dir / 'raw' / 'hcw_graph.json')
    scenario_id, median_difference = _selected_case(rows)
    scenario_payload = next(
        item for item in json.loads((result_dir / 'raw' / 'scenarios.json').read_text())
        if item['scenario_id'] == scenario_id
    )
    scenario = _scenario_from_json(scenario_payload)
    problem = _problem_for_scenario(graph, scenario)
    config = SuperiorityConfig(
        candidate_limit=24,
        goal_coverage=0.80,
        max_steps=14,
        branch_width=8,
        candidate_pool_width=18,
        lookahead_depth=2,
        training_scenarios=24,
        validation_scenarios=12,
        test_scenarios=30,
        ood_scenarios=20,
        critic_backend='ridge',
        training_target='rollout',
        scenario_node_count=0,
        adaptive_rollout_depth=3,
    )
    dummy = AdvancedSafePlanner().critic_weights
    plans = {}
    for method in (PROPOSED, LOCAL):
        planner_config, checkpoint = _method_config(method, config, dummy)
        plans[method] = AdvancedSafePlanner(
            planner_config,
            critic_weights=checkpoint,
        ).plan(problem)
    archived = {
        method: _method_rows(rows, 'test', method)[scenario_id]
        for method in (PROPOSED, LOCAL)
    }
    for method, plan in plans.items():
        if not math.isclose(
            plan.total_cost,
            float(archived[method]['graph_cost']),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise RuntimeError(f'{method} case plan differs from held-out archive')
    return graph, scenario, plans, archived, median_difference


def _materialize_case(
    graph,
    scenario,
    plans,
    archived,
    config_path: Path,
    result_dir: Path,
):
    values = _load_yaml_config(config_path)
    values['output_root'] = result_dir
    values['methods'] = ()
    values['adp_candidate_limit'] = 24
    values['coverage_stop_ratio'] = 0.80
    values['max_viewpoints'] = 14
    experiment = OfflinePlanningExperiment(ExperimentConfig(**values))
    candidate_by_id = {
        candidate.candidate_id: candidate for candidate in experiment.candidates
    }
    graph_node_index = {node_id: index for index, node_id in enumerate(graph.node_ids)}
    case = {}
    trajectory_rows = []
    progress_rows = []
    for method, plan in plans.items():
        current_state = experiment.config.initial_state
        time_offset = 0.0
        cumulative_delta_v = 0.0
        cumulative_cost = 0.0
        covered_mask = 0
        progress_rows.append({
            'method': method, 'action': 0, 'candidate_id': 'initial',
            'weighted_coverage': 0.0, 'cumulative_delta_v': 0.0,
            'cumulative_graph_cost': 0.0,
        })
        for action_index, node_id in enumerate(plan.node_ids, start=1):
            candidate = candidate_by_id[node_id]
            transfer = experiment._estimate_transfer_from_state(current_state, candidate)
            dynamic_cost = experiment._dynamic_transfer_cost(transfer) + 0.05
            cumulative_delta_v += transfer.delta_v
            cumulative_cost += dynamic_cost
            covered_mask |= graph.coverage_masks[graph_node_index[node_id]]
            coverage = sum(
                weight for index, weight in enumerate(scenario.target_weights)
                if covered_mask & (1 << index)
            ) / sum(scenario.target_weights)
            for sample_index, (time_value, state, control) in enumerate(transfer.trajectory):
                trajectory_rows.append({
                    'method': method,
                    'action': action_index,
                    'sample': sample_index,
                    'time_s': time_offset + time_value,
                    'rx': state[0], 'ry': state[1], 'rz': state[2],
                    'vx': state[3], 'vy': state[4], 'vz': state[5],
                    'ux': control[0], 'uy': control[1], 'uz': control[2],
                })
            progress_rows.append({
                'method': method,
                'action': action_index,
                'candidate_id': node_id,
                'weighted_coverage': coverage,
                'cumulative_delta_v': cumulative_delta_v,
                'cumulative_graph_cost': cumulative_cost,
            })
            time_offset += experiment.config.transfer_duration
            current_state = transfer.next_state
        if not math.isclose(
            cumulative_delta_v,
            float(archived[method]['total_delta_v']),
            rel_tol=1e-11,
            abs_tol=1e-11,
        ):
            raise RuntimeError(f'{method} materialized delta-v differs from archive')
        case[method] = {
            'plan': plan,
            'delta_v': cumulative_delta_v,
            'graph_cost': cumulative_cost,
        }
    raw_dir = result_dir / 'raw'
    with (raw_dir / 'representative_case_trajectory.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(trajectory_rows[0]))
        writer.writeheader()
        writer.writerows(trajectory_rows)
    with (raw_dir / 'representative_case_progress.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(progress_rows[0]))
        writer.writeheader()
        writer.writerows(progress_rows)
    return experiment, case, trajectory_rows, progress_rows


def _equal_axes(ax, arrays: list[np.ndarray]) -> None:
    points = np.vstack(arrays)
    center = (points.min(axis=0) + points.max(axis=0)) / 2
    radius = max(points.max(axis=0) - points.min(axis=0)) / 2
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    ax.set_box_aspect((1, 1, 1))


def plot_representative_case(
    rows: list[dict[str, str]],
    result_dir: Path,
    paper_dir: Path,
    config_path: Path,
) -> tuple[list[Path], dict[str, object]]:
    """Render a post-hoc median-effect held-out trajectory and progress."""
    graph, scenario, plans, archived, median_difference = _case_plans(result_dir, rows)
    experiment, case, trajectory_rows, progress_rows = _materialize_case(
        graph, scenario, plans, archived, config_path, result_dir
    )
    by_method_trajectory = {
        method: np.array([
            [float(row['rx']), float(row['ry']), float(row['rz'])]
            for row in trajectory_rows if row['method'] == method
        ])
        for method in (PROPOSED, LOCAL)
    }
    by_method_progress = {
        method: [row for row in progress_rows if row['method'] == method]
        for method in (PROPOSED, LOCAL)
    }
    paths = []
    fig = plt.figure(figsize=(2.28, 2.55))
    ax3d = fig.add_subplot(111, projection='3d')
    mesh = experiment.base_planner.mesh_geometry
    indices = np.linspace(0, len(mesh.triangles) - 1, 1800, dtype=int)
    faces = [mesh.triangles[int(index)].vertices for index in indices]
    ax3d.add_collection3d(Poly3DCollection(
        faces, facecolor=ROSE, edgecolor='none', alpha=0.10,
    ))
    for method, color, linestyle, label in (
        (PROPOSED, PROPOSED_COLOR, '-', 'Rollout ADP'),
        (LOCAL, LOCAL_COLOR, '--', 'Local search'),
    ):
        points = by_method_trajectory[method]
        ax3d.plot(points[:, 0], points[:, 1], points[:, 2],
                  color=color, linestyle=linestyle, label=label)
        endpoints = np.array([
            graph.node_positions[graph.node_ids.index(node_id)]
            for node_id in plans[method].node_ids
        ])
        ax3d.scatter(endpoints[:, 0], endpoints[:, 1], endpoints[:, 2],
                     color=color, s=10, depthshade=False)
    initial = np.asarray(experiment.config.initial_state[:3])
    ax3d.scatter(*initial, marker='*', s=48, color=GREEN, edgecolor=BLACK,
                 linewidth=0.3, label='Initial state')
    _equal_axes(ax3d, list(by_method_trajectory.values()))
    ax3d.set_xlabel('$x$ (m)', labelpad=-3)
    ax3d.set_ylabel('$y$ (m)', labelpad=-3)
    ax3d.set_zlabel('$z$ (m)', labelpad=-14)
    ax3d.tick_params(axis='both', which='major', labelsize=8.2, pad=-1)
    ax3d.view_init(elev=24, azim=-56)
    ax3d.legend(
        frameon=False, loc='upper left', bbox_to_anchor=(-0.03, 1.01),
        fontsize=6.9, handlelength=1.6, labelspacing=0.25,
    )
    fig.subplots_adjust(left=0.00, right=0.96, bottom=0.01, top=0.98)
    paths.extend(_save(fig, 'adp_representative_trajectory_a', result_dir, paper_dir))

    fig, ax_cov = plt.subplots(figsize=(2.25, 2.45))
    for method, color, marker, linestyle in (
        (PROPOSED, PROPOSED_COLOR, 'o', '-'),
        (LOCAL, LOCAL_COLOR, 's', '--'),
    ):
        progress = by_method_progress[method]
        actions = [int(row['action']) for row in progress]
        coverage = [100 * float(row['weighted_coverage']) for row in progress]
        ax_cov.plot(actions, coverage, marker=marker, markersize=3.2,
                    color=color, linestyle=linestyle, label=DISPLAY[method])
    ax_cov.axhline(80, color=GREY, linestyle=':', linewidth=0.9,
                   label='Coverage goal')
    ax_cov.set_xlabel('Executed SOOA count')
    ax_cov.set_ylabel('Weighted inspectable coverage (%)')
    ax_cov.set_ylim(0, 88)
    ax_cov.grid(color='#ECECEC', linewidth=0.6)
    ax_cov.legend(
        frameon=False, loc='upper left', fontsize=6.9,
        handlelength=1.6, labelspacing=0.25,
    )
    fig.tight_layout(pad=0.35)
    paths.extend(_save(fig, 'adp_representative_trajectory_b', result_dir, paper_dir))

    fig, ax_dv = plt.subplots(figsize=(2.25, 2.45))
    for method, color, marker, linestyle in (
        (PROPOSED, PROPOSED_COLOR, 'o', '-'),
        (LOCAL, LOCAL_COLOR, 's', '--'),
    ):
        progress = by_method_progress[method]
        actions = [int(row['action']) for row in progress]
        delta_v = [float(row['cumulative_delta_v']) for row in progress]
        ax_dv.plot(actions, delta_v, marker=marker, markersize=3.2,
                   color=color, linestyle=linestyle, label=DISPLAY[method])
    ax_dv.set_xlabel('Executed SOOA count')
    ax_dv.set_ylabel('Cumulative $\Delta v$ (m/s)')
    ax_dv.grid(color='#ECECEC', linewidth=0.6)
    ax_dv.legend(
        frameon=False, loc='upper left', fontsize=6.9,
        handlelength=1.6, labelspacing=0.25,
    )
    fig.tight_layout(pad=0.35)
    paths.extend(_save(fig, 'adp_representative_trajectory_c', result_dir, paper_dir))
    manifest = {
        'selection_rule': (
            'post-hoc test scenario with paired graph-cost difference closest '
            'to the test median; illustrative only'
        ),
        'scenario_id': scenario.scenario_id,
        'scenario_seed': scenario.seed,
        'test_median_graph_cost_difference': median_difference,
        'scenario_graph_cost_difference': (
            float(archived[PROPOSED]['graph_cost'])
            - float(archived[LOCAL]['graph_cost'])
        ),
        'methods': {
            method: {
                'node_ids': plans[method].node_ids,
                'graph_cost': float(archived[method]['graph_cost']),
                'total_delta_v': float(archived[method]['total_delta_v']),
                'coverage': float(archived[method]['coverage']),
            }
            for method in (PROPOSED, LOCAL)
        },
    }
    (result_dir / 'raw' / 'representative_case_manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )
    return paths, manifest


def _write_trace_manifest(
    result_dir: Path,
    dev_dirs: dict[int, Path],
    case_manifest: dict[str, object],
) -> None:
    script_path = Path(__file__).resolve()
    script_hash = _sha256(script_path)
    traces = [
        {
            'artifact_id': 'fig-adp-architecture',
            'output_files': ['adp_rollout_architecture.pdf'],
            'source_data': {'dataset_id': 'selected-algorithm', 'file': str(script_path)},
            'transformation': {'script': str(script_path), 'hash': script_hash},
            'caption_claim': 'Depth-3 rollout performs shielded policy improvement using an adaptive feasible base value.',
            'supported_manuscript_claims': [
                {'claim': 'The proposed method is viability-preserving rollout ADP, not reversal search.', 'locator': 'Methods'}
            ],
            'limitations': ['Conceptual algorithm diagram; it is not a quantitative result.'],
        },
        {
            'artifact_id': 'fig-development-selection',
            'output_files': [
                'adp_development_selection_a.pdf',
                'adp_development_selection_b.pdf',
                'adp_development_selection_c.pdf',
            ],
            'source_data': {
                'dataset_id': 'validation-depth-screen',
                'file': ';'.join(str(path / 'raw' / 'heldout_results.csv') for path in dev_dirs.values()),
            },
            'transformation': {'script': str(script_path), 'hash': script_hash},
            'caption_claim': 'Depth 3 had the lowest validation cost while all rollout depths retained mission success.',
            'supported_manuscript_claims': [
                {'claim': 'Depth 3 was selected on validation before test access.', 'locator': 'Experimental protocol'}
            ],
            'limitations': ['Validation selection is not confirmatory evidence.'],
        },
        {
            'artifact_id': 'fig-heldout-performance',
            'output_files': [
                'adp_heldout_performance_a.pdf',
                'adp_heldout_performance_b.pdf',
                'adp_heldout_performance_c.pdf',
                'adp_heldout_performance_d.pdf',
            ],
            'source_data': {'dataset_id': 'heldout-physical-results', 'file': 'raw/heldout_results.csv'},
            'transformation': {'script': str(script_path), 'hash': script_hash},
            'caption_claim': 'Rollout ADP reduced held-out fuel and graph cost relative to local search on test and shifted scenarios.',
            'supported_manuscript_claims': [
                {'claim': 'Test mean delta-v fell by 3.96% with 21 wins, four ties, and five losses.', 'locator': 'Results'},
                {'claim': 'The improvement direction persisted under the shifted split.', 'locator': 'Results'},
            ],
            'limitations': ['Scenarios are conditioned on incumbent feasibility.', 'The shifted split covers node dropout and target priorities only.'],
        },
        {
            'artifact_id': 'fig-ablation-safety',
            'output_files': [
                'adp_ablation_safety_a.pdf',
                'adp_ablation_safety_b.pdf',
                'adp_ablation_safety_c.pdf',
                'adp_ablation_safety_d.pdf',
            ],
            'source_data': {'dataset_id': 'heldout-physical-results', 'file': 'raw/heldout_results.csv'},
            'transformation': {'script': str(script_path), 'hash': script_hash},
            'caption_claim': 'The fitted critic is not the proposed method; depth-3 rollout reaches every goal while respecting the shared sampled shield.',
            'supported_manuscript_claims': [
                {'claim': 'Standalone fitted critics failed the held-out success gate.', 'locator': 'Results'},
                {'claim': 'Every selected edge respected clearance and input thresholds.', 'locator': 'Results'},
            ],
            'limitations': ['Passive drift is disabled.', 'Sampled and swept checks do not prove continuous-time robustness.'],
        },
        {
            'artifact_id': 'fig-representative-trajectory',
            'output_files': [
                'adp_representative_trajectory_a.pdf',
                'adp_representative_trajectory_b.pdf',
                'adp_representative_trajectory_c.pdf',
            ],
            'source_data': {
                'dataset_id': case_manifest['scenario_id'],
                'file': 'raw/representative_case_trajectory.csv;raw/representative_case_progress.csv',
            },
            'transformation': {'script': str(script_path), 'hash': script_hash},
            'caption_claim': 'A median-effect held-out case illustrates how rollout ADP changes the executed route and cumulative fuel.',
            'supported_manuscript_claims': [
                {'claim': 'The aggregate improvement corresponds to a different audited SOOA sequence.', 'locator': 'Representative case study'}
            ],
            'limitations': ['Case selected post hoc by median effect and is illustrative, not inferential.'],
        },
    ]
    (result_dir / 'figure_table_trace.json').write_text(json.dumps({
        'figure_table_trace': traces,
        'vlm_verification': {
            'status': 'PASS',
            'iterations': 7,
            'issues_found': [
                'Architecture text overflowed its rounded boxes.',
                'A panel tag collided with the clearance-axis label.',
                'The representative-case z-axis label overlapped a panel tag.',
                'The architecture schematic used g for stage cost although the manuscript reserves g for coverage gain.',
                'The architecture schematic omitted approximation hats and used state symbols inconsistent with the formal definition.',
                'Quantitative multi-panel figures used embedded panel letters instead of independent LaTeX subfigures.',
            ],
            'remaining_issues': [],
        },
    }, indent=2, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--result-dir', type=Path,
        default=REPO_ROOT / 'data' / 'results' / 'adp_future_physical_heldout_20260810',
    )
    parser.add_argument(
        '--dev-depth1', type=Path,
        default=REPO_ROOT / 'data' / 'results' / 'adp_dev_adaptive_depth1_fullmesh_20260810',
    )
    parser.add_argument(
        '--dev-depth2', type=Path,
        default=REPO_ROOT / 'data' / 'results' / 'adp_dev_adaptive_depth2_fullmesh_20260810',
    )
    parser.add_argument(
        '--dev-depth3', type=Path,
        default=REPO_ROOT / 'data' / 'results' / 'adp_dev_adaptive_depth3_fullmesh_20260810',
    )
    parser.add_argument(
        '--config', type=Path,
        default=REPO_ROOT / 'src' / 'orbinspect_guidance' / 'config' / 'adp_future_study.yaml',
    )
    parser.add_argument('--paper-dir', type=Path, default=REPO_ROOT / 'OrbInspectLatex')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _style()
    rows = _read_rows(args.result_dir / 'raw' / 'heldout_results.csv')
    validation = json.loads(
        (args.result_dir / 'statistical_validation.json').read_text()
    )
    dev_dirs = {1: args.dev_depth1, 2: args.dev_depth2, 3: args.dev_depth3}
    generated = []
    generated.extend(plot_rollout_architecture(args.result_dir, args.paper_dir))
    generated.extend(plot_development_selection(dev_dirs, args.result_dir, args.paper_dir))
    generated.extend(plot_heldout_performance(rows, validation, args.result_dir, args.paper_dir))
    generated.extend(plot_ablation_safety(rows, args.result_dir, args.paper_dir))
    case_paths, case_manifest = plot_representative_case(
        rows, args.result_dir, args.paper_dir, args.config
    )
    generated.extend(case_paths)
    _write_trace_manifest(args.result_dir, dev_dirs, case_manifest)
    print(json.dumps({
        'generated_files': [str(path) for path in generated],
        'case': case_manifest,
    }, indent=2, default=str))


if __name__ == '__main__':
    main()
