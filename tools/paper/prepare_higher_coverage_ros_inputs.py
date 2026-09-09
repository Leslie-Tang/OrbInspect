"""Freeze a searched hybrid ADP route and export explicit ROS execution inputs.

The exporter-compatible source is a new supplemental plan snapshot. It is not
a new held-out result and never overwrites the confirmation study.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import yaml

from add_ros_terminal_dwell import add_dwell
from orbinspect_guidance.offline_adp_superiority_study import load_archived_graph, _problem_for_scenario
from orbinspect_guidance.ros_route_exporter import (
    _audit_archived_route, _load_scenarios, _mission_for_scenario, _plan_metrics, export_routes,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source: Path, search: Path, output_root: Path, run_id: str, config: Path) -> dict:
    """Validate the selected plan, retain its provenance and materialize transfers."""
    values = yaml.safe_load(config.read_text())
    search_report = json.loads((search / 'summary.json').read_text())
    for name, expected in search_report['source_hashes'].items():
        if sha(source / 'raw' / name) != expected:
            raise ValueError(f'Frozen source changed: {name}')
    searched = json.loads((search / 'hybrid_search.json').read_text())
    selected, = [r for r in searched['results'] if r['success']
                and r['goal'] == values['background_goal']
                and r['observations'] == values['observation_count']]
    payload = next(s for s in json.loads((source / 'raw/scenarios.json').read_text())
                   if s['scenario_id'] == values['source_scenario'])
    graph = load_archived_graph(source / 'raw/hcw_graph.json')
    scenario = next(s for s in _load_scenarios(source / 'raw/scenarios.json')
                    if s.scenario_id == values['source_scenario'])
    derived = dict(payload, scenario_id=values['derived_scenario'], split='supplemental',
                   goal_mode=values['goal_mode'], goal_coverage=values['background_goal'],
                   parent_scenario_id=values['source_scenario'])
    mission = _mission_for_scenario(graph, derived)
    problem = replace(_problem_for_scenario(graph, scenario),
                      goal_mode=values['goal_mode'], goal_coverage=values['background_goal'],
                      required_target_mask=int(payload['required_target_mask']))
    plan = SimpleNamespace(node_ids=tuple(selected['route']), success=True,
                           coverage_ratio=selected['coverage'], total_cost=selected['graph_cost'])
    row = dict(_plan_metrics(plan, problem), scenario_id=values['derived_scenario'],
               method='adaptive_rollout_adp', route_node_ids=';'.join(selected['route']),
               covered_target_mask=selected['covered_target_mask'], required_coverage=1.0,
               result_origin='supplemental_plan_selected_before_ros_execution')
    summary = json.loads((source / 'summary.json').read_text())
    _audit_archived_route(problem, mission, row,
                          action_cost=summary['superiority_config']['action_cost'],
                          target_ids=graph.target_ids)
    frozen = output_root / f'{run_id}_plan'
    if frozen.exists():
        raise FileExistsError(frozen)
    (frozen / 'raw').mkdir(parents=True)
    (frozen / 'config_snapshot').mkdir()
    shutil.copy2(source / 'raw/hcw_graph.json', frozen / 'raw/hcw_graph.json')
    shutil.copy2(source / 'config_snapshot/base_experiment_config.json',
                 frozen / 'config_snapshot/base_experiment_config.json')
    shutil.copy2(config, frozen / 'config_snapshot/selection.yaml')
    shutil.copy2(search / 'hybrid_search.json', frozen / 'config_snapshot/prior_search.json')
    shutil.copy2(Path(__file__), frozen / 'config_snapshot/prepare_inputs.py')
    (frozen / 'raw/scenarios.json').write_text(json.dumps([derived], indent=2) + '\n')
    # This filename is the stable exporter interface, not a claim of held-out testing.
    with (frozen / 'raw/heldout_results.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    summary['superiority_config']['goal_coverage'] = values['background_goal']
    (frozen / 'summary.json').write_text(json.dumps({
        'execution_performed': False, 'result_kind': 'supplemental_selected_hybrid_plan',
        'superiority_config': summary['superiority_config'],
        'parent_scenario': values['source_scenario'], 'selection': values,
        'selected_plan': selected, 'parent_source_hashes': search_report['source_hashes'],
        'search_summary_sha256': sha(search / 'summary.json'),
    }, indent=2) + '\n')
    (frozen / 'summary.md').write_text(
        '# Supplemental hybrid plan\n\nSelected 12-view ADP plan with unchanged parent '
        'targets, weights, available nodes and graph. The background goal is now 95%. '
        'This is not a held-out result or ROS execution.\n')
    transfers = export_routes(frozen, output_root,
        Path('src/orbinspect_guidance/config/adp_future_study.yaml'),
        scenario_ids=(values['derived_scenario'],), methods=('adaptive_rollout_adp',),
        run_id=f'{run_id}_transfers')
    dwell = add_dwell(transfers, output_root / f'{run_id}_dwell60_inputs',
                     float(values['terminal_dwell_s']), float(values['mean_motion']),
                     selection_reason=values['selection_reason'])
    result = {'plan_snapshot': str(frozen.resolve()), 'transfer_inputs': str(transfers.resolve()),
              'execution_inputs': str(dwell.resolve()), 'scenario_id': values['derived_scenario']}
    (frozen / 'exported_paths.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('OrbInspectLatex/data/confirmation'))
    parser.add_argument('--search', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, default=Path('data/results'))
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--config', type=Path, default=Path(__file__).parent / 'config/higher_coverage_12.yaml')
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.search, args.output_root, args.run_id, args.config), indent=2))
