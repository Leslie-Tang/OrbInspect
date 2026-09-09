#!/usr/bin/env python3
"""Freeze and resume a sequential depth-one-to-six required-target diagnostic."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import platform
import resource
import shutil
from statistics import mean, median
import subprocess
import sys
from time import perf_counter, process_time

import numpy as np
import yaml

import run_required_target_confirmation as confirmation
import run_required_target_study as original

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT/'src/orbinspect_guidance/config/required_target_depth_diagnostic.yaml'


def now() -> str:
    """Return a timestamp independently of the human-readable bundle name."""
    return datetime.now(timezone.utc).isoformat()


def runtime() -> dict:
    """Record the host and runtime without promising an isolated benchmark."""
    result = {'recorded_at_utc':now(),'python_version':sys.version,
              'python_executable':sys.executable,'platform':platform.platform(),
              'machine':platform.machine(),'processor':platform.processor(),
              'logical_cpu_count':os.cpu_count(),'numpy_version':np.__version__,
              'pyyaml_version':yaml.__version__,
              'thread_environment':{k:os.environ.get(k) for k in
                                    ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')},
              'scheduling':'One plan at a time in depth-ascending order; no concurrent heavy project jobs requested.',
              'limitation':'Ordinary desktop background processes and thermal/scheduling variation are not controlled.'}
    if sys.platform=='darwin':
        for key,name in (('hw.memsize','physical_memory_bytes'),('machdep.cpu.brand_string','cpu_brand')):
            completed=subprocess.run(['sysctl','-n',key],capture_output=True,text=True,check=False)
            if completed.returncode==0:
                result[name]=completed.stdout.strip()
    return result


def freeze(config_path: Path, output: Path) -> None:
    """Freeze every reused validation input before the new timing pass."""
    if output.exists():
        raise FileExistsError(f'Will not overwrite {output}')
    diagnostic=yaml.safe_load(config_path.read_text())
    if diagnostic['diagnostic_depths']!=[1,2,3,4,5,6] or diagnostic['parallel_plans']!=1:
        raise ValueError('This diagnostic requires sequential depths one through six.')
    source=ROOT/diagnostic['source_study']
    confirmation.verify(source)
    scenarios=[p for p in json.loads((source/'raw/scenarios.json').read_text())
               if p['split']==diagnostic['scenario_split']]
    if len(scenarios)!=diagnostic['expected_scenario_count']:
        raise ValueError('The frozen validation scenario count differs.')
    required=json.loads((source/'config_snapshot/required_targets.json').read_text())
    profile=next(p for p in required['profiles'] if p['profile_id']==diagnostic['primary_profile'])
    if any(p['profile_id']!=profile['profile_id'] or p['required_target_ids']!=profile['required_target_ids']
           or p['required_target_mask']!=profile['required_target_mask'] for p in scenarios):
        raise ValueError('The source validation requirements are inconsistent.')
    for name in ('config_snapshot','raw','rosbag','figures','videos'):
        (output/name).mkdir(parents=True,exist_ok=True)
    shutil.copyfile(config_path,output/'config_snapshot/required_target_depth_diagnostic.yaml')
    for relative in ('raw/hcw_graph.json','raw/target_positions.csv',
                     'config_snapshot/required_target_study.yaml',
                     'config_snapshot/required_targets.json',
                     'config_snapshot/base_experiment_config.json'):
        shutil.copyfile(source/relative,output/relative)
    original.write_json(output/'raw/scenarios.json',scenarios)
    original.write_json(output/'config_snapshot/runtime_environment.json',runtime())
    inputs=['config_snapshot/required_target_depth_diagnostic.yaml',
            'config_snapshot/required_target_study.yaml','config_snapshot/required_targets.json',
            'config_snapshot/base_experiment_config.json','config_snapshot/runtime_environment.json',
            'raw/scenarios.json','raw/hcw_graph.json','raw/target_positions.csv']
    sources=[Path(__file__),Path(confirmation.__file__),Path(original.__file__),
             ROOT/'src/orbinspect_guidance/orbinspect_guidance/advanced_safe_planner.py',
             ROOT/'src/orbinspect_guidance/orbinspect_guidance/offline_adp_superiority_study.py']
    manifest={'frozen_at_utc':now(),'study_name':diagnostic['study_name'],
              'classification':diagnostic['classification'],'source_study':diagnostic['source_study'],
              'primary_profile':diagnostic['primary_profile'],'diagnostic_depths':diagnostic['diagnostic_depths'],
              'reference_depth':diagnostic['reference_depth'],'scenario_count':len(scenarios),
              'expected_plan_count':len(scenarios)*len(diagnostic['diagnostic_depths']),
              'scenario_ids':[p['scenario_id'] for p in scenarios],
              'required_target_ids':profile['required_target_ids'],
              'input_hashes':{p:original.sha256(output/p) for p in inputs},
              'source_hashes':{str(p.relative_to(ROOT)):original.sha256(p) for p in sources},
              'source_scenarios_sha256':original.sha256(source/'raw/scenarios.json'),
              'source_validation_results_sha256':original.sha256(source/'raw/validation_depth_results.csv'),
              'primary_test_policy_changed':False,'primary_test_results_recomputed':False,
              'depth_selection':'Post-selection diagnostic; depth three was already fixed and evaluated.',
              'completion_filter':'Keep all twelve scenarios at each depth, including visibility-impossible cases.',
              'timing_scope':'online_time_s includes standalone greedy-base construction plus ADP planning; graph loading and result serialization are excluded.',
              'screen_count_scope':'safe_action_evaluations counts ADP screens only and excludes the separate preliminary greedy-base call.',
              'observation_time_scope':'Observations are presumed stabilized with exposure completed a priori; mission_duration_s is transfer-only and adds no modeled exposure duration.'}
    original.write_json(output/'config_snapshot/freeze_manifest.json',manifest)
    print(json.dumps({'frozen':str(output),'plans':manifest['expected_plan_count'],
                      'depths':manifest['diagnostic_depths'],'scenarios':len(scenarios)},indent=2),flush=True)


def verify(output: Path) -> tuple[dict,dict,dict]:
    """Require byte-identical diagnostic inputs and implementation on resume."""
    manifest=json.loads((output/'config_snapshot/freeze_manifest.json').read_text())
    for section,base in (('input_hashes',output),('source_hashes',ROOT)):
        for relative,expected in manifest[section].items():
            if original.sha256(base/relative)!=expected:
                raise RuntimeError(f'Frozen {section} changed: {relative}')
    diagnostic=yaml.safe_load((output/'config_snapshot/required_target_depth_diagnostic.yaml').read_text())
    config=yaml.safe_load((output/'config_snapshot/required_target_study.yaml').read_text())
    return diagnostic,config,manifest


def read_rows(path: Path) -> list[dict]:
    """Read completed checkpoints without reevaluating their policies."""
    if not path.exists():
        return []
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def completed(row: dict) -> bool:
    """Normalize boolean values from either fresh or resumed CSV rows."""
    return str(row['success']).lower() in ('true','1')


def summarize(output: Path, rows: list[dict], diagnostic: dict, manifest: dict) -> None:
    """Use the common complete cohort for every depth's resource-cost mean."""
    depths=diagnostic['diagnostic_depths']
    groups={d:[r for r in rows if int(r['adaptive_rollout_depth'])==d] for d in depths}
    expected=set(manifest['scenario_ids'])
    if any({r['scenario_id'] for r in group}!=expected or len(group)!=len(expected) for group in groups.values()):
        raise RuntimeError('Incomplete or duplicate diagnostic matrix.')
    common=set.intersection(*[{r['scenario_id'] for r in group if completed(r)} for group in groups.values()])
    report=[]
    for depth,group in groups.items():
        successful=[r for r in group if completed(r)]
        matched=[r for r in group if r['scenario_id'] in common]
        report.append({'depth':depth,'scenario_count':len(group),'success_count':len(successful),
                       'common_success_count':len(matched),
                       'mean_common_graph_cost':mean(float(r['graph_cost']) for r in matched) if matched else math.nan,
                       'mean_common_delta_v':mean(float(r['total_delta_v']) for r in matched) if matched else math.nan,
                       'mean_penalized_cost_all':mean(float(r['penalized_cost']) for r in group),
                       'median_online_time_s_all':median(float(r['online_time_s']) for r in group),
                       'mean_online_time_s_all':mean(float(r['online_time_s']) for r in group),
                       'total_online_time_s_all':sum(float(r['online_time_s']) for r in group),
                       'median_online_time_s_common':median(float(r['online_time_s']) for r in matched) if matched else math.nan,
                       'mean_safe_action_evaluations_all':mean(float(r['safe_action_evaluations']) for r in group),
                       'mean_base_policy_time_s_all':mean(float(r['base_policy_time_s']) for r in group),
                       'max_process_peak_rss_bytes':max(int(r['process_peak_rss_bytes']) for r in group)})
    reference=next(r for r in report if r['depth']==diagnostic['reference_depth'])
    for row in report:
        row['graph_cost_difference_vs_depth3']=row['mean_common_graph_cost']-reference['mean_common_graph_cost']
        row['graph_cost_change_pct_vs_depth3']=100*(row['mean_common_graph_cost']/reference['mean_common_graph_cost']-1)
        row['median_online_time_ratio_vs_depth3']=row['median_online_time_s_all']/reference['median_online_time_s_all']
        row['screen_evaluation_ratio_vs_depth3']=row['mean_safe_action_evaluations_all']/reference['mean_safe_action_evaluations_all']
    original.write_rows(output/'raw/depth_summary.csv',report)
    summary={'study':diagnostic['study_name'],'classification':diagnostic['classification'],
             'frozen_at_utc':manifest['frozen_at_utc'],'completed_at_utc':now(),
             'primary_profile':diagnostic['primary_profile'],'scenario_count':len(expected),
             'plan_count':len(rows),'depths':depths,'common_success_scenario_ids':sorted(common),
             'reference_depth':3,'depth_summary':report,'primary_test_policy_changed':False,
             'source_study':diagnostic['source_study'],
             'timing_scope':manifest['timing_scope'],'screen_count_scope':manifest['screen_count_scope'],
             'observation_time_scope':manifest['observation_time_scope'],
             'limitations':['Post-selection validation diagnostic; cannot retroactively select the tested depth.',
                            'Single sequential measurement per scenario-depth on a shared desktop host.',
                            'Cost means condition on the common completed cohort; unconditional success and penalties remain visible.',
                            'Realized policy cost need not vary monotonically with depth; no universal optimum or real-time guarantee is implied.']}
    original.write_json(output/'summary.json',summary)
    lines=['# Required-target depth-one-to-six diagnostic','',
           'Post-selection, user-requested validation diagnostic. Exact twelve confirmation scenarios and nine required IDs are unchanged. Every depth is recomputed sequentially; primary test results are not changed.','',
           '| Depth | Complete | Common | Mean common J | Change vs d3 (%) | Median time (s) | Time / d3 | Mean ADP screens |',
           '|---:|---:|---:|---:|---:|---:|---:|---:|']
    lines += [f'| {r["depth"]} | {r["success_count"]}/{r["scenario_count"]} | {r["common_success_count"]} | {r["mean_common_graph_cost"]:.6f} | {r["graph_cost_change_pct_vs_depth3"]:.3f} | {r["median_online_time_s_all"]:.6f} | {r["median_online_time_ratio_vs_depth3"]:.3f} | {r["mean_safe_action_evaluations_all"]:.3f} |' for r in report]
    lines += ['',manifest['timing_scope'],manifest['screen_count_scope'],manifest['observation_time_scope'],'',
              *['- '+text for text in summary['limitations']]]
    (output/'summary.md').write_text('\n'.join(lines)+'\n')
    original.write_json(output/'raw/progress.json',{'state':'complete','completed_at_utc':now(),'completed_plans':len(rows),'expected_plans':manifest['expected_plan_count']})
    print(json.dumps(summary,indent=2),flush=True)


