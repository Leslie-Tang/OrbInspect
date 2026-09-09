"""Train once and evaluate frozen graph ADP on held-out HCW missions."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, replace
from datetime import datetime
import json
import math
from pathlib import Path
import random
from statistics import mean, median
from time import perf_counter

import numpy as np

from orbinspect_guidance.advanced_safe_planner import AdvancedPlannerConfig
from orbinspect_guidance.advanced_safe_planner import AdvancedSafePlanner
from orbinspect_guidance.advanced_safe_planner import SafeGraphEdge
from orbinspect_guidance.advanced_safe_planner import SafeGraphNode
from orbinspect_guidance.advanced_safe_planner import SafeGraphProblem
from orbinspect_guidance.offline_planning_experiment import _load_yaml_config
from orbinspect_guidance.offline_planning_experiment import ExperimentConfig
from orbinspect_guidance.offline_planning_experiment import OfflinePlanningExperiment


METHODS = (
    'adaptive_rollout_adp',
    'frozen_adp',
    'search_only',
    'incumbent',
    'rollout',
    'local_search',
    'frozen_adp_safeguard',
)


@dataclass(frozen=True)
class SuperiorityConfig:
    """Configuration for the train-once, held-out superiority study."""

    candidate_limit: int = 36
    goal_coverage: float = 0.90
    max_steps: int = 18
    branch_width: int = 6
    candidate_pool_width: int = 14
    lookahead_depth: int = 2
    training_scenarios: int = 24
    validation_scenarios: int = 8
    test_scenarios: int = 30
    ood_scenarios: int = 20
    episodes_per_training_scenario: int = 12
    learning_rate: float = 0.025
    ridge_regularization: float = 0.10
    critic_backend: str = 'mlp'
    mlp_hidden_units: int = 48
    mlp_regularization: float = 0.001
    training_target: str = 'rollout'
    scenario_node_count: int = 0
    ood_node_increment: int = 2
    exploration_rate: float = 0.30
    terminal_penalty: float = 500.0
    action_cost: float = 0.05
    cost_scale: float = 50.0
    local_improvement_passes: int = 3
    adaptive_rollout_depth: int = 1
    base_seed: int = 731


@dataclass(frozen=True)
class ArchivedEdge:
    """Serializable HCW edge record shared by every study method."""

    source_id: str | None
    target_id: str
    stage_cost: float
    feasible: bool
    min_clearance: float
    peak_input: float
    input_limit: float
    passive_margin: float | None
    delta_v: float = 0.0
    tracking_error: float = 0.0

    def to_safe_edge(self) -> SafeGraphEdge:
        """Convert the archived record to the planner edge interface."""
        return SafeGraphEdge(**asdict(self))


@dataclass(frozen=True)
class ArchivedGraph:
    """One fixed camera graph with HCW-audited directed transfers."""

    node_ids: tuple[str, ...]
    coverage_masks: tuple[int, ...]
    static_priorities: tuple[float, ...]
    target_ids: tuple[str, ...]
    base_target_weights: tuple[float, ...]
    edges: tuple[ArchivedEdge, ...]
    node_positions: tuple[tuple[float, float, float], ...] = ()

    def edge_map(self) -> dict[tuple[str | None, str], SafeGraphEdge]:
        """Index archived edges by source and target identifiers."""
        return {
            (edge.source_id, edge.target_id): edge.to_safe_edge()
            for edge in self.edges
        }


@dataclass(frozen=True)
class MissionScenario:
    """One mission distribution sample with no shared mutable state."""

    scenario_id: str
    split: str
    seed: int
    available_node_ids: tuple[str, ...]
    target_weights: tuple[float, ...]
    reference_node_ids: tuple[str, ...]
    goal_coverage: float
    max_steps: int


@dataclass(frozen=True)
class EvaluationRow:
    """One method result on one held-out mission."""

    split: str
    scenario_id: str
    scenario_seed: int
    method: str
    success: bool
    coverage: float
    graph_cost: float
    penalized_cost: float
    selected_count: int
    online_time_s: float
    safe_action_evaluations: int
    shield_rejections: int
    policy_source: str
    total_delta_v: float
    min_clearance: float
    peak_input: float


@dataclass(frozen=True)
class FrozenMLPCritic:
    """Portable NumPy inference checkpoint for a fitted MLP critic."""

    feature_mean: tuple[float, ...]
    feature_scale: tuple[float, ...]
    target_mean: float
    target_scale: float
    target_min: float
    target_max: float
    coefs: tuple[tuple[tuple[float, ...], ...], ...]
    intercepts: tuple[tuple[float, ...], ...]

    def __call__(self, features: tuple[float, ...]) -> float:
        """Predict one action value without requiring scikit-learn online."""
        activation = (
            np.asarray(features, dtype=float)
            - np.asarray(self.feature_mean, dtype=float)
        ) / np.asarray(self.feature_scale, dtype=float)
        for layer_index, (weights, bias) in enumerate(
            zip(self.coefs, self.intercepts)
        ):
            activation = (
                activation @ np.asarray(weights, dtype=float)
                + np.asarray(bias, dtype=float)
            )
            if layer_index < len(self.coefs) - 1:
                activation = np.maximum(activation, 0.0)
        normalized = float(np.ravel(activation)[0])
        prediction = self.target_mean + self.target_scale * normalized
        return max(self.target_min, min(self.target_max, prediction))

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable checkpoint payload."""
        return _jsonable(asdict(self))


