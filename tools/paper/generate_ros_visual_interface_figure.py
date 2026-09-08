#!/usr/bin/env python3
"""Compose the real Gazebo/RViz verification captures and record provenance."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAPTURE_DIR = (
    ROOT / 'data/results/ros_visual_proof_test_002_20260811'
)
EXPECTED_PROCESSES = (
    'planned_trajectory_replay_node-1',
    'verification_evaluator_node-2',
    'dynamics_node-3',
    'controller_node-4',
    'safety_filter_node-5',
    'gazebo-6',
    'rviz2-7',
    'create-8',
    'chaser_pose_follower-9',
)


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def timestamp(path: Path) -> str:
    """Return a local-time ISO 8601 file timestamp."""
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat()


def relative(path: Path) -> str:
    """Return a stable workspace-relative path."""
    return str(path.resolve().relative_to(ROOT))


def parse_args() -> argparse.Namespace:
    """Parse the optional evidence-directory override."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--capture-dir',
        type=Path,
        default=DEFAULT_CAPTURE_DIR,
        help='visual-only ROS result directory',
    )
    return parser.parse_args()


def validate_capture(capture_dir: Path) -> tuple[dict[str, object], str]:
    """Validate that the capture came from the declared visual launch."""
    config_dir = capture_dir / 'config_snapshot'
    run_manifest_path = config_dir / 'run_manifest.json'
    run_manifest = json.loads(run_manifest_path.read_text(encoding='utf-8'))
    expected = {
        'scenario_id': 'test_002',
        'method': 'adaptive_rollout_adp',
        'publish_mode': 'closed_loop',
        'headless': False,
        'time_scale': 1.0,
        'clock_mode': 'wall_time',
    }
    mismatches = {
        key: (run_manifest.get(key), value)
        for key, value in expected.items()
        if run_manifest.get(key) != value
    }
    if mismatches:
        raise ValueError(f'capture manifest mismatch: {mismatches}')
    if sha256(config_dir / 'input_manifest.json') != run_manifest[
        'input_manifest_sha256'
    ]:
        raise ValueError('captured input manifest hash does not match run manifest')
    if sha256(config_dir / 'ros_verification.yaml') != run_manifest[
        'configuration_sha256'
    ]:
        raise ValueError('captured protocol hash does not match run manifest')

    launch_log = (capture_dir / 'raw/launch.log').read_text(encoding='utf-8')
    for process in EXPECTED_PROCESSES:
        if f'[{process}]: process started with pid' not in launch_log:
            raise ValueError(f'missing process-start evidence for {process}')
        if f'[{process}]: process has finished cleanly' not in launch_log:
            raise ValueError(f'missing clean-exit evidence for {process}')
    death_signatures = ('process has died', 'Traceback (most recent call last)')
    if any(signature in launch_log for signature in death_signatures):
        raise ValueError('launch log contains a child-death signature')
    return run_manifest, launch_log


def configure_style() -> None:
    """Apply compact manuscript-compatible styling."""
    mpl.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 8.2,
        'axes.titlesize': 8.4,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })


