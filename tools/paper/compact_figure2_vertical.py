#!/usr/bin/env python3
"""Shorten the single-column ADP illustration by geometry changes only.

Contract: preserve the schematic's graph, decision and retained-completion
information, all 79 objects, every label, font size, color and edge relationship.
The native draw.io model remains the source for Python vector exports. Reflow
the context banner beside the first heading, tighten graph/table spacing and
panel gaps, and retain a single-column width. No nonuniform image scaling.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import figure2_single_column as original
import redesign_figure2_adp as shared

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/figure2_compact_vertical_20260908'
WIDTH, HEIGHT = 800, 920


def draw() -> shared.Figure:
    """Edit only geometries on the established, fully editable cell model."""
    d = original.draw()
    d.height = HEIGHT
    model = d.mx.find('.//mxGraphModel')
    model.set('dy', str(HEIGHT))
    model.set('pageHeight', str(HEIGHT))
    cells = {c.get('id'): c for c in d.cells}

    def move(ident: str, **changes: float) -> None:
        g = cells[ident].find('mxGeometry')
        for key, value in changes.items():
            g.set(key, str(value))

    # I: context shares the heading row; a more compact graph keeps node sizes.
    move('cell-1', height=351)
    move('cell-2', width=280)
    move('cell-3', x=324, y=23, width=442)
    move('cell-4', x=331, y=26, width=428)
    centers = {'v-0': (84, 214), 'v-1': (280, 152), 'v-2': (280, 250),
               'v-3': (180, 329), 'v-4': (676, 183), 'v-5': (500, 250),
               'tail-2': (128, 784), 'tail-5': (389, 784), 'tail-4': (650, 784)}
    for ident, (x, y) in centers.items():
        move(ident, x=x-26, y=y-26)
        d.centers[ident] = (x, y, 26)
    for number, y in {20: 72, 21: 153, 22: 133, 23: 203, 24: 213,
                      25: 184, 26: 293, 27: 178, 28: 277, 29: 277,
                      30: 216, 31: 313, 32: 313}.items():
        move(f'cell-{number}', y=y)
    move('cell-26', x=104)
    move('cell-32', x=242)

    # II: retain the same equation and complete 4-column, 3-action table.
    move('cell-33', y=377, height=286)
    move('cell-34', y=386)
    move('cell-35', y=392)
    move('cell-36', y=431, height=43)
    move('cell-37', y=433)
    move('cell-38', y=484, height=44)
    for number in range(39, 43):
        move(f'cell-{number}', y=486)
    for row, box_id in enumerate((43, 48, 53)):
        y = 528 + row*40
        move(f'cell-{box_id}', y=y, height=40)
        for number in range(box_id+1, box_id+5):
            move(f'cell-{number}', y=y+1)
    move('cell-58', y=484, height=164)

    # III: preserve state/action, edge costs, all coverage counts and the bound.
    move('cell-63', y=675, height=231)
    for number, y in {64: 685, 65: 727, 66: 727, 72: 748, 73: 748,
                      74: 813, 75: 813, 76: 813, 78: 849, 79: 851}.items():
        move(f'cell-{number}', y=y)
    move('cell-78', height=43)

    def points(ident: str, vertices: list[tuple[float, float]]) -> None:
        g = cells[ident].find('mxGeometry')
        for child in list(g):
            g.remove(child)
        for (x, y), role in [(vertices[0], 'sourcePoint'), (vertices[-1], 'targetPoint')]:
            ET.SubElement(g, 'mxPoint', x=str(x), y=str(y), **{'as': role})
        if len(vertices) > 2:
            arr = ET.SubElement(g, 'Array', **{'as': 'points'})
            for x, y in vertices[1:-1]:
                ET.SubElement(arr, 'mxPoint', x=str(x), y=str(y))

    # Recompute attachment points, keeping all source/target IDs and styles.
    for ident, c in cells.items():
        if not c.get('source'):
            continue
        src, dst = c.get('source'), c.get('target')
        waypoints = [(84, 329)] if dst == 'v-3' else (
            [(84, 108), (752, 108), (752, 183)] if ident == 'cell-17' else [])
        pts = [centers[src], *waypoints, centers[dst]]
        for i, other in ((0, 1), (-1, -2)):
            x, y = pts[i]
            dx, dy = pts[other][0]-x, pts[other][1]-y
            r = 26/math.hypot(dx, dy)
            pts[i] = (x+r*dx, y+r*dy)
        points(ident, pts)
    points('cell-18', [(527, 99), (545, 117)])
    points('cell-19', [(527, 117), (545, 99)])
    for number, x in ((59, 240), (60, 376), (61, 586)):
        points(f'cell-{number}', [(x, 484), (x, 648)])
    points('cell-62', [(34, 528), (766, 528)])
    points('cell-77', [(704, 782), (712, 790), (728, 770)])

    # Exact equality of every non-geometric cell attribute is the scope guard.
    before = {c.get('id'): c for c in original.draw().cells}
    assert cells.keys() == before.keys()
    for ident, c in cells.items():
        assert c.attrib == before[ident].attrib, (ident, 'information/style changed')
    return d


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    report = shared.example_report()
    previous = json.loads((original.OUT/'illustrative_graph.json').read_text())
    assert json.loads(json.dumps(report)) == previous
    d = draw()
    qa = shared.export(d, args.output, width_mm=original.COLUMN_MM)
    source = ET.parse(original.OUT/'adp_rollout_mechanism.drawio')
    before = {c.get('id'): c for c in source.findall('.//mxCell')}
    after = {c.get('id'): c for c in d.cells}
    assert before.keys() == after.keys()
    for ident in before:
        assert before[ident].attrib == after[ident].attrib, (ident, 'export attributes changed')
    assert qa['minimum_text_pt'] >= 7
    qa.update({'layout': 'Compact single column, same three panels and all information',
               'canvas': [WIDTH, HEIGHT],
               'previous_canvas': [original.WIDTH, original.HEIGHT],
               'height_reduction_percent': 100*(1-HEIGHT/original.HEIGHT),
               'all_non_geometric_cell_attributes_identical': True,
               'all_information_fonts_colors_and_topology_unchanged': True,
               'illustrative_graph_report_unchanged': True,
               'body_font_pt': 25*72/72.27*240/WIDTH,
               'previous_alternatives_preserved': True})
    (args.output/'illustrative_graph.json').write_text(json.dumps(report, indent=2)+'\n')
    (args.output/'QA.json').write_text(json.dumps(qa, indent=2)+'\n')
    print(json.dumps({k: v for k, v in qa.items() if k != 'label_metrics'}, indent=2))


if __name__ == '__main__':
    main()
