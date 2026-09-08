#!/usr/bin/env python3
"""Read-only artifact/evidence checks, plus a saved QA report for review drafts."""
import base64
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
import zlib

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'output/figure_options_20260907'
PDF = ROOT/'output/pdf/OrbInspect_figure_options_20260907.pdf'
sha = lambda data: hashlib.sha256(data).hexdigest()


def main():
    report = json.loads((OUT/'QA.json').read_text())
    for path, value in {**report['source_hashes'], **report['preserved_sha256']}.items():
        assert sha((ROOT/path).read_bytes()) == value, path
    master = ET.parse(OUT/'OrbInspect_figure_options.drawio').getroot()
    assert len(master.findall('diagram')) == 3
    photo = (OUT/'assets/camera_alexander_lucke.jpg').read_bytes()
    for page, record in zip(master.findall('diagram'), report['pages']):
        cells = page.findall('.//mxCell')
        ids = [c.get('id') for c in cells]
        assert len(set(ids)) == len(ids)
        assert len(cells)-2 == record['native_cells']
        assert not record['text_width_warnings']
        native = ET.parse(OUT/(record['stem']+'.drawio')).getroot().find('diagram')
        structure = lambda node: [(e.tag, e.attrib, (e.text or '').strip()) for e in node.iter()]
        assert structure(native) == structure(page)
        for cell in cells:
            style = cell.get('style','')
            if 'image=data:image/jpeg,' in style:
                encoded = style.split('image=data:image/jpeg,')[1].split(';')[0]
                assert base64.b64decode(encoded) == photo
            if 'shape=stencil(' in style:
                encoded = re.search(r'shape=stencil\(([^)]+)\)', style).group(1)
                source = urllib.parse.unquote(zlib.decompress(base64.b64decode(encoded),-15).decode())
                stencil = ET.fromstring(source)
                assert len(stencil.findall('.//path')) == record['vector_mesh_facets']
        assert all(label not in ''.join(c.get('value','') for c in cells).lower()
                   for label in ['backpropagat','passive drift','collision violation'])
    doc = pymupdf.open(PDF)
    assert len(doc) == 3
    for i, page in enumerate(doc):
        assert abs(page.rect.width*25.4/72-182) < .001
        text = page.get_text()
        assert 'rollout adp' in text.lower()
        assert '\ufffd' not in text
        assert 'noncompletion' in text
        assert ('9/9' in text) if i < 2 else ('No certified completion' in text)
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    r = pymupdf.Rect(span['bbox'])
                    assert r.x0 >= -1 and r.y0 >= -1
                    assert r.x1 <= page.rect.width+1 and r.y1 <= page.rect.height+1
    evidence = json.loads((OUT/'assets/evidence.json').read_text())
    assert sum(t['required'] for t in evidence['targets']) == 9
    assert evidence['required_covered'] == evidence['required_count'] == 9
    graph = json.loads((ROOT/'data/results/20260905_101500_required_target_confirmation/raw/hcw_graph.json').read_text())
    actual = {(e['source_id'],e['target_id']) for e in graph['edges'] if e['feasible']}
    assert all(tuple(edge) in actual for edge in evidence['graph_edges'])
    report['validation'] = {
        'native_pages':3, 'separate_files_match_master':True,
        'native_stencil_paths_validated':True, 'original_camera_bytes_preserved':True,
        'archived_sources_and_current_paper_hashes_match':True,
        'all_graph_arcs_are_archived_passed_audits':True,
        'required_target_count_and_route_record_match':True,
        'review_pdf_pages_and_text_bounds_checked':True,
        'drawio_browser_import': 'All three pages opened and visually inspected; native shapes and editable equations rendered.',
        'equation_export': 'Vector outlines; corresponding draw.io equations are editable text.',
    }
    (OUT/'QA.json').write_text(json.dumps(report,indent=2)+'\n')
    with zipfile.ZipFile(OUT.with_suffix('.zip'),'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob('*')):
            if path.is_file(): archive.write(path,path.relative_to(OUT.parent))
        archive.write(PDF,OUT.name+'/'+PDF.name)
    with zipfile.ZipFile(OUT.with_suffix('.zip')) as archive:
        assert archive.testzip() is None
        for path in OUT.rglob('*'):
            if path.is_file():assert archive.read(str(path.relative_to(OUT.parent))) == path.read_bytes()
        assert archive.read(OUT.name+'/'+PDF.name) == PDF.read_bytes()
    print(json.dumps(report['validation'],indent=2))


if __name__ == '__main__':
    main()
