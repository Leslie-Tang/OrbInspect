#!/usr/bin/env python3
"""Prepare a portable, verified layout-only snapshot for Figure 7.

No experiment is executed and no historical evidence is overwritten. Camera
pixels are extracted losslessly from the approved composite PDF, not synthesized
or decoded at a new video timestamp.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / 'OrbInspectLatex'
RUN = ROOT / 'data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812'
ARCHIVE = PAPER / 'archive/figure7_single_column_20260908'
DEST = PAPER / 'data/historical_ros/figure7'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest_path = RUN / 'figures/ros_key_camera_views_trajectory_manifest.json'
    original = json.loads(manifest_path.read_text())
    for relative, expected in original['sources_sha256'].items():
        assert sha(ROOT / relative) == expected, f'Source changed: {relative}'
    source_pdf = PAPER / 'figures/fig07_ros_camera_views/ros_key_camera_views_trajectory.pdf'
    expected = original['outputs_sha256']['OrbInspectLatex/figures/ros_key_camera_views_trajectory.pdf']
    assert sha(source_pdf) == expected, 'Expected approved pre-redesign Figure 7'
    assert not ARCHIVE.exists() and not DEST.exists(), 'Preserve existing snapshot; do not overwrite'

    ARCHIVE.mkdir(parents=True)
    for relative in ('figures/fig07_ros_camera_views', 'sections/ros_verification_results.tex',
                     'figures/manifest.json', 'README.md', 'data/README.md', 'build/main.pdf'):
        source = PAPER / relative
        target = ARCHIVE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    protected = [PAPER / name for name in ('main.tex', 'references.bib', 'IEEEtaes.cls', 'IEEEtran.bst')]
    for folder in ('tables', 'data', 'sections'):
        protected.extend(p for p in (PAPER / folder).rglob('*') if p.is_file()
                         and p.name != '.DS_Store' and p.name != 'ros_verification_results.tex')
    for folder in (PAPER / 'figures').iterdir():
        if folder.is_dir() and folder.name != 'fig07_ros_camera_views':
            protected.extend(p for p in folder.rglob('*') if p.is_file() and p.name != '.DS_Store')
    (ARCHIVE / 'protected_sha256.json').write_text(json.dumps(
        {str(p.relative_to(PAPER)): sha(p) for p in protected}, indent=2) + '\n')

    DEST.mkdir(parents=True)
    records = original['camera_views']
    with pymupdf.open(source_pdf) as document:
        images = sorted(document[0].get_images(full=True), key=lambda item: int(item[7][1:]))
        assert len(images) == len(records) == 10
        for image, record in zip(images, records, strict=True):
            assert image[7] == f'I{record["sequence"]}'
            pixels = pymupdf.Pixmap(document, image[0])
            destination = DEST / f'view_{record["sequence"]:02d}.png'
            pixels.save(destination)
            record['snapshot_image'] = destination.name
            record['snapshot_image_sha256'] = sha(destination)
            record['snapshot_pixel_sha256'] = hashlib.sha256(pixels.samples).hexdigest()
            record['snapshot_dimensions_px'] = [pixels.width, pixels.height]

    with (RUN / 'raw/trajectory.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    times = np.asarray([float(row['time']) for row in rows])
    executed = np.asarray([[float(row[k]) for k in ('rx', 'ry', 'rz')] for row in rows])
    planned = np.asarray([[float(row[k]) for k in ('planned_rx', 'planned_ry', 'planned_rz')]
                          for row in rows])
    event_points = np.asarray([r['executed_position_lvlh_m'] for r in records])
    for record, point in zip(records, event_points, strict=True):
        index = record['trajectory_row_index']
        assert abs(times[index] - record['mission_time_s']) <= 1e-6
        np.testing.assert_array_equal(executed[index], point)
        np.testing.assert_array_equal(planned[index], record['planned_position_lvlh_m'])

    for package in ('orbinspect_guidance', 'orbinspect_dynamics', 'orbinspect_perception', 'orbinspect_safety'):
        sys.path.insert(0, str(ROOT / 'src' / package))
    from orbinspect_guidance.offline_coverage_planner import _read_glb, _mesh_triangles_from_gltf
    mesh_path = ROOT / 'src/orbinspect_description/models/iss_real/meshes/ISS_stationary.glb'
    document, binary = _read_glb(mesh_path)
    triangles = list(_mesh_triangles_from_gltf(document, binary, 1.065))
    assert len(triangles) == 247525
    selection = np.linspace(0, len(triangles) - 1, 14000, dtype=int)
    display_triangles = np.asarray([triangles[i].vertices for i in selection])
    arrays = DEST / 'trajectory_and_display_mesh.npz'
    np.savez_compressed(arrays, times=times, planned=planned, executed=executed,
                        event_points=event_points, display_triangles=display_triangles)
    provenance = {
        'schema': 'orbinspect-figure7-layout-snapshot/v1',
        'source_run': str(RUN.relative_to(ROOT)),
        'source_manifest_sha256': sha(manifest_path),
        'source_figure_sha256': sha(source_pdf),
        'source_sha256': original['sources_sha256'],
        'camera_views': records,
        'arrays_file': arrays.name,
        'arrays_sha256': sha(arrays),
        'trajectory_rows': len(rows),
        'mesh_display': original['mesh_display'],
        'preparation_script_sha256': sha(Path(__file__)),
        'image_integrity': {
            'source': 'Lossless extraction of ten embedded image objects from the approved composite PDF',
            'crop': 'none', 'brightness_contrast_gamma': 'unchanged',
            'pseudo_color': 'none', 'new_frame_selection': False,
            'note': 'Embedded pixels retain the approved export resampling; full source camera frames are archived in the original run.',
        },
        'interpretation': original['interpretation'],
    }
    (DEST / 'snapshot.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(f'Prepared {len(records)} unchanged images and {len(rows)} trajectory rows; originals archived.')


if __name__ == '__main__':
    main()
