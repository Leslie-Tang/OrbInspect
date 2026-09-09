#!/usr/bin/env python3
"""Create Figure 1 as native draw.io cells and matching vector exports.

The schematic uses the user's pastel-zone reference as visual direction.
It contains original, editable geometric elements, not embedded screenshots.
All routes, spacecraft elements, and graph nodes are explanatory schematics.
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'OrbInspectLatex/figures/required_target'
W, H = 1400, 728
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
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
                    '<rect width="100%" height="100%" fill="white"/>']
        self.index = 1

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

    def station(self, cx: float, cy: float) -> None:
        """Schematic station silhouette made entirely from editable primitives."""
        self.box(cx-79,cy-10,158,20,'#D5DBE1',INK,3)
        for dx in (-76,-40,21,57):
            self.box(cx+dx,cy-56,19,46,'#E5D9BA',INK,1,1.4)
            self.box(cx+dx,cy+10,19,46,'#E5D9BA',INK,1,1.4)
            for dy in (-43,-29,25,40):
                self.line([(cx+dx,cy+dy),(cx+dx+19,cy+dy)],INK,.8)
        self.box(cx-13,cy-28,26,56,'#F9FAFB',INK,8)
        self.box(cx-27,cy-13,54,26,'#DCE6EB',INK,8)
        self.circle(cx,cy,8,'#C1D4E2')

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
                          'native_images':0, 'output':str(OUT)}, indent=2))


def main() -> None:
    d = Diagram()
    d.text(12,7,1376,51,'OrbInspect: completion-certified rollout ADP',34,True)
    zones = [(12,214,GREY,'1  Mission inputs'), (254,270,PALE_BLUE,'2  Arc construction'),
             (552,210,PALE_GREEN,'3  Safe graph'), (790,328,PALE_PINK,'4  Rollout ADP'),
             (1146,242,PALE_YELLOW,'5  Mission outputs')]
    for x,w,fill,title in zones:
        d.box(x,80,w,625,fill,'none',26,0)
        d.text(x+6,93,w-12,40,title,24,True)

    # Mission inputs.
    d.station(119,224)
    d.text(24,294,190,63,'Station mesh\nand target set',24,True)
    d.box(28,388,182,132,'#FFFFFF',INK,17)
    d.text(32,395,174,32,'Required targets',22,True)
    for i in range(3):
        for j in range(3):
            d.circle(69+50*j,447+25*i,7,PALE_PINK if (i+j)%2==0 else '#DEE6EC',
                     RED if (i+j)%2==0 else INK,1.5)
    d.text(26,567,186,93,'Initial state\nCamera model\nAction budget',22)

    # Visibility and transfer construction form parallel input layers.
    d.box(270,150,238,238,'#EEF3FA',INK,18)
    d.text(278,163,222,33,'Visibility',25,True)
    d.box(293,218,38,31,'#D2DEE7',INK,6)
    d.circle(330,233,12,'#FDFDFD')
    d.line([(342,233),(447,207),(447,265),(342,233)],BLUE,1.7)
    for x,y in [(431,219),(446,246),(419,258)]:
        d.circle(x,y,6,PALE_GREEN,INK,1.5)
    d.text(280,288,218,82,'Range and field of view\nIncidence and occlusion\nVisible-target masks',21)
    d.box(270,414,238,243,'#FAEDE8',INK,18)
    d.text(278,427,222,33,'HCW transfers',25,True)
    d.line([(294,517),(320,490),(354,483),(388,500),(426,505),(476,475)],BLUE,3,True)
    d.circle(294,517,8,'#D5E3EC')
    d.circle(476,475,8,'#EDCEBC')
    d.text(280,554,218,82,'Control and duration\nClearance and limits\nTerminal tolerances',21)
    d.line([(226,397),(241,397),(241,270),(270,270)],INK,2.2,True)
    d.line([(241,397),(241,535),(270,535)],INK,2.2,True)
    d.circle(241,397,3,INK,INK,0)
    d.line([(508,270),(538,270),(538,397),(552,397)],INK,2.2,True)
    d.line([(508,535),(538,535),(538,397)],INK,2.2)
    d.circle(538,397,3,INK,INK,0)

    # Directed safe action library.
    d.box(568,150,178,340,'#F8FBF5',INK,18)
    d.text(572,164,170,47,'Directed SOOAs',21,True)
    nodes=[(590,261),(651,227),(724,274),(602,365),(699,371),(655,440)]
    for a,b in [(0,1),(1,2),(0,3),(3,4),(2,4),(4,5),(3,5)]:
        x1,y1=nodes[a]; x2,y2=nodes[b]
        vx,vy=x2-x1,y2-y1
        norm=(vx*vx+vy*vy)**.5
        d.line([(x1+vx/norm*12,y1+vy/norm*12),(x2-vx/norm*14,y2-vy/norm*14)],BLUE,2,True)
    d.line([(596,272),(691,359)],RED,1.8,False,True)
    d.line([(638,307),(650,319)],RED,2.4)
    d.line([(638,319),(650,307)],RED,2.4)
    for i,(x,y) in enumerate(nodes):
        d.circle(x,y,12,PALE_BLUE if i%2==0 else PALE_GREEN,INK,1.8)
    d.text(562,522,190,91,'Target masks\nDirected motion cost\nEnabled safety audits',20.5)
    d.text(562,643,190,47,'Shield-admissible\naction library',21,True)
    d.line([(762,397),(790,397)],INK,2.2,True)

    # The ADP mechanism is visually central and more detailed than other stages.
    d.box(810,150,288,114,'#E8EEF7',INK,18)
    d.text(820,160,268,32,'Task state',25,True)
    d.text(820,201,268,50,'Node and target masks\nSelected views and budget',21)
    d.box(810,298,288,205,'#E9F1E2',INK,18)
    d.text(820,308,268,34,'Completion value',25,True)
    for x in (871,954,1037):
        d.line([(954,353),(x,392)],INK,1.7)
    d.circle(954,353,8,PALE_BLUE)
    for x,fill in [(871,PALE_GREEN),(954,PALE_GREEN),(1037,PALE_PINK)]:
        d.circle(x,392,8,fill)
    d.text(838,405,66,28,'finite',19,color=BLUE)
    d.text(921,405,66,28,'finite',19,color=BLUE)
    d.text(1004,405,66,28,'infinite',19,color=RED)
    d.text(824,445,260,50,'Base-policy completion\nor infinite value',21)
    d.box(810,536,288,92,'#FAF0EC',INK,18)
    d.text(820,546,268,32,'Select first action',25,True)
    d.text(820,587,268,28,'Update state and replan',21)
    d.line([(954,264),(954,298)],INK,2.2,True)
    d.line([(954,503),(954,536)],INK,2.2,True)
    d.line([(810,583),(800,583),(800,207),(810,207)],RED,1.8,True,True)
    d.text(810,641,288,55,'Finite-depth Bellman\nimprovement',22,True,color=RED)
    d.line([(1098,583),(1132,583),(1132,397),(1162,397)],INK,2.2,True)

    # Outputs describe interfaces, not an additional executed experiment.
    d.box(1162,150,210,167,'#FFFFFF',INK,18)
    d.text(1170,163,194,35,'Inspection route',23,True)
    route=[(1183,265),(1220,222),(1263,252),(1301,210),(1350,251)]
    d.line(route,BLUE,2.7,True)
    for i,(x,y) in enumerate(route):
        d.circle(x,y,6,BLUE if i==0 else PALE_YELLOW,INK,1.5)
    d.box(1162,343,210,150,'#FFFFFF',INK,18)
    d.text(1169,355,196,34,'Target-ID records',22,True)
    for y in (412,445):
        d.box(1180,y-11,22,22,'#E3EFD9',INK,3,1.4)
        d.line([(1185,y),(1190,y+5),(1198,y-5)],BLUE,2)
    d.text(1211,400,151,57,'Required IDs\nAccepted IDs',21,align='left')
    d.box(1162,520,210,137,'#FFFFFF',INK,18)
    d.text(1168,526,198,57,'Execution\ninterface',23,True)
    d.text(1170,585,194,54,'Trajectory · control\nROS 2 · CSV logs',21)
    d.finish()


if __name__ == '__main__':
    main()
