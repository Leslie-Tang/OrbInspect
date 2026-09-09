"""Try explicit centered boresights with the original visibility predicates."""
import json, numpy as np
from pathlib import Path
from orbinspect_guidance.offline_planning_experiment import OfflinePlanningExperiment,ExperimentConfig
p=Path(__file__).resolve().parent
v=json.loads((p/'config_snapshot/base_experiment_config.json').read_text());v['output_root']=Path(v['output_root']);exp=OfflinePlanningExperiment(ExperimentConfig(**v));targets={t.target_id:t for t in exp.targets}
search=json.loads((p/'viewpoint_refinement_search.json').read_text());eligible=[];seen=set();inventory=[]
for r in search['inventory']:
 if r['original_id']!='cand_0013' or tuple(r['position']) in seen:continue
 seen.add(tuple(r['position']));pos=np.array(r['position']);original=r['original_visible'];points=np.array([targets[t].position for t in original]);directions=points-pos;directions/=np.linalg.norm(directions,axis=1)[:,None]
 aims=[points.mean(axis=0),pos+directions.mean(axis=0)*30]
 for i in range(len(points)):
  for j in range(i+1,len(points)):aims.append(pos+(directions[i]+directions[j])*15)
 for aim in aims:
  visible=[t.target_id for t in exp.targets if exp.base_planner._target_visible(tuple(pos),t,tuple(aim))]
  row=dict(r,aim_position=aim.tolist(),visible_target_ids=visible,preserves_original_visibility=set(original)<=set(visible));inventory.append(row)
  if row['preserves_original_visibility']:eligible.append(row);print('FOUND',json.dumps(row),flush=True);break
(p/'centered_aim_search.json').write_text(json.dumps({'inventory':inventory,'eligible':eligible},indent=2)+'\n');print('eligible',len(eligible),flush=True)
