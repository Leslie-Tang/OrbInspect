from pathlib import Path

from orbinspect_guidance.offline_coverage_planner import config_from_args
from orbinspect_guidance.offline_coverage_planner import OfflineCoveragePlanner
from orbinspect_guidance.offline_coverage_planner import OfflinePlannerConfig
from orbinspect_guidance.offline_coverage_planner import parse_args


def test_offline_planner_generates_visibility_and_plan(tmp_path: Path) -> None:
    planner = OfflineCoveragePlanner(_small_config(tmp_path))

    plan = planner.plan()

    assert plan.targets
    assert plan.candidates
    assert plan.visibility.visible_targets_by_candidate
    assert plan.selected_viewpoints
    assert plan.summary['final_coverage_ratio'] > 0.0
    assert plan.summary['total_delta_v'] > 0.0


def test_offline_planner_saves_paper_outputs(tmp_path: Path) -> None:
    planner = OfflineCoveragePlanner(_small_config(tmp_path))
    plan = planner.plan()

    run_dir = planner.save_plan(plan)

    assert (run_dir / 'raw' / 'targets.csv').is_file()
    assert (run_dir / 'raw' / 'candidate_viewpoints.csv').is_file()
    assert (run_dir / 'raw' / 'selected_viewpoints.csv').is_file()
    assert (run_dir / 'raw' / 'planner.csv').is_file()
    assert (run_dir / 'raw' / 'planned_trajectory.csv').is_file()
    assert (run_dir / 'raw' / 'coverage.csv').is_file()
    assert (run_dir / 'raw' / 'coverage_over_time.csv').is_file()
    assert (run_dir / 'figures' / 'targets_3d.png').is_file()
    assert (run_dir / 'figures' / 'planned_trajectory_3d.png').is_file()
    assert (run_dir / 'figures' / 'coverage_over_time.png').is_file()
    assert (run_dir / 'summary.json').is_file()


def test_offline_planner_loads_yaml_config(tmp_path: Path) -> None:
    config_path = tmp_path / 'offline_coverage_planner.yaml'
    config_path.write_text(
        'offline_coverage_planner:\n'
        '  ros__parameters:\n'
        '    target_spacing: 18.0\n'
        '    candidate_shell_offsets: [0.0]\n'
        '    coverage_threshold: 0.4\n'
        '    initial_state: [1.0, -30.0, 8.0, 0.0, 0.0, 0.0]\n'
        '    output_root: data/results\n'
    )

    args = parse_args([
        '--config', str(config_path),
        '--coverage-threshold', '0.5',
        '--output-root', str(tmp_path),
        '--run-id', 'yaml_test',
    ])
    config = config_from_args(args)

    assert config.target_spacing == 18.0
    assert config.candidate_shell_offsets == (0.0,)
    assert config.coverage_threshold == 0.5
    assert config.initial_state == (1.0, -30.0, 8.0, 0.0, 0.0, 0.0)
    assert config.output_root == tmp_path
    assert config.run_id == 'yaml_test'


def _small_config(tmp_path: Path) -> OfflinePlannerConfig:
    return OfflinePlannerConfig(
        target_spacing=18.0,
        candidate_radius=22.0,
        candidate_shell_offsets=(0.0,),
        candidate_stride=2,
        coverage_threshold=0.25,
        max_viewpoints=8,
        transfer_duration=20.0,
        integration_dt=2.0,
        max_acceleration=0.02,
        output_root=tmp_path,
        run_id='offline_test',
    )
