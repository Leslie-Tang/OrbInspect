#!/usr/bin/env python3
"""Freeze and evaluate geometry-prescribed inspection requirements on an archived graph.

Run from the repository root with its source packages on PYTHONPATH.  A freeze
command writes all requirements and scenario inventories before any new plans
are evaluated.  The run command verifies those files and implementation hashes.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
from statistics import mean, median
from time import perf_counter

import numpy as np
import yaml

from orbinspect_guidance.advanced_safe_planner import AdvancedSafePlanner
from orbinspect_guidance.offline_adp_superiority_study import (
    MissionScenario, SuperiorityConfig, _method_config, _problem_for_scenario,
    load_archived_graph,
)
from orbinspect_guidance.offline_coverage_planner import OfflineCoveragePlanner
from orbinspect_guidance.offline_planning_experiment import (
    ExperimentConfig, _planner_config as experiment_planner_config,
)

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO / 'src/orbinspect_guidance/config/required_target_study.yaml'


def sha256(path: Path) -> str:
    """Hash an archived input without changing its representation."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def write_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def target_geometry(source: Path) -> tuple[dict, dict]:
    """Reconstruct the same deterministic 90 mesh surface samples."""
    summary = json.loads((source / 'summary.json').read_text())
    values = dict(summary['base_experiment_config'])
    values['output_root'] = Path(values['output_root'])
    values['methods'] = tuple(values['methods'])
    values['initial_state'] = tuple(values['initial_state'])
    planner = OfflineCoveragePlanner(experiment_planner_config(ExperimentConfig(**values)))
    positions = {target.target_id: tuple(float(v) for v in target.position)
                 for target in planner.load_targets()}
    return positions, summary['base_experiment_config']


