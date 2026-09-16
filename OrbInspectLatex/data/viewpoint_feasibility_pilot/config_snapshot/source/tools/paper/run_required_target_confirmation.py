#!/usr/bin/env python3
"""Freeze and run a fresh required-nine confirmation with an ADP-seeded comparator."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
from time import perf_counter

import yaml

import run_required_target_study as original
from orbinspect_guidance.advanced_safe_planner import AdvancedSafePlanner

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / 'src/orbinspect_guidance/config/required_target_confirmation.yaml'


def verify(output: Path) -> tuple[dict, dict]:
    """Verify fixed inputs and source before any confirmation evaluation."""
    config = yaml.safe_load((output/'config_snapshot/required_target_study.yaml').read_text())
    frozen = json.loads((output/'config_snapshot/freeze_manifest.json').read_text())
    for section, base in (('input_hashes', output), ('source_hashes', ROOT)):
        for relative, expected in frozen[section].items():
            if original.sha256(base/relative) != expected:
                raise RuntimeError(f'Frozen {section} changed: {relative}')
    return config, frozen


def freeze(config_path: Path, output: Path) -> None:
    """Copy the original required-nine identities and freeze fresh scenarios."""
    if output.exists():
        raise FileExistsError(f'Will not overwrite {output}')
    config = yaml.safe_load(config_path.read_text())
    source = ROOT/config['source_study']
    prior = json.loads((source/'config_snapshot/required_targets.json').read_text())
    profile = next(p for p in prior['profiles'] if p['profile_id']=='required09')
    requirements = dict(prior, profiles=[profile],
                        confirmation_requirement_source=str(source.relative_to(ROOT)),
                        requirements_reselected=False)
    graph = original.load_archived_graph(source/'raw/hcw_graph.json')
    known_seeds, scanned = set(), []
    for old in sorted((ROOT/'data/results').glob('*/raw/scenarios.json')):
        payload = json.loads(old.read_text())
        if isinstance(payload, list):
            known_seeds.update(int(row['seed']) for row in payload if 'seed' in row)
            scanned.append(str(old.relative_to(ROOT)))
    scenarios = []
    for split_index, split in enumerate(('validation','test','ood')):
        for index in range(config[f'{split}_scenarios']):
            seed = config['seed_base'] + split_index*10000 + index
            if seed in known_seeds:
                raise ValueError(f'Fresh confirmation seed collision: {seed}')
            scenarios.append(original.scenario_payload(graph,config,profile,split,index,seed))
    for name in ('config_snapshot','raw','rosbag','figures','videos'):
        (output/name).mkdir(parents=True,exist_ok=True)
    shutil.copyfile(config_path,output/'config_snapshot/required_target_study.yaml')
    for relative in ('raw/hcw_graph.json','raw/target_positions.csv',
                     'config_snapshot/base_experiment_config.json'):
        shutil.copyfile(source/relative,output/relative)
    original.write_json(output/'config_snapshot/required_targets.json',requirements)
    original.write_json(output/'raw/scenarios.json',scenarios)
    inputs = ['config_snapshot/required_target_study.yaml','config_snapshot/required_targets.json',
              'config_snapshot/base_experiment_config.json','raw/scenarios.json',
              'raw/target_positions.csv','raw/hcw_graph.json']
    sources = [Path(__file__),Path(original.__file__),
               ROOT/'src/orbinspect_guidance/orbinspect_guidance/advanced_safe_planner.py',
               ROOT/'src/orbinspect_guidance/orbinspect_guidance/offline_adp_superiority_study.py']
    protocol = {'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
                'source_graph_sha256':original.sha256(output/'raw/hcw_graph.json'),
                'input_hashes':{p:original.sha256(output/p) for p in inputs},
                'source_hashes':{str(p.relative_to(ROOT)):original.sha256(p) for p in sources},
                'predecessor_study':config['source_study'],
                'design_reason':'Original campaign exposed failed greedy seeds; comparator changed before new scenarios were evaluated.',
                'primary_profile':'required09','required_ids_copied_unchanged':profile['required_target_ids'],
                'primary_comparator':config['primary_comparator'],
                'primary_endpoint':config['primary_endpoint'],
                'methods':config['methods'],'scenario_count':len(scenarios),
                'prior_seed_count':len(known_seeds),'prior_scenario_archives_scanned':scanned,
                'rejected_scenario_count':0,
                'scenario_sampling':'Unconditional new seeds; requirements never shrink after node loss.',
                'depth_selection':'Depth three unchanged; validation depths are descriptive only.',
                'comparator':'Three-pass audited local search seeded by complete depth-one ADP, not a non-ADP baseline.',
                'fallback':'ADP3 receives no one-step fallback.',
                'failure_penalty':'cost + 500*required_missing_fraction + 500*not_required_complete'}
    original.write_json(output/'config_snapshot/freeze_manifest.json',protocol)
    print(json.dumps({'frozen':str(output),'scenario_count':len(scenarios),
                      'required_target_ids':profile['required_target_ids']},indent=2),flush=True)


def evaluate(graph, payload: dict, config: dict, method: str, depth: int=3) -> dict:
    """Audit routes on the shared required task and account for seed computation."""
    problem = original.make_problem(graph,payload,coverage_only=method=='coverage_only80')
    cfg = original.study_config(config,depth)
    base_cfg,_ = original._method_config('adaptive_rollout_adp',cfg,())
    started = perf_counter()
    base = AdvancedSafePlanner(base_cfg).base_policy_plan(problem)
    base_time = perf_counter()-started
    seed, seed_time = None, 0.0
    started = perf_counter()
    if method=='incumbent':
        plan = base
    elif method in {'one_step_adp','seeded_local_search'}:
        seed_cfg,_ = original._method_config('adaptive_rollout_adp',original.study_config(config,1),())
        seed_started = perf_counter()
        seed = AdvancedSafePlanner(seed_cfg).plan(problem)
        seed_time = perf_counter()-seed_started
        if method=='one_step_adp':
            plan = seed
        else:
            local_cfg,_ = original._method_config('local_search',cfg,())
            plan = AdvancedSafePlanner(local_cfg).plan(replace(problem,reference_node_ids=seed.node_ids if seed.success else ()))
    else:
        plan_cfg,_ = original._method_config('adaptive_rollout_adp',cfg,())
        plan = AdvancedSafePlanner(plan_cfg).plan(problem)
    elapsed = perf_counter()-started+base_time
    masks = dict(zip(graph.node_ids,graph.coverage_masks))
    covered, available, base_mask = 0,0,0
    current, edges = None,[]
    for node in payload['available_node_ids']:
        available |= masks[node]
    for node in plan.node_ids:
        covered |= masks[node]
        edges.append(problem.edge_evaluator(current,node))
        current=node
    for node in base.node_ids:
        base_mask |= masks[node]
    required = int(payload['required_target_mask'])
    required_count = required.bit_count()
    covered_count = (covered&required).bit_count()
    missing = [target for i,target in enumerate(graph.target_ids) if required&(1<<i) and not covered&(1<<i)]
    success,base_success = not missing,(base_mask&required)==required
    return {'profile_id':payload['profile_id'],'split':payload['split'],'scenario_id':payload['scenario_id'],
            'scenario_seed':payload['seed'],'method':method,'adaptive_rollout_depth':1 if method=='one_step_adp' else depth,
            'success':success,'native_goal_success':bool(plan.success),'required_coverage':covered_count/required_count,
            'required_target_count':required_count,'required_covered_count':covered_count,'missing_required_ids':';'.join(missing),
            'coverage':plan.coverage_ratio,'covered_target_count':covered.bit_count(),
            'inspectable_sample_coverage':covered.bit_count()/len(graph.target_ids),'whole_sample_coverage':covered.bit_count()/90,
            'graph_cost':plan.total_cost,'penalized_cost':plan.total_cost+config['evaluation_missing_fraction_penalty']*(1-covered_count/required_count)+config['evaluation_failure_penalty']*(not success),
            'total_delta_v':sum(e.delta_v for e in edges),'selected_count':len(plan.node_ids),
            'mission_duration_s':len(plan.node_ids)*config['transfer_duration_s'],'online_time_s':elapsed,'base_policy_time_s':base_time,
            'safe_action_evaluations':plan.safe_action_evaluations,'shield_rejections':plan.shield_rejections,
            'min_clearance':min((e.min_clearance for e in edges),default=math.nan),'peak_input':max((e.peak_input for e in edges),default=math.nan),
            'unsafe_selected_edges':sum(not e.feasible or e.min_clearance<0 or e.peak_input>e.input_limit+1e-12 for e in edges),
            'required_visibility_available':(available&required)==required,'required_visibility_upper_bound':(available&required).bit_count()/required_count,
            'available_node_count':len(payload['available_node_ids']),'base_success':base_success,'base_graph_cost':base.total_cost,
            'cost_exceeds_successful_base':bool(method=='adaptive_rollout_adp' and base_success and success and plan.total_cost>base.total_cost+1e-9),
            'policy_source':plan.policy_source,'route_node_ids':';'.join(plan.node_ids),'covered_target_mask':covered,'base_route_node_ids':';'.join(base.node_ids),
            'seed_route_node_ids':';'.join(seed.node_ids) if seed is not None else '',
            'seed_success':bool(seed.success) if seed is not None else False,
            'seed_graph_cost':seed.total_cost if seed is not None else math.nan,'seed_time_s':seed_time}


def run(output: Path, split: str) -> None:
    """Run a fixed campaign and preserve all failures and matched rows."""
    config,frozen = verify(output)
    graph = original.load_archived_graph(output/'raw/hcw_graph.json')
    scenarios = json.loads((output/'raw/scenarios.json').read_text())
    rows=[]
    for payload in scenarios:
        if (payload['split']=='validation') != (split=='validation'):
            continue
        jobs = [('adaptive_rollout_adp',d) for d in config['validation_depths']] if split=='validation' else [(m,config['adaptive_rollout_depth']) for m in config['methods']]
        for method,depth in jobs:
            row=evaluate(graph,payload,config,method,depth)
            rows.append(row)
        path=output/'raw'/('validation_depth_results.csv' if split=='validation' else 'scenario_results.csv')
        original.write_rows(path,rows)
        print(payload['scenario_id']+' '+', '.join(f'{r["method"]}:d{r["adaptive_rollout_depth"]} complete={int(r["success"])} J={r["graph_cost"]:.3f}' for r in rows[-len(jobs):]),flush=True)
    if split=='validation':
        return
    original.write_rows(output/'raw/heldout_results.csv',rows)
    summaries,comparisons=original.aggregate(rows,config)
    original.write_rows(output/'raw/heldout_summary.csv',summaries)
    original.write_rows(output/'raw/paired_comparisons.csv',comparisons)
    summary={'study':config['study_name'],'primary_profile':'required09',
             'primary_comparator':config['primary_comparator'],'primary_endpoint':config['primary_endpoint'],
             'frozen_at_utc':frozen['frozen_at_utc'],'completed_at_utc':datetime.now(timezone.utc).isoformat(),
             'source_graph_sha256':frozen['source_graph_sha256'],
             'base_experiment_config':json.loads((output/'config_snapshot/base_experiment_config.json').read_text()),
             'superiority_config':asdict(original.study_config(config)),
             'required_target_manifest':json.loads((output/'config_snapshot/required_targets.json').read_text()),
             'aggregates':summaries,'paired_comparisons':comparisons,'evaluation_rows':len(rows),
             'predecessor_study':config['source_study'],
             'limitations':['Comparator includes depth-one ADP; effects are empirical and not guaranteed against local search.',
                            'Same corrected graph and unchanged synthetic nine-item requirement; fresh perturbations are not independent geometries.',
                            'All greedy-base failures are retained; base-cost bound is conditional on successful greedy completion.',
                            'No new ROS execution or DRL-trained policy is represented by this campaign.']}
    original.write_json(output/'summary.json',summary)
    lines=['# Fresh required-nine ADP confirmation','',
           'The original nine required IDs are unchanged. Fresh scenarios and the one-step-ADP-seeded local comparator were frozen before evaluation.',
           'No scenario is rejected. ADP3 has no one-step fallback. All base diagnostics refer to the original greedy policy.','',
           '| Split | Method | Complete | N | Successful mean cost | Median time (s) |',
           '|---|---|---:|---:|---:|---:|']
    lines += [f'| {r["split"]} | {r["method"]} | {r["success_count"]} | {r["scenario_count"]} | {r["mean_successful_cost"]:.3f} | {r["median_online_time_s"]:.4f} |' for r in summaries]
    lines += ['',*['- '+item for item in summary['limitations']],'',
              'Frozen inputs, target identities and per-scenario routes are retained under raw/ and config_snapshot/. ROS bags and videos are not generated.']
    (output/'summary.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'complete':str(output),'rows':len(rows)},indent=2),flush=True)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('freeze','validation','evaluation'))
    parser.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='freeze':
        freeze(args.config.resolve(),args.output.resolve())
    else:
        run(args.output.resolve(),args.command)


if __name__=='__main__':
    main()
