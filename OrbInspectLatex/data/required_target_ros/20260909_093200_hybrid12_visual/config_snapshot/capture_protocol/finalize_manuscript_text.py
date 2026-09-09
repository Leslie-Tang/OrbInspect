"""Insert measured values only after execution, mesh and camera audits pass."""
from pathlib import Path
import json,re,math
root=Path.cwd();run=root/'data/results/20260909_093200_hybrid12_visual';cap=root/'data/results/20260909_093200_hybrid12_camera';paper=root/'OrbInspectLatex'
a=json.loads((run/'required_target_execution_audit.json').read_text());m=json.loads((run/'mesh_execution_audit.json').read_text());c=json.loads((run/'figure7/camera_audit.json').read_text())
assert a['passed'] and m['passed'] and c['passed']
assert a['accepted_observations']==12 and a['accepted_required_count']==9
assert abs(a['accepted_background_coverage']-0.9585771560419855)<1e-10
maxpos=max(e['position_error']for e in a['events']);maxspeed=max(e['terminal_speed']for e in a['events']);maxcam=max(v['camera_event_receipt_mismatch_s']for v in c['views'])
number=lambda n:f'{n:,}'.replace(',',r'\,')
values={'TIME':f"{a['terminal']['time']:.3f}",'POS':f'{maxpos:.3f}','SPEED':f'{maxspeed:.4f}','DV':f"{a['executed_delta_v_until_terminal_mps']:.3f}",'PLANDV':f"{a['planned_delta_v_mps']:.3f}",'CONTROLS':number(a['control_message_count']),'FILTER':number(a['filter_intervention_samples']),'STATES':number(m['trajectory_samples']),'MARGIN':f"{m['minimum_body_clearance_m']:.3f}",'CAMGAP':f'{math.ceil(maxcam*1000)/1000:.3f}'}
text=(cap/'config_snapshot/ros_results_template.tex').read_text()
for key,value in values.items():text=text.replace('@'+key+'@',value)
assert not re.search('@[A-Z]+@',text)
(paper/'sections/ros_verification_results.tex').write_text(text)
p=paper/'sections/required_target_study.tex';s=p.read_text();s=s.replace('ROS-native HCW dynamics and LQR control track the frozen ADP route without online replanning. Each observation contributes its frozen visibility mask only when','ROS-native HCW dynamics and LQR control track an ADP-derived reference fixed before execution, without online replanning. Each observation contributes its fixed geometric visibility mask only when');s=s.replace('Execution success requires every observation to pass and every required target to be accepted.','Execution success requires every observation to pass and every required target to be accepted; the supplemental hybrid case also requires 95\\% weighted background coverage.');s=s.replace('The representative nine-target task imposes no background-coverage threshold.','The parent nine-target task imposes no background-coverage threshold; the supplemental case adds this threshold while retaining its target IDs and weights.');p.write_text(s)
rows=[('Required targets accepted','9/9'),('Observations accepted','12/12'),('Weighted background coverage',f"{a['accepted_background_coverage']*100:.9f}%"),('Inspectable samples accepted','39/41'),('Completion time',f"{a['terminal']['time']:.9f} s"),('Safe-control integral through final event',f"{a['executed_delta_v_until_terminal_mps']:.9f} m/s"),('Transfer-and-hold reference effort',f"{a['planned_delta_v_mps']:.9f} m/s"),('Maximum terminal position error',f'{maxpos:.9f} m'),('Maximum terminal speed',f'{maxspeed:.9f} m/s'),('Filter-active safety messages',str(a['filter_intervention_samples'])),('Safe-control messages',str(a['control_message_count'])),('Trajectory samples',str(m['trajectory_samples'])),('Full transformed mesh triangles','247525'),('Minimum swept-body margin above required 2 m',f"{m['minimum_body_clearance_m']:.9f} m"),('Peak acceleration',f"{m['peak_safe_acceleration_mps2']:.9f} m/s²"),('Recorded camera messages',str(c['image_message_count'])),('Maximum selected camera/event receipt mismatch',f'{maxcam:.9f} s'),('Maximum scene/event position difference',f"{max(v['scene_to_event_odom_position_difference_m']for v in c['views']):.9f} m"),('Maximum scene/event orientation difference',f"{max(v['scene_to_event_odom_orientation_difference_deg']for v in c['views']):.9f} degrees")]
doc='''# Twelve-observation higher-coverage ROS execution, 2026-09-09

The supplemental normal-speed graphical execution **20260909_093200_hybrid12_visual**
accepted all 12 observations, all nine required targets and **95.8577156%** weighted
background coverage. The prior nine-view run reached 77.2174358% with the same
required IDs and weights. This is an 18.6403 percentage-point increase, with
three more observations and a 450-s longer nominal execution schedule.

This is a selected supplemental hybrid task, not a new held-out confirmation
result. The fixed denominator contains the same 41 inspectable target IDs;
39 are accepted. The two missing IDs are `mesh_00009` and `mesh_00088`. Neither
39/41 nor the weighted percentage denotes complete continuous ISS surface coverage.

## Selection and retained diagnostic

The hybrid ADP search on the unchanged parent scenario selected 12 views for a
95% goal. The original 12-view schedule passed 10/12 synchronous tracking checks;
views 5 and 12 stopped 2.868740 and 2.618019 m from their intended positions because
the endpoints lay inside the unchanged proxy caution zone. This failure is retained.
A declared local position-and-aim search moved those endpoints by 8 m and 6 m.
All original visible target IDs were preserved, all visibility masks and HCW
transfers were recomputed, and the 12-view order was retained. The selected
adjustments and full search inventories are included in the evidence snapshot.
The refined schedule passed all 12 synchronous checks before this graphical run.

The original 2-m safety margin, 8-m caution distance, 0.8-m vehicle radius,
0.060-m/s² acceleration limit, 1.5-m/s speed limit and 0.5-m/0.05-m/s acceptance
tolerances were unchanged. The same camera range, incidence, field-of-view and
full-mesh line-of-sight predicates were retained. Each 90-s transfer has a
60-s stationary settling interval, for a nominal 1800-s schedule. No accelerated
probe result is substituted for this normal-speed graphical execution.

## Recorded results

| Quantity | Value |
|---|---:|
'''+''.join(f'| {k} | {v} |\n'for k,v in rows)+'''
All execution, full-mesh and selected camera alignment gates passed. Target
credit is the union of pre-execution geometric visibility masks admitted by
terminal tracking; images provide synchronized visual context, not fresh
image-based target recognition or defect detection. The full-mesh audit checks
all connecting trajectory segments with the 0.8-m body radius and subtracts
the required 2-m margin. Control effort uses timestamped safe-command norms
with zero-order holds, clipped at the final event receipt.

Figure 7 retains Arial fonts, the approved path/mesh treatment and the existing
observation palette, extended for views 11 and 12. Twelve uncropped camera
frames appear in two chronological rows of six; odd/even numbered markers are
highlighted in the two equally scaled projections to prevent label collisions.
The new layout is 170 by 47 mm, with 18.1-mm camera panels. It is 3 mm taller
than the approved nine-view 44-mm layout and 34.7% shorter than the earlier
72-mm layout. No source image brightness, color, contrast or crop is changed.
The nine-view layout is archived in
`archive/figure7_nine_view_two_rows_20260909/`; its renderer regression retained
identical PNG pixels before adding the new 12-view branch.

The original 810-s failed run, the successful 1350-s nine-view graphical run,
the original 12-view diagnostic failure and all refinement inventories remain
available. Figures 1–6, the frozen offline study, bibliography and the 11.05%
offline saving are unchanged. This single adjusted execution establishes no
paired ROS maneuver-saving or population success-rate claim.

The compact evidence snapshot is
`data/required_target_ros/20260909_093200_hybrid12_visual/`. Its manifest records
all included file hashes and paths/hashes/sizes of the original local core and
camera MCAPs and named Gazebo pose stream. The reviewed manuscript is exported
to `output/pdf/OrbInspect_IEEE_TAES_ROS_12_observations_20260909.pdf` in the workspace.
'''
doc += (cap/'config_snapshot/reference_timing_note.md').read_text()
(paper/'docs/ROS_TWELVE_OBSERVATIONS_20260909.md').write_text(doc)
(cap/'measured_manuscript_values.json').write_text(json.dumps({'values':values,'table':dict(rows)},indent=2)+'\n')
print(json.dumps(values,indent=2))
