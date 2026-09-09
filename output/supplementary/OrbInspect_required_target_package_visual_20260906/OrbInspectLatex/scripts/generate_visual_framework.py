#!/usr/bin/env python3
"""Generate the concise, visual-first Figure 1 using native editable geometry."""
from __future__ import annotations

import csv
import hashlib
import json
import math

import generate_editable_framework as shared
from generate_editable_framework import (
    ASSETS, ROOT, BLUE, RED, INK, GREY, PALE_BLUE, PALE_GREEN,
    PALE_PINK, PALE_YELLOW, Diagram,
)

shared.W, shared.H = 1680, 590
GOLD = '#A77F29'
MUTED = '#AEB7BF'


def examples() -> dict:
    """Read frozen graph/trajectory records; never generate new experiment data."""
    portable = ASSETS / 'VISUAL_EXAMPLES.json'
    study = ROOT / 'data/results/20260905_101500_required_target_confirmation'
    if not study.is_dir():
        return json.loads(portable.read_text())
    graph = json.loads((study / 'raw/hcw_graph.json').read_text())
    case = json.loads((study / 'raw/representative_case_manifest.json').read_text())
    config = json.loads((study / 'config_snapshot/base_experiment_config.json').read_text())
    selected = ['cand_0005', 'cand_0000', 'cand_0070', 'cand_0068', 'cand_0021']
    edges = [[e['source_id'], e['target_id']] for e in graph['edges']
             if e['source_id'] in selected and e['target_id'] in selected and e['feasible']]
    with (study / 'raw/representative_case_trajectory.csv').open() as stream:
        trajectory = [[float(r[k]) for k in ['rx', 'rz']] for r in csv.DictReader(stream)
                      if r['method'] == 'adaptive_rollout_adp']
    trajectory.insert(0, [config['initial_state'][0], config['initial_state'][2]])
    required = set(case['required_target_ids'])
    with (study / 'raw/target_positions.csv').open() as stream:
        targets = [{'id': r['target_id'], 'xz': [float(r['position_x']), float(r['position_z'])],
                    'required': r['target_id'] in required} for r in csv.DictReader(stream)]
    record = case['methods']['adaptive_rollout_adp']
    assert record['required_covered_count'] == record['required_target_count'] == '9'
    sources = ['raw/hcw_graph.json', 'raw/representative_case_manifest.json',
               'raw/representative_case_trajectory.csv', 'raw/target_positions.csv',
               'config_snapshot/base_experiment_config.json']
    result = {'purpose': 'Representative planned route and graph excerpt, not new execution evidence',
              'scenario_id': case['scenario_id'], 'selection_rule': case['selection_rule'],
              'graph_nodes': selected, 'graph_edges': edges, 'trajectory_xz_m': trajectory,
              'targets': targets, 'required_covered': 9, 'required_count': 9,
              'route_node_ids': record['route_node_ids'].split(';'),
              'tree': 'Schematic; levels are compressed and terminal marks are illustrative, not measured costs.',
              'sources': {str((study / p).relative_to(ROOT)):
                          hashlib.sha256((study / p).read_bytes()).hexdigest() for p in sources}}
    portable.write_text(json.dumps(result, indent=2) + '\n')
    return result


def directed_edge(d: Diagram, start: tuple, end: tuple, radius: float = 28) -> None:
    """Draw two opposite directed edges in separate lanes when both are present."""
    dx, dy = end[0]-start[0], end[1]-start[1]
    length = math.hypot(dx, dy)
    ux, uy = dx/length, dy/length
    shift = 5
    d.line([(start[0]+radius*ux-shift*uy, start[1]+radius*uy+shift*ux),
            (end[0]-(radius+2)*ux-shift*uy, end[1]-(radius+2)*uy+shift*ux)],
           BLUE, 2.1, True)


