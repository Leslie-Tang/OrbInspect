"""Render offline-planning figures from saved result files."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use('Agg')
from matplotlib import pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Line3DCollection  # noqa: E402


Vector3 = tuple[float, float, float]

METHOD_COLORS = {
    'safe_graph_adp': '#0072B2',
    'safe_graph_adp_critic_only': '#8C8C8C',
    'safe_graph_adp_critic_safeguard': '#56B4E9',
    'safe_graph_adp_rollout': '#009E73',
    'safe_graph_adp_local_search': '#E69F00',
    'safe_graph_adp_no_local': '#7A6FAC',
    'set_cover_cw_tour': '#E69F00',
    'certified_graph_search': '#1B6B5A',
    'proposed_safe_cw_nbv': '#7884B4',
    'coverage_greedy': '#B64342',
    'safe_coverage_greedy': '#E28E2C',
    'distance_greedy': '#7BAA5B',
    'fuel_greedy': '#9A4D8E',
    'random_safe': '#767676',
}

METHOD_LABELS = {
    'safe_graph_adp': 'Complete graph policy',
    'safe_graph_adp_critic_only': 'Critic and lookahead only',
    'safe_graph_adp_critic_safeguard': 'Critic with incumbent safeguard',
    'safe_graph_adp_rollout': 'Rollout with incumbent safeguard',
    'safe_graph_adp_local_search': 'Local search with incumbent safeguard',
    'safe_graph_adp_no_local': 'Critic, rollout, and safeguard',
    'set_cover_cw_tour': 'Two-stage safe incumbent',
    'certified_graph_search': 'Certified graph optimum',
    'proposed_safe_cw_nbv': 'CW-NBV baseline',
    'coverage_greedy': 'Coverage greedy',
    'safe_coverage_greedy': 'Safe coverage greedy',
    'distance_greedy': 'Nearest NBV',
    'fuel_greedy': 'Fuel greedy',
    'random_safe': 'Random safe',
}

METHOD_LABELS_SHORT = {
    'safe_graph_adp': 'Full graph',
    'safe_graph_adp_critic_only': 'Critic only',
    'safe_graph_adp_critic_safeguard': 'Critic + base',
    'safe_graph_adp_rollout': 'Rollout + base',
    'safe_graph_adp_local_search': 'Local + base',
    'safe_graph_adp_no_local': 'API, no local',
    'set_cover_cw_tour': 'Incumbent',
    'certified_graph_search': 'Certified',
    'proposed_safe_cw_nbv': 'CW-NBV',
    'coverage_greedy': 'Coverage',
    'safe_coverage_greedy': 'Safe cov.',
    'distance_greedy': 'Nearest',
    'fuel_greedy': 'Fuel',
    'random_safe': 'Random',
    'abl_no_transfer_cost': 'No transfer',
    'abl_no_clearance_filter': 'No clearance',
    'abl_no_input_check': 'No input',
    'abl_unweighted_coverage': 'Unweighted',
}


def plot_targets_3d(result_dir: Path) -> Path:
    """Plot saved inspection targets and selected terminal viewpoints."""
    result_dir = Path(result_dir)
    targets = _read_csv(result_dir / 'raw' / 'targets.csv')
    selected = _read_csv(
        result_dir / 'raw' / 'selected_viewpoints.csv',
        allow_empty=True,
    )
    output_path = _figure_path(result_dir, 'targets_3d')

    _configure_style()
    figure = plt.figure(figsize=(7.2, 5.2))
    axis = figure.add_subplot(111, projection='3d')
    _draw_saved_geometry(axis, result_dir)
    target_points = [
        (float(row['px']), float(row['py']), float(row['pz']))
        for row in targets
    ]
    selected_points = [
        (float(row['x']), float(row['y']), float(row['z']))
        for row in selected
    ]
    axis.scatter(
        [point[0] for point in target_points],
        [point[1] for point in target_points],
        [point[2] for point in target_points],
        s=5,
        alpha=0.55,
        c='#0072B2',
        depthshade=False,
        label='inspection targets',
    )
    if selected_points:
        axis.scatter(
            [point[0] for point in selected_points],
            [point[1] for point in selected_points],
            [point[2] for point in selected_points],
            s=22,
            c='#D55E00',
            edgecolors='black',
            linewidths=0.25,
            depthshade=False,
            label='selected SOOA terminal poses',
        )
    _style_3d_axis(axis)
    _set_equal_3d_axes(axis, target_points, selected_points)
    axis.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, 1.02),
        ncol=2,
        frameon=False,
        handlelength=1.4,
    )
    figure.tight_layout()
    _save_figure(figure, output_path)
    plt.close(figure)
    return output_path


def plot_planned_trajectory_3d(result_dir: Path) -> Path:
    """Plot the saved HCW trajectory without rerunning the planner."""
    result_dir = Path(result_dir)
    samples = _read_csv(result_dir / 'raw' / 'planned_trajectory.csv')
    output_path = _figure_path(result_dir, 'planned_trajectory_3d')

    _configure_style()
    figure = plt.figure(figsize=(7.2, 5.2))
    axis = figure.add_subplot(111, projection='3d')
    _draw_saved_geometry(axis, result_dir)
    times = [float(row['time']) for row in samples]
    points = [
        (float(row['rx']), float(row['ry']), float(row['rz']))
        for row in samples
    ]
    axis.plot(
        [point[0] for point in points],
        [point[1] for point in points],
        [point[2] for point in points],
        color='#D55E00',
        linewidth=1.8,
        label='SOOA HCW trajectory',
        zorder=5,
    )
    stride = max(1, len(points) // 120)
    scatter = axis.scatter(
        [point[0] for point in points[::stride]],
        [point[1] for point in points[::stride]],
        [point[2] for point in points[::stride]],
        c=_normalized_values(times)[::stride],
        cmap='viridis',
        s=10,
        depthshade=False,
        label='time samples',
    )
    colorbar = figure.colorbar(scatter, ax=axis, shrink=0.62, pad=0.08)
    colorbar.set_label('normalized time')
    _style_3d_axis(axis)
    _set_equal_3d_axes(axis, points)
    axis.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, 1.02),
        ncol=2,
        frameon=False,
        handlelength=1.4,
    )
    figure.tight_layout()
    _save_figure(figure, output_path)
    plt.close(figure)
    return output_path


def plot_coverage_over_time(result_dir: Path) -> Path:
    """Plot coverage from the saved single-planner coverage CSV."""
    result_dir = Path(result_dir)
    timeline = _read_csv(result_dir / 'raw' / 'coverage_over_time.csv')
    output_path = _figure_path(result_dir, 'coverage_over_time')

    _configure_style()
    figure, axis = plt.subplots(figsize=(6.8, 3.6))
    times = [float(row['time']) for row in timeline]
    coverage = [float(row['coverage_ratio']) for row in timeline]
    axis.step(times, coverage, where='post', color='#0072B2', linewidth=2.0)
    axis.scatter(times, coverage, s=14, color='#0072B2', zorder=3)
    axis.set_xlabel('mission time [s]')
    axis.set_ylabel('coverage ratio')
    axis.set_ylim(0.0, 1.05)
    axis.spines['top'].set_visible(False)
    axis.spines['right'].set_visible(False)
    axis.grid(True, axis='y', color='#D9D9D9', linewidth=0.6)
    figure.tight_layout()
    _save_figure(figure, output_path)
    plt.close(figure)
    return output_path


def plot_coverage_comparison(result_dir: Path) -> Path:
    """Plot method coverage timelines from saved comparison CSV files."""
    result_dir = Path(result_dir)
    method_rows = _read_csv(result_dir / 'raw' / 'method_comparison.csv')
    coverage_rows = _read_csv(result_dir / 'raw' / 'coverage.csv')
    by_method: dict[str, list[dict[str, str]]] = {}
    for row in coverage_rows:
        by_method.setdefault(row['method'], []).append(row)
    output_path = _figure_path(result_dir, 'coverage_comparison')

    _configure_style()
    figure, axis = plt.subplots(figsize=(7.0, 4.0))
    for row in method_rows:
        method = row['method']
        timeline = by_method.get(method, [])
        if not timeline:
            continue
        final_raw = float(row['final_coverage_ratio'])
        final_inspectable = float(row['final_inspectable_coverage_ratio'])
        scale_factor = final_inspectable / max(final_raw, 1.0e-12)
        is_proposed = method == 'set_cover_cw_tour'
        axis.step(
            [float(item['time']) for item in timeline],
            [
                min(1.0, float(item['coverage_ratio']) * scale_factor)
                for item in timeline
            ],
            where='post',
            linewidth=2.5 if is_proposed else 1.65,
            color=METHOD_COLORS.get(method, '#4D4D4D'),
            alpha=1.0 if is_proposed else 0.76,
            label=_method_label(method),
        )
    axis.axhline(0.98, color='#272727', linestyle='--', linewidth=0.9, alpha=0.55)
    axis.text(
        0.99,
        0.955,
        '98% stop target',
        transform=axis.transAxes,
        ha='right',
        va='center',
        fontsize=8,
        color='#272727',
    )
    axis.set_xlabel('Mission time (s)')
    axis.set_ylabel('Inspectable area coverage')
    axis.set_ylim(0.0, 1.0)
    axis.grid(True, axis='y', color='#E1E1E1', linewidth=0.6)
    axis.spines['top'].set_visible(False)
    axis.spines['right'].set_visible(False)
    axis.legend(frameon=False, ncol=2, fontsize=8, loc='lower right')
    figure.tight_layout()
    _save_figure(figure, output_path)
    plt.close(figure)
    return output_path


def plot_delta_v_comparison(result_dir: Path) -> Path:
    """Plot total delta-v from a saved method-comparison CSV."""
    result_dir = Path(result_dir)
    return _plot_metric_bar(
        _read_csv(result_dir / 'raw' / 'method_comparison.csv'),
        _figure_path(result_dir, 'delta_v_comparison'),
        key='total_delta_v',
        xlabel=r'Total $\Delta v$ (m s$^{-1}$)',
    )


def plot_energy_efficiency_comparison(result_dir: Path) -> Path:
    """Plot delta-v per covered area from saved comparison metrics."""
    result_dir = Path(result_dir)
    return _plot_metric_bar(
        _read_csv(result_dir / 'raw' / 'method_comparison.csv'),
        _figure_path(result_dir, 'energy_efficiency_comparison'),
        key='delta_v_per_raw_coverage',
        xlabel=r'$\Delta v$ per covered area ratio (m s$^{-1}$)',
    )


def plot_safety_comparison(result_dir: Path) -> Path:
    """Plot minimum clearance from saved comparison metrics."""
    result_dir = Path(result_dir)
    return _plot_metric_bar(
        _read_csv(result_dir / 'raw' / 'method_comparison.csv'),
        _figure_path(result_dir, 'safety_comparison'),
        key='min_clearance',
        xlabel='Minimum clearance (m)',
        flag_infeasible=True,
    )


def plot_peak_input_comparison(result_dir: Path) -> Path:
    """Plot peak requested acceleration from saved comparison metrics."""
    result_dir = Path(result_dir)
    return _plot_metric_bar(
        _read_csv(result_dir / 'raw' / 'method_comparison.csv'),
        _figure_path(result_dir, 'peak_input_comparison'),
        key='peak_requested_input',
        xlabel='Peak requested input (m s$^{-2}$)',
    )


def plot_adp_primary_tradeoff(result_dir: Path) -> Path:
    """Plot coverage, effort, action count, and feasibility for the primary case."""
    result_dir = Path(result_dir)
    rows = _study_rows(result_dir, 'primary')
    output_path = _figure_path(result_dir, 'adp_primary_tradeoff')

    _configure_style()
    figure, axis = plt.subplots(figsize=(3.45, 3.05))
    annotation_offsets = {
        'safe_graph_adp': (4, 4),
        'set_cover_cw_tour': (4, 5),
        'safe_coverage_greedy': (4, 4),
        'fuel_greedy': (4, 4),
        'coverage_greedy': (-28, 5),
    }
    for row in rows:
        method = row['method']
        coverage = 100.0 * float(row['coverage'])
        delta_v = float(row['total_delta_v'])
        feasible = _as_bool(row['feasible'])
        marker = 'o' if feasible else 'X'
        axis.scatter(
            coverage,
            delta_v,
            s=54 if method == 'safe_graph_adp' else 38,
            marker=marker,
            color=METHOD_COLORS.get(method, '#767676'),
            edgecolor='#202020',
            linewidth=0.55,
            zorder=3,
            label=METHOD_LABELS_SHORT.get(method, method),
        )
        action_count = int(float(row['selected_count']))
        axis.annotate(
            f'n={action_count}',
            (coverage, delta_v),
            xytext=annotation_offsets.get(method, (4, 4)),
            textcoords='offset points',
            fontsize=6.7,
            color='#262626',
        )
    axis.axvline(
        98.0,
        color='#4D4D4D',
        linestyle='--',
        linewidth=0.8,
        alpha=0.7,
    )
    axis.set_xlabel('Inspectable coverage (%)')
    axis.set_ylabel(r'Cumulative $\Delta v$ (m s$^{-1}$)')
    axis.grid(True, color='#E5E5E5', linewidth=0.55)
    axis.set_axisbelow(True)
    axis.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, 1.19),
        ncol=2,
        fontsize=6.5,
        columnspacing=0.8,
        handletextpad=0.35,
    )
    figure.tight_layout()
    _save_figure(figure, output_path)
    plt.close(figure)
    return output_path


def plot_primary_trajectory_case_study(result_dir: Path) -> Path:
    """Compare the returned and incumbent trajectories from saved primary data."""
    result_dir = Path(result_dir)
    required_methods = ('safe_graph_adp', 'set_cover_cw_tour')
    trajectory_rows = _read_csv(result_dir / 'raw' / 'trajectory.csv')
    viewpoint_rows = _read_csv(result_dir / 'raw' / 'viewpoints.csv')
    comparison_rows = _read_csv(result_dir / 'raw' / 'method_comparison.csv')
    trajectories = {
        method: [
            (float(row['rx']), float(row['ry']), float(row['rz']))
            for row in trajectory_rows
            if row['method'] == method
        ]
        for method in required_methods
    }
    viewpoints = {
        method: [
            (
                float(row['viewpoint_x']),
                float(row['viewpoint_y']),
                float(row['viewpoint_z']),
            )
            for row in sorted(
                (
                    row for row in viewpoint_rows
                    if row['method'] == method
                ),
                key=lambda row: int(float(row['sequence'])),
            )
        ]
        for method in required_methods
    }
    metrics = {
        row['method']: row
        for row in comparison_rows
        if row['method'] in required_methods
    }
    missing = [
        method for method in required_methods
        if not trajectories[method] or not viewpoints[method] or method not in metrics
    ]
    if missing:
        raise ValueError(
            'primary trajectory case study is missing saved data for '
            + ', '.join(missing)
        )

    config_path = (
        result_dir
        / 'config_snapshot'
        / 'offline_planning_experiment_config.json'
    )
    if config_path.is_file():
        initial_state = json.loads(config_path.read_text()).get('initial_state', [])
    else:
        initial_state = []
    start = (
        tuple(float(value) for value in initial_state[:3])
        if len(initial_state) >= 3
        else trajectories['safe_graph_adp'][0]
    )
    output_path = _figure_path(result_dir, 'primary_trajectory_case_study')

    _configure_style()
    figure = plt.figure(figsize=(3.5, 3.65))
    axis = figure.add_subplot(111, projection='3d')
    _draw_saved_geometry(
        axis,
        result_dir,
        max_segments=7000,
        color='#56636A',
        linewidth=0.30,
        alpha=0.42,
    )
    plot_settings = {
        'set_cover_cw_tour': {
            'color': '#D89000',
            'linestyle': (0, (4.0, 2.0)),
            'linewidth': 1.25,
            'marker': '^',
            'marker_size': 15,
            'marker_face': 'white',
            'zorder': 5,
        },
        'safe_graph_adp': {
            'color': '#0072B2',
            'linestyle': '-',
            'linewidth': 1.85,
            'marker': 'o',
            'marker_size': 14,
            'marker_face': '#0072B2',
            'zorder': 7,
        },
    }
    route_handles = []
    for method in ('set_cover_cw_tour', 'safe_graph_adp'):
        points = trajectories[method]
        dwell_points = viewpoints[method]
        row = metrics[method]
        settings = plot_settings[method]
        source = row.get('adp_policy_source', '')
        method_label = (
            'Returned L+S route'
            if method == 'safe_graph_adp' and source == 'reference_improved'
            else METHOD_LABELS.get(method, method)
        )
        label = (
            f"{method_label}: {int(float(row['selected_sooa_count']))} SOOAs, "
            f"$\\Delta v$={float(row['total_delta_v']):.2f} m s$^{{-1}}$"
        )
        handle, = axis.plot(
            [point[0] for point in points],
            [point[1] for point in points],
            [point[2] for point in points],
            color=settings['color'],
            linestyle=settings['linestyle'],
            linewidth=settings['linewidth'],
            alpha=0.96,
            label=label,
            zorder=settings['zorder'],
        )
        route_handles.append(handle)
        axis.scatter(
            [point[0] for point in dwell_points],
            [point[1] for point in dwell_points],
            [point[2] for point in dwell_points],
            s=settings['marker_size'],
            marker=settings['marker'],
            facecolors=settings['marker_face'],
            edgecolors=settings['color'],
            linewidths=0.55,
            depthshade=False,
            zorder=settings['zorder'] + 1,
        )
        endpoint = points[-1]
        axis.scatter(
            [endpoint[0]],
            [endpoint[1]],
            [endpoint[2]],
            s=34,
            marker='X',
            c=settings['color'],
            edgecolors='white',
            linewidths=0.55,
            depthshade=False,
            zorder=10,
        )
    axis.scatter(
        [start[0]],
        [start[1]],
        [start[2]],
        s=48,
        marker='*',
        c='#159947',
        edgecolors='white',
        linewidths=0.6,
        depthshade=False,
        zorder=11,
    )
    _style_3d_axis(axis)
    _set_equal_3d_axes(
        axis,
        trajectories['safe_graph_adp'],
        trajectories['set_cover_cw_tour'],
    )
    axis.tick_params(axis='both', labelsize=6.2, pad=0)
    axis.xaxis.label.set_size(7)
    axis.yaxis.label.set_size(7)
    axis.set_zlabel('')
    axis.text2D(
        1.10,
        0.51,
        r'$z_{LVLH}$ [m]',
        transform=axis.transAxes,
        ha='center',
        va='center',
        rotation=90,
        fontsize=7,
    )
    axis.legend(
        handles=route_handles[::-1],
        loc='upper center',
        bbox_to_anchor=(0.5, 1.12),
        fontsize=6.1,
        handlelength=2.4,
        handletextpad=0.45,
        labelspacing=0.25,
    )
    adp_metrics = metrics['safe_graph_adp']
    incumbent_metrics = metrics['set_cover_cw_tour']
    adp_summary = (
        100.0 * float(adp_metrics['final_inspectable_coverage_ratio']),
        float(adp_metrics['min_clearance']),
        float(adp_metrics['rho_min']),
    )
    incumbent_summary = (
        100.0 * float(incumbent_metrics['final_inspectable_coverage_ratio']),
        float(incumbent_metrics['min_clearance']),
        float(incumbent_metrics['rho_min']),
    )
    shared_summary = all(
        abs(adp_value - incumbent_value) <= 1.0e-9
        for adp_value, incumbent_value in zip(adp_summary, incumbent_summary)
    )
    if shared_summary:
        summary_text = (
            f'Both: {adp_summary[0]:.2f}% coverage; '
            f'$d_{{min}}$={adp_summary[1]:.2f} m; '
            f'$\\rho_{{min}}$={adp_summary[2]:.2f} m'
        )
    else:
        summary_text = (
            f'Coverage: returned {adp_summary[0]:.2f}%; '
            f'incumbent {incumbent_summary[0]:.2f}%'
        )
    figure.text(
        0.5,
        0.018,
        summary_text,
        ha='center',
        va='bottom',
        fontsize=6.2,
        color='#303030',
    )
    figure.subplots_adjust(left=0.0, right=0.98, bottom=0.10, top=0.88)
    _save_figure(figure, output_path)
    plt.close(figure)
    return output_path


def plot_adp_policy_costs(result_dir: Path) -> Path:
    """Plot learned, rollout, incumbent, and returned graph costs."""
    result_dir = Path(result_dir)
    rows = _study_rows(result_dir, 'primary')
    adp_row = next(row for row in rows if row['method'] == 'safe_graph_adp')
    candidates = (
        ('Learned policy', 'learned_graph_cost', '#9ECAE1'),
        ('One-step rollout', 'rollout_graph_cost', '#6BAED6'),
        ('Safe incumbent', 'reference_graph_cost', '#F3C969'),
        ('Returned policy', 'graph_cost', '#0072B2'),
    )
    available = [
        (label, float(adp_row[key]), color)
        for label, key, color in candidates
        if adp_row.get(key, '') not in ('', None)
    ]
    output_path = _figure_path(result_dir, 'adp_policy_costs')

    _configure_style()
    figure, axis = plt.subplots(figsize=(3.45, 2.65))
    positions = list(range(len(available)))
    values = [item[1] for item in available]
    axis.barh(
        positions,
        values,
        color=[item[2] for item in available],
        edgecolor='#303030',
        linewidth=0.5,
        height=0.62,
    )
    axis.set_yticks(positions)
    axis.set_yticklabels([item[0] for item in available])
    axis.invert_yaxis()
    axis.set_xlabel('Audited graph objective')
    axis.grid(True, axis='x', color='#E5E5E5', linewidth=0.55)
    axis.set_axisbelow(True)
    span = max(values) if values else 1.0
    axis.set_xlim(0.0, 1.18 * span)
    for position, value in zip(positions, values):
        axis.text(
            value + 0.02 * span,
            position,
            f'{value:.1f}',
            va='center',
            fontsize=7.5,
        )
    figure.tight_layout()
    _save_figure(figure, output_path)
    plt.close(figure)
    return output_path


def plot_adp_component_ablation(result_dir: Path) -> Path:
    """Plot a normalized decision matrix for matched component variants."""
    result_dir = Path(result_dir)
    rows = _study_rows(result_dir, 'components')
    output_path = _figure_path(result_dir, 'adp_component_ablation')
    method_order = (
        'set_cover_cw_tour',
        'safe_graph_adp_critic_only',
        'safe_graph_adp_critic_safeguard',
        'safe_graph_adp_rollout',
        'safe_graph_adp_local_search',
        'safe_graph_adp_no_local',
        'safe_graph_adp',
    )
    component_labels = {
        'set_cover_cw_tour': 'Incumbent',
        'safe_graph_adp_critic_only': 'C only',
        'safe_graph_adp_critic_safeguard': 'C+S',
        'safe_graph_adp_rollout': 'R+S',
        'safe_graph_adp_local_search': 'L+S',
        'safe_graph_adp_no_local': 'C+R+S',
        'safe_graph_adp': 'C+R+S+L',
    }
    row_by_method = {row['method']: row for row in rows}
    methods = [method for method in method_order if method in row_by_method]
    if not methods:
        raise ValueError('component ablation contains no supported methods')
    reference_cost = next(
        float(row['reference_graph_cost'])
        for row in rows
        if row.get('reference_graph_cost', '') not in ('', None)
    )
    metric_specs = (
        ('$\\Delta v$\n(m s$^{-1}$)', 'total_delta_v', '{:.1f}'),
        ('SOOAs', 'selected_count', '{:.0f}'),
        ('Objective\n$J$', 'graph_cost', '{:.1f}'),
        ('Time\n(s)', 'planning_time', '{:.0f}'),
    )
    raw_matrix: list[list[float]] = []
    for method in methods:
        row = row_by_method[method]
        raw_matrix.append([
            (
                reference_cost
                if key == 'graph_cost' and row.get(key, '') in ('', None)
                else float(row[key])
            )
            for _, key, _ in metric_specs
        ])
    normalized_columns = [
        _normalized_values([row[column] for row in raw_matrix])
        for column in range(len(metric_specs))
    ]
    normalized_matrix = [
        [
            normalized_columns[column][row]
            for column in range(len(metric_specs))
        ]
        for row in range(len(methods))
    ]

    _configure_style()
    figure, axis = plt.subplots(figsize=(3.45, 3.15))
    axis.imshow(
        normalized_matrix,
        cmap='YlOrRd',
        vmin=0.0,
        vmax=1.0,
        aspect='auto',
        interpolation='nearest',
    )
    axis.set_xticks(range(len(metric_specs)))
    axis.set_xticklabels([label for label, _, _ in metric_specs])
    axis.xaxis.tick_top()
    axis.tick_params(axis='x', length=0, pad=4)
    axis.tick_params(axis='y', length=0)
    axis.set_yticks(range(len(methods)))
    axis.set_yticklabels([component_labels[method] for method in methods])
    for row_index, row_values in enumerate(raw_matrix):
        for column_index, value in enumerate(row_values):
            normalized = normalized_matrix[row_index][column_index]
            axis.text(
                column_index,
                row_index,
                metric_specs[column_index][2].format(value),
                ha='center',
                va='center',
                fontsize=6.8,
                color='white' if normalized >= 0.58 else '#262626',
                fontweight=(
                    'bold'
                    if methods[row_index] == 'safe_graph_adp_local_search'
                    else 'normal'
                ),
            )
    axis.set_xticks(
        [position - 0.5 for position in range(1, len(metric_specs))],
        minor=True,
    )
    axis.set_yticks(
        [position - 0.5 for position in range(1, len(methods))],
        minor=True,
    )
    axis.grid(which='minor', color='white', linewidth=1.0)
    axis.tick_params(which='minor', bottom=False, left=False)
    for spine in axis.spines.values():
        spine.set_visible(False)
    axis.set_title(
        'Darker cells indicate larger within-column burden',
        fontsize=7.0,
        pad=28,
    )
    figure.tight_layout()
    _save_figure(figure, output_path)
    plt.close(figure)
    return output_path


def plot_adp_oracle_gap(result_dir: Path) -> Path:
    """Plot exact Bellman search size and annotate returned-policy cost gaps."""
    result_dir = Path(result_dir)
    rows = _study_rows(result_dir, 'oracle')
    output_path = _figure_path(result_dir, 'adp_oracle_gap')

    _configure_style()
    figure, axis = plt.subplots(figsize=(3.45, 2.65))
    candidate_limits = sorted({
        int(float(row['candidate_limit'])) for row in rows
        if row.get('exact_expansions', '') not in ('', None)
    })
    expansions: list[int] = []
    for candidate_limit in candidate_limits:
        matching = [
            row for row in rows
            if int(float(row['candidate_limit'])) == candidate_limit
            and row.get('exact_expansions', '') not in ('', None)
        ]
        expansions.append(int(float(matching[0]['exact_expansions'])))
        gaps = [100.0 * float(row['optimality_gap']) for row in matching]
        if len(set(expansions[-1:] + [
            int(float(row['exact_expansions'])) for row in matching
        ])) != 1:
            raise ValueError(
                'exact Bellman expansion count changed across random seeds'
            )
        axis.annotate(
            f'{max(gaps):.1f}% gap\n({len(matching)}/{len(matching)} seeds)',
            (candidate_limit, expansions[-1]),
            xytext=(0, 6),
            textcoords='offset points',
            ha='center',
            va='bottom',
            fontsize=6.5,
        )
    axis.plot(
        candidate_limits,
        expansions,
        marker='o',
        markersize=4.6,
        linewidth=1.35,
        color='#0072B2',
    )
    axis.set_xlabel('Candidate nodes in exact graph')
    axis.set_ylabel('Bellman states expanded')
    axis.set_xticks(candidate_limits)
    axis.grid(True, axis='y', color='#E5E5E5', linewidth=0.55)
    figure.tight_layout()
    _save_figure(figure, output_path)
    plt.close(figure)
    return output_path


def plot_adp_compute_tradeoff(result_dir: Path) -> Path:
    """Plot coverage against planning time for ADP compute settings."""
    result_dir = Path(result_dir)
    rows = _study_rows(result_dir, 'compute')
    output_path = _figure_path(result_dir, 'adp_compute_tradeoff')

    _configure_style()
    figure, axis = plt.subplots(figsize=(3.45, 2.85))
    episode_values = [int(float(row['training_episodes'])) for row in rows]
    maximum_episode = max(episode_values) if episode_values else 1
    for row, episodes in zip(rows, episode_values):
        success = _as_bool(row['coverage_success'])
        axis.scatter(
            float(row['planning_time']),
            100.0 * float(row.get('raw_coverage', row['coverage'])),
            s=48,
            marker='o' if success else 'X',
            color=plt.cm.viridis(episodes / max(1, maximum_episode)),
            edgecolor='#202020',
            linewidth=0.5,
            zorder=3,
        )
        depth = int(float(row['lookahead_depth']))
        axis.annotate(
            f'{episodes} ep., d={depth}',
            (
                float(row['planning_time']),
                100.0 * float(row.get('raw_coverage', row['coverage'])),
            ),
            xytext=(4, 4),
            textcoords='offset points',
            fontsize=7,
        )
    axis.axhline(95.0, color='#4D4D4D', linestyle='--', linewidth=0.8)
    axis.set_xlabel('Planning time (s)')
    axis.set_ylabel('Weighted surface coverage (%)')
    axis.grid(True, color='#E5E5E5', linewidth=0.55)
    axis.set_axisbelow(True)
    figure.tight_layout()
    _save_figure(figure, output_path)
    plt.close(figure)
    return output_path


def plot_adp_initial_condition(result_dir: Path) -> Path:
    """Plot paired effort and passive margins across initial conditions."""
    result_dir = Path(result_dir)
    rows = _study_rows(result_dir, 'robustness')
    output_path = _figure_path(result_dir, 'adp_initial_condition')
    case_ids = list(dict.fromkeys(row['case_id'] for row in rows))
    methods = ('safe_graph_adp', 'set_cover_cw_tour')
    case_colors = ('#0072B2', '#B64342', '#009E73')

    _configure_style()
    figure, axis = plt.subplots(figsize=(3.45, 3.0))
    lower_margin = min(
        float(row['passive_margin'])
        for row in rows
        if row.get('passive_margin', '') not in ('', None)
    )
    upper_margin = max(
        float(row['passive_margin'])
        for row in rows
        if row.get('passive_margin', '') not in ('', None)
    )
    axis.axhspan(
        lower_margin - 1.0,
        0.0,
        color='#F6CFCB',
        alpha=0.55,
        zorder=0,
    )
    axis.axhline(0.0, color='#666666', linestyle='--', linewidth=0.85)
    for case_index, case_id in enumerate(case_ids):
        color = case_colors[case_index % len(case_colors)]
        case_rows = {
            row['method']: row
            for row in rows
            if row['case_id'] == case_id
        }
        missing = [method for method in methods if method not in case_rows]
        if missing:
            raise ValueError(
                f'{case_id} is missing rows for {", ".join(missing)}'
            )
        incumbent = case_rows['set_cover_cw_tour']
        returned = case_rows['safe_graph_adp']
        start = (
            float(incumbent['total_delta_v']),
            float(incumbent['passive_margin']),
        )
        end = (
            float(returned['total_delta_v']),
            float(returned['passive_margin']),
        )
        axis.annotate(
            '',
            xy=end,
            xytext=start,
            arrowprops={
                'arrowstyle': '-|>',
                'color': color,
                'linewidth': 1.35,
                'shrinkA': 5,
                'shrinkB': 5,
            },
            zorder=2,
        )
        axis.scatter(
            [start[0]],
            [start[1]],
            s=38,
            marker='s',
            facecolor='white',
            edgecolor=color,
            linewidth=1.2,
            zorder=3,
        )
        axis.scatter(
            [end[0]],
            [end[1]],
            s=42,
            marker='o',
            facecolor=color,
            edgecolor='white',
            linewidth=0.6,
            zorder=4,
        )
        case_label = case_id.replace('robustness_', '').upper()
        offsets = ((4, 5), (4, 5), (4, -10))
        offset = offsets[min(case_index, len(offsets) - 1)]
        axis.annotate(
            case_label,
            end,
            xytext=offset,
            textcoords='offset points',
            fontsize=7.0,
            fontweight='bold',
            color=color,
        )
    axis.scatter(
        [], [], s=34, marker='s', facecolor='white', edgecolor='#4D4D4D',
        linewidth=1.1, label='Two-stage incumbent',
    )
    axis.scatter(
        [], [], s=38, marker='o', facecolor='#4D4D4D', edgecolor='white',
        linewidth=0.6, label='Returned graph policy',
    )
    axis.text(
        0.98,
        0.04,
        'passive-audit failure',
        transform=axis.transAxes,
        ha='right',
        va='bottom',
        fontsize=6.5,
        color='#8F2D2D',
    )
    axis.set_xlabel(r'Cumulative $\Delta v$ (m s$^{-1}$)')
    axis.set_ylabel(r'Minimum passive margin $\rho_{\min}$ (m)')
    axis.set_ylim(lower_margin - 1.0, upper_margin + 1.2)
    axis.grid(True, color='#E5E5E5', linewidth=0.55)
    axis.set_axisbelow(True)
    axis.legend(loc='upper right', fontsize=6.5)
    figure.tight_layout()
    _save_figure(figure, output_path)
    plt.close(figure)
    return output_path


FIGURE_FUNCTIONS: dict[str, Callable[[Path], Path]] = {
    'targets_3d': plot_targets_3d,
    'planned_trajectory_3d': plot_planned_trajectory_3d,
    'coverage_over_time': plot_coverage_over_time,
    'coverage_comparison': plot_coverage_comparison,
    'delta_v_comparison': plot_delta_v_comparison,
    'energy_efficiency_comparison': plot_energy_efficiency_comparison,
    'safety_comparison': plot_safety_comparison,
    'peak_input_comparison': plot_peak_input_comparison,
    'adp_primary_tradeoff': plot_adp_primary_tradeoff,
    'primary_trajectory_case_study': plot_primary_trajectory_case_study,
    'adp_policy_costs': plot_adp_policy_costs,
    'adp_component_ablation': plot_adp_component_ablation,
    'adp_oracle_gap': plot_adp_oracle_gap,
    'adp_compute_tradeoff': plot_adp_compute_tradeoff,
    'adp_initial_condition': plot_adp_initial_condition,
}


def generate_figures(result_dir: Path) -> tuple[Path, ...]:
    """Generate every figure supported by the saved result directory."""
    result_dir = Path(result_dir)
    generated: list[Path] = []
    if (result_dir / 'raw' / 'targets.csv').is_file():
        generated.extend((
            plot_targets_3d(result_dir),
            plot_planned_trajectory_3d(result_dir),
            plot_coverage_over_time(result_dir),
        ))
    if (result_dir / 'raw' / 'method_comparison.csv').is_file():
        comparison_rows = _read_csv(
            result_dir / 'raw' / 'method_comparison.csv'
        )
        generated.extend((
            plot_coverage_comparison(result_dir),
            plot_delta_v_comparison(result_dir),
            plot_energy_efficiency_comparison(result_dir),
            plot_safety_comparison(result_dir),
            plot_peak_input_comparison(result_dir),
        ))
        comparison_methods = {row['method'] for row in comparison_rows}
        if (
            {'safe_graph_adp', 'set_cover_cw_tour'} <= comparison_methods
            and (result_dir / 'raw' / 'trajectory.csv').is_file()
            and (result_dir / 'raw' / 'viewpoints.csv').is_file()
        ):
            generated.append(plot_primary_trajectory_case_study(result_dir))
    if (result_dir / 'raw' / 'adp_study_runs.csv').is_file():
        study_rows = _read_csv(result_dir / 'raw' / 'adp_study_runs.csv')
        families = {row['family'] for row in study_rows}
        if 'primary' in families:
            generated.extend((
                plot_adp_primary_tradeoff(result_dir),
                plot_adp_policy_costs(result_dir),
            ))
        if 'components' in families:
            generated.append(plot_adp_component_ablation(result_dir))
        if 'oracle' in families:
            generated.append(plot_adp_oracle_gap(result_dir))
        if 'compute' in families:
            generated.append(plot_adp_compute_tradeoff(result_dir))
        if 'robustness' in families:
            generated.append(plot_adp_initial_condition(result_dir))
    if not generated:
        raise FileNotFoundError(
            f'{result_dir} does not contain supported offline-planning results'
        )
    return tuple(generated)


def _configure_style() -> None:
    plt.rcParams.update({
        'font.family': 'DejaVu Sans',
        'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans'],
        'font.size': 9,
        'axes.labelsize': 9,
        'axes.titlesize': 10,
        'legend.fontsize': 8,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'axes.linewidth': 1.0,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'legend.frameon': False,
        'figure.dpi': 160,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'svg.fonttype': 'none',
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })


def _read_csv(path: Path, allow_empty: bool = False) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows and not allow_empty:
        raise ValueError(f'{path} contains no data rows')
    return rows


def _study_rows(result_dir: Path, family: str) -> list[dict[str, str]]:
    rows = [
        row for row in _read_csv(
            result_dir / 'raw' / 'adp_study_runs.csv'
        )
        if row['family'] == family
    ]
    if not rows:
        raise ValueError(f'ADP study contains no {family!r} rows')
    return rows


def _figure_path(result_dir: Path, stem: str) -> Path:
    figure_dir = result_dir / 'figures'
    figure_dir.mkdir(parents=True, exist_ok=True)
    return figure_dir / f'{stem}.png'


def _save_figure(figure, path: Path) -> None:
    figure.savefig(path, dpi=360, bbox_inches='tight')
    figure.savefig(path.with_suffix('.pdf'), bbox_inches='tight')
    figure.savefig(path.with_suffix('.svg'), bbox_inches='tight')


def _plot_metric_bar(
    rows: list[dict[str, str]],
    path: Path,
    key: str,
    xlabel: str,
    flag_infeasible: bool = False,
) -> Path:
    _configure_style()
    figure, axis = plt.subplots(figsize=(7.0, 3.15))
    labels = [
        METHOD_LABELS_SHORT.get(row['method'], _method_label(row['method']))
        for row in rows
    ]
    values = [float(row[key]) for row in rows]
    y_positions = list(range(len(rows)))
    colors = [METHOD_COLORS.get(row['method'], '#767676') for row in rows]
    edge_colors = [
        '#0F4D92' if row['method'] == 'set_cover_cw_tour' else '#4D4D4D'
        for row in rows
    ]
    line_widths = [
        1.3 if row['method'] == 'set_cover_cw_tour' else 0.5
        for row in rows
    ]
    axis.barh(
        y_positions,
        values,
        color=colors,
        edgecolor=edge_colors,
        linewidth=line_widths,
        alpha=0.96,
        height=0.64,
    )
    axis.invert_yaxis()
    axis.set_yticks(y_positions)
    axis.set_yticklabels(labels)
    axis.set_xlabel(xlabel)
    axis.grid(True, axis='x', color='#E1E1E1', linewidth=0.6)
    axis.set_axisbelow(True)
    x_min = min(values) if values else 0.0
    x_max = max(values) if values else 1.0
    span = max(x_max - min(0.0, x_min), 1.0e-9)
    left_limit = min(0.0, x_min - 0.14 * span)
    right_limit = x_max + 0.18 * span
    axis.set_xlim(left_limit, right_limit)
    if x_min < 0.0:
        axis.axvline(0.0, color='#272727', linewidth=0.9, alpha=0.65)
    for y_position, value, row in zip(y_positions, values, rows):
        text = f'{value:.2f}' if value >= 1.0 else f'{value:.3f}'
        if value < 0.0:
            x_text = value - 0.018 * span
            horizontal_alignment = 'right'
        else:
            x_text = value + 0.018 * span
            horizontal_alignment = 'left'
        axis.text(
            x_text,
            y_position,
            text,
            va='center',
            ha=horizontal_alignment,
            fontsize=8,
            color='#272727',
            fontweight='bold' if row['method'] == 'set_cover_cw_tour' else 'normal',
        )
    if flag_infeasible:
        for y_position, row in zip(y_positions, rows):
            if row['method'] == 'coverage_greedy' and not _as_bool(row['feasible']):
                axis.text(
                    right_limit - 0.01 * span,
                    y_position,
                    'keep-out violation',
                    va='center',
                    ha='right',
                    fontsize=7,
                    color='#B64342',
                )
    axis.spines['top'].set_visible(False)
    axis.spines['right'].set_visible(False)
    figure.tight_layout()
    _save_figure(figure, path)
    plt.close(figure)
    return path


def _method_label(method: str) -> str:
    return METHOD_LABELS.get(method, method)


def _as_bool(value: object) -> bool:
    return str(value).strip().lower() in {'1', 'true', 'yes'}


def _draw_saved_geometry(
    axis,
    result_dir: Path,
    max_segments: int | None = None,
    color: str = '#6F6F6F',
    linewidth: float = 0.22,
    alpha: float = 0.28,
) -> None:
    segments = _load_saved_mesh_segments(result_dir, max_segments)
    if segments:
        axis.add_collection3d(Line3DCollection(
            segments,
            colors=color,
            linewidths=linewidth,
            alpha=alpha,
            zorder=1,
        ))
    else:
        _draw_proxy_wireframe(axis)


def _load_saved_mesh_segments(
    result_dir: Path,
    max_edges_override: int | None = None,
) -> list[tuple[Vector3, Vector3]]:
    config_dir = result_dir / 'config_snapshot'
    config_path = next(
        (
            path for path in (
                config_dir / 'offline_planner_config.json',
                config_dir / 'offline_planning_experiment_config.json',
            )
            if path.is_file()
        ),
        None,
    )
    if config_path is None:
        return []
    config = json.loads(config_path.read_text())
    if config.get('geometry_backend') != 'mesh':
        return []
    mesh_paths = []
    if config.get('iss_mesh_path'):
        mesh_paths.append(Path(str(config['iss_mesh_path'])))
    mesh_paths.extend((
        Path('data/iss_mesh/ISS_stationary.glb'),
        Path(
            'src/orbinspect_description/models/iss_real/meshes/'
            'ISS_stationary.glb'
        ),
    ))
    mesh_path = next(
        (
            resolved
            for path in mesh_paths
            if (resolved := _resolve_input_path(result_dir, path)) is not None
        ),
        None,
    )
    if mesh_path is None:
        return []
    max_edges = int(config.get('mesh_preview_max_edges', 60000))
    if max_edges_override is not None:
        max_edges = min(max_edges, max_edges_override)
    if max_edges <= 0:
        return []
    try:
        from orbinspect_guidance.offline_coverage_planner import _mesh_segments_from_gltf
        from orbinspect_guidance.offline_coverage_planner import _read_glb

        json_doc, binary = _read_glb(mesh_path)
        return _mesh_segments_from_gltf(
            json_doc,
            binary,
            float(config.get('iss_mesh_scale', 1.065)),
            max_edges,
        )
    except (ImportError, OSError, KeyError, ValueError):
        return []


def _resolve_input_path(result_dir: Path, path: Path) -> Path | None:
    if path.is_absolute():
        return path if path.is_file() else None
    candidates = [Path.cwd() / path]
    candidates.extend(parent / path for parent in result_dir.resolve().parents)
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _draw_proxy_wireframe(axis) -> None:
    boxes = (
        ((0.0, 0.0, 0.0), (80.0, 4.0, 4.0)),
        ((-25.0, 0.0, 12.0), (30.0, 1.0, 12.0)),
        ((25.0, 0.0, 12.0), (30.0, 1.0, 12.0)),
    )
    for center, size in boxes:
        axis.add_collection3d(Line3DCollection(
            _box_edges(center, size),
            colors='#9A9A9A',
            linewidths=0.45,
            alpha=0.25,
        ))


def _box_edges(center: Vector3, size: Vector3) -> list[tuple[Vector3, Vector3]]:
    center_x, center_y, center_z = center
    size_x, size_y, size_z = (
        size[0] / 2.0,
        size[1] / 2.0,
        size[2] / 2.0,
    )
    corners = [
        (
            center_x + direction_x * size_x,
            center_y + direction_y * size_y,
            center_z + direction_z * size_z,
        )
        for direction_x in (-1.0, 1.0)
        for direction_y in (-1.0, 1.0)
        for direction_z in (-1.0, 1.0)
    ]
    edges: list[tuple[Vector3, Vector3]] = []
    for index, first in enumerate(corners):
        for second in corners[index + 1:]:
            differences = sum(
                1
                for axis_index in range(3)
                if abs(first[axis_index] - second[axis_index]) > 1.0e-9
            )
            if differences == 1:
                edges.append((first, second))
    return edges


def _style_3d_axis(axis) -> None:
    axis.set_xlabel('$x_{LVLH}$ [m]', labelpad=7)
    axis.set_ylabel('$y_{LVLH}$ [m]', labelpad=7)
    axis.set_zlabel('$z_{LVLH}$ [m]', labelpad=7)
    axis.view_init(elev=22.0, azim=-58.0)
    axis.grid(True, color='#ECECEC', linewidth=0.45)
    for pane in (axis.xaxis.pane, axis.yaxis.pane, axis.zaxis.pane):
        pane.set_facecolor((1.0, 1.0, 1.0, 0.0))
        pane.set_edgecolor('#E6E6E6')


def _set_equal_3d_axes(axis, *point_sets: list[Vector3]) -> None:
    points = [
        point
        for point_set in point_sets
        for point in point_set
    ]
    points.extend(((-45.0, -25.0, -18.0), (45.0, 25.0, 22.0)))
    axis_values = tuple(
        [point[axis_index] for point in points]
        for axis_index in range(3)
    )
    centers = tuple(
        (min(values) + max(values)) / 2.0
        for values in axis_values
    )
    radius = max(max(values) - min(values) for values in axis_values) / 2.0
    radius = max(radius, 1.0) * 1.04
    axis.set_xlim(centers[0] - radius, centers[0] + radius)
    axis.set_ylim(centers[1] - radius, centers[1] + radius)
    axis.set_zlim(centers[2] - radius, centers[2] + radius)


def _normalized_values(values: list[float]) -> list[float]:
    minimum = min(values)
    maximum = max(values)
    span = max(maximum - minimum, 1.0e-12)
    return [(value - minimum) / span for value in values]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse plotting command arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--result-dir',
        required=True,
        type=Path,
        help='Saved result directory containing raw CSV files.',
    )
    parser.add_argument(
        '--figure',
        choices=('all', *FIGURE_FUNCTIONS),
        default='all',
        help='Render one named figure or every supported figure.',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Load saved results and render the requested figures."""
    args = parse_args(argv)
    if args.figure == 'all':
        generated = generate_figures(args.result_dir)
    else:
        generated = (FIGURE_FUNCTIONS[args.figure](args.result_dir),)
    print(json.dumps(
        {'figures': [str(path) for path in generated]},
        indent=2,
        sort_keys=True,
    ))


if __name__ == '__main__':
    main()
