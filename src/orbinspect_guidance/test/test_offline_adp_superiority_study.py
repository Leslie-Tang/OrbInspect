import csv
from pathlib import Path

import pytest

from orbinspect_guidance.offline_adp_superiority_study import ArchivedEdge
from orbinspect_guidance.offline_adp_superiority_study import ArchivedGraph
from orbinspect_guidance.offline_adp_superiority_study import MissionScenario
from orbinspect_guidance.offline_adp_superiority_study import SuperiorityConfig
from orbinspect_guidance.offline_adp_superiority_study import _problem_for_scenario
from orbinspect_guidance.offline_adp_superiority_study import build_scenarios
from orbinspect_guidance.offline_adp_superiority_study import load_archived_graph
from orbinspect_guidance.offline_adp_superiority_study import run_study
from orbinspect_guidance.offline_adp_superiority_study import save_archived_graph
from orbinspect_guidance.offline_planning_experiment import ExperimentConfig


def test_archived_graph_round_trip(tmp_path: Path) -> None:
    graph = _graph()
    path = tmp_path / 'graph.json'

    save_archived_graph(graph, path)
    loaded = load_archived_graph(path)

    assert loaded == graph


def test_scenario_splits_are_disjoint_and_reproducible() -> None:
    config = _config()

    first = build_scenarios(_graph(), config, quick=True)
    second = build_scenarios(_graph(), config, quick=True)

    assert first == second
    assert len({scenario.scenario_id for scenario in first}) == len(first)
    split_seeds = {
        split: {scenario.seed for scenario in first if scenario.split == split}
        for split in ('train', 'validation', 'test', 'ood')
    }
    assert all(split_seeds.values())
    assert all(
        split_seeds[first_split].isdisjoint(split_seeds[second_split])
        for first_split in split_seeds
        for second_split in split_seeds
        if first_split != second_split
    )


def test_quick_study_freezes_training_before_heldout_evaluation(
    tmp_path: Path,
) -> None:
    graph_path = tmp_path / 'input_graph.json'
    save_archived_graph(_graph(), graph_path)

    result_dir = run_study(
        ExperimentConfig(output_root=tmp_path, geometry_backend='proxy'),
        _config(),
        tmp_path,
        'superiority_test',
        quick=True,
        graph_cache=graph_path,
    )

    with (result_dir / 'raw' / 'heldout_results.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert {row['split'] for row in rows} == {'validation', 'test', 'ood'}
    assert 'train' not in {row['split'] for row in rows}
    checkpoint = result_dir / 'raw' / 'critic_checkpoint.json'
    assert checkpoint.is_file()
    assert (result_dir / 'raw' / 'heldout_summary.csv').is_file()


def test_scenario_problem_populates_safe_outgoing_topology() -> None:
    graph = _graph()
    scenario = MissionScenario(
        scenario_id='test_topology',
        split='test',
        seed=1,
        available_node_ids=('n0', 'n1', 'n2'),
        target_weights=graph.base_target_weights,
        reference_node_ids=('n0', 'n1', 'n2'),
        goal_coverage=0.75,
        max_steps=3,
    )

    problem = _problem_for_scenario(graph, scenario)
    first = problem.nodes[0]

    assert first.outgoing_cost_min == 1.2
    assert first.outgoing_cost_mean == pytest.approx(1.3)
    assert first.feasible_out_degree == 1.0


def _config() -> SuperiorityConfig:
    return SuperiorityConfig(
        candidate_limit=10,
        goal_coverage=0.75,
        max_steps=4,
        branch_width=3,
        candidate_pool_width=6,
        lookahead_depth=1,
        training_scenarios=4,
        validation_scenarios=2,
        test_scenarios=3,
        ood_scenarios=2,
        episodes_per_training_scenario=2,
        local_improvement_passes=1,
        critic_backend='ridge',
    )


def _graph() -> ArchivedGraph:
    node_ids = tuple(f'n{index}' for index in range(10))
    masks = tuple(
        (1 << index)
        | (1 << ((index + 1) % 10))
        | (1 << ((index + 3) % 10))
        for index in range(10)
    )
    edges = []
    for source_id in (None, *node_ids):
        for target_id in node_ids:
            if source_id == target_id:
                continue
            source_index = -1 if source_id is None else int(source_id[1:])
            target_index = int(target_id[1:])
            edges.append(ArchivedEdge(
                source_id=source_id,
                target_id=target_id,
                stage_cost=1.0 + abs(target_index - source_index) / 5.0,
                feasible=True,
                min_clearance=2.0,
                peak_input=0.01,
                input_limit=0.02,
                passive_margin=1.0,
            ))
    return ArchivedGraph(
        node_ids=node_ids,
        coverage_masks=masks,
        static_priorities=(1.0,) * len(node_ids),
        target_ids=tuple(f't{index}' for index in range(10)),
        base_target_weights=(1.0,) * 10,
        edges=tuple(edges),
    )
