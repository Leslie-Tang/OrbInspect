LATEXMK ?= latexmk
PYTHON ?= python3

.PHONY: all check package clean

all:
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex

check:
	$(PYTHON) scripts/check_project.py

package: all check
	$(PYTHON) scripts/package_source.py

# Remove only latexmk-managed intermediate files; keep the PDF and source.
clean:
	$(LATEXMK) -c main.tex
