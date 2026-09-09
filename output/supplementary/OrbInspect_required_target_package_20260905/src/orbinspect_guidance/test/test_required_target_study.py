"""Protocol and denominator regression tests for the required-target benchmark."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import yaml

from orbinspect_guidance.offline_adp_superiority_study import ArchivedEdge, ArchivedGraph


REPO = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    'required_target_study', REPO / 'OrbInspectLatex/scripts/run_required_target_study.py',
)
STUDY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(STUDY)


def config() -> dict:
    return yaml.safe_load((REPO / 'src/orbinspect_guidance/config/required_target_study.yaml').read_text())


def test_geometry_requirements_are_nested_and_use_only_positions() -> None:
    positions = {f't{i:02d}': (float(i), float(i % 4), float(i % 3)) for i in range(18)}
    ids = tuple(positions)
    manifest = STUDY.select_profiles(ids, positions, [6, 9, 12])
    profiles = manifest['profiles']
    assert [p['required_target_count'] for p in profiles] == [6, 9, 12]
    assert set(profiles[0]['required_target_ids']) < set(profiles[1]['required_target_ids'])
    assert set(profiles[1]['required_target_ids']) < set(profiles[2]['required_target_ids'])
    assert not manifest['selection_uses_scenario_inventory']
    assert not manifest['selection_uses_route_outcomes']
    assert STUDY.select_profiles(ids, dict(reversed(list(positions.items()))), [6, 9, 12]) == manifest


def test_scenario_sampler_keeps_complete_node_dropout_and_fixed_requirements() -> None:
    values = config()
    values['test_dropout_range'] = [1.0, 1.0]
    graph = SimpleNamespace(node_ids=('a', 'b'), base_target_weights=(1.0,) * 6)
    profile = {'profile_id': 'required06', 'required_target_ids': ['t0', 't1'], 'required_target_mask': 3}
    sample = STUDY.scenario_payload(graph, values, profile, 'test', 0, 202609099999)
    assert sample['available_node_ids'] == []
    assert sample['required_target_mask'] == 3
    assert sample['required_target_ids'] == ['t0', 't1']


def test_coverage_success_does_not_receive_required_success_credit() -> None:
    graph = ArchivedGraph(
        node_ids=('a', 'b'), coverage_masks=(15, 16), static_priorities=(1.0, 1.0),
        target_ids=('t0', 't1', 't2', 't3', 't4'), base_target_weights=(1.0,) * 5,
        edges=tuple(ArchivedEdge(source, target, cost, True, 5.0, 0.01, 1.0, None, 0.1)
                    for source, target, cost in ((None, 'a', 1.0), (None, 'b', 10.0), ('a', 'b', 10.0), ('b', 'a', 1.0))),
    )
    sample = {'scenario_id': 'required01_test_000', 'profile_id': 'required01', 'split': 'test',
              'seed': 202609099998, 'available_node_ids': ['a', 'b'], 'target_weights': [1.0] * 5,
              'required_target_ids': ['t4'], 'required_target_mask': 16, 'max_steps': 2}
    row = STUDY.evaluate(graph, sample, config(), 'coverage_only80')
    assert row['native_goal_success']
    assert not row['success']
    assert row['coverage'] == 0.8
    assert row['required_coverage'] == 0.0
    assert row['missing_required_ids'] == 't4'
    assert row['required_visibility_available']
    assert row['penalized_cost'] == row['graph_cost'] + 1000.0
