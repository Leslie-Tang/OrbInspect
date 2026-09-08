#!/usr/bin/env python3
"""Align all discussion figures to manuscript notation from one label source.

Contract: preserve the schematic-led composite, panel hierarchy, archived data,
colors and geometry; change only labels needed for notation consistency. Python
renders the review SVG/PDF. The same LaTeX tokens remain editable in draw.io with
mathematical typesetting enabled, rather than approximating math using Unicode.
"""
from __future__ import annotations

import copy
import hashlib
import html
import io
import json
import re
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile

import matplotlib as mpl
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import MathTextParser, math_to_image
import numpy as np
from PIL import Image, ImageChops
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'output/figure_adp_compact_20260907'
OUT = ROOT/'output/figure_notation_aligned_20260908'
PDF = ROOT/'output/pdf/OrbInspect_figures_notation_aligned_20260908.pdf'
PRIOR_PDF = ROOT/'output/pdf/OrbInspect_figure_adp_compact_20260907.pdf'
STEMS = ['A_integrated', 'B1_overview', 'B2_adp_mechanism']
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
mpl.rcParams.update({'mathtext.fontset': 'cm', 'svg.fonttype': 'path'})
PARSER = MathTextParser('path')
MATH_CACHE = {}


def T(text):
    return {'kind': 'text', 'value': text}


def M(latex):
    for command, argument in [('mathcal', 'U'), ('widehat', 'Q'), ('widehat', 'V'), ('bar', 'q')]:
        latex = latex.replace('\\'+command+' '+argument, '\\'+command+'{'+argument+'}')
    # Match the review renderer's display-style operators (sum and arg min)
    # even when the formula is embedded alongside ordinary words in draw.io.
    return {'kind': 'math', 'value': r'\displaystyle '+latex}


def line(*runs):
    return [list(runs)]


def plain(value):
    value = re.sub(r'<br\s*/?>', '\n', value)
    return html.unescape(re.sub(r'<[^>]+>', '', value)).strip()


def style_dict(cell):
    return dict(item.split('=', 1) for item in cell.get('style', '').split(';') if '=' in item)


def set_style(cell, **changes):
    parts = cell.get('style', '').split(';')
    for name, value in changes.items():
        parts = [p for p in parts if not p.startswith(name+'=')]
        parts.append(f'{name}={value}')
    cell.set('style', ';'.join(p for p in parts if p)+';')


def geometry(cell):
    g = cell.find('mxGeometry')
    return [float(g.get(k)) for k in ['x', 'y', 'width', 'height']]


def change_geometry(cell, **changes):
    for name, value in changes.items():
        cell.find('mxGeometry').set(name, str(value))


