#!/usr/bin/env python3
"""Create a portable manuscript ZIP without history or repository dependencies."""
from pathlib import Path
import zipfile

from check_project import ROOT, check


def main() -> None:
    check()
    destination = ROOT/'build/OrbInspectLatex_source.zip'
    destination.parent.mkdir(exist_ok=True)
    roots = [ROOT/p for p in ('main.tex','references.bib','IEEEtaes.cls','IEEEtran.bst',
                              'Makefile','.latexmkrc','.gitignore','README.md',
                              'sections','tables','figures','data','scripts','docs')]
    members = []
    for root in roots:
        members.extend(root.rglob('*') if root.is_dir() else [root])
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(members):
            if path.is_file() and path.name != '.DS_Store' and '__pycache__' not in path.parts:
                assert path.resolve().is_relative_to(ROOT), path
                z.write(path, path.relative_to(ROOT))
    print(destination)


if __name__ == '__main__':
    main()
