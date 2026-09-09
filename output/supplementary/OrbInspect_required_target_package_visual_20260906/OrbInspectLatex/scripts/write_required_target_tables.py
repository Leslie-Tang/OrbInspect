#!/usr/bin/env python3
"""Write IEEE tables and numerical macros from the required-target archive."""

from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

from generate_required_target_figures import interval, paired, read_rows, success

ROOT = Path(__file__).resolve().parents[2]
ADP, LOCAL = 'adaptive_rollout_adp', 'seeded_local_search'
METHODS = ('incumbent', 'one_step_adp', LOCAL, ADP)
DISPLAY = {'incumbent': 'Task-aware incumbent', 'one_step_adp': 'One-step ADP',
           LOCAL: 'ADP-seeded local search', ADP: 'Depth-three ADP'}


def number(value: float, decimals: int = 3) -> str:
    return f'{value:.{decimals}f}' if math.isfinite(value) else '--'


def mean(rows: list[dict], field: str) -> float:
    return float(np.mean([float(r[field]) for r in rows])) if rows else math.nan


def table(caption: str, label: str, spec: str, header: str, lines: list[str], wide=True) -> str:
    env = 'table*' if wide else 'table'
    return (f'\\begin{{{env}}}[t]\n  \\centering\n  \\caption{{{caption}}}\n'
            f'  \\label{{{label}}}\n  \\renewcommand{{\\arraystretch}}{{1.08}}\n'
            '  \\setlength{\\tabcolsep}{5pt}\n  \\footnotesize\n'
            f'  \\begin{{tabular}}{{@{{}}{spec}@{{}}}}\n    \\toprule\n'
            f'    {header} \\\\\n    \\midrule\n'
            + '\n'.join('    ' + x + r' \\' for x in lines)
            + f'\n    \\bottomrule\n  \\end{{tabular}}\n\\end{{{env}}}\n')


def profile(row: dict) -> str:
    return row.get('profile_id', row.get('profile', row.get('mission_profile', 'all')))


