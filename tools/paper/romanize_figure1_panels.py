#!/usr/bin/env python3
"""Change only the five Figure 1 panel prefixes, with native/export parity.

The existing schematic argument, Python backend, 182-mm vector export, colors,
geometry, equations, data and typography remain fixed. User-requested Roman
numerals replace the earlier lowercase panel convention.
"""
from pathlib import Path
import copy
import json
import shutil
import xml.etree.ElementTree as ET

import pymupdf
from align_figure_notation import label_svg, structure, style_dict

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'output/figure1_typography_refined_20260908'
OUT = ROOT/'output/figure1_roman_labels_20260908'
STEM = 'viability_preserving_rollout_adp'
MAPPING = {'4': ('a', 'I.'), '99': ('b', 'II.'), 'hcw-c-1': ('c', 'III.'),
           'adp-d-1': ('d', 'IV.'), '235': ('e', 'V.')}
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    original = ET.parse(SOURCE/f'{STEM}.drawio').getroot()
    native = copy.deepcopy(original)
    original_svg = ET.parse(SOURCE/f'{STEM}.svg').getroot()
    svg = copy.deepcopy(original_svg)
    old_cells = {c.get('id'): c for c in original.findall('.//mxCell')}
    cells = {c.get('id'): c for c in native.findall('.//mxCell')}
    changes = []
    for ident, (letter, roman) in MAPPING.items():
        cell = cells[ident]
        lines = json.loads(cell.get('notationSource'))
        text = lines[0][0]['value']
        assert len(lines) == 1 and len(lines[0]) == 1 and text.startswith(letter+' ')
        lines[0][0]['value'] = roman+' '+text[1:].lstrip()
        group, metric = label_svg(cell, lines, 'Figure1')
        target = next(e for e in svg if e.get('data-cell-id') == ident)
        index = list(svg).index(target)
        svg.remove(target)
        svg.insert(index, group)
        assert metric['font_size'] == metric['original_font_size']
        assert structure(cell.find('mxGeometry')) == structure(old_cells[ident].find('mxGeometry'))
        assert style_dict(cell) == style_dict(old_cells[ident])
        assert json.loads(group.get('data-notation-source')) == json.loads(cell.get('notationSource'))
        changes.append({'before': text, 'after': lines[0][0]['value']})
    assert all(structure(cell) == structure(old_cells[ident])
               for ident, cell in cells.items() if ident not in MAPPING)
    assert [structure(e) for e in original_svg if e.get('data-cell-id') not in MAPPING] == [
        structure(e) for e in svg if e.get('data-cell-id') not in MAPPING]
    ET.ElementTree(native).write(OUT/f'{STEM}.drawio', encoding='utf-8', xml_declaration=True)
    raw = ET.tostring(svg, encoding='utf-8', xml_declaration=True)
    (OUT/f'{STEM}.svg').write_bytes(raw)
    source = pymupdf.open(stream=raw, filetype='svg')
    converted = pymupdf.open('pdf', source.convert_to_pdf())
    previous = pymupdf.open(SOURCE/f'{STEM}.pdf')
    pdf = pymupdf.open()
    page = pdf.new_page(width=previous[0].rect.width, height=previous[0].rect.height)
    page.show_pdf_page(page.rect, converted, 0)
    pdf.set_metadata(previous.metadata)
    pdf.save(OUT/f'{STEM}.pdf', garbage=4, deflate=True)
    page.get_pixmap(dpi=220).save(OUT/f'{STEM}.png')
    (OUT/'QA.json').write_text(json.dumps({
        'changes': changes, 'all_other_native_svg_objects_identical': True,
        'geometry_fonts_colors_and_equations_unchanged': True,
        'native_export_heading_text_equal': True, 'visual_review': 'pending'
    }, indent=2)+'\n')
    print(json.dumps(changes, indent=2))


if __name__ == '__main__':
    main()
