from orbinspect_guidance.advanced_safe_planner import AdvancedPlannerConfig
from orbinspect_guidance.advanced_safe_planner import AdvancedSafePlanner
from orbinspect_guidance.advanced_safe_planner import SafeGraphEdge
from orbinspect_guidance.advanced_safe_planner import SafeGraphNode
from orbinspect_guidance.advanced_safe_planner import SafeGraphProblem
import pytest


def _required_planner(depth: int = 1, **overrides) -> AdvancedSafePlanner:
    settings = dict(
        horizon_steps=6,
        goal_coverage=0.0,
        branch_width=6,
        candidate_pool_width=6,
        lookahead_depth=3,
        training_episodes=0,
        action_cost=0.0,
        enable_critic=False,
        enable_rollout=False,
        enable_adaptive_rollout=True,
        adaptive_rollout_depth=depth,
        enable_reference_safeguard=False,
        reference_improvement_passes=0,
    )
    settings.update(overrides)
    return AdvancedSafePlanner(AdvancedPlannerConfig(**settings))


def _directed_required_problem(nodes, costs, *, required_mask, max_steps=6):
    def evaluate(source_id, target_id):
        cost = costs.get((source_id, target_id))
        return SafeGraphEdge(
            source_id=source_id,
            target_id=target_id,
            stage_cost=cost if cost is not None else 100.0,
            feasible=cost is not None,
            min_clearance=1.0 if cost is not None else -1.0,
        )

    target_count = max(required_mask.bit_length(), *(n.coverage_mask.bit_length() for n in nodes))
    return SafeGraphProblem(
        nodes=nodes,
        target_weights=(1.0,) * target_count,
        edge_evaluator=evaluate,
        goal_coverage=0.0,
        max_steps=max_steps,
        required_target_mask=required_mask,
        goal_mode='required',
    )


def test_required_completion_can_succeed_below_global_coverage_threshold() -> None:
    problem = _directed_required_problem(
        (SafeGraphNode('key', 0b01), SafeGraphNode('background', 0b10)),
        {(None, 'key'): 2.0, (None, 'background'): 0.1, ('key', 'background'): 0.1},
        required_mask=0b01,
    )
    problem = replace(problem, target_weights=(1.0, 9.0), goal_coverage=0.8)
    planner = _required_planner()

    for plan in (planner.base_policy_plan(problem), planner.plan(problem)):
        assert plan.success
        assert plan.node_ids == ('key',)
        assert plan.coverage_ratio == pytest.approx(0.1)
        assert plan.required_target_count == plan.required_covered_count == 1
        assert plan.missing_required_target_mask == 0
        assert plan.termination_reason == 'complete'
    assert planner.solve_exact(problem).total_cost == 2.0

    # Legacy coverage+mask and the explicit hybrid goal preserve conjunction.
    for mode in ('coverage', 'hybrid'):
        conjunction = replace(problem, goal_mode=mode)
        plan = planner.plan(conjunction)
        assert plan.success
        assert plan.node_ids == ('key', 'background')
        assert plan.coverage_ratio == 1.0


def test_high_global_coverage_does_not_hide_a_missing_required_item() -> None:
    problem = _directed_required_problem(
        (SafeGraphNode('background', 0b01), SafeGraphNode('key', 0b10)),
        {(None, 'background'): 1.0},
        required_mask=0b10,
    )
    problem = replace(problem, target_weights=(9.0, 1.0))
    planner = _required_planner()
    base = planner.base_policy_plan(problem)

    assert base.coverage_ratio == pytest.approx(0.9)
    assert not base.success
    assert base.required_covered_count == 0
    assert base.missing_required_target_mask == 0b10
    assert base.termination_reason == 'base_completion_failed'
    assert not planner.solve_exact(problem).feasible