def run(output: Path) -> None:
    """Checkpoint every completed plan and resume the fixed matrix sequentially."""
    diagnostic,config,manifest=verify(output)
    lock=(output/'raw/diagnostic_run.lock').open('a+')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise RuntimeError('Another process is already running this diagnostic.') from error
    graph=original.load_archived_graph(output/'raw/hcw_graph.json')
    scenarios=json.loads((output/'raw/scenarios.json').read_text())
    csv_path=output/'raw/validation_depth_results.csv'
    rows=read_rows(csv_path)
    expected=[(depth,p['scenario_id']) for depth in diagnostic['diagnostic_depths'] for p in scenarios]
    keys=[(int(r['adaptive_rollout_depth']),r['scenario_id']) for r in rows]
    if keys!=expected[:len(keys)]:
        raise RuntimeError('Checkpoint rows are not a valid prefix of the frozen execution order.')
    session={'started_at_utc':now(),'pid':os.getpid(),'resumed_completed_plans':len(rows),'runtime':runtime()}
    with (output/'raw/run_sessions.jsonl').open('a') as stream:
        stream.write(json.dumps(session)+'\n')
    for depth in diagnostic['diagnostic_depths']:
        for payload in scenarios:
            if (depth,payload['scenario_id']) in keys:
                continue
            original.write_json(output/'raw/progress.json',{'state':'running','updated_at_utc':now(),
                                'depth':depth,'scenario_id':payload['scenario_id'],'completed_plans':len(rows),
                                'expected_plans':manifest['expected_plan_count']})
            started=now(); wall=perf_counter(); cpu=process_time()
            row=confirmation.evaluate(graph,payload,config,'adaptive_rollout_adp',depth)
            row.update(evaluation_started_at_utc=started,evaluation_completed_at_utc=now(),
                       plan_call_wall_time_s=perf_counter()-wall,plan_call_cpu_time_s=process_time()-cpu,
                       process_peak_rss_bytes=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*(1 if sys.platform=='darwin' else 1024),
                       modeled_additional_exposure_time_s=0.0)
            rows.append(row);keys.append((depth,payload['scenario_id']))
            temporary=csv_path.with_suffix('.checkpoint.csv')
            original.write_rows(temporary,rows)
            temporary.replace(csv_path)
            print(f'd={depth} {payload["scenario_id"]} complete={int(completed(row))} J={row["graph_cost"]:.6f} online={row["online_time_s"]:.4f}s screens={row["safe_action_evaluations"]} ({len(rows)}/{len(expected)})',flush=True)
    summarize(output,rows,diagnostic,manifest)
    lock.close()


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('freeze','run'))
    parser.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='freeze':
        freeze(args.config.resolve(),args.output.resolve())
    else:
        run(args.output.resolve())


if __name__=='__main__':
    main()
