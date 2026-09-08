# Unified palette for Figures 3--6

This is a color-only revision. The manuscript text, evidence, numerical
statistics, labels, axes, line styles, hatches, panel sizes and LaTeX subfigure
assembly are unchanged. Figures 1, 2 and 7 are unchanged.

## Visual mapping

| Role | Color |
|---|---|
| Proposed ADP curves; test-cohort points/bars | Teal `#3F91A6` |
| Seeded local search; shifted-cohort points/bars | Muted purple `#8771AA` |
| One-step comparison in the effort panel | Pale purple `#B6A5CE` |
| Frozen depth-three square | Dark slate `#303E44` |
| Confidence bands | Pale teal `#B7D7DE`, at unchanged opacity |
| Required samples and input limit | Orange `#E97900` |
| Initial-state star | Green `#27A27F` |
| Zero-clearance boundary | Red `#C30000` |
| Reference lines and secondary annotations | Gray `#647687` |
| Station background mesh | Light gray `#DDDDDD` |

Colors identify methods where the panel compares methods, and cohorts where
the existing legend identifies test versus shifted cases. Marker shapes and
hatching retain those distinctions without reliance on color. The confidence
fill uses a slightly stronger teal tint than the framework's large background
panel so the statistical interval remains visible at final size.

## Reproduction and integrity

- `scripts/figure_palette.py` is the palette definition.
- `scripts/generate_result_figures.py` regenerates the current independent
  Figure 4/5 panels and legend from the included frozen comparison data.
- `scripts/recolor_result_figures.py` stages the complete Figure 3--6 revision.
  It changes only RGB paint in the finalized Figure 3/6 vector files, retaining
  their original paths, typography and camera projection. It does not rerun
  the dynamics, route selection or experiments.
- The verification compares every SVG after excluding color and generated
  identifiers, checks PDF text and page boxes, and preserves PNG dimensions.
  For the recolored Figure 3/6 PDFs, all non-color drawing instructions also
  remain identical. PDF box serialization is compared to 0.00001 point.
- Figure 4/5 evidence objects match the previous manifests exactly. All 86
  protected manuscript, evidence and unchanged-figure files retain their hashes.
- The machine-readable checks are in `FIGURE_PALETTE_QA_20260908.json`.

Run the optional staging workflow from the manuscript directory using a Python
environment containing matplotlib, NumPy, pypdf, PyMuPDF and Pillow:

```sh
python scripts/recolor_result_figures.py
```

Inspect the staged exports before promoting them. The initial approved
promotion preserves the old figure directories in
`archive/figure36_prepalette_20260908/` and updates the active integrity manifest.
It refuses to overwrite that archive. Future revisions should use a new
archive destination. The older per-study manifests remain evidence provenance
records; this revision's palette and geometry checks are recorded separately.

The source package includes the optional scripts but compiling the manuscript
still requires only the documented LaTeX dependencies.