@pytest.mark.parametrize('policy', ['base', 'adaptive', 'learned', 'suffix', 'reference'])
def test_required_missions_preserve_zero_gain_transit_connectors(policy) -> None:
    problem = _directed_required_problem(
        (SafeGraphNode('transit', 0), SafeGraphNode('key', 0b1)),
        {(None, 'transit'): 1.0, ('transit', 'key'): 2.0},
        required_mask=0b1,
        max_steps=2,
    )
    problem = replace(problem, reference_node_ids=('transit', 'key'))
    options = {}
    if policy == 'learned':
        options = dict(enable_adaptive_rollout=False, enable_critic=True)
    elif policy == 'suffix':
        options = dict(enable_adaptive_rollout=False, enable_rollout=True)
    elif policy == 'reference':
        options = dict(enable_adaptive_rollout=False, enable_reference_safeguard=True,
                       reference_improvement_passes=2)
    planner = _required_planner(**options)
    plan = planner.base_policy_plan(problem) if policy == 'base' else planner.plan(problem)

    assert plan.success
    assert plan.node_ids == ('transit', 'key')
    assert plan.decisions[0].new_target_mask == 0
    assert plan.total_cost == 3.0
    assert planner.solve_exact(problem).total_cost == 3.0


def test_failed_base_completion_is_not_an_infeasibility_certificate() -> None:
    problem = _directed_required_problem(
        (SafeGraphNode('transit', 0), SafeGraphNode('trap', 0b01),
         SafeGraphNode('viable', 0b01), SafeGraphNode('last', 0b10)),
        {(None, 'transit'): 1.0, ('transit', 'trap'): 0.1,
         ('transit', 'viable'): 2.0, ('viable', 'last'): 2.0},
        required_mask=0b11,
        max_steps=3,
    )
    shallow = _required_planner(depth=1)
    base = shallow.base_policy_plan(problem)
    adp1 = shallow.plan(problem)
    exact = shallow.solve_exact(problem)
    adp2 = _required_planner(depth=2).plan(problem)

    assert base.node_ids == ('transit', 'trap')
    assert base.termination_reason == 'base_completion_failed'
    assert not base.success
    assert not adp1.success
    assert adp1.termination_reason == 'no_certified_completion'
    assert exact.feasible
    assert exact.node_ids == ('transit', 'viable', 'last')
    assert adp2.success
    assert adp2.total_cost == exact.total_cost == 5.0


@pytest.mark.parametrize('depth', [1, 2, 3])
def test_required_adp_respects_successful_base_cost_bound(depth) -> None:
    problem = replace(_two_step_problem(), goal_mode='required',
                      goal_coverage=0.0, required_target_mask=0b11)
    planner = _required_planner(depth=depth)
    base = planner.base_policy_plan(problem)
    plan = planner.plan(problem)
    exact = planner.solve_exact(problem)

    assert base.success and plan.success and exact.feasible
    assert exact.total_cost <= plan.total_cost <= base.total_cost
    assert len(plan.node_ids) == len(set(plan.node_ids))
    assert len(plan.node_ids) <= problem.max_steps


@pytest.mark.parametrize('changes', [
    dict(goal_mode='required', required_target_mask=0),
    dict(goal_mode='hybrid', required_target_mask=0),
    dict(goal_mode='required', required_target_mask=-1),
    dict(goal_mode='required', required_target_mask=0b100),
    dict(goal_mode='unknown', required_target_mask=0b01),
    dict(goal_mode='coverage', goal_coverage=0.0),
    dict(goal_mode='hybrid', goal_coverage=0.0, required_target_mask=0b01),
])
def test_required_goal_validation_rejects_ambiguous_or_invalid_tasks(changes) -> None:
    with pytest.raises(ValueError):
        _required_planner().plan(replace(_two_step_problem(), **changes))


def test_graph_adp_prefers_lower_long_horizon_cost() -> None:
    problem = _two_step_problem()
    planner = AdvancedSafePlanner(AdvancedPlannerConfig(
        horizon_steps=2,
        goal_coverage=1.0,
        branch_width=3,
        candidate_pool_width=3,
        lookahead_depth=2,
        training_episodes=0,
        action_cost=0.0,
        oracle_node_limit=6,
    ))

    plan = planner.plan(problem)
    exact = planner.solve_exact(problem)

    assert planner.available
    assert plan.node_ids == ('b', 'c')
    assert plan.success
    assert plan.total_cost == 5.0
    assert exact.node_ids == ('b', 'c')
    assert exact.total_cost == plan.total_cost


