"""Build Figure 7 data from one audited graphical run and its original camera bag."""
from __future__ import annotations

import argparse
import bisect
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from audit_required_target_ros import read_bag, sha256


def stamp(message_stamp) -> float:
    return message_stamp.sec + message_stamp.nanosec * 1e-9


def nearest_index(times, value: float) -> int:
    """Find an interior nearest sample without silently clamping missing evidence."""
    if not len(times) or not times[0] <= value <= times[-1]:
        raise ValueError('Requested time is outside the recorded evidence')
    i = bisect.bisect_left(times, value)
    return min((max(0, i-1), min(i, len(times)-1)), key=lambda j: abs(times[j]-value))


def prepare(run: Path, capture: Path, output: Path) -> dict:
    """Select uncropped frames and verify their timing and scene-pose agreement."""
    audit = json.loads((run/'required_target_execution_audit.json').read_text())
    if not audit['passed']:
        raise ValueError('Graphical execution audit must pass before figure preparation')
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    events = audit['events']
    event_times = np.array([e['bag_receipt_time_s'] for e in events])
    selected = [None] * len(events)
    image_times, image_stamps, odometry, clock = [], [], [], []
    camera_bag = capture/'rosbag/camera'
    topics = ('/chaser/camera/image', '/chaser/odom', '/clock', '/verification/status')
    camera_events = []
    for topic, message, receipt in read_bag(camera_bag, topics):
        if topic == '/chaser/camera/image':
            header = stamp(message.header.stamp)
            image_times.append(receipt)
            image_stamps.append(header)
            sequence = int(np.argmin(abs(event_times-receipt)))
            mismatch = abs(event_times[sequence]-receipt)
            if mismatch <= 0.2 and (selected[sequence] is None or mismatch < selected[sequence]['gap']):
                if message.encoding != 'rgb8':
                    raise ValueError(f'Unexpected original image encoding: {message.encoding}')
                pixels = np.frombuffer(message.data, dtype=np.uint8).reshape(message.height, message.step)
                pixels = pixels[:, :message.width*3].reshape(message.height, message.width, 3).copy()
                selected[sequence] = dict(gap=float(mismatch), receipt=receipt,
                                          header=header, pixels=pixels, index=len(image_times)-1)
        elif topic == '/chaser/odom':
            p, q = message.pose.pose.position, message.pose.pose.orientation
            odometry.append((receipt, stamp(message.header.stamp), [p.x,p.y,p.z], [q.x,q.y,q.z,q.w]))
        elif topic == '/clock':
            clock.append((receipt, stamp(message.clock)))
        else:
            event = json.loads(message.data)
            event['camera_bag_receipt_time_s'] = receipt
            camera_events.append(event)
    if any(frame is None for frame in selected):
        raise ValueError('One or more observations have no camera frame within 0.2 s')
    original_events = json.loads((run/'raw/verification_events.json').read_text())
    if [{k:v for k,v in e.items() if k != 'bag_receipt_time_s'} for e in original_events] != [
        {k:v for k,v in e.items() if k != 'camera_bag_receipt_time_s'} for e in camera_events
    ]:
        raise ValueError('Camera and execution bags do not contain identical verification events')
    # Preserve duplicate or reordered sensor stamps as stream diagnostics.
    # Selection uses receipt times and each selected frame must independently
    # align with a named Gazebo pose; duplicates are never silently discarded.
    timing_diagnostics = {
        'nonincreasing_receipt_indices': np.flatnonzero(np.diff(image_times) <= 0).tolist(),
        'nonincreasing_sensor_stamp_indices': np.flatnonzero(np.diff(image_stamps) <= 0).tolist(),
        'backward_sensor_stamp_indices': np.flatnonzero(np.diff(image_stamps) < 0).tolist(),
    }
    (output/'camera_timing_diagnostics.json').write_text(json.dumps(timing_diagnostics,indent=2)+'\n')
    np.savez_compressed(output/'camera_message_timestamps.npz',
                        receipt_s=image_times, simulator_stamp_s=image_stamps)
    scene = []
    with (capture/'gazebo_scene_poses.jsonl').open() as stream:
        for line in stream:
            record = json.loads(line)
            message = record['message']
            header = message['header']['stamp']
            t = int(header.get('sec', 0)) + int(header.get('nsec', 0))*1e-9
            poses = [p for p in message['pose'] if p['name'] == 'chaser']
            if len(poses) != 1:
                raise ValueError('Expected exactly one named Gazebo chaser pose')
            p, q = poses[0]['position'], poses[0]['orientation']
            scene.append((t, [p.get(k, 0) for k in 'xyz'],
                          [q.get(k, 0) for k in 'xyzw'], record['wall_receipt_ns']*1e-9))
    scene_times = [p[0] for p in scene]
    odom_times = [p[0] for p in odometry]
    if np.any(np.diff(scene_times) < 0) or np.any(np.diff(odom_times) < 0):
        raise ValueError('Pose timestamps must be ordered')
    rows = list(csv.DictReader((run/'raw/trajectory.csv').open()))
    executed = np.array([[float(r[k]) for k in ('rx','ry','rz')] for r in rows])
    tree = cKDTree(executed)
    run_manifest = json.loads((run/'config_snapshot/run_manifest.json').read_text())
    inputs = Path(run_manifest['input_bundle'])
    planned_rows = list(csv.DictReader((inputs/'raw/trajectory.csv').open()))
    planned = np.array([[float(r[k]) for k in ('rx','ry','rz')] for r in planned_rows])
    root = Path(__file__).resolve().parents[2]
    historical = root/'OrbInspectLatex/data/historical_ros/figure7'
    historical_meta = json.loads((historical/'snapshot.json').read_text())
    mesh = json.loads((run/'mesh_execution_audit.json').read_text())
    mesh_source = 'src/orbinspect_description/models/iss_real/meshes/ISS_stationary.glb'
    if historical_meta['source_sha256'][mesh_source] != mesh['mesh_sha256']:
        raise ValueError('Historical display mesh differs from the audited execution model')
    display_path = historical/historical_meta['arrays_file']
    if sha256(display_path) != historical_meta['arrays_sha256']:
        raise ValueError('Display mesh source hash mismatch')
    display = np.load(display_path, allow_pickle=False)['display_triangles']
    records, points = [], []
    for i, (event, frame) in enumerate(zip(events, selected, strict=True)):
        odom = odometry[nearest_index(odom_times, event['bag_receipt_time_s'])]
        distance, row = tree.query(odom[2])
        if distance > 1e-10:
            raise ValueError('Selected odometry state is absent from the executed CSV')
        scene_pose = scene[nearest_index(scene_times, frame['header'])]
        position_gap = float(np.linalg.norm(np.array(scene_pose[1])-odom[2]))
        qa, qb = np.array(scene_pose[2]), np.array(odom[3])
        cosine = abs(float(np.dot(qa,qb)/(np.linalg.norm(qa)*np.linalg.norm(qb))))
        angle = float(np.degrees(2*np.arccos(np.clip(cosine,-1,1))))
        scene_gap = abs(scene_pose[0]-frame['header'])
        if scene_gap > 0.041 or position_gap > 0.1 or angle > 0.5:
            raise ValueError(f'Camera pose alignment failed for view {i+1}: {scene_gap}, {position_gap}, {angle}')
        if frame['pixels'].std() < 2:
            raise ValueError(f'Camera view {i+1} is blank or nearly uniform')
        name = f'view_{i+1:02}.png'
        Image.fromarray(frame['pixels']).save(output/name)
        import hashlib
        record = dict(sequence=i+1, waypoint_id=event['current_waypoint_id'],
                      mission_time_s=event['time'], credited=event['credited'],
                      required_target_count=event['required_target_count'],
                      accepted_required_count=event['required_covered_count'],
                      cumulative_coverage=event['coverage_ratio'],
                      accepted_target_ids=event['credited_target_ids'],
                      camera_frame_index=frame['index'], camera_header_sim_time_s=frame['header'],
                      camera_bag_receipt_time_s=frame['receipt'],
                      event_bag_receipt_time_s=event['bag_receipt_time_s'],
                      camera_event_receipt_mismatch_s=frame['gap'],
                      scene_pose_sim_time_s=scene_pose[0], scene_camera_stamp_mismatch_s=scene_gap,
                      gazebo_chaser_position_m=scene_pose[1],
                      scene_to_event_odom_position_difference_m=position_gap,
                      scene_to_event_odom_orientation_difference_deg=angle,
                      event_odom_receipt_mismatch_s=abs(odom[0]-event['bag_receipt_time_s']),
                      trajectory_row_index=int(row), trajectory_time_s=float(rows[row]['time']),
                      executed_position_lvlh_m=executed[row].tolist(),
                      snapshot_image=name, snapshot_image_sha256=sha256(output/name),
                      snapshot_pixel_sha256=hashlib.sha256(frame['pixels'].tobytes()).hexdigest(),
                      snapshot_dimensions_px=[frame['pixels'].shape[1],frame['pixels'].shape[0]])
        records.append(record)
        points.append(executed[row])
    array_file = output/'trajectory_and_display_mesh.npz'
    np.savez_compressed(array_file, planned=planned, executed=executed,
                        event_points=np.array(points), display_triangles=display)
    gaps = np.diff(image_times)
    sim_gaps = np.diff(image_stamps)
    camera_audit = dict(
        passed=True, camera_and_execution_event_streams_identical=True,
        selection='Nearest MCAP wall receipt within 0.2 s; no endpoint clamping',
        image_message_count=len(image_times), clock_message_count=len(clock),
        camera_receipt_max_gap_s=float(gaps.max()), camera_receipt_median_gap_s=float(np.median(gaps)),
        camera_sim_stamp_max_gap_s=float(sim_gaps.max()),
        camera_stamp_nonincreasing_count=int(np.count_nonzero(sim_gaps<=0)),
        receipt_gap_over_0_2_s_count=int(np.count_nonzero(gaps>0.2)),
        missing_nominal_sensor_slots_estimate=int(np.maximum(0,np.rint(sim_gaps*15)-1).sum()),
        pose_gates=dict(scene_stamp_tolerance_s=0.041, position_tolerance_m=0.1, angle_tolerance_deg=0.5),
        camera_events=camera_events, views=records,
        stream_timing_diagnostics=timing_diagnostics,
        limitations='Receipt matching includes transport delay. Named scene poses verify alignment, not image-derived target identification or fresh visibility tests.',
        source_sha256={str(p):sha256(p) for p in [
            run/'required_target_execution_audit.json',run/'raw/trajectory.csv',
            capture/'capture_manifest.json',capture/'gazebo_scene_poses.jsonl',
            *sorted(camera_bag.glob('*'))] if p.is_file()})
    (output/'camera_audit.json').write_text(json.dumps(camera_audit,indent=2)+'\n')
    snapshot = dict(schema='orbinspect-required-target-camera-snapshot/v1', source_run=str(run),
                    goal_mode='required', execution_audit_passed=True, camera_audit_passed=True,
                    arrays_file=array_file.name, arrays_sha256=sha256(array_file),
                    trajectory_rows=len(executed), camera_views=records,
                    minimum_body_clearance_m=mesh['minimum_body_clearance_m'],
                    projection_limits_m=dict(x=[-58.46153846153846,58.46153846153846],
                                             y=[-50.38461538461539,60.38461538461539],z=[-80,80]),
                    mesh_sha256=mesh['mesh_sha256'], display_mesh_source_sha256=sha256(display_path),
                    display_mesh_scope='Unchanged corrected ISS geometry only; all camera images, paths and event positions come from this graphical run',
                    image_processing='Original RGB camera pixels, uncropped; no brightness, contrast, gamma or color adjustment',
                    camera_audit_sha256=sha256(output/'camera_audit.json'))
    (output/'snapshot.json').write_text(json.dumps(snapshot,indent=2)+'\n')
    print(json.dumps({k:v for k,v in camera_audit.items() if k not in ('source_sha256','views','camera_events')},indent=2))
    return snapshot


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('capture', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    prepare(args.run, args.capture, args.output)
