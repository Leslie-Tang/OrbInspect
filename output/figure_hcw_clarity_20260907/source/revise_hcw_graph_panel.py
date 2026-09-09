#!/usr/bin/env python3
"""Replace only integrated panel c with an explicit transfer/audit/graph sequence.

Figure contract: a source-dependent HCW transfer becomes an available SOOA edge
only after all enabled motion audits pass; observation visibility belongs to the
destination node. Preserve the other panels, reference palette, 182-mm dimensions,
archived evidence and editable Python/native-vector output workflow.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
from PIL import Image, ImageChops
import pymupdf

from generate_figure_options import Draft

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'output/figure_color_test_20260907'
OUT = ROOT/'output/figure_hcw_clarity_20260907'
PDF = ROOT/'output/pdf/OrbInspect_figure_hcw_clarity_20260907.pdf'
ET.register_namespace('', 'http://www.w3.org/2000/svg')
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
BLACK, WHITE = '#000000', '#FFFFFF'
TEAL, GREEN, RED, BURGUNDY = '#3F91A6', '#27A27F', '#C30000', '#830027'
PINK, CREAM = '#FAE8E7', '#FFF2E1'


def panel(data):
    d = Draft('Panel c', 'hcw_panel', 1160)
    d.box(480,80,828,390,WHITE,BLACK,16,1.4)
    d.text(498,96,792,44,'c  HCW transfer → SOOA graph',31,True,BLACK,align='left')
    for x,w,label in [(500,240,'1  Solve HCW'), (782,223,'2  Audit motion'), (1053,239,'3  Build graph')]:
        d.box(x,151,w,37,PINK,'none',7,0)
        d.text(x+5,155,w-10,29,label,26,True,BLACK)

    # Step 1: the actual archived C70-to-C68 transfer, not a decorative curve.
    positions = np.array(data['hcw_transfer']['positions_xyz'])[:,[0,2]]
    center = (positions.min(axis=0)+positions.max(axis=0))/2
    points = [(618+(x-center[0])*2.5, 273-(z-center[1])*2.5) for x,z in positions]
    d.text(500,195,242,29,'Rest-to-rest · 90 s',23,color=BLACK)
    d.line(points,TEAL,2.9)
    d.line(points[13:17],TEAL,2.9,True)
    d.circle(*points[0],8,WHITE,TEAL,1.9)
    d.circle(*points[-1],8,TEAL,GREEN,1.9)
    d.text(points[0][0]-64,points[0][1]-14,53,28,'C70',23,True,BLACK)
    d.text(points[-1][0]+12,points[-1][1]-14,60,28,'C68',23,True,BLACK)
    d.line([(510,313),(540,313)],BLACK,1.2,True)
    d.line([(510,313),(510,283)],BLACK,1.2,True)
    d.text(541,300,25,26,'x',22,color=BLACK)
    d.text(498,255,25,26,'z',22,color=BLACK)
    d.text(504,347,240,28,'Trajectory + control',24,True,BLACK)
    d.text(505,381,238,28,'xᵢⱼ(t), uᵢⱼ(t)',25,color=BLACK)
    d.line([(746,264),(780,264)],BLACK,2,True)

    # Step 2: all checks must pass, including the previously implicit speed test.
    d.box(782,207,223,125,WHITE,BLACK,8,1.1)
    for y,label in [(212,'Input + speed'), (250,'Mesh clearance'), (288,'Terminal errors')]:
        d.check(799,y+15,GREEN,.64)
        d.text(818,y,176,29,label,23,color=BLACK,align='left')
    d.text(777,343,232,31,'All pass: χᵢⱼ = 1',23,True,GREEN)
    d.text(780,386,228,29,'Fail → omit edge',23,color=BURGUNDY)
    d.line([(1007,264),(1060,264)],GREEN,2,True)
    d.text(1008,230,49,27,'pass',22,color=GREEN)

    # Step 3: one accepted directed edge, with node/edge records distinguished.
    d.text(1060,198,226,28,'SOOA aᵢⱼ',25,True,BLACK)
    source, target = (1090,264), (1244,264)
    d.circle(*source,25,WHITE,TEAL,1.8)
    d.circle(*target,25,WHITE,TEAL,1.8)
    d.text(source[0]-25,source[1]-15,50,30,'C70',23,color=BLACK)
    d.text(target[0]-25,target[1]-15,50,30,'C68',23,color=BLACK)
    d.line([(1117,264),(1217,264)],TEAL,2.5,True)
    d.text(1135,228,67,28,'ℓᵢⱼ',25,color=BLACK)
    d.text(1048,301,93,27,'Source i',23,color=BLACK)
    d.text(1195,301,95,27,'View j',23,color=BLACK)
    d.text(1049,340,245,29,'Edge: motion + cost',23,True,BLACK)
    # The camera connector is unchanged and terminates at (1190,414).
    d.box(1054,379,242,35,CREAM,TEAL,7,1.2)
    d.text(1060,382,230,29,'Node: view + mask Gⱼ',23,color=BLACK)
    return d


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def structure(node):
    return [(e.tag,e.attrib,(e.text or '').strip()) for e in node.iter()]


def main():
    data = json.loads((SOURCE/'assets/evidence.json').read_text())
    edge = data['hcw_transfer']['audit_record']
    assert edge['feasible'] and edge['source_id']=='cand_0070' and edge['target_id']=='cand_0068'
    saved_paths = [p for p in SOURCE.rglob('*') if p.is_file()]
    saved_paths += [ROOT/'OrbInspectLatex/main.tex', ROOT/'OrbInspectLatex/main.pdf',
                    ROOT/'output/pdf/OrbInspect_figure_color_test_20260907.pdf']
    saved = {str(p.relative_to(ROOT)):sha(p) for p in saved_paths}
    d = panel(data)
    warnings = []
    for label in d.labels:
        font = pymupdf.Font('hebo' if label['bold'] else 'helv')
        for text in label['text'].split('\n'):
            width = font.text_length(text,fontsize=label['size'])
            if width > label['w']*1.01:
                warnings.append({'text':text,'width':width,'box':label['w']})
    print('Text width warnings:',warnings)
    OUT.mkdir(parents=True, exist_ok=True)

    # Existing section c is exactly cells 134..180; connectors are kept intact.
    original = ET.parse(SOURCE/'A_integrated.drawio').getroot()
    native = copy.deepcopy(original)
    cells = native.find('.//root')
    old = list(cells)
    removed = [c for c in old if 134<=int(c.get('id'))<=180]
    assert len(removed)==47 and 'HCW transfer' in removed[1].get('value','')
    insertion = old.index(removed[0])
    for c in removed:cells.remove(c)
    added = []
    for index,c in enumerate(list(d.cells)[2:]):
        item=copy.deepcopy(c);item.set('id',f'hcw-c-{index}')
        added.append(item);cells.insert(insertion+index,item)
    before=[c for c in original.findall('.//mxCell') if c.get('id') not in {e.get('id') for e in removed}]
    after=[c for c in native.findall('.//mxCell') if not c.get('id').startswith('hcw-c-')]
    assert [structure(c) for c in before] == [structure(c) for c in after]
    ET.ElementTree(native).write(OUT/'A_integrated.drawio',encoding='utf-8',xml_declaration=True)

    svg_original = ET.parse(SOURCE/'A_integrated.svg').getroot()
    svg = copy.deepcopy(svg_original)
    elements=list(svg)
    start=next(i for i,e in enumerate(elements) if e.tag.rsplit('}',1)[-1]=='rect'
        and e.get('x')=='480' and e.get('y')=='80')
    end=next(i for i,e in enumerate(elements) if e.tag.rsplit('}',1)[-1]=='text'
        and ''.join(e.itertext())=='ℓᵢⱼ; χᵢⱼ')+1
    section_xml=ET.fromstring(d.svg[0]+'\n'.join(d.svg[2:])+'</svg>')
    for e in elements[start:end]:svg.remove(e)
    for i,e in enumerate(section_xml):svg.insert(start+i,copy.deepcopy(e))
    preserved_svg=list(svg)[:start]+list(svg)[start+len(section_xml):]
    original_svg=elements[:start]+elements[end:]
    assert [structure(e) for e in preserved_svg]==[structure(e) for e in original_svg]
    raw=ET.tostring(svg,encoding='utf-8')
    (OUT/'A_integrated.svg').write_bytes(raw)
    source=pymupdf.open(stream=raw,filetype='svg')
    page_doc=pymupdf.open('pdf',source.convert_to_pdf())
    page_doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(OUT/'A_integrated.png')

    # Only the requested panel may differ even at the rendered-pixel level.
    image_old=Image.open(SOURCE/'A_integrated.png').convert('RGB')
    image_new=Image.open(OUT/'A_integrated.png').convert('RGB')
    diff=np.asarray(ImageChops.difference(image_old,image_new)).copy()
    diff[int(78*1.5):int(473*1.5),int(478*1.5):int(1311*1.5)]=0
    assert not diff.any(), 'Unexpected rendered changes outside section c'

    master=ET.parse(SOURCE/'OrbInspect_figure_options.drawio').getroot()
    old_page=master.findall('diagram')[0]
    master.remove(old_page);master.insert(0,copy.deepcopy(native.find('diagram')))
    ET.ElementTree(master).write(OUT/'OrbInspect_figure_options.drawio',encoding='utf-8',xml_declaration=True)
    for stem in ['B1_overview','B2_adp_mechanism']:
        for extension in ['drawio','svg','png']:
            shutil.copy2(SOURCE/(stem+'.'+extension),OUT/(stem+'.'+extension))
    previous_pdf=pymupdf.open(ROOT/'output/pdf/OrbInspect_figure_color_test_20260907.pdf')
    review=pymupdf.open()
    page=review.new_page(width=previous_pdf[0].rect.width,height=previous_pdf[0].rect.height)
    page.show_pdf_page(page.rect,page_doc,0)
    review.insert_pdf(previous_pdf,from_page=1,to_page=2)
    review.set_metadata(previous_pdf.metadata)
    review.save(PDF,garbage=4,deflate=True)
    for i in [1,2]:
        assert review[i].get_pixmap().samples==previous_pdf[i].get_pixmap().samples
    shutil.copytree(SOURCE/'assets',OUT/'assets',dirs_exist_ok=True)
    shutil.copy2(SOURCE/'palette.json',OUT/'palette.json')
    (OUT/'source').mkdir(exist_ok=True)
    for file in [Path(__file__),Path(__file__).with_name('generate_figure_options.py'),
                 Path(__file__).with_name('generate_editable_framework.py')]:
        shutil.copy2(file,OUT/'source'/file.name)
    (OUT/'README.md').write_text('''# Section c: HCW transfer to SOOA graph

Only section c of A (the integrated alternative) has changed. B1, B2, all other
A panels, the camera/graph and graph/ADP connectors, and the reference palette
are preserved. The manuscript and preceding alternatives are untouched.

The revised sequence is:
1. Solve the source-to-destination rest-to-rest HCW transfer.
2. Audit input/speed limits, mesh clearance (including the swept checks), and
   terminal position/velocity errors. All enabled checks must pass. A failed
   audit omits the edge; the example shown is a passed archived transfer.
3. Store the accepted transfer as the directed SOOA edge, with its motion record
   and stage cost. Observation pose/visibility belongs to the destination node,
   not to the edge. The existing camera connector now visibly feeds that record.

The C70-to-C68 x-z trajectory is the same archived 90-second transfer, displayed
with equal position scale. The two-node excerpt illustrates one graph edge;
the construction is repeated for candidate pairs. No new motion result, passive
drift guarantee, full-surface coverage claim or execution result is introduced.
The existing ADP panels are unchanged.

Native draw.io shapes and text remain editable. The QA report compares unchanged
native and SVG objects and confirms zero pixel changes outside the revised panel.
The three-page PDF retains the two complementary alternatives without edits.
''')
    report={'revision':'Integrated section c only','new_panel_native_cells':len(added),
        'text_width_warnings':warnings,'all_other_native_cells_identical':True,
        'all_other_svg_elements_identical':True,'zero_pixel_changes_outside_section_c':True,
        'B1_and_B2_copied_unchanged':True,'same_archived_transfer':edge,
        'preserved_sha256':saved,'sources_and_manuscript_unchanged':all(sha(ROOT/p)==h for p,h in saved.items())}
    assert report['sources_and_manuscript_unchanged']
    (OUT/'QA.json').write_text(json.dumps(report,indent=2)+'\n')
    with zipfile.ZipFile(OUT.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as bundle:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():bundle.write(p,p.relative_to(OUT.parent))
        bundle.write(PDF,OUT.name+'/'+PDF.name)
    with zipfile.ZipFile(OUT.with_suffix('.zip')) as bundle:assert bundle.testzip() is None
    print(json.dumps({k:v for k,v in report.items() if k!='preserved_sha256'},indent=2))


if __name__=='__main__':main()