def specifications(stem, cells):
    """Canonical text/math runs; no independently maintained export equations."""
    common = {
        'Required targets K': line(T('Required targets '), M(r'\mathcal{K}')),
        'Fixed required set K': line(T('Fixed required set '), M(r'\mathcal{K}')),
        'Camera rⱼ': line(T('Camera '), M(r'\bar{\mathbf{r}}_j')),
        'pᵢ': line(M(r'p_i')), 'nᵢ': line(M(r'n_i')),
        'θ': line(M(r'\theta')), 'ρ': line(T('Range')),
        'αₘₐₓ': line(M(r'\alpha_{\max}')),
        'b(qⱼ)': line(M(r'b(\bar q_j)')),
        'Valid targets → Gⱼ': line(T('Valid targets → '), M(r'G_j')),
        's = (j, m, b, h)': line(M(r's=(j,m,b,h)')),
        's': line(M('s')),
        'Deterministic greedy μ': line(T('Deterministic greedy '), M(r'\mu')),
        'Lookahead depth d': line(T('Lookahead depth '), M('d')),
        'Lookahead d': line(T('Lookahead '), M('d')),
        'Safe actions · depth d': line(T('Safe actions · depth '), M('d')),
        'Initial state; budget H': line(T('Initial state; budget '), M('H')),
        'a₁': None, 'a₂': None,
        'a ∈ Uₛ(s)': line(M(r'a\in\mathcal U_s(s)')),
        '+∞': line(M(r'+\infty')),
        'Noncompletion\n+∞': [[T('Noncompletion')], [M(r'+\infty')]],
        'First action a*': line(T('First action '), M(r'a^\star')),
        's′ = f(s, a*)': line(M(r"s^{\prime}=f(s,a^\star)")),
    }
    spec = {c.get('id'): copy.deepcopy(common[plain(c.get('value', ''))])
            for c in cells if plain(c.get('value', '')) in common}
    q = r'\widehat Q_d(s,a)=\ell_{ja}+\widehat V_{d-1}(f(s,a))'
    if stem == 'A_integrated':
        spec.update({
            'hcw-c-20': line(M(r'\mathbf{x}_{ij}(t),\;\mathbf{u}_{ij}(t)')),
            'hcw-c-29': line(T('All pass: '), M(r'\chi_{ij}=1')),
            'hcw-c-33': line(T('SOOA '), M(r'a_{ij}')),
            'hcw-c-39': line(M(r'\ell_{ij}')),
            'hcw-c-40': line(T('Source '), M('i')),
            'hcw-c-41': line(T('View '), M('j')),
            'hcw-c-44': line(T('Node: view + mask '), M(r'G_j')),
            'adp-d-35': line(M(r'\widehat V_0(s)=\sum\ell')),
            'adp-d-38': line(M(r'\widehat V_0(s)=+\infty')),
            'adp-d-39': line(M(r'a\in\mathcal U_s(s)')),
            'adp-d-44': line(T('3  Bellman backup · discard '), M(r'+\infty'), T(' actions')),
            'adp-d-46': line(M(q)),
            '238': line(T('Minimum finite '), M(r'\widehat Q_d(s,a)')),
        })
    elif stem == 'B1_overview':
        spec.update({
            '135': line(M(r'\|\mathbf{u}\|_2'), T(' (m/s²)')),
            '153': line(T('HCW motion '), M(r'\mathbf{x}_{ij}(t)')),
        })
    else:
        spec.update({
            '7': [[M('j'), T('  current node')], [M('m'), T('  covered-target mask')],
                  [M('b'), T('  selected-view mask')], [M('h'), T('  remaining budget')]],
            '10': line(M(r'\mathcal U_s(s):\;b_a=0,\;\chi_{ja}=1')),
            '61': line(M(q)),
            '67': line(M(r'a^\star=\arg\min_a\,\widehat Q_d(s,a)')),
            '81': [[T('All '), M(r'\widehat Q_d(s,a)=+\infty')],
                   [T('No certified completion')]],
        })
    return spec


def math_svg(latex, size, color):
    """One formula token drives both editable math and outlined review glyphs."""
    key = (latex, round(size, 5), color)
    if key in MATH_CACHE:
        return MATH_CACHE[key]
    stream = io.BytesIO()
    expression = latex.removeprefix(r'\displaystyle ')
    with mpl.rc_context({'svg.fonttype': 'path', 'savefig.transparent': True}):
        math_to_image('$'+expression+'$', stream, prop=FontProperties(size=size), format='svg', color=color)
    svg = ET.fromstring(stream.getvalue())
    glyphs = {e.get('id'): e for e in svg.iter() if e.get('id')}
    for parent in list(svg.iter()):
        for i, child in enumerate(list(parent)):
            if child.tag.rsplit('}', 1)[-1] != 'use':
                continue
            ref = child.get('{http://www.w3.org/1999/xlink}href', child.get('href', ''))
            glyph = copy.deepcopy(glyphs[ref.removeprefix('#')])
            glyph.attrib.pop('id', None)
            transform = child.get('transform', '') + f' translate({child.get("x", "0")} {child.get("y", "0")})'
            group = ET.Element('{'+NS+'}g', transform=transform)
            group.append(glyph)
            parent.remove(child)
            parent.insert(i, group)
    for parent in list(svg.iter()):
        for child in list(parent):
            if child.tag.rsplit('}', 1)[-1] in ['defs', 'metadata']:
                parent.remove(child)
        parent.attrib.pop('id', None)
    _, _, width, height = map(float, svg.get('viewBox').split())
    parsed = PARSER.parse('$'+expression+'$', dpi=72, prop=FontProperties(size=size))
    MATH_CACHE[key] = (svg, width, height, float(parsed.depth))
    return MATH_CACHE[key]


