"""Independent exhaustive checks for the required-route MILP formulation."""
from itertools import permutations
from types import SimpleNamespace
from unittest.mock import patch
import math
import random

import pytest

from orbinspect_guidance.advanced_safe_planner import SafeGraphEdge, SafeGraphNode, SafeGraphProblem
from orbinspect_guidance.required_route_milp import solve_required_route, validate_route


def problem(masks, edges, required=3, budget=5):
    nodes = tuple(SafeGraphNode(str(i), mask) for i, mask in enumerate(masks))
    records = {(source, target): SafeGraphEdge(source, target, cost, safe, 3.0,
                                               0.01, 0.06, None, cost/5)
               for source, target, cost, safe in edges}
    def edge(source, target):
        return records.get((source, target), SafeGraphEdge(source, target, 0, False, -1))
    return SafeGraphProblem(nodes, (1, 1, 1), edge, 0.0, budget,
                            required_target_mask=required, goal_mode='required')


def brute_force(task):
    best = math.inf
    for count in range(min(len(task.nodes), task.max_steps)+1):
        for route in permutations((n.node_id for n in task.nodes), count):
            try:
                metrics = validate_route(task, route)
            except ValueError:
                continue
            if metrics['success']:
                best = min(best, metrics['graph_cost'])
    return best


def test_zero_gain_connector_is_required_and_selected():
    task = problem([0, 1, 2], [(None, '0', 1, True), ('0', '1', 2, True),
                              ('1', '2', 3, True)], budget=3)
    result = solve_required_route(task)
    assert result.status == 'feasible' and result.optimal
    assert result.node_ids == ('0', '1', '2')
    assert result.graph_cost == pytest.approx(6.15)


def test_disconnected_cycle_cannot_supply_required_credit():
    task = problem([0, 1, 2], [(None, '0', 1, True), ('1', '2', 1, True),
                              ('2', '1', 1, True)])
    assert solve_required_route(task).status == 'infeasible'


def test_individually_reachable_targets_do_not_imply_a_complete_route():
    task = problem([1, 2], [(None, '0', 1, True), (None, '1', 1, True)])
    result = solve_required_route(task)
    assert result.status == 'infeasible' and result.reason == 'milp_infeasible'


def test_order_constraints_exclude_a_cheaper_disconnected_selected_cycle():
    task = problem([1, 2, 4], [(None, '0', 1, True), ('0', '1', 10, True),
                              ('1', '2', 0.1, True), ('2', '1', 0.1, True)], required=7)
    result = solve_required_route(task)
    assert result.node_ids == ('0', '1', '2')
    assert result.graph_cost == pytest.approx(11.25)


def test_time_limited_integer_witness_is_feasible_without_an_optimality_claim():
    from scipy.optimize import milp
    task = problem([1, 2], [(None, '0', 1, True), ('0', '1', 1, True)])
    def limited(*args, **kwargs):
        result = milp(*args, **kwargs)
        result.status = 1
        result.message = 'time limit with a feasible incumbent'
        return result
    with patch('scipy.optimize.milp', side_effect=limited):
        result = solve_required_route(task)
    assert result.status == 'feasible' and not result.optimal
    assert result.node_ids == ('0', '1')


def test_action_budget_can_make_visible_connected_task_infeasible():
    task = problem([0, 1, 2], [(None, '0', 1, True), ('0', '1', 1, True),
                              ('1', '2', 1, True)], budget=2)
    assert solve_required_route(task).status == 'infeasible'


def test_unsafe_shortcut_is_not_selected():
    task = problem([1, 2, 0], [(None, '0', 1, True), ('0', '1', 1, False),
                              ('0', '2', 4, True), ('2', '1', 2, True)])
    assert solve_required_route(task).node_ids == ('0', '2', '1')


def test_missing_view_is_a_proof_but_time_limit_is_not():
    missing = solve_required_route(problem([1], [(None, '0', 1, True)]))
    assert missing.status == 'infeasible' and missing.missing_required_mask == 2
    task = problem([1, 2], [(None, '0', 1, True), ('0', '1', 1, True)])
    with patch('scipy.optimize.milp', return_value=SimpleNamespace(status=1, x=None,
                                                               message='time limit')):
        result = solve_required_route(task)
    assert result.status == 'unresolved' and not result.optimal


@pytest.mark.parametrize('seed', range(12))
def test_milp_matches_all_permutations_on_small_directed_graphs(seed):
    rng = random.Random(seed)
    masks = [rng.randrange(8) for _ in range(5)]
    edges = [(source, str(j), rng.uniform(0.1, 10), rng.random() < 0.65)
             for source in [None, *map(str, range(5))] for j in range(5)
             if source != str(j)]
    task = problem(masks, edges, required=7, budget=1+seed % 5)
    expected = brute_force(task)
    result = solve_required_route(task)
    if math.isfinite(expected):
        assert result.status == 'feasible' and result.optimal
        assert result.graph_cost == pytest.approx(expected)
        assert result.lower_bound == pytest.approx(expected)
    else:
        assert result.status == 'infeasible'