def test_graph_adp_shield_rejects_unsafe_low_cost_edge() -> None:
    nodes = (
        SafeGraphNode('unsafe', 0b1),
        SafeGraphNode('safe', 0b1),
    )

    def edge_evaluator(source_id: str | None, target_id: str) -> SafeGraphEdge:
        del source_id
        return SafeGraphEdge(
            source_id=None,
            target_id=target_id,
            stage_cost=0.1 if target_id == 'unsafe' else 5.0,
            feasible=target_id == 'safe',
            min_clearance=-0.1 if target_id == 'unsafe' else 1.0,
            peak_input=0.01,
            input_limit=0.02,
        )

    planner = AdvancedSafePlanner(AdvancedPlannerConfig(
        horizon_steps=1,
        goal_coverage=1.0,
        branch_width=2,
        candidate_pool_width=2,
        lookahead_depth=1,
        training_episodes=0,
        action_cost=0.0,
    ))
    plan = planner.plan(SafeGraphProblem(
        nodes=nodes,
        target_weights=(1.0,),
        edge_evaluator=edge_evaluator,
        goal_coverage=1.0,
        max_steps=1,
    ))

    assert plan.node_ids == ('safe',)
    assert plan.shield_rejections >= 1
    assert plan.success


def test_graph_adp_requires_mandatory_targets_beyond_coverage_goal() -> None:
    nodes = (
        SafeGraphNode('bulk', 0b011),
        SafeGraphNode('required', 0b100),
    )

    def edge_evaluator(source_id: str | None, target_id: str) -> SafeGraphEdge:
        return SafeGraphEdge(
            source_id=source_id,
            target_id=target_id,
            stage_cost=1.0,
            feasible=True,
            min_clearance=1.0,
            peak_input=0.01,
            input_limit=0.02,
        )

    planner = AdvancedSafePlanner(AdvancedPlannerConfig(
        horizon_steps=2,
        goal_coverage=2.0 / 3.0,
        branch_width=2,
        candidate_pool_width=2,
        lookahead_depth=1,
        training_episodes=0,
        action_cost=0.0,
        enable_critic=False,
        enable_rollout=False,
        enable_adaptive_rollout=True,
        enable_reference_safeguard=False,
        reference_improvement_passes=0,
    ))
    plan = planner.plan(SafeGraphProblem(
        nodes=nodes,
        target_weights=(1.0, 1.0, 1.0),
        edge_evaluator=edge_evaluator,
        goal_coverage=2.0 / 3.0,
        max_steps=2,
        required_target_mask=0b100,
    ))

    covered_mask = 0
    for decision in plan.decisions:
        covered_mask |= decision.new_target_mask
    assert plan.success
    assert len(plan.node_ids) == 2
    assert covered_mask & 0b100


def test_graph_adp_rejects_unknown_required_target() -> None:
    problem = _two_step_problem()
    invalid_problem = SafeGraphProblem(
        nodes=problem.nodes,
        target_weights=problem.target_weights,
        edge_evaluator=problem.edge_evaluator,
        goal_coverage=problem.goal_coverage,
        max_steps=problem.max_steps,
        reference_node_ids=problem.reference_node_ids,
        required_target_mask=1 << len(problem.target_weights),
    )

    with pytest.raises(ValueError, match='required target mask'):
        AdvancedSafePlanner(AdvancedPlannerConfig()).plan(invalid_problem)


def test_graph_adp_training_is_deterministic() -> None:
    config = AdvancedPlannerConfig(
        horizon_steps=2,
        goal_coverage=1.0,
        branch_width=3,
        candidate_pool_width=3,
        lookahead_depth=2,
        training_episodes=12,
        random_seed=19,
        action_cost=0.0,
    )

    first = AdvancedSafePlanner(config).plan(_two_step_problem())
    second = AdvancedSafePlanner(config).plan(_two_step_problem())

    assert first.node_ids == second.node_ids
    assert first.critic_weights == second.critic_weights
    assert first.mean_absolute_td_error == second.mean_absolute_td_error


