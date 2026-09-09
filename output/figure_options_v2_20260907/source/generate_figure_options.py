#!/usr/bin/env python3
"""Create discussion-only native draw.io alternatives without editing the paper."""
from __future__ import annotations

import base64
import copy
import csv
import hashlib
import html
import io
import json
import math
from pathlib import Path
import shutil
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
import zlib

import numpy as np
import pymupdf
import matplotlib as mpl
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import math_to_image

mpl.rcParams.update({'svg.fonttype':'none', 'mathtext.fontset':'dejavusans'})

import generate_editable_framework as shared
from generate_editable_framework import Diagram, INK, BLUE, RED

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/figure_options_20260907'
ASSETS = ROOT / 'OrbInspectLatex/figures/required_target/framework_assets'
STUDY = ROOT / 'data/results/20260905_101500_required_target_confirmation'
PDF = ROOT / 'output/pdf/OrbInspect_figure_options_20260907.pdf'
GREY, PALE_BLUE, PEACH = '#F0F1F5', '#ECF2F6', '#F9EDE7'
YELLOW, GREEN, GOLD = '#FCF4E1', '#E9F2EC', '#A77F29'
MUTED, BORDER, WHITE = '#A8B2BB', '#CCD3DA', '#FFFFFF'
SUCCESS = '#3D725B'
WIDTH = 1680


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_evidence() -> dict:
    """Read archived data and the exact geometry transform; never rerun a study."""
    data = json.loads((ASSETS / 'VISUAL_EXAMPLES.json').read_text())
    data['transfer_profile'] = json.loads((ASSETS / 'TECHNICAL_EXAMPLES.json').read_text())['curve']
    with (STUDY / 'raw/target_positions.csv').open() as stream:
        data['target_xyz'] = [
            dict(id=r['target_id'], xyz=[float(r['position_' + a]) for a in 'xyz'])
            for r in csv.DictReader(stream)
        ]
    for package in ['orbinspect_guidance', 'orbinspect_dynamics',
                    'orbinspect_perception', 'orbinspect_safety']:
        sys.path.insert(0, str(ROOT / 'src' / package))
    from orbinspect_guidance.offline_coverage_planner import _read_glb, _mesh_triangles_from_gltf
    path = ROOT / 'src/orbinspect_description/models/iss_real/meshes/ISS_stationary.glb'
    doc, binary = _read_glb(path)
    triangles = _mesh_triangles_from_gltf(doc, binary, 1.065)
    data['mesh'] = np.asarray([t.vertices for t in triangles])
    data['normals'] = np.asarray([t.normal for t in triangles])
    data['sources'][str(path.relative_to(ROOT))] = digest(path)
    data['sources']['src/orbinspect_description/models/iss_real/model.sdf'] = digest(
        ROOT / 'src/orbinspect_description/models/iss_real/model.sdf')
    return data


