#!/usr/bin/env python3
"""Create the ROS visual-interface figure from the corrected accepted video."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import cv2
import matplotlib as mpl
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = (
    ROOT / 'data/results/'
    'ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812'
)


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def frame_at(path: Path, seconds: float):
    """Decode the frame nearest one elapsed stream time."""
    video = cv2.VideoCapture(str(path))
    if not video.isOpened():
        raise RuntimeError(f'failed to open {path}')
    video.set(cv2.CAP_PROP_POS_MSEC, 1000.0 * seconds)
    ok, frame = video.read()
    video.release()
    if not ok:
        raise RuntimeError(f'failed to decode {path} at {seconds:.3f} s')
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def parse_args() -> argparse.Namespace:
    """Parse source-run and capture-time arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument('--elapsed-seconds', type=float, default=125.0)
    return parser.parse_args()


def main() -> None:
    """Validate the run, extract synchronized frames, and save the figure."""
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    audit_path = run_dir / 'mesh_execution_audit.json'
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    summary_path = run_dir / 'summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    manifest_path = run_dir / 'videos/video_manifest.json'
    video_manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not audit.get('passed', False):
        raise ValueError('source run did not pass the mesh execution audit')
    if not summary.get('verification', {}).get('success', False):
        raise ValueError('source run did not complete the task')

    rviz_path = run_dir / 'raw/rviz_window_raw.mp4'
    camera_path = run_dir / 'raw/camera_sensor_raw.mp4'
    timing_path = run_dir / 'config_snapshot/video_timing.json'
    timing = json.loads(timing_path.read_text(encoding='utf-8'))
    rviz_wall = (
        float(timing['rviz_capture_start_wall_epoch_s'])
        + args.elapsed_seconds
    )
    camera_seconds = max(
        0.0,
        rviz_wall - float(timing['camera_first_frame_wall_epoch_s']),
    )
    rviz_frame = frame_at(rviz_path, args.elapsed_seconds)
    camera_frame = frame_at(camera_path, camera_seconds)

    mpl.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 8.2,
        'axes.titlesize': 8.4,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })
    figure, axes = plt.subplots(1, 2, figsize=(7.15, 3.10))
    axes[0].imshow(camera_frame)
    axes[0].set_title(
        '(a) Gazebo Harmonic: live chaser camera',
        loc='left', fontweight='semibold', pad=3,
    )
    axes[1].imshow(rviz_frame)
    axes[1].set_title(
        '(b) RViz2: corrected trajectory overlays',
        loc='left', fontweight='semibold', pad=3,
    )
    for axis in axes:
        axis.set_xticks([])
        axis.set_yticks([])
        for spine in axis.spines.values():
            spine.set_linewidth(0.6)
            spine.set_edgecolor('#2D3436')
    figure.subplots_adjust(
        left=0.004, right=0.996, bottom=0.015, top=0.91, wspace=0.018,
    )

    paper_dir = ROOT / 'OrbInspectLatex/figures'
    evidence_dir = run_dir / 'figures'
    paper_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    pdf = paper_dir / 'ros_visual_interface.pdf'
    png = paper_dir / 'ros_visual_interface.png'
    figure.savefig(pdf, dpi=400)
    figure.savefig(png, dpi=400)
    plt.close(figure)
    for output in (pdf, png):
        shutil.copy2(output, evidence_dir / output.name)

    provenance = {
        'schema_version': 'orbinspect-corrected-ros-visual-interface/v2',
        'source_run': str(run_dir.relative_to(ROOT)),
        'scenario_id': 'validation_002',
        'method': 'adaptive_rollout_adp',
        'rviz_elapsed_seconds': args.elapsed_seconds,
        'camera_elapsed_seconds': camera_seconds,
        'verification': summary['verification'],
        'mesh_audit_passed': audit['passed'],
        'vehicle_bounding_radius_m': audit['vehicle_bounding_radius_m'],
        'minimum_body_clearance_m': audit['minimum_body_clearance_m'],
        'video_sha256': video_manifest['final_video']['sha256'],
        'sources_sha256': {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (
                rviz_path, camera_path, timing_path, summary_path,
                audit_path, manifest_path,
            )
        },
        'outputs_sha256': {
            str(path.relative_to(ROOT)): sha256(path) for path in (pdf, png)
        },
        'script_sha256': sha256(Path(__file__)),
        'interpretation': (
            'Synchronized views from the accepted corrected full-task run; '
            'Gazebo is visual-only and ROS HCW dynamics is the state truth.'
        ),
    }
    out_manifest = evidence_dir / 'ros_visual_interface_manifest.json'
    out_manifest.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )
    print(pdf)
    print(png)
    print(out_manifest)


if __name__ == '__main__':
    main()