def compose_figure(
    gazebo_path: Path,
    rviz_path: Path,
    manuscript_dir: Path,
    evidence_dir: Path,
) -> tuple[Path, Path, dict[str, dict[str, list[int]]]]:
    """Compose application captures after removing blank XWD right padding."""
    configure_style()
    source_images = (
        Image.open(gazebo_path).convert('RGB'),
        Image.open(rviz_path).convert('RGB'),
    )
    image_names = ('gazebo', 'rviz')
    images = []
    crops: dict[str, dict[str, list[int]]] = {}
    for name, image in zip(image_names, source_images, strict=True):
        bounding_box = image.getbbox()
        if bounding_box is None:
            raise ValueError(f'{name} capture contains no visible pixels')
        if bounding_box[:2] != (0, 0) or bounding_box[3] != image.height:
            raise ValueError(f'unexpected {name} capture bounds: {bounding_box}')
        crop_box = (0, 0, bounding_box[2], image.height)
        images.append(image.crop(crop_box))
        crops[name] = {
            'source_size_pixels': [image.width, image.height],
            'displayed_crop_pixels': list(crop_box),
        }
    titles = (
        '(a) Gazebo Harmonic: ISS proxy and chaser entity',
        '(b) RViz2: LVLH frame and trajectory overlays',
    )
    figure, axes = plt.subplots(1, 2, figsize=(7.15, 3.10))
    for axis, image, title in zip(axes, images, titles, strict=True):
        axis.imshow(image)
        axis.set_title(title, loc='left', fontweight='semibold', pad=3)
        axis.set_xticks([])
        axis.set_yticks([])
        axis.add_patch(Rectangle(
            (0, 0), 1, 1,
            transform=axis.transAxes,
            fill=False,
            edgecolor='#2D3436',
            linewidth=0.6,
        ))
    figure.subplots_adjust(left=0.004, right=0.996, bottom=0.015,
                           top=0.91, wspace=0.018)

    manuscript_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    pdf = manuscript_dir / 'ros_visual_interface.pdf'
    png = manuscript_dir / 'ros_visual_interface.png'
    figure.savefig(
        pdf,
        dpi=400,
        metadata={
            'Creator': 'OrbInspect visual-interface evidence generator',
            'Title': 'Gazebo Harmonic and RViz2 ROS verification views',
        },
    )
    figure.savefig(png, dpi=400)
    plt.close(figure)
    for output in (pdf, png):
        shutil.copy2(output, evidence_dir / output.name)
    return pdf, png, crops