def main() -> None:
    data = examples()
    d = Diagram()
    for x, width, color, title in [
        (12, 302, GREY, 'a  Mission'),
        (346, 282, PALE_BLUE, 'b  SOOA graph'),
        (660, 610, PALE_PINK, 'c  Rollout ADP'),
        (1302, 366, PALE_YELLOW, 'd  Inspection plan'),
    ]:
        d.box(x, 12, width, 558, color, 'none', 14, 0)
        d.text(x+12, 28, width-24, 44, title, 32, True)

    # Physical context uses the two original photographs, without decorative icons.
    d.box(26, 96, 274, 186, '#FFFFFF', '#9AA6B0', 3, 1)
    d.photo(30, 100, 266, 178, ASSETS/'iss_nasa_s132e012208.jpg',
            'NASA / STS-132 original ISS context photograph.',
            'https://images.nasa.gov/details-s132e012208')
    d.photo(76, 326, 174, 130, ASSETS/'camera_alexander_lucke.jpg',
            'Illustrative camera: Alexander Lucke, CC BY-SA 3.0. Unmodified original.',
            'https://commons.wikimedia.org/wiki/File:SVCam-ECO_Series_black_with_Tubus.JPG')
    d.text(28, 503, 270, 38, 'Required targets K', 29, True)

    # A small real directed graph communicates the action library without record tables.
    positions = {'cand_0005': (406, 171), 'cand_0000': (568, 171),
                 'cand_0070': (487, 287), 'cand_0068': (568, 401),
                 'cand_0021': (406, 469)}
    for source, target in data['graph_edges']:
        directed_edge(d, positions[source], positions[target])
    for node, (x, y) in positions.items():
        d.circle(x, y, 28, '#FFFFFF', BLUE, 2)
        d.text(x-28, y-20, 56, 40, f'C{int(node.split("_")[-1])}', 26)
    d.text(360, 520, 254, 32, 'Views + safe transfers', 25)
    d.line([(314, 290), (346, 290)], INK, 2.5, True)

    # An intentionally schematic ADP tree replaces state definitions and prose boxes.
    d.text(694, 89, 246, 38, 'Lookahead d', 29, True)
    d.text(976, 89, 278, 38, 'Base policy μ', 29, True, color=BLUE)
    d.box(684, 139, 560, 314, '#FFFFFF', '#B9BEC4', 6, 1.2)
    d.line([(952, 151), (952, 441)], '#A6ADB5', 1.5, False, True)
    root = (710, 290)
    mids = [(800, 211), (800, 363)]
    leaves = [(922, 164), (922, 248), (922, 332), (922, 416)]
    d.line([root, mids[0]], BLUE, 3.6)
    d.line([root, mids[1]], MUTED, 2)
    for i, leaf in enumerate(leaves):
        d.line([mids[i//2], leaf], BLUE if i == 0 else MUTED, 3.6 if i == 0 else 2)
    d.circle(*root, 11, '#FFFFFF', BLUE, 2)
    d.text(689, 252, 42, 29, 's', 27)
    for i, point in enumerate(mids):
        d.circle(*point, 6, BLUE if i == 0 else '#FFFFFF', BLUE if i == 0 else MUTED, 1.8)
    for i, (x, y) in enumerate(leaves):
        color = BLUE if i == 0 else MUTED
        d.circle(x, y, 6, color if i == 0 else '#FFFFFF', color, 1.8)
        d.line([(x+7, y), (1151, y)], color, 2.8 if i == 0 else 1.8, True)
        for cx in [996, 1056, 1116]:
            d.circle(cx, y, 4.5, '#FFFFFF', color, 1.5)
        if i == 1:
            d.text(1160, y-22, 72, 44, '+∞', 32, True, color=RED)
        else:
            d.line([(1175, y), (1184, y+9), (1207, y-15)], color, 3)
    d.text(1144, 456, 98, 29, '✓ Goal', 24, color=BLUE)
    d.line([(964, 453), (964, 490)], INK, 2, True)
    d.box(804, 490, 352, 53, '#FFFFFF', BLUE, 6, 1.7)
    d.text(814, 496, 332, 41, 'Min-cost first action', 28, True)
    d.line([(804, 517), (676, 517), (676, 320), (710, 320), (710, 302)], RED, 1.8, True, True)
    d.text(690, 470, 104, 30, 'Replan', 25, color=RED)
    d.line([(628, 290), (698, 290)], INK, 2.5, True)
    d.line([(1270, 290), (1302, 290)], INK, 2.5, True)

    # The actual archived route, not a freehand path. Plot x/z at equal physical scale.
    px, py, pw, ph = 1360, 125, 270, 315
    xy = lambda x, z: (px+(x+60)/120*pw, py+(60-z)/140*ph)
    d.text(1360, 86, 105, 29, 'z (m)', 25, align='left')
    for value in [-80, 0, 60]:
        yy = xy(0, value)[1]
        d.text(1316, yy-14, 36, 28, str(value), 23, align='right')
    d.line([(px, py), (px, py+ph), (px+pw, py+ph)], '#78838D', 1.1)
    for value in [-60, 0, 60]:
        xx = xy(value, 0)[0]
        d.line([(xx, py+ph), (xx, py+ph+4)], '#78838D', 1.1)
        d.text(xx-23, py+ph+7, 46, 28, str(value), 23)
    d.text(1460, 480, 90, 28, 'x (m)', 25)
    for target in data['targets']:
        x, z = target['xz']
        assert -60 <= x <= 60 and -80 <= z <= 60
        d.circle(*xy(x, z), 1.8, '#C4C8CB', 'none', 0)
    points = [xy(x, z) for x, z in data['trajectory_xz_m']]
    d.line(points, BLUE, 2.7)
    for index in [59, 149, 238]:
        d.line(points[index:index+3], BLUE, 2.7, True)
    for target in data['targets']:
        if target['required']:
            d.circle(*xy(*target['xz']), 4.5, 'none', GOLD, 2)
    d.circle(*points[0], 3.5, INK, INK, 1)
    d.circle(*points[-1], 4, BLUE, BLUE, 1)
    d.circle(1339, 533, 4.5, 'none', GOLD, 2)
    d.text(1353, 514, 300, 38, 'Required targets: 9/9', 27, True)
    d.finish()


if __name__ == '__main__':
    main()
