#!/usr/bin/env python3
"""Editable Figure 2: a checked, explicitly illustrative rollout decision.

Contract: the schematic-led composite distinguishes motion admissibility from
goal completion, explains a cost-to-go decision, and shows the retained tail.
The two-target graph and assigned costs/audit flags are an educational example,
not archived HCW motion or a new experiment. Use the Figure 1 palette and Roman
headings at 182 mm. Native draw.io cells are the geometry/label source for all
Python-rendered exports. LaTeX stays editable in draw.io; export math is vector.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import html
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pymupdf

from align_figure_notation import T, M, label_svg, style_dict
from refine_figure1_typography import line_svg, svg_element

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/figure2_adp_mechanism_20260908'
STEM = 'adp_rollout_mechanism'
WIDTH, HEIGHT = 1680, 746
NS = 'http://www.w3.org/2000/svg'

# Exact colors from the current Figure 1; no new palette.
INK, WHITE, TEAL = '#000000', '#FFFFFF', '#3F91A6'
PINK, PALE, CREAM = '#FAE8E7', '#E0F1F1', '#FFF2E1'
PURPLE, CHARCOAL, RUST = '#8771AA', '#303E44', '#956054'
GREEN, RED, WINE, ORANGE = '#27A27F', '#C30000', '#830027', '#E97900'

# Required target indices are 1 and 2. Masks below are bit masks, not node IDs.
MASKS = {0: 0, 1: 1, 2: 0, 3: 0, 4: 2, 5: 1}
EDGES = {(0, 1): 2.0, (1, 4): 6.0, (0, 2): 1.0,
         (2, 5): 1.0, (5, 4): 2.0, (0, 3): 0.5}
REJECTED = (0, 4)
START = (0, 0, 0, 3)
GOAL_MASK, DEPTH = 3, 2


def actions(state: tuple[int, int, int, int]) -> tuple[int, ...]:
    """The manuscript's no-revisit, audited action set on this example."""
    j, _, selected, h = state
    return tuple(sorted(a for i, a in EDGES if i == j and not selected & (1 << (a - 1)))) if h else ()


def transition(state: tuple[int, int, int, int], action: int) -> tuple[int, int, int, int]:
    """Apply the same (node, coverage, selected views, budget) transition."""
    _, mask, selected, h = state
    assert h > 0 and action in actions(state)
    return action, mask | MASKS[action], selected | (1 << (action - 1)), h - 1


def base_action(state: tuple[int, int, int, int]) -> int:
    """Gain/cost, gain, lower cost, then lower ID: manuscript policy mu."""
    j, mask, _, _ = state
    def score(a):
        gain = (MASKS[a] & ~mask & GOAL_MASK).bit_count()
        cost = EDGES[j, a]
        return gain / max(.05, cost), gain, -cost, -a
    return max(actions(state), key=score)


def base_rollout(state: tuple[int, int, int, int]) -> tuple[float, list[int]]:
    """Simulate the complete base tail, not a one-step estimate."""
    total, route = 0., []
    while state[1] & GOAL_MASK != GOAL_MASK:
        if not actions(state):
            return math.inf, route
        a = base_action(state)
        total += EDGES[state[0], a]
        route.append(a)
        state = transition(state, a)
    return total, route


@lru_cache(None)
def value(state: tuple[int, int, int, int], depth: int) -> float:
    """Exhaustive Bellman prefix terminated by the complete base policy."""
    if state[1] & GOAL_MASK == GOAL_MASK:
        return 0.
    if not actions(state):
        return math.inf
    if depth == 0:
        return base_rollout(state)[0]
    return min(EDGES[state[0], a] + value(transition(state, a), depth - 1)
               for a in actions(state))