def native_value(lines):
    result = []
    for runs in lines:
        result.append(''.join(html.escape(run['value']).replace(' ', '&#160;') if run['kind'] == 'text'
                              else r'\('+html.escape(run['value'])+r'\)' for run in runs))
    return '<div style="line-height:1.2">'+'<br>'.join(result)+'</div>'


def label_svg(cell, lines, stem):
    """Render canonical label runs into the existing box, adjusting text only."""
    x, y, w, h = geometry(cell)
    style = style_dict(cell)
    original_size = float(style['fontSize'])
    color = style.get('fontColor', '#000000')
    bold = int(style.get('fontStyle', '0')) & 1
    font = pymupdf.Font('hebo' if bold else 'helv')
    size = original_size
    for iteration in range(15):
        widths = [sum(font.text_length(r['value'], fontsize=size) if r['kind'] == 'text'
                      else math_svg(r['value'], size, color)[1] for r in runs) for runs in lines]
        line_metrics = []
        for runs in lines:
            ascents, descents = [size*.82], [size*.22]
            for run in runs:
                if run['kind'] == 'math':
                    _, _, mh, depth = math_svg(run['value'], size, color)
                    ascents.append(mh-depth)
                    descents.append(depth)
            ascent, descent = max(ascents), max(descents)
            line_metrics.append((max(size*1.2, ascent+descent), ascent, descent))
        total_h = sum(m[0] for m in line_metrics)
        factor = min(1, (w-1)/max(widths), h/total_h)
        if factor >= .999:
            break
        size *= factor*.997
    assert size >= 19, (stem, cell.get('id'), size, lines)
    set_style(cell, fontSize=f'{size:.5f}', whiteSpace='nowrap', overflow='fill')
    cell.set('value', native_value(lines))
    cell.set('notationSource', json.dumps(lines, ensure_ascii=False))
    group = ET.Element('{'+NS+'}g', id=f'label-{stem}-{cell.get("id")}',
                       **{'data-cell-id': cell.get('id'), 'data-notation-source': json.dumps(lines, ensure_ascii=False)})
    top = y+(h-total_h)/2
    for i, runs in enumerate(lines):
        line_h, ascent, descent = line_metrics[i]
        align = style.get('align', 'center')
        left = x if align == 'left' else x+w-widths[i] if align == 'right' else x+(w-widths[i])/2
        baseline = top+(line_h-ascent-descent)/2+ascent
        for run in runs:
            if run['kind'] == 'text':
                e = ET.SubElement(group, '{'+NS+'}text', x=str(left), y=str(baseline),
                    **{'font-family': 'Arial,Helvetica,sans-serif', 'font-size': str(size),
                       'font-weight': '700' if bold else '400', 'fill': color})
                e.text = run['value'].replace(' ', '\u00a0')
                left += font.text_length(run['value'], fontsize=size)
            else:
                math, mw, mh, depth = math_svg(run['value'], size, color)
                # Both native MathJax and the review use ordinary inline baselines.
                sub = ET.SubElement(group, '{'+NS+'}g', transform=f'translate({left},{baseline-mh+depth})')
                sub.extend(copy.deepcopy(list(math)))
                left += mw
        top += line_h
    return group, {'font_size': size, 'original_font_size': original_size,
                   'width': max(widths), 'box_width': w, 'line_heights': [m[0] for m in line_metrics]}


def locate_old_label(cell, elements):
    """Locate legacy label objects by geometry and literal value, not broad regex."""
    x, y, w, h = geometry(cell)
    style = style_dict(cell)
    if style.get('whiteSpace') == 'nowrap':
        matches = []
        for e in elements:
            if e.tag.rsplit('}', 1)[-1] != 'g':
                continue
            match = re.match(r'translate\(([^,]+),([^\)]+)\)', e.get('transform', ''))
            if match and x-1 <= float(match[1]) <= x+w+1 and y-1 <= float(match[2]) <= y+h+1:
                matches.append(e)
        assert len(matches) == 1, (cell.get('id'), len(matches))
        return matches
    lines = plain(cell.get('value')).split('\n')
    size = float(style['fontSize'])
    align = style.get('align', 'center')
    tx = x if align == 'left' else x+w if align == 'right' else x+w/2
    matches = []
    for i, text in enumerate(lines):
        ty = y+h/2-(len(lines)-1)*size*1.22/2+size*.34+i*size*1.22
        match = [e for e in elements if e.tag.rsplit('}', 1)[-1] == 'text'
                 and ''.join(e.itertext()) == text and abs(float(e.get('x'))-tx) < .05
                 and abs(float(e.get('y'))-ty) < .05]
        assert len(match) == 1, (cell.get('id'), text, len(match))
        matches.extend(match)
    return matches


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def structure(element):
    return [(e.tag, e.attrib, (e.text or '').strip()) for e in element.iter()]


