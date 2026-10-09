#!/usr/bin/env python3
"""Export separate Figure 8 panels; LaTeX owns their labels and subcaptions."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/rviz_overview/20260909_113140_hybrid12_rviz_video'
OUTPUT = ROOT / 'figures/fig08_rviz_overview'
STEM = 'rviz_execution_overview'
# Match the existing screenshot widths and gap within the 85 mm layout.
# Removing the embedded headings leaves room for LaTeX subcaptions below.
WIDTH_MM, HEIGHT_MM = 85.0, 42.3
PANEL_FRACTIONS = {'a': .426, 'b': .5}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_at(fig, x: float, y: float, value: str, *, bold: bool = False):
    width_mm = fig.get_figwidth() * 25.4
    return fig.text(x / width_mm, y / HEIGHT_MM, value, va='top', ha='left',
                    fontsize=7.5 if bold else 7.2,
                    fontweight='bold' if bold else 'normal', color='#111820')


def image_panel(fig, pixels, *, x, top, width, edge):
    width_mm = fig.get_figwidth() * 25.4
    height = width * pixels.shape[0] / pixels.shape[1]
    axis = fig.add_axes((x / width_mm, (top-height) / HEIGHT_MM,
                         width / width_mm, height / HEIGHT_MM))
    # Native pixels are embedded in PDF/SVG. No local or global image adjustment.
    axis.imshow(pixels, interpolation='none', aspect='equal')
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_color(edge)
        spine.set_linewidth(0.65)
    return axis


def generate(output: Path = OUTPUT) -> None:
    source = json.loads((DATA / 'source_manifest.json').read_text())
    for name, digest in source['files'].items():
        assert sha(DATA/name) == digest, f'Source changed: {name}'
    summary = json.loads((DATA / 'capture_summary.json').read_text())
    audit = json.loads((DATA / 'required_target_execution_audit.json').read_text())
    assert audit['passed'] and audit['accepted_observations'] == 12
    assert audit['accepted_required_count'] == 9
    assert summary['weighted_coverage'] == audit['accepted_background_coverage']
    # Progress labels describe the selected transfer frame, not the final audit.
    state = source['frame_state']
    timing = json.loads((DATA / 'capture_finished.json').read_text())
    frame_time = source['video_frame_time_s'] - timing['mission_offset_s_estimated_from_event_receipts']
    events = [json.loads(line)['payload'] for line in (DATA / 'video_events.jsonl').read_text().splitlines()]
    accepted = [event for event in events if event['event'] == 'observation_credited' and event['time'] <= frame_time]
    last = accepted[-1]
    assert state['accepted_observations'] == len(accepted)
    assert state['from_observation'] == last['current_waypoint_index']
    assert state['to_observation'] == state['from_observation'] + 1
    assert state['accepted_required_count'] == last['required_covered_count']
    assert state['weighted_coverage'] == last['coverage_ratio']
    assert state['phase'] == 'transfer' and last['time'] < frame_time < last['time'] + 90.0
    frame = np.asarray(Image.open(DATA / source['frame_file']).convert('RGB'))
    assert list(frame.shape[1::-1]) == source['source_dimensions_px']
    panels = {}
    for key in ('global', 'camera'):
        x0, y0, x1, y1 = source[f'{key}_crop_xyxy']
        panels[key] = frame[y0:y1, x0:x1].copy()

    # Keep the actual DejaVu Sans annotations embedded in the approved export,
    # the original screenshot colors, and the existing border treatment.
    mpl.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['DejaVu Sans'],
        'font.size': 7.2, 'svg.fonttype': 'none', 'pdf.fonttype': 42,
        'ps.fonttype': 42, 'figure.facecolor': 'white',
        'savefig.facecolor': 'white', 'svg.hashsalt': 'orbinspect-fig8-rviz',
    })
    output.mkdir(parents=True, exist_ok=True)
    files = {}
    for suffix, key, width, edge in (('a', 'global', 35.2, '#8A939C'),
                                     ('b', 'camera', 41.5, '#7E4A9E')):
        fig = plt.figure(figsize=(WIDTH_MM*PANEL_FRACTIONS[suffix]/25.4, HEIGHT_MM/25.4))
        axis = image_panel(fig, panels[key], x=0.5, top=41.8, width=width, edge=edge)
        np.testing.assert_array_equal(np.asarray(axis.images[0].get_array()), panels[key])
        if suffix == 'b':
            text_at(fig, 0.5, 10.8, f"Transfer {state['from_observation']} to {state['to_observation']}", bold=True)
            text_at(fig, 0.5, 7.2, f"{state['accepted_observations']}/12 observations; {state['accepted_required_count']}/9 required")
            # Match the one-decimal coverage labels in the observation montage.
            text_at(fig, 0.5, 3.6, f"Weighted coverage: {100*state['weighted_coverage']:.1f}%")
        fig.canvas.draw()
        for label in fig.texts:
            box = label.get_window_extent(fig.canvas.get_renderer())
            assert box.x0 >= 0 and box.x1 <= fig.bbox.width, label.get_text()
            assert box.y0 >= 0 and box.y1 <= fig.bbox.height, label.get_text()
        fig.savefig(output / f'{STEM}_{suffix}.pdf', dpi=600, facecolor='white')
        fig.savefig(output / f'{STEM}_{suffix}.svg', dpi=600, facecolor='white')
        fig.savefig(output / f'{STEM}_{suffix}.png', dpi=600, facecolor='white')
        plt.close(fig)
        for ext in ('pdf', 'svg', 'png'):
            name = f'{STEM}_{suffix}.{ext}'
            files[name] = sha(output/name)
    manifest = {
        'figure_number': 8, 'width_mm': WIDTH_MM, 'height_mm': HEIGHT_MM,
        'layout': 'Two independent panels assembled with LaTeX subfloat',
        'panel_labels': 'LaTeX-generated; no panel labels or subcaptions in image exports',
        'panel_width_mm': {key: WIDTH_MM*value for key, value in PANEL_FRACTIONS.items()},
        'latex_column_fractions': PANEL_FRACTIONS,
        'generator_sha256': sha(Path(__file__)),
        'source_manifest': str((DATA/'source_manifest.json').relative_to(ROOT)),
        'source_manifest_sha256': sha(DATA/'source_manifest.json'),
        'conclusion': 'The recorded repeat execution presents the global trajectory and a distinct central-module camera view together during transfer from observation 9 to 10.',
        'archetype': 'image plate + progress counts',
        'reuse': 'Approved crops, borders and progress annotations retained; weighted coverage displayed to one decimal place to match the observation montage. Screenshot pixels unchanged.',
        'independent_execution': source['repeat_execution_id'],
        'selected_video_frame_time_s': source['video_frame_time_s'],
        'frame_state': state,
        'panel_a': {'question': 'Where did the spacecraft travel relative to the station?',
                    'crop_xyxy': source['global_crop_xyxy'], 'native_pixels': list(panels['global'].shape[1::-1]),
                    'effective_source_dpi': panels['global'].shape[1]/35.2*25.4},
        'panel_b': {'question': 'What did the onboard camera show during the transfer between observation stops?',
                    'crop_xyxy': source['camera_crop_xyxy'], 'native_pixels': list(panels['camera'].shape[1::-1]),
                    'effective_source_dpi': panels['camera'].shape[1]/41.5*25.4},
        'image_adjustments': 'Exact rectangular crops only; original brightness, contrast, colors, geometry and camera field retained.',
        'replicate_unit': 'One illustrative repeat execution; no uncertainty estimate or aggregate inference.',
        'minimum_label_font_pt': 7.2,
        'files': files,
    }
    (output/'overview_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'figure': 8, 'separate_panels': 2, 'output': str(output)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    generate(parser.parse_args().output_dir)
