import csv
from pathlib import Path

from orbinspect_guidance.offline_planning_experiment import config_from_args
from orbinspect_guidance.offline_planning_experiment import ExperimentConfig
from orbinspect_guidance.offline_planning_experiment import GRAPH_ADP_VARIANTS
from orbinspect_guidance.offline_planning_experiment import OfflinePlanningExperiment
from orbinspect_guidance.offline_planning_experiment import parse_args
from orbinspect_guidance.offline_planning_plots import plot_coverage_comparison
from orbinspect_guidance.offline_planning_plots import plot_delta_v_comparison
from orbinspect_guidance.offline_planning_plots import (
    plot_energy_efficiency_comparison,
)
from orbinspect_guidance.offline_planning_plots import plot_peak_input_comparison
from orbinspect_guidance.offline_planning_plots import (
    plot_primary_trajectory_case_study,
)
from orbinspect_guidance.offline_planning_plots import plot_safety_comparison
from orbinspect_guidance.offline_validation_matrix import main as validation_matrix_main


def test_offline_planning_experiment_runs_baselines(tmp_path: Path) -> None:
    experiment = OfflinePlanningExperiment(_small_config(tmp_path))

    results = experiment.run()

    assert {result.method for result in results} == {
        'safe_graph_adp',
        'set_cover_cw_tour',
        'certified_graph_search',
        'proposed_safe_cw_nbv',
        'coverage_greedy',
        'safe_coverage_greedy',
        'fuel_greedy',
    }
    assert any(result.summary['final_coverage_ratio'] > 0.0 for result in results)
    assert any(result.trajectory for result in results)
    adp_result = next(
        result
        for result in results
        if result.method == 'safe_graph_adp'
    )
    assert adp_result.summary['adp_training_episodes'] == 8
    assert int(adp_result.summary['adp_safe_action_evaluations']) > 0


def test_offline_planning_experiment_runs_ablation_methods(tmp_path: Path) -> None:
    config = _small_config(tmp_path)
    experiment = OfflinePlanningExperiment(config.__class__(
        **{
            **config.__dict__,
            'methods': (
                'set_cover_cw_tour',
                'abl_no_transfer_cost',
                'abl_no_clearance_filter',
                'abl_no_input_check',
                'abl_unweighted_coverage',
            ),
        }
    ))

    results = experiment.run()

    assert {result.method for result in results} == {
        'set_cover_cw_tour',
        'abl_no_transfer_cost',
        'abl_no_clearance_filter',
        'abl_no_input_check',
        'abl_unweighted_coverage',
    }
    assert all('peak_requested_input' in result.summary for result in results)


def test_offline_planning_experiment_runs_graph_component_variants(
    tmp_path: Path,
) -> None:
    config = _small_config(tmp_path)
    experiment = OfflinePlanningExperiment(config.__class__(
        **{
            **config.__dict__,
            'methods': tuple(GRAPH_ADP_VARIANTS),
        }
    ))

    results = experiment.run()

    assert {result.method for result in results} == set(GRAPH_ADP_VARIANTS)
    result_by_method = {result.method: result for result in results}
    assert not result_by_method[
        'safe_graph_adp_critic_only'
    ].summary['adp_safeguard_enabled']
    assert not result_by_method[
        'safe_graph_adp_rollout'
    ].summary['adp_critic_enabled']
    assert result_by_method[
        'safe_graph_adp_local_search'
    ].summary['adp_local_improvement_enabled']


def test_offline_planning_experiment_runs_certified_graph_search(tmp_path: Path) -> None:
    experiment = OfflinePlanningExperiment(ExperimentConfig(
        output_root=tmp_path,
        run_id='certified_test',
        mesh_target_count=24,
        mesh_occlusion_max_triangles=0,
        candidate_radius=34.0,
        candidate_stride=3,
        coverage_threshold=0.10,
        coverage_stop_ratio=0.25,
        max_viewpoints=4,
        transfer_duration=90.0,
        integration_dt=5.0,
        max_acceleration=0.06,
        passive_safety_horizon=0.0,
        methods=('certified_graph_search',),
        certified_candidate_limit=8,
        certified_time_limit_s=3.0,
        certified_max_expansions=5000,
    ))

    result = experiment.run()[0]

    assert result.method == 'certified_graph_search'
    assert result.summary['certificate_status'] == 'optimal'
    assert result.summary['feasible']
    assert result.summary['certificate_candidate_count'] <= 8


