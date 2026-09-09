#!/usr/bin/env python3
"""Package the verified IEEE revision without overwriting earlier deliverables."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
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
    parser.add_argument('--depth-study',type=Path,help='Optional versioned post-selection depth diagnostic.')
    parser.add_argument('--revision-tag',default='20260905',help='Safe filename suffix for a new deliverable version.')
    parser.add_argument('--refresh-produced-artifacts',action='store_true',help='Refresh only this script\'s fixed required-target deliverable names; earlier survey versions are untouched.')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',args.revision_tag):
        raise ValueError('Revision tag must be a simple filename suffix.')
    overleaf=ROOT/f'OrbInspect_Overleaf_required_targets_{args.revision_tag}'
    supplement=ROOT/f'output/supplementary/OrbInspect_required_target_package_{args.revision_tag}'
    final=ROOT/f'output/pdf/OrbInspect_IEEE_TAES_required_targets_{args.revision_tag}.pdf'
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
    editable_figures = [source.with_suffix('.drawio') for source in inputs
                        if source.suffix == '.pdf' and source.with_suffix('.drawio').is_file()]
    for source in editable_figures:
        inputs.add(source)
        if source.with_suffix('.svg').is_file():
            inputs.add(source.with_suffix('.svg'))
        asset_folder = source.parent / 'framework_assets'
        if source.stem == 'orbinspect_framework' and asset_folder.is_dir():
            inputs.update(p for p in asset_folder.iterdir()
                          if p.is_file() and p.suffix in {'.jpg', '.png', '.md', '.json'})
    for source in inputs:
        copy(source,overleaf/source.relative_to(PAPER))
    copy(final,overleaf/'paper.pdf')
    figure_note = ('Figure 1 combines native editable draw.io shapes in a pastel-stage style '
                   'with two independently embedded photographs; image credits and original '
                   'assets are included in figures/required_target/framework_assets/. '
                   'Its .drawio and matching .svg files accompany the mixed-media PDF. '
                   'All remaining figures retain their established style and panel layouts.'
                   if editable_figures else 'Figures retain the established style and panel layouts.')
    (overleaf/'README.md').write_text('# Required-target IEEE TAES revision\n\nUpload this folder to Overleaf and select main.tex as the main document. Compile with pdfLaTeX and BibTeX (latexmk locally). The included paper.pdf is the verified reference build.\n\nADP is the main contribution. '+figure_note+' Every figure has an explicit body-text reference. The ROS camera example is historical, not a new required-target execution. Publication DOI and code/data licensing remain author decisions.\n')
    supplement.mkdir(parents=True,exist_ok=refresh)
    shutil.copytree(overleaf,supplement/'OrbInspectLatex',dirs_exist_ok=refresh)
    shutil.copytree(ROOT/'src',supplement/'src',dirs_exist_ok=refresh,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.glb','*.gltf','.DS_Store'))
    shutil.copytree(PAPER/'scripts',supplement/'OrbInspectLatex/scripts',dirs_exist_ok=refresh,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    development=ROOT/'data/results/20260905_093000_required_target_adp'
    for bundle in (development,args.confirmation.resolve(),args.replay.resolve()):
        shutil.copytree(bundle,supplement/bundle.relative_to(ROOT),dirs_exist_ok=refresh,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    if args.depth_study:
        bundle=args.depth_study.resolve()
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
                 'required_target_evidence_audit_20260905.md','required_target_depth_audit_20260905.md',
                 'required_target_depth_revision_20260905.md','manuscript_cleanup_20260906.md',
                 'figure1_photographic_revision_20260906.md'):
        source=ROOT/'docs'/note
        if source.exists():
            copy(source,supplement/'docs'/note)
    copy(ROOT/'pytest.ini',supplement/'pytest.ini')
    if args.depth_study:
        copy(ROOT/'test/test_required_target_depth_summary.py',supplement/'test/test_required_target_depth_summary.py')
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

This is a local submission package, not a public repository deposit. No DOI, accession or new code/data license has been assigned. The authors must confirm repository, persistent identifier, and code/data license before publication. The NASA geometry asset is not redistributed. Figure 1 photographs are included unchanged with their original credits and rights documented in `OrbInspectLatex/figures/required_target/framework_assets/IMAGE_CREDITS.md`; they are not relicensed. Historical media remain in the separately preserved earlier package; their current PDF figure and source execution logs are included here.

## Integrity

Run `shasum -a 256 -c SHA256SUMS.txt` from this directory. Hashes cover every packaged file other than the checksum listing itself.
'''
    if args.depth_study:
        content += f'''\n## Depth-one-to-six revision\n\n`data/results/{args.depth_study.name}/` contains the post-selection validation-only depths 1--6 diagnostic. This supersedes the older three-row depth table/plot, not the frozen primary test data. All six depths use the same 12 validation cases and are rerun in one sequential pass. See the depth revision and audit notes for the resulting cost/computation trade-off.\n\nAfter the general figure/table commands above, regenerate the current depth figure and table with:\n\n```bash\npython OrbInspectLatex/scripts/generate_required_target_depth_figures.py --depth-study data/results/{args.depth_study.name}\n```\n\nThe optional depth runner evaluates archived graph records without the NASA geometry asset. It freezes the diagnostic inputs before executing and supports resuming saved rows. No new test-depth sweep or ROS execution is included.\n'''
    if editable_figures:
        content += '''\n## Editable framework figure and prose cleanup\n\nFigure 1 is `OrbInspectLatex/figures/required_target/orbinspect_framework.drawio`. Open it in draw.io to edit its native shapes, labels, and connectors. Matching SVG and vector PDF exports are included. The paper uses the PDF across two columns; numerical plots are unchanged. See `docs/manuscript_cleanup_20260906.md` for the figure-reference audit and the boundaries retained during prose consolidation.\n\nTo rebuild the supplied diagram variants from their shared geometry, install PyMuPDF and run:\n\n```bash\npython OrbInspectLatex/scripts/generate_editable_framework.py\n```\n\nThis regenerates the supplied authored diagram; manual edits made subsequently in draw.io should instead be exported from draw.io and must not be overwritten by regeneration.\n'''
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
