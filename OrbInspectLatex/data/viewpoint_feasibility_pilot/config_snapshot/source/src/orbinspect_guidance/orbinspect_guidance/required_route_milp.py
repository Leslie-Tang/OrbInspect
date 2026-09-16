"""Independent mixed-integer certificates for finite required-target routes.

This module does not call ADP or its exact recursion. Binary directed arcs form
one source-to-sink path; continuous increasing ranks eliminate disconnected
cycles. Required-target coverage, the observation budget, and no revisits are
explicit constraints. SciPy/HiGHS is an optional offline-study dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from time import perf_counter

from orbinspect_guidance.advanced_safe_planner import SafeGraphEdge, SafeGraphProblem


@dataclass(frozen=True)
class RouteCertificate:
    """A checked witness, a proof of impossibility, or an unresolved solve."""

    status: str
    reason: str
    node_ids: tuple[str, ...] = ()
    graph_cost: float | None = None
    lower_bound: float | None = None
    relative_gap: float | None = None
    optimal: bool = False
    elapsed_s: float = 0.0
    solver_status: int | None = None
    solver_message: str = ''
    missing_required_mask: int = 0


def admissible(edge: SafeGraphEdge) -> bool:
    """Check the published enabled graph audits without invoking the planner."""
    return (edge.feasible and math.isfinite(edge.min_clearance)
            and edge.min_clearance >= 0.0 and math.isfinite(edge.peak_input)
            and edge.peak_input <= edge.input_limit + 1e-12
            and (edge.passive_margin is None or edge.passive_margin >= 0.0))


def validate_route(problem: SafeGraphProblem, route: tuple[str, ...],
                   action_cost: float = 0.05) -> dict:
    """Reconstruct membership, budget, edge audits, credit and cost of a route."""
    nodes = {n.node_id: n for n in problem.nodes}
    if len(route) > problem.max_steps or len(route) != len(set(route)):
        raise ValueError('Route exceeds its budget or revisits a node.')
    covered = 0
    source = None
    cost = delta_v = 0.0
    clearance = math.inf
    peak = 0.0
    for target in route:
        if target not in nodes:
            raise ValueError(f'Unavailable route node: {target}')
        edge = problem.edge_evaluator(source, target)
        if edge.source_id != source or edge.target_id != target or not admissible(edge):
            raise ValueError(f'Invalid directed edge: {source} -> {target}')
        if not math.isfinite(edge.stage_cost) or edge.stage_cost < 0.0:
            raise ValueError('Expected finite, nonnegative graph costs.')
        covered |= nodes[target].coverage_mask
        cost += edge.stage_cost + action_cost
        delta_v += edge.delta_v
        clearance = min(clearance, edge.min_clearance)
        peak = max(peak, edge.peak_input)
        source = target
    required = problem.required_target_mask
    return {'success': covered & required == required, 'covered_mask': covered,
            'required_covered_count': (covered & required).bit_count(),
            'missing_required_mask': required & ~covered, 'graph_cost': cost,
            'total_delta_v': delta_v, 'selected_count': len(route),
            'min_clearance': clearance if route else None, 'peak_input': peak}


def solve_required_route(problem: SafeGraphProblem, *, time_limit_s: float = 15.0,
                         action_cost: float = 0.05) -> RouteCertificate:
    """Minimize route cost and independently classify finite-graph feasibility.

    A time limit is never evidence of infeasibility. A returned integer solution
    is checked against the MILP and reconstructed through the original graph.
    The formulation supports required-only goals and nonnegative additive costs.
    """
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix

    start = perf_counter()
    if problem.goal_mode != 'required':
        raise ValueError('This certificate solver supports required-only goals.')
    if time_limit_s <= 0 or action_cost < 0 or problem.max_steps < 0:
        raise ValueError('Invalid solver budget or action cost.')
    ids = tuple(n.node_id for n in problem.nodes)
    if len(ids) != len(set(ids)) or problem.required_target_mask < 0:
        raise ValueError('Invalid node identities or required-target mask.')
    n = len(ids)
    required = problem.required_target_mask
    if not required:
        return RouteCertificate('feasible', 'empty_requirement', graph_cost=0.0,
                                lower_bound=0.0, relative_gap=0.0, optimal=True,
                                elapsed_s=perf_counter()-start)
    union = 0
    for node in problem.nodes:
        union |= node.coverage_mask
    missing = required & ~union
    if missing:
        return RouteCertificate('infeasible', 'missing_required_visibility',
                                elapsed_s=perf_counter()-start,
                                missing_required_mask=missing)
    if problem.max_steps == 0:
        return RouteCertificate('infeasible', 'zero_action_budget',
                                elapsed_s=perf_counter()-start)

    # -1 is the unique source, n is the artificial terminal sink.
    arcs: list[tuple[int, int, float]] = []
    adjacency: dict[int, list[int]] = {i: [] for i in range(-1, n)}
    for i in range(-1, n):
        for j in range(n):
            if i == j:
                continue
            edge = problem.edge_evaluator(None if i == -1 else ids[i], ids[j])
            if not admissible(edge):
                continue
            if edge.source_id != (None if i == -1 else ids[i]) or edge.target_id != ids[j]:
                raise ValueError('Edge evaluator returned inconsistent identities.')
            cost = edge.stage_cost + action_cost
            if not math.isfinite(cost) or cost < 0:
                raise ValueError('Expected finite, nonnegative graph costs.')
            arcs.append((i, j, cost))
            adjacency[i].append(j)
    reachable = {-1}
    queue = [-1]
    while queue:
        for j in adjacency[queue.pop()]:
            if j not in reachable:
                reachable.add(j)
                queue.append(j)
    reach_mask = 0
    for i in reachable - {-1}:
        reach_mask |= problem.nodes[i].coverage_mask
    missing = required & ~reach_mask
    if missing:
        return RouteCertificate('infeasible', 'unreachable_required_visibility',
                                elapsed_s=perf_counter()-start,
                                missing_required_mask=missing)
    arcs.extend((i, n, 0.0) for i in range(n))
    m = len(arcs)
    size = m + 2*n
    horizon = min(problem.max_steps, n)
    row_indices: list[int] = []
    col_indices: list[int] = []
    values: list[float] = []
    lower: list[float] = []
    upper: list[float] = []

    def constraint(coefficients: dict[int, float], lo: float, hi: float) -> None:
        index = len(lower)
        for col, value in coefficients.items():
            row_indices.append(index); col_indices.append(col); values.append(value)
        lower.append(lo); upper.append(hi)

    constraint({k: 1.0 for k, (i, _, _) in enumerate(arcs) if i == -1}, 1, 1)
    constraint({k: 1.0 for k, (_, j, _) in enumerate(arcs) if j == n}, 1, 1)
    for i in range(n):
        incoming = {k: 1.0 for k, (_, j, _) in enumerate(arcs) if j == i}
        outgoing = {k: 1.0 for k, (j, _, _) in enumerate(arcs) if j == i}
        incoming[m+i] = -1.0; outgoing[m+i] = -1.0
        constraint(incoming, 0, 0); constraint(outgoing, 0, 0)
        constraint({m+n+i: 1, m+i: -1}, 0, math.inf)
        constraint({m+n+i: 1, m+i: -horizon}, -math.inf, 0)
    constraint({m+i: 1 for i in range(n)}, 0, horizon)
    for bit in range(required.bit_length()):
        if required & (1 << bit):
            constraint({m+i: 1 for i, node in enumerate(problem.nodes)
                        if node.coverage_mask & (1 << bit)}, 1, math.inf)
    for k, (i, j, _) in enumerate(arcs):
        if i >= 0 and j < n:
            constraint({m+n+i: 1, m+n+j: -1, k: horizon+1}, -math.inf, horizon)
    matrix = coo_matrix((values, (row_indices, col_indices)),
                        shape=(len(lower), size)).tocsc()
    costs = np.array([cost for _, _, cost in arcs] + [0.0]*(2*n))
    integrality = np.array([1]*(m+n) + [0]*n)
    bounds = Bounds(np.zeros(size), np.array([1.0]*(m+n) + [float(horizon)]*n))
    remaining = time_limit_s - (perf_counter()-start)
    if remaining <= 0:
        return RouteCertificate('unresolved', 'model_time_limit', elapsed_s=perf_counter()-start)
    result = milp(costs, integrality=integrality, bounds=bounds,
                  constraints=LinearConstraint(matrix, lower, upper),
                  options={'time_limit': remaining, 'mip_rel_gap': 0.0, 'presolve': True})

    def finite(value) -> float | None:
        return float(value) if value is not None and math.isfinite(value) else None

    common = {'elapsed_s': perf_counter()-start, 'solver_status': int(result.status),
              'solver_message': str(result.message),
              'lower_bound': finite(getattr(result, 'mip_dual_bound', None)),
              'relative_gap': finite(getattr(result, 'mip_gap', None))}
    if result.status == 2:
        return RouteCertificate('infeasible', 'milp_infeasible', **common)
    x = result.x
    if x is None:
        return RouteCertificate('unresolved', 'no_integer_witness', **common)
    ax = matrix @ x
    integer_ok = np.max(np.abs(x[:m+n]-np.round(x[:m+n]))) <= 1e-5
    bounds_ok = np.all(x >= bounds.lb-1e-6) and np.all(x <= bounds.ub+1e-6)
    rows_ok = np.all(ax >= np.asarray(lower)-1e-6) and np.all(ax <= np.asarray(upper)+1e-6)
    if not (integer_ok and bounds_ok and rows_ok):
        return RouteCertificate('unresolved', 'invalid_integer_witness', **common)
    selected = [(i, j) for k, (i, j, _) in enumerate(arcs) if x[k] > 0.5]
    successor = dict(selected)
    route_indices = []
    current = -1
    while current in successor and successor[current] != n:
        current = successor[current]
        if current in route_indices:
            raise RuntimeError('MILP cycle escaped the order constraints.')
        route_indices.append(current)
    if successor.get(current) != n or len(selected) != len(route_indices)+1:
        raise RuntimeError('MILP witness contains a disconnected component.')
    route = tuple(ids[i] for i in route_indices)
    metrics = validate_route(problem, route, action_cost)
    if not metrics['success'] or not math.isclose(metrics['graph_cost'], result.fun,
                                                rel_tol=1e-7, abs_tol=1e-6):
        raise RuntimeError('Reconstructed MILP route does not match the solved objective.')
    return RouteCertificate('feasible', 'checked_route_witness', node_ids=route,
                            graph_cost=metrics['graph_cost'], optimal=result.status == 0,
                            **common)
