#!/usr/bin/env python3
"""Check standalone manuscript inputs and approved figure integrity."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
COMMAND = re.compile(r'\\(input|include|includegraphics|bibliography|bibliographystyle|documentclass)(?:\[[^\]]*\])?\{([^}]+)\}')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependencies() -> set[Path]:
    """Resolve project-relative TeX inputs, rejecting external dependencies."""
    pending, seen = [ROOT/'main.tex'], set()
    extensions = {'input': '.tex', 'include': '.tex', 'bibliography': '.bib',
                  'bibliographystyle': '.bst', 'documentclass': '.cls'}
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        assert path.is_file(), f'Missing input: {path}'
        assert path.resolve().is_relative_to(ROOT), f'External input: {path}'
        seen.add(path)
        if path.suffix != '.tex':
            continue
        text = re.sub(r'(?<!\\)%[^\n]*', '', path.read_text())
        for command, value in COMMAND.findall(text):
            for item in value.split(','):
                target = ROOT/item.strip()
                if not target.suffix:
                    target = target.with_suffix(extensions.get(command, '.pdf'))
                assert 'archive' not in target.relative_to(ROOT).parts, target
                pending.append(target)
    return seen


def check() -> dict:
    inputs = dependencies()
    manifest = json.loads((ROOT/'figures/manifest.json').read_text())
    checked = 0
    for figure in manifest['figures']:
        for record in figure['files']:
            path = ROOT/record['file']
            assert path.is_file() and sha(path) == record['sha256'], f'Figure changed: {record["file"]}'
            checked += 1
            if path.suffix == '.drawio':
                tree = ET.parse(path)
                cells = tree.findall('.//mxCell')
                assert cells, f'Expected native editable cells: {path.name}'
                for cell in cells:
                    for field in cell.get('style', '').split(';'):
                        if field.startswith('image='):
                            value = urllib.parse.unquote(field[6:])
                            assert value.startswith('data:image/'), f'External diagram image: {path.name}'
            elif path.suffix == '.svg':
                for element in ET.parse(path).iter():
                    for attr, value in element.attrib.items():
                        if attr.split('}')[-1] == 'href':
                            assert value.startswith(('data:', '#')), f'External SVG resource: {path.name}'
    assert [f['number'] for f in manifest['figures']] == list(range(1, 9))
    return {'local_compilation_inputs': len(inputs), 'figure_groups': len(manifest['figures']),
            'verified_figure_files': checked, 'external_project_inputs': 0,
            'native_diagram_images': 'embedded', 'status': 'passed'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-archive', action='store_true')
    args = parser.parse_args()
    result = check()
    if args.verify_archive:
        report = json.loads((ROOT/'docs/organization_manifest.json').read_text())
        for name, digest in report['original_files'].items():
            path = ROOT/report['archive']/name
            assert path.is_file() and sha(path) == digest, f'Archive mismatch: {name}'
        result['preserved_archive_files'] = len(report['original_files'])
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
