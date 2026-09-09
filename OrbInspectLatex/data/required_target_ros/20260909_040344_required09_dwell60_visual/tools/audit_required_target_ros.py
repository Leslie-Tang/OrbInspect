#!/usr/bin/env python3
"""Audit accepted target identities and measured control effort in a ROS bag.

Run after ros_evidence_audit. The exit status is nonzero for a rejected mission;
the audit and per-event evidence are still written for unsuccessful attempts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    """Hash a source without loading a large bag into memory."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def integrate_safe_control(samples: list[tuple[float, float]], end: float) -> float:
    """Integrate held acceleration norms from the first command to an end time.

    Each command applies until the next stamped command. The recording must
    bracket the requested end time; no extrapolation beyond the bag is allowed.
    """
    if len(samples) < 2 or not samples[0][0] <= end <= samples[-1][0]:
        raise ValueError('safe-control timestamps must bracket mission completion')
    if any(not math.isfinite(x) for sample in samples for x in sample):
        raise ValueError('safe-control samples must be finite')
    if any(norm < 0 for _, norm in samples):
        raise ValueError('acceleration norms must be nonnegative')
    if any(b[0] <= a[0] for a, b in zip(samples, samples[1:])):
        raise ValueError('safe-control stamps must be strictly increasing')
    return sum(norm * max(0.0, min(next_time, end) - time)
               for (time, norm), (next_time, _) in zip(samples, samples[1:]))


def audit_target_events(events: list[dict], views: list[dict], mission: dict) -> dict:
    """Reconstruct accepted unions independently of planned cumulative coverage."""
    weights = mission['target_weights']
    required = set(mission['required_target_ids'])
    accepted: set[str] = set()
    if len(events) != len(views):
        raise ValueError('recorded observation count differs from the frozen route')
    rows, checks = [], []
    for sequence, (event, view) in enumerate(zip(events, views, strict=True), 1):
        visible = set(filter(None, view['visible_target_ids'].split(';')))
        if visible - weights.keys():
            raise ValueError('view references an unknown target')
        credited = event['event'] == 'observation_credited'
        if credited:
            accepted |= visible
        coverage = sum(weights[key] for key in sorted(accepted)) / sum(weights.values())
        consistent = (
            event['current_waypoint_id'] == view['candidate_id']
            and event['current_waypoint_index'] == sequence
            and bool(event['credited']) == credited
            and set(event['credited_target_ids']) == accepted
            and event['required_covered_count'] == len(accepted & required)
            and event['required_target_count'] == len(required)
            and event['credited_target_count'] == len(accepted)
            and event['total_target_count'] == len(weights)
            and math.isclose(event['required_coverage_ratio'],
                             len(accepted & required) / len(required), abs_tol=1e-12)
            and bool(event['required_targets_complete']) == (not required - accepted)
            and bool(event['mission_goal_reached']) == (not required - accepted)
            and event['mission_sha256'] == mission['mission_sha256']
            and event['goal_mode'] == 'required'
            and set(event['missing_required_target_ids']) == required - accepted
            and math.isclose(event['coverage_ratio'], coverage, abs_tol=1e-12)
        )
        checks.append(consistent)
        rows.append({
            **event, 'sequence': sequence, 'audit_consistent': consistent,
            'visible_target_ids': sorted(visible),
            'reconstructed_accepted_target_ids': sorted(accepted),
            'reconstructed_required_count': len(accepted & required),
            'reconstructed_background_coverage': coverage,
        })
    return {
        'event_accounting_passed': all(checks), 'events': rows,
        'accepted_target_ids': sorted(accepted),
        'required_target_count': len(required),
        'accepted_required_count': len(accepted & required),
        'missing_required_target_ids': sorted(required - accepted),
        'accepted_observations': sum(bool(row['credited']) for row in rows),
        'rejected_observations': sum(not bool(row['credited']) for row in rows),
    }


def read_bag(path: Path, topics: tuple[str, ...]):
    """Yield selected deserialized messages using the installed Jazzy reader."""
    from rclpy.serialization import deserialize_message
    import rosbag2_py
    from rosidl_runtime_py.utilities import get_message

    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(path), storage_id='mcap'),
                rosbag2_py.ConverterOptions('', ''))
    types = {item.name: get_message(item.type)
             for item in reader.get_all_topics_and_types() if item.name in topics}
    if set(topics) - types.keys():
        raise ValueError(f'missing bag topics: {set(topics) - types.keys()}')
    reader.set_filter(rosbag2_py.StorageFilter(topics=list(topics)))
    while reader.has_next():
        topic, serialized, stamp = reader.read_next()
        yield topic, deserialize_message(serialized, types[topic]), stamp * 1e-9


