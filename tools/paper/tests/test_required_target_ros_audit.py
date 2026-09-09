"""Checks for control integration and identity-based execution evidence."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_required_target_ros import audit_target_events, integrate_safe_control


def test_control_integral_uses_stamps_and_clips_terminal_interval():
    assert integrate_safe_control([(0, 1), (2, 3), (5, 9)], 4) == 8
    with pytest.raises(ValueError, match='bracket'):
        integrate_safe_control([(0, 1), (2, 3)], 4)
    with pytest.raises(ValueError, match='strictly'):
        integrate_safe_control([(0, 1), (0, 3), (2, 4)], 1)


def test_rejected_and_repeated_views_do_not_add_target_credit():
    mission = {'target_weights': {'a': 1, 'b': 2},
               'required_target_ids': ['a', 'b'], 'mission_sha256': 'fixed'}
    views = [{'candidate_id': f'view{i}', 'visible_target_ids': visible}
             for i, visible in enumerate(['a', 'a;b', 'a'], 1)]
    events = []
    for i, credited in enumerate([True, False, True], 1):
        events.append({'event': 'observation_credited' if credited else 'observation_rejected',
                       'credited': credited, 'credited_target_ids': ['a'],
                       'current_waypoint_id': f'view{i}', 'current_waypoint_index': i,
                       'goal_mode': 'required', 'required_covered_count': 1,
                       'required_target_count': 2, 'missing_required_target_ids': ['b'],
                       'credited_target_count': 1, 'total_target_count': 2,
                       'required_coverage_ratio': 0.5, 'required_targets_complete': False,
                       'mission_goal_reached': False,
                       'coverage_ratio': 1 / 3, 'mission_sha256': 'fixed'})
    result = audit_target_events(events, views, mission)
    assert result['event_accounting_passed']
    assert result['accepted_required_count'] == 1
    assert result['missing_required_target_ids'] == ['b']
    events[1]['credited_target_ids'] = ['a', 'b']
    assert not audit_target_events(events, views, mission)['event_accounting_passed']
    with pytest.raises(ValueError, match='count'):
        audit_target_events(events[:-1], views, mission)


def test_hybrid_completion_requires_background_goal_after_required_completion():
    mission = {'target_weights': {'a': 1, 'b': 4}, 'required_target_ids': ['a'],
               'mission_sha256': 'hybrid', 'goal_mode': 'hybrid', 'goal_coverage': 0.8}
    views = [{'candidate_id': f'view{i}', 'visible_target_ids': visible}
             for i, visible in enumerate(['a', 'b'], 1)]
    events = []
    for i, covered in enumerate([['a'], ['a', 'b']], 1):
        events.append({'event': 'observation_credited', 'credited': True,
                       'credited_target_ids': covered, 'current_waypoint_id': f'view{i}',
                       'current_waypoint_index': i, 'goal_mode': 'hybrid',
                       'required_covered_count': 1, 'required_target_count': 1,
                       'missing_required_target_ids': [], 'credited_target_count': len(covered),
                       'total_target_count': 2, 'required_coverage_ratio': 1.0,
                       'required_targets_complete': True, 'mission_goal_reached': i == 2,
                       'coverage_ratio': 0.2 if i == 1 else 1.0,
                       'mission_sha256': 'hybrid'})
    result = audit_target_events(events, views, mission)
    assert result['event_accounting_passed']
    assert result['accepted_background_coverage'] == 1.0
    events[0]['mission_goal_reached'] = True
    assert not audit_target_events(events, views, mission)['event_accounting_passed']
    with pytest.raises(ValueError, match='positive background'):
        audit_target_events(events, views, {**mission, 'goal_coverage': 0.0})