def example_report() -> dict:
    """Verify all depicted costs, coverage progress, and certificate claims."""
    rows = []
    for a in actions(START):
        future = value(transition(START, a), DEPTH - 1)
        q = EDGES[0, a] + future
        rows.append({'action': a, 'stage_cost': EDGES[0, a],
                     'continuation_value': future if math.isfinite(future) else '+infinity',
                     'rollout_value': q if math.isfinite(q) else '+infinity'})
    assert rows == [
        {'action': 1, 'stage_cost': 2., 'continuation_value': 6., 'rollout_value': 8.},
        {'action': 2, 'stage_cost': 1., 'continuation_value': 3., 'rollout_value': 4.},
        {'action': 3, 'stage_cost': .5, 'continuation_value': '+infinity', 'rollout_value': '+infinity'}]
    base_cost, base_route = base_rollout(START)
    assert base_action(START) == 1 and (base_cost, base_route) == (8., [1, 4])
    assert REJECTED not in EDGES and 4 not in actions(START)
    state, route, trace, cost = START, [], [], 0.
    while state[1] & GOAL_MASK != GOAL_MASK:
        a = min(actions(state), key=lambda a: (EDGES[state[0], a] + value(transition(state, a), DEPTH - 1), a))
        before = value(state, DEPTH)
        successor = transition(state, a)
        assert EDGES[state[0], a] + value(successor, DEPTH) <= before
        cost += EDGES[state[0], a]
        trace.append({'state': state, 'chosen_action': a, 'successor': successor,
                      'value_before': before, 'value_after': value(successor, DEPTH),
                      'covered_required_targets': successor[1].bit_count()})
        route.append(a)
        state = successor
    assert route == [2, 5, 4] and cost == 4 and value(START, 2) == 4
    assert transition(START, 2) == (2, 0, 2, 2)
    assert base_rollout(transition(START, 2)) == (3., [5, 4])
    assert MASKS[2] == 0 and MASKS[3] == 0
    # Verify the stated theorem inequalities at every reachable state, d=1..6.
    states, frontier = {START}, [START]
    while frontier:
        current = frontier.pop()
        for a in actions(current):
            successor = transition(current, a)
            if successor not in states:
                states.add(successor)
                frontier.append(successor)
    for state in states:
        for d in range(1, 7):
            assert value(state, d) <= value(state, 0)
            if state[1] & GOAL_MASK != GOAL_MASK and math.isfinite(value(state, d)):
                a = min(actions(state), key=lambda a: (EDGES[state[0], a] + value(transition(state, a), d - 1), a))
                assert EDGES[state[0], a] + value(transition(state, a), d) <= value(state, d)
    return {'kind': 'Illustrative finite graph; not experimental or physical HCW data',
            'audit_flags': 'Assigned for illustration, not computed collision certificates',
            'required_targets': [1, 2], 'initial_state': START, 'depth': DEPTH,
            'node_target_sets': {j: [i + 1 for i in range(2) if mask & (1 << i)] for j, mask in MASKS.items()},
            'audited_edges': [{'source': i, 'destination': a, 'cost': c} for (i, a), c in EDGES.items()],
            'audit_rejected_transfer': {'source': 0, 'destination': 4, 'chi': 0},
            'decision_rows': rows, 'base_route': [0] + base_route, 'base_cost': base_cost,
            'replanned_route': [0] + route, 'replanned_cost': cost, 'state_trace': trace,
            'reachable_states_checked': len(states), 'depths_checked': list(range(1, 7))}


