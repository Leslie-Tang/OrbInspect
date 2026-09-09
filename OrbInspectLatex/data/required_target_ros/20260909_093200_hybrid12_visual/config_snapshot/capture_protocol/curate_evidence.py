"""Copy a compact, auditable evidence snapshot after all run and camera gates pass."""
from pathlib import Path
import json,shutil,hashlib
root=Path.cwd();run=root/'data/results/20260909_093200_hybrid12_visual';cap=root/'data/results/20260909_093200_hybrid12_camera';out=root/'OrbInspectLatex/data/required_target_ros'/run.name
bundle=root/'data/results/20260909_092700_hybrid12_refined_inputs_dwell60';plan=root/'data/results/20260909_090745_hybrid12_plan';search=root/'data/results/20260909_085617_ros_background_coverage_search'
def cp(source,dest):
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
def tree(source,dest):
 for p in source.rglob('*'):
  if p.is_file():cp(p,dest/p.relative_to(source))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
for name in ('required_target_execution_audit.json','mesh_execution_audit.json'):
 assert json.loads((run/name).read_text())['passed']
assert json.loads((run/'figure7/camera_audit.json').read_text())['passed']
if out.exists():raise FileExistsError(out)
out.mkdir(parents=True)
for name in ('raw','config_snapshot','figure7'):tree(run/name,out/name)
for p in cap.joinpath('config_snapshot').glob('*'):
 if p.is_file():cp(p,out/'config_snapshot/capture_protocol'/p.name)
for name in ('summary.json','summary.md','mesh_execution_audit.json','required_target_execution_audit.json','mesh_audit.log','target_audit.log','camera_preparation.log','camera_preparation_attempt1_empty_scene.log','reference_timing_diagnostic.json','reference_timing_diagnostic.log','figure_generation.log','figure_pdf_qa.json'):
 if (run/name).is_file():cp(run/name,out/name)
cp(cap/'visual.launch.log',out/'launch.log')
cp(cap/'capture_manifest.json',out/'rosbag/camera/capture_manifest.json')
cp(cap/'launch_completion.json',out/'launch_completion.json')
cp(cap/'figure_source_qa.json',out/'figure_source_qa.json')
cp(root/'OrbInspectLatex/data/required_target_ros/20260909_040344_required09_dwell60_visual/font_provenance.json',out/'font_provenance.json')
cp(cap/'tool_tests.log',out/'tool_tests.log')
cp(cap/'rosbag/camera/metadata.yaml',out/'rosbag/camera/metadata.yaml')
cp(run/'rosbag/orbinspect_run/metadata.yaml',out/'rosbag/core/metadata.yaml')
for name in ('raw','config_snapshot'):tree(bundle/name,out/'config_snapshot/replay_inputs'/name)
cp(bundle/'manifest.json',out/'config_snapshot/replay_inputs/manifest.json')
cp(bundle/'synchronous_screen.json',out/'search/refined_synchronous_screen.json')
cp(root/'data/results/20260909_090745_hybrid12_dwell60_inputs/synchronous_screen.json',out/'search/original12_synchronous_screen.json')
for p in plan.iterdir():
 if p.is_file() and p.suffix in ('.json','.py','.log','.md'):cp(p,out/'search/viewpoint_refinement'/p.name)
for p in search.iterdir():
 if p.is_file() and p.suffix in ('.json','.py','.log','.md'):cp(p,out/'search/background_coverage'/p.name)
for name in ('prepare_higher_coverage_ros_inputs.py','refine_ros_viewpoints.py','add_ros_terminal_dwell.py','audit_required_target_ros.py','prepare_required_target_camera_snapshot.py','record_gazebo_pose.py','screen_required_target_routes.py'):
 cp(root/'tools/paper'/name,out/'tools'/name)
cp(root/'OrbInspectLatex/scripts/generate_ros_camera_figure.py',out/'tools/generate_ros_camera_figure.py')
large=[*sorted((run/'rosbag/orbinspect_run').glob('*.mcap')),*sorted((cap/'rosbag/camera').glob('*.mcap')),cap/'gazebo_scene_poses.jsonl']
manifest={'result_kind':'compact supplemental12 ROS evidence snapshot','source_execution':str(run.relative_to(root)),'source_camera_capture':str(cap.relative_to(root)),'local_large_evidence':{str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size}for p in large},'scope':'Original unaltered bags and scene poses retained locally; selected RGB frames, complete CSV logs, audits, execution inputs and search/protocol provenance included.'}
(out/'rosbag/README.md').write_text('# Original recorded evidence\n\nCore and camera MCAPs and named Gazebo scene poses remain in the timestamped workspace result directories. Paths, sizes and SHA-256 values are in `snapshot_manifest.json`; these large files are not duplicated in the manuscript snapshot. Selected camera frames are unchanged RGB pixels from those bags.\n')
(out/'videos').mkdir();(out/'videos/README.md').write_text('# Video evidence\n\nOriginal camera messages are retained in the identified camera MCAP. Figure7 uses 12 independently aligned uncropped source frames. No separately encoded video is claimed.\n')
manifest['files_sha256']={str(p.relative_to(out)):sha(p)for p in sorted(out.rglob('*'))if p.is_file()}
(out/'snapshot_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(out)
