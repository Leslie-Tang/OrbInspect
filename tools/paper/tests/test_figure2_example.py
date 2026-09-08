"""Independent checks for the educational Figure 2 graph (not HCW data)."""
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import redesign_figure2_adp as figure


def test_base_policy_is_task_aware():
    assert figure.base_action(figure.START) == 1
    assert figure.base_rollout(figure.START) == (8., [1, 4])


def test_full_tail_and_zero_gain_connector():
    successor = figure.transition(figure.START, 2)
    assert successor == (2, 0, 2, 2)
    assert figure.MASKS[2] == 0
    assert figure.base_rollout(successor) == (3., [5, 4])
    assert figure.value(successor, 1) == 3.


def test_audit_and_completion_are_different_checks():
    assert figure.actions(figure.START) == (1, 2, 3)
    assert figure.REJECTED not in figure.EDGES
    assert math.isinf(figure.value(figure.transition(figure.START, 3), 1))


def test_independent_exhaustive_route_costs():
    # Independent set-based path enumeration, not the figure's bit-mask solver.
    target_sets = {0: set(), 1: {1}, 2: set(), 3: set(), 4: {2}, 5: {1}}
    stack = [([0], set(), 0.)]
    completed = []
    while stack:
        route, covered, cost = stack.pop()
        if covered == {1, 2}:
            completed.append((route, cost))
            continue
        if len(route) == 4:
            continue
        for (source, dest), edge_cost in figure.EDGES.items():
            if source == route[-1] and dest not in route:
                stack.append((route + [dest], covered | target_sets[dest], cost + edge_cost))
    assert sorted(completed) == [([0, 1, 4], 8.), ([0, 2, 5, 4], 4.)]
    assert figure.value(figure.START, 2) == min(cost for _, cost in completed)


def test_goal_and_budget_terminal_values():
    assert figure.value((4, 3, 26, 0), 2) == 0
    assert math.isinf(figure.value((2, 0, 2, 0), 2))
    assert math.isinf(figure.value((2, 0, 2, 1), 2))


def test_all_displayed_claims_and_reachable_state_bounds():
    report = figure.example_report()
    assert report['replanned_route'] == [0, 2, 5, 4]
    assert [r['covered_required_targets'] for r in report['state_trace']] == [0, 1, 2]
    assert report['depths_checked'] == [1, 2, 3, 4, 5, 6]