def revise(stem, review, prior):
    original = ET.parse(SOURCE/(stem+'.drawio')).getroot()
    native = copy.deepcopy(original)
    model = native.find('.//mxGraphModel')
    model.set('math', '1')
    cell_root = native.find('.//root')
    cells = {c.get('id'): c for c in cell_root}
    old_cells = {c.get('id'): c for c in original.findall('.//mxCell')}
    specs = specifications(stem, list(cell_root))
    original_svg = ET.parse(SOURCE/(stem+'.svg')).getroot()
    svg = copy.deepcopy(original_svg)
    elements = list(svg)
    removed_svg = set()
    additions = {}
    log = []
    for ident, lines in specs.items():
        old = old_cells[ident]
        cell = cells[ident]
        targets = locate_old_label(old, elements)
        removed_svg.update(targets)
        if lines is None:
            cell_root.remove(cell)
            log.append({'cell': ident, 'before': plain(old.get('value')), 'removed': True})
            continue
        if plain(old.get('value')) == 'ρ':
            x, y, w, h = geometry(cell)
            change_geometry(cell, x=x+w/2-38, width=76)
        if stem == 'B2_adp_mechanism' and ident == '81':
            change_geometry(cell, y=838, height=56)
        group, metric = label_svg(cell, lines, stem)
        additions[targets[0]] = group
        log.append({'cell': ident, 'before': plain(old.get('value')), 'canonical': lines,
                    'geometry_before': geometry(old), 'geometry_after': geometry(cell), **metric})
    for e in list(svg):
        svg.remove(e)
    for e in elements:
        if e in additions:
            svg.append(additions[e])
        elif e not in removed_svg:
            svg.append(e)
    # Non-label content, archived images, curves, all frames and connectors are exact.
    for ident, old in old_cells.items():
        if ident not in specs:
            assert structure(old) == structure(cells[ident])
    original_kept = [structure(e) for e in elements if e not in removed_svg]
    revised_kept = [structure(e) for e in svg if not e.get('data-cell-id')]
    assert original_kept == revised_kept
    ids = [c.get('id') for c in cell_root]
    assert len(ids) == len(set(ids))
    model.set('notationVersion', 'manuscript-aligned-20260908')
    # Provenance clarifications stay off the busy diagram surface.
    for cell in cell_root:
        label = plain(cell.get('value', ''))
        if re.fullmatch(r'C\d+', label):
            cell.set('tooltip', 'Example candidate-library identifier; C0 is not the initial graph node v_0.')
        if label == r'\(\displaystyle \theta\)':
            cell.set('tooltip', 'Incidence angle in the visibility test; accepted only when theta <= theta_max.')
    math_count = 0
    for ident, lines in specs.items():
        if lines is None:
            continue
        cell = cells[ident]
        group = next(e for e in svg if e.get('data-cell-id') == ident)
        assert json.loads(cell.get('notationSource')) == json.loads(group.get('data-notation-source'))
        native_math = re.findall(r'\\\((.*?)\\\)', html.unescape(cell.get('value')), re.S)
        canonical = [run['value'] for runs in lines for run in runs if run['kind'] == 'math']
        assert native_math == canonical
        math_count += len(canonical)
    ET.ElementTree(native).write(OUT/(stem+'.drawio'), encoding='utf-8', xml_declaration=True)
    raw = ET.tostring(svg, encoding='utf-8')
    (OUT/(stem+'.svg')).write_bytes(raw)
    svg_doc = pymupdf.open(stream=raw, filetype='svg')
    page_doc = pymupdf.open('pdf', svg_doc.convert_to_pdf())
    page_doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(OUT/(stem+'.png'))
    index = STEMS.index(stem)
    page = review.new_page(width=prior[index].rect.width, height=prior[index].rect.height)
    page.show_pdf_page(page.rect, page_doc, 0)
    return native.find('diagram'), {'updated_labels': log, 'shared_math_tokens': math_count,
        'native_export_math_source_equal': True, 'unchanged_nonlabel_svg_elements': len(original_kept),
        'unchanged_geometry_data_palette': True}


