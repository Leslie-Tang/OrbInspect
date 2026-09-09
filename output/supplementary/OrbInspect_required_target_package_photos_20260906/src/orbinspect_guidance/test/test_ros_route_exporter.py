"""Tests for identity-preserving frozen-route metadata and route audits."""

from types import SimpleNamespace

from orbinspect_guidance.advanced_safe_planner import SafeGraphEdge
from orbinspect_guidance.advanced_safe_planner import SafeGraphNode
from orbinspect_guidance.advanced_safe_planner import SafeGraphProblem
from orbinspect_guidance.ros_route_exporter import _audit_archived_route
from orbinspect_guidance.ros_route_exporter import _mission_for_scenario
import pytest


def _mission():
    return _mission_for_scenario(SimpleNamespace(target_ids=('background', 'key')), {
        'target_weights': (9.0, 1.0), 'goal_mode': 'required', 'goal_coverage': 0.0,
        'required_target_ids': ['key'], 'required_target_mask': 0b10,
    })


def test_mission_export_keeps_original_universe_weights_and_required_ids() -> None:
    mission = _mission()
    assert tuple(mission.target_weights) == ('background', 'key')
    assert mission.metadata()['target_weights'] == {'background': 9.0, 'key': 1.0}
    assert mission.metadata()['required_target_ids'] == ['key']
    assert mission.goal_mode == 'required'
    assert len(mission.mission_sha256) == 64


def test_mission_export_rejects_disagreeing_mask_and_ids() -> None:
    with pytest.raises(ValueError, match='disagree'):
        _mission_for_scenario(SimpleNamespace(target_ids=('a', 'b')), {
            'target_weights': (1.0, 1.0), 'goal_mode': 'required', 'goal_coverage': 0.0,
            'required_target_ids': ['a'], 'required_target_mask': 2,
        })


def _problem():
    def edge(source_id, target_id):
        return SafeGraphEdge(
            source_id, target_id, stage_cost=1.0, feasible=True,
            min_clearance=2.0, peak_input=0.01, input_limit=0.1, delta_v=0.3,
        )
    return SafeGraphProblem(
        nodes=(SafeGraphNode('transit', 0), SafeGraphNode('observe', 2)),
        target_weights=(9.0, 1.0), edge_evaluator=edge, goal_coverage=0.0,
        max_steps=2, required_target_mask=2, goal_mode='required',
    )


def _archived():
    return {
        'route_node_ids': 'transit;observe', 'success': True, 'selected_count': 2,
        'coverage': 0.1, 'graph_cost': 2.1, 'total_delta_v': 0.6,
        'min_clearance': 2.0, 'peak_input': 0.01, 'covered_target_mask': '0x2',
        'required_coverage': 1.0,
    }


def test_archived_route_audit_preserves_necessary_zero_gain_transit() -> None:
    plan = _audit_archived_route(
        _problem(), _mission(), _archived(), action_cost=0.05, target_ids=('background', 'key'),
    )
    assert plan.node_ids == ('transit', 'observe')
    assert plan.success
    assert plan.coverage_ratio == 0.1


def test_archived_route_audit_rejects_changed_cost_or_mask() -> None:
    row = _archived()
    row['graph_cost'] = 1.0
    with pytest.raises(RuntimeError, match='graph_cost'):
        _audit_archived_route(_problem(), _mission(), row, action_cost=0.05, target_ids=('background', 'key'))
    row = _archived()
    row['covered_target_mask'] = '0x3'
    with pytest.raises(ValueError, match='credited mask'):
        _audit_archived_route(_problem(), _mission(), row, action_cost=0.05, target_ids=('background', 'key'))


def test_archived_route_audit_rejects_empty_and_repeated_routes() -> None:
    for route in ('', 'observe;observe'):
        with pytest.raises(ValueError):
            _audit_archived_route(
                _problem(), _mission(), {**_archived(), 'route_node_ids': route},
                action_cost=0.05, target_ids=('background', 'key'),
            )
