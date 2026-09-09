"""Screen frozen routes with synchronous production dynamics and control functions.

This deterministic diagnostic omits ROS scheduling and is not execution evidence.
Final acceptance always requires the recorded ROS run and independent audits.
"""

import argparse
import bisect
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

from orbinspect_control.lqr_controller import LQRController
from orbinspect_dynamics.hcw_dynamics import HCWDynamics
from orbinspect_safety.collision_checker import CollisionChecker
from orbinspect_safety.keepout_zones import KeepoutZoneModel
from orbinspect_safety.projection_filter import ProjectionSafetyFilter


def screen(bundle: Path, config: Path) -> dict:
    """Return terminal errors using the unchanged runtime parameters at 20 Hz."""
    params = yaml.safe_load(config.read_text())
    dyn = params['hcw_dynamics_node']['ros__parameters']
    ctrl = params['trajectory_tracking_controller']['ros__parameters']
    safety = params['safety_filter_node']['ros__parameters']
    gates = params['verification_evaluator_node']['ros__parameters']
    dt = dyn['integration_dt']
    controller = LQRController(
        ctrl['position_gain'], ctrl['velocity_gain'], ctrl['max_acceleration'],
        controller_type=ctrl['controller_type'], mean_motion=ctrl['mean_motion'],
        control_dt=1 / ctrl['control_rate'], state_weights=ctrl['lqr_state_weights'],
        control_weights=ctrl['lqr_control_weights'],
        riccati_iterations=ctrl['riccati_iterations'],
    )
    model = HCWDynamics(dyn['mean_motion'])
    filt = ProjectionSafetyFilter(
        checker=CollisionChecker(KeepoutZoneModel(**{
            key: safety[key] for key in ('safety_margin', 'caution_margin', 'vehicle_radius')
        })), **{key: safety[key] for key in (
            'max_acceleration', 'max_speed', 'repulsion_gain', 'braking_time'
        )},
    )
    manifest = json.loads((bundle / 'manifest.json').read_text())
    rows = list(csv.DictReader((bundle / 'raw/trajectory.csv').open()))
    results = []
    for route in manifest['routes']:
        selected = [r for r in rows if r['scenario_id'] == route['scenario_id']
                    and r['method'] == route['method']]
        times = [float(r['time']) for r in selected]
        states = np.array([[float(r[k]) for k in ('rx', 'ry', 'rz', 'vx', 'vy', 'vz')]
                           for r in selected])
        ff = np.array([[float(r[k]) for k in ('ax', 'ay', 'az')] for r in selected])
        state = np.array(route['initial_state'])
        event_rows = [i for i, row in enumerate(selected)
                      if i == len(selected)-1 or row['action'] != selected[i+1]['action']]
        events_by_step = {round(times[i] / dt): i for i in event_rows}
        events = []
        interventions = 0
        delta_v = 0.0
        for step in range(round(times[-1] / dt) + 1):
            t = step * dt
            if step in events_by_step:
                i = events_by_step[step]
                position_error = float(np.linalg.norm(state[:3] - states[i, :3]))
                speed = float(np.linalg.norm(state[3:]))
                events.append(dict(action=int(selected[i]['action']),
                                   candidate_id=selected[i]['candidate_id'], time=t,
                                   position_error=position_error, speed=speed,
                                   accepted=position_error <= gates['position_tolerance']
                                   and speed <= gates['velocity_tolerance']))
            i = min(bisect.bisect_left(times, t), len(times)-1)
            ratio = 0 if i == 0 else np.clip((t-times[i-1])/(times[i]-times[i-1]), 0, 1)
            reference = states[0] if i == 0 else states[i-1] + ratio*(states[i]-states[i-1])
            command = controller.compute_control(state, reference[:3], reference[3:], ff[max(i, 1)])
            filtered = filt.filter_command(state[:3], state[3:], command)
            interventions += filtered.modified
            delta_v += np.linalg.norm(filtered.command) * dt
            state = np.array(model.rk4_step(state, filtered.command, dt))
        result = dict(scenario_id=route['scenario_id'], events=events,
                      all_observations_accepted=all(e['accepted'] for e in events),
                      accepted_count=sum(e['accepted'] for e in events),
                      filter_interventions=interventions, delta_v=float(delta_v))
        results.append(result)
        print(json.dumps(result), flush=True)
    return dict(kind='synchronous screening; not ROS execution',
                input_manifest_sha256=hashlib.sha256((bundle/'manifest.json').read_bytes()).hexdigest(),
                runtime_config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(), results=results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--config', type=Path,
                        default=Path('src/orbinspect_guidance/config/ros_verification.yaml'))
    args = parser.parse_args()
    report = screen(args.bundle, args.config)
    (args.bundle/'synchronous_screen.json').write_text(json.dumps(report, indent=2)+'\n')