class Draft(Diagram):
    """Native draw.io geometry and a matching vector review rendering."""

    def __init__(self, name: str, stem: str, height: int) -> None:
        shared.W, shared.H = WIDTH, height
        super().__init__()
        self.name, self.stem, self.height = name, stem, height
        page = self.mx.find('diagram')
        page.set('name', name)
        page.set('id', stem)
        self.labels = []
        self.mesh_facets = 0

    def text(self, x, y, w, h, value, size=25, bold=False, color=INK, align='center'):
        self.labels.append(dict(x=x, y=y, w=w, h=h, text=value, size=size, bold=bold))
        return super().text(x, y, w, h, value, size, bold, color, align)

    def panel(self, x, y, w, h, title, color):
        self.box(x, y, w, h, color, BORDER, 16, 1.4)
        self.text(x+18, y+16, w-36, 44, title, 31, True, align='left')

    def check(self, x, y, color=SUCCESS, scale=1):
        self.line([(x-10*scale, y), (x-2*scale, y+8*scale),
                   (x+14*scale, y-11*scale)], color, 3*scale)

    def cross(self, x, y, scale=1):
        self.line([(x-8*scale, y-8*scale), (x+8*scale, y+8*scale)], RED, 2.6*scale)
        self.line([(x-8*scale, y+8*scale), (x+8*scale, y-8*scale)], RED, 2.6*scale)

    def native_paths(self, x, y, w, h, paths, label):
        """Embed scientific vector paths as one editable custom draw.io shape.

        Each path is (points, fill, stroke, width). The shape is independently
        movable/resizable, with editable stencil source; no bitmap is involved.
        """
        stencil = ET.Element('shape', name=label, w=str(w), h=str(h), aspect='fixed', strokewidth='inherit')
        foreground = ET.SubElement(stencil, 'foreground')
        previous = None
        for points, fill, stroke, width in paths:
            style = (fill, stroke, width)
            if style != previous:
                ET.SubElement(foreground, 'fillcolor', color=fill)
                ET.SubElement(foreground, 'strokecolor', color=stroke)
                ET.SubElement(foreground, 'strokewidth', width=str(width), fixed='1')
                previous = style
            path = ET.SubElement(foreground, 'path')
            for i, (px, py) in enumerate(points):
                ET.SubElement(path, 'move' if i == 0 else 'line', x=f'{px:.3f}', y=f'{py:.3f}')
            ET.SubElement(path, 'close')
            ET.SubElement(foreground, 'fillstroke' if width else 'fill')
            self.svg.append('<polygon points="' + ' '.join(f'{x+px:.3f},{y+py:.3f}' for px, py in points)
                            + f'" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
        raw = urllib.parse.quote(ET.tostring(stencil, encoding='unicode'), safe="~()*!.'")
        packed = base64.b64encode(zlib.compress(raw.encode(), 9)[2:-4]).decode()
        ident = self.ident()
        cell = ET.SubElement(self.cells, 'mxCell', id=ident, value='',
                             style=f'shape=stencil({packed});fillColor=#D8DEE5;strokeColor=#647687;',
                             vertex='1', parent='1', tooltip=label)
        ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as': 'geometry'})

    def equation(self, x, y, w, h, which, size=28):
        """Typeset an equation with native editable HTML and SVG character runs."""
        equations = {
            'q': [('Q̂',0), ('d',-1), ('(s, a) = ℓ',0), ('ja',-1), (' + V̂',0),
                  ('d−1',-1), ('(f(s, a))',0)],
            'argmin': [('a* = arg min',0), ('a',-1), (' Q̂',0), ('d',-1), ('(s, a)',0)],
            'state': [('s = (j, m, b, h)',0)],
            'update': [("s′ = f(s, a*)",0)],
            'goal': [('Γ',0), ('K',-1), ('(m) = 1',0)],
            'safe': [('U',0), ('s',-1), ('(s): b',0), ('a',-1), (' = 0, χ',0), ('ja',-1), (' = 1',0)],
        }
        runs = equations[which]
        latex = {
            'q': r'$\widehat{Q}_{d}(s,a)=\ell_{ja}+\widehat{V}_{d-1}(f(s,a))$',
            'argmin': r'$a^{*}=\arg\min_{a}\widehat{Q}_{d}(s,a)$',
            'state': r'$s=(j,m,b,h)$',
            'update': r"$s^{\prime}=f(s,a^{*})$",
            'goal': r'$\Gamma_{K}(m)=1$',
            'safe': r'$\mathcal{U}_{s}(s):\ b_{a}=0,\ \chi_{ja}=1$',
        }
        # SVG and draw.io both retain text. The display font is consistent with labels.
        plain = ''.join(t for t, _ in runs)
        self.labels.append(dict(x=x,y=y,w=w,h=h,text=plain,size=size,bold=False,equation=True))
        value = '<div>' + ''.join('<sub>'+html.escape(t)+'</sub>' if sub else html.escape(t)
                                 for t, sub in runs) + '</div>'
        ident = self.ident()
        cell = ET.SubElement(self.cells, 'mxCell', id=ident, value=value, vertex='1', parent='1',
            style=f'text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;'
                  f'fontFamily=Arial;fontSize={size};fontColor={INK};whiteSpace=nowrap;spacing=0;')
        ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as': 'geometry'})
        # Equation glyphs are vector paths in review exports to avoid renderer
        # substitutions for accents/Greek/prime. draw.io retains editable HTML;
        # ordinary labels remain selectable text in SVG/PDF.
        stream = io.BytesIO()
        with mpl.rc_context({'svg.fonttype':'path','savefig.transparent':True}):
            math_to_image(latex[which],stream,prop=FontProperties(size=size),format='svg',color=INK)
        svg = ET.fromstring(stream.getvalue())
        glyphs = {e.get('id'): e for e in svg.iter() if e.get('id')}
        for parent in list(svg.iter()):
            for index, child in enumerate(list(parent)):
                if child.tag.rsplit('}',1)[-1] != 'use':
                    continue
                reference = child.get('{http://www.w3.org/1999/xlink}href', child.get('href',''))
                glyph = copy.deepcopy(glyphs[reference.removeprefix('#')])
                glyph.attrib.pop('id',None)
                transform = child.get('transform','') + f' translate({child.get("x","0")} {child.get("y","0")})'
                group = ET.Element('{http://www.w3.org/2000/svg}g', transform=transform)
                group.append(glyph)
                parent.remove(child); parent.insert(index,group)
        _,_,mw,mh = map(float,svg.attrib['viewBox'].split())
        factor = min(1,w/mw,h/mh)
        self.svg.append(f'<g transform="translate({x+(w-mw*factor)/2},{y+(h-mh*factor)/2}) scale({factor})">')
        self.svg.extend(ET.tostring(child,encoding='unicode') for child in svg)
        self.svg.append('</g>')

    def save(self):
        ET.indent(self.mx, space='  ')
        ET.ElementTree(self.mx).write(OUT/f'{self.stem}.drawio', encoding='utf-8', xml_declaration=True)
        svg = '\n'.join(self.svg + ['</svg>'])
        (OUT/f'{self.stem}.svg').write_text(svg)
        source = pymupdf.open(stream=svg.encode(), filetype='svg')
        doc = pymupdf.open('pdf', source.convert_to_pdf())
        doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(OUT/f'{self.stem}.png')
        return doc


def mesh_illustration(d, data, x, y, w, h, direction_values=(.68,.67,.30)):
    """Orthographic CAD-like projection of the actual transformed ISS mesh."""
    # Align the long station truss diagonally, keeping the solar arrays distinct.
    direction = np.array(direction_values); direction /= np.linalg.norm(direction)
    up = np.array([0.,0.,1.])
    right = np.cross(direction, up); right /= np.linalg.norm(right)
    vertical = np.cross(right, direction)
    angle = math.radians(-22)
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    basis = np.array([right, vertical])
    verts = data['mesh']
    projected = verts @ basis.T @ rotation.T
    mins, maxs = projected.min(axis=(0,1)), projected.max(axis=(0,1))
    scale = min((w-12)/(maxs[0]-mins[0]), (h-12)/(maxs[1]-mins[1]))
    offsets = np.array([(w-scale*(maxs[0]-mins[0]))/2,
                        (h-scale*(maxs[1]-mins[1]))/2])
    xy = (projected-mins)*scale+offsets
    xy[:,:,1] = h-xy[:,:,1]
    v1, v2 = xy[:,1]-xy[:,0], xy[:,2]-xy[:,0]
    areas = np.abs(v1[:,0]*v2[:,1]-v1[:,1]*v2[:,0])/2
    # Only subpixel faces are omitted from the illustration, never from audits.
    keep = np.flatnonzero(areas >= .15)
    keep = keep[np.argsort(verts.mean(axis=1)[keep] @ direction)]
    light = np.array([-.4,-.7,.6]); light /= np.linalg.norm(light)
    shades = np.abs(data['normals'] @ light)
    paths = []
    for i in keep:
        level = int(155+shades[i]*60)
        fill = f'#{max(0,level-11):02x}{max(0,level-5):02x}{level:02x}'
        paths.append((xy[i].tolist(), fill, '#657685', .18 if areas[i] > 10 else 0))
    d.native_paths(x, y, w, h, paths, 'NASA ISS mesh - orthographic vector projection')
    d.mesh_facets += len(paths)
    required = {t['id'] for t in data['targets'] if t['required']}
    for target in data['target_xyz']:
        point = (np.array(target['xyz']) @ basis.T @ rotation.T-mins)*scale+offsets
        px, py = x+point[0], y+h-point[1]
        if target['id'] not in required:
            d.circle(px, py, 1.7, '#919CA5', 'none', 0)
    for target in data['target_xyz']:
        if target['id'] in required:
            point = (np.array(target['xyz']) @ basis.T @ rotation.T-mins)*scale+offsets
            d.circle(x+point[0], y+h-point[1], 5.7, 'none', GOLD, 2.3)


def graph(d, data, x, y, w, h, labels=True):
    coords = [(0.12,.08),(.88,.08),(.5,.5),(.88,.92),(.12,.92)]
    positions = {n:(x+u*w, y+v*h) for n,(u,v) in zip(data['graph_nodes'],coords)}
    radius = 25 if labels else 12
    for a,b in data['graph_edges']:
        aa,bb=np.array(positions[a]),np.array(positions[b])
        unit=(bb-aa)/np.linalg.norm(bb-aa); normal=np.array([-unit[1],unit[0]])
        d.line([tuple(aa+(radius+1)*unit+normal*4), tuple(bb-(radius+2)*unit+normal*4)], BLUE, 1.8, True)
    for n,(cx,cy) in positions.items():
        d.circle(cx,cy,radius,WHITE,BLUE,2)
        if labels:
            d.text(cx-radius,cy-19,2*radius,38,f'C{int(n.split("_")[1])}',23)


def transfer_trace(d, data, x, y, w, h):
    """Use the archived C70-to-C68 radial/time trace, not a decorative zigzag."""
    values = np.array(data['transfer_profile']['values'])
    minimum, maximum = values.min(axis=0), values.max(axis=0)
    points = (values-minimum)/(maximum-minimum)*np.array([w,h])
    points[:,0] += x
    points[:,1] = y+h-points[:,1]
    d.line([tuple(p) for p in points], BLUE, 2.5, True)


def route(d, data, x, y, w, h, ticks=True):
    # Match x and z physical units; no perspective distortion of the result.
    scale=min((w-60)/120,(h-70)/140)
    pw,ph=120*scale,140*scale
    px=x+(w-pw)/2+15; py=y+18
    xy=lambda xx,zz:(px+(xx+60)*scale,py+(60-zz)*scale)
    d.line([(px,py),(px,py+ph),(px+pw,py+ph)],'#83909A',1.1)
    d.text(px-5,py-29,88,26,'z (m)',23,align='left')
    for val in [-60,0,60]:
        xx,_=xy(val,0)
        d.line([(xx,py+ph),(xx,py+ph+4)],'#83909A',1)
        if ticks: d.text(xx-24,py+ph+5,48,28,str(val),22)
    for val in [-80,0,60]:
        _,yy=xy(0,val)
        if ticks: d.text(px-48,yy-14,40,28,str(val),22,align='right')
    d.text(px+pw/2-45,py+ph+35,90,29,'x (m)',23)
    for t in data['targets']:
        d.circle(*xy(*t['xz']),1.4,'#BEC5CA','none',0)
    points=[xy(*p) for p in data['trajectory_xz_m']]
    d.line(points,BLUE,2.4)
    for i in [59,149,238]: d.line(points[i:i+3],BLUE,2.4,True)
    for t in data['targets']:
        if t['required']:d.circle(*xy(*t['xz']),4.3,'none',GOLD,1.8)
    d.circle(*points[0],3.5,INK,INK,1)
    d.circle(*points[-1],4,BLUE,BLUE,1)


def tree(d, x, y, w, h, compact=False):
    """Schematic exact prefix followed by full base-policy completions."""
    root=(x+22,y+h*.5); mids=[(x+w*.22,y+h*.26),(x+w*.22,y+h*.76)]
    leaves=[(x+w*.46,y+h*v) for v in [.08,.36,.64,.92]]
    boundary=x+w*.51
    d.line([(boundary,y-13),(boundary,y+h+13)],BORDER,1.2,False,True)
    for i,p in enumerate(mids):d.line([root,p],BLUE if i==0 else MUTED,3.3 if i==0 else 1.8)
    for i,p in enumerate(leaves):d.line([mids[i//2],p],BLUE if i==0 else MUTED,3.3 if i==0 else 1.8)
    d.circle(*root,10,WHITE,BLUE,2)
    d.text(root[0]-22,root[1]-45,44,28,'s',26)
    for i,p in enumerate(mids):d.circle(*p,6,BLUE if i==0 else WHITE,BLUE if i==0 else MUTED,1.7)
    for i,(cx,cy) in enumerate(leaves):
        color=BLUE if i==0 else MUTED
        d.circle(cx,cy,6,BLUE if i==0 else WHITE,color,1.7)
        end=x+w*.86
        d.line([(cx+7,cy),(end,cy)],color,3 if i==0 else 1.7,True)
        for f in [.59,.69,.79]:d.circle(x+w*f,cy,4.5,WHITE,color,1.5)
        if i==1:
            d.text(end+5,cy-19,w*.14-5,38,'+∞',29,True,RED)
        else:
            d.check(end+w*.07,cy,color if i==0 else SUCCESS,.9)
    return root, boundary


def mission(d, data, x, y, w, h, state=False):
    mesh_illustration(d,data,x+9,y+20,w-18,330 if state else 360)
    ly=y+(375 if state else 410)
    d.circle(x+23,ly+17,5.7,'none',GOLD,2.3)
    d.text(x+38,ly,w-45,34,'Required targets K',26,True,align='left')
    if state:
        d.photo(x+25,ly+60,100,86,ASSETS/'camera_alexander_lucke.jpg',
                'Camera: Alexander Lucke, CC BY-SA 3.0; unmodified, illustrative hardware.',
                'https://commons.wikimedia.org/wiki/File:SVCam-ECO_Series_black_with_Tubus.JPG')
        d.text(x+137,ly+77,w-147,52,'Camera\nmodel',25,align='left')
        d.box(x+12,ly+184,w-24,146,WHITE,BORDER,10,1.2)
        d.text(x+24,ly+194,w-48,36,'Initial planning state',26,True)
        d.equation(x+22,ly+240,w-44,40,'state',29)
        d.text(x+22,ly+285,w-44,30,'Start pose x₀; budget H',23)
    else:
        d.text(x+12,ly+59,w-24,32,'Start pose x₀; budget H',24)


def integrated(data):
    d=Draft('A - Integrated figure','A_integrated',980)
    d.text(18,14,1644,46,'Viability-preserving rollout ADP for orbital inspection',36,True)
    d.panel(16,80,336,860,'a  Mission inputs',GREY)
    mission(d,data,25,135,318,730,True)
    d.panel(384,80,908,338,'b  Audited SOOA graph',PALE_BLUE)
    d.text(410,148,386,36,'Viewpoints + visibility masks',25)
    graph(d,data,421,210,340,150)
    d.box(851,165,407,217,WHITE,BORDER,10,1.3)
    d.text(869,178,369,40,'Directed HCW transfers',28,True)
    d.text(871,225,363,38,'Dynamics · clearance · arrival',23)
    transfer_trace(d,data,884,269,126,36)
    d.check(1040,276)
    d.text(1067,257,167,39,'Audit passed',24,align='left')
    d.text(870,326,367,34,'Arc cost ℓ; admissibility χ',25)
    d.line([(851,292),(789,292)],INK,2.3,True)
    d.line([(352,245),(384,245)],INK,2.5,True)
    d.panel(384,454,908,486,'c  Rollout ADP',PEACH)
    d.text(413,518,353,35,'Exact prefix: depth d',28,True)
    d.text(822,518,440,35,'Complete base-policy tails',28,True)
    root,_=tree(d,416,587,807,221)
    d.line([(804,418),(804,454)],INK,2.4,True)
    d.line([(352,root[1]),(root[0]-12,root[1])],INK,2.4,True)
    d.box(481,852,734,60,WHITE,BLUE,8,1.6)
    d.equation(491,864,714,36,'q',29)
    d.text(867,809,336,30,'✓ goal     +∞ noncompletion',23)
    d.line([(782,812),(782,850)],INK,2,True)
    d.text(441,812,316,33,'Bellman backup',25,True)
    d.panel(1324,80,340,860,'d  Replanning',YELLOW)
    d.box(1346,175,296,90,WHITE,BLUE,10,1.6)
    d.text(1356,186,276,34,'First action a*',28,True)
    d.text(1356,222,276,30,'Minimum finite value',24)
    # Selection consumes the backed-up value; the flow travels in the inter-panel gutter.
    d.line([(1215,882),(1308,882),(1308,220),(1346,220)],INK,2.2,True)
    d.line([(1494,265),(1494,305)],INK,2.2,True)
    d.box(1346,305,296,107,WHITE,BORDER,10,1.3)
    d.text(1356,314,276,35,'Append arc + update',26,True)
    d.equation(1356,355,276,38,'update',27)
    d.line([(1494,412),(1494,457)],INK,2.2,True)
    d.box(1381,457,226,78,WHITE,GOLD,25,1.7)
    d.text(1391,466,206,56,'Required goal\nreached?',25,True)
    d.line([(1494,535),(1494,583)],SUCCESS,2.2,True)
    d.text(1510,541,95,34,'Yes',24,color=SUCCESS,align='left')
    d.text(1345,585,298,34,'Planned route',27,True)
    route(d,data,1342,642,302,244)
    d.text(1345,899,298,32,'Required targets: 9/9',25,True)
    # Incomplete tasks return to the state node, not to the Q formula.
    d.line([(1607,496),(1650,496),(1650,963),(403,963),(403,729),(438,729),(438,root[1]+12)],
           RED,1.9,True,True)
    d.text(1608,535,43,31,'No',23,color=RED)
    d.box(708,944,375,30,WHITE,'none',0,0)
    d.text(716,944,359,29,'Update state and replan',23,color=RED)
    return d


def overview(data):
    d=Draft('B1 - Mission-to-plan overview','B1_overview',710)
    d.text(18,14,1644,44,'Orbital inspection: from required targets to a complete plan',35,True)
    panels=[(16,318,'a  Mission',GREY),(360,276,'b  Construction',PALE_BLUE),
            (662,246,'c  Graph',PALE_BLUE),(934,412,'d  Rollout ADP',PEACH),
            (1372,292,'e  Plan',YELLOW)]
    for x,w,title,col in panels:d.panel(x,80,w,609,title,col)
    mission(d,data,23,137,304,490)
    d.photo(399,163,198,149,ASSETS/'camera_alexander_lucke.jpg',
            'Camera: Alexander Lucke, CC BY-SA 3.0; unmodified, illustrative hardware.',
            'https://commons.wikimedia.org/wiki/File:SVCam-ECO_Series_black_with_Tubus.JPG')
    d.text(380,331,236,36,'Visibility masks',27,True)
    d.box(378,416,240,172,WHITE,BORDER,10,1.2)
    d.text(388,427,220,35,'HCW transfers',26,True)
    transfer_trace(d,data,401,484,150,42)
    d.check(580,495)
    d.text(387,544,222,32,'Motion audits',25)
    graph(d,data,696,200,180,361)
    d.text(676,617,218,34,'Audited actions',25)
    d.text(951,172,170,65,'Lookahead\nd',26,True)
    d.text(1136,172,190,65,'Complete\npolicy tails',26,True)
    tree(d,948,288,375,213,True)
    d.text(962,522,350,32,'✓ goal     +∞ noncompletion',23)
    d.box(969,592,340,61,WHITE,BLUE,9,1.5)
    d.text(983,604,312,35,'Min-cost first action',27,True)
    d.line([(969,622),(949,622),(949,522),(970,522),(970,410)],RED,1.6,True,True)
    d.text(982,559,331,29,'State update + replan',23,color=RED)
    d.line([(1328,515),(1328,622),(1310,622)],INK,1.9,True)
    route(d,data,1384,202,268,383)
    d.text(1382,607,272,43,'Required targets: 9/9',24,True)
    for x0,x1 in [(334,360),(636,662),(908,934),(1346,1372)]:
        d.line([(x0,387),(x1,387)],INK,2.2,True)
    return d


def mechanism(data):
    d=Draft('B2 - ADP mechanism','B2_adp_mechanism',830)
    d.text(18,14,1644,44,'Viability-preserving rollout ADP: decision and state update',35,True)
    d.panel(16,80,286,570,'a  Planning state',GREY)
    d.box(31,168,256,95,WHITE,BORDER,10,1.3)
    d.equation(39,188,240,51,'state',28)
    d.text(41,293,239,181,'j   current viewpoint\nm  covered targets\nb  selected views\nh  remaining budget',24,align='left')
    d.box(32,519,254,99,WHITE,GOLD,10,1.3)
    d.text(43,530,232,32,'Goal: cover K',25,True)
    d.equation(44,568,231,34,'goal',27)
    d.panel(328,80,276,570,'b  Safe actions',PALE_BLUE)
    d.text(344,174,244,36,'Audited + unvisited',25,True)
    d.box(344,244,244,78,WHITE,BORDER,8,1.2)
    d.circle(370,281,12,WHITE,BLUE,1.8)
    d.line([(383,281),(491,281)],BLUE,2.2,True)
    d.circle(504,281,12,WHITE,BLUE,1.8)
    d.check(554,281)
    d.equation(344,343,244,32,'safe',24)
    d.line([(359,402),(415,402)],MUTED,1.7,False,True)
    d.cross(443,402)
    d.text(464,383,115,39,'Unsafe',24,align='left')
    d.line([(359,455),(415,455)],MUTED,1.7)
    d.cross(443,455)
    d.text(464,436,115,39,'Visited',24,align='left')
    d.box(344,519,244,99,WHITE,BLUE,10,1.3)
    d.text(354,529,224,74,'Safe connecting\nactions retained',24,True)
    d.panel(630,80,716,570,'c  Rollout value evaluation',PEACH)
    d.text(650,161,285,58,'Exact prefix\ndepth d',27,True)
    d.text(964,161,364,58,'Complete base policy μ\nto goal or budget limit',25,True)
    root,_=tree(d,654,266,648,211)
    d.text(973,490,350,30,'✓ goal      +∞ noncompletion',23)
    d.box(650,556,676,67,WHITE,BLUE,9,1.5)
    d.equation(660,568,656,42,'q',29)
    d.text(661,499,286,38,'Bellman backup',26,True)
    d.line([(964,522),(964,554)],INK,1.9,True)
    d.panel(1372,80,292,570,'d  Policy update',YELLOW)
    d.box(1390,199,256,142,WHITE,BLUE,10,1.5)
    d.text(1400,211,236,36,'Finite values only',25,True)
    d.equation(1401,258,234,40,'argmin',25)
    d.text(1400,302,236,28,'First action a*',24)
    d.box(1390,405,256,178,WHITE,BORDER,10,1.3)
    d.text(1401,419,234,62,'Append selected arc\nand update state',24,True)
    d.equation(1400,499,236,40,'update',27)
    d.text(1400,547,236,27,'h ← h − 1',24)
    d.line([(1518,341),(1518,403)],INK,2.1,True)
    d.line([(302,372),(328,372)],INK,2.2,True)
    d.line([(604,root[1]),(root[0]-11,root[1])],INK,2.2,True)
    d.line([(1326,590),(1358,590),(1358,270),(1390,270)],INK,2.1,True)
    # Exit logic is below, distinct from value evaluation and motion auditing.
    d.box(1176,691,248,82,WHITE,GOLD,25,1.6)
    d.text(1188,702,224,59,'Required goal\nreached?',25,True)
    d.line([(1518,583),(1518,732),(1424,732)],INK,2.1,True)
    d.box(856,691,244,82,GREEN,SUCCESS,10,1.3)
    d.text(868,712,220,40,'Complete plan',27,True)
    d.line([(1176,717),(1100,717)],SUCCESS,2.1,True)
    d.text(1109,678,65,30,'Yes',23,color=SUCCESS)
    d.line([(1300,773),(1300,809),(6,809),(6,218),(31,218)],RED,1.9,True,True)
    d.box(568,788,326,35,WHITE,'none',0,0)
    d.text(576,788,310,32,'No: update and replan',24,color=RED)
    d.box(354,684,446,85,WHITE,RED,9,1.2)
    d.text(366,694,422,64,'All values +∞\nNo certified completion',25,color=RED)
    # This is a value-test outcome, not a physical-safety rejection or infeasibility proof.
    d.line([(992,650),(992,672),(802,672),(802,723),(800,723)],RED,1.5,True,True)
    return d


README = '''# OrbInspect figure options - for discussion

Nothing in the manuscript or its current figures has been replaced.

## Two alternatives

- **A: Integrated figure.** Recreates the new reference's mission / graph / ADP /
  replanning organization, with corrected technical logic and shorter labels.
- **B: Two-figure set.** B1 is the visual mission-to-plan overview; B2 explains the
  ADP mechanism. Use B1 and B2 together, rather than B1 plus the integrated option.

Open `OrbInspect_figure_options.drawio` in diagrams.net; its three page tabs are A,
B1 and B2. Individual editable files are also supplied. Labels, nodes, connectors,
target markers, route and trees are native objects. The ISS is a native vector
stencil (one independently movable/resizable object, with editable shape source).
The camera is an independently replaceable, original embedded photograph. No
complete diagram is flattened into an image. SVG and PNG exports are included.
Review-export equation glyphs are vector outlines for reliable symbol rendering;
the corresponding draw.io equations remain editable text.

These are draft alternatives, not a recommendation to insert three figures.
The PDF presents the three proposals in the same order, at 182-mm figure width.

## Logic and evidence

- State is s=(j,m,b,h), with K fixed; masks and remaining budget are not omitted.
- Motion audits define available arcs. Full base-policy tails provide completion
  certificates; the two tests are not interchangeable.
- The depth-d prefix is followed by a full deterministic task-aware greedy tail.
  The tree is schematic, with compressed levels and illustrative terminal marks.
- Q is an action value; the policy selects the minimum finite value. The operation
  is a Bellman backup, not gradient backpropagation or a newly trained DRL model.
- The loop appends a planned arc and updates the graph state. It is not a claim
  that the required-target mission has been executed in a new physical/ROS run.
- Passive-drift auditing was disabled in this study and is not depicted as active.
- If no value is finite, the output is no certified completion, not a proof of
  infeasibility of the physical mission.

The required goal is full coverage of K, not every mesh sample. The route inset is
the archived representative planned route, with all nine required targets covered.
Its x-z axes have equal physical scale. Gray dots show other sampled targets;
gold rings show required samples; a black dot denotes the initial position.
The graph is a five-node excerpt of the archived safe directed graph. Candidate
IDs are shortened with the prefix C. No quantitative performance claim is added.
The small HCW trace is the archived C70-to-C68 radial/time profile, normalized
to its display box; it illustrates a transfer record rather than a spatial path.

## Image and geometry integrity

The ISS is projected from the repository's NASA GLB using the same full scene
hierarchy and SDF rotation/scale as the experiment loader. The target overlay uses
the same projection on archived world coordinates. For display only, triangle
faces smaller than 0.15 square drawing units are omitted. This is a visualization
simplification, never a collision or visibility approximation. The projection is
orthographic, uniformly scaled and rotated in the image plane. Face color is
neutral illumination shading, not a measured field; target rings are annotations.

Camera credit: Alexander Lucke, SVCam-ECO Series black with Tubus,
CC BY-SA 3.0. The original image is reproduced without cropping, retouching,
background removal, or AI editing. It is illustrative hardware, not a selected
or space-qualified inspection camera. See `assets/IMAGE_CREDITS.md` for source
links and license. ISS geometry credit: NASA; original repository GLB.

`assets/evidence.json` preserves the graph, route, target positions and provenance
hashes. `QA.json` records editability, figure dimensions and preservation checks.
The generator sources are included for use in the original repository environment;
the editable diagrams and their embedded illustrations are fully self-contained.
'''


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    baseline_paths = [ROOT/'OrbInspectLatex/main.tex', ROOT/'OrbInspectLatex/main.pdf',
        ROOT/'OrbInspectLatex/figures/required_target/orbinspect_framework.drawio',
        ROOT/'OrbInspectLatex/figures/required_target/orbinspect_framework.pdf']
    baseline={str(p.relative_to(ROOT)):digest(p) for p in baseline_paths}
    data=load_evidence()
    pages=[integrated(data),overview(data),mechanism(data)]
    review=pymupdf.open()
    master=ET.Element('mxfile',host='app.diagrams.net',type='device')
    report={'status':'review drafts; manuscript unchanged','pages':[],
            'evidence_scenario':data['scenario_id'],'source_hashes':data['sources']}
    for draft in pages:
        doc=draft.save()
        width=182/25.4*72
        page=review.new_page(width=width,height=width*draft.height/WIDTH)
        page.show_pdf_page(page.rect,doc,0)
        master.append(copy.deepcopy(draft.mx.find('diagram')))
        cells=list(draft.cells)
        issues=[]
        for label in draft.labels:
            font=pymupdf.Font('hebo' if label['bold'] else 'helv')
            if not label.get('equation'):
                for line in label['text'].split('\n'):
                    measured=font.text_length(line,fontsize=label['size'])
                    if measured > label['w']*1.01:issues.append({'text':line,'width':measured,'box':label['w']})
        report['pages'].append(dict(name=draft.name, stem=draft.stem, native_cells=len(cells)-2,
            photo_objects=draft.image_count, vector_mesh_facets=draft.mesh_facets,
            label_count=len(draft.labels), word_count=sum(len(t['text'].split()) for t in draft.labels),
            width_mm=182,height_mm=182*draft.height/WIDTH,
            min_font_pt=min(t['size'] for t in draft.labels)*width/WIDTH,
            text_width_warnings=issues))
    ET.indent(master,space='  ')
    ET.ElementTree(master).write(OUT/'OrbInspect_figure_options.drawio',encoding='utf-8',xml_declaration=True)
    review.set_metadata({'title':'OrbInspect editable figure alternatives','subject':'Discussion drafts: A integrated; B1 overview; B2 ADP mechanism',
                         'author':'OrbInspect authors'})
    review.save(PDF,garbage=4,deflate=True)
    (OUT/'README.md').write_text(README)
    assets=OUT/'assets';assets.mkdir(exist_ok=True)
    clean_data={k:v for k,v in data.items() if k not in ['mesh','normals']}
    (assets/'evidence.json').write_text(json.dumps(clean_data,indent=2)+'\n')
    for name in ['camera_alexander_lucke.jpg','IMAGE_CREDITS.md']:
        shutil.copy2(ASSETS/name,assets/name)
    source=OUT/'source';source.mkdir(exist_ok=True)
    for name in ['generate_figure_options.py','generate_editable_framework.py']:
        shutil.copy2(Path(__file__).with_name(name),source/name)
    report['preserved_sha256']=baseline
    report['manuscript_and_current_figure_unchanged']=all(digest(ROOT/p)==value for p,value in baseline.items())
    assert report['manuscript_and_current_figure_unchanged']
    (OUT/'QA.json').write_text(json.dumps(report,indent=2)+'\n')
    with zipfile.ZipFile(OUT.with_suffix('.zip'),'w',compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(OUT.rglob('*')):
            if path.is_file():bundle.write(path,path.relative_to(OUT.parent))
        bundle.write(PDF,OUT.name+'/'+PDF.name)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
