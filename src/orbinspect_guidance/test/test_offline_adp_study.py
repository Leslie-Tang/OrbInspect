import csv
from pathlib import Path

from orbinspect_guidance.offline_adp_study import build_study_cases
from orbinspect_guidance.offline_planning_experiment import ExperimentConfig
from orbinspect_guidance.offline_planning_plots import plot_adp_component_ablation
from orbinspect_guidance.offline_planning_plots import plot_adp_compute_tradeoff
from orbinspect_guidance.offline_planning_plots import plot_adp_initial_condition
from orbinspect_guidance.offline_planning_plots import plot_adp_oracle_gap
from orbinspect_guidance.offline_planning_plots import plot_adp_policy_costs
from orbinspect_guidance.offline_planning_plots import plot_adp_primary_tradeoff


def test_study_cases_cover_every_evidence_family() -> None:
    cases = build_study_cases(
        ExperimentConfig(
            output_root=Path('data/results'),
            geometry_backend='proxy',
        ),
        quick=True,
    )

    families = {case.family for case in cases}
    assert families == {
        'primary', 'components', 'oracle', 'robustness', 'compute'
    }
    assert len({case.case_id for case in cases}) == len(cases)


def test_oracle_cases_respect_exact_solver_limit() -> None:
    cases = build_study_cases(ExperimentConfig(), quick=True)

    oracle_cases = [case for case in cases if case.family == 'oracle']
    assert oracle_cases
    assert all(
        case.config.adp_candidate_limit
        <= case.config.adp_oracle_node_limit
        for case in oracle_cases
    )


def test_each_adp_study_figure_has_a_standalone_function(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / 'raw'
    raw_dir.mkdir()
    common = {
        'case_id': 'case',
        'case_label': 'case',
        'run_dir': 'case',
        'case_elapsed_s': 1.0,
        'random_seed': 7,
        'initial_x': 0.0,
        'initial_y': -35.0,
        'initial_z': 10.0,
        'mesh_target_count': 24,
        'candidate_limit': 8,
        'branch_width': 2,
        'candidate_pool_width': 4,
        'lookahead_depth': 2,
        'training_episodes': 20,
        'coverage': 0.98,
        'raw_coverage': 0.98,
        'coverage_success': True,
        'feasible': True,
        'total_delta_v': 10.0,
        'min_clearance': 2.0,
        'passive_margin': 1.0,
        'peak_input': 0.01,
        'selected_count': 4,
        'planning_time': 3.0,
        'graph_cost': 40.0,
        'policy_source': 'reference_improved',
        'learned_graph_cost': 55.0,
        'rollout_graph_cost': 43.0,
        'reference_graph_cost': 45.0,
        'improved_reference_graph_cost': 40.0,
        'incumbent_improvement': 5.0,
        'exact_cost': '',
        'optimality_gap': '',
        'exact_expansions': '',
        'td_updates': 20,
        'mean_absolute_td_error': 2.0,
        'shield_rejections': 3,
        'safe_action_evaluations': 12,
        'critic_enabled': True,
        'rollout_enabled': True,
        'safeguard_enabled': True,
        'local_improvement_enabled': True,
    }
    rows = [
        {**common, 'family': 'primary', 'method': 'safe_graph_adp'},
        {
            **common,
            'family': 'primary',
            'method': 'set_cover_cw_tour',
            'total_delta_v': 12.0,
            'selected_count': 5,
        },
        {
            **common,
            'family': 'oracle',
            'method': 'safe_graph_adp',
            'optimality_gap': 0.0,
            'exact_expansions': 23,
        },
        {**common, 'family': 'compute', 'method': 'safe_graph_adp'},
        {
            **common,
            'family': 'robustness',
            'case_id': 'robustness_ic0',
            'method': 'safe_graph_adp',
        },
        {
            **common,
            'family': 'robustness',
            'case_id': 'robustness_ic0',
            'method': 'set_cover_cw_tour',
            'total_delta_v': 12.0,
        },
        {
            **common,
            'family': 'components',
            'method': 'set_cover_cw_tour',
            'total_delta_v': 12.0,
        },
        {
            **common,
            'family': 'components',
            'method': 'safe_graph_adp',
        },
    ]
    with (raw_dir / 'adp_study_runs.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    paths = (
        plot_adp_primary_tradeoff(tmp_path),
        plot_adp_policy_costs(tmp_path),
        plot_adp_component_ablation(tmp_path),
        plot_adp_oracle_gap(tmp_path),
        plot_adp_compute_tradeoff(tmp_path),
        plot_adp_initial_condition(tmp_path),
    )

    assert all(path.is_file() for path in paths)
    assert all(path.with_suffix('.pdf').is_file() for path in paths)