def select_profiles(target_ids: tuple[str, ...], positions: dict, counts: list[int]) -> dict:
    """Select nested, spatially spread requirements using coordinates alone.

    Three equal-width slabs span the longest axis of all surface samples.
    Each slab starts with its candidate closest to its geometric centroid and
    then uses deterministic farthest-point sampling within that slab.
    """
    all_positions = np.asarray(list(positions.values()))
    axis = int(np.argmax(np.ptp(all_positions, axis=0)))
    low, high = float(all_positions[:, axis].min()), float(all_positions[:, axis].max())
    cuts = [low + (high - low) * fraction / 3 for fraction in range(4)]
    scale = np.maximum(np.ptp(all_positions, axis=0), 1.0e-12)
    regions = []
    order_by_region = []
    for region_index in range(3):
        available = sorted(target for target in target_ids
                           if min(2, int((positions[target][axis] - low) / (high-low) * 3)) == region_index)
        if len(available) < max(counts) // 3:
            raise ValueError('Geometry slab has too few candidate-observable samples.')
        normalized = {target: np.asarray(positions[target]) / scale for target in available}
        centroid = np.mean(list(normalized.values()), axis=0)
        chosen = [min(available, key=lambda target: (float(np.linalg.norm(normalized[target]-centroid)), target))]
        while len(chosen) < max(counts) // 3:
            remaining = [target for target in available if target not in chosen]
            chosen.append(min(remaining, key=lambda target: (
                -min(float(np.linalg.norm(normalized[target]-normalized[selected])) for selected in chosen), target)))
        order_by_region.append(chosen)
        regions.append({'region_id': f'axis_{"xyz"[axis]}_slab_{region_index+1}',
                        'axis': 'xyz'[axis], 'lower_bound_m': cuts[region_index],
                        'upper_bound_m': cuts[region_index+1],
                        'candidate_observable_item_count': len(available),
                        'ordered_target_ids': chosen})
    profiles = []
    for count in counts:
        selected = [target for order in order_by_region for target in order[:count//3]]
        mask = sum(1 << target_ids.index(target) for target in selected)
        profiles.append({'profile_id': f'required{count:02d}', 'required_target_count': count,
                         'required_target_ids': selected, 'required_target_mask': mask,
                         'region_target_ids': {region['region_id']: order[:count//3]
                                               for region, order in zip(regions, order_by_region)}})
    return {'selection_inputs': 'mesh coordinates and archived candidate-observable target IDs only',
            'selection_uses_scenario_inventory': False, 'selection_uses_route_outcomes': False,
            'geometric_regions': regions, 'profiles': profiles,
            'mesh_target_count': len(positions), 'candidate_observable_target_count': len(target_ids),
            'scientific_scope': 'Synthetic geometric benchmark requirements; no component-criticality claim.'}


def scenario_payload(graph, config: dict, profile: dict, split: str, index: int, seed: int) -> dict:
    """Sample once, retaining all node-dropout outcomes without rejection."""
    generator = random.Random(seed)
    prefix = 'ood' if split == 'ood' else 'test'
    dropout = generator.uniform(*config[f'{prefix}_dropout_range'])
    available = [node for node in graph.node_ids if generator.random() >= dropout]
    weights = list(graph.base_target_weights)
    count = max(1, round(len(weights) * generator.uniform(*config[f'{prefix}_priority_fraction'])))
    multiplier = generator.uniform(*config[f'{prefix}_priority_multiplier'])
    for target_index in generator.sample(range(len(weights)), count):
        weights[target_index] *= multiplier
    return {'scenario_id': f'{profile["profile_id"]}_{split}_{index:03d}',
            'profile_id': profile['profile_id'], 'split': split, 'seed': seed,
            'available_node_ids': available, 'target_weights': weights,
            'reference_node_ids': [], 'goal_coverage': 0.0, 'goal_mode': 'required',
            'required_target_ids': profile['required_target_ids'],
            'required_target_mask': profile['required_target_mask'],
            'max_steps': config['max_steps'], 'sampled_dropout_probability': dropout}


def freeze(config_path: Path, output: Path) -> None:
    """Write the fixed experiment protocol and its input hashes before testing."""
    if output.exists():
        raise FileExistsError(f'Will not overwrite existing experiment {output}')
    config = yaml.safe_load(config_path.read_text())
    source = REPO / config['graph_root']
    graph_path = source / 'raw/hcw_graph.json'
    graph = load_archived_graph(graph_path)
    positions, base_config = target_geometry(source)
    manifest = select_profiles(graph.target_ids, positions, config['required_counts'])
    known_seeds = set()
    scanned = []
    for old in sorted((REPO / 'data/results').glob('*/raw/scenarios.json')):
        payload = json.loads(old.read_text())
        if isinstance(payload, list):
            known_seeds.update(int(row['seed']) for row in payload if 'seed' in row)
            scanned.append(str(old.relative_to(REPO)))
    scenarios = []
    for profile_index, profile in enumerate(manifest['profiles']):
        for split_index, split in enumerate(('validation', 'test', 'ood')):
            for index in range(config[f'{split}_scenarios']):
                seed = int(config['seed_base']) + profile_index*100000 + split_index*10000 + index
                if seed in known_seeds:
                    raise ValueError(f'Fresh scenario seed collides with archive: {seed}')
                scenarios.append(scenario_payload(graph, config, profile, split, index, seed))
    for directory in ('config_snapshot', 'raw', 'rosbag', 'figures', 'videos'):
        (output / directory).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config_path, output / 'config_snapshot/required_target_study.yaml')
    shutil.copyfile(graph_path, output / 'raw/hcw_graph.json')
    write_json(output / 'config_snapshot/required_targets.json', manifest)
    write_json(output / 'config_snapshot/base_experiment_config.json', base_config)
    write_json(output / 'raw/scenarios.json', scenarios)
    rows = [{'target_id': target, 'position_x': position[0], 'position_y': position[1],
             'position_z': position[2], 'candidate_observable': target in graph.target_ids,
             'graph_bit_index': graph.target_ids.index(target) if target in graph.target_ids else -1,
             **{profile['profile_id']: target in profile['required_target_ids'] for profile in manifest['profiles']}}
            for target, position in sorted(positions.items())]
    write_rows(output / 'raw/target_positions.csv', rows)
    sources = [Path(__file__), REPO / 'src/orbinspect_guidance/orbinspect_guidance/advanced_safe_planner.py',
               REPO / 'src/orbinspect_guidance/orbinspect_guidance/offline_adp_superiority_study.py']
    protocol = {'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_graph_sha256': sha256(graph_path),
                'source_hashes': {str(path.relative_to(REPO)): sha256(path) for path in sources},
                'input_hashes': {str(path.relative_to(output)): sha256(path) for path in
                                [output/'config_snapshot/required_target_study.yaml',
                                 output/'config_snapshot/required_targets.json', output/'raw/scenarios.json',
                                 output/'raw/target_positions.csv', output/'raw/hcw_graph.json']},
                'prior_scenario_archives_scanned': scanned, 'prior_seed_count': len(known_seeds),
                'scenario_count': len(scenarios), 'rejected_scenario_count': 0,
                'primary_profile': config['primary_profile'],
                'depth_selection': 'Depth three fixed in advance; all validation depths descriptive.',
                'scenario_sampling': 'Unconditional; no resampling for missing visibility or failed base policy.',
                'visibility_bound': 'Necessary visibility condition only; not a feasibility certificate.',
                'failure_penalty': 'cost + 500*required_missing_fraction + 500*not_required_complete'}
    write_json(output / 'config_snapshot/freeze_manifest.json', protocol)
    print(json.dumps({'frozen': str(output), 'profiles': manifest['profiles'],
                      'scenario_count': len(scenarios), 'graph_sha256': protocol['source_graph_sha256']}, indent=2), flush=True)


def make_problem(graph, payload: dict, *, coverage_only: bool = False):
    scenario = MissionScenario(scenario_id=payload['scenario_id'], split=payload['split'], seed=payload['seed'],
                               available_node_ids=tuple(payload['available_node_ids']),
                               target_weights=tuple(payload['target_weights']), reference_node_ids=(),
                               goal_coverage=0.8 if coverage_only else 0.0, max_steps=payload['max_steps'])
    return replace(_problem_for_scenario(graph, scenario), goal_mode='coverage' if coverage_only else 'required',
                   required_target_mask=0 if coverage_only else payload['required_target_mask'])


def study_config(config: dict, depth: int = 3) -> SuperiorityConfig:
    names = ('max_steps', 'branch_width', 'candidate_pool_width', 'lookahead_depth',
             'local_improvement_passes', 'action_cost', 'cost_scale', 'terminal_penalty')
    return SuperiorityConfig(**{key: config[key] for key in names}, goal_coverage=0.0,
                             adaptive_rollout_depth=depth)


def evaluate(graph, payload: dict, config: dict, method: str, depth: int = 3) -> dict:
    """Evaluate actual accepted graph target unions and common mission penalties."""
    problem = make_problem(graph, payload, coverage_only=method == 'coverage_only80')
    cfg = study_config(config, depth)
    base_cfg, _ = _method_config('adaptive_rollout_adp', cfg, ())
    base_start = perf_counter()
    base = AdvancedSafePlanner(base_cfg).base_policy_plan(problem)
    base_time = perf_counter()-base_start
    start = perf_counter()
    if method == 'incumbent':
        plan = base
    else:
        actual_method = 'adaptive_rollout_adp' if method == 'coverage_only80' else method
        planner_cfg, _ = _method_config(actual_method, cfg, ())
        plan = AdvancedSafePlanner(planner_cfg).plan(replace(problem, reference_node_ids=base.node_ids if base.success else ()))
    elapsed = perf_counter()-start + base_time
    masks = dict(zip(graph.node_ids, graph.coverage_masks))
    covered = 0
    available = 0
    edges = []
    current = None
    for node_id in payload['available_node_ids']:
        available |= masks[node_id]
    for node_id in plan.node_ids:
        covered |= masks[node_id]
        edges.append(problem.edge_evaluator(current, node_id))
        current = node_id
    required_mask = int(payload['required_target_mask'])
    required_count = required_mask.bit_count()
    covered_required = (covered & required_mask).bit_count()
    required_coverage = covered_required / required_count
    missing = [target for index, target in enumerate(graph.target_ids)
               if required_mask & (1 << index) and not covered & (1 << index)]
    success = not missing
    base_mask = 0
    for node in base.node_ids:
        base_mask |= masks[node]
    base_success = (base_mask & required_mask) == required_mask
    goal_native = bool(plan.success)
    return {'profile_id': payload['profile_id'], 'split': payload['split'],
            'scenario_id': payload['scenario_id'], 'scenario_seed': payload['seed'], 'method': method,
            'adaptive_rollout_depth': depth, 'success': success, 'native_goal_success': goal_native,
            'required_coverage': required_coverage, 'required_target_count': required_count,
            'required_covered_count': covered_required, 'missing_required_ids': ';'.join(missing),
            'coverage': plan.coverage_ratio, 'covered_target_count': covered.bit_count(),
            'inspectable_sample_coverage': covered.bit_count()/len(graph.target_ids),
            'whole_sample_coverage': covered.bit_count()/90,
            'graph_cost': plan.total_cost,
            'penalized_cost': plan.total_cost + config['evaluation_missing_fraction_penalty']*(1-required_coverage)
                              + config['evaluation_failure_penalty']*(not success),
            'total_delta_v': sum(edge.delta_v for edge in edges),
            'selected_count': len(plan.node_ids), 'mission_duration_s': len(plan.node_ids)*config['transfer_duration_s'],
            'online_time_s': elapsed, 'base_policy_time_s': base_time,
            'safe_action_evaluations': plan.safe_action_evaluations,
            'shield_rejections': plan.shield_rejections,
            'min_clearance': min((edge.min_clearance for edge in edges), default=math.nan),
            'peak_input': max((edge.peak_input for edge in edges), default=math.nan),
            'unsafe_selected_edges': sum(not edge.feasible or edge.min_clearance < 0 or edge.peak_input > edge.input_limit + 1e-12 for edge in edges),
            'required_visibility_available': (available & required_mask) == required_mask,
            'required_visibility_upper_bound': (available & required_mask).bit_count()/required_count,
            'available_node_count': len(payload['available_node_ids']),
            'base_success': base_success, 'base_graph_cost': base.total_cost,
            'cost_exceeds_successful_base': bool(method == 'adaptive_rollout_adp' and base_success and success and plan.total_cost > base.total_cost+1e-9),
            'policy_source': plan.policy_source, 'route_node_ids': ';'.join(plan.node_ids),
            'covered_target_mask': covered, 'base_route_node_ids': ';'.join(base.node_ids)}


def bootstrap(values: list[float], config: dict) -> list[float]:
    if not values:
        return [math.nan, math.nan]
    rng = np.random.default_rng(config['bootstrap_seed'])
    samples = np.asarray(values)
    means = samples[rng.integers(0, len(samples), size=(config['bootstrap_replicates'], len(samples)))].mean(axis=1)
    return np.quantile(means, [0.025, 0.975]).tolist()


def aggregate(rows: list[dict], config: dict) -> tuple[list[dict], list[dict]]:
    summaries = []
    paired = []
    groups = sorted({(row['profile_id'], row['split']) for row in rows})
    for profile, split in groups:
        subset = [row for row in rows if row['profile_id']==profile and row['split']==split]
        for method in config['methods']:
            method_rows = [row for row in subset if row['method']==method]
            successful = [row for row in method_rows if row['success']]
            summaries.append({'profile_id': profile, 'split': split, 'method': method,
                              'scenario_count': len(method_rows), 'success_count': len(successful),
                              'success_rate': len(successful)/len(method_rows),
                              'required_visibility_available_count': sum(row['required_visibility_available'] for row in method_rows),
                              'mean_required_coverage': mean(row['required_coverage'] for row in method_rows),
                              'mean_penalized_cost': mean(row['penalized_cost'] for row in method_rows),
                              'mean_successful_cost': mean(row['graph_cost'] for row in successful) if successful else math.nan,
                              'mean_successful_delta_v': mean(row['total_delta_v'] for row in successful) if successful else math.nan,
                              'mean_successful_background_coverage': mean(row['coverage'] for row in successful) if successful else math.nan,
                              'mean_successful_whole_sample_coverage': mean(row['whole_sample_coverage'] for row in successful) if successful else math.nan,
                              'median_online_time_s': median(row['online_time_s'] for row in method_rows),
                              'unsafe_selected_edges': sum(row['unsafe_selected_edges'] for row in method_rows),
                              'successful_base_bound_violations': sum(row['cost_exceeds_successful_base'] for row in method_rows)})
        proposed = {row['scenario_id']: row for row in subset if row['method']=='adaptive_rollout_adp'}
        for method in config['methods']:
            if method == 'adaptive_rollout_adp':
                continue
            comparisons = [(proposed[row['scenario_id']], row) for row in subset if row['method']==method]
            joint = [(left,right) for left,right in comparisons if left['success'] and right['success']]
            delta = [left['graph_cost']-right['graph_cost'] for left,right in joint]
            dv = [left['total_delta_v']-right['total_delta_v'] for left,right in joint]
            penalty = [left['penalized_cost']-right['penalized_cost'] for left,right in comparisons]
            wins, losses = sum(value < -1e-9 for value in delta), sum(value > 1e-9 for value in delta)
            n = wins+losses
            sign_p = min(1.0, 2*sum(math.comb(n,k) for k in range(min(wins,losses)+1))/2**n) if n else 1.0
            paired.append({'profile_id': profile, 'split': split, 'baseline': method,
                           'all_scenario_count': len(comparisons), 'joint_success_count': len(joint),
                           'mean_paired_cost_difference': mean(delta) if delta else math.nan,
                           'paired_cost_difference_ci95': bootstrap(delta,config),
                           'mean_paired_cost_reduction_pct': mean([(right['graph_cost']-left['graph_cost'])/right['graph_cost']*100 for left,right in joint]) if joint else math.nan,
                           'mean_paired_delta_v_difference': mean(dv) if dv else math.nan,
                           'paired_delta_v_difference_ci95': bootstrap(dv,config),
                           'mean_allscenario_penalized_cost_difference': mean(penalty),
                           'allscenario_penalized_cost_difference_ci95': bootstrap(penalty,config),
                           'joint_success_wins': wins, 'joint_success_losses': losses,
                           'joint_success_ties': len(delta)-n, 'sign_test_two_sided_p': sign_p,
                           'scope': 'Coverage-only80 uses a different native task; diagnostic comparison only.' if method=='coverage_only80' else 'Matched required-target task.'})
    return summaries, paired


def run(output: Path, split: str) -> None:
    config = yaml.safe_load((output/'config_snapshot/required_target_study.yaml').read_text())
    protocol = json.loads((output/'config_snapshot/freeze_manifest.json').read_text())
    for relative, expected in protocol['input_hashes'].items():
        if sha256(output/relative) != expected:
            raise RuntimeError(f'Frozen input changed: {relative}')
    for relative, expected in protocol['source_hashes'].items():
        if sha256(REPO/relative) != expected:
            raise RuntimeError(f'Implementation changed after freeze: {relative}')
    graph = load_archived_graph(output/'raw/hcw_graph.json')
    scenarios = json.loads((output/'raw/scenarios.json').read_text())
    rows = []
    for payload in scenarios:
        if split == 'validation' and payload['split'] != 'validation':
            continue
        if split == 'evaluation' and payload['split'] == 'validation':
            continue
        if split == 'validation':
            for depth in config['validation_depths']:
                row = evaluate(graph,payload,config,'adaptive_rollout_adp',depth)
                rows.append(row)
                print(f'{payload["scenario_id"]} depth={depth} success={row["success"]} cost={row["graph_cost"]:.3f} time={row["online_time_s"]:.3f}',flush=True)
        else:
            for method in config['methods']:
                row = evaluate(graph,payload,config,method,config['adaptive_rollout_depth'])
                rows.append(row)
            write_rows(output/'raw/scenario_results.csv',rows)
            print(f'{payload["scenario_id"]} '+', '.join(f'{row["method"]}:{int(row["success"])} J={row["graph_cost"]:.3f} t={row["online_time_s"]:.3f}' for row in rows[-len(config['methods']):]),flush=True)
    if split == 'validation':
        write_rows(output/'raw/validation_depth_results.csv',rows)
        return
    write_rows(output/'raw/heldout_results.csv',rows)
    summaries, paired = aggregate(rows,config)
    write_rows(output/'raw/heldout_summary.csv',summaries)
    write_rows(output/'raw/paired_comparisons.csv',paired)
    summary = {'study':config['study_name'],'primary_profile':config['primary_profile'],
               'frozen_at_utc':protocol['frozen_at_utc'], 'completed_at_utc':datetime.now(timezone.utc).isoformat(),
               'source_graph_sha256':protocol['source_graph_sha256'], 'superiority_config':asdict(study_config(config)),
               'base_experiment_config':json.loads((output/'config_snapshot/base_experiment_config.json').read_text()),
               'required_target_manifest':json.loads((output/'config_snapshot/required_targets.json').read_text()),
               'aggregates':summaries,'paired_comparisons':paired,
               'evaluation_rows':len(rows),'test_access_policy':'Requirements, splits and implementation hashes frozen before evaluation.',
               'limitations':['Same corrected archived graph; fresh scenario perturbations are not independent geometries.',
                              'Synthetic geometric requirements conditioned on archived candidate observability.',
                              'Visibility upper bounds are necessary conditions only.',
                              'No new ROS execution is represented by these graph results.']}
    write_json(output/'summary.json',summary)
    lines=['# Required-target ADP study','',f'Primary profile: `{config["primary_profile"]}`.',
           'Requirements and scenarios were frozen before evaluation; no infeasible scenario was removed.',
           'The 90 mesh-sample denominator is retained separately from the 41 candidate-observable samples.',
           '', '| Profile | Split | Method | Complete | N | Mean successful cost | Median online time (s) |',
           '|---|---|---|---:|---:|---:|---:|']
    lines += [f'| {r["profile_id"]} | {r["split"]} | {r["method"]} | {r["success_count"]} | {r["scenario_count"]} | {r["mean_successful_cost"]:.3f} | {r["median_online_time_s"]:.4f} |' for r in summaries]
    lines += ['', '## Evidence limits', '', *['- '+item for item in summary['limitations']], '',
              'ROS bags and videos are not generated by this offline study. Frozen manifests, per-scenario routes, target identities, and outcomes are archived under `raw/` and `config_snapshot/`.']
    (output/'summary.md').write_text('\n'.join(lines)+'\n')


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('freeze','validation','evaluation'))
    parser.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    output=args.output.resolve()
    if args.command=='freeze':
        freeze(args.config.resolve(),output)
    else:
        run(output,args.command)


if __name__=='__main__':
    main()
