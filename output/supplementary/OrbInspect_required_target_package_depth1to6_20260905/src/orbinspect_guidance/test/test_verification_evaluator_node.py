"""Tests for closed-loop observation credit gates."""

import ast
import csv
import json
import math
from pathlib import Path
from types import SimpleNamespace

from orbinspect_guidance.observation_credit import ObservationMission
from orbinspect_guidance.observation_credit import credit_observation
from orbinspect_guidance.observation_credit import coverage_metrics
from orbinspect_guidance.observation_credit import load_observation_mission
import pytest


def _load_evaluator_definitions() -> dict:
    """Exercise the actual pure logic and node methods without requiring ROS."""
    source = Path(__file__).parents[1] / 'orbinspect_guidance/verification_evaluator_node.py'
    tree = ast.parse(source.read_text())
    definitions = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        and getattr(node, 'name', '') != 'main'
    ]
    module = ast.Module(body=[ast.ImportFrom(
        module='__future__', names=[ast.alias(name='annotations')], level=0,
    ), *definitions], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {
        'Node': object, 'math': math, 'csv': csv, 'json': json, 'Path': Path,
        'credit_observation': credit_observation, 'coverage_metrics': coverage_metrics,
        'String': lambda **values: SimpleNamespace(**values),
        'CoverageMap': lambda: SimpleNamespace(header=SimpleNamespace()),
    }
    exec(compile(module, str(source), 'exec'), namespace)
    return namespace


_DEFINITIONS = _load_evaluator_definitions()
evaluate_observation = _DEFINITIONS['evaluate_observation']


def test_credits_observation_at_declared_limits() -> None:
    """Accept tracking exactly on both predeclared tolerances."""
    result = evaluate_observation(
        executed=(0.5, 0.0, 0.0, 0.05, 0.0, 0.0),
        planned=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        position_tolerance=0.5,
        velocity_tolerance=0.05,
    )

    assert result['credited']
    assert result['position_error'] == 0.5
    assert result['terminal_speed'] == 0.05


def test_rejects_observation_for_position_error() -> None:
    """Reject a terminal state outside the position gate."""
    result = evaluate_observation(
        executed=(0.5001, 0.0, 0.0, 0.0, 0.0, 0.0),
        planned=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        position_tolerance=0.5,
        velocity_tolerance=0.05,
    )

    assert not result['credited']


def test_rejects_observation_for_terminal_speed() -> None:
    """Reject a terminal state outside the speed gate."""
    result = evaluate_observation(
        executed=(0.0, 0.0, 0.0, 0.0, 0.0501, 0.0),
        planned=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        position_tolerance=0.5,
        velocity_tolerance=0.05,
    )

    assert not result['credited']


def test_rejected_observation_cannot_be_imported_by_later_acceptance() -> None:
    """Replay the actual node ticks and verify published counts and identities."""
    class Stamp(float):
        def __sub__(self, other):
            return Stamp(float(self) - float(other))

        @property
        def nanoseconds(self):
            return float(self)

        def to_msg(self):
            return self

    node = _DEFINITIONS['VerificationEvaluatorNode'].__new__(
        _DEFINITIONS['VerificationEvaluatorNode']
    )
    node.mission = ObservationMission({'a': 3.0, 'b': 1.0}, frozenset({'a', 'b'}), 'required')
    node.covered_target_ids = frozenset()
    node.new_targets_seen = 0
    node.finished = False
    node.start_time = Stamp(0)
    node.get_clock = lambda: SimpleNamespace(now=lambda: Stamp(3.0e9))
    node.next_observation = 0
    node.coverage = 0.0
    node.credited_actions = 0
    node.failed_actions = 0
    node.position_tolerance = 0.5
    node.velocity_tolerance = 0.05
    node.max_sooas = 14
    node.frame_id = 'lvlh'
    messages = []
    coverage_messages = []
    node.event_pub = SimpleNamespace(publish=messages.append)
    node.status_pub = SimpleNamespace(publish=lambda _message: None)
    node.coverage_pub = SimpleNamespace(publish=coverage_messages.append)
    node.observations = tuple({
        'time': float(index), 'action': index + 1,
        'candidate_id': target, 'state': (0.0,) * 6,
        'visible_target_ids': frozenset({target}), 'visible_target_count': 1,
        'weighted_coverage': (0.75, 1.0)[index],
        'covered_targets': index + 1, 'total_targets': 2,
    } for index, target in enumerate(('a', 'b')))
    node.latest_state = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    node._tick()
    assert node.covered_target_ids == frozenset()
    assert coverage_messages[-1].inspected_targets == 0
    node.latest_state = (0.0,) * 6
    node._tick()
    result = json.loads(messages[-1].data)
    assert node.covered_target_ids == frozenset({'b'})
    assert node.coverage == 0.25
    assert coverage_messages[-1].inspected_targets == 1
    assert result['missing_required_target_ids'] == ['a']
    assert not result['success']


def test_required_completion_uses_fixed_ids_not_background_threshold() -> None:
    mission = ObservationMission({'key': 1.0, 'background': 9.0}, frozenset({'key'}), 'required')
    assert coverage_metrics(frozenset({'key'}), mission)['mission_goal_reached']
    assert not coverage_metrics(frozenset({'background'}), mission)['mission_goal_reached']
    hybrid = ObservationMission(mission.target_weights, mission.required_target_ids, 'hybrid')
    assert not coverage_metrics(frozenset({'key'}), hybrid)['mission_goal_reached']
    assert coverage_metrics(frozenset(mission.target_weights), hybrid)['mission_goal_reached']
    legacy_mask = ObservationMission(mission.target_weights, mission.required_target_ids, 'coverage')
    assert not coverage_metrics(frozenset({'background'}), legacy_mask)['mission_goal_reached']


def test_overlapping_observations_do_not_double_credit() -> None:
    mission = ObservationMission({'a': 1.0, 'b': 1.0, 'c': 2.0})
    covered, new = credit_observation(frozenset(), frozenset({'a', 'b'}), True, mission)
    assert new == 2
    covered, new = credit_observation(covered, frozenset({'b'}), True, mission)
    assert new == 0
    assert coverage_metrics(covered, mission)['coverage_ratio'] == 0.5


@pytest.mark.parametrize('required, mode', [(frozenset(), 'required'), (frozenset({'missing'}), 'hybrid')])
def test_invalid_required_target_specification_fails(required, mode) -> None:
    with pytest.raises(ValueError):
        ObservationMission({'a': 1.0}, required, mode)


def test_unknown_observation_target_fails() -> None:
    with pytest.raises(ValueError, match='fixed universe'):
        credit_observation(frozenset(), frozenset({'missing'}), True, ObservationMission({'a': 1.0}))


def test_self_contained_mission_round_trip(tmp_path: Path) -> None:
    mission = ObservationMission({'a': 2.0, 'b': 3.0}, frozenset({'b'}), 'required', 0.0, 'abc')
    (tmp_path / 'manifest.json').write_text(json.dumps({'routes': [{
        'scenario_id': 'fresh_000', 'method': 'adaptive_rollout_adp', 'mission': mission.metadata(),
    }]}))
    loaded = load_observation_mission(tmp_path, 'fresh_000', 'adaptive_rollout_adp')
    assert loaded.metadata() == mission.metadata()


def test_observation_loader_preserves_visible_identities(tmp_path: Path) -> None:
    raw = tmp_path / 'raw'
    raw.mkdir()
    (raw / 'trajectory.csv').write_text(
        'scenario_id,method,action,rx,ry,rz,vx,vy,vz\n'
        'test_000,adp,1,0,0,0,0,0,0\n'
    )
    (raw / 'viewpoints.csv').write_text(
        'scenario_id,method,action,candidate_id,time,weighted_coverage,'
        'covered_target_count,total_target_count,visible_target_ids\n'
        'test_000,adp,1,v1,90,0.2,2,10,a;b\n'
    )
    observations = _DEFINITIONS['_load_observations'](tmp_path, 'test_000', 'adp')
    assert observations[0]['visible_target_ids'] == frozenset({'a', 'b'})
