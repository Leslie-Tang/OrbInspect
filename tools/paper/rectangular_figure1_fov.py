#!/usr/bin/env python3
"""Revise only Figure 1's camera panel to show a rectangular angular FOV.

Style-only inheritance: keep the current native diagram and exported objects,
camera photo, palette, and typography. The perspective pyramid is schematic;
its two principal-plane half-angles match the manuscript's visibility bounds.
No measured imagery or experimental data are changed.
"""
from __future__ import annotations

import argparse
import base64
import copy
import json
import math
from pathlib import Path
import shutil
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

import matplotlib as mpl
import pymupdf
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

from align_figure_notation import label_svg, structure, style_dict, set_style
from refine_figure1_typography import set_box, set_edge, line_svg, stencil_svg, svg_element

ROOT = Path(__file__).resolve().parents[2]
STEM = 'viability_preserving_rollout_adp'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
ET.register_namespace('xhtml', 'http://www.w3.org/1999/xhtml')
mpl.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'DejaVu Sans'],
                     'svg.fonttype': 'none', 'pdf.fonttype': 42})


def polygon_stencil(cell, polygons):
    """Encode the projected faces as editable native draw.io stencil paths."""
    points = [p for poly in polygons for p in poly]
    x, y = min(p[0] for p in points), min(p[1] for p in points)
    w, h = max(p[0] for p in points)-x, max(p[1] for p in points)-y
    shape = ET.Element('shape', name='Rectangular camera FOV', w=str(w), h=str(h),
                       aspect='fixed', strokewidth='inherit')
    fg = ET.SubElement(shape, 'foreground')
    for polygon in polygons:
        ET.SubElement(fg, 'fillcolor', color='#F0EDF4')
        ET.SubElement(fg, 'strokecolor', color='#8771AA')
        ET.SubElement(fg, 'strokewidth', width='1.1', fixed='1')
        path = ET.SubElement(fg, 'path')
        for i, (px, py) in enumerate(polygon):
            ET.SubElement(path, 'move' if i == 0 else 'line', x=str(px-x), y=str(py-y))
        ET.SubElement(path, 'close')
        ET.SubElement(fg, 'fillstroke')
    compressor = zlib.compressobj(wbits=-15)
    encoded = urllib.parse.quote(ET.tostring(shape, encoding='unicode')).encode()
    packed = base64.b64encode(compressor.compress(encoded)+compressor.flush()).decode()
    set_style(cell, shape=f'stencil({packed})')
    set_box(cell, x=x, y=y, width=w, height=h)
    cell.set('tooltip', 'Rectangular angular FOV; horizontal and vertical half-angles are independent. Range is checked separately.')


