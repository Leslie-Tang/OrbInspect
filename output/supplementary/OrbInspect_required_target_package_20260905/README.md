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

This is a local submission package, not a public repository deposit. No DOI, accession or new license has been assigned. The authors must confirm repository, persistent identifier, and code/data license before publication. Third-party NASA assets are not relicensed or redistributed. Historical media remain in the separately preserved earlier package; their current PDF figure and source execution logs are included here.

## Integrity

Run `shasum -a 256 -c SHA256SUMS.txt` from this directory. Hashes cover every packaged file other than the checksum listing itself.