def test_frozen_critic_uses_checkpoint_without_test_time_updates() -> None:
    training_config = AdvancedPlannerConfig(
        horizon_steps=2,
        goal_coverage=1.0,
        branch_width=3,
        candidate_pool_width=3,
        lookahead_depth=1,
        training_episodes=12,
        random_seed=23,
        action_cost=0.0,
        reference_improvement_passes=0,
        enable_rollout=False,
        enable_reference_safeguard=False,
    )
    trainer = AdvancedSafePlanner(training_config)
    checkpoint = trainer.fit_critic((_two_step_problem(),))
    frozen = AdvancedSafePlanner(
        AdvancedPlannerConfig(
            horizon_steps=2,
            goal_coverage=1.0,
            branch_width=3,
            candidate_pool_width=3,
            lookahead_depth=1,
            training_episodes=99,
            action_cost=0.0,
            reference_improvement_passes=0,
            enable_rollout=False,
            enable_reference_safeguard=False,
            critic_mode='frozen',
        ),
        critic_weights=checkpoint,
    )

    plan = frozen.plan(_two_step_problem())

    assert plan.critic_weights == checkpoint
    assert plan.training_episodes == 0
    assert plan.td_update_count == 0


def test_critic_checkpoint_dimension_is_validated() -> None:
    with pytest.raises(ValueError, match='checkpoint'):
        AdvancedSafePlanner(
            AdvancedPlannerConfig(critic_mode='frozen'),
            critic_weights=(1.0, 2.0),
        )


def test_exact_advantage_targets_preserve_zero_cost_optimal_actions() -> None:
    planner = AdvancedSafePlanner(AdvancedPlannerConfig(
        horizon_steps=2,
        goal_coverage=1.0,
        branch_width=3,
        candidate_pool_width=3,
        lookahead_depth=0,
        training_episodes=0,
        action_cost=0.0,
        oracle_node_limit=6,
    ))

    samples = planner.exact_advantage_training_samples(_two_step_problem())
    targets = [target for _features, target in samples]

    assert samples
    assert min(targets) == pytest.approx(0.0)
    assert all(target >= -1.0e-12 for target in targets)
    assert any(target > 0.0 for target in targets)


def test_graph_adp_safeguard_is_no_worse_than_reference() -> None:
    base_problem = _two_step_problem()
    problem = SafeGraphProblem(
        nodes=base_problem.nodes,
        target_weights=base_problem.target_weights,
        edge_evaluator=base_problem.edge_evaluator,
        goal_coverage=base_problem.goal_coverage,
        max_steps=base_problem.max_steps,
        reference_node_ids=('b', 'c'),
    )
    planner = AdvancedSafePlanner(AdvancedPlannerConfig(
        horizon_steps=2,
        goal_coverage=1.0,
        branch_width=1,
        candidate_pool_width=3,
        lookahead_depth=1,
        training_episodes=0,
        action_cost=0.0,
        reference_improvement_passes=0,
    ))

    plan = planner.plan(problem)

    assert plan.success
    assert plan.total_cost <= 5.0
    assert plan.reference_total_cost == 5.0
    assert plan.incumbent_improvement is not None
    assert plan.incumbent_improvement >= 0.0
    assert plan.policy_source == 'rollout_adp'


def test_graph_adp_component_switches_isolate_policy_candidates() -> None:
    base_problem = _two_step_problem()
    rollout_problem = SafeGraphProblem(
        nodes=base_problem.nodes,
        target_weights=base_problem.target_weights,
        edge_evaluator=base_problem.edge_evaluator,
        goal_coverage=base_problem.goal_coverage,
        max_steps=base_problem.max_steps,
        reference_node_ids=('b', 'c'),
    )
    critic_only = AdvancedSafePlanner(AdvancedPlannerConfig(
        horizon_steps=2,
        goal_coverage=1.0,
        branch_width=3,
        candidate_pool_width=3,
        lookahead_depth=2,
        training_episodes=0,
        action_cost=0.0,
        reference_improvement_passes=0,
        enable_rollout=False,
        enable_reference_safeguard=False,
    )).plan(rollout_problem)
    rollout_only = AdvancedSafePlanner(AdvancedPlannerConfig(
        horizon_steps=2,
        goal_coverage=1.0,
        branch_width=3,
        candidate_pool_width=3,
        lookahead_depth=2,
        training_episodes=20,
        action_cost=0.0,
        reference_improvement_passes=0,
        enable_critic=False,
        enable_rollout=True,
        enable_reference_safeguard=True,
    )).plan(rollout_problem)

    assert critic_only.policy_source == 'learned_adp'
    assert critic_only.learned_total_cost == 5.0
    assert critic_only.reference_total_cost is None
    assert rollout_only.policy_source == 'rollout_adp'
    assert rollout_only.learned_total_cost is None
    assert rollout_only.training_episodes == 0
    assert rollout_only.td_update_count == 0


