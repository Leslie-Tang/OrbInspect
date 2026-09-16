#!/usr/bin/env python3
"""Generate new view libraries, certify tasks independently, and benchmark ADP.

Run prepare, certify, benchmark, and summarize in that order. Every stage uses
the frozen YAML and verifies source/input hashes. No manuscript figure is drawn.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import signal
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
for package in ('orbinspect_guidance', 'orbinspect_dynamics', 'orbinspect_perception', 'orbinspect_safety'):
    sys.path.insert(0, str(ROOT/'src'/package))

import numpy as np
import scipy
import yaml

import run_required_target_confirmation as confirmation
import run_required_target_study as original
from orbinspect_guidance.offline_coverage_planner import CandidateViewpoint, OfflineCoveragePlanner
from orbinspect_guidance.offline_planning_experiment import ExperimentConfig, _planner_config
from orbinspect_guidance.offline_adp_superiority_study import (
    ArchivedEdge, ArchivedGraph, load_archived_graph, save_archived_graph,
)
from orbinspect_guidance.required_route_milp import solve_required_route, validate_route

DEFAULT_CONFIG = ROOT/'src/orbinspect_guidance/config/viewpoint_feasibility_pilot.yaml'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(value):
    if isinstance(value, (np.integer, np.floating)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(clean(value), indent=2, sort_keys=True, allow_nan=False)+'\n')


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text('status\nno_rows\n')
        return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(clean(rows))


def source_files() -> list[Path]:
    return [Path(__file__), Path(original.__file__), Path(confirmation.__file__),
            *[ROOT/'src/orbinspect_guidance/orbinspect_guidance'/name for name in
              ('required_route_milp.py', 'advanced_safe_planner.py', 'offline_coverage_planner.py',
               'offline_planning_experiment.py', 'offline_adp_superiority_study.py',
               'mesh_spatial_index.py')],
            ROOT/'src/orbinspect_dynamics/orbinspect_dynamics/hcw_dynamics.py',
            ROOT/'src/orbinspect_perception/orbinspect_perception/visibility_checker.py']


def verify(output: Path, prepared: bool = True) -> dict:
    frozen = json.loads((output/'config_snapshot/protocol.json').read_text())
    for name, digest in frozen['source_hashes'].items():
        if sha(ROOT/name) != digest:
            raise RuntimeError(f'Frozen source changed: {name}')
    for name, digest in frozen['input_hashes'].items():
        if sha(output/name) != digest:
            raise RuntimeError(f'Frozen input changed: {name}')
    if prepared:
        manifest = json.loads((output/'config_snapshot/graph_manifest.json').read_text())
        for name, digest in manifest['input_hashes'].items():
            if sha(output/name) != digest:
                raise RuntimeError(f'Frozen graph/scenario changed: {name}')
    return yaml.safe_load((output/'config_snapshot/pilot.yaml').read_text())


def unit(vector):
    value = np.asarray(vector, dtype=float)
    return value / np.linalg.norm(value)


def candidate_pool(planner, target, cfg, rng, prefix):
    """Sample a predeclared cone and retain geometry-valid views only."""
    normal = unit(target.normal)
    axis = np.eye(3)[int(np.argmin(np.abs(normal)))]
    u = unit(np.cross(normal, axis)); v = np.cross(normal, u)
    accepted, attempted = [], []
    cosine_min = math.cos(math.radians(cfg['normal_cone_angle_deg']))
    for index in range(cfg['candidate_attempts_per_target']):
        cosine = rng.uniform(cosine_min, 1.0)
        phi = rng.uniform(0, 2*math.pi)
        radius = rng.uniform(*cfg['standoff_range_m'])
        direction = cosine*normal + math.sqrt(1-cosine*cosine)*(math.cos(phi)*u+math.sin(phi)*v)
        position = tuple(float(x) for x in np.asarray(target.position)+radius*direction)
        margin = planner._station_clearance(position)
        visible = margin >= 0 and planner._target_visible(position, target, target.position)
        candidate = CandidateViewpoint(f'{prefix}_{index:03d}', position, target.target_id, margin)
        attempted.append({**asdict(candidate), 'source_visible': bool(visible), 'standoff_m': radius})
        if visible:
            accepted.append(candidate)
    return accepted, attempted


def distinct_views(pool, count, separation):
    """Select geometrically spread views without looking at planner outcomes."""
    selected = []
    remaining = list(pool)
    while remaining and len(selected) < count:
        if not selected:
            chosen = remaining[0]
        else:
            chosen = max(remaining, key=lambda c: min(
                math.dist(c.position, old.position) for old in selected))
            if min(math.dist(chosen.position, old.position) for old in selected) < separation:
                break
        selected.append(chosen); remaining.remove(chosen)
    if len(selected) != count:
        raise RuntimeError(f'Only {len(selected)}/{count} separated valid viewpoints; retain this diagnostic.')
    return selected


def prepare(config_path: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(f'Will not overwrite {output}')
    cfg = yaml.safe_load(config_path.read_text())
    for directory in ('config_snapshot', 'raw', 'rosbag', 'figures', 'videos'):
        (output/directory).mkdir(parents=True)
    shutil.copyfile(config_path, output/'config_snapshot/pilot.yaml')
    source = ROOT/cfg['source_bundle']
    for name in ('required_targets.json', 'base_experiment_config.json'):
        shutil.copyfile(source/'config_snapshot'/name, output/'config_snapshot'/name)
    shutil.copyfile(source/'raw/target_positions.csv', output/'config_snapshot/target_positions.csv')
    inputs = list((output/'config_snapshot').iterdir())
    write_json(output/'config_snapshot/protocol.json', {
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_hashes': {str(p.relative_to(ROOT)): sha(p) for p in source_files()},
        'input_hashes': {str(p.relative_to(output)): sha(p) for p in inputs},
        'environment': {'python': sys.version, 'platform': platform.platform(),
                        'numpy': np.__version__, 'scipy': scipy.__version__},
        'scope': 'Development pilot. Shared ISS geometry; independently sampled viewpoint graphs.',
        'selection': 'Geometry and frozen seeds only; no ADP outcomes used to select graphs or scenarios.',
        'classification': 'Independent MILP checked witness, impossibility certificate, or unresolved.',
    })
    (output/'rosbag/README.md').write_text('Offline graph experiment; no ROS process or bag recording.\n')
    (output/'videos/README.md').write_text('Offline graph experiment; no rendered simulation video.\n')
    (output/'figures/README.md').write_text('No manuscript figures changed or generated by this pilot.\n')
    base_values = json.loads((output/'config_snapshot/base_experiment_config.json').read_text())
    base_values['output_root'] = Path(base_values['output_root'])
    base = ExperimentConfig(**base_values)
    planner = OfflineCoveragePlanner(_planner_config(base))
    start = perf_counter()
    targets = tuple(planner.load_targets())
    by_id = {t.target_id: t for t in targets}
    frozen_positions = list(csv.DictReader((output/'config_snapshot/target_positions.csv').open()))
    for row in frozen_positions:
        expected = tuple(float(row[f'position_{axis}']) for axis in 'xyz')
        if math.dist(by_id[row['target_id']].position, expected) > 1e-8:
            raise RuntimeError('Target geometry differs from the frozen nine-target study.')
    previous = load_archived_graph(source/'raw/hcw_graph.json')
    profile = json.loads((output/'config_snapshot/required_targets.json').read_text())['profiles'][0]
    required_ids = profile['required_target_ids']
    target_ids = previous.target_ids
    target_index = {name: i for i, name in enumerate(target_ids)}
    assert all(name in target_index for name in required_ids)
    connector_ids = []
    remaining = [t for t in target_ids if t not in required_ids]
    anchors = [by_id[t].position for t in required_ids]
    for _ in range(cfg['connector_count']):
        chosen = max(remaining, key=lambda t: (min(math.dist(by_id[t].position, p) for p in anchors), t))
        connector_ids.append(chosen); anchors.append(by_id[chosen].position); remaining.remove(chosen)
    write_json(output/'raw/geometry.json', {'mesh_sha256': sha(ROOT/planner.config.iss_mesh_path),
        'mesh_triangle_count': len(planner.mesh_geometry.triangles),
        'mesh_load_seconds': perf_counter()-start, 'camera': asdict(planner.visibility_checker.camera),
        'required_ids': required_ids, 'connector_source_target_ids': connector_ids,
        'targets': [asdict(t) for t in targets], 'planner_config': {
            k: str(v) if isinstance(v, Path) else v for k, v in asdict(planner.config).items()}})
    print(f'Mesh loaded: {len(planner.mesh_geometry.triangles)} triangles; target coordinates match.', flush=True)
    all_scenarios, graph_records = [], []
    for graph_index, seed in enumerate(cfg['graph_seeds']):
        graph_id = f'g{graph_index+1:02d}'
        graph_dir = output/'raw'/graph_id
        graph_dir.mkdir()
        started = perf_counter()
        rng = random.Random(seed)
        candidates, attempts = [], []
        for tindex, target_id in enumerate([*required_ids, *connector_ids]):
            count = cfg['views_per_required_target'] if target_id in required_ids else 1
            pool, attempted = candidate_pool(planner, by_id[target_id], cfg, rng, f'{graph_id}_t{tindex:02d}')
            attempts.extend(attempted)
            write_json(graph_dir/'candidate_attempts.json', attempts)
            candidates.extend(distinct_views(pool, count, cfg['minimum_view_separation_m']))
        visibility = planner.compute_visibility_matrix(targets, candidates)
        masks = tuple(sum(1 << target_index[t] for t in visibility.visible_targets_by_candidate[c.candidate_id]
                          if t in target_index) for c in candidates)
        redundancy = {t: sum(bool(mask & (1 << target_index[t])) for mask in masks) for t in required_ids}
        write_json(graph_dir/'candidates.json', [{'candidate': asdict(c), 'coverage_mask': hex(mask),
                    'all_visible_ids': sorted(visibility.visible_targets_by_candidate[c.candidate_id])}
                   for c, mask in zip(candidates, masks)])
        print(f'{graph_id}: {len(candidates)} candidates; required view counts {list(redundancy.values())}', flush=True)
        edge_records, audits, states, controls = [], [], [], []
        for source_node in [None, *candidates]:
            initial = base.initial_state if source_node is None else (*source_node.position, 0.0, 0.0, 0.0)
            source_id = None if source_node is None else source_node.candidate_id
            for target in candidates:
                if source_id == target.candidate_id:
                    continue
                transfer = planner.estimate_transfer(initial, target.position)
                passive_margin, passive_safe = planner._passive_safety_audit(tuple(s for _, s, _ in transfer.trajectory))
                cost = (base.cw_energy_weight*transfer.delta_v + base.cw_tracking_weight*transfer.tracking_error
                        + base.cw_safety_weight*max(0, -transfer.min_clearance))
                edge_records.append(ArchivedEdge(source_id, target.candidate_id, cost,
                    transfer.feasible and passive_safe is not False, transfer.min_clearance,
                    transfer.peak_requested_input, base.max_acceleration, passive_margin,
                    transfer.delta_v, transfer.tracking_error))
                audits.append({'edge_index': len(edge_records)-1, 'source_id': source_id,
                    'target_id': target.candidate_id, 'feasible': edge_records[-1].feasible,
                    'rejection_reason': planner._transfer_rejection_reason(transfer, passive_safe),
                    'min_clearance': transfer.min_clearance, 'peak_input': transfer.peak_requested_input,
                    'max_speed': transfer.max_speed, 'terminal_position_error': transfer.terminal_error,
                    'terminal_speed': math.dist(transfer.next_state[3:], (0, 0, 0)), 'stage_cost': cost})
                states.append([s for _, s, _ in transfer.trajectory])
                controls.append([u for _, _, u in transfer.trajectory])
            print(f'{graph_id}: archived {len(edge_records)}/{len(candidates)**2} transfers', flush=True)
        graph = ArchivedGraph(tuple(c.candidate_id for c in candidates), masks,
            tuple(c.safety_margin for c in candidates), target_ids, previous.base_target_weights,
            tuple(edge_records), tuple(c.position for c in candidates))
        save_archived_graph(graph, graph_dir/'hcw_graph.json')
        write_csv(graph_dir/'edge_audits.csv', audits)
        np.savez_compressed(graph_dir/'edge_samples.npz', states=np.asarray(states),
                            controls=np.asarray(controls), dt=base.integration_dt)
        record = {'graph_id': graph_id, 'seed': seed, 'node_count': len(candidates),
                  'feasible_edge_count': sum(e.feasible for e in edge_records),
                  'required_view_counts': redundancy, 'build_seconds': perf_counter()-started}
        graph_records.append(record)
        for split, count in [('reference', 1), ('nominal', cfg['nominal_scenarios_per_graph']),
                             ('shifted', cfg['shifted_scenarios_per_graph'])]:
            split_number = {'reference': 0, 'nominal': 1, 'shifted': 2}[split]
            for index in range(count):
                sample_seed = cfg['scenario_seed_base']+graph_index*100000+split_number*10000+index
                sample_rng = random.Random(sample_seed)
                dropout = 0.0 if split == 'reference' else sample_rng.uniform(*cfg[f'{split}_dropout_range'])
                available = [node for node in graph.node_ids if sample_rng.random() >= dropout]
                all_scenarios.append({'scenario_id': f'{graph_id}_{split}_{index:03d}',
                    'graph_id': graph_id, 'profile_id': 'required09', 'split': split,
                    'seed': sample_seed, 'available_node_ids': available,
                    'target_weights': list(previous.base_target_weights), 'reference_node_ids': [],
                    'goal_coverage': 0.0, 'goal_mode': 'required', 'max_steps': cfg['max_steps'],
                    'required_target_ids': required_ids, 'required_target_mask': profile['required_target_mask'],
                    'sampled_dropout_probability': dropout})
    write_json(output/'raw/scenarios.json', all_scenarios)
    write_json(output/'raw/graph_summary.json', graph_records)
    inputs = [p for p in (output/'raw').rglob('*') if p.is_file()]
    write_json(output/'config_snapshot/graph_manifest.json', {
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'graph_count': len(graph_records), 'scenario_count': len(all_scenarios),
        'input_hashes': {str(p.relative_to(output)): sha(p) for p in inputs}})
    print(f'Frozen {len(graph_records)} graphs and all {len(all_scenarios)} scenarios.', flush=True)


def certify(output: Path) -> None:
    cfg = verify(output)
    if (output/'raw/feasibility.json').exists():
        raise FileExistsError('Independent certification already exists.')
    rows = []
    scenarios = json.loads((output/'raw/scenarios.json').read_text())
    for payload in scenarios:
        graph = load_archived_graph(output/'raw'/payload['graph_id']/'hcw_graph.json')
        problem = original.make_problem(graph, payload)
        result = solve_required_route(problem, time_limit_s=cfg['solver_time_limit_s'], action_cost=cfg['action_cost'])
        rows.append({'scenario_id': payload['scenario_id'], 'graph_id': payload['graph_id'],
                     'split': payload['split'], **asdict(result)})
        write_json(output/'raw/feasibility_progress.json', rows)
        print(f"{payload['scenario_id']}: {result.status}, optimal={result.optimal}, {result.elapsed_s:.2f}s", flush=True)
    write_json(output/'raw/feasibility.json', rows)
    write_csv(output/'raw/feasibility.csv', rows)
    write_json(output/'config_snapshot/certification_manifest.json', {
        'completed_before_adp_evaluation_utc': datetime.now(timezone.utc).isoformat(),
        'feasibility_sha256': sha(output/'raw/feasibility.json')})


class PlannerTimeout(Exception):
    pass


def timeout_handler(_signum, _frame):
    raise PlannerTimeout('Common per-method wall-clock limit reached.')


def benchmark(output: Path) -> None:
    cfg = verify(output)
    certification = json.loads((output/'config_snapshot/certification_manifest.json').read_text())
    if sha(output/'raw/feasibility.json') != certification['feasibility_sha256']:
        raise RuntimeError('Independent feasibility results changed.')
    if (output/'raw/benchmark_results.json').exists():
        raise FileExistsError('Benchmark already exists.')
    certificates = {r['scenario_id']: r for r in json.loads((output/'raw/feasibility.json').read_text())}
    scenarios = json.loads((output/'raw/scenarios.json').read_text())
    rows = []
    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    try:
        for payload in scenarios:
            graph = load_archived_graph(output/'raw'/payload['graph_id']/'hcw_graph.json')
            problem = original.make_problem(graph, payload)
            certificate = certificates[payload['scenario_id']]
            methods = [m for m in cfg['methods'] if m != 'independent_milp']
            random.Random(payload['seed']).shuffle(methods)
            methods.append('independent_milp')
            for method in methods:
                start = perf_counter()
                if method == 'independent_milp':
                    route = tuple(certificate['node_ids'])
                    row = {'method': method, 'route_node_ids': ';'.join(route),
                        'online_time_s': certificate['elapsed_s'], 'termination_reason': certificate['reason'],
                        'optimal': certificate['optimal'], 'lower_bound': certificate['lower_bound']}
                else:
                    try:
                        signal.setitimer(signal.ITIMER_REAL, cfg['planner_time_limit_s'])
                        row = confirmation.evaluate(graph, payload, cfg, method, cfg['adaptive_rollout_depth'])
                        row['termination_reason'] = 'complete' if row['success'] else 'no_completion'
                    except PlannerTimeout:
                        row = {'method': method, 'route_node_ids': '', 'online_time_s': perf_counter()-start,
                               'termination_reason': 'time_limit'}
                    finally:
                        signal.setitimer(signal.ITIMER_REAL, 0)
                    route = tuple(filter(None, row['route_node_ids'].split(';')))
                metrics = validate_route(problem, route, cfg['action_cost'])
                if row.get('success') is not None and bool(row['success']) != metrics['success']:
                    raise RuntimeError('Planner success disagrees with independent route reconstruction.')
                if row.get('graph_cost') is not None and not math.isclose(row['graph_cost'], metrics['graph_cost'], rel_tol=1e-8):
                    raise RuntimeError('Planner objective disagrees with independent reconstruction.')
                row.update(metrics)
                row.update({'scenario_id': payload['scenario_id'], 'graph_id': payload['graph_id'],
                    'split': payload['split'], 'method': method, 'available_node_count': len(payload['available_node_ids']),
                    'independent_feasibility': certificate['status'], 'independent_optimal': certificate['optimal']})
                row['optimality_gap_percent'] = (100*(metrics['graph_cost']/certificate['graph_cost']-1)
                    if metrics['success'] and certificate['optimal'] and certificate['graph_cost'] else None)
                if row['optimality_gap_percent'] is not None and row['optimality_gap_percent'] < -1e-6:
                    raise RuntimeError('Route improves on a claimed global optimum; audit formulation.')
                rows.append(row)
                write_json(output/'raw/benchmark_progress.json', rows)
                print(f"{payload['scenario_id']} {method}: success={metrics['success']} time={row['online_time_s']:.2f}s", flush=True)
    finally:
        signal.signal(signal.SIGALRM, original_handler)
    write_json(output/'raw/benchmark_results.json', rows)
    write_csv(output/'raw/benchmark_results.csv', rows)
    write_csv(output/'raw/planner.csv', rows)
    materialize(output, rows, scenarios)


def materialize(output, rows, scenarios):
    """Export each completed route from the frozen HCW edge samples."""
    trajectory, control, safety, coverage, events = [], [], [], [], []
    lookup = {p['scenario_id']: p for p in scenarios}
    cache = {}
    for row in rows:
        if not row['success']:
            continue
        gid = row['graph_id']
        if gid not in cache:
            graph = load_archived_graph(output/'raw'/gid/'hcw_graph.json')
            data = np.load(output/'raw'/gid/'edge_samples.npz')
            cache[gid] = (graph, data, {(e.source_id, e.target_id): i for i, e in enumerate(graph.edges)})
        graph, data, edge_index = cache[gid]
        masks = dict(zip(graph.node_ids, graph.coverage_masks))
        payload = lookup[row['scenario_id']]
        prefix = {k: row[k] for k in ('scenario_id', 'graph_id', 'method')}
        source, covered, time = None, 0, 0.0
        dt = float(data['dt'])
        for sequence, target in enumerate(row['route_node_ids'].split(';'), 1):
            index = edge_index[(source, target)]; edge = graph.edges[index]
            for state, command in zip(data['states'][index], data['controls'][index]):
                time += dt
                trajectory.append({**prefix, 'time': time, 'sequence': sequence,
                                   **dict(zip(('x','y','z','vx','vy','vz'), state))})
                control.append({**prefix, 'time': time, 'sequence': sequence,
                                **dict(zip(('ax','ay','az'), command))})
            new = masks[target] & ~covered; covered |= masks[target]
            count = (covered & payload['required_target_mask']).bit_count()
            coverage.append({**prefix, 'time': time, 'sequence': sequence, 'required_covered': count,
                             'required_total': len(payload['required_target_ids']),
                             'library_sample_coverage': covered.bit_count()/len(graph.target_ids),
                             'whole_sample_coverage': covered.bit_count()/90})
            events.append({**prefix, 'time': time, 'sequence': sequence, 'event': 'offline_observation_credited',
                           'node_id': target, 'new_target_mask': new, 'covered_target_mask': covered})
            safety.append({**prefix, 'time': time, 'sequence': sequence, 'source_id': source,
                           'target_id': target, 'edge_feasible': edge.feasible,
                           'min_clearance': edge.min_clearance, 'peak_input': edge.peak_input})
            source = target
    for name, values in [('trajectory',trajectory), ('control',control), ('coverage',coverage),
                         ('safety',safety), ('mission_events',events)]:
        write_csv(output/'raw'/f'{name}.csv', values)
    for _, data, _ in cache.values():
        data.close()


def summarize(output: Path) -> None:
    cfg = verify(output)
    feasibility = json.loads((output/'raw/feasibility.json').read_text())
    results = json.loads((output/'raw/benchmark_results.json').read_text())
    graphs = json.loads((output/'raw/graph_summary.json').read_text())
    counts, comparisons = {}, []
    for split in ('reference', 'nominal', 'shifted'):
        cohort = [r for r in feasibility if r['split'] == split]
        counts[split] = {'total': len(cohort), **dict(Counter(r['status'] for r in cohort)),
                        'proven_optimal': sum(r['optimal'] for r in cohort)}
        for method in cfg['methods']:
            rows = [r for r in results if r['split']==split and r['method']==method]
            eligible = [r for r in rows if r['independent_feasibility']=='feasible']
            successful = [r for r in eligible if r['success']]
            gaps = [r['optimality_gap_percent'] for r in successful if r['optimality_gap_percent'] is not None]
            comparisons.append({'split':split, 'method':method, 'total':len(rows),
                'complete':sum(r['success'] for r in rows), 'certified_feasible':len(eligible),
                'complete_on_certified_feasible':len(successful),
                'time_limits':sum(r['termination_reason']=='time_limit' for r in rows),
                'median_seconds':float(np.median([r['online_time_s'] for r in rows])),
                'mean_delta_v_success':float(np.mean([r['total_delta_v'] for r in successful])) if successful else None,
                'optimum_comparison_count':len(gaps), 'mean_optimality_gap_percent':float(np.mean(gaps)) if gaps else None})
    gate = cfg['scale_gate']
    conditions = {
        'redundancy': all(min(g['required_view_counts'].values()) >= gate['minimum_views_per_required_target'] for g in graphs),
        'nominal_feasibility': counts['nominal'].get('feasible',0)/counts['nominal']['total'] >= gate['minimum_feasible_fraction_nominal'],
        'shifted_feasibility': counts['shifted'].get('feasible',0)/counts['shifted']['total'] >= gate['minimum_feasible_fraction_shifted'],
        'classification_resolved': sum(r['status']=='unresolved' for r in feasibility)/len(feasibility) <= gate['maximum_unresolved_fraction'],
        'build_practicality': max(g['build_seconds'] for g in graphs) <= gate['maximum_graph_build_seconds'],
    }
    report = {'study_type':'development pilot', 'graphs':graphs, 'feasibility':counts,
              'comparisons':comparisons, 'scaling_conditions':conditions,
              'geometry_feasibility_scale_gate_passed':all(conditions.values()),
              'main_manuscript_changed':False, 'original_confirmation_changed':False,
              'scope_limitations':['Same ISS geometry, nine targets and start state across graphs.',
                                  'One timing measurement per method-case pair.',
                                  'The pilot is development evidence, not an independent confirmation.',
                                  'Physical closed-loop execution and ROS recording were not performed.']}
    write_json(output/'summary.json', report)
    lines = ['# Redundant-viewpoint feasibility pilot', '',
             'New viewpoint graphs on the same ISS mesh, with the original nine required IDs,',
             'dynamics, camera and safety limits. All generated scenarios are retained.',
             'Feasibility was certified independently before ADP evaluation. No manuscript figures changed.', '',
             '| Split | Total | Independently feasible | Proven infeasible | Unresolved | Proven optimal |',
             '|---|---:|---:|---:|---:|---:|']
    for split, c in counts.items():
        lines.append(f"| {split} | {c['total']} | {c.get('feasible',0)} | {c.get('infeasible',0)} | {c.get('unresolved',0)} | {c['proven_optimal']} |")
    lines += ['', '| Split | Method | Complete / all | Complete / independently feasible | Median time (s) | Mean gap to proven optimum (%) |',
              '|---|---|---:|---:|---:|---:|']
    for r in comparisons:
        gap = '--' if r['mean_optimality_gap_percent'] is None else f"{r['mean_optimality_gap_percent']:.2f}"
        lines.append(f"| {r['split']} | {r['method']} | {r['complete']}/{r['total']} | {r['complete_on_certified_feasible']}/{r['certified_feasible']} | {r['median_seconds']:.3f} | {gap} |")
    lines += ['', '## Interpretation', '',
        'Optimality-gap means use completed cases with a proven independent optimum; denominators',
        'can differ by method. Inspect paired case rows before claiming comparative savings.',
        'Zero completion on a time-limited run means no completed route was returned within the budget.',
        'A time limit without a checked witness is never labeled infeasible.', '',
        f"Geometry/feasibility scaling gate passed: **{all(conditions.values())}**.",
        'The gate was frozen before generation and does not depend on ADP outperforming any comparator.', '',
        '## Output provenance', '',
        'Graph and source hashes are in `config_snapshot/`. Every generated viewpoint and rejected',
        'candidate attempt, directed edge audit, and sampled HCW state/control is retained in `raw/`.',
        'The six standard CSVs materialize completed offline routes. Camera exposure is credited',
        'under the existing stabilized-view assumption; no ROS, physical trial, or video is claimed.', '',
        '## Limits', '', *['- '+s for s in report['scope_limitations']]]
    (output/'summary.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(report['feasibility'], indent=2), flush=True)
    print(f'Scaling gate: {conditions}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare','certify','benchmark','summarize'])
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/'data/results'):
        raise ValueError('Paper experiment outputs must be under data/results/.')
    if args.stage == 'prepare':
        prepare(args.config, output)
    else:
        {'certify':certify,'benchmark':benchmark,'summarize':summarize}[args.stage](output)


if __name__ == '__main__':
    main()
