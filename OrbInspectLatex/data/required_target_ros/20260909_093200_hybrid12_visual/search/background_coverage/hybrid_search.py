"""Diagnostic planning only: keep required targets and scenario weights fixed."""
import dataclasses
import hashlib
import json
from pathlib import Path
import time
import yaml
from orbinspect_guidance.advanced_safe_planner import AdvancedSafePlanner
from orbinspect_guidance.offline_adp_superiority_study import load_archived_graph, SuperiorityConfig, _method_config, _problem_for_scenario
from orbinspect_guidance.ros_route_exporter import _load_scenarios
out=Path(__file__).resolve().parent
source=Path('OrbInspectLatex/data/confirmation')
config=yaml.safe_load((out/'config_snapshot/search.yaml').read_text())
graph=load_archived_graph(source/'raw/hcw_graph.json')
scenario=next(s for s in _load_scenarios(source/'raw/scenarios.json') if s.scenario_id==config['source_scenario'])
payload=next(s for s in json.loads((source/'raw/scenarios.json').read_text()) if s['scenario_id']==scenario.scenario_id)
settings=SuperiorityConfig(**json.loads((source/'summary.json').read_text())['superiority_config'])
mask_by_node=dict(zip(graph.node_ids,graph.coverage_masks));required=int(payload['required_target_mask'])
results=[]
for max_steps in config['max_observations']:
    for goal in config['goal_coverages']:
        problem=dataclasses.replace(_problem_for_scenario(graph,scenario),goal_mode='hybrid',goal_coverage=goal,max_steps=max_steps,required_target_mask=required)
        params=dataclasses.replace(settings,goal_coverage=goal,max_steps=max_steps)
        planner_config,checkpoint=_method_config('adaptive_rollout_adp',params,AdvancedSafePlanner().critic_weights)
        start=time.monotonic();plan=AdvancedSafePlanner(planner_config,critic_weights=checkpoint).plan(problem)
        mask=0
        for node in plan.node_ids:mask |= mask_by_node[node]
        covered_ids=[t for i,t in enumerate(graph.target_ids) if mask>>i&1]
        result={'goal':goal,'max_steps':max_steps,'success':plan.success,'coverage':plan.coverage_ratio,'observations':len(plan.node_ids),'route':list(plan.node_ids),'required_accepted':(mask & required).bit_count(),'covered_samples':mask.bit_count(),'covered_target_mask':mask,'covered_ids':covered_ids,'graph_cost':plan.total_cost,'planning_wall_s':time.monotonic()-start}
        results.append(result);print(json.dumps(result),flush=True)
        (out/'hybrid_search.json').write_text(json.dumps({'result_kind':'planning_predictions_not_ros_execution','source_scenario':scenario.scenario_id,'required_ids':payload['required_target_ids'],'source_graph_sha256':hashlib.sha256((source/'raw/hcw_graph.json').read_bytes()).hexdigest(),'results':results},indent=2)+'\n')
