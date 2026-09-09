#!/usr/bin/env python3
"""Create Figure 1 as editable draw.io cells and matching mixed-media exports.

The schematic uses the user's pastel-zone reference as visual direction.
Labels, stages, connectors and schematics are native editable elements.
Two credited, unmodified photographs illustrate the ISS and camera hardware.
They are embedded as independent replaceable image objects, not a flattened figure.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import html
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'OrbInspectLatex/figures/required_target'
ASSETS = OUT / 'framework_assets'
W, H = 1800, 934
INK, BLUE, RED = '#20252B', '#5A7D94', '#8C2940'
GREY, PALE_BLUE = '#EEF0F2', '#E6EEF5'
PALE_GREEN, PALE_PINK, PALE_YELLOW = '#E7F0E0', '#F8E8E2', '#FCF2D9'


class Diagram:
    """Write one shared geometry model to editable mxGraph cells and SVG."""

    def __init__(self) -> None:
        self.mx = ET.Element('mxfile', host='app.diagrams.net')
        page = ET.SubElement(self.mx, 'diagram', name='OrbInspect Figure 1', id='orbinspect-framework')
        model = ET.SubElement(page, 'mxGraphModel', dx=str(W), dy=str(H), grid='1',
                              gridSize='10', guides='1', tooltips='1', connect='1',
                              arrows='1', fold='1', page='1', pageScale='1',
                              pageWidth=str(W), pageHeight=str(H), math='0', shadow='0')
        self.cells = ET.SubElement(model, 'root')
        ET.SubElement(self.cells, 'mxCell', id='0')
        ET.SubElement(self.cells, 'mxCell', id='1', parent='0')
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
                    '<rect width="100%" height="100%" fill="white"/>']
        self.index = 1
        self.image_count = 0

    def ident(self) -> str:
        self.index += 1
        return str(self.index)

    def box(self, x: float, y: float, w: float, h: float, fill: str = '#FFFFFF',
            stroke: str = INK, radius: int = 16, width: float = 1.8,
            gradient: bool = False) -> str:
        ident = self.ident()
        style = (f'rounded={int(radius>0)};arcSize={max(1, int(200*radius/min(w,h)))};'
                 f'whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth={width};')
        if gradient:
            style += 'gradientColor=#FAFCFD;gradientDirection=north;'
        cell = ET.SubElement(self.cells, 'mxCell', id=ident, value='', style=style, vertex='1', parent='1')
        ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as':'geometry'})
        svg_fill = fill
        if gradient:
            self.svg.append(f'<defs><linearGradient id="g{ident}" x1="0" y1="1" x2="0" y2="0">'
                            f'<stop offset="0" stop-color="{fill}"/><stop offset="1" stop-color="#FAFCFD"/>'
                            '</linearGradient></defs>')
            svg_fill = f'url(#g{ident})'
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
                        f'fill="{svg_fill}" stroke="{stroke}" stroke-width="{width}"/>')
        return ident

    def text(self, x: float, y: float, w: float, h: float, value: str, size: float = 22,
             bold: bool = False, color: str = INK, align: str = 'center') -> str:
        ident = self.ident()
        lines = value.split('\n')
        value_html = '<div>' + '<br>'.join(html.escape(t) for t in lines) + '</div>'
        style = (f'text;html=1;strokeColor=none;fillColor=none;align={align};verticalAlign=middle;'
                 f'whiteSpace=wrap;rounded=0;fontFamily=Arial;fontSize={size};fontStyle={int(bold)};'
                 f'fontColor={color};spacing=0;')
        cell = ET.SubElement(self.cells, 'mxCell', id=ident, value=value_html, style=style, vertex='1', parent='1')
        ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as':'geometry'})
        anchor = {'center':'middle', 'left':'start', 'right':'end'}[align]
        tx = x+w/2 if align == 'center' else x if align == 'left' else x+w
        line_h = size*1.22
        first = y+h/2-(len(lines)-1)*line_h/2 + size*.34
        for i, line in enumerate(lines):
            self.svg.append(f'<text x="{tx}" y="{first+i*line_h}" text-anchor="{anchor}" '
                            f'font-family="Arial,Helvetica,sans-serif" font-size="{size}" '
                            f'font-weight="{700 if bold else 400}" fill="{color}">{html.escape(line)}</text>')
        return ident

    def circle(self, x: float, y: float, r: float, fill: str = '#FFFFFF',
               stroke: str = INK, width: float = 1.8) -> str:
        ident = self.ident()
        cell = ET.SubElement(self.cells, 'mxCell', id=ident, value='',
                             style=f'ellipse;fillColor={fill};strokeColor={stroke};strokeWidth={width};',
                             vertex='1', parent='1')
        ET.SubElement(cell, 'mxGeometry', x=str(x-r), y=str(y-r), width=str(2*r), height=str(2*r), **{'as':'geometry'})
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
        return ident

    def photo(self, x: float, y: float, w: float, h: float, path: Path,
              description: str, source_url: str) -> str:
        """Embed original image bytes, aspect-fitted without cropping or retouching."""
        encoded = base64.b64encode(path.read_bytes()).decode('ascii')
        with pymupdf.open(path) as image_doc:
            iw, ih = image_doc[0].rect.width, image_doc[0].rect.height
        scale = min(w / iw, h / ih)
        fw, fh = iw * scale, ih * scale
        fx, fy = x + (w - fw) / 2, y + (h - fh) / 2
        ident = self.ident()
        # draw.io's image style stores data-URI base64 without an internal semicolon.
        style = ('shape=image;verticalLabelPosition=bottom;verticalAlign=top;'
                 'imageAspect=1;aspect=fixed;fillColor=none;strokeColor=none;'
                 f'image=data:image/jpeg,{encoded};')
        cell = ET.SubElement(self.cells, 'mxCell', id=ident, value='', style=style,
                             vertex='1', parent='1', tooltip=description, link=source_url)
        ET.SubElement(cell, 'mxGeometry', x=str(fx), y=str(fy), width=str(fw),
                      height=str(fh), **{'as': 'geometry'})
        self.svg.append(f'<image x="{fx}" y="{fy}" width="{fw}" height="{fh}" '
                        f'xlink:href="data:image/jpeg;base64,{encoded}" preserveAspectRatio="xMidYMid meet">'
                        f'<title>{html.escape(description)}</title></image>')
        self.image_count += 1
        return ident

    def line(self, points: list[tuple[float, float]], color: str = INK, width: float = 2,
             arrow: bool = False, dashed: bool = False) -> None:
        ident = self.ident()
        style = (f'edgeStyle=none;rounded=0;html=1;strokeColor={color};strokeWidth={width};'
                 f'endArrow={"block" if arrow else "none"};endFill=1;endSize=9;'
                 f'dashed={int(dashed)};')
        cell = ET.SubElement(self.cells, 'mxCell', id=ident, value='', style=style, edge='1', parent='1')
        geo = ET.SubElement(cell, 'mxGeometry', relative='1', **{'as':'geometry'})
        ET.SubElement(geo, 'mxPoint', x=str(points[0][0]), y=str(points[0][1]), **{'as':'sourcePoint'})
        ET.SubElement(geo, 'mxPoint', x=str(points[-1][0]), y=str(points[-1][1]), **{'as':'targetPoint'})
        if len(points)>2:
            arr = ET.SubElement(geo, 'Array', **{'as':'points'})
            for x,y in points[1:-1]:
                ET.SubElement(arr, 'mxPoint', x=str(x), y=str(y))
        if dashed:
            # Explicit dash geometry avoids renderer-specific SVG dash support.
            for (x1,y1),(x2,y2) in zip(points,points[1:]):
                length=math.hypot(x2-x1,y2-y1)
                for offset in range(0,math.ceil(length),12):
                    t0,t1=offset/length,min(offset+7,length)/length
                    self.svg.append(f'<line x1="{x1+(x2-x1)*t0}" y1="{y1+(y2-y1)*t0}" '
                                    f'x2="{x1+(x2-x1)*t1}" y2="{y1+(y2-y1)*t1}" '
                                    f'stroke="{color}" stroke-width="{width}"/>')
        else:
            xy = ' '.join(f'{x},{y}' for x,y in points)
            self.svg.append(f'<polyline points="{xy}" fill="none" stroke="{color}" stroke-width="{width}" '
                            'stroke-linejoin="round"/>')
        if arrow:
            x,y=points[-1]; px,py=points[-2]
            norm=math.hypot(x-px,y-py); ux,uy=(x-px)/norm,(y-py)/norm
            corners=[(x,y),(x-ux*10-uy*4.5,y-uy*10+ux*4.5),
                     (x-ux*10+uy*4.5,y-uy*10-ux*4.5)]
            self.svg.append(f'<polygon points="{" ".join(f"{a},{b}" for a,b in corners)}" fill="{color}"/>')

    def finish(self) -> None:
        OUT.mkdir(parents=True, exist_ok=True)
        ET.indent(self.mx, space='  ')
        ET.ElementTree(self.mx).write(OUT/'orbinspect_framework.drawio', encoding='utf-8', xml_declaration=True)
        svg = '\n'.join(self.svg + ['</svg>'])
        (OUT/'orbinspect_framework.svg').write_text(svg)
        doc = pymupdf.open(stream=svg.encode(), filetype='svg')
        pdf = pymupdf.open('pdf', doc.convert_to_pdf())
        pdf.save(OUT/'orbinspect_framework.pdf', garbage=4, deflate=True)
        pdf[0].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(OUT/'orbinspect_framework.png')
        print(json.dumps({'drawio_cells':len(list(self.cells)), 'pdf_pages':len(pdf),
                          'embedded_photographs':self.image_count, 'output':str(OUT)}, indent=2))


def archived_examples() -> dict:
    """Extract fixed, illustrative records without rerunning or altering experiments."""
    portable = ASSETS / 'TECHNICAL_EXAMPLES.json'
    study = ROOT / 'data/results/20260905_101500_required_target_confirmation'
    if not study.is_dir():
        return json.loads(portable.read_text())
    graph = json.loads((study / 'raw/hcw_graph.json').read_text())
    case = json.loads((study / 'raw/representative_case_manifest.json').read_text())
    route = case['methods']['adaptive_rollout_adp']['route_node_ids'].split(';')
    source, destination = route[2:4]
    source_x = graph['node_positions'][graph['node_ids'].index(source)][0]
    with (study / 'raw/representative_case_trajectory.csv').open() as stream:
        rows = [r for r in csv.DictReader(stream)
                if r['method'] == 'adaptive_rollout_adp' and r['action'] == '4']
    config = json.loads((study / 'config_snapshot/base_experiment_config.json').read_text())
    duration = float(config['transfer_duration'])
    curve = [[0.0, source_x]] + [[float(r['time_s']) - 3 * duration, float(r['rx'])] for r in rows]
    assert source == 'cand_0070' and destination == 'cand_0068'
    assert abs(curve[-1][0] - duration) < 1e-8
    masks = {}
    for node in ['cand_0005', 'cand_0000', 'cand_0070']:
        mask = int(graph['coverage_masks'][graph['node_ids'].index(node)], 16)
        masks[node] = [t for i, t in enumerate(graph['target_ids']) if mask & (1 << i)]
    edge_lookup = {(e['source_id'], e['target_id']): e for e in graph['edges']}
    directed = [{k: edge_lookup[a, b][k] for k in ('source_id', 'target_id', 'feasible')}
                for a, b in [('cand_0070', 'cand_0009'), ('cand_0009', 'cand_0070')]]
    assert [e['feasible'] for e in directed] == [True, False]
    sources = ['raw/hcw_graph.json', 'raw/representative_case_manifest.json',
               'raw/representative_case_trajectory.csv', 'config_snapshot/base_experiment_config.json']
    result = {'purpose': 'Illustrative method records, not new experimental evidence',
              'scenario_id': case['scenario_id'], 'selection_rule': case['selection_rule'],
              'curve': {'source_id': source, 'destination_id': destination,
                        'action': 4, 'columns': ['elapsed_transfer_time_s', 'radial_position_m'],
                        'values': curve, 'source_state_included': True},
              'node_masks': masks, 'directed_audit_examples': directed,
              'abbreviations': {'C070': 'cand_0070', 'T01': 'mesh_00001'},
              'sources': {str((study / p).relative_to(ROOT)):
                          hashlib.sha256((study / p).read_bytes()).hexdigest() for p in sources}}
    portable.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main() -> None:
    evidence = archived_examples()
    d = Diagram()
    d.text(12,9,1776,49,'OrbInspect: completion-certified rollout ADP',34,True)
    zones = [(12,278,GREY,'a  Mission\ndefinition'),
             (320,302,PALE_BLUE,'b  Observation and\ntransfer construction'),
             (652,278,PALE_GREEN,'c  Graph\nrepresentation'),
             (960,494,PALE_PINK,'d  Rollout ADP\nFixed requirements K'),
             (1484,304,PALE_YELLOW,'e  Mission outputs\nand execution')]
    for x,w,fill,title in zones:
        d.box(x,82,w,796,fill,'none',14,0)
        d.text(x+10,94,w-20,66,title,28,True)

    # (a) Fixed problem data. The NASA photo gives context, not simulation evidence.
    d.box(26,178,250,174,'#FFFFFF',INK,3,1.4)
    d.photo(30,182,242,166,ASSETS/'iss_nasa_s132e012208.jpg',
            'ISS context photograph: NASA / crew of STS-132, 23 May 2010, s132e012208.',
            'https://images.nasa.gov/details-s132e012208')
    d.text(28,363,246,34,'ISS structure',27,True)
    d.box(26,422,250,264,'#FFFFFF',INK,6,1.5)
    d.text(35,434,232,36,'Fixed inputs',27,True)
    d.line([(42,480),(260,480)],'#BDC5CD',1)
    d.text(40,496,222,172,'Mesh; target IDs\nRequired subset K\nInitial state x₀\nCandidate poses\nAction budget H',25,align='left')
    d.box(26,721,250,125,'#FFFFFF',BLUE,6,1.5)
    d.text(36,734,230,32,'Inspection goal',27,True)
    d.text(35,777,232,56,'Required IDs: 100%\nOther IDs: auxiliary',25)

    # (b) Camera masks and source-dependent motion are different construction paths.
    d.box(334,178,274,256,'#FFFFFF',INK,6,1.5)
    d.text(344,190,254,37,'Visibility model',27,True)
    d.photo(347,239,125,94,ASSETS/'camera_alexander_lucke.jpg',
            'Illustrative industrial camera: Alexander Lucke, SVCam-ECO Series black with Tubus, CC BY-SA 3.0. Original, unmodified photograph.',
            'https://commons.wikimedia.org/wiki/File:SVCam-ECO_Series_black_with_Tubus.JPG')
    d.text(474,249,122,69,'Pose j\n(rⱼ, qⱼ)',27)
    d.text(348,350,246,65,'Range · field of view\nIncidence · occlusion',25)
    d.box(334,482,274,364,'#FFFFFF',INK,6,1.5)
    d.text(344,494,254,62,'Source-dependent\nHCW transfer',26,True)
    # A genuine 90-s archived radial-position trace; no freehand route or fake arc.
    px, py, pw, ph = 384, 586, 198, 136
    d.text(384,555,130,27,'rₓ (m)',25,align='left')
    for value in [-30, 0, 30]:
        yy = py + (30-value)/60*ph
        d.line([(px,yy),(px+pw,yy)],'#DCE2E7',1)
        d.text(339,yy-15,35,30,str(value),24,align='right')
    d.line([(px,py),(px,py+ph),(px+pw,py+ph)],INK,1.4)
    for value in [0, 90]:
        xx = px + value/90*pw
        d.line([(xx,py+ph),(xx,py+ph+5)],INK,1.4)
        d.text(xx-20,py+ph+9,40,29,str(value),24)
    points = [(px+t/90*pw, py+(30-rx)/60*ph) for t,rx in evidence['curve']['values']]
    d.line(points,BLUE,3.3)
    for xx,yy in [points[0],points[-1]]:
        d.circle(xx,yy,4,BLUE,BLUE,1)
    d.text(388,761,190,30,'Time (s)',25)
    d.text(346,807,250,28,'C070 → C068',26,True)
    d.line([(290,532),(306,532),(306,306),(334,306)],INK,2,True)
    d.line([(306,532),(306,664),(334,664)],INK,2,True)
    d.circle(306,532,3,INK,INK,0)
    d.line([(608,308),(666,308)],INK,2,True)
    d.line([(608,660),(666,660)],INK,2,True)

    # (c) Indexed scientific records replace anonymous network icons.
    d.box(666,178,250,256,'#FFFFFF',INK,6,1.5)
    d.text(676,190,230,36,'Node visibility Gⱼ',26,True)
    d.text(680,243,83,31,'View',25,True)
    d.text(774,243,132,31,'Target IDs',25,True)
    d.line([(680,281),(902,281)],INK,1.1)
    for row,(node,targets) in enumerate(evidence['node_masks'].items()):
        yy=290+row*41
        short_node = f'C{int(node.split("_")[-1]):03d}'
        short_targets = ', '.join(f'T{int(t.split("_")[-1]):02d}' for t in targets)
        d.text(680,yy,83,32,short_node,25)
        d.text(774,yy,132,32,short_targets,25)
    d.box(666,482,250,364,'#FFFFFF',INK,6,1.5)
    d.text(675,494,232,36,'Directed arcs',27,True)
    d.text(678,548,226,34,'x(t), u(t), cost ℓᵢⱼ',26)
    d.text(678,597,226,34,'Enabled audit χᵢⱼ',26,True)
    for index,edge in enumerate(evidence['directed_audit_examples']):
        a,b=[f'C{int(edge[k].split("_")[-1]):03d}' for k in ['source_id','target_id']]
        d.text(674,635+index*37,234,30,
               f'{a} → {b}: {"pass" if edge["feasible"] else "reject"}',25,
               color=BLUE if edge['feasible'] else RED)
    d.line([(680,714),(902,714)],'#BDC5CD',1)
    d.text(678,727,226,109,'Input · speed\nMesh clearance\nSurface intersections\nTerminal errors',24)
    d.line([(916,246),(946,246),(946,222),(982,222)],INK,2,True)
    d.line([(916,603),(946,603),(946,361),(982,361)],INK,2,True)

    # (d) Larger ADP panel: exact-prefix / complete-tail boundary and graph-state loop.
    d.box(982,178,452,108,'#FFFFFF',INK,6,1.6)
    d.text(994,189,428,34,'State s = (j, m, b, h)',29,True)
    d.text(994,232,428,45,'Current view · covered IDs\nSelected views · budget',25)
    d.line([(1208,286),(1208,321)],INK,2,True)
    d.box(982,321,452,99,'#FFFFFF',INK,6,1.6)
    d.text(994,332,428,32,'Shield: audits + no revisits',27,True)
    d.text(994,377,428,29,'Zero-gain connections allowed',25)
    d.line([(1208,420),(1208,455)],INK,2,True)
    d.box(982,455,452,254,'#FFFFFF',INK,6,1.6)
    d.text(994,468,428,33,'Exhaustive prefix to depth d',27,True)
    d.text(994,511,428,32,'Stage costs + leaf completion value',25)
    d.line([(999,558),(1417,558)],BLUE,1.5,False,True)
    d.text(997,571,422,34,'Complete base-policy rollout μ',27,True,color=BLUE)
    d.text(997,614,422,69,'Goal within budget → finite cost\nOtherwise → +∞ (discard)',25)
    # The chosen first action is appended to a plan, not sent directly to a spacecraft.
    d.line([(1378,709),(1378,786)],INK,2,True)
    d.box(1330,733,96,30,PALE_PINK,'none',0,0)
    d.text(1330,733,96,30,'Finite',25)
    d.text(988,717,326,56,'No finite branch:\nno certified completion',25,color=RED)
    d.line([(982,660),(972,660),(972,745),(988,745)],RED,1.6,True)
    d.box(982,786,452,70,'#FFFFFF',RED,6,1.6)
    d.text(994,792,428,30,'Choose finite minimizing action',26,True)
    d.text(994,825,428,28,'Append arc; update s ← f(s, a*)',25)
    d.line([(1434,820),(1445,820),(1445,254),(1434,254)],RED,1.8,True,True)
    d.line([(1434,210),(1498,210)],INK,2,True)

    # (e) Goal output is separate from execution-side observation acceptance.
    d.box(1498,178,276,253,'#FFFFFF',INK,6,1.5)
    d.text(1510,191,252,36,'Goal reached',28,True)
    d.text(1510,238,252,31,'K ⊆ covered IDs',27)
    d.line([(1514,285),(1758,285)],'#BDC5CD',1)
    d.text(1510,302,252,36,'Planned route',27,True)
    d.text(1510,348,252,65,'π; x(t), u(t), q(t)\nPlanned target IDs',25)
    d.line([(1636,431),(1636,466)],INK,2)
    d.text(1510,468,252,36,'Plan export',26)
    d.line([(1636,507),(1636,585)],INK,2,True)
    d.line([(1498,548),(1774,548)],BLUE,1.4,False,True)
    d.box(1498,585,276,261,'#FFFFFF',INK,6,1.5)
    d.text(1510,600,252,35,'Execution interface',27,True)
    d.text(1510,649,252,31,'ROS 2 / log interface',25)
    d.line([(1636,690),(1636,715)],INK,1.8,True)
    d.text(1510,723,252,32,'Acceptance gate',27,True)
    d.text(1510,771,252,58,'Execution credit:\naccepted IDs only',25)

    d.text(16,895,1160,28,'Archived trace and graph records.  C070 = cand_0070; T01 = mesh_00001.',25,align='left')
    d.line([(1272,910),(1334,910)],RED,1.8,True,True)
    d.text(1344,895,440,28,'Internal graph-state planning loop',25,align='left')
    d.finish()


if __name__ == '__main__':
    main()
