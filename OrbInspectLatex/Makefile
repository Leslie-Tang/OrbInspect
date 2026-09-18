LATEXMK ?= latexmk
PYTHON ?= python3

.PHONY: all main supplement check package clean

all: main supplement

main:
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex

supplement:
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -file-line-error supplement.tex

check:
	$(PYTHON) scripts/check_project.py

package: all check
	$(PYTHON) scripts/package_source.py

# Remove only latexmk-managed intermediate files; keep the PDF and source.
clean:
	$(LATEXMK) -c main.tex
	$(LATEXMK) -c supplement.tex