def main():
    saved_files = [p for p in SOURCE.rglob('*') if p.is_file()]
    saved_files += [ROOT/'OrbInspectLatex/main.tex', ROOT/'OrbInspectLatex/main.pdf', PRIOR_PDF]
    saved = {str(p.relative_to(ROOT)): sha(p) for p in saved_files}
    OUT.mkdir(parents=True, exist_ok=True)
    prior = pymupdf.open(PRIOR_PDF)
    review = pymupdf.open()
    master = ET.Element('mxfile', host='app.diagrams.net')
    reports = {}
    for stem in STEMS:
        page, report = revise(stem, review, prior)
        master.append(copy.deepcopy(page))
        reports[stem] = report
        print(stem, 'updated labels', len(report['updated_labels']), 'shared math tokens', report['shared_math_tokens'])
    ET.ElementTree(master).write(OUT/'OrbInspect_figure_options.drawio', encoding='utf-8', xml_declaration=True)
    review.set_metadata({'title': 'OrbInspect figure alternatives - manuscript-aligned notation',
                         'subject': 'Three editable alternatives; notation-only revision'})
    review.save(PDF, garbage=4, deflate=True)
    shutil.copytree(SOURCE/'assets', OUT/'assets', dirs_exist_ok=True)
    shutil.copy2(SOURCE/'palette.json', OUT/'palette.json')
    (OUT/'source').mkdir(exist_ok=True)
    shutil.copy2(Path(__file__), OUT/'source'/Path(__file__).name)
    # Include exact legacy inputs, so the revision can also be reproduced offline.
    (OUT/'source/input').mkdir(exist_ok=True)
    for stem in STEMS:
        for ext in ['drawio', 'svg']:
            shutil.copy2(SOURCE/(stem+'.'+ext), OUT/'source/input'/(stem+'.'+ext))
    (OUT/'README.md').write_text('''# Manuscript-aligned notation in three editable figure alternatives

All three figures retain their preceding layouts, colors, mesh/camera assets,
archived HCW transfer and inspection route. Only notation and associated label
typesetting have changed. The manuscript has not been modified.

Open OrbInspect_figure_options.drawio for the three-page editable master, or
A_integrated.drawio, B1_overview.drawio and B2_adp_mechanism.drawio individually.
Mathematical typesetting is enabled in each file. Edit the LaTeX between the
inline math delimiters in a text label; ordinary words remain ordinary text.
Draw.io supports this through Extras > Mathematical Typesetting. See the
[official documentation](https://www.drawio.com/docs/manual/text/math-typesetting/).
If a viewer does not load MathJax, open the file in draw.io with typesetting
enabled; the formulas are not flattened screenshots.

Every revised label is stored as one canonical list of text/LaTeX runs. The native
draw.io values and review SVG/PDF math are generated from that same list, with
programmatic equality checks. Review math glyphs are outlined for reliable font
display; their editable LaTeX is retained in draw.io. Ordinary export text remains
selectable. Browser/MathJax and Python renderers may differ slightly in glyph
metrics; no claim of pixel-identical font rasterization is made.

The live MathJax browser check could not complete on this host: its private
headless browser failed to initialize even on a blank page. Shared LaTeX source
equality and Python/PDF rendering were checked; live draw.io rendering is not
reported as a passed test. The supplied notation follows draw.io's documented
mathematical-typesetting interface, with display-style operators enabled.

The corrections include calligraphic sets, barred terminal observation poses,
bold translational vectors, proper action-value hats and depth indices, state
arguments in base-policy values, and superscript action stars. Ambiguous action
labels a_1/a_2 were removed. Camera range is labelled in words to avoid reusing
the passive-clearance symbol. Mathematical meaning is unchanged.

See NOTATION_NOTES.md for compact caption-ready explanations of the incidence
angle, candidate identifiers, complete-tail summation and finite-value selection.
The audit records exact preservation of all unaffected drawing objects and source
file hashes, together with the shared native/export math tokens.
''')
    (OUT/'NOTATION_NOTES.md').write_text(r'''# Notation notes for the figure alternatives

These notes supplement the diagrams without enlarging their text or changing
the manuscript. Figure A is the integrated alternative; B1 and B2 form the
complementary overview and ADP-mechanism pair.

## Shared definitions

- $\mathcal K$ is the fixed required-target set; $K$ in the manuscript's HCW
  edge record is a different quantity, the number of transfer steps.
- $s=(j,m,b,h)$ is the generic decision state. Here $j$ is the current node,
  $m$ the covered-target mask, $b$ the selected-view mask, and $h$ the remaining
  action budget. $H$ is the initial budget. Omitting the time subscript $k$ is
  consistent with the manuscript's Bellman equations.
- $a\in\mathcal U_s(s)$ is an audited, unvisited destination choice. An edge
  $a_{ij}$ joins source $i$ to destination $j$; $\ell_{ij}$ and $\chi_{ij}$ are
  its stage cost and audit indicator. At decision state $s$, the corresponding
  indices are $\ell_{ja}$ and $\chi_{ja}$.

## Camera and example identifiers (A and B1)

The camera center and boresight at observation node $j$ are
$\bar{\mathbf r}_j$ and $b(\bar q_j)$. Target position $p_i$ and surface normal
$n_i$ use the manuscript's notation. The displayed range is
$\|p_i-\bar{\mathbf r}_j\|$. The illustrated incidence angle is

$$\theta=\arccos\frac{(\bar{\mathbf r}_j-p_i)^{\mathsf T}n_i}
{\|\bar{\mathbf r}_j-p_i\|\|n_i\|},\qquad\theta\leq\theta_{\max}.$$

The FOV half-angle is $\alpha_{\max}$, and $G_j$ contains camera-valid targets.
The letters $x,z$ on spatial axes name the LVLH directions, corresponding to
position components $r_x,r_z$; bold $\mathbf x$ denotes the six-dimensional state.

C5, C0, C70, C68 and C21 are archived candidate-library identifiers used in the
illustrative graph/transfer, not a replacement for the abstract graph-node
notation $v_j$. In particular, C0 is candidate ID zero, not the distinguished
initial node $v_0$. The initial node is not included in that five-candidate excerpt.

## Base-policy evaluation and backup (A and B2)

At each prefix leaf, $s$ denotes that leaf's state and $\mu$ is the same
deterministic task-aware base policy. The compact finite-tail sum in A means

$$\widehat V_0(s)=\sum_{k=0}^{L-1}\ell_{j_k\mu(s_k)}$$

when the policy reaches $\Gamma_{\mathcal K}(m)=1$ within the leaf's remaining
budget; otherwise $\widehat V_0(s)=+\infty$. Thus the sum includes every stage
cost of the full tail, not merely its first step. Each leaf has its own value.
The displayed branches are schematic, not a branch cap or a fixed depth of two.

The backup is $\widehat Q_d(s,a)=\ell_{ja}+\widehat V_{d-1}(f(s,a))$.
Finite-valued actions compete in the minimization defining $a^\star$;
$s'=f(s,a^\star)$ is the updated planning state. If all admissible actions have
$\widehat Q_d(s,a)=+\infty$, the outcome is no certified completion, not a proof
of physical infeasibility. The words 'required goal reached' denote
$\Gamma_{\mathcal K}(m)=1$. A complete inspection plan is distinct from a
closed-loop flight-execution claim.
''')
    report = {'revision': 'Notation and native/export consistency in A, B1, B2',
              'math_source': 'One canonical LaTeX token sequence per label',
              'live_mathjax_rendering': {'verified': False,
                  'reason': 'Private headless browser could not initialize even on a blank page; no live renderer pass is claimed.'},
              'figures': reports, 'preserved_sha256': saved,
              'sources_and_manuscript_unchanged': all(sha(ROOT/p) == h for p, h in saved.items())}
    assert report['sources_and_manuscript_unchanged']
    (OUT/'QA.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    with zipfile.ZipFile(OUT.with_suffix('.zip'), 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(OUT.rglob('*')):
            if path.is_file():
                bundle.write(path, path.relative_to(OUT.parent))
        bundle.write(PDF, OUT.name+'/'+PDF.name)
    with zipfile.ZipFile(OUT.with_suffix('.zip')) as bundle:
        assert bundle.testzip() is None
    print('Saved', PDF)


if __name__ == '__main__':
    main()