def test_offline_planning_experiment_saves_outputs(tmp_path: Path) -> None:
    experiment = OfflinePlanningExperiment(_small_config(tmp_path))
    results = experiment.run()

    run_dir = experiment.save(results)

    assert (run_dir / 'raw' / 'method_comparison.csv').is_file()
    assert (run_dir / 'raw' / 'planner.csv').is_file()
    assert (run_dir / 'raw' / 'selected_sooas.csv').is_file()
    assert (run_dir / 'raw' / 'viewpoints.csv').is_file()
    assert (run_dir / 'raw' / 'trajectory.csv').is_file()
    assert (run_dir / 'raw' / 'attitude.csv').is_file()
    assert (run_dir / 'raw' / 'coverage.csv').is_file()
    assert not any((run_dir / 'figures').iterdir())

    plot_coverage_comparison(run_dir)
    plot_delta_v_comparison(run_dir)
    plot_energy_efficiency_comparison(run_dir)
    plot_safety_comparison(run_dir)
    plot_peak_input_comparison(run_dir)

    assert (run_dir / 'figures' / 'coverage_comparison.pdf').is_file()
    assert (run_dir / 'figures' / 'delta_v_comparison.pdf').is_file()
    assert (run_dir / 'figures' / 'energy_efficiency_comparison.pdf').is_file()
    assert (run_dir / 'figures' / 'safety_comparison.pdf').is_file()
    assert (run_dir / 'figures' / 'peak_input_comparison.pdf').is_file()
    assert (run_dir / 'summary.json').is_file()
    assert (run_dir / 'summary.md').is_file()

    with (run_dir / 'raw' / 'method_comparison.csv').open(newline='') as handle:
        method_row = next(csv.DictReader(handle))
    assert 'total_dynamic_cost' in method_row
    assert 'coverage_per_delta_v' in method_row
    assert 'certificate_status' in method_row
    assert 'selected_sooa_count' in method_row
    assert 'rho_min' in method_row
    assert 'trajectory_feasible' in method_row
    assert 'adp_training_episodes' in method_row
    assert 'adp_shield_rejections' in method_row
    assert 'adp_policy_source' in method_row
    assert 'adp_reference_graph_cost' in method_row
    assert 'adp_critic_enabled' in method_row
    assert 'adp_local_improvement_enabled' in method_row

    with (run_dir / 'raw' / 'planner.csv').open(newline='') as handle:
        planner_row = next(csv.DictReader(handle))
    assert 'transfer_dynamic_cost' in planner_row
    assert 'coverage_gain_area' in planner_row
    assert 'sooa_id' in planner_row
    assert 'selected_inspection_action' in planner_row
    assert 'adp_estimated_cost_to_go' in planner_row
    assert 'adp_safe_action_count' in planner_row

    with (run_dir / 'raw' / 'selected_sooas.csv').open(newline='') as handle:
        sooa_row = next(csv.DictReader(handle))
    assert 'passive_margin' in sooa_row
    assert 'visible_target_count' in sooa_row


