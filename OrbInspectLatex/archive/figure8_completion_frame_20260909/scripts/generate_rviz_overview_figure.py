#!/usr/bin/env python3
"""Build Figure 8 from two exact crops of one recorded RViz video frame."""
from __future__ import annotations

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
WIDTH_MM, HEIGHT_MM = 85.0, 46.0
TRIM_BOTTOM_MM = 9.0


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_at(fig, x: float, y: float, value: str, *, bold: bool = False):
    return fig.text(x / WIDTH_MM, (y-TRIM_BOTTOM_MM) / HEIGHT_MM, value, va='top', ha='left',
                    fontsize=7.5 if bold else 7.2,
                    fontweight='bold' if bold else 'normal', color='#111820')


def image_panel(fig, pixels, *, x, top, width, edge):
    height = width * pixels.shape[0] / pixels.shape[1]
    axis = fig.add_axes((x / WIDTH_MM, (top-height-TRIM_BOTTOM_MM) / HEIGHT_MM,
                         width / WIDTH_MM, height / HEIGHT_MM))
    # Native pixels are embedded in PDF/SVG. No local or global image adjustment.
    axis.imshow(pixels, interpolation='none', aspect='equal')
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_color(edge)
        spine.set_linewidth(0.65)
    return axis


def main() -> None:
    source = json.loads((DATA / 'source_manifest.json').read_text())
    for name, digest in source['files'].items():
        assert sha(DATA/name) == digest, f'Source changed: {name}'
    summary = json.loads((DATA / 'capture_summary.json').read_text())
    audit = json.loads((DATA / 'required_target_execution_audit.json').read_text())
    assert audit['passed'] and audit['accepted_observations'] == 12
    assert audit['accepted_required_count'] == 9
    assert summary['weighted_coverage'] == audit['accepted_background_coverage']
    frame = np.asarray(Image.open(DATA / 'video_completion.png').convert('RGB'))
    assert list(frame.shape[1::-1]) == source['source_dimensions_px']
    panels = {}
    for key in ('global', 'camera'):
        x0, y0, x1, y1 = source[f'{key}_crop_xyxy']
        panels[key] = frame[y0:y1, x0:x1].copy()

    # Inherit the approved Figure 7 typography and white outer canvas. Retain
    # the original RViz colors inside the screenshot and the view-12 border.
    mpl.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 7.2, 'svg.fonttype': 'none', 'pdf.fonttype': 42,
        'ps.fonttype': 42, 'figure.facecolor': 'white',
        'savefig.facecolor': 'white', 'svg.hashsalt': 'orbinspect-fig8-rviz',
    })
    fig = plt.figure(figsize=(WIDTH_MM/25.4, HEIGHT_MM/25.4))
    text_at(fig, 0.5, 54.7, '(a) Global trajectory', bold=True)
    text_at(fig, 43.0, 54.7, '(b) Onboard camera', bold=True)
    image_panel(fig, panels['global'], x=0.5, top=50.8, width=35.2, edge='#8A939C')
    image_panel(fig, panels['camera'], x=43.0, top=50.8, width=41.5, edge='#7E4A9E')
    text_at(fig, 43.0, 19.8, 'Mission complete', bold=True)
    text_at(fig, 43.0, 16.2, f"{audit['accepted_observations']}/12 observations; {audit['accepted_required_count']}/9 required")
    text_at(fig, 43.0, 12.6, f"Weighted coverage: {100*audit['accepted_background_coverage']:.2f}%")
    fig.canvas.draw()
    for label in fig.texts:
        box = label.get_window_extent(fig.canvas.get_renderer())
        assert box.x0 >= 0 and box.x1 <= fig.bbox.width, label.get_text()
        assert box.y0 >= 0 and box.y1 <= fig.bbox.height, label.get_text()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / f'{STEM}.pdf', dpi=600, facecolor='white')
    fig.savefig(OUTPUT / f'{STEM}.svg', dpi=600, facecolor='white')
    fig.savefig(OUTPUT / f'{STEM}.png', dpi=600, facecolor='white')
    plt.close(fig)
    manifest = {
        'figure_number': 8, 'width_mm': WIDTH_MM, 'height_mm': HEIGHT_MM,
        'source_manifest': str((DATA/'source_manifest.json').relative_to(ROOT)),
        'source_manifest_sha256': sha(DATA/'source_manifest.json'),
        'conclusion': 'The recorded repeat execution presents the global trajectory and onboard camera together in RViz at mission completion.',
        'archetype': 'image plate + completion counts',
        'reuse': 'Style-only inheritance from Figure 7; screenshot pixels unchanged.',
        'independent_execution': source['repeat_execution_id'],
        'panel_a': {'question': 'Where did the spacecraft travel relative to the station?',
                    'crop_xyxy': source['global_crop_xyxy'], 'native_pixels': list(panels['global'].shape[1::-1]),
                    'effective_source_dpi': panels['global'].shape[1]/35.2*25.4},
        'panel_b': {'question': 'What did the onboard camera show at completion?',
                    'crop_xyxy': source['camera_crop_xyxy'], 'native_pixels': list(panels['camera'].shape[1::-1]),
                    'effective_source_dpi': panels['camera'].shape[1]/41.5*25.4},
        'image_adjustments': 'Exact rectangular crops only; original brightness, contrast, colors, geometry and camera field retained.',
        'replicate_unit': 'One illustrative repeat execution; no uncertainty estimate or aggregate inference.',
        'minimum_label_font_pt': 7.2,
        'files': {f'{STEM}.{ext}': sha(OUTPUT/f'{STEM}.{ext}') for ext in ('pdf', 'svg', 'png')},
    }
    (OUTPUT/'overview_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'figure': 8, 'dimensions_mm': [WIDTH_MM, HEIGHT_MM], 'output': str(OUTPUT)}, indent=2))


if __name__ == '__main__':
    main()