def field(row: dict, *names: str, default=''):
    return next((row[name] for name in names if name in row), default)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--development-study', type=Path, required=True)
    args = parser.parse_args()
    study = args.study.resolve()
    src = study / 'raw' / 'scenario_results.csv'
    if not src.exists():
        src = study / 'raw' / 'heldout_results.csv'
    frozen = json.loads((study / 'config_snapshot/freeze_manifest.json').read_text())
    rows = [r for r in read_rows(src) if r['profile_id'] == frozen['primary_profile']]
    development = read_rows(args.development_study / 'raw/scenario_results.csv')
    out = ROOT / 'OrbInspectLatex' / 'data'
    out.mkdir(exist_ok=True)
    report = {'source': str(src.relative_to(ROOT)), 'primary_profile': frozen['primary_profile'], 'splits': {}, 'profiles': {}}
    macros = {}

    def write(name: str, value: str) -> None:
        (out / f'required_target_{name}.tex').write_text(value)

    aggregate, profile_lines, paired_lines, objective_lines = [], [], [], []
    for split, display in (('test', 'Test'), ('ood', 'Shifted')):
        subset = [r for r in rows if r['split'] == split]
        main_rows = [r for r in subset if r['method'] == ADP]
        local_rows = [r for r in subset if r['method'] == LOCAL]
        n, wins = len(main_rows), sum(success(r) for r in main_rows)
        prefix = 'RTTest' if split == 'test' else 'RTOod'
        macros[prefix + 'N'] = str(n)
        macros[prefix + 'Success'] = str(wins)
        macros['RTLocalTestSuccess' if split == 'test' else 'RTLocalOodSuccess'] = str(sum(success(r) for r in local_rows))
        report['splits'][split] = {'n': n, 'adp_success': wins, 'methods': {}}
        for method in METHODS:
            all_rows = [r for r in subset if r['method'] == method]
            complete = [r for r in all_rows if success(r)]
            vals = {'n': len(all_rows), 'success': len(complete),
                    'mean_delta_v_complete': mean(complete, 'total_delta_v'),
                    'mean_graph_cost_complete': mean(complete, 'graph_cost'),
                    'mean_actions_complete': mean(complete, 'selected_count'),
                    'mean_penalized_cost_all': mean(all_rows, 'penalized_cost')}
            report['splits'][split]['methods'][method] = vals
            aggregate.append(f'{display} & {DISPLAY[method]} & {len(complete)}/{len(all_rows)} & '
                             f'{number(vals["mean_actions_complete"], 2)} & '
                             f'{number(vals["mean_delta_v_complete"])} & '
                             f'{number(vals["mean_graph_cost_complete"])} & '
                             f'{number(vals["mean_penalized_cost_all"])}')
        pairs = paired(rows, split)
        macros['RTJointTestN' if split == 'test' else 'RTJointOodN'] = str(len(pairs))
        all_local = {r['scenario_id']: r for r in local_rows}
        for metric, label in (('penalized_cost', r'$J_{\mathrm{pen}}$ (all)'), ('graph_cost', r'$J$'), ('total_delta_v', r'$\Delta v$ (m/s)')):
            metric_pairs = [(a, all_local[a['scenario_id']]) for a in main_rows] if metric == 'penalized_cost' else pairs
            diffs = np.array([float(a[metric]) - float(b[metric]) for a, b in metric_pairs])
            lo, hi = interval(diffs)
            w, t, l = int(np.sum(diffs < -1e-9)), int(np.sum(abs(diffs) <= 1e-9)), int(np.sum(diffs > 1e-9))
            sign_p = min(1., 2 * sum(math.comb(w+l, k) for k in range(min(w, l)+1)) / 2**(w+l)) if w+l else 1.
            avg = float(diffs.mean()) if len(diffs) else math.nan
            macros[prefix + {'graph_cost':'CostDiff', 'total_delta_v':'DvDiff', 'penalized_cost':'PenaltyDiff'}[metric]] = number(avg)
            report['splits'][split][metric + '_paired'] = {
                'n': len(metric_pairs), 'mean': avg, 'ci': [lo, hi], 'wins_ties_losses': [w,t,l], 'sign_p': sign_p}
            p_text = f'${sign_p / 10**math.floor(math.log10(sign_p)):.2f}\\times10^{{{math.floor(math.log10(sign_p))}}}$' if 0 < sign_p < .0001 else number(sign_p, 4)
            paired_lines.append(f'{display} & {label} & {len(metric_pairs)} & {number(avg)} & '
                                f'$[{number(lo)},{number(hi)}]$ & {w}/{t}/{l} & {p_text}')
        for p in sorted(set(profile(r) for r in development)):
            a = [r for r in development if profile(r) == p and r['split'] == split and r['method'] == ADP]
            b = [r for r in development if profile(r) == p and r['split'] == split and r['method'] == 'local_search']
            required = field(a[0], 'required_target_count', 'required_count', default='--')
            report['profiles'][f'{p}:{split}'] = {'n':len(a), 'adp_success':sum(success(r) for r in a),
                                                'local_success':sum(success(r) for r in b), 'required_n':required}
            profile_lines.append(f'{p.replace("_", " ")} & {required} & {display} & '
                                 f'{sum(success(r) for r in a)}/{len(a)} & {sum(success(r) for r in b)}/{len(b)}')
        for method in sorted(set(r['method'] for r in subset) - set(METHODS)):
            diagnostic = [r for r in subset if r['method'] == method]
            count_field = next((k for k in ('required_complete', 'required_targets_covered', 'required_success') if k in diagnostic[0]), None)
            if count_field:
                completed = sum(str(r[count_field]).lower() in ('true','1') for r in diagnostic)
            else:
                completed = sum(float(field(r, 'required_coverage', 'required_completion', default=0)) >= 1.-1e-12 for r in diagnostic)
            objective_lines.append(f'{display} & {method.replace("_", " ")} & {completed}/{len(diagnostic)}')
            report['splits'][split][method + '_required_complete'] = completed

    validation = read_rows(study / 'raw' / 'validation_depth_results.csv')
    macros['RTValidationN'] = str(len({r['scenario_id'] for r in validation}))
    requirements = json.loads((args.development_study / 'config_snapshot' / 'required_targets.json').read_text())
    profile_manifest = []
    for p in requirements['profiles']:
        region_counts = '/'.join(str(len(ids)) for ids in p['region_target_ids'].values())
        ids = ', '.join(target.removeprefix('mesh_') for target in p['required_target_ids'])
        profile_manifest.append(f'{p["profile_id"]} & {p["required_target_count"]} & {region_counts} & {ids}')
    write('profiles', table('Frozen synthetic required-target profiles. Three equal-width slabs span the mesh longest axis; each slab uses centroid-first, normalized farthest-point selection. IDs omit the common mesh prefix. The nine-item profile is primary',
                            'tab:required-profiles', 'lrrl', 'Profile & Items & Slab counts & Required sample IDs', profile_manifest))
    depths = sorted({int(r['adaptive_rollout_depth']) for r in validation})
    depth_groups = {d: [r for r in validation if int(r['adaptive_rollout_depth']) == d] for d in depths}
    common_depth = set.intersection(*[{r['scenario_id'] for r in group if success(r)} for group in depth_groups.values()])
    depth_lines, depth_report = [], []
    for d, group in depth_groups.items():
        completed = [r for r in group if r['scenario_id'] in common_depth]
        time = float(np.median([float(r['online_time_s']) for r in group]))
        cost, evaluations = mean(completed, 'graph_cost'), mean(group, 'safe_action_evaluations')
        depth_lines.append(f'{d} & {sum(success(r) for r in group)}/{len(group)} & {len(completed)} & {number(cost)} & {number(mean(group, "penalized_cost"))} & {number(time, 4)} & {evaluations:,.0f}')
        depth_report.append({'depth':d,'success_n':sum(success(r) for r in group),'n':len(group),'common_success_n':len(completed),
                             'mean_common_cost':cost,'mean_penalized_cost':mean(group,'penalized_cost'),
                             'median_time_s':time,'mean_safety_evaluations':evaluations})
    report['validation_depth'] = depth_report
    write('depth_table', table('Required-target validation depth diagnostic. Graph-cost means use the same scenarios completed at all depths. Penalized cost, timing, and safety-screen counts include every validation scenario; depth three was fixed before this diagnostic',
                               'tab:depth-sensitivity', 'crrrrrr', r'Depth & Complete & Common pairs & Mean $J$ & Penalized $J$ & Median time (s) & Mean evaluations', depth_lines))
    all_groups = [{r['scenario_id'] for r in rows if r['split'] == 'test' and r['method'] == m and success(r)} for m in METHODS[1:]]
    macros['RTFourMethodN'] = str(len(set.intersection(*all_groups)))
    write('aggregate', table('Required-target results. Resource means use successful routes of each method; the final column includes every scenario with the fixed failure penalty',
                            'tab:paired-aggregate', 'llrrrrr',
                            r'Split & Method & Complete & Mean SOOAs & Mean $\Delta v$ (m/s) & Mean $J$ & Penalized $J$', aggregate))
    write('profile_results', table('First-campaign development results by fixed profile. Local search in this campaign was initialized by the greedy incumbent, unlike the fresh confirmation comparator. Profiles use different seeds, so cross-profile rates are descriptive',
                                  'tab:required-profile-results', 'lr lrr'.replace(' ', ''),
                                  'Profile & Required items & Split & ADP complete & Local complete', profile_lines))
    write('paired', table('ADP-minus-seeded-local effects. The predeclared penalized endpoint includes all scenarios; physical resources and graph cost use jointly complete pairs. Intervals are percentile 95\\% paired-bootstrap intervals; sign tests exclude ties',
                         'tab:required-paired', 'llrrlrr',
                         r'Split & Endpoint & Pairs & Mean difference & 95\% interval & Win/tie/loss & Sign-test $p$', paired_lines))
    write('objective_ablation', table('Required-target completion under the coverage-only objective. The required set is identical to that of the main comparison',
                                     'tab:required-objective', 'llr', 'Split & Objective ablation & All required complete', objective_lines, wide=False))
    write('numbers', '\n'.join(f'\\newcommand{{\\{name}}}{{{value}}}' for name, value in macros.items()) + '\n')
    (study / 'raw' / 'manuscript_statistics.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
