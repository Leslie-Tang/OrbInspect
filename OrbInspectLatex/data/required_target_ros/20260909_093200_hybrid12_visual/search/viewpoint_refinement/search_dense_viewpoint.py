"""Search a bounded position shell with common-visibility and centered aim gates."""
import json, math, itertools, numpy as np, yaml
from pathlib import Path
from orbinspect_guidance.offline_planning_experiment import OfflinePlanningExperiment,ExperimentConfig
from orbinspect_safety.collision_checker import CollisionChecker
from orbinspect_safety.keepout_zones import KeepoutZoneModel
p=Path(__file__).resolve().parent
v=json.loads((p/'config_snapshot/base_experiment_config.json').read_text());v['output_root']=Path(v['output_root']);exp=OfflinePlanningExperiment(ExperimentConfig(**v));ts={t.target_id:t for t in exp.targets};base=next(c for c in exp.candidates if c.candidate_id=='cand_0013');original=exp.visibility.visible_targets_by_candidate[base.candidate_id];targets=[ts[t] for t in sorted(original)];points=np.array([t.position for t in targets]);print('camera',exp.base_planner.visibility_checker.camera,'targets',[(t.target_id,t.position,t.normal)for t in targets],flush=True)
s=yaml.safe_load(Path('src/orbinspect_guidance/config/ros_verification.yaml').read_text())['safety_filter_node']['ros__parameters'];checker=CollisionChecker(KeepoutZoneModel(**{k:s[k]for k in ('safety_margin','caution_margin','vehicle_radius')}));eligible=[];examined=individual_ok=0
for radius in (5.2,6,8,12,16,24,32):
 for k in range(1000):
  z=1-2*(k+.5)/1000;phi=k*math.pi*(3-math.sqrt(5));d=np.array([math.sqrt(1-z*z)*math.cos(phi),math.sqrt(1-z*z)*math.sin(phi),z]);pos=np.array(base.position)+radius*d;a=checker.assess(pos)
  if a.body_clearance<8.3:continue
  examined+=1
  if not all(exp.base_planner._target_visible(tuple(pos),t,t.position)for t in targets):continue
  individual_ok+=1;directions=points-pos;directions/=np.linalg.norm(directions,axis=1)[:,None]
  aims=[pos+directions.mean(axis=0)*30]
  aims.extend(pos+(directions[i]+directions[j])*15 for i,j in itertools.combinations(range(5),2))
  for aim in aims:
   if not all(exp.base_planner._target_visible(tuple(pos),t,tuple(aim))for t in targets):continue
   visible=[t.target_id for t in exp.targets if exp.base_planner._target_visible(tuple(pos),t,tuple(aim))];row=dict(original_id=base.candidate_id,candidate_id='cand_0013_safe',position=pos.tolist(),aim_position=aim.tolist(),displacement_m=radius,body_clearance=a.body_clearance,visible_target_ids=visible,original_visible=sorted(original));eligible.append(row);print('FOUND',json.dumps(row),flush=True);break
  if len(eligible)>=12:break
 print('radius',radius,'examined',examined,'individually_visible',individual_ok,'eligible',len(eligible),flush=True)
 if eligible:break
(p/'dense_viewpoint_search.json').write_text(json.dumps({'eligible':eligible,'examined':examined,'individually_visible':individual_ok,'search':'1000 Fibonacci directions, radii 5.2/6/8/12/16/24/32, original range/incidence/LOS/FOV, body clearance >=8.3'},indent=2)+'\n')
