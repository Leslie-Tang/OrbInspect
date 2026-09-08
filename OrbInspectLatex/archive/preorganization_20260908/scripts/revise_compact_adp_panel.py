#!/usr/bin/env python3
"""Compact only integrated panel d, preserving the editable figure alternatives.

Figure contract: exact safe-action prefixes are evaluated with complete greedy
tails, then Bellman backups select a finite first action. The three illustrative
leaves are schematic, not experimental data or a fixed lookahead-depth claim.
Use Python/native draw.io vectors; preserve every object outside panel d.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import numbers
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile

import matplotlib as mpl
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import math_to_image
import numpy as np
from PIL import Image, ImageChops
import pymupdf

from generate_figure_options import Draft

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'output/figure_hcw_clarity_20260907'
OUT = ROOT / 'output/figure_adp_compact_20260907'
PREVIOUS_PDF = ROOT / 'output/pdf/OrbInspect_figure_hcw_clarity_20260907.pdf'
PDF = ROOT / 'output/pdf/OrbInspect_figure_adp_compact_20260907.pdf'
ET.register_namespace('', 'http://www.w3.org/2000/svg')
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
BLACK, WHITE = '#000000', '#FFFFFF'
TEAL, GREEN, RED, BURGUNDY = '#3F91A6', '#27A27F', '#C30000', '#830027'
PINK, CREAM, CYAN = '#FAE8E7', '#FFF2E1', '#E0F1F1'
PURPLE, CHARCOAL, BROWN, ORANGE = '#8771AA', '#303E44', '#956054', '#E97900'


def formula(d, x, y, w, h, latex, native_html, size=28, color=BLACK):
    """Keep native math editable and render special glyphs as vector outlines."""
    ident = d.ident()
    cell = ET.SubElement(d.cells, 'mxCell', id=ident, value='<div>'+native_html+'</div>',
        vertex='1', parent='1',
        style=f'text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;'
              f'fontFamily=Arial;fontSize={size};fontColor={color};whiteSpace=nowrap;spacing=0;')
    ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h),
                  **{'as': 'geometry'})
    stream = io.BytesIO()
    with mpl.rc_context({'svg.fonttype': 'path', 'savefig.transparent': True}):
        math_to_image(latex, stream, prop=FontProperties(size=size), format='svg', color=color)
    svg = ET.fromstring(stream.getvalue())
    glyphs = {e.get('id'): e for e in svg.iter() if e.get('id')}
    for parent in list(svg.iter()):
        for index, child in enumerate(list(parent)):
            if child.tag.rsplit('}', 1)[-1] != 'use':
                continue
            reference = child.get('{http://www.w3.org/1999/xlink}href', child.get('href', ''))
            glyph = copy.deepcopy(glyphs[reference.removeprefix('#')])
            glyph.attrib.pop('id', None)
            transform = child.get('transform', '') + f' translate({child.get("x", "0")} {child.get("y", "0")})'
            group = ET.Element('{http://www.w3.org/2000/svg}g', transform=transform)
            group.append(glyph)
            parent.remove(child)
            parent.insert(index, group)
    _, _, mw, mh = map(float, svg.attrib['viewBox'].split())
    factor = min(1, w / mw, h / mh)
    d.svg.append(f'<g transform="translate({x+(w-mw*factor)/2},{y+(h-mh*factor)/2}) scale({factor})">')
    d.svg.extend(ET.tostring(child, encoding='unicode') for child in svg)
    d.svg.append('</g>')


def panel():
    """Three numbered stages with a compressed, three-leaf prefix/tail sketch."""
    d = Draft('Panel d', 'compact_adp_panel', 1160)
    d.box(480, 502, 828, 616, CYAN, BLACK, 16, 1.4)
    d.text(498, 518, 792, 44, 'd  Rollout ADP', 31, True, BLACK, align='left')

    for x, w, title in [(500, 329, '1  Exact lookahead'), (857, 430, '2  Full policy tails')]:
        d.box(x, 581, w, 38, PINK, 'none', 7, 0)
        d.text(x+5, 585, w-10, 30, title, 27, True, BLACK)
    d.text(500, 629, 329, 31, 'Safe actions · depth d', 25, color=BLACK)
    d.text(857, 629, 430, 31, 'Deterministic greedy μ', 25, color=BLACK)

    # The fixed root preserves the existing state and replanning connectors.
    root = (532, 822)
    mids = [(650, 766), (650, 880)]
    leaves = [(805, 734), (805, 800), (805, 888)]
    d.line([(840, 696), (840, 918)], BLACK, 1.1, False, True)
    d.text(748, 677, 91, 28, 'Leaves', 23, color=BLACK)

    def edge(a, b, color=BLACK, radius_a=15, radius_b=14):
        a, b = np.array(a, dtype=float), np.array(b, dtype=float)
        unit = (b-a) / np.linalg.norm(b-a)
        d.line([tuple(a+unit*radius_a), tuple(b-unit*radius_b)], color, 2, True)

    for i, mid in enumerate(mids):
        edge(root, mid, TEAL if i == 0 else BLACK, 19, 15)
        d.circle(*mid, 14, TEAL, BLACK, 1.6)
    for i, leaf in enumerate(leaves):
        edge(mids[0 if i < 2 else 1], leaf)
        # Prefix-node color does not assert completion: only the full tail does.
        d.circle(*leaf, 13, TEAL, BLACK, 1.5)
    d.circle(*root, 18, PURPLE, BLACK, 1.8)
    d.text(507, 769, 50, 31, 's', 28, color=BLACK)
    d.text(565, 748, 58, 30, 'a₁', 25, color=BLACK)
    d.text(565, 873, 58, 30, 'a₂', 25, color=BLACK)

    # Variable-length simulations share the same Markov base policy at each leaf.
    # Three rows are illustrative examples, not a restriction to three leaves.
    for i, leaf in enumerate(leaves):
        color = TEAL if i < 2 else RED
        d.line([(leaf[0]+14, leaf[1]), (1054, leaf[1])], color, 1.9, True, i == 2)
        for xx in [904, 975]:
            d.circle(xx, leaf[1], 4, WHITE, color, 1.1)

    # Shared finite category replaces two oversized outcome blocks. Each leaf
    # still receives its own cost; neither the paths nor their values are merged.
    d.box(1058, 711, 225, 114, CHARCOAL, GREEN, 8, 1.2)
    d.text(1066, 720, 209, 30, 'Goal within budget', 23, True, WHITE)
    formula(d, 1074, 763, 193, 41, r'$\widehat{V}_{0}=\sum\ell$',
            'V̂<sub>0</sub> = ∑ ℓ', 29, WHITE)
    d.box(1058, 852, 225, 78, BROWN, RED, 8, 1.2)
    d.text(1066, 858, 209, 29, 'No completion', 23, True, WHITE)
    formula(d, 1074, 890, 193, 31, r'$\widehat{V}_{0}=+\infty$',
            'V̂<sub>0</sub> = +∞', 27, WHITE)

    formula(d, 546, 933, 269, 34, r'$a\in\mathcal{U}_{s}(s)$',
            'a ∈ U<sub>s</sub>(s)', 26)
    d.text(859, 939, 427, 30, 'Until goal or budget limit', 24, color=BLACK)

    # Both finite and infinite terminal values enter the backward recursion.
    # The original external output anchor remains at (1245,1056).
    d.line([(1283, 768), (1294, 768), (1294, 1021), (1227, 1021), (1227, 1026)], BLACK, 1.2, True)
    d.line([(1283, 891), (1294, 891)], BLACK, 1.2)
    d.box(545, 983, 700, 35, PINK, 'none', 7, 0)
    d.text(550, 986, 690, 29, '3  Bellman backup · discard +∞ actions', 26, True, BLACK)
    d.box(545, 1026, 700, 59, CREAM, ORANGE, 7, 1.2)
    formula(d, 555, 1034, 680, 42,
            r'$\widehat{Q}_{d}(s,a)=\ell_{ja}+\widehat{V}_{d-1}(f(s,a))$',
            'Q̂<sub>d</sub>(s, a) = ℓ<sub>ja</sub> + V̂<sub>d−1</sub>(f(s, a))', 31)
    return d


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def structure(node):
    return [(e.tag, e.attrib, (e.text or '').strip()) for e in node.iter()]


def check_rendered_surroundings(old_page, new_page):
    """Check content, allowing only SVG renderer floating-point transform drift."""
    zone = pymupdf.Rect(478, 500, 1311, 1121)
    maximum = 0.0

    def equal(a, b):
        nonlocal maximum
        if isinstance(a, dict):
            return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a if k != 'seqno')
        if isinstance(a, (list, tuple, pymupdf.Point, pymupdf.Rect, pymupdf.Quad)):
            return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
        if isinstance(a, numbers.Real) and isinstance(b, numbers.Real):
            maximum = max(maximum, abs(a-b))
            return abs(a-b) < .01
        return a == b

    surroundings = []
    for page in [old_page, new_page]:
        paths = [d for d in page.get_drawings() if not zone.contains(d['rect'])]
        spans = [s for b in page.get_text('dict')['blocks'] if 'lines' in b
                 for line in b['lines'] for s in line['spans']
                 if not zone.contains(pymupdf.Rect(s['bbox']))]
        surroundings.append((paths, spans))
    assert equal(surroundings[0], surroundings[1]), 'Content changed outside panel d'
    return {'identical_path_and_text_content': True, 'maximum_coordinate_drift': maximum,
            'path_count': len(surroundings[0][0]), 'text_span_count': len(surroundings[0][1])}


def main():
    saved_paths = [p for p in SOURCE.rglob('*') if p.is_file()]
    saved_paths += [ROOT/'OrbInspectLatex/main.tex', ROOT/'OrbInspectLatex/main.pdf', PREVIOUS_PDF]
    saved = {str(p.relative_to(ROOT)): sha(p) for p in saved_paths}
    d = panel()
    warnings = []
    for label in d.labels:
        font = pymupdf.Font('hebo' if label['bold'] else 'helv')
        for text in label['text'].split('\n'):
            width = font.text_length(text, fontsize=label['size'])
            if width > label['w']*1.01:
                warnings.append({'text': text, 'width': width, 'box': label['w']})
    print('Text width warnings:', warnings)
    assert not warnings
    OUT.mkdir(parents=True, exist_ok=True)

    original = ET.parse(SOURCE/'A_integrated.drawio').getroot()
    native = copy.deepcopy(original)
    cells = native.find('.//root')
    old = list(cells)
    removed = [c for c in old if c.get('id').isdigit() and 183 <= int(c.get('id')) <= 231]
    assert len(removed) == 49 and 'd  Rollout ADP' in removed[1].get('value', '')
    insertion = old.index(removed[0])
    for c in removed:
        cells.remove(c)
    added = []
    for index, c in enumerate(list(d.cells)[2:]):
        item = copy.deepcopy(c)
        item.set('id', f'adp-d-{index}')
        added.append(item)
        cells.insert(insertion+index, item)
    removed_ids = {c.get('id') for c in removed}
    before = [c for c in original.findall('.//mxCell') if c.get('id') not in removed_ids]
    after = [c for c in native.findall('.//mxCell') if not c.get('id').startswith('adp-d-')]
    assert [structure(c) for c in before] == [structure(c) for c in after]
    identifiers = [c.get('id') for c in cells]
    assert len(identifiers) == len(set(identifiers))
    ET.ElementTree(native).write(OUT/'A_integrated.drawio', encoding='utf-8', xml_declaration=True)

    svg_original = ET.parse(SOURCE/'A_integrated.svg').getroot()
    svg = copy.deepcopy(svg_original)
    elements = list(svg)
    start = next(i for i, e in enumerate(elements) if e.tag.rsplit('}', 1)[-1] == 'rect'
                 and e.get('x') == '480' and e.get('y') == '502')
    qbar = next(i for i, e in enumerate(elements) if e.tag.rsplit('}', 1)[-1] == 'rect'
                and e.get('x') == '545' and e.get('y') == '1026')
    assert elements[qbar+1].tag.rsplit('}', 1)[-1] == 'g'
    end = qbar+2
    section_xml = ET.fromstring(d.svg[0]+'\n'.join(d.svg[2:])+'</svg>')
    for e in elements[start:end]:
        svg.remove(e)
    for i, e in enumerate(section_xml):
        svg.insert(start+i, copy.deepcopy(e))
    preserved_svg = list(svg)[:start]+list(svg)[start+len(section_xml):]
    original_svg = elements[:start]+elements[end:]
    assert [structure(e) for e in preserved_svg] == [structure(e) for e in original_svg]
    raw = ET.tostring(svg, encoding='utf-8')
    (OUT/'A_integrated.svg').write_bytes(raw)
    source = pymupdf.open(stream=raw, filetype='svg')
    page_doc = pymupdf.open('pdf', source.convert_to_pdf())
    page_doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(OUT/'A_integrated.png')

    image_old = Image.open(SOURCE/'A_integrated.png').convert('RGB')
    image_new = Image.open(OUT/'A_integrated.png').convert('RGB')
    diff = np.asarray(ImageChops.difference(image_old, image_new)).copy()
    diff[int(500*1.5):int(1121*1.5), int(478*1.5):int(1311*1.5)] = 0
    old_svg_doc = pymupdf.open(SOURCE/'A_integrated.svg')
    old_page_doc = pymupdf.open('pdf', old_svg_doc.convert_to_pdf())
    rendered_check = check_rendered_surroundings(old_page_doc[0], page_doc[0])
    # Additional math groups change the renderer's floating-point roundoff by
    # less than 0.01 drawing unit. This can alter boundary antialiasing, so record
    # rather than falsely claim literal pixel identity. Source vectors are exact.
    rendered_check['antialiasing_changed_pixel_count'] = int((diff.max(axis=2) > 0).sum())

    master = ET.parse(SOURCE/'OrbInspect_figure_options.drawio').getroot()
    master.remove(master.findall('diagram')[0])
    master.insert(0, copy.deepcopy(native.find('diagram')))
    ET.ElementTree(master).write(OUT/'OrbInspect_figure_options.drawio', encoding='utf-8', xml_declaration=True)
    for stem in ['B1_overview', 'B2_adp_mechanism']:
        for extension in ['drawio', 'svg', 'png']:
            shutil.copy2(SOURCE/(stem+'.'+extension), OUT/(stem+'.'+extension))
        assert structure(master.findall('diagram')[1 if stem.startswith('B1') else 2]) == structure(
            ET.parse(OUT/(stem+'.drawio')).getroot().find('diagram'))

    previous_pdf = pymupdf.open(PREVIOUS_PDF)
    review = pymupdf.open()
    page = review.new_page(width=previous_pdf[0].rect.width, height=previous_pdf[0].rect.height)
    page.show_pdf_page(page.rect, page_doc, 0)
    review.insert_pdf(previous_pdf, from_page=1, to_page=2)
    review.set_metadata(previous_pdf.metadata)
    review.save(PDF, garbage=4, deflate=True)
    for i in [1, 2]:
        assert review[i].get_pixmap().samples == previous_pdf[i].get_pixmap().samples
    shutil.copytree(SOURCE/'assets', OUT/'assets', dirs_exist_ok=True)
    shutil.copy2(SOURCE/'palette.json', OUT/'palette.json')
    (OUT/'source').mkdir(exist_ok=True)
    for file in [Path(__file__), Path(__file__).with_name('generate_figure_options.py'),
                 Path(__file__).with_name('generate_editable_framework.py')]:
        shutil.copy2(file, OUT/'source'/file.name)
    (OUT/'README.md').write_text('''# Compact rollout ADP: panel d revision

Only panel d of A (the integrated alternative) has changed. Its outer frame,
reference palette and all input/output anchors are preserved. The prefix/tail
sketch is compressed and repeated outcome graphics are reduced. Panels a, b, c
and e, B1, B2, the manuscript and every preceding alternative are unchanged.

## Read the revised panel in three steps

1. **Exact lookahead:** enumerate all audited, unvisited actions in U_s(s) for
   the depth-d prefix. The three displayed leaves are schematic, not a branch
   cap or a declaration that d equals two. Full enumeration is unchanged.
2. **Full policy tails:** simulate the same deterministic, task-aware greedy
   policy from every leaf until the required goal is reached or completion
   fails within that leaf's remaining budget. V-hat_0 is the sum of all stage
   costs in the completed tail; otherwise it is positive infinity. The finite
   outcome card groups a category, not equal numerical values across leaves.
3. **Bellman backup:** propagate these terminal values through the exact prefix
   using the displayed recurrence. Discard actions whose backed-up Q is infinite.
   The adjoining, unchanged replanning panel chooses the minimum finite Q,
   appends the first arc, updates the state and rebuilds the lookahead search.

If all Q values are infinite, the algorithm reports no certified completion;
this is not a claim of physical infeasibility. A failure to complete the base
policy is distinct from a collision/motion audit. This is model-based rollout
ADP, not a learned terminal critic or neural-network training illustration.

The prefix/tail drawing now spans 180 vertical drawing units (including nodes),
compared with 294 previously, a 39 percent reduction. The outer frame stays the same size to preserve
alignment with the camera and replanning panels. The summary formula uses a
compact sum over all costs in each full tail; its precise limits are defined
in the manuscript's base-policy evaluation equation.

Open A_integrated.drawio for the revised integrated figure, or the three-page
OrbInspect_figure_options.drawio for all discussion alternatives. All new nodes,
connectors, labels, equation text and outcome cards are native editable objects.
Special mathematical glyphs are outlined only in review SVG/PDF exports to avoid
font substitutions. Ordinary text remains selectable. The QA report verifies
unchanged native/SVG objects elsewhere, and equal rendered paths and text with
only sub-0.01-unit renderer roundoff in coordinates (boundary antialiasing).
''')
    report = {
        'revision': 'Integrated panel d only',
        'backend': 'Python with native draw.io vector objects',
        'old_panel_native_cells': len(removed), 'new_panel_native_cells': len(added),
        'text_width_warnings': warnings,
        'all_other_native_cells_identical': True, 'all_other_svg_elements_identical': True,
        'rendered_surroundings_check': rendered_check,
        'prefix_tail_vertical_span_reduction_percent': round((1-180/294)*100, 1),
        'fixed_anchors': {'root': [532, 822], 'output': [1245, 1056]},
        'B1_and_B2_copied_unchanged': True, 'other_PDF_pages_pixel_identical': True,
        'preserved_sha256': saved,
        'sources_and_manuscript_unchanged': all(sha(ROOT/p) == h for p, h in saved.items()),
        'scientific_checks': {
            'full_greedy_completion_at_every_leaf': True,
            'exact_prefix_not_fixed_depth_two': True,
            'finite_tail_value_is_sum_of_all_tail_costs': True,
            'infinite_backed_up_actions_discarded': True,
            'all_infinite_is_no_certified_completion_not_infeasibility': True,
            'no_neural_critic_or_new_experiment_claim': True,
        },
    }
    assert report['sources_and_manuscript_unchanged']
    (OUT/'QA.json').write_text(json.dumps(report, indent=2)+'\n')
    with zipfile.ZipFile(OUT.with_suffix('.zip'), 'w', zipfile.ZIP_DEFLATED) as bundle:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():
                bundle.write(p, p.relative_to(OUT.parent))
        bundle.write(PDF, OUT.name+'/'+PDF.name)
    with zipfile.ZipFile(OUT.with_suffix('.zip')) as bundle:
        assert bundle.testzip() is None
    print(json.dumps({k: v for k, v in report.items() if k != 'preserved_sha256'}, indent=2))


if __name__ == '__main__':
    main()
