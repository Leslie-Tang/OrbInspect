"""Bounded nearby-position/aim search; no changes to visibility or safety gates."""
import itertools,json,math,yaml
from dataclasses import replace
from pathlib import Path
from orbinspect_guidance.offline_planning_experiment import OfflinePlanningExperiment,ExperimentConfig
from orbinspect_safety.collision_checker import CollisionChecker
from orbinspect_safety.keepout_zones import KeepoutZoneModel
p=Path('OrbInspectLatex/data/confirmation');values=json.loads((p/'config_snapshot/base_experiment_config.json').read_text());values['output_root']=Path(values['output_root']);exp=OfflinePlanningExperiment(ExperimentConfig(**values))
safety=yaml.safe_load(Path('src/orbinspect_guidance/config/ros_verification.yaml').read_text())['safety_filter_node']['ros__parameters'];checker=CollisionChecker(KeepoutZoneModel(**{k:safety[k] for k in ('safety_margin','caution_margin','vehicle_radius')}))
byid={c.candidate_id:c for c in exp.candidates};target_by_id={t.target_id:t for t in exp.targets}
directions=[tuple(v/math.sqrt(sum(x*x for x in d)) for v in d) for d in itertools.product((-1,0,1),repeat=3) if any(d)]
results={};inventory=[]
for node in ('cand_0063','cand_0013'):
    base=byid[node];original=exp.visibility.visible_targets_by_candidate[node];aim_ids=sorted(original|{base.source_target_id});candidates=[]
    for radius in (5.5,8.0,11.0):
        for d in directions:
            pos=tuple(v+radius*u for v,u in zip(base.position,d));a=checker.assess(pos)
            if a.body_clearance < safety['caution_margin']+.3:continue
            for aim in aim_ids:
                c=replace(base,candidate_id=f'{node}_near_{len(inventory):04}',position=pos,source_target_id=aim)
                visible=exp.base_planner.compute_visibility_matrix(exp.targets,[c]).visible_targets_by_candidate[c.candidate_id]
                row={'original_id':node,'candidate_id':c.candidate_id,'position':pos,'source_target_id':aim,'displacement_m':radius,'body_clearance':a.body_clearance,'original_visible':sorted(original),'visible_target_ids':sorted(visible),'preserves_original_visibility':original<=visible}
                inventory.append(row)
                if original<=visible:candidates.append(row)
    results[node]=candidates
    print(node,'candidates_preserving_all_original_targets',len(candidates),flush=True)
    if candidates:print(json.dumps(candidates[:3]),flush=True)
out=Path(__file__).resolve().parent
(out/'viewpoint_refinement_search.json').write_text(json.dumps({'scope':'26 cube directions, radii 5.5/8/11 m, original visible targets as possible aim anchors; body clearance >= caution margin +0.3 m; original geometry and camera criteria unchanged','inventory':inventory,'eligible':results},indent=2)+'\n')
