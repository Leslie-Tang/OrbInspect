#!/usr/bin/env python3
"""Validate the editable LOS/HCW/ADP drafts against their archived evidence."""
import argparse
import base64
import csv
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
import zlib

import numpy as np
import pymupdf

from generate_figure_options_v2 import OUT, PDF, ROOT, pack

sha = lambda value: hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-visually-checked', action='store_true')
    parser.add_argument('--pdf-visually-checked', action='store_true')
    args = parser.parse_args()
    report = json.loads((OUT/'QA.json').read_text())
    for path, expected in {**report['source_hashes'], **report['preserved_sha256']}.items():
        assert sha((ROOT/path).read_bytes()) == expected, path
    master = ET.parse(OUT/'OrbInspect_figure_options.drawio').getroot()
    assert len(master.findall('diagram')) == 3
    camera = (OUT/'assets/camera_alexander_lucke.jpg').read_bytes()
    assert camera == (ROOT/'OrbInspectLatex/figures/required_target/framework_assets/camera_alexander_lucke.jpg').read_bytes()
    stencil_counts = []
    for page, record in zip(master.findall('diagram'), report['pages']):
        cells = page.findall('.//mxCell')
        ids = [cell.get('id') for cell in cells]
        assert len(set(ids)) == len(ids)
        assert len(cells)-2 == record['native_cells']
        assert not record['text_width_warnings']
        native = ET.parse(OUT/(record['stem']+'.drawio')).getroot().find('diagram')
        structure = lambda node: [(e.tag, e.attrib, (e.text or '').strip()) for e in node.iter()]
        assert structure(native) == structure(page)
        photo_count, mesh_count, geometry_count = 0, 0, 0
        for cell in cells:
            style = cell.get('style', '')
            if 'image=data:image/jpeg,' in style:
                encoded = style.split('image=data:image/jpeg,')[1].split(';')[0]
                assert base64.b64decode(encoded) == camera
                photo_count += 1
            if 'shape=stencil(' in style:
                encoded = re.search(r'shape=stencil\(([^)]+)\)', style).group(1)
                source = urllib.parse.unquote(zlib.decompress(base64.b64decode(encoded), -15).decode())
                stencil = ET.fromstring(source)
                paths = stencil.findall('.//path')
                assert paths
                if 'NASA ISS' in cell.get('tooltip', ''):
                    mesh_count += len(paths)
                else:
                    geometry_count += len(paths)
                    assert len(paths) == 1
                for node in stencil.iter():
                    for key in ('x', 'y', 'w', 'h'):
                        if key in node.attrib:
                            assert np.isfinite(float(node.get(key)))
        assert photo_count == record['photo_objects']
        assert mesh_count == record['vector_mesh_facets']
        assert geometry_count == (3 if photo_count else 0)
        stencil_counts.append({'ISS_facets':mesh_count, 'LOS_geometry':geometry_count})
        labels = ''.join(cell.get('value', '') for cell in cells).lower()
        assert all(word not in labels for word in ['backpropagat', 'passive drift', 'collision violation'])
        assert 'bellman backup' in labels
        if record['stem'] != 'B1_overview':
            assert 's = (j, m, b, h)' in labels
            assert 'noncompletion' in labels and 'finite cost' in labels
    doc = pymupdf.open(PDF)
    assert len(doc) == 3
    for index, page in enumerate(doc):
        assert abs(page.rect.width*25.4/72-182) < .001
        text = page.get_text().lower()
        assert 'rollout adp' in text and '\ufffd' not in text
        assert ('9/9' in text) if index < 2 else ('no certified completion' in text)
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    box = pymupdf.Rect(span['bbox'])
                    assert box.x0 >= -1 and box.y0 >= -1
                    assert box.x1 <= page.rect.width+1 and box.y1 <= page.rect.height+1
    evidence = json.loads((OUT/'assets/evidence.json').read_text())
    assert sum(t['required'] for t in evidence['targets']) == 9
    assert evidence['required_covered'] == evidence['required_count'] == 9
    study = ROOT/'data/results/20260905_101500_required_target_confirmation'
    graph = json.loads((study/'raw/hcw_graph.json').read_text())
    actual = {(edge['source_id'], edge['target_id']) for edge in graph['edges'] if edge['feasible']}
    assert all(tuple(edge) in actual for edge in evidence['graph_edges'])
    transfer = evidence['hcw_transfer']
    with (study/'raw/representative_case_trajectory.csv').open() as stream:
        rows = [r for r in csv.DictReader(stream) if r['method'] == 'adaptive_rollout_adp' and r['action'] == '4']
    source = graph['node_positions'][graph['node_ids'].index(transfer['source_id'])]
    positions = [source]+[[float(r['r'+axis]) for axis in 'xyz'] for r in rows]
    controls = [[float(r['u'+axis]) for axis in 'xyz'] for r in rows]
    assert len(rows) == 30 and transfer['duration_s'] == 90
    assert positions == transfer['positions_xyz'] and controls == transfer['controls_xyz']
    edge = next(e for e in graph['edges'] if e['source_id'] == transfer['source_id'] and e['target_id'] == transfer['target_id'])
    assert transfer['audit_record'] == edge and edge['feasible']
    peak = float(np.linalg.norm(controls, axis=1).max())
    assert abs(peak-edge['peak_input']) < 1e-12 and peak < edge['input_limit']
    for name in ['generate_figure_options_v2.py', 'generate_figure_options.py', 'generate_editable_framework.py']:
        assert (OUT/'source'/name).read_bytes() == (Path(__file__).parent/name).read_bytes()
    report['validation'] = {
        'native_pages':3,
        'separate_files_match_master':True,
        'native_stencils_validated':stencil_counts,
        'original_camera_bytes_preserved':True,
        'archived_sources_manuscript_and_v1_hashes_match':True,
        'all_graph_arcs_are_archived_passed_audits':True,
        'hcw_positions_and_controls_match_30_archived_intervals':True,
        'hcw_peak_control_m_s2':peak,
        'review_pdf_pages_and_text_bounds_checked':True,
        'native_drawio_import_visually_checked':args.native_visually_checked,
        'poppler_review_pdf_visually_checked':args.pdf_visually_checked,
        'equation_export':'Vector outlines; corresponding draw.io equations are editable HTML text.',
    }
    (OUT/'QA.json').write_text(json.dumps(report, indent=2)+'\n')
    pack()
    with zipfile.ZipFile(OUT.with_suffix('.zip')) as archive:
        assert archive.testzip() is None
        for path in OUT.rglob('*'):
            if path.is_file():
                assert archive.read(str(path.relative_to(OUT.parent))) == path.read_bytes()
        assert archive.read(OUT.name+'/'+PDF.name) == PDF.read_bytes()
    print(json.dumps(report['validation'], indent=2))


if __name__ == '__main__':
    main()
