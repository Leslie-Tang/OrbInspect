#!/usr/bin/env python3
"""Render the post-selection depths 1--6 diagnostic in the established style.

Contract: a quantitative three-panel grid shows common-completion graph cost,
all-scenario runtime, and planner-screen workload. The original panel sizes,
palette, markers, and red square at the frozen depth-three setting are kept.
This reports a resource trade-off, not an optimal-depth selection procedure.
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

import generate_depth_tradeoff_figure as style
from generate_required_target_figures import read_rows, success
from write_required_target_tables import number, table

ROOT = Path(__file__).resolve().parents[2]


def validate_provenance(rows: list[dict], manifest: dict, scenarios: list[dict]) -> None:
    """Reject rows from another method or campaign with reused scenario names."""
    by_id = {s['scenario_id']: s for s in scenarios}
    if len(by_id) != 12 or set(by_id) != set(manifest['scenario_ids']):
        raise ValueError('Frozen diagnostic scenario inventory must contain exactly 12 cases')
    required_n = len(manifest['required_target_ids'])
    for row in rows:
        scenario = by_id.get(row['scenario_id'])
        if (scenario is None or row['method'] != 'adaptive_rollout_adp'
                or row['profile_id'] != manifest['primary_profile']
                or row['profile_id'] != scenario['profile_id']
                or int(row['scenario_seed']) != int(scenario['seed'])
                or int(row['required_target_count']) != required_n):
            raise ValueError('Depth row does not match the frozen method, requirement, or scenario')


def summarize(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Compare every depth on identical cases and a fixed success intersection."""
    depths = sorted({int(r['adaptive_rollout_depth']) for r in rows})
    if depths != list(range(1, 7)):
        raise ValueError(f'Complete depths 1--6 required; observed {depths}')
    groups = {d: [r for r in rows if int(r['adaptive_rollout_depth']) == d] for d in depths}
    ids = {r['scenario_id'] for r in groups[1]}
    if len(ids) != 12 or any(len(g) != 12 or {r['scenario_id'] for r in g} != ids for g in groups.values()):
        raise ValueError('Each depth must contain the same 12 unique validation cases')
    if any(r['split'] != 'validation' for r in rows):
        raise ValueError('Only validation data may enter the depth diagnostic')
    common = sorted(set.intersection(*[{r['scenario_id'] for r in g if success(r)} for g in groups.values()]))
    if not common:
        raise ValueError('No common completed cases: do not draw a physical-cost comparison')
    report = []
    for d, group in groups.items():
        completed = [r for r in group if r['scenario_id'] in common]
        report.append(dict(
            depth=d, n=len(group), success_n=sum(success(r) for r in group), common_success_n=len(common),
            mean_graph_cost=float(np.mean([float(r['graph_cost']) for r in completed])),
            mean_delta_v=float(np.mean([float(r['total_delta_v']) for r in completed])),
            mean_penalized_cost=float(np.mean([float(r['penalized_cost']) for r in group])),
            median_time_s=float(np.median([float(r['online_time_s']) for r in group])),
            min_time_s=min(float(r['online_time_s']) for r in group),
            max_time_s=max(float(r['online_time_s']) for r in group),
            median_common_success_time_s=float(np.median([float(r['online_time_s']) for r in completed])),
            mean_safety_evaluations=float(np.mean([float(r['safe_action_evaluations']) for r in group])),
        ))
    ref = report[2]
    for row in report:
        row['cost_difference_vs_depth3_pct'] = 100 * (row['mean_graph_cost']/ref['mean_graph_cost']-1)
        row['time_ratio_vs_depth3'] = row['median_time_s']/ref['median_time_s']
        row['screen_ratio_vs_depth3'] = row['mean_safety_evaluations']/ref['mean_safety_evaluations']
    return report, common


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--depth-study', type=Path, required=True)
    args = parser.parse_args()
    study = args.depth_study.resolve()
    source = study/'raw/validation_depth_results.csv'
    rows = read_rows(source)
    manifest = json.loads((study/'config_snapshot/freeze_manifest.json').read_text())
    for relative, expected in manifest['input_hashes'].items():
        if hashlib.sha256((study/relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Frozen input checksum mismatch: {relative}')
    validate_provenance(rows, manifest, json.loads((study/'raw/scenarios.json').read_text()))
    report, common = summarize(rows)
    paper = ROOT/'OrbInspectLatex/figures/required_target'
    paper.mkdir(parents=True, exist_ok=True)
    (study/'figures').mkdir(exist_ok=True)
    style._style()
    plt.rcParams['svg.fonttype'] = 'none'
    generated = []
    for field, ylabel, suffix, log in (
        ('mean_graph_cost', 'Mean complete-task graph cost, $J$', 'a', False),
        ('median_time_s', 'Median planning time (s)', 'b', True),
        ('mean_safety_evaluations', 'Mean safety-screen count', 'c', True),
    ):
        x, y = [r['depth'] for r in report], [r[field] for r in report]
        fig, ax = plt.subplots(figsize=(2.18, 2.45))
        ax.plot(x, y, color=style.BLUE, marker='o', markersize=4.6,
                markerfacecolor='white', markeredgewidth=1.05, zorder=2)
        ax.scatter([3], [y[2]], color=style.RED, marker='s', s=38,
                   edgecolor=style.BLACK, linewidth=.35, zorder=3)
        if log:
            ax.set_yscale('log')
        ax.set_xticks(x)
        ax.set(xlabel='Rollout depth, $d$', ylabel=ylabel)
        ax.grid(axis='y', which='both', color='#ECECEC', linewidth=.6)
        note = f'common complete n = {len(common)}' if suffix == 'a' else 'post-selection diagnostic'
        ax.text(.98 if suffix == 'a' else .02, .97, note, transform=ax.transAxes,
                ha='right' if suffix == 'a' else 'left', va='top', color=style.GREY, fontsize=7)
        fig.tight_layout(pad=.35)
        for extension in ('pdf', 'png', 'svg'):
            path = study/'figures'/f'adp_depth_tradeoff_{suffix}.{extension}'
            fig.savefig(path)
            shutil.copy2(path, paper/path.name)
            generated.append(str(path.relative_to(ROOT)))
        plt.close(fig)

    lines = []
    for r in report:
        cells = [str(r['depth']), f'{r["success_n"]}/{r["n"]}', number(r['mean_graph_cost']),
                 f'{r["cost_difference_vs_depth3_pct"]:+.2f}', number(r['median_time_s'], 4),
                 number(r['time_ratio_vs_depth3'], 2), f'{r["mean_safety_evaluations"]:,.0f}',
                 number(r['screen_ratio_vs_depth3'], 2)]
        if r['depth'] == 3:
            cells = [r'\textbf{' + c + '}' for c in cells]
        lines.append(' & '.join(cells))
    caption = (f'Post-selection required-target depth diagnostic on the same 12 validation scenarios. '
               f'Graph-cost means use the {len(common)} scenarios completed at all six depths. '
               r'Time and screen counts include all 12 cases; ratios use depth three. '
               r'Negative $\Delta J$ denotes lower mean cost. All depths were rerun sequentially; the primary depth-three test results are unchanged')
    tex = table(caption, 'tab:depth-sensitivity', 'crrrrrrr',
                r'Depth & Complete & Mean $J$ & $\Delta J$ (\%) & Median time (s) & Time ($\times$) & Mean screens & Screens ($\times$)', lines)
    (ROOT/'OrbInspectLatex/data/required_target_depth_table.tex').write_text(tex)
    (study/'raw/manuscript_depth_table.tex').write_text(tex)
    with (study/'raw/manuscript_depth_statistics.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(report[0]))
        writer.writeheader()
        writer.writerows(report)
    manifest = dict(
        source=str(source.relative_to(ROOT)), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        purpose='Post-selection diagnostic; depth three remains the frozen primary policy, not a proven optimum.',
        common_completed_scenarios=common, per_depth=report, generated_files=generated,
        cost_statistic='Mean on the same common-completion set; not a confidence interval.',
        timing_statistic='Median on all 12 cases, including failures; one sequential pass, no timing repeat CI.',
        workload_statistic='Mean selected planner screen count on all 12 cases, excluding separately timed initializer.',
    )
    (study/'figures/required_target_depth_figure_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    shutil.copy2(study/'figures/required_target_depth_figure_manifest.json',paper/'required_target_depth_figure_manifest.json')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
