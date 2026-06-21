#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y \
  latexmk \
  texlive-latex-recommended \
  texlive-latex-extra \
  texlive-publishers \
  texlive-science \
  texlive-fonts-recommended \
  texlive-bibtex-extra \
  biber \
  chktex

echo "TeX toolchain installed. Recommended VS Code extension: LaTeX Workshop."
