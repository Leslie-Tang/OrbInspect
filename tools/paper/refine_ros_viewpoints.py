"""Materialize explicitly declared viewpoint refinements for a supplemental ROS case.

All transfer states, controls and visibility masks are recomputed. Target weights,
required identities, geometry and camera predicates remain those of the source.
This creates execution inputs, not held-out planning or ROS execution evidence.
"""
from __future__ import annotations
import argparse
import csv
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
import yaml
from add_ros_terminal_dwell import add_dwell
from orbinspect_guidance.offline_planning_experiment import ExperimentConfig, OfflinePlanningExperiment
from orbinspect_guidance.observation_credit import ObservationMission, coverage_metrics


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source: Path, destination: Path, config: Path) -> Path:
    """Recompute the entire selected route with named position/aim replacements."""
    if destination.exists():
        raise FileExistsError(destination)
    values = yaml.safe_load(config.read_text())
    manifest = json.loads((source/'manifest.json').read_text())
    for name, digest in manifest['output_files_sha256'].items():
        if sha(source/'raw'/name) != digest:
            raise ValueError(f'Source hash mismatch: {name}')
    route, = manifest['routes']
    params = json.loads((source/'config_snapshot/base_experiment_config.json').read_text())
    params['output_root'] = Path(params['output_root'])
    experiment = OfflinePlanningExperiment(ExperimentConfig(**params))
    candidates = {c.candidate_id: c for c in experiment.candidates}
    targets = {t.target_id: t for t in experiment.targets}
    mission = ObservationMission(**{**route['mission'],
        'required_target_ids': frozenset(route['mission']['required_target_ids'])})
    replacements = {r['original_id']: r for r in values['refinements']}
    old = {name: list(csv.DictReader((source/'raw'/name).open()))
           for name in manifest['output_files_sha256']}
    output = {name: [] for name in old}
    state = tuple(route['initial_state'])
    offset = cost = delta_v = peak = 0.0
    minimum = float('inf')
    covered = set()
    provenance = []
    nodes = []
    for action, original_id in enumerate(route['route_node_ids'], 1):
        candidate = candidates[original_id]
        change = replacements.get(original_id)
        aim = targets[candidate.source_target_id].position
        if change:
            candidate = replace(candidate, candidate_id=change['candidate_id'],
                                position=tuple(change['position']))
            aim = tuple(change['aim_position'])
        visible_all = {t.target_id for t in experiment.targets
                       if experiment.base_planner._target_visible(candidate.position, t, aim)}
        visible = visible_all & set(mission.target_weights)
        covered |= visible
        metrics = coverage_metrics(frozenset(covered), mission)
        transfer = experiment._estimate_transfer_from_state(state, candidate)
        if not transfer.feasible:
            raise ValueError(f'Infeasible transfer to {candidate.candidate_id}: {transfer}')
        stage_cost = experiment._dynamic_transfer_cost(transfer) + float(values['action_cost'])
        cost += stage_cost
        delta_v += transfer.delta_v
        peak = max(peak, transfer.peak_requested_input)
        minimum = min(minimum, transfer.min_clearance)
        end_time = offset + experiment.config.transfer_duration
        node = candidate.candidate_id
        nodes.append(node)
        common = {'scenario_id': route['scenario_id'], 'method': route['method'],
                  'split': route['split'], 'scenario_seed': route['scenario_seed'],
                  'action': action, 'candidate_id': node}
        for sample, (local_time, sample_state, control) in enumerate(transfer.trajectory):
            sample_common = dict(common, sample=sample, time=offset+local_time)
            boresight = np.array(aim)-np.array(sample_state[:3])
            boresight /= np.linalg.norm(boresight)
            output['trajectory.csv'].append(dict(sample_common,
                **dict(zip(('rx','ry','rz','vx','vy','vz'),sample_state)),
                **dict(zip(('ax','ay','az'),control))))
            output['attitude.csv'].append(dict(sample_common,
                **dict(zip(('boresight_x','boresight_y','boresight_z'),boresight))))
            output['control.csv'].append({**{k: sample_common[k] for k in
                ('scenario_id','method','action','candidate_id','sample','time')},
                **dict(zip(('ax','ay','az'),control)), 'record_basis':'planned_command_not_execution'})
        boresight = np.array(aim)-np.array(transfer.next_state[:3])
        boresight /= np.linalg.norm(boresight)
        view = dict(old['viewpoints.csv'][action-1], **common, time=end_time,
            **dict(zip(('viewpoint_x','viewpoint_y','viewpoint_z'),candidate.position)),
            **dict(zip(('boresight_x','boresight_y','boresight_z'),boresight)),
            weighted_coverage=metrics['coverage_ratio'], covered_target_count=len(covered),
            required_covered_count=metrics['required_covered_count'],
            required_coverage=metrics['required_coverage_ratio'],
            covered_target_ids=';'.join(sorted(covered)), visible_target_ids=';'.join(sorted(visible)))
        output['viewpoints.csv'].append(view)
        output['safety.csv'].append(dict(old['safety.csv'][action-1], time=end_time,
            candidate_id=node, feasible=transfer.feasible, min_clearance=transfer.min_clearance,
            peak_input=transfer.peak_requested_input, max_speed=transfer.max_speed,
            terminal_error=transfer.terminal_error,
            record_basis='recomputed_transfer_not_execution'))
        output['planner.csv'].append(dict(old['planner.csv'][action-1], time=end_time,
            candidate_id=node, stage_cost=stage_cost, cumulative_cost=cost,
            cumulative_delta_v=delta_v, coverage_ratio=metrics['coverage_ratio'],
            required_coverage_ratio=metrics['required_coverage_ratio'],
            required_covered_count=metrics['required_covered_count'],
            missing_required_target_ids=';'.join(metrics['missing_required_target_ids']),
            record_basis='recomputed_transfer_and_visibility_not_execution'))
        output['coverage.csv'].append(dict(old['coverage.csv'][action-1], time=end_time,
            candidate_id=node, coverage_ratio=metrics['coverage_ratio'], inspected_targets=len(covered),
            required_covered_count=metrics['required_covered_count'],
            required_coverage_ratio=metrics['required_coverage_ratio'],
            covered_target_ids=';'.join(sorted(covered))))
        provenance.append(dict(action=action, original_id=original_id, candidate_id=node,
            position=candidate.position, aim_position=aim, visible_target_ids=sorted(visible),
            visible_outside_fixed_universe=sorted(visible_all-visible),
            original_visible_target_ids=sorted(experiment.visibility.visible_targets_by_candidate[original_id]),
            min_clearance=transfer.min_clearance, peak_input=transfer.peak_requested_input))
        state = transfer.next_state
        offset = end_time
    if len(nodes) != values['observation_count'] or not metrics['mission_goal_reached']:
        raise ValueError(f'Refined plan fails frozen mission: {metrics}')
    output['mission_events.csv'] = [dict(old['mission_events.csv'][0], time=offset,
        planned_success=True, coverage_ratio=metrics['coverage_ratio'],
        required_coverage_ratio=metrics['required_coverage_ratio'])]
    for folder in ('raw','config_snapshot','rosbag','figures','videos'):
        (destination/folder).mkdir(parents=True)
    for name, rows in output.items():
        with (destination/'raw'/name).open('w',newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(old[name][0]))
            writer.writeheader()
            writer.writerows(rows)
    for path in (source/'config_snapshot').iterdir():
        if path.is_file(): shutil.copy2(path,destination/'config_snapshot'/path.name)
    shutil.copy2(config,destination/'config_snapshot/viewpoint_refinements.yaml')
    shutil.copy2(Path(__file__),destination/'config_snapshot/refine_ros_viewpoints.py')
    shutil.copy2(source/'manifest.json',destination/'config_snapshot/parent_input_manifest.json')
    original_metrics = dict(route)
    route.update(metrics_archived=False, route_node_ids=nodes,
        planned_coverage=metrics['coverage_ratio'], planned_graph_cost=cost,
        planned_delta_v=delta_v, planned_min_clearance=minimum, planned_peak_input=peak,
        duration_s=offset)
    manifest['viewpoint_refinement'] = dict(selection=values['selection_reason'],
        source_bundle=str(source.resolve()), source_manifest_sha256=sha(source/'manifest.json'),
        fixed_target_universe='unchanged 41 parent target IDs and weights',
        original_route=original_metrics, observations=provenance,
        metrics_basis='all transfers and visibility recomputed; not archived graph metrics')
    manifest['output_files_sha256'] = {name: sha(destination/'raw'/name) for name in output}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (destination/'summary.json').write_text(json.dumps(dict(execution_performed=False,
        result_kind='supplemental_refined_viewpoint_execution_inputs',routes=[route],
        refinement=manifest['viewpoint_refinement']),indent=2)+'\n')
    (destination/'summary.md').write_text('# Supplemental refined ROS inputs\n\n'
        'Two viewpoint positions/aims adapted after the synchronous tracking diagnostic. '
        'All transfers and visibility recomputed with unchanged physical gates, target '
        'identities and weights. This is not a held-out or executed result.\n')
    return add_dwell(destination, destination.with_name(destination.name+'_dwell60'),
        float(values['terminal_dwell_s']), float(manifest['mean_motion']),
        selection_reason=values['selection_reason'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('destination',type=Path)
    parser.add_argument('--config',required=True,type=Path)
    args = parser.parse_args()
    print(prepare(args.source,args.destination,args.config))
