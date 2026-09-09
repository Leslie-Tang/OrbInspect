"""Non-authoritative live progress and image previews; audits use original bags."""
from pathlib import Path
import json,time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image as RosImage
from std_msgs.msg import String
from nav_msgs.msg import Odometry
from PIL import Image
import numpy as np
out=Path(__file__).resolve().parents[1]
rclpy.init();node=Node('hybrid12_progress_preview');latest=[None];count=[0];start=time.time();progress={}
def camera(msg):
 latest[0]=msg
 if not (out/'camera_startup_preview.png').exists():save(msg,out/'camera_startup_preview.png')
def save(msg,path):
 a=np.frombuffer(msg.data,dtype=np.uint8).reshape(msg.height,msg.step)[:,:msg.width*3].reshape(msg.height,msg.width,3)
 Image.fromarray(a).save(path)
def event(msg):
 row=json.loads(msg.data);count[0]+=1
 with (out/'live_events.jsonl').open('a')as f:f.write(json.dumps(row)+'\n')
 if latest[0]is not None:save(latest[0],out/f'preview_observation_{count[0]:02}.png')
 progress['latest_event']=row
 print(json.dumps(row),flush=True)
def odom(msg):
 progress['latest_odom_stamp']=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
 progress['position']=[getattr(msg.pose.pose.position,k)for k in 'xyz']
def tick():
 progress.update(wall_time=time.time(),observations_seen=count[0],monitor_elapsed_s=time.time()-start)
 (out/'live_progress.json').write_text(json.dumps(progress,indent=2)+'\n')
node.create_subscription(RosImage,'/chaser/camera/image',camera,qos_profile_sensor_data)
node.create_subscription(String,'/verification/status',event,100)
node.create_subscription(Odometry,'/chaser/odom',odom,qos_profile_sensor_data)
node.create_timer(10,tick)
try:rclpy.spin(node)
except KeyboardInterrupt:pass
finally:node.destroy_node();rclpy.try_shutdown()