def test_graph_adp_local_search_can_be_run_without_critic_or_rollout() -> None:
    base_problem = _two_step_problem()
    problem = SafeGraphProblem(
        nodes=base_problem.nodes,
        target_weights=base_problem.target_weights,
        edge_evaluator=base_problem.edge_evaluator,
        goal_coverage=base_problem.goal_coverage,
        max_steps=base_problem.max_steps,
        reference_node_ids=('a', 'c'),
    )
    plan = AdvancedSafePlanner(AdvancedPlannerConfig(
        horizon_steps=2,
        goal_coverage=1.0,
        branch_width=3,
        candidate_pool_width=3,
        lookahead_depth=2,
        training_episodes=20,
        action_cost=0.0,
        reference_improvement_passes=2,
        enable_critic=False,
        enable_rollout=False,
        enable_reference_safeguard=True,
    )).plan(problem)

    assert plan.policy_source == 'reference_improved'
    assert plan.reference_total_cost == 101.0
    assert plan.total_cost == 100.0
    assert plan.local_improvement_enabled


def test_adaptive_rollout_is_a_standalone_viable_policy() -> None:
    plan = AdvancedSafePlanner(AdvancedPlannerConfig(
        horizon_steps=2,
        goal_coverage=1.0,
        branch_width=3,
        candidate_pool_width=3,
        training_episodes=0,
        action_cost=0.0,
        enable_critic=False,
        enable_rollout=False,
        enable_adaptive_rollout=True,
        adaptive_rollout_depth=2,
        enable_reference_safeguard=False,
        reference_improvement_passes=0,
    )).plan(_two_step_problem())

    assert plan.success
    assert plan.node_ids == ('b', 'c')
    assert plan.total_cost == 5.0
    assert plan.policy_source == 'adaptive_rollout_adp'
    assert plan.adaptive_rollout_enabled


def test_graph_adp_rejects_configuration_without_policy_candidate() -> None:
    with pytest.raises(ValueError, match='policy candidate'):
        AdvancedSafePlanner(AdvancedPlannerConfig(
            reference_improvement_passes=0,
            enable_critic=False,
            enable_rollout=False,
            enable_adaptive_rollout=False,
            enable_reference_safeguard=False,
        ))


def _two_step_problem() -> SafeGraphProblem:
    nodes = (
        SafeGraphNode('a', 0b01),
        SafeGraphNode('b', 0b01),
        SafeGraphNode('c', 0b10),
    )
    costs = {
        (None, 'a'): 1.0,
        (None, 'b'): 3.0,
        (None, 'c'): 50.0,
        ('a', 'b'): 1.0,
        ('a', 'c'): 100.0,
        ('b', 'a'): 1.0,
        ('b', 'c'): 2.0,
        ('c', 'a'): 50.0,
        ('c', 'b'): 50.0,
    }

    def edge_evaluator(source_id: str | None, target_id: str) -> SafeGraphEdge:
        return SafeGraphEdge(
            source_id=source_id,
            target_id=target_id,
            stage_cost=costs[(source_id, target_id)],
            feasible=True,
            min_clearance=2.0,
            peak_input=0.01,
            input_limit=0.02,
        )

    return SafeGraphProblem(
        nodes=nodes,
        target_weights=(1.0, 1.0),
        edge_evaluator=edge_evaluator,
        goal_coverage=1.0,
        max_steps=2,
    )
from dataclasses import replace
