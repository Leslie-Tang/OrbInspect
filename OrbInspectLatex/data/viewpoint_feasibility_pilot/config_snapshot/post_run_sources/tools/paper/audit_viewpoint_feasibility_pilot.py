#!/usr/bin/env python3
"""Reconstruct a completed viewpoint pilot from frozen inputs and raw arrays."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import random

import run_viewpoint_feasibility_pilot as pilot
import numpy as np


def audit(output: Path) -> dict:
    cfg = pilot.verify(output)
    scenarios = json.loads((output/'raw/scenarios.json').read_text())
    results = json.loads((output/'raw/benchmark_results.json').read_text())
    certificates = json.loads((output/'raw/feasibility.json').read_text())
    by_case = {s['scenario_id']: s for s in scenarios}
    cert_by_case = {r['scenario_id']: r for r in certificates}
    rows = {(r['scenario_id'], r['method']): r for r in results}
    assert len(by_case) == len(scenarios) == len(certificates) == len(cert_by_case)
    assert len(rows) == len(results) == len(scenarios)*len(cfg['methods'])
    assert len({s['seed'] for s in scenarios}) == len(scenarios)
    prior = json.loads((pilot.ROOT/cfg['source_bundle']/'raw/scenarios.json').read_text())
    assert not {s['seed'] for s in prior} & {s['seed'] for s in scenarios}
    original_goals = json.loads((output/'config_snapshot/required_targets.json').read_text())['profiles'][0]
    geometry = json.loads((output/'raw/geometry.json').read_text())
    targets = {t['target_id']: t for t in geometry['targets']}
    edges_checked = numeric_checked = base_bound_cases = lower_bound_checks = 0
    graph_by_id = {}
    for gid in sorted({s['graph_id'] for s in scenarios}):
        directory = output/'raw'/gid
        graph = pilot.load_archived_graph(directory/'hcw_graph.json')
        graph_by_id[gid] = graph
        candidates = json.loads((directory/'candidates.json').read_text())
        attempts = {a['candidate_id']: a for a in json.loads((directory/'candidate_attempts.json').read_text())}
        positions = dict(zip(graph.node_ids, graph.node_positions))
        assert len(candidates) == len(graph.node_ids) == len(set(graph.node_ids))
        for item, mask in zip(candidates, graph.coverage_masks):
            c = item['candidate']; target = targets[c['source_target_id']]
            assert attempts[c['candidate_id']]['source_visible']
            assert tuple(c['position']) == positions[c['candidate_id']]
            delta = np.asarray(c['position'])-np.asarray(target['position'])
            radius = float(np.linalg.norm(delta))
            assert cfg['standoff_range_m'][0]-1e-9 <= radius <= cfg['standoff_range_m'][1]+1e-9
            cosine = float(np.dot(delta/radius, pilot.unit(target['normal'])))
            assert cosine >= math.cos(math.radians(cfg['normal_cone_angle_deg']))-1e-9
            assert mask == int(item['coverage_mask'],0)
            assert mask == sum(1 << i for i, t in enumerate(graph.target_ids) if t in item['all_visible_ids'])
            assert c['source_target_id'] in item['all_visible_ids']
        for tid in original_goals['required_target_ids']:
            selected = [r['candidate']['position'] for r in candidates if r['candidate']['source_target_id']==tid]
            assert len(selected) == cfg['views_per_required_target']
            assert all(math.dist(a,b) >= cfg['minimum_view_separation_m']-1e-9
                       for i,a in enumerate(selected) for b in selected[i+1:])
        audit_rows = list(csv.DictReader((directory/'edge_audits.csv').open()))
        with np.load(directory/'edge_samples.npz') as arrays:
            states = arrays['states']; commands = arrays['controls']; dt = float(arrays['dt'])
            assert len(states) == len(commands) == len(graph.edges) == len(audit_rows)
            for i, edge in enumerate(graph.edges):
                delta_v = float(np.linalg.norm(commands[i],axis=1).sum()*dt)
                peak = float(np.linalg.norm(commands[i],axis=1).max())
                speed = float(np.linalg.norm(states[i,:,3:],axis=1).max())
                destination = np.asarray(positions[edge.target_id])
                terminal_error = float(np.linalg.norm(states[i,-1,:3]-destination))
                tracking = float(np.sqrt(np.mean(np.sum((states[i,:,:3]-destination)**2,axis=1))))
                assert math.isclose(delta_v,edge.delta_v,abs_tol=1e-9)
                assert math.isclose(peak,edge.peak_input,abs_tol=1e-9)
                assert math.isclose(tracking,edge.tracking_error,abs_tol=1e-9)
                assert math.isclose(5*delta_v+.18*tracking+120*max(0,-edge.min_clearance),edge.stage_cost,abs_tol=1e-8)
                assert math.isclose(speed,float(audit_rows[i]['max_speed']),abs_tol=1e-9)
                if edge.feasible:
                    assert terminal_error <= .5 and np.linalg.norm(states[i,-1,3:]) <= .05
                    assert peak <= .06+1e-9 and speed <= 2 and edge.min_clearance >= 0
                numeric_checked += 1
    for case, payload in by_case.items():
        graph = graph_by_id[payload['graph_id']]
        assert payload['required_target_ids'] == original_goals['required_target_ids']
        assert payload['required_target_mask'] == original_goals['required_target_mask']
        rng = random.Random(payload['seed'])
        p = 0 if payload['split']=='reference' else rng.uniform(*cfg[f"{payload['split']}_dropout_range"])
        assert p == payload['sampled_dropout_probability']
        assert payload['available_node_ids'] == [n for n in graph.node_ids if rng.random() >= p]
        problem = pilot.original.make_problem(graph,payload)
        certificate = cert_by_case[case]
        if certificate['status']=='feasible':
            assert pilot.validate_route(problem,tuple(certificate['node_ids']),cfg['action_cost'])['success']
        elif certificate['reason']=='missing_required_visibility':
            union = 0
            for node in problem.nodes:
                union |= node.coverage_mask
            assert problem.required_target_mask & ~union == certificate['missing_required_mask'] != 0
        else:
            assert certificate['status']=='unresolved' or certificate['reason'] in {
                'unreachable_required_visibility','milp_infeasible','zero_action_budget'}
        if certificate['optimal']:
            assert certificate['solver_status']==0 or certificate['reason']=='empty_requirement'
            assert math.isclose(certificate['graph_cost'],certificate['lower_bound'],rel_tol=1e-7,abs_tol=1e-6)
        for method in cfg['methods']:
            row = rows[(case,method)]
            route = tuple(filter(None,row['route_node_ids'].split(';')))
            metrics = pilot.validate_route(problem,route,cfg['action_cost'])
            assert metrics['success']==row['success']
            assert metrics['covered_mask']==row['covered_mask']
            assert math.isclose(metrics['graph_cost'],row['graph_cost'],abs_tol=1e-8)
            assert math.isclose(metrics['total_delta_v'],row['total_delta_v'],abs_tol=1e-8)
            if row['success']:
                assert certificate['status']!='infeasible'
                if certificate['lower_bound'] is not None:
                    assert row['graph_cost'] >= certificate['lower_bound']-1e-6
                    lower_bound_checks += 1
            edges_checked += len(route)
        base = rows[(case,'incumbent')]
        for method in ('one_step_adp','adaptive_rollout_adp'):
            candidate = rows[(case,method)]
            if base['success'] and candidate['success']:
                assert candidate['graph_cost'] <= base['graph_cost']+1e-7
                base_bound_cases += 1
    paired = []
    for split in ('reference','nominal','shifted'):
        for other in ('incumbent','one_step_adp','independent_milp'):
            pairs = [(rows[(s['scenario_id'],'adaptive_rollout_adp')],rows[(s['scenario_id'],other)])
                     for s in scenarios if s['split']==split]
            pairs = [(a,b) for a,b in pairs if a['success'] and b['success']]
            paired.append({'split':split,'comparator':other,'jointly_completed':len(pairs),
                'mean_adp_minus_comparator_cost':float(np.mean([a['graph_cost']-b['graph_cost'] for a,b in pairs])) if pairs else None,
                'mean_adp_minus_comparator_delta_v':float(np.mean([a['total_delta_v']-b['total_delta_v'] for a,b in pairs])) if pairs else None,
                'cost_wins_ties_losses':dict(Counter('win' if a['graph_cost']<b['graph_cost']-1e-8 else 'loss'
                    if a['graph_cost']>b['graph_cost']+1e-8 else 'tie' for a,b in pairs))})
    report = {'status':'passed','scenarios_verified':len(scenarios),'method_rows_verified':len(results),
              'numeric_edge_records_verified':numeric_checked,'selected_edges_verified':edges_checked,
              'completed_base_cost_bounds_checked':base_bound_cases,
              'independent_lower_bounds_checked':lower_bound_checks,'paired_comparisons':paired,
              'auditor_sha256':pilot.sha(Path(__file__))}
    pilot.write_json(output/'raw/independent_audit.json',report)
    write_review(output, report, certificates, results)
    print(json.dumps(report,indent=2))
    return report


def write_review(output: Path, audit_report: dict, certificates: list, results: list) -> None:
    """Add interpretation and explicit limit/gap denominators to derived reports."""
    summary = json.loads((output/'summary.json').read_text())
    limit_rows = []
    for comparison in summary['comparisons']:
        split, method = comparison['split'], comparison['method']
        if method == 'independent_milp':
            limited = [c for c in certificates if c['split']==split and c['solver_status']==1]
            with_witness = sum(c['status']=='feasible' for c in limited)
            total = len(limited)
        else:
            total = sum(r['split']==split and r['method']==method and
                        r['termination_reason']=='time_limit' for r in results)
            with_witness = 0
        comparison['time_limits'] = total
        comparison['time_limit_with_feasible_witness'] = with_witness
        comparison['time_limit_without_feasible_witness'] = total-with_witness
        limit_rows.append({'split':split,'method':method,'time_limit_reached':total,
                           'feasible_witness_at_limit':with_witness})
    summary['post_run_audit'] = {k:v for k,v in audit_report.items() if k!='paired_comparisons'}
    summary['post_run_review'] = 'review.md'
    pilot.write_json(output/'summary.json',summary)
    pilot.write_csv(output/'raw/time_limit_counts.csv',limit_rows)
    adp = [r for r in results if r['method']=='adaptive_rollout_adp']
    gaps = [r['optimality_gap_percent'] for r in adp if r['optimality_gap_percent'] is not None]
    stats = {k:next(r for r in summary['comparisons'] if r['split']==k and
                   r['method']=='adaptive_rollout_adp') for k in ('reference','nominal','shifted')}
    labels = {'incumbent':'Greedy base policy','one_step_adp':'One-step ADP',
              'adaptive_rollout_adp':'Depth-three ADP','independent_milp':'Independent MILP'}
    lines = ['# Viewpoint feasibility pilot: completed review', '',
        'The pilot supports a larger, separately frozen confirmation using redundant viewpoints. '
        'Depth-three ADP completed every independently feasible case. The four remaining failures '
        'were impossible in their available viewpoint libraries because all views of a required '
        'target had been removed. This does not prove impossibility in continuous space.', '',
        'The experiment contains three newly sampled 33-view graphs on the same ISS geometry. '
        'Each required target has at least three valid views before dropout. All 63 generated '
        'cases were retained: three reference, 30 nominal and 30 shifted cases.', '',
        '| Method | Nominal completion | Shifted completion | Nominal median time (s) | Shifted median time (s) |',
        '|---|---:|---:|---:|---:|']
    for method, label in labels.items():
        n = next(r for r in summary['comparisons'] if r['split']=='nominal' and r['method']==method)
        s = next(r for r in summary['comparisons'] if r['split']=='shifted' and r['method']==method)
        lines.append(f"| {label} | {n['complete']}/{n['total']} | {s['complete']}/{s['total']} | "
                     f"{n['median_seconds']:.3f} | {s['median_seconds']:.3f} |")
    lines += ['', 'Independent certification found 30/30 nominal and 26/30 shifted cases feasible, '
        'with no unresolved cases. Depth-three ADP also completed all three reference cases; '
        'its completion on the independently feasible set was 59/59. One-step ADP missed two '
        'feasible shifted cases.', '', '## Cost and timing evidence', '',
        f"An independent optimum was proven for {len(gaps)} cases: nine nominal and 18 shifted. "
        f"Depth-three ADP's mean relative gap across these cases was {np.mean(gaps):.2f}%. "
        f"The split means were {stats['nominal']['mean_optimality_gap_percent']:.2f}% (n=9) and "
        f"{stats['shifted']['mean_optimality_gap_percent']:.2f}% (n=18). "
        'These optima concern the finite graph objective and its 14-observation budget.', '',
        'Depth-three ADP did not have the lowest cost in every case. The independent MILP '
        'returned a lower mean graph cost in both perturbed splits. It reached its nominal '
        '15-s limit in 32 cases (three reference, 21 nominal, eight shifted), returning a '
        'checked feasible route in every such case; those 32 costs are not proven optimal. '
        'There were no ADP timeouts. Solver termination and reporting can slightly exceed '
        'the requested 15 s. Each case was timed once; the MILP certification phase preceded '
        'the shuffled greedy/ADP evaluations, so these timings are pilot implementation measurements.', '',
        '| Comparator | Split | Jointly complete cases | Mean ADP minus comparator cost | ADP wins / ties / losses |',
        '|---|---|---:|---:|---:|']
    for r in audit_report['paired_comparisons']:
        if r['split']=='reference':
            continue
        c = r['cost_wins_ties_losses']
        lines.append(f"| {labels[r['comparator']]} | {r['split']} | {r['jointly_completed']} | "
                     f"{r['mean_adp_minus_comparator_cost']:.3f} | "
                     f"{c.get('win',0)} / {c.get('tie',0)} / {c.get('loss',0)} |")
    lines += ['', 'Negative paired differences favor ADP. Comparisons use only cases completed '
        'by both methods; the completion table supplies the excluded-case context. A win over '
        'MILP can occur only against its time-limited feasible route, not against a proven optimum.', '',
        '## Implication for the manuscript', '',
        'The earlier 43/50 and 9/30 completion counts reflected a fragile fixed viewpoint library: '
        'all 28 unsuccessful cases lacked an available view of at least one required target. '
        'Five required targets originally had only one candidate view. The new pilot addresses '
        'that observed bottleneck while preserving the old results. It changes the viewpoint '
        'library and perturbation protocol, so the two campaigns are not a paired performance comparison.', '',
        'The predeclared geometry/feasibility gate passed. The next manuscript experiment should '
        'freeze the tested generation rules and all methods, then use fresh graph and scenario '
        'seeds for a larger confirmation. Retain every sampled case and report both all-case '
        'completion and completion conditional on independent feasibility. Report infeasible '
        'and unresolved cases separately, and preserve paired cost denominators. Do not tune '
        'the method on that confirmation set.', '',
        'The pilot itself is development evidence. All graphs share the ISS mesh, target identities '
        'and initial state. Repeated dropout masks occur within the nominal splits (7, 9 and 10 '
        'distinct masks per ten cases), and cases share graph geometry; no population significance '
        'claim is justified by these three graphs. Camera visibility and geometric clearance use '
        'the existing geometry implementation. Independent certification means an independent '
        'route-optimization formulation, not a second geometry engine. Physical and ROS execution '
        'were not part of this pilot. The manuscript and its approved figures were not edited.', '',
        '## Audit and saved evidence', '',
        f"The post-run audit reconstructed {audit_report['numeric_edge_records_verified']:,} directed edge records "
        f"and checked all {audit_report['method_rows_verified']} method-case rows. It also checked "
        f"{audit_report['completed_base_cost_bounds_checked']} applicable completed-base cost bounds and "
        f"{audit_report['independent_lower_bounds_checked']} independent lower-bound comparisons. "
        'The source, graph and scenario hashes match their frozen manifests.', '',
        '- [Aggregate results](summary.md) and [machine-readable summary](summary.json)',
        '- [Independent audit and paired comparisons](raw/independent_audit.json)',
        '- [Solver limit counts](raw/time_limit_counts.csv)',
        '- [Prior confirmation audit](raw/previous_confirmation_audit.json)',
        '- [Scenario diversity](raw/scenario_diversity.json)',
        '- [Frozen protocol](config_snapshot/pilot.yaml)',
        '- [Validation: Python tests, ROS packages and manuscript assets](config_snapshot/validation/validation.json)', '',
        'The six standard CSVs and raw per-edge state/control arrays are retained. They describe '
        'offline planned routes with the existing stabilized-view observation assumption.']
    (output/'review.md').write_text('\n'.join(lines)+'\n')
    summary_path = output/'summary.md'
    marker = '\n## Post-run review\n'
    content = summary_path.read_text().split(marker)[0]
    summary_path.write_text(content+marker+'\nSee [the completed interpretation and audit](review.md) for '
        'paired comparisons, exact gap denominators, limitations and the next experiment. '
        'The JSON time-limit counts include 32 MILP runs with feasible witnesses at the limit; '
        'none of those runs is called optimal.\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    audit(parser.parse_args().output.resolve())
