#!/usr/bin/env python3
"""Single-column Figure 2 without changing the checked illustrative ADP case.

Contract: three vertically ordered panels (graph, decision, retained completion)
at the actual IEEEtaes column width, approximately 84.35 x 118.09 mm. Keep the
Figure 1 palette and readable 7--8 pt labels. The graph, cost values, visibility
sets, and certificate are unchanged. Source generation and review exports use
the established Python/native-draw.io workflow; mathematical text remains
editable in draw.io. The graph is illustrative, not new experiment data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import redesign_figure2_adp as shared
from redesign_figure2_adp import (
    Figure, T, M, INK, WHITE, TEAL, PINK, PALE, CREAM, PURPLE,
    CHARCOAL, RUST, GREEN, RED, WINE, ORANGE,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/figure2_single_column_20260908'
WIDTH, HEIGHT = 800, 1120
# IEEEtaes.cls: textwidth = 41pc, columnsep = 12pt (TeX points).
COLUMN_MM = ((41*12-12)/2)/72.27*25.4


def draw() -> Figure:
    """Recompose objects at readable scale; do not shrink the wide diagram."""
    d = Figure(WIDTH, HEIGHT)
    d.box(14, 14, 772, 475, radius=16)
    d.label(32, 26, 736, 40, T('I. Audited graph'), size=30, bold=True, align='left')
    d.box(34, 76, 732, 40, PINK, 'none', 8)
    d.label(42, 79, 716, 34, T('Illustrative  ·  '), M(r'\mathcal{K}=\{1,2\}'), T('    '), M('h=3'), size=25)

    positions = {0: (84, 281), 1: (280, 215), 2: (280, 350),
                 3: (235, 449), 4: (676, 258), 5: (500, 350)}
    fills = {0: PURPLE, 1: WHITE, 2: TEAL, 3: RUST, 4: WHITE, 5: TEAL}
    for node, (x, y) in positions.items():
        d.node(node, x, y, fills[node], WHITE if node in (2, 3, 5) else INK)
    nodes = list(d.cells)[-len(positions):]
    for cell in nodes:
        d.cells.remove(cell)
    for a, b in shared.EDGES:
        selected = (a, b) in ((0, 2), (2, 5), (5, 4))
        d.edge(f'v-{a}', f'v-{b}', color=TEAL if selected else INK,
               width=3 if selected else 1.8, via=[(84, 449)] if b == 3 else None)
    d.edge('v-0', 'v-4', color=RED, width=1.7,
           via=[(84, 153), (752, 153), (752, 258)], dashed=True)
    d.line([(527, 144), (545, 162)], RED, 2.5)
    d.line([(527, 162), (545, 144)], RED, 2.5)
    for cell in nodes:
        d.cells.append(cell)
    d.label(292, 119, 302, 30, T('Rejected  '), M(r'\chi_{04}=0'), size=24, color=WINE)
    for x, y, value in [(152, 218, '2'), (466, 202, '6'), (160, 282, '1'),
                         (366, 313, '1'), (556, 272, '2'), (128, 412, '0.5')]:
        d.label(x, y, 54, 30, M(value), size=27)
    for node, x, y, mask in [(1, 207, 248, r'\{1\}'), (2, 207, 383, r'\varnothing'),
                              (5, 427, 383, r'\{1\}'), (4, 603, 296, r'\{2\}'),
                              (3, 552, 432, r'\varnothing')]:
        d.label(x, y, 146, 34, M(f'G_{node}={mask}'), size=25)
    d.label(294, 432, 250, 33, T('No completion'), color=WINE, align='left')

    d.box(14, 509, 772, 323, PALE, radius=16)
    d.label(32, 522, 510, 40, T('II. Rollout decision'), size=30, bold=True, align='left')
    d.label(560, 528, 206, 34, M('d=2'), size=25, align='right')
    d.box(34, 573, 732, 47, PINK, 'none', 8)
    d.label(44, 576, 712, 40, M(r'\widehat Q_d(s,a)=\ell_{ja}+\widehat V_{d-1}(f(s,a))'), size=26)
    columns = [34, 240, 376, 586, 766]
    d.box(34, 636, 732, 50, PINK, 'none', 0)
    headings = [[T('Action '), M('a')], [M(r'\ell_{0a}')],
                [M(r'\widehat V_1(f(s,a))')], [M(r'\widehat Q_2(s,a)')]]
    for left, right, runs in zip(columns, columns[1:], headings):
        d.label(left+6, 641, right-left-12, 40, *runs, size=25)
    rows = [([M('1'), T(' (base)')], '2', '6', '8'),
            ([M('2'), T(' (rollout)')], '1', '1+2=3', '4'),
            ([M('3'), T(' (discard)')], '0.5', r'+\infty', r'+\infty')]
    for i, row in enumerate(rows):
        y = 686+i*44
        d.box(34, y, 732, 44, CHARCOAL if i == 1 else WHITE, 'none', 0)
        for k, (left, right, content) in enumerate(zip(columns, columns[1:], row)):
            color = WHITE if i == 1 else WINE if i == 2 and k != 1 else INK
            runs = content if k == 0 else [M(content)]
            d.label(left+6, y+3, right-left-12, 38, *runs, size=25 if k == 0 else 27, color=color)
    d.box(34, 636, 732, 182, 'none', INK, 0, 1.2)
    for x in columns[1:-1]:
        d.line([(x, 636), (x, 818)], INK, .7)
    d.line([(34, 686), (766, 686)], INK, 1)

    d.box(14, 852, 772, 254, radius=16)
    d.label(32, 864, 736, 40, T('III. Retained completion'), size=30, bold=True, align='left')
    d.label(34, 908, 360, 34, T('After '), M(r'a^\star=2'), size=25, align='left')
    d.label(434, 908, 332, 34, T('Tail cost: 3'), size=25, color=GREEN, align='right')
    for node, x in [(2, 128), (5, 389), (4, 650)]:
        d.node(node, x, 965, PURPLE if node == 2 else TEAL, INK if node == 2 else WHITE, 'tail')
    d.edge('tail-2', 'tail-5', color=TEAL, width=2.5)
    d.edge('tail-5', 'tail-4', color=TEAL, width=2.5)
    d.label(232, 929, 48, 29, M('1'), size=25)
    d.label(494, 929, 48, 29, M('2'), size=25)
    for x, count in [(128, 0), (389, 1), (650, 2)]:
        d.label(x-69, 998, 138, 30, T(f'{count}/2 covered'), size=24)
    d.line([(704, 963), (712, 971), (728, 951)], GREEN, 2.6)
    d.box(34, 1042, 732, 47, CREAM, ORANGE, 8, 1.1)
    d.label(44, 1046, 712, 39, M(r'J_{\mathrm{rollout}}(s)=4=\widehat V_2(s)<\widehat V_0(s)=8'), size=26)
    return d


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    report = shared.example_report()
    previous = json.loads((ROOT/'output/figure2_adp_mechanism_20260908/illustrative_graph.json').read_text())
    assert json.loads(json.dumps(report)) == previous, 'Never alter the illustrative evidence for a layout change'
    d = draw()
    qa = shared.export(d, args.output, width_mm=COLUMN_MM)
    assert qa['minimum_text_pt'] >= 7, qa['minimum_text_pt']
    labels = [json.loads(c.get('notationSource')) for c in d.cells if c.get('notationSource')]
    actual = [r['value'] for line in labels for runs in line for r in runs]
    required = [r'\displaystyle G_1=\{1\}', r'\displaystyle G_2=\varnothing',
                r'\displaystyle G_3=\varnothing', r'\displaystyle G_4=\{2\}',
                r'\displaystyle G_5=\{1\}', r'\displaystyle \chi_{04}=0',
                r'\displaystyle 1+2=3']
    assert set(required) <= set(actual)
    edges = {(c.get('source'), c.get('target')) for c in d.cells if c.get('source')}
    assert edges == {(f'v-{a}', f'v-{b}') for a, b in shared.EDGES} | {
        ('v-0', 'v-4'), ('tail-2', 'tail-5'), ('tail-5', 'tail-4')}
    qa.update({'layout': 'Single-column; vertically stacked graph, decision and retained completion',
               'illustrative_graph_values_and_masks_unchanged': True,
               'canvas': [WIDTH, HEIGHT], 'column_width_tex_pt': 240,
               'body_font_pt': 25*72/72.27*240/WIDTH,
               'heading_font_pt': 30*72/72.27*240/WIDTH,
               'wide_alternative_preserved': True})
    (args.output/'illustrative_graph.json').write_text(json.dumps(report, indent=2)+'\n')
    (args.output/'QA.json').write_text(json.dumps(qa, indent=2)+'\n')
    print(json.dumps({k: v for k, v in qa.items() if k != 'label_metrics'}, indent=2))


if __name__ == '__main__':
    main()