def audit_run(run: Path) -> dict:
    """Write a reproducible audit even when required-target execution failed."""
    run = run.resolve()
    manifest_path = run / 'config_snapshot/input_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    run_manifest = json.loads((run / 'config_snapshot/run_manifest.json').read_text())
    if float(run_manifest.get('time_scale', 1.0)) != 1.0:
        raise ValueError('Receipt-based effort audit requires an unaccelerated wall-clock run')
    route, = [item for item in manifest['routes']
              if item['scenario_id'] == run_manifest['scenario_id']
              and item['method'] == run_manifest['method']]
    mission = route['mission']
    if mission['goal_mode'] != 'required':
        raise ValueError('this audit requires an explicit required-target mission')
    bundled = run / 'config_snapshot/replay_inputs'
    inputs = bundled if bundled.exists() else Path(run_manifest['input_bundle'])
    input_hashes_passed = all(
        sha256(inputs / 'raw' / name) == digest
        for name, digest in manifest['output_files_sha256'].items())
    with (inputs / 'raw/viewpoints.csv').open() as stream:
        views = [row for row in csv.DictReader(stream)
                 if row['scenario_id'] == route['scenario_id'] and row['method'] == route['method']]
    bag = run / 'rosbag/orbinspect_run'
    status, mission_events, controls, safety = [], [], [], []
    topics = ('/verification/status', '/mission/event',
              '/chaser/safe_control_command', '/chaser/safety_status')
    for topic, message, receipt in read_bag(bag, topics):
        if topic == '/chaser/safe_control_command':
            stamp = message.header.stamp.sec + message.header.stamp.nanosec * 1e-9
            a = message.accel.linear
            controls.append((stamp, math.sqrt(a.x**2 + a.y**2 + a.z**2)))
        else:
            payload = json.loads(message.data)
            payload['bag_receipt_time_s'] = receipt
            if topic == '/verification/status':
                status.append(payload)
            elif topic == '/mission/event':
                mission_events.append(payload)
            else:
                safety.append(payload)
    observed = [event for event in status if event['event'].startswith('observation_')]
    result = audit_target_events(observed, views, mission)
    terminal, = [event for event in status
                 if event['event'] in ('mission_complete', 'mission_failed')]
    source_events = [{k: v for k, v in event.items() if k != 'bag_receipt_time_s'}
                     for event in status]
    independent_events = [{k: v for k, v in event.items() if k != 'bag_receipt_time_s'}
                          for event in mission_events]
    for name, records in (('verification_events.json', status),
                          ('mission_event_messages.json', mission_events)):
        (run / 'raw' / name).write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')
    with (run / 'raw/safe_control_integral_samples.csv').open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(('ros_header_time_s', 'safe_acceleration_norm_mps2'))
        writer.writerows(controls)
    mesh = json.loads((run / 'mesh_execution_audit.json').read_text())
    summary = json.loads((run / 'summary.json').read_text())
    end = terminal['bag_receipt_time_s']
    start_estimates = [event['bag_receipt_time_s'] - event['time'] for event in status]
    start = min(start_estimates)
    for row in result['events']:
        index = row['sequence'] - 1
        action_start = start + (float(views[index-1]['time']) if index else 0.0)
        action_end = start + float(views[index]['time'])
        selected = [sample for sample in safety
                    if action_start <= sample['time'] < action_end]
        row['filter_intervention_samples'] = sum(bool(x['filter_active']) for x in selected)
        row['filter_reasons'] = sorted({x['filter_reason'] for x in selected if x['filter_active']})
        row['filter_primitives'] = sorted({x['nearest_primitive'] for x in selected if x['filter_active']})
    gates = {
        'closed_loop_execution': run_manifest['publish_mode'] == 'closed_loop',
        'frozen_input_hashes': (input_hashes_passed and
                                sha256(manifest_path) == run_manifest['input_manifest_sha256']),
        'event_accounting': result['event_accounting_passed'],
        'independent_event_topics_agree': source_events == independent_events,
        'summary_terminal_event_agrees': summary['verification'] == source_events[-1],
        'all_required_targets_accepted': result['accepted_required_count'] == len(mission['required_target_ids']),
        'all_observations_accepted': result['rejected_observations'] == 0,
        'mission_success': bool(terminal['success']),
        'full_mesh_execution_audit': bool(mesh['passed']),
    }
    result.update({
        'schema_version': 'orbinspect-required-target-ros-audit/v1',
        'scenario_id': route['scenario_id'], 'method': route['method'],
        'mission_sha256': mission['mission_sha256'], 'terminal': terminal,
        'gates': gates, 'passed': all(gates.values()),
        'planned_delta_v_mps': route['planned_delta_v'],
        'executed_delta_v_until_terminal_mps': integrate_safe_control(controls, end),
        'control_integral_definition': 'Zero-order hold of safe-command norms, from first stamped command to receipt of the final verification event; recording brackets the integration endpoint.',
        'logged_whole_run_delta_v_mps': summary['cumulative_delta_v'],
        'mission_epoch_receipt_spread_s': max(start_estimates) - min(start_estimates),
        'maximum_safe_control_stamp_gap_s': max(b[0] - a[0] for a, b in zip(controls, controls[1:])),
        'control_message_count': len(controls),
        'filter_intervention_samples': sum(bool(x['filter_active']) for x in safety),
        'physical_mesh_gates': {key: value for key, value in mesh['gates'].items()
                                if key not in ('terminal_verification',
                                               'reference_stream_completion')},
        'source_sha256': {
            str(path.relative_to(run)): sha256(path)
            for path in [manifest_path, run / 'config_snapshot/run_manifest.json',
                         run / 'mesh_execution_audit.json', run / 'summary.json',
                         *sorted((run / 'raw').glob('*')),
                         *sorted(bag.glob('*'))] if path.is_file()
        },
        'audit_script_sha256': sha256(Path(__file__)),
    })
    output = run / 'required_target_execution_audit.json'
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('events', 'source_sha256')}, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if audit_run(args.run_dir)['passed'] else 1)