def build_archived_graph(
    base: ExperimentConfig,
    config: SuperiorityConfig,
) -> ArchivedGraph:
    """Build and exhaustively archive a compact HCW-audited SOOA graph."""
    experiment = OfflinePlanningExperiment(replace(
        base,
        methods=(),
        adp_candidate_limit=config.candidate_limit,
        coverage_stop_ratio=config.goal_coverage,
        max_viewpoints=config.max_steps,
    ))
    reference = tuple(experiment._order_candidates_by_cw_cost(
        experiment._weighted_set_cover_candidates('set_cover_cw_tour'),
        'set_cover_cw_tour',
    ))
    candidates = tuple(experiment._adp_candidate_pool(reference))
    # Normalize the graph objective over targets visible from at least one
    # archived candidate.  Keeping unreachable mesh samples in the denominator
    # makes otherwise valid coverage goals impossible and biases every failure
    # penalty in the same direction.
    target_ids = tuple(sorted(experiment.inspectable_targets))
    target_index = {
        target_id: index for index, target_id in enumerate(target_ids)
    }
    candidate_by_id = {
        candidate.candidate_id: candidate for candidate in candidates
    }
    coverage_masks = tuple(
        _target_mask(
            experiment.visibility.visible_targets_by_candidate[
                candidate.candidate_id
            ],
            target_index,
        )
        for candidate in candidates
    )
    static_priorities = tuple(
        max(0.0, candidate.safety_margin) for candidate in candidates
    )
    base_target_weights = tuple(
        experiment.base_planner.target_area_by_id.get(target_id, 1.0)
        for target_id in target_ids
    )
    edges: list[ArchivedEdge] = []
    sources: tuple[str | None, ...] = (None, *candidate_by_id)
    for source_id in sources:
        if source_id is None:
            source_state = experiment.config.initial_state
        else:
            source = candidate_by_id[source_id]
            source_state = (
                source.position[0],
                source.position[1],
                source.position[2],
                0.0,
                0.0,
                0.0,
            )
        for target_id, target in candidate_by_id.items():
            if source_id == target_id:
                continue
            transfer = experiment._estimate_transfer_from_state(
                source_state,
                target,
            )
            states = tuple(
                state for _time, state, _control in transfer.trajectory
            )
            passive_margin, passive_safe = (
                experiment.base_planner._passive_safety_audit(states)
            )
            edges.append(ArchivedEdge(
                source_id=source_id,
                target_id=target_id,
                stage_cost=experiment._dynamic_transfer_cost(transfer),
                feasible=(
                    transfer.feasible
                    and passive_safe is not False
                ),
                min_clearance=transfer.min_clearance,
                peak_input=transfer.peak_requested_input,
                input_limit=experiment.config.max_acceleration,
                passive_margin=passive_margin,
                delta_v=transfer.delta_v,
                tracking_error=transfer.tracking_error,
            ))
    return ArchivedGraph(
        node_ids=tuple(candidate_by_id),
        coverage_masks=coverage_masks,
        static_priorities=static_priorities,
        target_ids=target_ids,
        base_target_weights=base_target_weights,
        edges=tuple(edges),
        node_positions=tuple(candidate.position for candidate in candidates),
    )


