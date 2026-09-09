# Required-target rollout ADP — IEEE TAES revision

The primary evidence is `20260905_101500_required_target_confirmation`, a fresh nine-target confirmation after the first geometry-prescribed campaign exposed failed greedy initialization. Required IDs and ADP3 are unchanged. Local search now starts from one-step ADP; it is not an independent non-ADP baseline. Every scenario remains in success and penalty denominators.

## Evidence map

- `data/results/20260905_101500_required_target_confirmation/`: frozen protocol, graph, scenarios, all method rows, depth validation, primary tables/statistics, figure source and representative repropagation.
- `data/results/20260905_093000_required_target_adp/`: first campaign, preserved as development and descriptive six/nine/twelve-target sensitivity evidence.
- `data/results/20260905_111500_required_target_confirmation_replay/`: planned replay export and exact target-identity metadata; **not an executed ROS experiment**.
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
python OrbInspectLatex/scripts/write_required_target_tables.py --study data/results/20260905_101500_required_target_confirmation --development-study data/results/20260905_093000_required_target_adp
python OrbInspectLatex/scripts/generate_required_target_figures.py --study data/results/20260905_101500_required_target_confirmation
python OrbInspectLatex/scripts/generate_required_target_details.py --study data/results/20260905_101500_required_target_confirmation
```

The final command needs the original NASA asset. Existing raw trajectories and vector figures are included for inspection without it. Do not interpret the fixed 500-unit failure penalties as maneuver costs, weighted background score as physical mesh area, or repeated seeds/routes as independent geometries.

## Access and rights

This is a local submission package, not a public repository deposit. No DOI, accession or new code/data license has been assigned. The authors must confirm repository, persistent identifier, and code/data license before publication. The NASA geometry asset is not redistributed. Figure 1 photographs are included unchanged with their original credits and rights documented in `OrbInspectLatex/figures/required_target/framework_assets/IMAGE_CREDITS.md`; they are not relicensed. Historical media remain in the separately preserved earlier package; their current PDF figure and source execution logs are included here.

## Integrity

Run `shasum -a 256 -c SHA256SUMS.txt` from this directory. Hashes cover every packaged file other than the checksum listing itself.

## Depth-one-to-six revision

`data/results/20260905_100500_required_target_depth_diagnostic/` contains the post-selection validation-only depths 1--6 diagnostic. This supersedes the older three-row depth table/plot, not the frozen primary test data. All six depths use the same 12 validation cases and are rerun in one sequential pass. See the depth revision and audit notes for the resulting cost/computation trade-off.

After the general figure/table commands above, regenerate the current depth figure and table with:

```bash
python OrbInspectLatex/scripts/generate_required_target_depth_figures.py --depth-study data/results/20260905_100500_required_target_depth_diagnostic
```

The optional depth runner evaluates archived graph records without the NASA geometry asset. It freezes the diagnostic inputs before executing and supports resuming saved rows. No new test-depth sweep or ROS execution is included.

## Editable framework figure and prose cleanup

Figure 1 is `OrbInspectLatex/figures/required_target/orbinspect_framework.drawio`. Open it in draw.io to edit its native shapes, labels, record tables, trajectory curve, and connectors. Matching SVG and mixed-media PDF exports are included. The paper uses the PDF across two columns; Figures 2–7 and the numerical results are unchanged. See `docs/figure1_technical_revision_20260906.md` for the logic audit, and `docs/manuscript_cleanup_20260906.md` for the earlier figure-reference audit and prose consolidation.

The transfer trace and directed/node records are extracted from frozen archives, not invented schematics or new performance evidence. `figures/required_target/framework_assets/TECHNICAL_EXAMPLES.json` records the exact source hashes, abbreviated IDs, and plotted samples. The ISS and camera photographs remain independently replaceable, unchanged image objects with their original credits.

To rebuild the supplied diagram variants from their shared geometry, install PyMuPDF and run:

```bash
python OrbInspectLatex/scripts/generate_editable_framework.py
```

This regenerates the supplied authored diagram; manual edits made subsequently in draw.io should instead be exported from draw.io and must not be overwritten by regeneration.
