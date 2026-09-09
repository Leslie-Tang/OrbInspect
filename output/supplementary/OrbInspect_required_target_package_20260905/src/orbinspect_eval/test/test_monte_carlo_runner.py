from orbinspect_eval.monte_carlo_runner import run_monte_carlo


def test_monte_carlo_runner_creates_summary(tmp_path) -> None:
    result_dir = run_monte_carlo(
        scenario='full_station',
        methods=['fixed_waypoints', 'greedy_nbv_safety_filter'],
        num_runs=2,
        seed=1,
        result_root=str(tmp_path),
    )

    assert (result_dir / 'summary_table.csv').exists()
    assert (result_dir / 'figures' / 'method_comparison.png').exists()
    assert (result_dir / 'fixed_waypoints_000' / 'summary.json').exists()
    assert (result_dir / 'greedy_nbv_safety_filter_001' / 'summary.json').exists()