def arc(origin, endpoint, radius):
    """Project a schematic half-angle from the boresight to its plane limit."""
    angle = math.atan2(endpoint[1]-origin[1], endpoint[0]-origin[0])
    return [(origin[0]+radius*math.cos(angle*i/24),
             origin[1]+radius*math.sin(angle*i/24)) for i in range(25)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'OrbInspectLatex/figures/fig01_framework')
    parser.add_argument('--output', type=Path, default=ROOT/'output/figure1_rectangular_fov_20261009')
    parser.add_argument('--chrome', default=shutil.which('google-chrome') or shutil.which('chromium'),
                        help='Chromium executable; defaults to a browser found on PATH')
    args = parser.parse_args()
    if not args.chrome:
        parser.error('A Chromium browser is required; specify --chrome.')
    args.output.mkdir(parents=True, exist_ok=True)
    native = ET.parse(args.source/f'{STEM}.drawio').getroot()
    svg = ET.parse(args.source/f'{STEM}.svg').getroot()
    original = copy.deepcopy(native)
    original_svg = copy.deepcopy(svg)
    root = native.find('.//root')
    cells = {c.get('id'): c for c in native.findall('.//mxCell')}
    groups = {g.get('data-cell-id'): g for g in svg.iter() if g.get('data-cell-id')}
    parents = {child: parent for parent in svg.iter() for child in parent}
    modified = {'100', '101', '114', '116', '117', '118', '119'}
    added = set()

    def clone(ident, template):
        added.add(ident)
        if ident in cells:
            return cells[ident]
        cell = copy.deepcopy(cells[template])
        cell.set('id', ident)
        # Keep new geometry behind the LOS/mesh annotations.
        root.insert(list(root).index(cells['102']), cell)
        cells[ident] = cell
        return cell

    origin = (111.2, 662.6)
    center = (355, 662.6)
    horizontal = (421, 692.6)
    vertical = (355, 563.6)
    corners = [(289, 533.6), (421, 593.6), (421, 791.6), (289, 731.6)]
    # An oblique projection of a rectangle: opposite sides remain parallel.
    assert all(abs(corners[0][i]+corners[2][i]-2*center[i]) < 1e-8 for i in (0, 1))
    polygon_stencil(cells['100'], [[origin, corners[0], corners[1]],
                                  [origin, corners[3], corners[2]], corners])
    set_edge(cells['101'], [origin, center])
    for ident, endpoint in [('fov-h-ray', horizontal), ('fov-v-ray', vertical)]:
        cell = clone(ident, '101')
        set_style(cell, endArrow='none', strokeWidth=1.1)
        set_edge(cell, [origin, endpoint])
    set_edge(cells['116'], arc(origin, vertical, 64))
    set_edge(clone('fov-h-arc', '116'), arc(origin, horizontal, 102))
    set_box(cells['117'], x=45, y=549, width=100, height=44)
    v_lines = [[{'kind': 'math', 'value': r'\displaystyle \alpha_{\max}^{\mathrm{v}}'}]]
    cells['117'].set('notationSource', json.dumps(v_lines))
    label = clone('fov-h-label', '117')
    set_box(label, x=151, y=728, width=100, height=44)
    label.set('notationSource', json.dumps([[{'kind': 'math', 'value': r'\displaystyle \alpha_{\max}^{\mathrm{h}}'}]]))
    set_edge(cells['118'], [(115, 593), (174, 650)])
    set_edge(clone('fov-h-leader', '118'), [(204, 728), (213, 668)])
    set_box(cells['114'], x=145, y=524)
    set_box(cells['119'], x=337, y=697)

    metrics = []
    for ident in sorted(modified | added):
        cell = cells[ident]
        group = svg_element('g', **{'data-cell-id': ident})
        if cell.get('value'):
            group, metric = label_svg(cell, json.loads(cell.get('notationSource')), 'Figure1')
            metrics.append({'id': ident, **metric})
        elif cell.get('edge'):
            line_svg(group, cell, style_dict(cell))
        else:
            stencil_svg(group, cell, style_dict(cell))
        # The approved diagrams.net SVG crops native coordinates by (16, 14).
        wrapper = svg_element('g', transform='translate(-16,-14)')
        wrapper.append(group)
        if ident in groups:
            target = groups[ident]
            parent = parents[target]
            if parent.get('transform') == 'translate(-16,-14)' and len(parent) == 1:
                target, parent = parent, parents[parent]
            index = list(parent).index(target)
            parent.remove(target)
            parent.insert(index, wrapper)
        else:
            parent = parents[groups['102']]
            parent.insert(list(parent).index(groups['102']), wrapper)

    old_cells = {c.get('id'): c for c in original.findall('.//mxCell')}
    assert all(structure(cell) == structure(old_cells[ident])
               for ident, cell in cells.items() if ident not in modified | added)
    old_groups = {g.get('data-cell-id'): g for g in original_svg.iter() if g.get('data-cell-id')}
    new_groups = {g.get('data-cell-id'): g for g in svg.iter() if g.get('data-cell-id')}
    assert all(structure(group) == structure(new_groups[ident])
               for ident, group in old_groups.items() if ident not in modified | added | {'0', '1'})
    ET.ElementTree(native).write(args.output/f'{STEM}.drawio', encoding='utf-8', xml_declaration=True)
    raw = ET.tostring(svg, encoding='unicode')
    raw = '\n'.join(line.rstrip(' \t') for line in raw.splitlines())+'\n'
    (args.output/f'{STEM}.svg').write_text(raw)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chrome, headless=True)
        page = browser.new_page(viewport={'width': 1650, 'height': 983}, device_scale_factor=1)
        # Load as XML so XHTML line breaks and embedded MathJax retain namespaces.
        page.goto((args.output/f'{STEM}.svg').resolve().as_uri())
        page.evaluate('document.fonts.ready')
        page.locator('svg').first.screenshot(path=str(args.output/f'{STEM}.png'))
        page.pdf(path=str(args.output/f'{STEM}.pdf'), width='1650px', height='983px',
                 print_background=True, margin={key:'0' for key in ('top','bottom','left','right')})
        browser.close()
    before = Image.open(args.source/f'{STEM}.png').convert('RGB')
    after = Image.open(args.output/f'{STEM}.png').convert('RGB')
    assert before.size == after.size
    changed_bounds = ImageChops.difference(before, after).getbbox()
    if changed_bounds:
        x0, y0, x1, y1 = changed_bounds
        assert 0 <= x0 <= x1 <= 434 and 500 <= y0 <= y1 <= 805, changed_bounds
    doc = pymupdf.open(args.output/f'{STEM}.pdf')
    doc[0].get_pixmap(matrix=pymupdf.Matrix(1, 1), clip=pymupdf.Rect(0, 330, 325, 705)).save(args.output/'panel_II.png')
    report = {
        'scope': 'Panel II rectangular FOV geometry and its two half-angle labels',
        'modified_native_ids': sorted(modified), 'new_native_ids': sorted(added),
        'other_native_cells_and_svg_objects_identical': True,
        'source_camera_photo_unchanged': True,
        'preview_difference_bounds': changed_bounds,
        'other_panels_pixel_identical': True,
        'fov_shape': 'Perspective rectangular pyramid; range gate remains independent',
        'half_angles': [r'\alpha_{\max}^{\mathrm h}', r'\alpha_{\max}^{\mathrm v}'],
        'label_metrics': metrics,
        'reuse_level': 'Style-only inheritance; current five-panel native source',
        'backend': 'Python XML geometry and existing math renderer; Chromium SVG/PDF export via Python',
        'typography_exemption': 'Preserve existing paper styling and math-path export; final-size visual review required.',
        'preflight_warnings': 'Font sizes inherited from native cells; vector PDF is the manuscript asset; PNG is a preview, not a TIFF submission asset. Manuscript controls final width at 0.85 linewidth.',
        'visual_review': 'pending',
    }
    (args.output/'QA.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
