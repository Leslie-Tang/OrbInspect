# OrbInspect AST Paper Draft

This folder contains an Elsevier/Aerospace Science and Technology-style LaTeX
manuscript draft for OrbInspect.

The draft is intentionally written before claiming a full Gazebo inspection
result. It formalizes the inspection planning problem, assumptions, constraints,
mission setting, and an offline trajectory generation algorithm that should be
implemented and evaluated before using Gazebo videos as evidence.

## Build

The source uses the Elsevier `elsarticle` class, which is the standard template
family used for Aerospace Science and Technology submissions.

```bash
cd OrbInspectLatex
latexmk -pdf main.tex
```

If `latexmk` is unavailable:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

This workspace currently does not include a TeX distribution, so compilation
may require installing TeX Live and the Elsevier template package.

## Structure

- `main.tex`: manuscript entry point.
- `sections/`: paper sections.
- `references.bib`: initial bibliography placeholders.
- `figures/`: generated paper figures should be placed here.
- `tables/`: generated tables should be placed here.
- `algorithms/`: algorithm pseudocode snippets.

