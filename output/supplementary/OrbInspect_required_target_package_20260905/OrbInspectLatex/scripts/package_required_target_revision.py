#!/usr/bin/env python3
"""Package the verified IEEE revision without overwriting earlier deliverables."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
PAPER=ROOT/'OrbInspectLatex'


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy(path: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,destination)


def archive(directory: Path, refresh=False) -> Path:
    path=directory.with_suffix('.zip')
    if path.exists() and not refresh:
        raise FileExistsError(path)
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as stream:
        for file in sorted(directory.rglob('*')):
            if file.is_file():
                stream.write(file,file.relative_to(directory.parent))
    return path


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirmation',type=Path,required=True)
    parser.add_argument('--replay',type=Path,required=True)
    parser.add_argument('--refresh-produced-artifacts',action='store_true',help='Refresh only this script\'s fixed required-target deliverable names; earlier survey versions are untouched.')
    args=parser.parse_args()
    overleaf=ROOT/'OrbInspect_Overleaf_required_targets_20260905'
    supplement=ROOT/'output/supplementary/OrbInspect_required_target_package_20260905'
    final=ROOT/'output/pdf/OrbInspect_IEEE_TAES_required_targets_20260905.pdf'
    refresh=args.refresh_produced_artifacts
    if (overleaf.exists() or supplement.exists() or final.exists()) and not refresh:
        raise FileExistsError('New revision destination already exists; use a new version name.')
    copy(PAPER/'main.pdf',final)
    overleaf.mkdir(exist_ok=refresh)
    inputs={PAPER/'main.tex',PAPER/'references.bib',PAPER/'IEEEtaes.cls',PAPER/'Makefile'}
    for line in (PAPER/'main.fls').read_text().splitlines():
        if line.startswith('INPUT '):
            candidate=Path(line[6:])
            candidate=(candidate if candidate.is_absolute() else PAPER/candidate).resolve()
            if candidate.is_relative_to(PAPER) and candidate.is_file() and candidate.suffix in {'.tex','.pdf','.png','.jpg','.cls','.bst','.bbl'} and candidate!=PAPER/'main.pdf':
                inputs.add(candidate)
    for source in inputs:
        copy(source,overleaf/source.relative_to(PAPER))
    copy(final,overleaf/'paper.pdf')
    (overleaf/'README.md').write_text('# Required-target IEEE TAES revision\n\nUpload this folder to Overleaf and select main.tex as the main document. Compile with pdfLaTeX and BibTeX (latexmk locally). The included paper.pdf is the verified reference build.\n\nADP is the main contribution. Figures retain the established style and panel layouts. The ROS camera example is historical, not a new required-target execution. Publication DOI and code/data licensing remain author decisions.\n')
    supplement.mkdir(parents=True,exist_ok=refresh)
    shutil.copytree(overleaf,supplement/'OrbInspectLatex',dirs_exist_ok=refresh)
    shutil.copytree(ROOT/'src',supplement/'src',dirs_exist_ok=refresh,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.glb','*.gltf','.DS_Store'))
    shutil.copytree(PAPER/'scripts',supplement/'OrbInspectLatex/scripts',dirs_exist_ok=refresh,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    development=ROOT/'data/results/20260905_093000_required_target_adp'
    for bundle in (development,args.confirmation.resolve(),args.replay.resolve()):
        shutil.copytree(bundle,supplement/bundle.relative_to(ROOT),dirs_exist_ok=refresh,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # Preserve the actual historical ROS evidence without implying a fresh run.
    historical=ROOT/'data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812'
    for relative in ('summary.json','summary.md','mesh_execution_audit.json','raw','config_snapshot'):
        source=historical/relative
        target=supplement/historical.relative_to(ROOT)/relative
        if source.is_dir():
            shutil.copytree(source,target,dirs_exist_ok=refresh,ignore=shutil.ignore_patterns('*.mp4','*.mov'))
        elif source.is_file():
            copy(source,target)
    # The original graph's model configuration and provenance support reconstruction.
    original=ROOT/'data/results/adp_future_full_transform_radius080_20260812'
    for relative in ('summary.json','summary.md','raw/hcw_graph.json'):
        copy(original/relative,supplement/original.relative_to(ROOT)/relative)
    for note in ('ieee_required_target_revision_plan_20260905.md','required_target_reproducibility_notes_20260905.md',
                 'required_target_execution_validation_20260905.md','required_target_revision_summary_20260905.md',
                 'required_target_evidence_audit_20260905.md'):
        source=ROOT/'docs'/note
        if source.exists():
            copy(source,supplement/'docs'/note)
    copy(ROOT/'pytest.ini',supplement/'pytest.ini')
    copy(ROOT/'AGENTS.md',supplement/'project/AGENTS.md')
    for name in ('README.md','EVIDENCE_CORRECTIONS.json'):
        copy(ROOT/'output/supplementary/OrbInspect_reproducibility_package_20260905'/name,supplement/'historical_documentation'/name)
    content=f'''# Required-target rollout ADP — IEEE TAES revision

The primary evidence is `{args.confirmation.name}`, a fresh nine-target confirmation after the first geometry-prescribed campaign exposed failed greedy initialization. Required IDs and ADP3 are unchanged. Local search now starts from one-step ADP; it is not an independent non-ADP baseline. Every scenario remains in success and penalty denominators.

## Evidence map

- `data/results/{args.confirmation.name}/`: frozen protocol, graph, scenarios, all method rows, depth validation, primary tables/statistics, figure source and representative repropagation.
- `data/results/{development.name}/`: first campaign, preserved as development and descriptive six/nine/twelve-target sensitivity evidence.
- `data/results/{args.replay.name}/`: planned replay export and exact target-identity metadata; **not an executed ROS experiment**.
- `OrbInspectLatex/`: buildable paper, current vector figure inputs and generation scripts.
- `src/`: current implementation and tests. NASA geometry is excluded; obtain the original public asset with the source and checksum in the historical documentation before regenerating mesh/trajectory figures. Archived graph evaluation does not require reconstructing geometry.
- `docs/`: change log, evidence and execution-accounting checks, limitations, and data dictionaries.
- `historical_documentation/`: earlier survey package notes, explicitly not current primary results.

## Reproduce without altering the archived evidence

Use the recorded environment for exact timing comparability; the evaluated local runtime is Python 3.14 on macOS, whereas the intended ROS deployment remains Ubuntu 24.04/ROS 2 Jazzy/Python 3.12. Timing is not an onboard benchmark. Install NumPy, SciPy, Matplotlib, PyYAML and pytest for offline analysis. Copy the confirmation folder to a separate rerun folder before running validation/evaluation commands; frozen source/input hashes are checked automatically.

```bash
export PYTHONPATH="$PWD/src/orbinspect_guidance:$PWD/src/orbinspect_dynamics:$PWD/src/orbinspect_perception:$PWD/src/orbinspect_safety"
python OrbInspectLatex/scripts/run_required_target_confirmation.py validation --output data/results/confirmation_rerun
python OrbInspectLatex/scripts/run_required_target_confirmation.py evaluation --output data/results/confirmation_rerun
python OrbInspectLatex/scripts/write_required_target_tables.py --study data/results/{args.confirmation.name} --development-study data/results/{development.name}
python OrbInspectLatex/scripts/generate_required_target_figures.py --study data/results/{args.confirmation.name}
python OrbInspectLatex/scripts/generate_required_target_details.py --study data/results/{args.confirmation.name}
```

The final command needs the original NASA asset. Existing raw trajectories and vector figures are included for inspection without it. Do not interpret the fixed 500-unit failure penalties as maneuver costs, weighted background score as physical mesh area, or repeated seeds/routes as independent geometries.

## Access and rights

This is a local submission package, not a public repository deposit. No DOI, accession or new license has been assigned. The authors must confirm repository, persistent identifier, and code/data license before publication. Third-party NASA assets are not relicensed or redistributed. Historical media remain in the separately preserved earlier package; their current PDF figure and source execution logs are included here.

## Integrity

Run `shasum -a 256 -c SHA256SUMS.txt` from this directory. Hashes cover every packaged file other than the checksum listing itself.
'''
    (supplement/'README.md').write_text(content)
    for directory in (overleaf,supplement):
        lines=[f'{checksum(p)}  {p.relative_to(directory).as_posix()}' for p in sorted(directory.rglob('*')) if p.is_file() and p!=directory/'SHA256SUMS.txt']
        (directory/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n')
        if directory==overleaf:
            copy(directory/'SHA256SUMS.txt',supplement/'OrbInspectLatex/SHA256SUMS.txt')
    results={'pdf':str(final),'pdf_sha256':checksum(final),'overleaf_zip':str(archive(overleaf,refresh)),
             'supplement_zip':str(archive(supplement,refresh))}
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    main()
