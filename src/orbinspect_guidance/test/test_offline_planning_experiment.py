import csv
from pathlib import Path

from orbinspect_guidance.offline_planning_experiment import config_from_args
from orbinspect_guidance.offline_planning_experiment import ExperimentConfig
from orbinspect_guidance.offline_planning_experiment import OfflinePlanningExperiment
from orbinspect_guidance.offline_planning_experiment import parse_args


def test_offline_planning_experiment_runs_baselines(tmp_path: Path) -> None:
    experiment = OfflinePlanningExperiment(_small_config(tmp_path))

    results = experiment.run()

    assert {result.method for result in results} == {
        'set_cover_cw_tour',
        'proposed_safe_cw_nbv',
        'coverage_greedy',
        'safe_coverage_greedy',
        'fuel_greedy',
    }
    assert any(result.summary['final_coverage_ratio'] > 0.0 for result in results)
    assert any(result.trajectory for result in results)


def test_offline_planning_experiment_saves_outputs(tmp_path: Path) -> None:
    experiment = OfflinePlanningExperiment(_small_config(tmp_path))
    results = experiment.run()

    run_dir = experiment.save(results)

    assert (run_dir / 'raw' / 'method_comparison.csv').is_file()
    assert (run_dir / 'raw' / 'planner.csv').is_file()
    assert (run_dir / 'raw' / 'viewpoints.csv').is_file()
    assert (run_dir / 'raw' / 'trajectory.csv').is_file()
    assert (run_dir / 'raw' / 'attitude.csv').is_file()
    assert (run_dir / 'raw' / 'coverage.csv').is_file()
    assert (run_dir / 'figures' / 'coverage_comparison.pdf').is_file()
    assert (run_dir / 'figures' / 'delta_v_comparison.pdf').is_file()
    assert (run_dir / 'figures' / 'energy_efficiency_comparison.pdf').is_file()
    assert (run_dir / 'figures' / 'safety_comparison.pdf').is_file()
    assert (run_dir / 'summary.json').is_file()
    assert (run_dir / 'summary.md').is_file()

    with (run_dir / 'raw' / 'method_comparison.csv').open(newline='') as handle:
        method_row = next(csv.DictReader(handle))
    assert 'total_dynamic_cost' in method_row
    assert 'coverage_per_delta_v' in method_row

    with (run_dir / 'raw' / 'planner.csv').open(newline='') as handle:
        planner_row = next(csv.DictReader(handle))
    assert 'transfer_dynamic_cost' in planner_row
    assert 'coverage_gain_area' in planner_row


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
            'set_cover_cw_tour',
            'proposed_safe_cw_nbv',
            'coverage_greedy',
            'safe_coverage_greedy',
            'fuel_greedy',
        ),
    )
