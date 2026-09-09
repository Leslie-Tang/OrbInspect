"""Record one normal-speed graphical execution with independently logged camera poses."""
from pathlib import Path
import json,os,signal,subprocess,time
root=Path.cwd();cap=root/'data/results/20260909_093200_hybrid12_camera';run=root/'data/results/20260909_093200_hybrid12_visual';bundle=root/'data/results/20260909_092700_hybrid12_refined_inputs_dwell60'
env=dict(os.environ,GZ_PARTITION='orbinspect_hybrid12_20260909_093200',QT_QPA_PLATFORM='xcb')
(cap/'capture_manifest.json').write_text(json.dumps({'associated_graphical_run':str(run),'clock_basis':'ROS wall time; Gazebo sensor stamps; nearest MCAP wall receipt and named Gazebo scene-pose alignment','storage':'MCAP zstd_fast; original sensor messages','selection_rule':'Nearest receipt within 0.2 s, no endpoint clamping'},indent=2)+'\n')
children=[];handles=[]
def start(command,name):
 f=(cap/name).open('w');handles.append(f);p=subprocess.Popen(command,stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True);children.append(p);return p
try:
 start(['ros2','run','ros_gz_bridge','parameter_bridge','/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],'bridge.log')
 start(['python3','tools/paper/record_gazebo_pose.py',str(cap/'gazebo_scene_poses.jsonl')],'pose_recorder.log')
 start(['ros2','bag','record','-o',str(cap/'rosbag/camera'),'--storage','mcap','--storage-preset-profile','zstd_fast','--disable-keyboard-controls','--topics','/chaser/camera/image','/chaser/odom','/chaser/attitude_reference','/verification/status','/clock'],'recorder.log')
 launch=start(['ros2','launch','orbinspect_bringup','ros_verification.launch.py',f'result_dir:={bundle}','scenario_id:=required09_test_000_bg95','method:=adaptive_rollout_adp','publish_mode:=closed_loop','headless:=false','time_scale:=1.0','visual_startup_delay:=10.0',f'gz_partition:={env["GZ_PARTITION"]}','record:=true','record_bag:=true','save_figures:=false',f'run_id:={run.name}'],'visual.launch.log')
 (cap/'processes.json').write_text(json.dumps({'runner':os.getpid(),'children':[p.pid for p in children],'started_wall_s':time.time()},indent=2)+'\n')
 code=launch.wait();time.sleep(2)
 (cap/'launch_completion.json').write_text(json.dumps({'exit_code':code,'finished_wall_s':time.time()},indent=2)+'\n')
finally:
 for p in reversed(children):
  if p.poll() is None:os.killpg(p.pid,signal.SIGINT)
 for p in children:
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
 for f in handles:f.close()
