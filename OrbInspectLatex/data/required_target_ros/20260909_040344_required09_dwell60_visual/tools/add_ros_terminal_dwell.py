"""Create an explicit execution schedule with uniform terminal settling periods.

The archived route and transfers remain immutable. This derived input bundle
adds stationary HCW references and evaluates observations after each dwell.
It is not an archived planning result and does not change acceptance gates.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import yaml


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_dwell(source: Path, destination: Path, seconds: float, mean_motion: float) -> Path:
    """Append fixed-position, zero-velocity HCW holds on the source sample grid."""
    if destination.exists():
        raise FileExistsError(destination)
    manifest = json.loads((source/'manifest.json').read_text())
    dt = float(manifest['integration_dt'])
    if seconds <= 0 or not math.isclose(seconds / dt, round(seconds / dt)):
        raise ValueError('Dwell must be positive and a multiple of the sample interval')
    for name, digest in manifest['output_files_sha256'].items():
        if sha(source/'raw'/name) != digest:
            raise ValueError(f'Source hash mismatch: {name}')
    if manifest['route_count'] != 1:
        raise ValueError('Use a single frozen route per derived bundle')
    destination.mkdir(parents=True)
    for folder in ('raw', 'config_snapshot', 'rosbag', 'figures', 'videos'):
        (destination/folder).mkdir()
    shutil.copy2(source/'manifest.json', destination/'config_snapshot/frozen_input_manifest.json')
    route = manifest['routes'][0]
    original_metrics = {k: route[k] for k in ('duration_s', 'planned_delta_v',
                       'planned_graph_cost', 'planned_min_clearance', 'planned_peak_input')}
    n_hold = round(seconds/dt)
    views = list(csv.DictReader((source/'raw/viewpoints.csv').open()))
    action_by_candidate = {r['candidate_id']:int(r['action']) for r in views}
    trajectory = list(csv.DictReader((source/'raw/trajectory.csv').open()))
    (destination/'config_snapshot/terminal_dwell.yaml').write_text(
        yaml.safe_dump({'terminal_dwell_s':seconds, 'mean_motion':mean_motion}))
    dwell_effort = 0.0
    for filename in ('trajectory.csv', 'attitude.csv', 'control.csv', 'viewpoints.csv',
                     'coverage.csv', 'planner.csv', 'safety.csv', 'mission_events.csv'):
        rows = list(csv.DictReader((source/'raw'/filename).open()))
        fields = list(rows[0])
        output = []
        for i, row in enumerate(rows):
            row = dict(row)
            action = int(row.get('action') or action_by_candidate.get(
                row.get('candidate_id'), route['action_count']))
            end = i == len(rows)-1 or rows[i+1].get('action') != row.get('action')
            is_sample = filename in ('trajectory.csv', 'attitude.csv', 'control.csv')
            row['time'] = float(row['time']) + seconds * (action-1 if is_sample else action)
            output.append(row)
            if not is_sample or not end:
                continue
            # Endpoints have zero terminal velocity in the archived CW transfers.
            terminal = next(r for r in reversed(trajectory) if int(r['action']) == action)
            position = [float(terminal[k]) for k in ('rx', 'ry', 'rz')]
            if max(abs(float(terminal[k])) for k in ('vx', 'vy', 'vz')) > 1e-8:
                raise ValueError('A stationary dwell requires a zero-velocity transfer endpoint')
            hold_control = [-3*mean_motion**2*position[0], 0.0, mean_motion**2*position[2]]
            if filename == 'trajectory.csv':
                dwell_effort += seconds * math.sqrt(sum(a*a for a in hold_control))
            for j in range(1, n_hold+1):
                hold = dict(row, time=float(row['time'])+dt*j, sample=int(row['sample'])+j)
                if filename in ('trajectory.csv', 'control.csv'):
                    hold.update(zip(('ax', 'ay', 'az'), hold_control))
                if filename == 'trajectory.csv':
                    hold.update(vx=0.0, vy=0.0, vz=0.0)
                output.append(hold)
        with (destination/'raw'/filename).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(output)
    route.update(duration_s=route['duration_s']+seconds*route['action_count'],
                 planned_delta_v=route['planned_delta_v']+dwell_effort,
                 metrics_archived=False, frozen_transfer_metrics=original_metrics)
    manifest['execution_schedule'] = dict(
        kind='frozen_transfers_with_uniform_terminal_dwell', terminal_dwell_s=seconds,
        observation_timing='after each fixed dwell', mean_motion=mean_motion,
        source_manifest_sha256=sha(source/'manifest.json'), source_bundle=str(source.resolve()),
        stationary_hold_delta_v=dwell_effort,
        graph_cost_basis='unchanged archived transfers only; excludes settling time and feedback',
        selection='Post-hoc execution adaptation after frozen route tracking failure; offline study unchanged',
    )
    manifest['output_files_sha256'] = {f.name:sha(f) for f in sorted((destination/'raw').glob('*.csv'))}
    (destination/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (destination/'summary.json').write_text(json.dumps(dict(
        execution_performed=False, result_kind='derived_ros_execution_inputs_with_terminal_dwell',
        manifest_sha256=sha(destination/'manifest.json'), routes=manifest['routes'],
        execution_schedule=manifest['execution_schedule']), indent=2)+'\n')
    (destination/'summary.md').write_text(
        f'# Derived execution inputs\n\nUniform {seconds:g}-s stationary terminal dwell after each '
        'unchanged archived transfer. Observations evaluated after dwell. This is not execution evidence.\n')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--config', type=Path,
                        default=Path(__file__).parent/'config/required_target_settling.yaml')
    args = parser.parse_args()
    values = yaml.safe_load(args.config.read_text())
    print(add_dwell(args.source, args.destination,
                    float(values['terminal_dwell_s']), float(values['mean_motion'])))
