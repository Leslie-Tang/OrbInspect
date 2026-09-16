# Single local manuscript source

The editable manuscript is now entirely in `main.tex`: both former section
files and all nine table/numerical files are included as literal source blocks.
Comments mark each former file boundary. No manuscript `\input` or `\include`
commands remain. The bibliography stays in `references.bib`; the journal class,
bibliography style and original figure PDFs remain external supporting assets.

The original `main.tex`, `sections/`, `tables/` and compiled manuscript are
preserved in `archive/modular_tex_20260914/`. Its `source_manifest.json` records
the SHA-256 hashes of all twelve original TeX files. Historical documentation
that names the former section/table paths refers to this archived organization.

The manuscript's wording, data, commands, figure paths and Figure 8 LaTeX
subfigures are preserved. The source-package command now includes one manuscript
TeX file, and `make check` enforces this single-file compilation structure.
Future regenerated table values must be copied to the corresponding marked
blocks in `main.tex`.

Validation is recorded in `SINGLE_TEX_QA_20260914.json`. The local PDF remains
13 pages, with no pixel differences from the pre-consolidation manuscript at
100 dpi. No Overleaf edits, ROS runs, figure regeneration or Git push were
performed for this change.
