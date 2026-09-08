#!/usr/bin/env python3
"""Compose a full RViz task video with a synchronized camera inset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = (
    ROOT
    / 'data/results/'
    'ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812'
)
HEADER_HEIGHT = 100
OUTPUT_SIZE = (1600, 1080)
CAMERA_SIZE = (500, 357)
CAMERA_ORIGIN = (28, 265)


def parse_args() -> argparse.Namespace:
    """Parse the optional run-directory override."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=DEFAULT_RUN_DIR)
    return parser.parse_args()


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file into dictionaries."""
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def relative(path: Path) -> str:
    """Return a stable workspace-relative path."""
    return str(path.resolve().relative_to(ROOT))


def validate_run(run_dir: Path) -> tuple[dict[str, object], dict[str, object]]:
    """Require a complete mission and all post-run audit gates."""
    summary = json.loads((run_dir / 'summary.json').read_text(encoding='utf-8'))
    audit = json.loads(
        (run_dir / 'mesh_execution_audit.json').read_text(encoding='utf-8')
    )
    verification = summary.get('verification', {})
    reference = summary.get('reference_stream', {})
    run_manifest = json.loads(
        (run_dir / 'config_snapshot/run_manifest.json').read_text(
            encoding='utf-8'
        )
    )
    if not verification.get('success', False):
        raise ValueError('demo run did not complete the mission gate')
    if verification.get('credited_actions') != run_manifest['planned_action_count']:
        raise ValueError('demo run did not credit every planned action')
    if not reference.get('passed', False):
        raise ValueError('demo reference stream is incomplete')
    if not audit.get('passed', False):
        raise ValueError('demo full-mesh execution audit failed')
    if audit.get('schema_version') != 'orbinspect-ros-evidence-audit/v2':
        raise ValueError('demo requires the finite-body v2 mesh audit')
    if not audit.get('gates', {}).get('finite_body_safety_margin', False):
        raise ValueError('demo finite-body safety-margin gate failed')
    return summary, audit


def latest_event(
    events: list[dict[str, str]],
    mission_time: float,
) -> dict[str, str] | None:
    """Return the latest observation event at a mission time."""
    eligible = [
        event for event in events
        if event['event'] == 'observation_credited'
        and float(event['time']) <= mission_time + 0.25
    ]
    return eligible[-1] if eligible else None


def status_text(
    mission_time: float,
    duration: float,
    action_count: int,
) -> str:
    """Describe the current phase of the planned task."""
    if mission_time < 0.0:
        return 'INITIALIZING ROS VISUALIZATION'
    if mission_time >= duration:
        return 'MISSION COMPLETE'
    action = min(int(mission_time // 90.0) + 1, action_count)
    return f'TRACKING VIEW {action}/{action_count}'


def draw_text(
    image: np.ndarray,
    text: str,
    origin: tuple[int, int],
    scale: float,
    color: tuple[int, int, int],
    thickness: int = 1,
) -> None:
    """Draw antialiased sans-serif text."""
    cv2.putText(
        image,
        text,
        origin,
        cv2.FONT_HERSHEY_DUPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def compose_frame(
    rviz_frame: np.ndarray,
    camera_frame: np.ndarray,
    mission_time: float,
    duration: float,
    action_count: int,
    events: list[dict[str, str]],
    body_radius: float,
    minimum_body_clearance: float,
) -> np.ndarray:
    """Add the camera inset, task phase, mission clock, and progress bar."""
    canvas = np.zeros((OUTPUT_SIZE[1], OUTPUT_SIZE[0], 3), dtype=np.uint8)
    canvas[:HEADER_HEIGHT] = (26, 20, 13)
    canvas[HEADER_HEIGHT:] = rviz_frame

    draw_text(
        canvas,
        'OrbInspect - Full Planned Inspection Task',
        (24, 36),
        0.82,
        (245, 245, 245),
        2,
    )
    draw_text(
        canvas,
        'Frozen rollout-ADP route -> controller -> finite-body safety filter -> '
        'ROS-native HCW dynamics',
        (24, 70),
        0.52,
        (190, 205, 220),
    )
    phase = status_text(mission_time, duration, action_count)
    phase_color = (90, 220, 140) if mission_time >= duration else (80, 190, 255)
    draw_text(canvas, phase, (1110, 38), 0.62, phase_color, 2)

    shown_time = min(max(mission_time, 0.0), duration)
    event = latest_event(events, shown_time)
    credited = int(event['current_waypoint_index']) if event else 0
    coverage = float(event['coverage_ratio']) if event else 0.0
    detail = (
        f'Mission time {shown_time:6.1f}/{duration:.0f} s  |  '
        f'credited {credited}/{action_count}  |  coverage {100.0 * coverage:5.1f}%'
    )
    draw_text(canvas, detail, (1010, 70), 0.47, (225, 230, 235))

    progress = min(max(shown_time / duration, 0.0), 1.0)
    cv2.rectangle(canvas, (24, 84), (1576, 94), (70, 78, 88), -1)
    cv2.rectangle(
        canvas,
        (24, 84),
        (24 + int(1552 * progress), 94),
        (210, 150, 45),
        -1,
    )

    inset = cv2.resize(camera_frame, CAMERA_SIZE, interpolation=cv2.INTER_AREA)
    x, y = CAMERA_ORIGIN
    cv2.rectangle(
        canvas,
        (x - 7, y - 39),
        (x + CAMERA_SIZE[0] + 7, y + CAMERA_SIZE[1] + 7),
        (14, 18, 24),
        -1,
    )
    canvas[y:y + CAMERA_SIZE[1], x:x + CAMERA_SIZE[0]] = inset
    cv2.rectangle(
        canvas,
        (x - 1, y - 1),
        (x + CAMERA_SIZE[0], y + CAMERA_SIZE[1]),
        (80, 190, 255),
        2,
    )
    draw_text(
        canvas,
        'LIVE CHASER CAMERA  /chaser/camera/image',
        (x, y - 12),
        0.50,
        (235, 240, 245),
        1,
    )
    cv2.rectangle(canvas, (730, 1027), (1592, 1076), (14, 18, 24), -1)
    draw_text(
        canvas,
        f'FULL-MESH AUDIT PASS  |  body radius {body_radius:.2f} m  |  '
        f'minimum safety clearance {minimum_body_clearance:.2f} m',
        (746, 1058),
        0.43,
        (235, 235, 235),
        1,
    )
    return canvas


def transcode_h264(source: Path, destination: Path) -> None:
    """Transcode the composed MPEG-4 stream to broadly compatible H.264."""
    command = [
        'gst-launch-1.0', '-e',
        'filesrc', f'location={source}', '!',
        'qtdemux', '!', 'decodebin', '!', 'videoconvert', '!',
        'video/x-raw,format=I420', '!',
        'x264enc', 'speed-preset=veryfast', 'bitrate=5000',
        'key-int-max=30', '!', 'h264parse', '!',
        'mp4mux', 'faststart=true', '!',
        'filesink', f'location={destination}',
    ]
    subprocess.run(command, check=True)


def main() -> None:
    """Generate the final annotated MP4, preview, and provenance manifest."""
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    summary, audit = validate_run(run_dir)
    timing = json.loads(
        (run_dir / 'config_snapshot/video_timing.json').read_text(
            encoding='utf-8'
        )
    )
    events = read_csv(run_dir / 'raw/mission_events.csv')
    rviz_path = run_dir / 'raw/rviz_window_raw.mp4'
    camera_path = run_dir / 'raw/camera_sensor_raw.mp4'
    rviz = cv2.VideoCapture(str(rviz_path))
    camera = cv2.VideoCapture(str(camera_path))
    if not rviz.isOpened() or not camera.isOpened():
        raise RuntimeError('failed to open a raw demo video')

    fps = float(rviz.get(cv2.CAP_PROP_FPS))
    frame_count = int(rviz.get(cv2.CAP_PROP_FRAME_COUNT))
    rviz_width = int(rviz.get(cv2.CAP_PROP_FRAME_WIDTH))
    rviz_height = int(rviz.get(cv2.CAP_PROP_FRAME_HEIGHT))
    camera_count = int(camera.get(cv2.CAP_PROP_FRAME_COUNT))
    camera_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    camera_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if frame_count < 2 or camera_count < 2:
        raise ValueError('raw demo videos must contain multiple frames')
    ok, camera_frame = camera.read()
    if not ok:
        raise RuntimeError('failed to read first camera frame')
    camera_index = 0

    videos_dir = run_dir / 'videos'
    figures_dir = run_dir / 'figures'
    videos_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    temporary = videos_dir / 'orbinspect_rviz_full_planning_demo_mpeg4_temp.mp4'
    scenario_id = str(timing['scenario_id'])
    output = videos_dir / f'orbinspect_rviz_full_planning_demo_{scenario_id}.mp4'
    writer = cv2.VideoWriter(
        str(temporary),
        cv2.VideoWriter_fourcc(*'mp4v'),
        fps,
        OUTPUT_SIZE,
    )
    if not writer.isOpened():
        raise RuntimeError(f'failed to open video writer: {temporary}')

    rviz_start = float(timing['rviz_capture_start_wall_epoch_s'])
    mission_start = float(timing['mission_process_start_wall_epoch_s'])
    camera_start = float(timing['camera_first_frame_wall_epoch_s'])
    camera_end = float(timing['camera_last_frame_wall_epoch_s'])
    time_scale = float(timing['mission_time_scale'])
    duration = float(timing['mission_duration_s'])
    action_count = int(timing['planned_action_count'])
    body_radius = float(audit['vehicle_bounding_radius_m'])
    minimum_body_clearance = float(audit['minimum_body_clearance_m'])
    preview_frames: list[np.ndarray] = []
    preview_targets = (
        -1.0,
        0.30 * duration,
        0.60 * duration,
        0.90 * duration,
    )
    preview_recorded = [False] * len(preview_targets)

    try:
        processed_frames = 0
        for frame_index in range(frame_count):
            ok, rviz_frame = rviz.read()
            if not ok:
                break
            wall_time = rviz_start + frame_index / fps
            camera_fraction = (
                (wall_time - camera_start) / (camera_end - camera_start)
            )
            target_camera_index = int(round(
                min(max(camera_fraction, 0.0), 1.0) * (camera_count - 1)
            ))
            while camera_index < target_camera_index:
                ok, next_camera_frame = camera.read()
                if not ok:
                    break
                camera_frame = next_camera_frame
                camera_index += 1
            mission_time = (wall_time - mission_start) * time_scale
            composed = compose_frame(
                rviz_frame,
                camera_frame,
                mission_time,
                duration,
                action_count,
                events,
                body_radius,
                minimum_body_clearance,
            )
            writer.write(composed)
            processed_frames += 1
            for index, target in enumerate(preview_targets):
                if not preview_recorded[index] and mission_time >= target:
                    preview_frames.append(composed.copy())
                    preview_recorded[index] = True
    finally:
        writer.release()
        rviz.release()
        camera.release()

    if processed_frames < 2:
        raise RuntimeError('failed to decode enough RViz frames')
    frame_count = processed_frames

    transcode_h264(temporary, output)
    temporary.unlink()
    final_video = cv2.VideoCapture(str(output))
    if not final_video.isOpened():
        raise RuntimeError(f'failed to inspect final video: {output}')
    final_frame_count = int(final_video.get(cv2.CAP_PROP_FRAME_COUNT))
    final_fps = float(final_video.get(cv2.CAP_PROP_FPS))
    final_width = int(final_video.get(cv2.CAP_PROP_FRAME_WIDTH))
    final_height = int(final_video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    final_video.release()
    if final_frame_count != frame_count:
        raise ValueError('final video frame count differs from raw RViz stream')
    if (final_width, final_height) != OUTPUT_SIZE:
        raise ValueError('final video resolution differs from requested output')
    if len(preview_frames) != len(preview_targets):
        raise RuntimeError('failed to collect all milestone preview frames')
    tiles = [cv2.resize(frame, (800, 540)) for frame in preview_frames]
    preview = np.vstack((np.hstack(tiles[:2]), np.hstack(tiles[2:])))
    preview_path = figures_dir / 'rviz_full_planning_demo_preview.png'
    cv2.imwrite(str(preview_path), preview)

    source_paths = (
        rviz_path,
        camera_path,
        run_dir / 'raw/mission_events.csv',
        run_dir / 'raw/trajectory.csv',
        run_dir / 'raw/control.csv',
        run_dir / 'raw/launch.log',
        run_dir / 'summary.json',
        run_dir / 'mesh_execution_audit.json',
        run_dir / 'config_snapshot/run_manifest.json',
        run_dir / 'config_snapshot/video_timing.json',
    )
    manifest = {
        'schema_version': 'orbinspect-rviz-planning-demo-video/v1',
        'scenario_id': timing['scenario_id'],
        'method': timing['method'],
        'publish_mode': 'closed_loop',
        'state_source_of_truth': 'ROS-native HCW dynamics node',
        'gazebo_role': 'visualization and chaser camera only',
        'mission_time_scale': time_scale,
        'mission_duration_s': duration,
        'planned_action_count': action_count,
        'verification': summary['verification'],
        'reference_stream': summary['reference_stream'],
        'mesh_execution_audit_passed': audit['passed'],
        'vehicle_bounding_radius_m': body_radius,
        'minimum_body_clearance_m': minimum_body_clearance,
        'raw_rviz': {
            'frames': frame_count,
            'fps': fps,
            'width': rviz_width,
            'height': rviz_height,
        },
        'raw_camera': {
            'frames': camera_count,
            'source_topic': '/chaser/camera/image',
            'source_width': camera_width,
            'source_height': camera_height,
        },
        'final_video': {
            'path': relative(output),
            'frames': final_frame_count,
            'fps': final_fps,
            'duration_s': final_frame_count / final_fps,
            'width': final_width,
            'height': final_height,
            'sha256': sha256(output),
        },
        'preview': {
            'path': relative(preview_path),
            'sha256': sha256(preview_path),
        },
        'sources_sha256': {
            relative(path): sha256(path) for path in source_paths
        },
        'script_sha256': sha256(Path(__file__)),
        'interpretation': (
            'The video documents one complete accelerated ROS closed-loop task. '
            'It is a demonstration artifact, not an additional campaign row.'
        ),
    }
    manifest_path = videos_dir / 'video_manifest.json'
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )
    (videos_dir / 'README.md').write_text(
        '# RViz full planning demo\n\n'
        f'This directory contains the complete `{scenario_id}` rollout-ADP '
        f'planned task at {time_scale:g}x mission time. The main view is the '
        'recorded RViz2 window; '
        'the inset is the live Gazebo chaser-camera topic. The task credited '
        f'all {action_count} views, reached '
        f'{100.0 * float(summary["verification"]["coverage_ratio"]):.2f}% '
        'coverage, and passed every post-run full-mesh finite-body '
        f'execution-audit gate with {minimum_body_clearance:.2f} m minimum '
        'safety clearance. Gazebo remains visual-only; the ROS '
        'HCW dynamics node is the state source of truth.\n\n'
        'Regenerate the video, milestone preview, and provenance manifest from '
        'the retained raw captures with:\n\n'
        '```bash\n'
        'python3 OrbInspectLatex/scripts/'
        'compose_rviz_planning_demo_video.py --run-dir '
        f'{relative(run_dir)}\n'
        '```\n',
        encoding='utf-8',
    )
    print(output)
    print(preview_path)
    print(manifest_path)


if __name__ == '__main__':
    main()