class Figure:
    """One native cell model drives both editable source and review export."""

    def __init__(self, width=WIDTH, height=HEIGHT):
        self.width, self.height = width, height
        self.mx = ET.Element('mxfile', host='app.diagrams.net')
        page = ET.SubElement(self.mx, 'diagram', name='Completion-certified rollout ADP', id=STEM)
        model = ET.SubElement(page, 'mxGraphModel', dx=str(width), dy=str(height), grid='1', gridSize='10',
                             guides='1', tooltips='1', connect='1', arrows='1', fold='1', page='1', pageScale='1',
                             pageWidth=str(width), pageHeight=str(height), math='1', shadow='0')
        self.cells = ET.SubElement(model, 'root')
        ET.SubElement(self.cells, 'mxCell', id='0')
        ET.SubElement(self.cells, 'mxCell', id='1', parent='0')
        self.count = 0
        self.centers = {}

    def vertex(self, x, y, w, h, *, fill='none', stroke='none', width=1.4, radius=0,
               lines=None, size=26, bold=False, color=INK, align='center', circle=False, ident=None):
        self.count += 1
        ident = ident or f'cell-{self.count}'
        style = ('ellipse;' if circle else 'rounded=1;' if radius else 'rounded=0;')
        style += (f'html=1;fillColor={fill};strokeColor={stroke};strokeWidth={width};'
                  f'absoluteArcSize=1;arcSize={radius*2};fontFamily=Arial;fontSize={size};'
                  f'fontStyle={int(bold)};fontColor={color};align={align};verticalAlign=middle;'
                  'whiteSpace=nowrap;spacing=0;overflow=fill;')
        c = ET.SubElement(self.cells, 'mxCell', id=ident, value='', vertex='1', parent='1', style=style)
        ET.SubElement(c, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as': 'geometry'})
        if lines:
            c.set('notationSource', json.dumps(lines, ensure_ascii=False))
        if circle:
            self.centers[ident] = (x + w/2, y + h/2, w/2)
        return c

    def label(self, x, y, w, h, *runs, size=26, bold=False, color=INK, align='center'):
        return self.vertex(x, y, w, h, lines=[list(runs)], size=size, bold=bold, color=color, align=align)

    def box(self, x, y, w, h, fill=WHITE, stroke=INK, radius=12, width=1.4):
        return self.vertex(x, y, w, h, fill=fill, stroke=stroke, radius=radius, width=width)

    def line(self, points, color=INK, width=2, arrow=False, dashed=False, source=None, target=None):
        self.count += 1
        c = ET.SubElement(self.cells, 'mxCell', id=f'cell-{self.count}', value='', edge='1', parent='1',
                          style=f'edgeStyle=none;rounded=0;html=1;strokeColor={color};strokeWidth={width};'
                                f'endArrow={"block" if arrow else "none"};endFill=1;endSize=8;'
                                f'dashed={int(dashed)};dashPattern=7 5;')
        if source:
            c.set('source', source)
        if target:
            c.set('target', target)
        g = ET.SubElement(c, 'mxGeometry', relative='1', **{'as': 'geometry'})
        for (x, y), role in [(points[0], 'sourcePoint'), (points[-1], 'targetPoint')]:
            ET.SubElement(g, 'mxPoint', x=str(x), y=str(y), **{'as': role})
        if len(points) > 2:
            arr = ET.SubElement(g, 'Array', **{'as': 'points'})
            for x, y in points[1:-1]:
                ET.SubElement(arr, 'mxPoint', x=str(x), y=str(y))
        return c

    def node(self, node, x, y, fill=WHITE, color=INK, prefix='v'):
        ident = f'{prefix}-{node}'
        self.vertex(x-26, y-26, 52, 52, fill=fill, stroke=INK, width=1.6,
                    lines=[[M(f'v_{node}')]], size=28, color=color, circle=True, ident=ident)
        return ident

    def edge(self, source, target, *, color=INK, width=2, via=None, dashed=False):
        sx, sy, sr = self.centers[source]
        tx, ty, tr = self.centers[target]
        points = [(sx, sy)] + (via or []) + [(tx, ty)]
        for i, r, other in [(0, sr, 1), (-1, tr, -2)]:
            x, y = points[i]
            vx, vy = points[other][0]-x, points[other][1]-y
            norm = math.hypot(vx, vy)
            points[i] = (x+r*vx/norm, y+r*vy/norm)
        return self.line(points, color, width, True, dashed, source, target)


def draw_figure() -> Figure:
    d = Figure()
    # I: graph structure only, not a second orbital-motion illustration.
    d.box(14, 14, 638, 718, radius=16)
    d.label(32, 28, 602, 40, T('I. Motion vs. completion'), size=30, bold=True, align='left')
    d.box(34, 80, 598, 40, PINK, 'none', 8)
    d.label(42, 83, 582, 34, T('Illustrative graph · budget '), M('h=3'))
    d.label(34, 132, 598, 36, M(r's=(0,\mathbf{0},\mathbf{0},3)'), T('     '), M(r'\mathcal{K}=\{1,2\}'), size=25)

    points = {0: (85, 390), 1: (260, 275), 2: (260, 442), 3: (210, 565), 4: (562, 290), 5: (445, 442)}
    fills = {0: PURPLE, 1: WHITE, 2: TEAL, 3: RUST, 4: WHITE, 5: TEAL}
    # Create connected edges behind nodes; labels travel with native nodes.
    for node, (x, y) in points.items():
        d.node(node, x, y, fills[node], WHITE if node in (2, 3, 5) else INK)
    node_cells = list(d.cells)[-len(points):]
    for c in node_cells:
        d.cells.remove(c)
    for a, b in EDGES:
        selected = (a, b) in ((0, 2), (2, 5), (5, 4))
        d.edge(f'v-{a}', f'v-{b}', color=TEAL if selected else INK, width=3 if selected else 1.8)
    d.edge('v-0', 'v-4', color=RED, width=1.7, via=[(85, 204), (630, 204), (630, 290)], dashed=True)
    d.line([(427, 195), (445, 213)], RED, 2.5)
    d.line([(427, 213), (445, 195)], RED, 2.5)
    for c in node_cells:
        d.cells.append(c)
    d.label(184, 169, 302, 30, T('Rejected transfer  '), M(r'\chi_{04}=0'), size=24, color=WINE)
    for x, y, text in [(138, 298, '2'), (379, 235, '6'), (149, 396, '1'),
                       (332, 405, '1'), (505, 346, '2'), (113, 482, '0.5')]:
        d.label(x, y, 54, 30, M(text), size=27)
    d.label(32, 425, 103, 30, T('Current'), size=24)
    d.label(191, 310, 138, 35, M(r'G_1=\{1\}'), size=25)
    d.label(488, 225, 138, 35, M(r'G_4=\{2\}'), size=25)
    d.label(190, 479, 140, 35, M(r'G_2=\varnothing'), size=25)
    d.label(373, 479, 147, 35, M(r'G_5=\{1\}'), size=25)
    d.label(140, 601, 140, 35, M(r'G_3=\varnothing'), size=25)
    d.label(255, 548, 333, 34, T('No completion'), color=WINE, align='left')
    d.label(286, 591, 322, 32, T('Edge labels: stage cost'), size=24)
    d.box(34, 655, 598, 51, CREAM, ORANGE, 8, 1.1)
    d.label(44, 662, 578, 37, T('Zero-gain views can be useful connectors.'), size=25)

    # II: one worked decision. Colors augment explicit words and numeric costs.
    d.box(672, 14, 994, 438, PALE, radius=16)
    d.label(692, 28, 954, 40, T('II. Cost-to-go changes the decision'), size=30, bold=True, align='left')
    d.box(692, 81, 954, 46, PINK, 'none', 8)
    d.label(704, 83, 930, 42, M(r'\widehat Q_d(s,a)=\ell_{ja}+\widehat V_{d-1}(f(s,a))'), size=28)
    d.label(692, 139, 570, 32, T('Exact prefix '), M('d=2'), T(' + full base-policy tail'), size=25, align='left')
    d.label(1280, 139, 366, 32, M(r'a\in\mathcal{U}_s(s)'), size=25, align='right')
    columns = [692, 836, 1006, 1256, 1456, 1646]
    d.box(692, 180, 954, 56, PINK, 'none', 0)
    labels = [[T('Action '), M('a')], [M(r'\ell_{0a}')], [M(r'\widehat V_1(f(s,a))')],
              [M(r'\widehat Q_2(s,a)')], [T('Decision')]]
    for left, right, runs in zip(columns, columns[1:], labels):
        d.label(left+6, 188, right-left-12, 40, *runs, size=26)
    rows = [('1', '2', '6', '8', 'Base policy'), ('2', '1', '1+2=3', '4', 'Selected'),
            ('3', '0.5', r'+\infty', r'+\infty', 'Discard')]
    for i, row in enumerate(rows):
        y = 236 + i*55
        d.box(692, y, 954, 55, CHARCOAL if i == 1 else WHITE, 'none', 0)
        for k, (left, right, label) in enumerate(zip(columns, columns[1:], row)):
            color = WHITE if i == 1 else WINE if i == 2 and k >= 2 else INK
            d.label(left+6, y+7, right-left-12, 41, M(label) if k < 4 else T(label), size=27 if k < 4 else 25, color=color)
    d.box(692, 180, 954, 221, 'none', INK, 0, 1.2)
    for x in columns[1:-1]:
        d.line([(x, 180), (x, 401)], INK, .7)
    d.line([(692, 236), (1646, 236)], INK, 1)
    d.label(692, 407, 954, 34, T('Rollout selects the lowest finite total cost.'), size=25)

    # III: successor certificate rather than duplicating Figure 1's control loop.
    d.box(672, 472, 994, 260, radius=16)
    d.label(692, 486, 954, 40, T('III. Replan with a retained completion'), size=30, bold=True, align='left')
    d.box(692, 550, 337, 86, WHITE, TEAL, 8, 1.3)
    d.label(702, 552, 317, 34, T('Take '), M(r'a^\star=2'))
    d.label(700, 590, 321, 37, M(r"s'=(2,\mathbf{0},\mathbf{e}_2,2)"), size=26)
    d.line([(1029, 592), (1082, 592)], INK, 1.8, True)
    d.label(1084, 532, 542, 32, T('Retained tail: cost 3'), size=25, color=GREEN)
    for node, x in [(2, 1130), (5, 1330), (4, 1530)]:
        d.node(node, x, 592, PURPLE if node == 2 else TEAL, INK if node == 2 else WHITE, 'tail')
    d.edge('tail-2', 'tail-5', color=TEAL, width=2.5)
    d.edge('tail-5', 'tail-4', color=TEAL, width=2.5)
    d.label(1206, 558, 48, 29, M('1'), size=25)
    d.label(1406, 558, 48, 29, M('2'), size=25)
    for x, n in [(1130, 0), (1330, 1), (1530, 2)]:
        d.label(x-66, 625, 132, 30, T(f'{n}/2 covered'), size=24)
    d.line([(1573, 590), (1581, 598), (1597, 578)], GREEN, 2.6)
    d.box(692, 670, 954, 46, CREAM, ORANGE, 8, 1.1)
    d.label(704, 672, 930, 42, M(r'J_{\mathrm{rollout}}(s)=4=\widehat V_2(s)<\widehat V_0(s)=8'), size=28)
    return d


def export(d: Figure, output: Path, width_mm: float = 182) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    width, height = d.width, d.height
    svg = svg_element('svg', width=width, height=height, viewBox=f'0 0 {width} {height}')
    svg.append(svg_element('rect', x=0, y=0, width=width, height=height, fill=WHITE))
    metrics = []
    for cell in d.cells:
        if cell.get('id') in ('0', '1'):
            continue
        group = svg_element('g', **{'data-cell-id': cell.get('id')})
        st = style_dict(cell)
        if cell.get('edge'):
            line_svg(group, cell, st)
        else:
            geo = cell.find('mxGeometry')
            x, y, w, h = [float(geo.get(k, 0)) for k in ('x', 'y', 'width', 'height')]
            assert x >= 0 and y >= 0 and x+w <= width and y+h <= height
            if st['fillColor'] != 'none' or st['strokeColor'] != 'none':
                common = dict(fill=st['fillColor'], stroke=st['strokeColor'], **{'stroke-width': st['strokeWidth']})
                if cell.get('style').startswith('ellipse;'):
                    group.append(svg_element('circle', cx=x+w/2, cy=y+h/2, r=w/2, **common))
                else:
                    group.append(svg_element('rect', x=x, y=y, width=w, height=h,
                                             rx=float(st.get('arcSize', 0))/2, **common))
            if cell.get('notationSource'):
                lines = json.loads(cell.get('notationSource'))
                label, metric = label_svg(cell, lines, 'Figure2')
                # draw.io's overflow=fill gives its inner HTML the full cell
                # height. Explicit flex centering keeps native MathJax labels
                # centered after asynchronous typesetting, including in nodes.
                justify = {'left': 'flex-start', 'right': 'flex-end'}.get(st.get('align'), 'center')
                cell.set('value', '<div style="height:100%;display:flex;align-items:center;'
                         f'justify-content:{justify}">'+cell.get('value')+'</div>')
                group.set('data-notation-source', cell.get('notationSource'))
                group.append(label)
                metrics.append({'id': cell.get('id'), **metric})
                # Canonical math is shared, not retyped in the review export.
                math_tokens = [r['value'] for line in lines for r in line if r['kind'] == 'math']
                assert re.findall(r'\\\((.*?)\\\)', html.unescape(cell.get('value')), re.S) == math_tokens
        svg.append(group)
    ET.indent(d.mx, space='  ')
    ET.ElementTree(d.mx).write(output/f'{STEM}.drawio', encoding='utf-8', xml_declaration=True)
    raw = ET.tostring(svg, encoding='utf-8', xml_declaration=True)
    (output/f'{STEM}.svg').write_bytes(raw)
    source = pymupdf.open(stream=raw, filetype='svg')
    converted = pymupdf.open('pdf', source.convert_to_pdf())
    pdf = pymupdf.open()
    width_pt = width_mm/25.4*72
    page = pdf.new_page(width=width_pt, height=width_pt*height/width)
    page.show_pdf_page(page.rect, converted, 0)
    pdf.set_metadata({'title': 'Completion-certified rollout ADP: illustrative decision',
                      'subject': 'Native editable draw.io; illustrative graph, not experiment data'})
    pdf.save(output/f'{STEM}.pdf', garbage=4, deflate=True)
    page.get_pixmap(dpi=240).save(output/f'{STEM}.png')
    # No hidden picture masquerading as editable content; all objects are native.
    assert not any('image=' in c.get('style', '') for c in d.cells)
    assert len(metrics) > 40
    assert min(x['font_size'] for x in metrics) >= 23
    ids = {c.get('id') for c in d.cells}
    assert all(c.get(k) in ids for c in d.cells for k in ('source', 'target') if c.get(k))
    assert len(ids) == len(d.cells)
    colors = {st[k] for c in d.cells for st in [style_dict(c)]
              for k in ('fontColor', 'fillColor', 'strokeColor') if k in st and st[k] != 'none'}
    previous = ET.parse(ROOT/'OrbInspectLatex/figures/fig01_framework/viability_preserving_rollout_adp.drawio')
    prior_colors = {st[k] for c in previous.findall('.//mxCell') for st in [style_dict(c)]
                    for k in ('fontColor', 'fillColor', 'strokeColor') if k in st}
    assert colors <= prior_colors
    return {'native_cells': len(d.cells)-2, 'editable_labels': len(metrics),
            'palette_subset_of_figure1': True, 'native_connected_edges': sum(bool(c.get('source')) for c in d.cells),
            'native_and_svg_same_geometry_and_math_source': True,
            'figure_size_mm': [width_mm, width_mm*height/width], 'minimum_text_pt': min(x['font_size'] for x in metrics)*width_pt/width,
            'visual_review': 'pending', 'live_drawio_export': 'pending', 'label_metrics': metrics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    report = example_report()
    d = draw_figure()
    qa = export(d, args.output)
    (args.output/'illustrative_graph.json').write_text(json.dumps(report, indent=2)+'\n')
    (args.output/'QA.json').write_text(json.dumps(qa, indent=2)+'\n')
    print(json.dumps({k: v for k, v in qa.items() if k != 'label_metrics'}, indent=2))
    print('Checked: base route 0-1-4 = 8; rollout route 0-2-5-4 = 4; discarded action 3.')


if __name__ == '__main__':
    main()