def save_archived_graph(graph: ArchivedGraph, path: Path) -> None:
    """Write a reusable graph archive without simulation-side plotting."""
    payload = {
        'node_ids': graph.node_ids,
        'coverage_masks': [hex(mask) for mask in graph.coverage_masks],
        'static_priorities': graph.static_priorities,
        'target_ids': graph.target_ids,
        'base_target_weights': graph.base_target_weights,
        'edges': [asdict(edge) for edge in graph.edges],
        'node_positions': graph.node_positions,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def load_archived_graph(path: Path) -> ArchivedGraph:
    """Load an HCW graph produced by :func:`save_archived_graph`."""
    payload = json.loads(path.read_text())
    return ArchivedGraph(
        node_ids=tuple(payload['node_ids']),
        coverage_masks=tuple(
            int(mask, 16) for mask in payload['coverage_masks']
        ),
        static_priorities=tuple(payload['static_priorities']),
        target_ids=tuple(payload['target_ids']),
        base_target_weights=tuple(payload['base_target_weights']),
        edges=tuple(ArchivedEdge(**edge) for edge in payload['edges']),
        node_positions=tuple(
            tuple(float(value) for value in position)
            for position in payload.get('node_positions', ())
        ),
    )


def build_scenarios(
    graph: ArchivedGraph,
    config: SuperiorityConfig,
    *,
    quick: bool = False,
) -> tuple[MissionScenario, ...]:
    """Generate disjoint mission splits with feasible paired incumbents."""
    requested = {
        'train': min(8, config.training_scenarios) if quick
        else config.training_scenarios,
        'validation': min(4, config.validation_scenarios) if quick
        else config.validation_scenarios,
        'test': min(8, config.test_scenarios) if quick
        else config.test_scenarios,
        'ood': min(6, config.ood_scenarios) if quick
        else config.ood_scenarios,
    }
    split_offsets = {
        'train': 0,
        'validation': 10000,
        'test': 20000,
        'ood': 30000,
    }
    scenarios: list[MissionScenario] = []
    for split, count in requested.items():
        accepted = 0
        attempt = 0
        while accepted < count:
            if attempt >= count * 200:
                raise RuntimeError(
                    f'could not generate {count} feasible {split} scenarios'
                )
            seed = config.base_seed + split_offsets[split] + attempt
            scenario = _make_scenario(graph, config, split, seed, accepted)
            attempt += 1
            if scenario is None:
                continue
            scenarios.append(scenario)
            accepted += 1
    return tuple(scenarios)


def run_study(
    base: ExperimentConfig,
    config: SuperiorityConfig,
    output_root: Path,
    run_id: str = '',
    *,
    quick: bool = False,
    graph_cache: Path | None = None,
    evaluation_splits: tuple[str, ...] = ('validation', 'test', 'ood'),
) -> Path:
    """Train on training missions and evaluate a frozen critic on held-out data."""
    study_id = run_id or f'adp_superiority_{datetime.now():%Y%m%d_%H%M%S}'
    result_dir = Path(output_root) / study_id
    raw_dir = result_dir / 'raw'
    config_dir = result_dir / 'config_snapshot'
    for directory in (
        raw_dir,
        config_dir,
        result_dir / 'figures',
        result_dir / 'rosbag',
        result_dir / 'videos',
    ):
        directory.mkdir(parents=True, exist_ok=True)

    archive_path = raw_dir / 'hcw_graph.json'
    graph_start = perf_counter()
    if graph_cache is not None and graph_cache.is_file():
        graph = load_archived_graph(graph_cache)
        graph_source = str(graph_cache)
    else:
        graph = build_archived_graph(base, config)
        save_archived_graph(graph, archive_path)
        graph_source = 'generated'
    graph_time = perf_counter() - graph_start
    if not archive_path.is_file():
        save_archived_graph(graph, archive_path)

    scenarios = build_scenarios(graph, config, quick=quick)
    (raw_dir / 'scenarios.json').write_text(json.dumps(
        [_jsonable(asdict(scenario)) for scenario in scenarios],
        indent=2,
        sort_keys=True,
    ))
    problems = {
        scenario.scenario_id: _problem_for_scenario(graph, scenario)
        for scenario in scenarios
    }
    training = tuple(
        problems[scenario.scenario_id]
        for scenario in scenarios
        if scenario.split == 'train'
    )
    training_config = _planner_config(
        config,
        episodes=(
            min(6, config.episodes_per_training_scenario)
            if quick else config.episodes_per_training_scenario
        ),
        critic_mode='frozen',
        enable_critic=True,
        enable_rollout=False,
        enable_reference_safeguard=False,
        local_passes=0,
    )
    trainer = AdvancedSafePlanner(training_config)
    training_start = perf_counter()
    if config.training_target == 'rollout':
        training_samples = tuple(
            sample
            for problem in training
            for sample in trainer.rollout_training_samples(problem)
        )
        training_target_label = 'shielded one-step rollout action value'
    elif config.training_target == 'exact':
        training_samples = tuple(
            sample
            for problem in training
            for sample in trainer.exact_training_samples(problem)
        )
        training_target_label = 'exact shielded Bellman action value'
    elif config.training_target == 'exact_advantage':
        training_samples = tuple(
            sample
            for problem in training
            for sample in trainer.exact_advantage_training_samples(problem)
        )
        training_target_label = 'exact shielded Bellman action advantage'
    else:
        raise ValueError(
            f'unsupported training target: {config.training_target}'
        )
    if config.critic_backend == 'ridge':
        checkpoint = _fit_ridge_critic(
            training_samples,
            config.ridge_regularization,
        )
        critic_predictor: FrozenMLPCritic | None = None
        predictor_payload: dict[str, object] = {
            'backend': 'ridge',
            'weights': checkpoint,
            'ridge_regularization': config.ridge_regularization,
        }
    elif config.critic_backend == 'mlp':
        critic_predictor = _fit_mlp_critic(training_samples, config)
        checkpoint = trainer.critic_weights
        predictor_payload = {
            'backend': 'mlp',
            'model': critic_predictor.to_dict(),
            'hidden_units': config.mlp_hidden_units,
            'regularization': config.mlp_regularization,
        }
    else:
        raise ValueError(
            f'unsupported critic backend: {config.critic_backend}'
        )
    training_time = perf_counter() - training_start
    checkpoint_path = raw_dir / 'critic_checkpoint.json'
    checkpoint_path.write_text(json.dumps({
        'feature_count': len(checkpoint),
        **predictor_payload,
        'training_scenarios': len(training),
        'episodes_per_scenario': training_config.training_episodes,
        'training_time_s': training_time,
        'training_sample_count': len(training_samples),
        'training_target': training_target_label,
        'ridge_regularization': config.ridge_regularization,
    }, indent=2, sort_keys=True))

    rows: list[EvaluationRow] = []
    for scenario in scenarios:
        if scenario.split not in evaluation_splits:
            continue
        problem = problems[scenario.scenario_id]
        for method in METHODS:
            rows.append(_evaluate_method(
                method,
                problem,
                scenario,
                config,
                checkpoint,
                critic_predictor,
            ))
    _write_rows(raw_dir / 'heldout_results.csv', rows)
    aggregate = _aggregate_rows(rows, training_time)
    _write_dict_rows(raw_dir / 'heldout_summary.csv', aggregate)
    superiority = _superiority_decision(rows)
    manifest = {
        'base_experiment_config': _jsonable(asdict(base)),
        'superiority_config': _jsonable(asdict(config)),
        'quick': quick,
        'evaluation_splits': evaluation_splits,
        'graph_source': graph_source,
        'graph_build_or_load_time_s': graph_time,
        'node_count': len(graph.node_ids),
        'target_count': len(graph.target_ids),
        'edge_count': len(graph.edges),
        'split_counts': {
            split: sum(scenario.split == split for scenario in scenarios)
            for split in ('train', 'validation', 'test', 'ood')
        },
        'training_time_s': training_time,
        'superiority': superiority,
    }
    (config_dir / 'study_manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )
    (result_dir / 'summary.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )
    (result_dir / 'summary.md').write_text(
        _summary_markdown(manifest, aggregate)
    )
    return result_dir


def _make_scenario(
    graph: ArchivedGraph,
    config: SuperiorityConfig,
    split: str,
    seed: int,
    sequence: int,
) -> MissionScenario | None:
    generator = random.Random(seed)
    ood = split == 'ood'
    if config.scenario_node_count > 0:
        requested_nodes = config.scenario_node_count + (
            config.ood_node_increment if ood else 0
        )
        if requested_nodes > len(graph.node_ids):
            return None
        available = generator.sample(
            graph.node_ids,
            requested_nodes,
        )
    else:
        dropout = (
            generator.uniform(0.15, 0.25)
            if ood else generator.uniform(0.0, 0.10)
        )
        available = [
            node_id for node_id in graph.node_ids
            if generator.random() >= dropout
        ]
    if len(available) < max(6, config.max_steps):
        return None
    weights = list(graph.base_target_weights)
    priority_fraction = generator.uniform(0.12, 0.20) if ood else generator.uniform(0.06, 0.14)
    priority_count = max(1, round(len(weights) * priority_fraction))
    multiplier = generator.uniform(5.0, 8.0) if ood else generator.uniform(2.0, 4.0)
    for index in generator.sample(range(len(weights)), priority_count):
        weights[index] *= multiplier
    edge_map = graph.edge_map()
    masks = dict(zip(graph.node_ids, graph.coverage_masks))
    reference = _greedy_reference(
        tuple(available),
        masks,
        tuple(weights),
        edge_map,
        config.goal_coverage,
        config.max_steps,
    )
    if not reference:
        return None
    scenario = MissionScenario(
        scenario_id=f'{split}_{sequence:03d}',
        split=split,
        seed=seed,
        available_node_ids=tuple(available),
        target_weights=tuple(weights),
        reference_node_ids=reference,
        goal_coverage=config.goal_coverage,
        max_steps=config.max_steps,
    )
    problem = _problem_for_scenario(graph, scenario)
    audit = AdvancedSafePlanner(_planner_config(
        config,
        episodes=0,
        critic_mode='frozen',
        enable_critic=False,
        enable_rollout=False,
        enable_reference_safeguard=True,
        local_passes=0,
    )).plan(problem)
    return scenario if audit.success else None


def _problem_for_scenario(
    graph: ArchivedGraph,
    scenario: MissionScenario,
) -> SafeGraphProblem:
    edge_map = graph.edge_map()
    available_node_ids = set(scenario.available_node_ids)
    node_data = {
        node_id: (mask, priority)
        for node_id, mask, priority in zip(
            graph.node_ids,
            graph.coverage_masks,
            graph.static_priorities,
        )
    }
    nodes = []
    successor_count = max(1, len(available_node_ids) - 1)
    for node_id in scenario.available_node_ids:
        outgoing_costs = [
            edge.stage_cost
            for (source_id, target_id), edge in edge_map.items()
            if source_id == node_id
            and target_id in available_node_ids
            and target_id != node_id
            and _edge_safe(edge)
        ]
        nodes.append(SafeGraphNode(
            node_id=node_id,
            coverage_mask=node_data[node_id][0],
            static_priority=node_data[node_id][1],
            outgoing_cost_min=(min(outgoing_costs) if outgoing_costs else 0.0),
            outgoing_cost_mean=(mean(outgoing_costs) if outgoing_costs else 0.0),
            feasible_out_degree=len(outgoing_costs) / successor_count,
        ))

    def evaluate_edge(source_id: str | None, target_id: str) -> SafeGraphEdge:
        return edge_map[(source_id, target_id)]

    return SafeGraphProblem(
        nodes=tuple(nodes),
        target_weights=scenario.target_weights,
        edge_evaluator=evaluate_edge,
        goal_coverage=scenario.goal_coverage,
        max_steps=scenario.max_steps,
        reference_node_ids=scenario.reference_node_ids,
    )


def _greedy_reference(
    available_node_ids: tuple[str, ...],
    masks: dict[str, int],
    target_weights: tuple[float, ...],
    edge_map: dict[tuple[str | None, str], SafeGraphEdge],
    goal: float,
    max_steps: int,
) -> tuple[str, ...]:
    selected: list[str] = []
    covered_mask = 0
    current: str | None = None
    remaining = set(available_node_ids)
    total_weight = max(sum(target_weights), 1.0e-12)
    while remaining and len(selected) < max_steps:
        if _mask_weight(covered_mask, target_weights) / total_weight >= goal:
            break
        candidates = []
        for node_id in remaining:
            edge = edge_map.get((current, node_id))
            if edge is None or not _edge_safe(edge):
                continue
            new_mask = masks[node_id] & ~covered_mask
            gain = _mask_weight(new_mask, target_weights) / total_weight
            if gain <= 0.0:
                continue
            score = gain / max(0.05, edge.stage_cost)
            candidates.append((score, gain, -edge.stage_cost, node_id))
        if not candidates:
            return ()
        _score, _gain, _cost, selected_id = max(candidates)
        selected.append(selected_id)
        covered_mask |= masks[selected_id]
        current = selected_id
        remaining.remove(selected_id)
    coverage = _mask_weight(covered_mask, target_weights) / total_weight
    return tuple(selected) if coverage >= goal else ()


def _evaluate_method(
    method: str,
    problem: SafeGraphProblem,
    scenario: MissionScenario,
    config: SuperiorityConfig,
    checkpoint: tuple[float, ...],
    critic_predictor: FrozenMLPCritic | None,
) -> EvaluationRow:
    method_config, weights = _method_config(method, config, checkpoint)
    planner = AdvancedSafePlanner(
        method_config,
        critic_weights=weights,
        critic_predictor=(
            critic_predictor
            if method in {'frozen_adp', 'frozen_adp_safeguard'}
            else None
        ),
    )
    start = perf_counter()
    plan = planner.plan(problem)
    elapsed = perf_counter() - start
    route_edges = []
    source_id: str | None = None
    for node_id in plan.node_ids:
        route_edges.append(problem.edge_evaluator(source_id, node_id))
        source_id = node_id
    shortfall = max(0.0, scenario.goal_coverage - plan.coverage_ratio)
    penalized = plan.total_cost + config.terminal_penalty * shortfall
    if not plan.success:
        penalized += 0.5 * config.terminal_penalty
    return EvaluationRow(
        split=scenario.split,
        scenario_id=scenario.scenario_id,
        scenario_seed=scenario.seed,
        method=method,
        success=plan.success,
        coverage=plan.coverage_ratio,
        graph_cost=plan.total_cost,
        penalized_cost=penalized,
        selected_count=len(plan.node_ids),
        online_time_s=elapsed,
        safe_action_evaluations=plan.safe_action_evaluations,
        shield_rejections=plan.shield_rejections,
        policy_source=plan.policy_source,
        total_delta_v=sum(edge.delta_v for edge in route_edges),
        min_clearance=min(
            (edge.min_clearance for edge in route_edges),
            default=math.nan,
        ),
        peak_input=max(
            (edge.peak_input for edge in route_edges),
            default=math.nan,
        ),
    )


def _method_config(
    method: str,
    config: SuperiorityConfig,
    checkpoint: tuple[float, ...],
) -> tuple[AdvancedPlannerConfig, tuple[float, ...] | None]:
    common = {
        'episodes': 0,
        'critic_mode': 'frozen',
        'local_passes': 0,
    }
    if method == 'frozen_adp':
        return _planner_config(
            config,
            **common,
            enable_critic=True,
            enable_rollout=False,
            enable_reference_safeguard=False,
        ), checkpoint
    if method == 'adaptive_rollout_adp':
        return _planner_config(
            config,
            **common,
            enable_critic=False,
            enable_rollout=False,
            enable_reference_safeguard=False,
            enable_adaptive_rollout=True,
        ), None
    if method == 'search_only':
        return _planner_config(
            config,
            **common,
            enable_critic=True,
            enable_rollout=False,
            enable_reference_safeguard=False,
        ), None
    if method == 'incumbent':
        return _planner_config(
            config,
            **common,
            enable_critic=False,
            enable_rollout=False,
            enable_reference_safeguard=True,
        ), None
    if method == 'rollout':
        return _planner_config(
            config,
            **common,
            enable_critic=False,
            enable_rollout=True,
            enable_reference_safeguard=True,
        ), None
    if method == 'local_search':
        return _planner_config(
            config,
            episodes=0,
            critic_mode='frozen',
            enable_critic=False,
            enable_rollout=False,
            enable_reference_safeguard=True,
            local_passes=config.local_improvement_passes,
        ), None
    if method == 'frozen_adp_safeguard':
        return _planner_config(
            config,
            **common,
            enable_critic=True,
            enable_rollout=False,
            enable_reference_safeguard=True,
        ), checkpoint
    raise ValueError(f'unsupported superiority-study method: {method}')


def _planner_config(
    config: SuperiorityConfig,
    *,
    episodes: int,
    critic_mode: str,
    enable_critic: bool,
    enable_rollout: bool,
    enable_reference_safeguard: bool,
    local_passes: int,
    enable_adaptive_rollout: bool = False,
) -> AdvancedPlannerConfig:
    return AdvancedPlannerConfig(
        horizon_steps=config.max_steps,
        goal_coverage=config.goal_coverage,
        branch_width=config.branch_width,
        candidate_pool_width=config.candidate_pool_width,
        lookahead_depth=config.lookahead_depth,
        training_episodes=episodes,
        learning_rate=config.learning_rate,
        exploration_rate=config.exploration_rate,
        terminal_penalty=config.terminal_penalty,
        action_cost=config.action_cost,
        cost_scale=config.cost_scale,
        random_seed=config.base_seed,
        reference_improvement_passes=local_passes,
        enable_critic=enable_critic,
        enable_rollout=enable_rollout,
        enable_adaptive_rollout=enable_adaptive_rollout,
        adaptive_rollout_depth=config.adaptive_rollout_depth,
        enable_reference_safeguard=enable_reference_safeguard,
        critic_mode=critic_mode,
    )


def _aggregate_rows(
    rows: list[EvaluationRow],
    training_time: float,
) -> list[dict[str, float | int | str]]:
    aggregates = []
    for split in ('validation', 'test', 'ood'):
        for method in METHODS:
            subset = [
                row for row in rows
                if row.split == split and row.method == method
            ]
            if not subset:
                continue
            times = sorted(row.online_time_s for row in subset)
            successful_costs = [
                row.graph_cost for row in subset if row.success
            ]
            successful_delta_v = [
                row.total_delta_v for row in subset if row.success
            ]
            aggregates.append({
                'split': split,
                'method': method,
                'n': len(subset),
                'success_rate': mean(row.success for row in subset),
                'mean_coverage': mean(row.coverage for row in subset),
                'mean_successful_cost': (
                    mean(successful_costs) if successful_costs else math.nan
                ),
                'median_successful_cost': (
                    median(successful_costs) if successful_costs else math.nan
                ),
                'mean_successful_delta_v': (
                    mean(successful_delta_v)
                    if successful_delta_v else math.nan
                ),
                'worst_min_clearance': min(
                    row.min_clearance for row in subset
                ),
                'peak_input': max(row.peak_input for row in subset),
                'mean_penalized_cost': mean(
                    row.penalized_cost for row in subset
                ),
                'median_online_time_s': median(times),
                'p95_online_time_s': times[
                    min(len(times) - 1, math.ceil(0.95 * len(times)) - 1)
                ],
                'mean_safe_action_evaluations': mean(
                    row.safe_action_evaluations for row in subset
                ),
                'training_time_s': (
                    training_time if method.startswith('frozen_adp') else 0.0
                ),
            })
    return aggregates


def _fit_ridge_critic(
    samples: tuple[tuple[tuple[float, ...], float], ...],
    regularization: float,
) -> tuple[float, ...]:
    """Fit a deterministic linear action-value critic to rollout targets."""
    if not samples:
        raise ValueError('ridge critic fitting requires training samples')
    if regularization < 0.0:
        raise ValueError('ridge regularization cannot be negative')
    features = np.asarray([sample[0] for sample in samples], dtype=float)
    targets = np.asarray([sample[1] for sample in samples], dtype=float)
    penalty = np.eye(features.shape[1], dtype=float) * regularization
    penalty[0, 0] = 0.0
    weights = np.linalg.solve(
        features.T @ features + penalty,
        features.T @ targets,
    )
    checkpoint = tuple(float(weight) for weight in weights)
    if not all(math.isfinite(weight) for weight in checkpoint):
        raise ValueError('ridge fitting produced a non-finite checkpoint')
    return checkpoint


def _fit_mlp_critic(
    samples: tuple[tuple[tuple[float, ...], float], ...],
    config: SuperiorityConfig,
) -> FrozenMLPCritic:
    """Fit a deterministic nonlinear critic and export NumPy-only weights."""
    if not samples:
        raise ValueError('MLP critic fitting requires training samples')
    try:
        from sklearn.neural_network import MLPRegressor
    except ImportError as error:
        raise RuntimeError(
            'the paper-study MLP backend requires scikit-learn'
        ) from error
    features = np.asarray([sample[0] for sample in samples], dtype=float)
    targets = np.asarray([sample[1] for sample in samples], dtype=float)
    feature_mean = features.mean(axis=0)
    feature_scale = features.std(axis=0)
    feature_scale[feature_scale < 1.0e-9] = 1.0
    target_mean = float(targets.mean())
    target_scale = float(targets.std())
    if target_scale < 1.0e-9:
        target_scale = 1.0
    normalized_features = (features - feature_mean) / feature_scale
    normalized_targets = (targets - target_mean) / target_scale
    model = MLPRegressor(
        hidden_layer_sizes=(
            config.mlp_hidden_units,
            config.mlp_hidden_units,
        ),
        activation='relu',
        solver='lbfgs',
        alpha=config.mlp_regularization,
        max_iter=700,
        random_state=config.base_seed,
        tol=1.0e-7,
    )
    model.fit(normalized_features, normalized_targets)
    return FrozenMLPCritic(
        feature_mean=tuple(float(value) for value in feature_mean),
        feature_scale=tuple(float(value) for value in feature_scale),
        target_mean=target_mean,
        target_scale=target_scale,
        target_min=float(targets.min()),
        target_max=float(targets.max()),
        coefs=tuple(
            tuple(tuple(float(value) for value in row) for row in matrix)
            for matrix in model.coefs_
        ),
        intercepts=tuple(
            tuple(float(value) for value in vector)
            for vector in model.intercepts_
        ),
    )


def _superiority_decision(rows: list[EvaluationRow]) -> dict[str, object]:
    proposed_method = 'adaptive_rollout_adp'
    test_rows = [row for row in rows if row.split == 'test']
    if not test_rows:
        return {
            'criterion': (
                'Adaptive rollout ADP must match local-search success and have '
                'an upper 95% paired penalized-cost confidence bound below zero '
                'on the held-out test split.'
            ),
            'comparisons': {},
            'demonstrated': False,
            'status': 'not assessed because the test split was not evaluated',
        }
    by_key = {
        (row.scenario_id, row.method): row for row in test_rows
    }
    scenario_ids = sorted({row.scenario_id for row in test_rows})
    comparisons = {}
    for baseline in ('search_only', 'incumbent', 'rollout', 'local_search'):
        differences = [
            by_key[(scenario_id, proposed_method)].penalized_cost
            - by_key[(scenario_id, baseline)].penalized_cost
            for scenario_id in scenario_ids
        ]
        lower, upper = _paired_bootstrap_interval(differences)
        comparisons[baseline] = {
            'mean_paired_penalized_cost_difference': mean(differences),
            'bootstrap_95_ci': [lower, upper],
            'adaptive_rollout_adp_win_rate': mean(
                value < 0.0 for value in differences
            ),
        }
    adp = [row for row in test_rows if row.method == proposed_method]
    local = [row for row in test_rows if row.method == 'local_search']
    demonstrated = bool(
        adp
        and mean(row.success for row in adp)
        >= mean(row.success for row in local)
        and comparisons['local_search']['bootstrap_95_ci'][1] < 0.0
    )
    return {
        'criterion': (
            'Adaptive rollout ADP must match local-search success and have an '
            'upper 95% paired penalized-cost confidence bound below zero on '
            'the held-out test split.'
        ),
        'proposed_method': proposed_method,
        'proposed_median_online_time_s': median(
            row.online_time_s for row in adp
        ),
        'local_search_median_online_time_s': median(
            row.online_time_s for row in local
        ),
        'comparisons': comparisons,
        'demonstrated': demonstrated,
    }


def _paired_bootstrap_interval(
    values: list[float],
    *,
    draws: int = 4000,
) -> tuple[float, float]:
    if not values:
        return math.nan, math.nan
    generator = random.Random(99173)
    means = sorted(
        mean(values[generator.randrange(len(values))] for _ in values)
        for _draw in range(draws)
    )
    return (
        means[math.floor(0.025 * (draws - 1))],
        means[math.ceil(0.975 * (draws - 1))],
    )


def _write_rows(path: Path, rows: list[EvaluationRow]) -> None:
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def _write_dict_rows(
    path: Path,
    rows: list[dict[str, float | int | str]],
) -> None:
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _summary_markdown(
    manifest: dict[str, object],
    aggregate: list[dict[str, float | int | str]],
) -> str:
    lines = [
        '# Safety-shielded rollout ADP held-out superiority study',
        '',
        f"- Nodes: {manifest['node_count']}",
        f"- Targets: {manifest['target_count']}",
        f"- Training time: {manifest['training_time_s']:.3f} s",
        f"- Superiority demonstrated: {manifest['superiority']['demonstrated']}",
        '',
        '| Split | Method | n | Success | Penalized cost | Median online time (s) |',
        '|---|---|---:|---:|---:|---:|',
    ]
    for row in aggregate:
        lines.append(
            f"| {row['split']} | {row['method']} | {row['n']} | "
            f"{row['success_rate']:.3f} | {row['mean_penalized_cost']:.3f} | "
            f"{row['median_online_time_s']:.6f} |"
        )
    return '\n'.join(lines) + '\n'


def _target_mask(target_ids: frozenset[str], index: dict[str, int]) -> int:
    mask = 0
    for target_id in target_ids:
        target_index = index.get(target_id)
        if target_index is not None:
            mask |= 1 << target_index
    return mask


def _mask_weight(mask: int, weights: tuple[float, ...]) -> float:
    return sum(
        weight for index, weight in enumerate(weights)
        if mask & (1 << index)
    )


def _edge_safe(edge: SafeGraphEdge) -> bool:
    return bool(
        edge.feasible
        and edge.min_clearance >= 0.0
        and edge.peak_input <= edge.input_limit + 1.0e-12
        and (edge.passive_margin is None or edge.passive_margin >= 0.0)
    )


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the frozen-ADP study."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--config',
        type=Path,
        default=Path(
            'src/orbinspect_guidance/config/offline_planning_experiment.yaml'
        ),
    )
    parser.add_argument('--output-root', type=Path, default=None)
    parser.add_argument('--run-id', default='')
    parser.add_argument('--graph-cache', type=Path, default=None)
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--candidate-limit', type=int, default=36)
    parser.add_argument('--goal-coverage', type=float, default=0.90)
    parser.add_argument('--max-steps', type=int, default=18)
    parser.add_argument('--branch-width', type=int, default=6)
    parser.add_argument('--candidate-pool-width', type=int, default=14)
    parser.add_argument('--lookahead-depth', type=int, default=2)
    parser.add_argument('--training-scenarios', type=int, default=24)
    parser.add_argument('--validation-scenarios', type=int, default=8)
    parser.add_argument('--test-scenarios', type=int, default=30)
    parser.add_argument('--ood-scenarios', type=int, default=20)
    parser.add_argument('--episodes-per-scenario', type=int, default=12)
    parser.add_argument('--learning-rate', type=float, default=0.025)
    parser.add_argument('--ridge-regularization', type=float, default=0.10)
    parser.add_argument(
        '--critic-backend',
        choices=('ridge', 'mlp'),
        default='mlp',
    )
    parser.add_argument('--mlp-hidden-units', type=int, default=48)
    parser.add_argument('--mlp-regularization', type=float, default=0.001)
    parser.add_argument(
        '--training-target',
        choices=('rollout', 'exact', 'exact_advantage'),
        default='rollout',
    )
    parser.add_argument('--scenario-node-count', type=int, default=0)
    parser.add_argument('--ood-node-increment', type=int, default=2)
    parser.add_argument('--base-seed', type=int, default=731)
    parser.add_argument('--adaptive-rollout-depth', type=int, default=1)
    parser.add_argument(
        '--splits',
        default='validation,test,ood',
        help='Comma-separated evaluation splits; training is never evaluated.',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the train-once, held-out ADP evaluation."""
    args = parse_args(argv)
    values = _load_yaml_config(args.config)
    if 'output_root' in values:
        values['output_root'] = Path(str(values['output_root']))
    if 'methods' in values:
        values['methods'] = tuple(
            str(method) for method in values['methods']
        )
    if 'initial_state' in values:
        values['initial_state'] = tuple(
            float(value) for value in values['initial_state']
        )
    base = ExperimentConfig(**values)
    output_root = args.output_root or base.output_root
    config = SuperiorityConfig(
        candidate_limit=args.candidate_limit,
        goal_coverage=args.goal_coverage,
        max_steps=args.max_steps,
        branch_width=args.branch_width,
        candidate_pool_width=args.candidate_pool_width,
        lookahead_depth=args.lookahead_depth,
        training_scenarios=args.training_scenarios,
        validation_scenarios=args.validation_scenarios,
        test_scenarios=args.test_scenarios,
        ood_scenarios=args.ood_scenarios,
        episodes_per_training_scenario=args.episodes_per_scenario,
        learning_rate=args.learning_rate,
        ridge_regularization=args.ridge_regularization,
        critic_backend=args.critic_backend,
        mlp_hidden_units=args.mlp_hidden_units,
        mlp_regularization=args.mlp_regularization,
        training_target=args.training_target,
        scenario_node_count=args.scenario_node_count,
        ood_node_increment=args.ood_node_increment,
        base_seed=args.base_seed,
        adaptive_rollout_depth=args.adaptive_rollout_depth,
    )
    result_dir = run_study(
        base,
        config,
        output_root,
        args.run_id,
        quick=args.quick,
        graph_cache=args.graph_cache,
        evaluation_splits=tuple(
            split.strip()
            for split in args.splits.split(',')
            if split.strip()
        ),
    )
    print(json.dumps({'result_dir': str(result_dir)}, indent=2))


if __name__ == '__main__':
    main()
