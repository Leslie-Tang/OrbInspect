import pytest

from orbinspect_guidance.advanced_safe_planner import AdvancedPlannerConfig
from orbinspect_guidance.advanced_safe_planner import AdvancedSafePlanner
from orbinspect_guidance.advanced_safe_planner import SafeGraphEdge
from orbinspect_guidance.advanced_safe_planner import SafeGraphNode
from orbinspect_guidance.advanced_safe_planner import SafeGraphProblem


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
