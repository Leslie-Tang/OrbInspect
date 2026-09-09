"""Retain every reference-header gap above the existing nominal threshold."""
from pathlib import Path
import sys,json,numpy as np
root=Path.cwd();sys.path.insert(0,str(root/'tools/paper'))
from audit_required_target_ros import read_bag,sha256
run=root/'data/results/20260909_093200_hybrid12_visual';samples=[]
for topic,msg,receipt in read_bag(run/'rosbag/orbinspect_run',('/chaser/reference_state',)):
 samples.append((msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9,receipt))
gaps=np.diff([s[0]for s in samples]);out={'kind':'reference timing diagnostic; separate from the unchanged count-completion gate','nominal_threshold_s':.075,'message_count':len(samples),'maximum_recorded_header_gap_s':float(max(gaps)),'gaps_above_nominal':[dict(preceding_header_s=samples[i][0],following_header_s=samples[i+1][0],gap_s=float(gaps[i]),time_since_first_reference_s=samples[i+1][0]-samples[0][0])for i in np.flatnonzero(gaps>.075)],'publisher_status':json.loads((run/'mesh_execution_audit.json').read_text())['reference_stream']}
(run/'reference_timing_diagnostic.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