def test_primary_trajectory_case_study_loads_archived_csvs(tmp_path: Path) -> None:
    raw_dir = tmp_path / 'raw'
    raw_dir.mkdir()
    _write_rows(raw_dir / 'trajectory.csv', [
        {'method': 'safe_graph_adp', 'rx': 0.0, 'ry': -35.0, 'rz': 10.0},
        {'method': 'safe_graph_adp', 'rx': 8.0, 'ry': -20.0, 'rz': 18.0},
        {'method': 'set_cover_cw_tour', 'rx': 0.0, 'ry': -35.0, 'rz': 10.0},
        {'method': 'set_cover_cw_tour', 'rx': -6.0, 'ry': -18.0, 'rz': 22.0},
    ])
    _write_rows(raw_dir / 'viewpoints.csv', [
        {
            'method': 'safe_graph_adp', 'sequence': 0,
            'viewpoint_x': 8.0, 'viewpoint_y': -20.0, 'viewpoint_z': 18.0,
        },
        {
            'method': 'set_cover_cw_tour', 'sequence': 0,
            'viewpoint_x': -6.0, 'viewpoint_y': -18.0, 'viewpoint_z': 22.0,
        },
    ])
    _write_rows(raw_dir / 'method_comparison.csv', [
        {
            'method': 'safe_graph_adp', 'selected_sooa_count': 1,
            'total_delta_v': 1.0, 'final_inspectable_coverage_ratio': 0.5,
            'min_clearance': 9.0, 'rho_min': 2.0,
            'adp_policy_source': 'reference_improved',
        },
        {
            'method': 'set_cover_cw_tour', 'selected_sooa_count': 1,
            'total_delta_v': 1.2, 'final_inspectable_coverage_ratio': 0.5,
            'min_clearance': 9.0, 'rho_min': 2.0,
            'adp_policy_source': '',
        },
    ])

    output_path = plot_primary_trajectory_case_study(tmp_path)

    assert output_path.is_file()
    assert output_path.with_suffix('.pdf').is_file()
    assert output_path.with_suffix('.svg').is_file()


def test_offline_planning_experiment_loads_yaml_config(tmp_path: Path) -> None:
    config_path = tmp_path / 'experiment.yaml'
    config_path.write_text(
        'offline_planning_experiment:\n'
        '  ros__parameters:\n'
        '    mesh_target_count: 24\n'
        '    methods: [proposed_safe_cw_nbv, fuel_greedy]\n'
        '    output_root: data/results\n'
    )

    args = parse_args([
        '--config', str(config_path),
        '--output-root', str(tmp_path),
        '--coverage-threshold', '0.2',
        '--run-id', 'yaml_exp',
    ])
    config = config_from_args(args)

    assert config.mesh_target_count == 24
    assert config.methods == ('proposed_safe_cw_nbv', 'fuel_greedy')
    assert config.coverage_threshold == 0.2
    assert config.output_root == tmp_path
    assert config.run_id == 'yaml_exp'


def test_offline_planning_experiment_loads_block_method_list(tmp_path: Path) -> None:
    config_path = tmp_path / 'experiment_block_list.yaml'
    config_path.write_text(
        'offline_planning_experiment:\n'
        '  ros__parameters:\n'
        '    methods:\n'
        '      - set_cover_cw_tour\n'
        '      - random_safe\n'
        '    output_root: data/results\n'
    )

    args = parse_args([
        '--config', str(config_path),
        '--output-root', str(tmp_path),
    ])
    config = config_from_args(args)

    assert config.methods == ('set_cover_cw_tour', 'random_safe')


def test_offline_validation_matrix_quick_run(tmp_path: Path) -> None:
    output_root = tmp_path / 'validation'

    validation_matrix_main([
        '--output-root', str(output_root),
        '--quick',
    ])

    assert (output_root / 'validation_matrix_summary.csv').is_file()
    with (output_root / 'validation_matrix_summary.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert {'target_density', 'candidate_density', 'ablation'} <= {
        row['study'] for row in rows
    }
    assert any(row['method'] == 'abl_no_transfer_cost' for row in rows)


def _small_config(tmp_path: Path) -> ExperimentConfig:
    return ExperimentConfig(
        output_root=tmp_path,
        run_id='experiment_test',
        mesh_target_count=36,
        mesh_occlusion_max_triangles=0,
        candidate_radius=28.0,
        candidate_stride=3,
        coverage_threshold=0.10,
        max_viewpoints=4,
        transfer_duration=12.0,
        integration_dt=3.0,
        max_acceleration=0.025,
        methods=(
            'safe_graph_adp',
            'set_cover_cw_tour',
            'certified_graph_search',
            'proposed_safe_cw_nbv',
            'coverage_greedy',
            'safe_coverage_greedy',
            'fuel_greedy',
        ),
        certified_candidate_limit=8,
        certified_time_limit_s=2.0,
        certified_max_expansions=2000,
        adp_candidate_limit=12,
        adp_branch_width=4,
        adp_candidate_pool_width=8,
        adp_lookahead_depth=2,
        adp_training_episodes=8,
        adp_oracle_node_limit=12,
    )


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
