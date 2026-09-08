#!/usr/bin/env python3
"""Apply a reference palette to existing vectors; prove all non-color content is fixed.

Figure contract: preserve the sensing -> audited graph -> rollout ADP argument,
all three schematic-composite layouts, labels, evidence and 182-mm export sizes.
This is a Python/native-vector color test, not a redesign or manuscript revision.
The camera photo and rendered ISS geometry/colors remain untouched.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
import zlib

import pymupdf
from PIL import Image

ET.register_namespace('', 'http://www.w3.org/2000/svg')
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'output/figure_options_v2_20260907'
OUT = ROOT/'output/figure_color_test_20260907'
PDF = ROOT/'output/pdf/OrbInspect_figure_color_test_20260907.pdf'
STEMS = ['A_integrated', 'B1_overview', 'B2_adp_mechanism']
HEX = re.compile(r'#[0-9a-fA-F]{6}\b')
COLOR_KEYS = {'fillColor', 'strokeColor', 'fontColor', 'gradientColor', 'labelBackgroundColor'}
SVG_COLOR_KEYS = {'fill', 'stroke', 'color', 'stop-color', 'flood-color'}

PALETTE = {
    'background':'#FFFFFF', 'ink':'#000000', 'adp_panel':'#E0F1F1',
    'neutral':'#DDDDDD', 'lavender':'#F0EDF4', 'cream':'#FFF2E1',
    'soft_pink':'#FAE8E7', 'charcoal':'#303E44', 'warm_brown':'#956054',
    'purple':'#8771AA', 'violet':'#9B75C8', 'teal':'#3F91A6',
    'green':'#27A27F', 'orange':'#E97900', 'peach':'#FDD3AF',
    'red':'#C30000', 'red_text':'#830027', 'muted_red':'#C4594E',
}

GENERAL = {
    '#20252B':'#000000', '#5A7D94':'#3F91A6', '#8C2940':'#C30000',
    '#3D725B':'#27A27F', '#A77F29':'#E97900', '#A8B2BB':'#BCBCBC',
    '#B5C9D7':'#8771AA', '#8193A0':'#000000', '#798A99':'#000000',
    '#96A3AE':'#BCBCBC', '#85939E':'#000000', '#82919D':'#000000',
    '#83909A':'#000000', '#BEC5CA':'#DDDDDD',
}
FILLS = {
    '#F0F1F5':'#FFFFFF', '#ECF2F6':'#FFFFFF', '#F9EDE7':'#E0F1F1',
    '#FCF4E1':'#FFFFFF', '#E9F2EC':'#F0EDF4', '#D7D4E7':'#8771AA',
    '#E9D4C7':'#FDD3AF', '#F1D8A7':'#FFF2E1', '#F2F7FB':'#F0EDF4',
    '#DDE4E9':'#DDDDDD', '#CCD3DA':'#DDDDDD',
}


def color(value, role='fill', shape=''):
    original = value.upper()
    if role == 'text' and original == '#8C2940':
        return PALETTE['red_text']
    if role == 'fill':
        if original == '#CBE3D8':
            return PALETTE['teal'] if shape in {'ellipse', 'circle'} else PALETTE['charcoal']
        if original == '#E9C6C7':
            return PALETTE['muted_red'] if shape in {'ellipse', 'circle'} else PALETTE['warm_brown']
        if original in FILLS:
            return FILLS[original]
    if role == 'stroke' and original == '#CCD3DA':
        return PALETTE['ink']
    return GENERAL.get(original, value)


def decode_stencil(value):
    return urllib.parse.unquote(zlib.decompress(base64.b64decode(value), -15).decode())


def encode_stencil(value):
    quoted = urllib.parse.quote(value, safe="~()*!.'")
    compressor = zlib.compressobj(level=9, wbits=-15)
    return base64.b64encode(compressor.compress(quoted.encode())+compressor.flush()).decode()


def recolor_stencil(packed):
    tree = ET.fromstring(decode_stencil(packed))
    for element in tree.iter():
        if element.tag in {'fillcolor', 'strokecolor'}:
            role = 'fill' if element.tag == 'fillcolor' else 'stroke'
            element.set('color', color(element.get('color'), role))
    return encode_stencil(ET.tostring(tree, encoding='unicode'))


def white_label(cell):
    value = cell.get('value', '')
    return ('Goal reached<br>Finite cost' in value or 'Noncompletion<br>+∞' in value)


def recolor_native(original):
    tree = copy.deepcopy(original)
    changed = []
    for page in tree.findall('diagram'):
        page_changes = []
        for cell in page.findall('.//mxCell'):
            old = cell.get('style', '')
            # Keep the original photograph and ISS rendering byte-for-byte.
            if 'NASA ISS' in cell.get('tooltip', '') or 'image=data:' in old:
                continue
            shape = 'ellipse' if old.startswith('ellipse;') else 'rect'
            result = []
            for token in old.split(';'):
                if '=' not in token:
                    result.append(token)
                    continue
                key, value = token.split('=', 1)
                if key in COLOR_KEYS:
                    role = 'text' if key == 'fontColor' else ('stroke' if key == 'strokeColor' else 'fill')
                    value = '#FFFFFF' if key == 'fontColor' and white_label(cell) else color(value, role, shape)
                elif key == 'shape' and value.startswith('stencil('):
                    value = 'stencil('+recolor_stencil(value[8:-1])+')'
                result.append(key+'='+value)
            new = ';'.join(result)
            if new != old:
                cell.set('style', new)
                page_changes.append(cell.get('id'))
        changed.append({'page':page.get('name'), 'color_changed_cells':len(page_changes)})
    return tree, changed


def recolor_svg(original):
    tree = copy.deepcopy(original)
    dark_labels = set()
    for node in tree.iter():
        if node.tag.rsplit('}', 1)[-1] == 'text':
            text = ''.join(node.itertext())
            if text in {'Goal reached', 'Finite cost', 'Noncompletion'}:
                dark_labels.add(id(node))
            # +infinity is white only in the full mechanism's outcome box.
            if text == '+∞' and float(node.get('font-size', '0')) == 24:
                dark_labels.add(id(node))
    for node in tree.iter():
        tag = node.tag.rsplit('}', 1)[-1]
        if tag == 'image' or (tag == 'polygon' and node.get('stroke') == '#657685'):
            continue
        for key, value in list(node.attrib.items()):
            if key in SVG_COLOR_KEYS:
                role = 'text' if tag in {'text', 'tspan'} else ('stroke' if key == 'stroke' else 'fill')
                node.set(key, '#FFFFFF' if id(node) in dark_labels and key == 'fill' else color(value, role, tag))
            elif key == 'style':
                node.set(key, HEX.sub(lambda match:color(match.group(), 'text'), value))
    return tree


def normalized_native(original):
    tree = copy.deepcopy(original)
    for cell in tree.findall('.//mxCell'):
        if 'NASA ISS' in cell.get('tooltip', '') or 'image=data:' in cell.get('style', ''):
            continue
        tokens = []
        for token in cell.get('style', '').split(';'):
            if '=' in token:
                key, value = token.split('=', 1)
                if key in COLOR_KEYS:
                    token = key+'=<COLOR>'
                elif key == 'shape' and value.startswith('stencil('):
                    inner = ET.fromstring(decode_stencil(value[8:-1]))
                    for e in inner.iter():
                        if e.tag in {'fillcolor', 'strokecolor'}:
                            e.set('color', '<COLOR>')
                    token = 'shape='+ET.tostring(inner, encoding='unicode')
            tokens.append(token)
        if 'style' in cell.attrib:
            cell.set('style', ';'.join(tokens))
    return [(e.tag, e.attrib, e.text, e.tail) for e in tree.iter()]


def normalized_svg(original):
    tree = copy.deepcopy(original)
    for e in tree.iter():
        tag = e.tag.rsplit('}', 1)[-1]
        if tag == 'image' or (tag == 'polygon' and e.get('stroke') == '#657685'):
            continue
        for key, value in list(e.attrib.items()):
            if key in SVG_COLOR_KEYS:
                e.set(key, '<COLOR>')
            elif key == 'style':
                e.set(key, HEX.sub('<COLOR>', value))
    return [(e.tag, e.attrib, e.text, e.tail) for e in tree.iter()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path, required=True)
    args = parser.parse_args()
    reference = Image.open(args.reference).convert('RGB')
    counts = reference.getcolors(reference.width*reference.height)
    pixels = {'#%02X%02X%02X'%rgb:n for n, rgb in counts}
    assert all(value in pixels for value in PALETTE.values())
    preserved_paths = [p for p in SOURCE.rglob('*') if p.is_file()]
    preserved_paths += [ROOT/'OrbInspectLatex/main.tex', ROOT/'OrbInspectLatex/main.pdf',
                        ROOT/'output/pdf/OrbInspect_figure_options_v2_20260907.pdf']
    preserved = {str(p.relative_to(ROOT)):digest(p) for p in preserved_paths}
    OUT.mkdir(parents=True, exist_ok=True)
    master_source = ET.parse(SOURCE/'OrbInspect_figure_options.drawio').getroot()
    master, changes = recolor_native(master_source)
    assert normalized_native(master) == normalized_native(master_source)
    ET.ElementTree(master).write(OUT/'OrbInspect_figure_options.drawio', encoding='utf-8', xml_declaration=True)
    review = pymupdf.open()
    source_pdf = pymupdf.open(ROOT/'output/pdf/OrbInspect_figure_options_v2_20260907.pdf')
    for i, stem in enumerate(STEMS):
        native_original = ET.parse(SOURCE/(stem+'.drawio')).getroot()
        native, _ = recolor_native(native_original)
        assert normalized_native(native) == normalized_native(native_original)
        ET.ElementTree(native).write(OUT/(stem+'.drawio'), encoding='utf-8', xml_declaration=True)
        page_structure = lambda e: [(n.tag, n.attrib, (n.text or '').strip()) for n in e.iter()]
        assert page_structure(native.find('diagram')) == page_structure(master.findall('diagram')[i])
        svg_original = ET.parse(SOURCE/(stem+'.svg')).getroot()
        svg = recolor_svg(svg_original)
        assert normalized_svg(svg) == normalized_svg(svg_original)
        raw = ET.tostring(svg, encoding='utf-8')
        (OUT/(stem+'.svg')).write_bytes(raw)
        vector = pymupdf.open(stream=raw, filetype='svg')
        doc = pymupdf.open('pdf', vector.convert_to_pdf())
        doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(OUT/(stem+'.png'))
        page = review.new_page(width=source_pdf[i].rect.width, height=source_pdf[i].rect.height)
        page.show_pdf_page(page.rect, doc, 0)
        old_images = source_pdf[i].get_image_info(hashes=True)
        new_images = page.get_image_info(hashes=True)
        assert len(new_images) == len(old_images)
        for old, new in zip(old_images, new_images):
            assert old['digest'] == new['digest']
            assert all(abs(a-b) < .001 for a,b in zip(old['bbox'], new['bbox']))
        # The labels, their positions and glyph sizes must stay fixed in export.
        old_words = source_pdf[i].get_text('words')
        new_words = page.get_text('words')
        assert len(new_words) == len(old_words)
        for old, new in zip(old_words, new_words):
            assert old[4:] == new[4:]
            assert all(abs(a-b) < .001 for a,b in zip(old[:4], new[:4]))
    review.set_metadata(source_pdf.metadata)
    review.save(PDF, garbage=4, deflate=True)
    shutil.copytree(SOURCE/'assets', OUT/'assets', dirs_exist_ok=True)
    (OUT/'source').mkdir(exist_ok=True)
    shutil.copy2(__file__, OUT/'source'/Path(__file__).name)
    (OUT/'README.md').write_text('''# Reference-palette color test

This is a separate color-only copy of the three existing alternatives: A is the
integrated figure; B1 and B2 are the complementary pair. No layout or content
decision has been applied to the manuscript.

Colors are sampled exactly from the supplied reference: white backgrounds and
black outlines; pale cyan ADP panel; charcoal/brown outcome blocks; purple, teal,
green and red accents; cream value bar. White lettering is used on dark blocks.
Fonts, sizes, wording, equations, geometry, connectors, widths, dashes and page
dimensions are unchanged. The camera photo and original ISS rendering are intact.

The master and each individual .drawio file remain editable. SVG and PNG previews
and a three-page review PDF are included. QA.json records a strict non-color
comparison and preservation hashes. palette.json gives the sampled palette.
''')
    report = {'operation':'color-only discussion test', 'source_reference_sha256':digest(args.reference),
        'pages':changes, 'palette_exactly_present_in_reference':True,
        'native_non_color_structure_unchanged':True, 'svg_non_color_structure_unchanged':True,
        'text_and_equation_values_unchanged':True, 'fonts_sizes_and_geometry_unchanged':True,
        'export_word_positions_unchanged':True, 'camera_and_ISS_unchanged':True,
        'preserved_sha256':preserved,
        'source_figures_and_manuscript_unchanged':all(digest(ROOT/p)==h for p,h in preserved.items())}
    assert report['source_figures_and_manuscript_unchanged']
    (OUT/'QA.json').write_text(json.dumps(report, indent=2)+'\n')
    (OUT/'palette.json').write_text(json.dumps(PALETTE, indent=2)+'\n')
    with zipfile.ZipFile(OUT.with_suffix('.zip'), 'w', zipfile.ZIP_DEFLATED) as bundle:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():bundle.write(p, p.relative_to(OUT.parent))
        bundle.write(PDF, OUT.name+'/'+PDF.name)
    with zipfile.ZipFile(OUT.with_suffix('.zip')) as bundle:
        assert bundle.testzip() is None
    print(json.dumps({key:value for key,value in report.items() if key != 'preserved_sha256'}, indent=2))


if __name__ == '__main__':
    main()