def main() -> None:
    """Generate the manuscript figure, evidence manifest, and visual-only summary."""
    args = parse_args()
    capture_dir = args.capture_dir.expanduser().resolve()
    run_manifest, launch_log = validate_capture(capture_dir)
    launch_timestamps = [
        float(line.split(maxsplit=1)[0])
        for line in launch_log.splitlines()
        if line and line[0].isdigit()
    ]
    launch_runtime_s = round(
        launch_timestamps[-1] - launch_timestamps[0], 3
    )
    figures_dir = capture_dir / 'figures'
    raw_dir = capture_dir / 'raw'
    gazebo_path = figures_dir / 'gazebo_window.png'
    rviz_path = figures_dir / 'rviz_window.png'
    pdf, png, crops = compose_figure(
        gazebo_path,
        rviz_path,
        ROOT / 'OrbInspectLatex/figures',
        figures_dir,
    )

    run_manifest_path = capture_dir / 'config_snapshot/run_manifest.json'
    source_paths = (
        capture_dir / 'config_snapshot/input_manifest.json',
        capture_dir / 'config_snapshot/ros_verification.yaml',
        run_manifest_path,
        raw_dir / 'launch.log',
        raw_dir / 'gazebo_window.xwd',
        raw_dir / 'rviz_window.xwd',
        gazebo_path,
        rviz_path,
    )
    run_start = run_manifest_path.stat().st_mtime
    frames = {
        'gazebo': {
            'path': relative(gazebo_path),
            'captured_at': timestamp(gazebo_path),
            'seconds_after_launch_manifest': round(
                gazebo_path.stat().st_mtime - run_start, 3
            ),
            'sha256': sha256(gazebo_path),
        },
        'rviz': {
            'path': relative(rviz_path),
            'captured_at': timestamp(rviz_path),
            'seconds_after_launch_manifest': round(
                rviz_path.stat().st_mtime - run_start, 3
            ),
            'sha256': sha256(rviz_path),
        },
    }
    manifest = {
        'schema_version': 'orbinspect-ros-visual-interface/v1',
        'purpose': 'visual_interface_documentation_only',
        'campaign_row': False,
        'quantitative_evidence': False,
        'record': False,
        'full_route_completed': False,
        'manual_shutdown_after_capture': True,
        'route': {
            key: run_manifest[key]
            for key in (
                'scenario_id', 'split', 'scenario_seed', 'method',
                'publish_mode', 'headless', 'time_scale', 'clock_mode',
                'source_route_hash', 'input_manifest_sha256',
                'configuration_sha256', 'git_revision',
            )
        },
        'visual_launch_command': (
            'ros2 launch orbinspect_bringup ros_verification.launch.py '
            'result_dir:=$PWD/data/results/ros_verification_inputs_frozen_20260811 '
            'scenario_id:=test_002 method:=adaptive_rollout_adp '
            'publish_mode:=closed_loop headless:=false time_scale:=1.0 '
            'record:=false record_bag:=false save_figures:=false '
            'run_id:=ros_visual_proof_test_002_20260811'
        ),
        'frames': frames,
        'composition': {
            'content_modification': 'none',
            'transform': 'crop uniform all-black trailing XWD padding only',
            'crops': crops,
        },
        'launch_log_evidence': {
            'expected_processes': list(EXPECTED_PROCESSES),
            'process_start_count': launch_log.count('process started with pid'),
            'clean_exit_count': launch_log.count('process has finished cleanly'),
            'child_death_signature_count': launch_log.count('process has died'),
            'launch_runtime_s': launch_runtime_s,
        },
        'sources_sha256': {
            relative(path): sha256(path) for path in source_paths
        },
        'script_sha256': sha256(Path(__file__)),
        'outputs_sha256': {
            relative(pdf): sha256(pdf),
            relative(png): sha256(png),
        },
        'interpretation': (
            'The selected frames document the live ROS integration and shared '
            'visualization path. They are not a statistical campaign run, a '
            'safety proof, or an independent dynamics result.'
        ),
    }
    manifest_path = figures_dir / 'ros_visual_interface_manifest.json'
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )

    summary = {
        'schema_version': 'orbinspect-visual-proof-summary/v1',
        'status': 'complete_visual_only',
        'scenario_id': run_manifest['scenario_id'],
        'method': run_manifest['method'],
        'campaign_row': False,
        'record': False,
        'full_route_completed': False,
        'rosbag_recorded': False,
        'csv_logging_enabled': False,
        'reason_no_campaign_csv_or_rosbag': (
            'This separately labeled run captured the live Gazebo/RViz '
            'interface only; all quantitative evidence comes from the frozen '
            'recorded campaign and its representative retained rosbag.'
        ),
        'process_start_count': launch_log.count('process started with pid'),
        'clean_exit_count': launch_log.count('process has finished cleanly'),
        'launch_runtime_s': launch_runtime_s,
        'planned_route_duration_s': run_manifest['planned_duration_s'],
        'figure_manifest': relative(manifest_path),
    }
    (capture_dir / 'summary.json').write_text(
        json.dumps(summary, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )
    (capture_dir / 'summary.md').write_text(
        '# ROS visual-interface proof\n\n'
        'Status: complete (visual-only; excluded from campaign inference).\n\n'
        'The frozen `test_002` rollout-ADP route was running through the '
        'controller, safety filter, and ROS-native HCW dynamics node at real '
        'time. Gazebo Harmonic and RViz2 visualized that ROS state. Recording '
        'was deliberately disabled, so this directory has no campaign CSVs or '
        'rosbag; the launch log records nine starts and nine clean exits. The '
        f'visual launch was stopped after capture at {launch_runtime_s:.3f} s; '
        'it was not intended to complete the 900 s route. The '
        'selected window frames, untouched raw XWD captures, composed figure, '
        'configuration snapshots, and SHA-256 provenance manifest are retained '
        'here.\n\n'
        'Interpretation: these frames document the ROS integration and '
        'visualization procedure. Quantitative claims remain tied to the '
        'frozen campaign CSVs, audits, and representative MCAP rosbag.\n',
        encoding='utf-8',
    )

    print(pdf)
    print(png)
    print(manifest_path)


if __name__ == '__main__':
    main()
