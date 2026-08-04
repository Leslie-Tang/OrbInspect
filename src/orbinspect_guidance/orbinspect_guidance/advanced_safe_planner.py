"""Safety-shielded graph approximate dynamic programming for SOOA selection."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
import math
import random


@dataclass(frozen=True)
class AdvancedPlannerConfig:
    """Configuration for safety-shielded graph ADP."""

    method: str = 'safe_graph_adp'
    horizon_steps: int = 36
    time_step: float = 90.0
    safety_margin: float = 2.0
    goal_coverage: float = 0.98
    branch_width: int = 8
    candidate_pool_width: int = 24
    lookahead_depth: int = 3
    training_episodes: int = 80
    learning_rate: float = 0.035
    exploration_rate: float = 0.25
    terminal_penalty: float = 500.0
    action_cost: float = 0.05
    cost_scale: float = 50.0
    discount: float = 1.0
    random_seed: int = 7
    min_new_target_count: int = 1
    oracle_node_limit: int = 14
    reference_improvement_passes: int = 4
    enable_critic: bool = True
    enable_rollout: bool = True
    enable_reference_safeguard: bool = True
    critic_mode: str = 'online'


@dataclass(frozen=True)
class SafeGraphNode:
    """One candidate-view decision node and its target-visibility mask."""

    node_id: str
    coverage_mask: int
    static_priority: float = 0.0
    outgoing_cost_min: float = 0.0
    outgoing_cost_mean: float = 0.0
    feasible_out_degree: float = 0.0


@dataclass(frozen=True)
class SafeGraphEdge:
    """One audited directed transfer between two decision nodes."""

    source_id: str | None
    target_id: str
    stage_cost: float
    feasible: bool
    min_clearance: float
    peak_input: float = 0.0
    input_limit: float = math.inf
    passive_margin: float | None = None


@dataclass(frozen=True)
class GraphDecisionState:
    """Markov state for finite-horizon candidate-node selection."""

    current_node_id: str | None
    covered_mask: int
    selected_mask: int
    remaining_steps: int


@dataclass(frozen=True)
class GraphDecision:
    """One action selected by the shielded ADP policy."""

    sequence: int
    node_id: str
    new_target_mask: int
    coverage_ratio: float
    stage_cost: float
    estimated_cost_to_go: float
    safe_action_count: int
    shield_rejections: int


@dataclass(frozen=True)
class SafeGraphProblem:
    """Finite candidate graph, target weights, goal, and lazy edge evaluator."""

    nodes: tuple[SafeGraphNode, ...]
    target_weights: tuple[float, ...]
    edge_evaluator: Callable[[str | None, str], SafeGraphEdge]
    goal_coverage: float
    max_steps: int
    reference_node_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphPlan:
    """Complete learned graph policy result and training diagnostics."""

    node_ids: tuple[str, ...]
    decisions: tuple[GraphDecision, ...]
    total_cost: float
    coverage_ratio: float
    success: bool
    critic_weights: tuple[float, ...]
    training_episodes: int
    td_update_count: int
    mean_absolute_td_error: float
    safe_action_evaluations: int
    shield_rejections: int
    policy_source: str
    learned_total_cost: float | None
    rollout_total_cost: float | None
    reference_total_cost: float | None
    improved_reference_total_cost: float | None
    incumbent_improvement: float | None
    critic_enabled: bool
    rollout_enabled: bool
    safeguard_enabled: bool
    local_improvement_enabled: bool


@dataclass(frozen=True)
class ExactGraphSolution:
    """Exact reduced-graph solution used only for certification."""

    node_ids: tuple[str, ...]
    total_cost: float
    coverage_ratio: float
    expanded_states: int
    feasible: bool


class AdvancedSafePlanner:
    """Learn and execute a long-horizon policy on a shielded SOOA graph."""

    _FEATURE_COUNT = 26

    def __init__(
        self,
        config: AdvancedPlannerConfig | None = None,
        critic_weights: tuple[float, ...] | None = None,
        critic_predictor: Callable[[tuple[float, ...]], float] | None = None,
    ) -> None:
        self.config = config or AdvancedPlannerConfig()
        self._validate_config()
        self._weights = self._initial_weights()
        if critic_weights is not None:
            self.set_critic_weights(critic_weights)
        self._critic_predictor = critic_predictor
        self._safe_action_evaluations = 0
        self._shield_rejections = 0
        self._action_cache: dict[
            GraphDecisionState,
            tuple[
                tuple[tuple[SafeGraphNode, SafeGraphEdge, int, float], ...],
                int,
            ],
        ] | None = None
        self._value_cache: dict[tuple[GraphDecisionState, int], float] = {}

    @property
    def available(self) -> bool:
        """Return whether the configured graph-ADP backend is implemented."""
        return self.config.method in {'safe_graph_adp', 'graph_adp'}

    @property
    def critic_weights(self) -> tuple[float, ...]:
        """Return the current critic checkpoint weights."""
        return tuple(self._weights)

    def set_critic_weights(self, weights: tuple[float, ...]) -> None:
        """Load a critic checkpoint after validating its feature dimension."""
        if len(weights) != self._FEATURE_COUNT:
            raise ValueError(
                f'critic checkpoint needs {self._FEATURE_COUNT} weights, '
                f'got {len(weights)}'
            )
        if not all(math.isfinite(weight) for weight in weights):
            raise ValueError('critic checkpoint weights must be finite')
        self._weights = list(weights)

    def fit_critic(
        self,
        problems: tuple[SafeGraphProblem, ...],
        *,
        reset: bool = True,
    ) -> tuple[float, ...]:
        """Fit one reusable critic across a training-only problem collection."""
        if not problems:
            raise ValueError('critic training requires at least one problem')
        if reset:
            self._weights = self._initial_weights()
        for problem in problems:
            self._validate_problem(problem)
            self._safe_action_evaluations = 0
            self._shield_rejections = 0
            self._action_cache = None
            self._value_cache = {}
            self._fit_critic(problem)
        self._action_cache = None
        self._value_cache = {}
        return tuple(self._weights)

    def rollout_training_samples(
        self,
        problem: SafeGraphProblem,
    ) -> tuple[tuple[tuple[float, ...], float], ...]:
        """Return shielded rollout action-value targets for offline fitting."""
        self._validate_problem(problem)
        if not problem.reference_node_ids:
            raise ValueError('rollout targets require a reference policy')
        self._safe_action_evaluations = 0
        self._shield_rejections = 0
        self._action_cache = {}
        self._value_cache = {}
        node_index = {
            node.node_id: index
            for index, node in enumerate(problem.nodes)
        }
        state = GraphDecisionState(
            current_node_id=None,
            covered_mask=0,
            selected_mask=0,
            remaining_steps=min(problem.max_steps, self.config.horizon_steps),
        )
        samples: list[tuple[tuple[float, ...], float]] = []
        while (
            not self._goal_reached(problem, state.covered_mask)
            and state.remaining_steps > 0
        ):
            candidate_actions, _rejected = self._safe_actions(problem, state)
            action_by_id = {
                action[0].node_id: action for action in candidate_actions
            }
            for node_id in problem.reference_node_ids:
                index = node_index.get(node_id)
                if index is None or state.selected_mask & (1 << index):
                    continue
                node = problem.nodes[index]
                new_mask = node.coverage_mask & ~state.covered_mask
                if new_mask.bit_count() < self.config.min_new_target_count:
                    continue
                edge = problem.edge_evaluator(state.current_node_id, node_id)
                self._safe_action_evaluations += 1
                if not self._edge_is_safe(edge):
                    self._shield_rejections += 1
                    continue
                action_by_id[node_id] = (
                    node,
                    edge,
                    new_mask,
                    self._mask_weight(problem, new_mask)
                    / self._total_weight(problem),
                )

            evaluated = []
            for action in action_by_id.values():
                next_state = self._transition(state, action, node_index)
                if self._goal_reached(problem, next_state.covered_mask):
                    completion_cost = 0.0
                    completion_success = True
                else:
                    remaining_reference = tuple(
                        node_id
                        for node_id in problem.reference_node_ids
                        if node_id != action[0].node_id
                        and not (
                            next_state.selected_mask
                            & (1 << node_index[node_id])
                        )
                    )
                    completion_cost, completion_success = self._completion_cost(
                        problem,
                        next_state,
                        remaining_reference,
                        node_index,
                    )
                target = self._stage_cost(action[1])
                if completion_success:
                    target += completion_cost
                else:
                    target += self._terminal_cost(problem, next_state)
                features = self._action_features(problem, state, action)
                samples.append((features, target))
                evaluated.append((
                    not completion_success,
                    target,
                    action[1].stage_cost,
                    action[0].node_id,
                    next_state,
                ))
            feasible = [item for item in evaluated if not item[0]]
            if not feasible:
                break
            state = min(feasible)[4]
        self._action_cache = None
        self._value_cache = {}
        return tuple(samples)

    def exact_training_samples(
        self,
        problem: SafeGraphProblem,
    ) -> tuple[tuple[tuple[float, ...], float], ...]:
        """Return exact Bellman action values on an exhaustible graph."""
        return self._exact_training_samples(problem, center_by_state=False)

    def exact_advantage_training_samples(
        self,
        problem: SafeGraphProblem,
    ) -> tuple[tuple[tuple[float, ...], float], ...]:
        """Return exact nonnegative action gaps for policy distillation."""
        return self._exact_training_samples(problem, center_by_state=True)

    def _exact_training_samples(
        self,
        problem: SafeGraphProblem,
        *,
        center_by_state: bool,
    ) -> tuple[tuple[tuple[float, ...], float], ...]:
        """Enumerate exact action targets, optionally centered within state."""
        self._validate_problem(problem)
        if len(problem.nodes) > self.config.oracle_node_limit:
            raise ValueError(
                f'exact graph limit is {self.config.oracle_node_limit} nodes, '
                f'got {len(problem.nodes)}'
            )
        node_index = {
            node.node_id: index
            for index, node in enumerate(problem.nodes)
        }
        samples: list[tuple[tuple[float, ...], float]] = []

        @lru_cache(maxsize=None)
        def value(state: GraphDecisionState) -> float:
            if self._goal_reached(problem, state.covered_mask):
                return 0.0
            if state.remaining_steps <= 0:
                return math.inf
            best_cost = math.inf
            state_samples = []
            for action in self._all_safe_actions(problem, state):
                next_state = self._transition(state, action, node_index)
                future_cost = value(next_state)
                action_cost = self._stage_cost(action[1])
                candidate_cost = action_cost + future_cost
                target = (
                    candidate_cost
                    if math.isfinite(candidate_cost)
                    else action_cost + self._terminal_cost(problem, next_state)
                )
                state_samples.append((
                    self._action_features(problem, state, action),
                    target,
                ))
                best_cost = min(best_cost, candidate_cost)
            if center_by_state and state_samples:
                state_best = min(target for _features, target in state_samples)
                state_samples = [
                    (features, target - state_best)
                    for features, target in state_samples
                ]
            samples.extend(state_samples)
            return best_cost

        value(GraphDecisionState(
            current_node_id=None,
            covered_mask=0,
            selected_mask=0,
            remaining_steps=min(problem.max_steps, self.config.horizon_steps),
        ))
        return tuple(samples)

    def plan(self, problem: SafeGraphProblem) -> GraphPlan:
        """Fit the critic and select a safe candidate sequence."""
        if not self.available:
            raise ValueError(
                f'unsupported advanced planner method: {self.config.method}'
            )
        self._validate_problem(problem)
        self._safe_action_evaluations = 0
        self._shield_rejections = 0
        if self.config.critic_mode == 'online':
            self._weights = self._initial_weights()
        self._action_cache = None
        self._value_cache = {}
        td_errors = (
            self._fit_critic(problem)
            if (
                self.config.enable_critic
                and self.config.critic_mode == 'online'
            )
            else []
        )
        self._action_cache = {}
        node_index = {
            node.node_id: index
            for index, node in enumerate(problem.nodes)
        }

        candidate_plans: list[
            tuple[
                tuple[str, ...],
                tuple[GraphDecision, ...],
                float,
                float,
                bool,
                str,
            ]
        ] = []
        learned_total_cost: float | None = None
        rollout_total_cost: float | None = None
        reference_total_cost: float | None = None
        improved_reference_total_cost: float | None = None

        if self.config.enable_critic:
            learned = self._learned_solution(problem, node_index)
            learned_total_cost = learned[2]
            candidate_plans.append((*learned, 'learned_adp'))

        if self.config.enable_rollout:
            rollout = self._rollout_solution(problem, node_index)
            if rollout is not None:
                if rollout[4]:
                    rollout_total_cost = rollout[2]
                candidate_plans.append((*rollout, 'rollout_adp'))

        if self.config.enable_reference_safeguard:
            reference = self._reference_solution(problem, node_index)
        else:
            reference = None
        if reference is not None:
            (
                reference_node_ids,
                reference_decisions,
                improved_reference_cost,
                reference_coverage,
                reference_success,
                reference_total_cost,
            ) = reference
            improved_reference_total_cost = improved_reference_cost
            reference_source = (
                'reference_improved'
                if improved_reference_cost
                < reference_total_cost - 1.0e-12
                else 'reference_safeguard'
            )
            candidate_plans.append((
                reference_node_ids,
                reference_decisions,
                improved_reference_cost,
                reference_coverage,
                reference_success,
                reference_source,
            ))

        if not candidate_plans:
            candidate_plans.append(((), (), 0.0, 0.0, False, 'no_candidate'))
        successful_plans = [plan for plan in candidate_plans if plan[4]]
        source_priority = {
            'rollout_adp': 0,
            'learned_adp': 1,
            'reference_improved': 2,
            'reference_safeguard': 3,
            'no_candidate': 4,
        }
        if successful_plans:
            selected_plan = min(
                successful_plans,
                key=lambda plan: (
                    plan[2],
                    source_priority.get(plan[5], 99),
                ),
            )
        else:
            selected_plan = min(
                candidate_plans,
                key=lambda plan: (
                    -plan[3],
                    plan[2],
                    source_priority.get(plan[5], 99),
                ),
            )
        (
            selected_node_ids,
            selected_decisions,
            total_cost,
            selected_coverage,
            selected_success,
            policy_source,
        ) = selected_plan
        incumbent_improvement = (
            reference_total_cost - total_cost
            if reference_total_cost is not None and selected_success
            else None
        )

        return GraphPlan(
            node_ids=selected_node_ids,
            decisions=selected_decisions,
            total_cost=total_cost,
            coverage_ratio=selected_coverage,
            success=selected_success,
            critic_weights=tuple(self._weights),
            training_episodes=(
                self.config.training_episodes
                if (
                    self.config.enable_critic
                    and self.config.critic_mode == 'online'
                ) else 0
            ),
            td_update_count=len(td_errors),
            mean_absolute_td_error=(
                sum(abs(error) for error in td_errors) / len(td_errors)
                if td_errors else 0.0
            ),
            safe_action_evaluations=self._safe_action_evaluations,
            shield_rejections=self._shield_rejections,
            policy_source=policy_source,
            learned_total_cost=learned_total_cost,
            rollout_total_cost=rollout_total_cost,
            reference_total_cost=reference_total_cost,
            improved_reference_total_cost=improved_reference_total_cost,
            incumbent_improvement=incumbent_improvement,
            critic_enabled=self.config.enable_critic,
            rollout_enabled=self.config.enable_rollout,
            safeguard_enabled=self.config.enable_reference_safeguard,
            local_improvement_enabled=(
                self.config.enable_reference_safeguard
                and self.config.reference_improvement_passes > 0
            ),
        )

    def _learned_solution(
        self,
        problem: SafeGraphProblem,
        node_index: dict[str, int],
    ) -> tuple[
        tuple[str, ...],
        tuple[GraphDecision, ...],
        float,
        float,
        bool,
    ]:
        """Generate the critic-guided finite-lookahead policy candidate."""
        state = GraphDecisionState(
            current_node_id=None,
            covered_mask=0,
            selected_mask=0,
            remaining_steps=min(problem.max_steps, self.config.horizon_steps),
        )
        decisions: list[GraphDecision] = []
        total_cost = 0.0
        while (
            not self._goal_reached(problem, state.covered_mask)
            and state.remaining_steps > 0
        ):
            actions, rejected = self._safe_actions(problem, state)
            if not actions:
                break
            scored = []
            depth = self.config.lookahead_depth
            for action in actions:
                next_state = self._transition(state, action, node_index)
                if depth == 0:
                    estimate = self._predict_q(problem, state, action)
                else:
                    estimate = (
                        self._stage_cost(action[1])
                        + self.config.discount * self._value(
                            problem,
                            next_state,
                            depth - 1,
                            node_index,
                        )
                    )
                scored.append((estimate, action, next_state))
            estimate, action, next_state = min(
                scored,
                key=lambda item: (
                    item[0],
                    item[1][1].stage_cost,
                    item[1][0].node_id,
                ),
            )
            node, edge, new_target_mask, _gain_ratio = action
            total_cost += self._stage_cost(edge)
            decisions.append(GraphDecision(
                sequence=len(decisions),
                node_id=node.node_id,
                new_target_mask=new_target_mask,
                coverage_ratio=self._coverage_ratio(
                    problem,
                    next_state.covered_mask,
                ),
                stage_cost=self._stage_cost(edge),
                estimated_cost_to_go=estimate,
                safe_action_count=len(actions),
                shield_rejections=rejected,
            ))
            state = next_state
        coverage = self._coverage_ratio(problem, state.covered_mask)
        return (
            tuple(decision.node_id for decision in decisions),
            tuple(decisions),
            total_cost,
            coverage,
            coverage + 1.0e-12 >= problem.goal_coverage,
        )

    def solve_exact(self, problem: SafeGraphProblem) -> ExactGraphSolution:
        """Solve a small shielded graph exactly by Bellman recursion."""
        self._validate_problem(problem)
        if len(problem.nodes) > self.config.oracle_node_limit:
            raise ValueError(
                f'exact graph limit is {self.config.oracle_node_limit} nodes, '
                f'got {len(problem.nodes)}'
            )
        node_index = {
            node.node_id: index
            for index, node in enumerate(problem.nodes)
        }
        expanded_states = 0

        @lru_cache(maxsize=None)
        def value(state: GraphDecisionState) -> tuple[float, tuple[str, ...]]:
            nonlocal expanded_states
            expanded_states += 1
            if self._goal_reached(problem, state.covered_mask):
                return 0.0, ()
            if state.remaining_steps <= 0:
                return math.inf, ()
            best_cost = math.inf
            best_sequence: tuple[str, ...] = ()
            for action in self._all_safe_actions(problem, state):
                next_state = self._transition(state, action, node_index)
                future_cost, future_sequence = value(next_state)
                candidate_cost = self._stage_cost(action[1]) + future_cost
                if candidate_cost < best_cost:
                    best_cost = candidate_cost
                    best_sequence = (action[0].node_id,) + future_sequence
            return best_cost, best_sequence

        initial_state = GraphDecisionState(
            current_node_id=None,
            covered_mask=0,
            selected_mask=0,
            remaining_steps=min(problem.max_steps, self.config.horizon_steps),
        )
        total_cost, node_ids = value(initial_state)
        covered_mask = 0
        for node_id in node_ids:
            covered_mask |= problem.nodes[node_index[node_id]].coverage_mask
        coverage_ratio = self._coverage_ratio(problem, covered_mask)
        return ExactGraphSolution(
            node_ids=node_ids,
            total_cost=total_cost,
            coverage_ratio=coverage_ratio,
            expanded_states=expanded_states,
            feasible=math.isfinite(total_cost),
        )

    def _fit_critic(self, problem: SafeGraphProblem) -> list[float]:
        """Fit a linear action-value critic from reproducible safe rollouts."""
        generator = random.Random(self.config.random_seed)
        node_index = {
            node.node_id: index
            for index, node in enumerate(problem.nodes)
        }
        errors: list[float] = []
        episode_count = max(0, self.config.training_episodes)
        for episode in range(episode_count):
            state = GraphDecisionState(
                current_node_id=None,
                covered_mask=0,
                selected_mask=0,
                remaining_steps=min(problem.max_steps, self.config.horizon_steps),
            )
            samples: list[tuple[tuple[float, ...], float]] = []
            while (
                not self._goal_reached(problem, state.covered_mask)
                and state.remaining_steps > 0
            ):
                actions, _rejected = self._safe_actions(problem, state)
                if not actions:
                    break
                epsilon = self.config.exploration_rate / math.sqrt(1.0 + episode)
                if generator.random() < epsilon:
                    action = actions[generator.randrange(len(actions))]
                else:
                    action = min(
                        actions,
                        key=lambda item: (
                            self._predict_q(problem, state, item),
                            item[1].stage_cost,
                            item[0].node_id,
                        ),
                    )
                features = self._action_features(problem, state, action)
                samples.append((features, self._stage_cost(action[1])))
                state = self._transition(state, action, node_index)

            return_value = self._terminal_cost(problem, state)
            episode_samples: list[tuple[tuple[float, ...], float]] = []
            for features, stage_cost in reversed(samples):
                return_value = stage_cost + self.config.discount * return_value
                episode_samples.append((features, return_value))
            learning_rate = self.config.learning_rate / math.sqrt(1.0 + episode)
            for features, target in reversed(episode_samples):
                prediction = self._dot(self._weights, features)
                error = max(
                    -2.0 * self.config.terminal_penalty,
                    min(2.0 * self.config.terminal_penalty, target - prediction),
                )
                normalizer = 1.0 + self._dot(features, features)
                self._weights = [
                    weight + learning_rate * error * feature / normalizer
                    for weight, feature in zip(self._weights, features)
                ]
                errors.append(error)
        return errors

    def _rollout_solution(
        self,
        problem: SafeGraphProblem,
        node_index: dict[str, int],
    ) -> tuple[
        tuple[str, ...],
        tuple[GraphDecision, ...],
        float,
        float,
        bool,
    ] | None:
        """Apply one-step rollout using the safe incumbent as base policy."""
        if not problem.reference_node_ids:
            return None
        state = GraphDecisionState(
            current_node_id=None,
            covered_mask=0,
            selected_mask=0,
            remaining_steps=min(problem.max_steps, self.config.horizon_steps),
        )
        selected: list[
            tuple[
                SafeGraphNode,
                SafeGraphEdge,
                int,
                GraphDecisionState,
                float,
                int,
                int,
            ]
        ] = []
        while (
            not self._goal_reached(problem, state.covered_mask)
            and state.remaining_steps > 0
        ):
            learned_actions, rejected = self._safe_actions(problem, state)
            action_by_id = {
                action[0].node_id: action
                for action in learned_actions
            }
            for node_id in problem.reference_node_ids:
                index = node_index.get(node_id)
                if index is None or state.selected_mask & (1 << index):
                    continue
                node = problem.nodes[index]
                new_mask = node.coverage_mask & ~state.covered_mask
                if new_mask.bit_count() < self.config.min_new_target_count:
                    continue
                edge = problem.edge_evaluator(state.current_node_id, node_id)
                self._safe_action_evaluations += 1
                if not self._edge_is_safe(edge):
                    self._shield_rejections += 1
                    continue
                gain_ratio = (
                    self._mask_weight(problem, new_mask)
                    / self._total_weight(problem)
                )
                action_by_id[node_id] = (
                    node,
                    edge,
                    new_mask,
                    gain_ratio,
                )

            scored = []
            for action in action_by_id.values():
                next_state = self._transition(state, action, node_index)
                remaining_reference = tuple(
                    node_id
                    for node_id in problem.reference_node_ids
                    if node_id != action[0].node_id
                    and not (
                        next_state.selected_mask
                        & (1 << node_index[node_id])
                    )
                )
                completion_cost, completion_success = self._completion_cost(
                    problem,
                    next_state,
                    remaining_reference,
                    node_index,
                )
                if self._goal_reached(problem, next_state.covered_mask):
                    completion_cost = 0.0
                    completion_success = True
                if not completion_success:
                    continue
                rollout_cost = self._stage_cost(action[1]) + completion_cost
                scored.append((rollout_cost, action, next_state))
            if not scored:
                break
            rollout_cost, action, next_state = min(
                scored,
                key=lambda item: (
                    item[0],
                    item[1][1].stage_cost,
                    item[1][0].node_id,
                ),
            )
            selected.append((
                action[0],
                action[1],
                action[2],
                next_state,
                rollout_cost,
                len(action_by_id),
                rejected,
            ))
            state = next_state

        decisions = tuple(
            GraphDecision(
                sequence=index,
                node_id=node.node_id,
                new_target_mask=new_mask,
                coverage_ratio=self._coverage_ratio(
                    problem,
                    next_state.covered_mask,
                ),
                stage_cost=self._stage_cost(edge),
                estimated_cost_to_go=rollout_cost,
                safe_action_count=safe_action_count,
                shield_rejections=rejected,
            )
            for index, (
                node,
                edge,
                new_mask,
                next_state,
                rollout_cost,
                safe_action_count,
                rejected,
            ) in enumerate(selected)
        )
        coverage = self._coverage_ratio(problem, state.covered_mask)
        return (
            tuple(decision.node_id for decision in decisions),
            decisions,
            sum(decision.stage_cost for decision in decisions),
            coverage,
            self._goal_reached(problem, state.covered_mask),
        )

    def _completion_cost(
        self,
        problem: SafeGraphProblem,
        initial_state: GraphDecisionState,
        node_ids: tuple[str, ...],
        node_index: dict[str, int],
    ) -> tuple[float, bool]:
        """Evaluate a fixed safe base-policy completion from a Markov state."""
        state = initial_state
        total_cost = 0.0
        for node_id in node_ids:
            if self._goal_reached(problem, state.covered_mask):
                return total_cost, True
            if state.remaining_steps <= 0:
                return math.inf, False
            index = node_index.get(node_id)
            if index is None or state.selected_mask & (1 << index):
                continue
            node = problem.nodes[index]
            new_mask = node.coverage_mask & ~state.covered_mask
            if new_mask.bit_count() < self.config.min_new_target_count:
                continue
            edge = problem.edge_evaluator(state.current_node_id, node_id)
            self._safe_action_evaluations += 1
            if not self._edge_is_safe(edge):
                self._shield_rejections += 1
                return math.inf, False
            gain_ratio = (
                self._mask_weight(problem, new_mask)
                / self._total_weight(problem)
            )
            action = (node, edge, new_mask, gain_ratio)
            total_cost += self._stage_cost(edge)
            state = self._transition(state, action, node_index)
        return total_cost, self._goal_reached(problem, state.covered_mask)

    def _reference_solution(
        self,
        problem: SafeGraphProblem,
        node_index: dict[str, int],
    ) -> tuple[
        tuple[str, ...],
        tuple[GraphDecision, ...],
        float,
        float,
        bool,
        float,
    ] | None:
        """Audit and locally improve the supplied safe incumbent sequence."""
        if not problem.reference_node_ids:
            return None
        raw = self._sequence_metrics(
            problem,
            problem.reference_node_ids,
            node_index,
        )
        if raw is None or not raw[4]:
            return None
        best = raw
        best_ids = raw[0]
        for _pass in range(self.config.reference_improvement_passes):
            improved = False
            candidate_best = best
            candidate_ids = best_ids
            for left in range(len(best_ids)):
                for right in range(left + 2, len(best_ids) + 1):
                    proposal = (
                        best_ids[:left]
                        + tuple(reversed(best_ids[left:right]))
                        + best_ids[right:]
                    )
                    metrics = self._sequence_metrics(
                        problem,
                        proposal,
                        node_index,
                    )
                    if (
                        metrics is not None
                        and metrics[4]
                        and metrics[2] < candidate_best[2] - 1.0e-12
                    ):
                        candidate_best = metrics
                        candidate_ids = metrics[0]
                        improved = True
            if not improved:
                break
            best = candidate_best
            best_ids = candidate_ids
        return (*best, raw[2])

    def _sequence_metrics(
        self,
        problem: SafeGraphProblem,
        node_ids: tuple[str, ...],
        node_index: dict[str, int],
    ) -> tuple[
        tuple[str, ...],
        tuple[GraphDecision, ...],
        float,
        float,
        bool,
    ] | None:
        """Return audited metrics for a fixed node sequence."""
        state = GraphDecisionState(
            current_node_id=None,
            covered_mask=0,
            selected_mask=0,
            remaining_steps=min(problem.max_steps, self.config.horizon_steps),
        )
        audited: list[
            tuple[
                SafeGraphNode,
                SafeGraphEdge,
                int,
                float,
                GraphDecisionState,
            ]
        ] = []
        for node_id in node_ids:
            if state.remaining_steps <= 0:
                break
            index = node_index.get(node_id)
            if index is None or state.selected_mask & (1 << index):
                return None
            node = problem.nodes[index]
            new_mask = node.coverage_mask & ~state.covered_mask
            if new_mask.bit_count() < self.config.min_new_target_count:
                continue
            edge = problem.edge_evaluator(state.current_node_id, node_id)
            self._safe_action_evaluations += 1
            if not self._edge_is_safe(edge):
                self._shield_rejections += 1
                return None
            gain_ratio = (
                self._mask_weight(problem, new_mask)
                / self._total_weight(problem)
            )
            action = (node, edge, new_mask, gain_ratio)
            next_state = self._transition(state, action, node_index)
            audited.append((node, edge, new_mask, gain_ratio, next_state))
            state = next_state
            if self._goal_reached(problem, state.covered_mask):
                break

        costs = [self._stage_cost(item[1]) for item in audited]
        suffix_costs = [0.0] * len(costs)
        running_cost = 0.0
        for index in range(len(costs) - 1, -1, -1):
            running_cost += costs[index]
            suffix_costs[index] = running_cost
        decisions = tuple(
            GraphDecision(
                sequence=index,
                node_id=node.node_id,
                new_target_mask=new_mask,
                coverage_ratio=self._coverage_ratio(
                    problem,
                    next_state.covered_mask,
                ),
                stage_cost=costs[index],
                estimated_cost_to_go=suffix_costs[index],
                safe_action_count=0,
                shield_rejections=0,
            )
            for index, (
                node,
                _edge,
                new_mask,
                _gain_ratio,
                next_state,
            ) in enumerate(audited)
        )
        coverage = self._coverage_ratio(problem, state.covered_mask)
        return (
            tuple(decision.node_id for decision in decisions),
            decisions,
            sum(costs),
            coverage,
            self._goal_reached(problem, state.covered_mask),
        )

    def _value(
        self,
        problem: SafeGraphProblem,
        state: GraphDecisionState,
        depth: int,
        node_index: dict[str, int],
    ) -> float:
        cache_key = (state, depth)
        cached = self._value_cache.get(cache_key)
        if cached is not None:
            return cached
        if self._goal_reached(problem, state.covered_mask):
            return 0.0
        if state.remaining_steps <= 0:
            return self._terminal_cost(problem, state)
        actions, _rejected = self._safe_actions(problem, state)
        if not actions:
            return self._terminal_cost(problem, state)
        if depth <= 0:
            value = min(
                self._predict_q(problem, state, action)
                for action in actions
            )
        else:
            value = min(
                self._stage_cost(action[1])
                + self.config.discount
                * self._value(
                    problem,
                    self._transition(state, action, node_index),
                    depth - 1,
                    node_index,
                )
                for action in actions
            )
        self._value_cache[cache_key] = value
        return value

    def _safe_actions(
        self,
        problem: SafeGraphProblem,
        state: GraphDecisionState,
    ) -> tuple[
        list[tuple[SafeGraphNode, SafeGraphEdge, int, float]],
        int,
    ]:
        if self._action_cache is not None:
            cached = self._action_cache.get(state)
            if cached is not None:
                cached_actions, rejected = cached
                return list(cached_actions), rejected
        candidates = self._candidate_actions(problem, state)
        width = max(self.config.branch_width, self.config.candidate_pool_width)
        evaluated: list[tuple[SafeGraphNode, SafeGraphEdge, int, float]] = []
        rejected = 0
        for node, new_mask, gain_ratio in candidates[:width]:
            edge = problem.edge_evaluator(state.current_node_id, node.node_id)
            self._safe_action_evaluations += 1
            if not self._edge_is_safe(edge):
                rejected += 1
                self._shield_rejections += 1
                continue
            evaluated.append((node, edge, new_mask, gain_ratio))
        evaluated.sort(
            key=lambda item: (
                self._predict_q(problem, state, item),
                item[1].stage_cost,
                item[0].node_id,
            )
        )
        actions = evaluated[:max(1, self.config.branch_width)]
        if self._action_cache is not None:
            self._action_cache[state] = (tuple(actions), rejected)
        return actions, rejected

    def _all_safe_actions(
        self,
        problem: SafeGraphProblem,
        state: GraphDecisionState,
    ) -> list[tuple[SafeGraphNode, SafeGraphEdge, int, float]]:
        actions = []
        for node, new_mask, gain_ratio in self._candidate_actions(problem, state):
            edge = problem.edge_evaluator(state.current_node_id, node.node_id)
            if self._edge_is_safe(edge):
                actions.append((node, edge, new_mask, gain_ratio))
        return actions

    def _candidate_actions(
        self,
        problem: SafeGraphProblem,
        state: GraphDecisionState,
    ) -> list[tuple[SafeGraphNode, int, float]]:
        actions = []
        for index, node in enumerate(problem.nodes):
            if state.selected_mask & (1 << index):
                continue
            new_mask = node.coverage_mask & ~state.covered_mask
            if new_mask.bit_count() < self.config.min_new_target_count:
                continue
            gain_ratio = self._mask_weight(problem, new_mask) / self._total_weight(problem)
            actions.append((node, new_mask, gain_ratio))
        actions.sort(
            key=lambda item: (item[2], item[0].static_priority, item[0].node_id),
            reverse=True,
        )
        return actions

    def _transition(
        self,
        state: GraphDecisionState,
        action: tuple[SafeGraphNode, SafeGraphEdge, int, float],
        node_index: dict[str, int],
    ) -> GraphDecisionState:
        node = action[0]
        return GraphDecisionState(
            current_node_id=node.node_id,
            covered_mask=state.covered_mask | node.coverage_mask,
            selected_mask=state.selected_mask | (1 << node_index[node.node_id]),
            remaining_steps=state.remaining_steps - 1,
        )

    def _predict_q(
        self,
        problem: SafeGraphProblem,
        state: GraphDecisionState,
        action: tuple[SafeGraphNode, SafeGraphEdge, int, float],
    ) -> float:
        features = self._action_features(problem, state, action)
        if self._critic_predictor is not None:
            prediction = float(self._critic_predictor(features))
            if not math.isfinite(prediction):
                raise ValueError('critic predictor returned a non-finite value')
            return prediction
        return self._dot(self._weights, features)

    def _action_features(
        self,
        problem: SafeGraphProblem,
        state: GraphDecisionState,
        action: tuple[SafeGraphNode, SafeGraphEdge, int, float],
    ) -> tuple[float, ...]:
        node, edge, new_mask, gain_ratio = action
        del node
        next_mask = state.covered_mask | new_mask
        coverage_after = self._coverage_ratio(problem, next_mask)
        goal = max(problem.goal_coverage, 1.0e-12)
        gap_after = max(0.0, problem.goal_coverage - coverage_after) / goal
        used_fraction = 1.0 - state.remaining_steps / max(
            1.0,
            float(min(problem.max_steps, self.config.horizon_steps)),
        )
        stage_cost = self._stage_cost(edge) / max(self.config.cost_scale, 1.0e-12)
        efficiency = gain_ratio / max(stage_cost, 0.05)
        clearance_deficit = max(
            0.0,
            self.config.safety_margin - edge.min_clearance,
        ) / max(self.config.safety_margin, 1.0)
        input_ratio = (
            edge.peak_input / edge.input_limit
            if edge.input_limit > 0.0 and math.isfinite(edge.input_limit)
            else 0.0
        )
        total_weight = self._total_weight(problem)
        node_weight = self._mask_weight(
            problem,
            action[0].coverage_mask,
        ) / total_weight
        novelty_fraction = gain_ratio / max(node_weight, 1.0e-12)
        remaining_gains = []
        for index, candidate in enumerate(problem.nodes):
            if state.selected_mask & (1 << index):
                continue
            if candidate.node_id == action[0].node_id:
                continue
            residual_mask = candidate.coverage_mask & ~next_mask
            remaining_gains.append(
                self._mask_weight(problem, residual_mask) / total_weight
            )
        remaining_gains.sort(reverse=True)
        best_remaining_gain = remaining_gains[0] if remaining_gains else 0.0
        top_remaining = remaining_gains[:3]
        mean_top_remaining_gain = (
            sum(top_remaining) / len(top_remaining)
            if top_remaining else 0.0
        )
        best_two_step_gain = min(
            1.0,
            gain_ratio + best_remaining_gain,
        )
        gap_weight = max(0.0, problem.goal_coverage - coverage_after)
        if gap_weight <= 1.0e-12:
            optimistic_actions = 0
        elif best_remaining_gain <= 1.0e-12:
            optimistic_actions = state.remaining_steps
        else:
            optimistic_actions = math.ceil(gap_weight / best_remaining_gain)
        remaining_after = max(0, state.remaining_steps - 1)
        budget_slack = max(
            -1.0,
            min(
                1.0,
                (remaining_after - optimistic_actions)
                / max(1.0, float(self.config.horizon_steps)),
            ),
        )
        bin_count = 4
        new_weight_bins = [0.0] * bin_count
        uncovered_weight_bins = [0.0] * bin_count
        target_count = max(1, len(problem.target_weights))
        for index, weight in enumerate(problem.target_weights):
            bin_index = min(bin_count - 1, index * bin_count // target_count)
            bit = 1 << index
            if new_mask & bit:
                new_weight_bins[bin_index] += weight / total_weight
            if not next_mask & bit:
                uncovered_weight_bins[bin_index] += weight / total_weight
        outgoing_cost_min = action[0].outgoing_cost_min / max(
            self.config.cost_scale,
            1.0e-12,
        )
        outgoing_cost_mean = action[0].outgoing_cost_mean / max(
            self.config.cost_scale,
            1.0e-12,
        )
        return (
            1.0,
            gap_after,
            gap_after * gap_after,
            stage_cost,
            gain_ratio,
            efficiency,
            used_fraction,
            1.0 / max(1.0, float(state.remaining_steps)),
            clearance_deficit,
            input_ratio,
            novelty_fraction,
            best_remaining_gain,
            mean_top_remaining_gain,
            best_two_step_gain,
            budget_slack,
            *new_weight_bins,
            *uncovered_weight_bins,
            outgoing_cost_min,
            outgoing_cost_mean,
            action[0].feasible_out_degree,
        )

    def _terminal_cost(
        self,
        problem: SafeGraphProblem,
        state: GraphDecisionState,
    ) -> float:
        coverage = self._coverage_ratio(problem, state.covered_mask)
        if coverage + 1.0e-12 >= problem.goal_coverage:
            return 0.0
        gap = (problem.goal_coverage - coverage) / max(problem.goal_coverage, 1.0e-12)
        return self.config.terminal_penalty * (0.5 + gap)

    def _edge_is_safe(self, edge: SafeGraphEdge) -> bool:
        passive_safe = edge.passive_margin is None or edge.passive_margin >= 0.0
        return (
            edge.feasible
            and edge.min_clearance >= 0.0
            and edge.peak_input <= edge.input_limit + 1.0e-12
            and passive_safe
        )

    def _stage_cost(self, edge: SafeGraphEdge) -> float:
        return edge.stage_cost + self.config.action_cost

    def _goal_reached(self, problem: SafeGraphProblem, covered_mask: int) -> bool:
        return self._coverage_ratio(problem, covered_mask) + 1.0e-12 >= problem.goal_coverage

    def _coverage_ratio(self, problem: SafeGraphProblem, covered_mask: int) -> float:
        return self._mask_weight(problem, covered_mask) / self._total_weight(problem)

    @staticmethod
    def _mask_weight(problem: SafeGraphProblem, mask: int) -> float:
        return sum(
            weight
            for index, weight in enumerate(problem.target_weights)
            if mask & (1 << index)
        )

    @staticmethod
    def _total_weight(problem: SafeGraphProblem) -> float:
        return max(sum(problem.target_weights), 1.0e-12)

    def _initial_weights(self) -> list[float]:
        penalty = self.config.terminal_penalty
        return [
            0.0,
            0.55 * penalty,
            0.45 * penalty,
            self.config.cost_scale,
            -0.15 * penalty,
            -0.02 * penalty,
            0.05 * penalty,
            0.02 * penalty,
            0.10 * penalty,
            0.05 * penalty,
            -0.05 * penalty,
            -0.10 * penalty,
            -0.05 * penalty,
            -0.10 * penalty,
            -0.05 * penalty,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]

    def _validate_config(self) -> None:
        if self.config.horizon_steps <= 0:
            raise ValueError('horizon_steps must be positive')
        if self.config.branch_width <= 0:
            raise ValueError('branch_width must be positive')
        if self.config.candidate_pool_width < self.config.branch_width:
            raise ValueError('candidate_pool_width must be at least branch_width')
        if self.config.lookahead_depth < 0:
            raise ValueError('lookahead_depth cannot be negative')
        if self.config.training_episodes < 0:
            raise ValueError('training_episodes cannot be negative')
        if self.config.reference_improvement_passes < 0:
            raise ValueError('reference_improvement_passes cannot be negative')
        if self.config.critic_mode not in {'online', 'frozen'}:
            raise ValueError("critic_mode must be 'online' or 'frozen'")
        if (
            self.config.reference_improvement_passes > 0
            and not self.config.enable_reference_safeguard
        ):
            raise ValueError(
                'reference improvement requires the reference safeguard'
            )
        if not (
            self.config.enable_critic
            or self.config.enable_rollout
            or self.config.enable_reference_safeguard
        ):
            raise ValueError('at least one policy candidate must be enabled')
        if self.config.learning_rate <= 0.0:
            raise ValueError('learning_rate must be positive')
        if not 0.0 <= self.config.exploration_rate <= 1.0:
            raise ValueError('exploration_rate must lie in [0, 1]')
        if not 0.0 < self.config.discount <= 1.0:
            raise ValueError('discount must lie in (0, 1]')
        if self.config.cost_scale <= 0.0:
            raise ValueError('cost_scale must be positive')
        if not 0.0 < self.config.goal_coverage <= 1.0:
            raise ValueError('goal_coverage must lie in (0, 1]')

    @staticmethod
    def _validate_problem(problem: SafeGraphProblem) -> None:
        if not problem.nodes:
            raise ValueError('safe graph requires at least one node')
        if not problem.target_weights:
            raise ValueError('safe graph requires target weights')
        if problem.max_steps <= 0:
            raise ValueError('safe graph max_steps must be positive')
        if not 0.0 < problem.goal_coverage <= 1.0:
            raise ValueError('safe graph goal_coverage must lie in (0, 1]')
        node_ids = tuple(node.node_id for node in problem.nodes)
        if len(set(node_ids)) != len(node_ids):
            raise ValueError('safe graph node identifiers must be unique')
        if len(set(problem.reference_node_ids)) != len(problem.reference_node_ids):
            raise ValueError('reference node identifiers must be unique')
        unknown_reference_ids = set(problem.reference_node_ids) - set(node_ids)
        if unknown_reference_ids:
            raise ValueError(
                'reference contains unknown nodes: '
                + ', '.join(sorted(unknown_reference_ids))
            )
        valid_mask = (1 << len(problem.target_weights)) - 1
        for node in problem.nodes:
            if node.coverage_mask & ~valid_mask:
                raise ValueError(f'node {node.node_id} references an unknown target')

    @staticmethod
    def _dot(
        left: tuple[float, ...] | list[float],
        right: tuple[float, ...] | list[float],
    ) -> float:
        return sum(first * second for first, second in zip(left, right))
