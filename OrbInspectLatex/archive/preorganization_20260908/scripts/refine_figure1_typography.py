#!/usr/bin/env python3
"""Compact the selected Figure 1 without changing its scientific content.

Contract: a schematic-led composite explains audited observations/transfers,
complete-tail rollout ADP, and graph-state replanning. Preserve all five panels,
the reference palette, camera/LOS geometry, archived mesh/route/transfer data,
and every mathematical token. Remove only the redundant in-image title, reduce
bold emphasis, and translate objects to reclaim vertical whitespace. Python
exports one native draw.io model to SVG/PDF; photos are not retouched or cropped.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import html
import json
import math
from pathlib import Path
import re
import shutil
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
import zlib

import pymupdf

from align_figure_notation import label_svg, native_value, plain, style_dict, set_style

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'output/figure_notation_aligned_20260908'
OUT = ROOT / 'output/figure1_typography_refined_20260908'
STEM = 'viability_preserving_rollout_adp'
NS = 'http://www.w3.org/2000/svg'
XLINK = 'http://www.w3.org/1999/xlink'
ET.register_namespace('', NS)
ET.register_namespace('xlink', XLINK)
WIDTH, HEIGHT = 1680, 990
PANEL_HEADINGS = {'4', '99', 'hcw-c-1', 'adp-d-1', '235'}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def box(cell):
    geo = cell.find('mxGeometry')
    return tuple(float(geo.get(k, 0)) for k in ('x', 'y', 'width', 'height'))


def set_box(cell, **changes):
    for key, value in changes.items():
        cell.find('mxGeometry').set(key, str(value))


def shift(cell, dy=0, dx=0):
    geo = cell.find('mxGeometry')
    if cell.get('edge'):
        for point in geo.iter('mxPoint'):
            point.set('x', str(float(point.get('x')) + dx))
            point.set('y', str(float(point.get('y')) + dy))
    else:
        x, y, _, _ = box(cell)
        set_box(cell, x=x+dx, y=y+dy)


def edge_points(cell):
    geo = cell.find('mxGeometry')
    nodes = [geo.find("mxPoint[@as='sourcePoint']")]
    nodes += geo.findall('Array/mxPoint')
    nodes += [geo.find("mxPoint[@as='targetPoint']")]
    return [(float(p.get('x')), float(p.get('y'))) for p in nodes]


def set_edge(cell, points):
    geo = cell.find('mxGeometry')
    geo.clear()
    geo.attrib.update({'relative': '1', 'as': 'geometry'})
    for point, role in [(points[0], 'sourcePoint'), (points[-1], 'targetPoint')]:
        ET.SubElement(geo, 'mxPoint', x=str(point[0]), y=str(point[1]), **{'as': role})
    if len(points) > 2:
        arr = ET.SubElement(geo, 'Array', **{'as': 'points'})
        for x, y in points[1:-1]:
            ET.SubElement(arr, 'mxPoint', x=str(x), y=str(y))


def edit_layout(native):
    cells = {c.get('id'): c for c in native.findall('.//mxCell')}
    native.find('.//root').remove(cells['2'])
    model = native.find('.//mxGraphModel')
    model.set('pageHeight', str(HEIGHT))
    model.set('dy', str(HEIGHT))
    model.set('layoutVersion', 'compact-typography-20260908')
    native.find('diagram').set('name', 'Viability-preserving rollout ADP for orbital inspection')

    # Translating scientific illustrations preserves their angles/aspect/data.
    for ident, cell in cells.items():
        if ident in ('0', '1', '2'):
            continue
        if ident.isdigit():
            number = int(ident)
            if 5 <= number <= 95:
                shift(cell, -73)  # unchanged ISS projection and target locations
            elif 100 <= number <= 128:
                shift(cell, -140)  # unchanged LOS/FOV construction and camera
            elif 250 <= number <= 366:
                shift(cell, -142)  # unchanged equal-aspect archived route
        elif ident.startswith('hcw-c-'):
            shift(cell, -72)
        elif ident.startswith('adp-d-'):
            shift(cell, -148)

    placements = {
        '3': (14, 424), '4': (28, 40), '96': (407, None), '97': (397, 34),
        '98': (460, 490), '99': (474, 40), '129': (809, 34),
        '130': (849, 40), '131': (852, 34), '132': (895, 44), '133': (901, 34),
        'hcw-c-0': (14, 346), 'hcw-c-1': (28, 40),
        'hcw-c-2': (82, 38), 'hcw-c-3': (84, 34),
        'hcw-c-4': (82, 38), 'hcw-c-5': (84, 34),
        'hcw-c-6': (82, 38), 'hcw-c-7': (84, 34),
        'hcw-c-8': (127, 34), 'hcw-c-19': (266, 34), 'hcw-c-20': (301, 34),
        'hcw-c-29': (270, 34), 'hcw-c-30': (308, 34),
        'hcw-c-42': (264, 34), 'hcw-c-43': (301, 40), 'hcw-c-44': (304, 34),
        'adp-d-0': (382, 568), 'adp-d-1': (396, 40),
        'adp-d-2': (449, 38), 'adp-d-3': (451, 34),
        'adp-d-4': (449, 38), 'adp-d-5': (451, 34),
        'adp-d-6': (495, 34), 'adp-d-7': (495, 34), 'adp-d-9': (535, 34),
        'adp-d-39': (793, 36), 'adp-d-40': (797, 34),
        'adp-d-43': (842, 37), 'adp-d-44': (844, 34),
        'adp-d-45': (891, 47), 'adp-d-46': (896, 37),
        '234': (14, 936), '235': (28, 40),
        '236': (95, 95), '237': (104, 38), '238': (148, 34),
        '241': (224, 100), '242': (235, 34), '243': (274, 37),
        '245': (355, 76), '246': (365, 57), '248': (440, 34),
        '249': (482, 34), '367': (911, 35), '369': (435, 34),
        '370': (962, 28), '371': (960, 32),
    }
    for ident, (y, height) in placements.items():
        set_box(cells[ident], y=y, **({'height': height} if height is not None else {}))

    # Keep the true motion and geometry plots rigid; only interface connectors reroute.
    replacements = {
        '181': [(450, 204), (480, 204)],
        '182': [(347, 869), (463, 869), (463, 351), (1190, 351), (1190, 341)],
        '232': [(913, 360), (913, 382)],
        '233': [(450, 917), (476, 917), (476, 674), (513, 674)],
        '239': [(1245, 914.5), (1324, 914.5), (1324, 142.5), (1356, 142.5)],
        '240': [(1501, 190), (1501, 224)],
        '244': [(1501, 324), (1501, 355)],
        '247': [(1501, 431), (1501, 474)],
        '368': [(1625, 393), (1650, 393), (1650, 976), (490, 976), (490, 710), (532, 710), (532, 693)],
        'adp-d-41': [(1283, 620), (1294, 620), (1294, 880), (1227, 880), (1227, 891)],
    }
    for ident, points in replacements.items():
        set_edge(cells[ident], points)

    # Widen a few label boxes without moving scientific geometry or changing text.
    set_box(cells['104'], x=28, width=130)
    set_box(cells['119'], x=357, width=82)
    set_box(cells['114'], x=148, y=574, width=154)
    set_box(cells['hcw-c-32'], x=1008, width=49, height=32)
    set_box(cells['adp-d-34'], x=1062, width=217, height=34)
    set_box(cells['adp-d-37'], x=1062, width=217, height=34)
    set_box(cells['370'], x=720, width=362)
    set_box(cells['371'], x=725, width=352)

    for cell in native.findall('.//mxCell'):
        if not cell.get('value'):
            continue
        ident = cell.get('id')
        # Only panel headings remain bold. Maths use the established serif font.
        size = 30 if ident in PANEL_HEADINGS else 26
        if ident in ('133', '243', 'adp-d-35', 'adp-d-38', 'adp-d-46'):
            size = 28
        if ident in ('hcw-c-36', 'hcw-c-37'):
            size = 25
        set_style(cell, fontStyle=int(ident in PANEL_HEADINGS), fontSize=size)
        x, y, w, h = box(cell)
        if h < 34:
            set_box(cell, y=y-(34-h)/2, height=34)
    return cells


def svg_element(tag, **attributes):
    return ET.Element('{'+NS+'}'+tag, {k: str(v) for k, v in attributes.items()})


def line_svg(group, cell, style):
    points = edge_points(cell)
    color, width = style['strokeColor'], float(style['strokeWidth'])
    if style.get('dashed') == '1':
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            length = math.hypot(x2-x1, y2-y1)
            if not length:
                continue
            for offset in range(0, math.ceil(length), 12):
                t0, t1 = offset/length, min(offset+7, length)/length
                group.append(svg_element('line', x1=x1+(x2-x1)*t0, y1=y1+(y2-y1)*t0,
                    x2=x1+(x2-x1)*t1, y2=y1+(y2-y1)*t1,
                    stroke=color, **{'stroke-width': width}))
    else:
        group.append(svg_element('polyline', points=' '.join(f'{x},{y}' for x, y in points),
            fill='none', stroke=color, **{'stroke-width': width, 'stroke-linejoin': 'round'}))
    if style.get('endArrow') == 'block':
        x, y = points[-1]
        px, py = points[-2]
        norm = math.hypot(x-px, y-py)
        ux, uy = (x-px)/norm, (y-py)/norm
        corners = [(x, y), (x-ux*10-uy*4.5, y-uy*10+ux*4.5),
                   (x-ux*10+uy*4.5, y-uy*10-ux*4.5)]
        group.append(svg_element('polygon', points=' '.join(f'{a},{b}' for a, b in corners), fill=color))


def stencil_svg(group, cell, style):
    packed = style['shape'][8:-1]
    xml = urllib.parse.unquote(zlib.decompress(base64.b64decode(packed), -15).decode())
    stencil = ET.fromstring(xml)
    x, y, w, h = box(cell)
    sw, sh = float(stencil.get('w')), float(stencil.get('h'))
    assert abs(w/sw-h/sh) < 1e-9, 'Do not distort an image or scientific stencil'
    group.set('transform', f'translate({x},{y}) scale({w/sw})')
    fill, stroke, width = 'none', 'none', 0
    path = None
    for item in stencil.find('foreground'):
        if item.tag == 'fillcolor':
            fill = item.get('color')
        elif item.tag == 'strokecolor':
            stroke = item.get('color')
        elif item.tag == 'strokewidth':
            width = float(item.get('width'))
        elif item.tag == 'path':
            points = [(p.get('x'), p.get('y')) for p in item if p.tag in ('move', 'line')]
            path = ' '.join(f'{px},{py}' for px, py in points)
        elif item.tag in ('fill', 'fillstroke'):
            group.append(svg_element('polygon', points=path, fill=fill, stroke=stroke,
                **{'stroke-width': width if item.tag == 'fillstroke' else 0}))
        else:
            raise ValueError(item.tag)


def export(native, original_svg, old_cells):
    svg = svg_element('svg', width=WIDTH, height=HEIGHT, viewBox=f'0 0 {WIDTH} {HEIGHT}')
    svg.append(svg_element('rect', width='100%', height='100%', fill='white'))
    rects = {tuple(float(e.get(k)) for k in ('x', 'y', 'width', 'height')): float(e.get('rx', 0))
             for e in original_svg if e.tag == '{'+NS+'}rect' and e.get('x')}
    metrics = []
    for cell in native.findall('.//mxCell'):
        ident = cell.get('id')
        if ident in ('0', '1'):
            continue
        style = style_dict(cell)
        group = svg_element('g', **{'data-cell-id': ident})
        if cell.get('value'):
            if cell.get('notationSource'):
                lines = json.loads(cell.get('notationSource'))
            else:
                lines = [[{'kind': 'text', 'value': text}] for text in plain(cell.get('value')).split('\n')]
            group, metric = label_svg(cell, lines, 'Figure1')
            metrics.append({'id': ident, 'label': plain(cell.get('value')), **metric})
        elif cell.get('edge'):
            line_svg(group, cell, style)
        else:
            x, y, w, h = box(cell)
            if style.get('shape', '').startswith('stencil('):
                stencil_svg(group, cell, style)
            elif style.get('shape') == 'image':
                uri = style['image'].replace('data:image/jpeg,', 'data:image/jpeg;base64,')
                group.append(svg_element('image', x=x, y=y, width=w, height=h,
                    preserveAspectRatio='xMidYMid meet', **{'{'+XLINK+'}href': uri}))
            elif cell.get('style').startswith('ellipse;'):
                assert w == h
                group.append(svg_element('circle', cx=x+w/2, cy=y+h/2, r=w/2,
                    fill=style['fillColor'], stroke=style['strokeColor'],
                    **{'stroke-width': style['strokeWidth']}))
            else:
                radius = rects[box(old_cells[ident])]
                # Explicit absolute corner radius keeps native/export corners aligned.
                set_style(cell, absoluteArcSize=1, arcSize=2*radius)
                group.append(svg_element('rect', x=x, y=y, width=w, height=h, rx=radius,
                    fill=style['fillColor'], stroke=style['strokeColor'],
                    **{'stroke-width': style['strokeWidth']}))
        svg.append(group)
    raw = ET.tostring(svg, encoding='utf-8', xml_declaration=True)
    (OUT / f'{STEM}.svg').write_bytes(raw)
    ET.ElementTree(native).write(OUT / f'{STEM}.drawio', encoding='utf-8', xml_declaration=True)
    source = pymupdf.open(stream=raw, filetype='svg')
    converted = pymupdf.open('pdf', source.convert_to_pdf())
    pdf = pymupdf.open()
    width_pt = 182/25.4*72
    page = pdf.new_page(width=width_pt, height=width_pt*HEIGHT/WIDTH)
    page.show_pdf_page(page.rect, converted, 0)
    pdf.set_metadata({'title': 'Viability-preserving rollout ADP for orbital inspection',
                      'subject': 'Compact typography; editable native draw.io source'})
    pdf.save(OUT / f'{STEM}.pdf', garbage=4, deflate=True)
    page.get_pixmap(dpi=220).save(OUT / f'{STEM}.png')
    return svg, metrics


def verify(original, native, svg, metrics):
    old = {c.get('id'): c for c in original.findall('.//mxCell')}
    new = {c.get('id'): c for c in native.findall('.//mxCell')}
    assert set(old) - set(new) == {'2'}
    assert set(new) - set(old) == set()
    for ident, cell in new.items():
        prev = old[ident]
        if prev.get('notationSource'):
            assert json.loads(prev.get('notationSource')) == json.loads(cell.get('notationSource'))
        elif prev.get('value'):
            assert plain(prev.get('value')).split() == plain(cell.get('value')).split()
        pstyle, nstyle = style_dict(prev), style_dict(cell)
        for key in ('fillColor', 'strokeColor', 'fontColor', 'shape', 'image', 'strokeWidth', 'endArrow', 'dashed'):
            assert pstyle.get(key) == nstyle.get(key), (ident, key)
        if cell.get('value'):
            group = next(g for g in svg if g.get('data-cell-id') == ident)
            assert cell.get('notationSource') == group.get('data-notation-source')
            math_tokens = [r['value'] for line in json.loads(cell.get('notationSource')) for r in line if r['kind'] == 'math']
            assert re.findall(r'\\\((.*?)\\\)', html.unescape(cell.get('value')), re.S) == math_tokens
    # These illustrations must be rigid translations, not arbitrary rescaling.
    rigid = [(list(map(str, range(5, 96))), -73),
             ([str(i) for i in range(100, 129) if not old[str(i)].get('value')], -140),
             ([str(i) for i in range(250, 367) if not old[str(i)].get('value')], -142),
             (['hcw-c-'+str(i) for i in (9, 10, 11, 12, 15, 16)], -72)]
    for ids, dy in rigid:
        for ident in ids:
            if old[ident].get('edge'):
                assert all(abs(a-c)<1e-7 and abs(b+dy-d)<1e-7
                    for (a, b), (c, d) in zip(edge_points(old[ident]), edge_points(new[ident])))
            else:
                x, y, w, h = box(old[ident])
                nx, ny, nw, nh = box(new[ident])
                assert abs(x-nx)<1e-7 and abs(y+dy-ny)<1e-7 and w == nw and h == nh
    return {
        'scope': 'Figure 1 title, typography, and vertical spacing only',
        'canvas_before': [1680, 1160], 'canvas_after': [WIDTH, HEIGHT],
        'height_reduction_percent': round(100*(1-HEIGHT/1160), 2),
        'only_deleted_object': 'Redundant in-image title',
        'all_other_text_and_math_preserved': True,
        'palette_camera_bytes_stencil_data_preserved': True,
        'rigid_scientific_illustrations_verified': True,
        'native_svg_geometry_from_same_cells': True,
        'native_export_math_tokens_equal': True,
        'bold_labels_before': sum(bool(int(style_dict(c).get('fontStyle', 0)) & 1) for c in old.values() if c.get('value')),
        'bold_labels_after': len(PANEL_HEADINGS),
        'label_metrics': metrics,
        'live_drawio_rendering': 'Not verified; native/source parity and PDF rendering are checked separately.',
        'visual_review': 'pending',
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    saved = {p: sha(p) for p in [SOURCE/'A_integrated.drawio', SOURCE/'A_integrated.svg', ROOT/'OrbInspectLatex/main.tex']}
    original = ET.parse(SOURCE/'A_integrated.drawio').getroot()
    native = copy.deepcopy(original)
    original_svg = ET.parse(SOURCE/'A_integrated.svg').getroot()
    old_cells = {c.get('id'): c for c in original.findall('.//mxCell')}
    edit_layout(native)
    svg, metrics = export(native, original_svg, old_cells)
    report = verify(original, native, svg, metrics)
    assert all(sha(p) == value for p, value in saved.items())
    (OUT/'QA.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    shutil.copy2(SOURCE/'NOTATION_NOTES.md', OUT/'NOTATION_NOTES.md')
    (OUT/'source').mkdir(exist_ok=True)
    for name in ('refine_figure1_typography.py', 'align_figure_notation.py'):
        shutil.copy2(Path(__file__).with_name(name), OUT/'source'/name)
    print(json.dumps({k:v for k,v in report.items() if k != 'label_metrics'}, indent=2))
    print('Fitted label sizes:', sorted({round(m['font_size'], 2) for m in metrics}))


if __name__ == '__main__':
    main()
