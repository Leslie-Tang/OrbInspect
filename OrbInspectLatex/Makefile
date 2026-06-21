PDFLATEX ?= pdflatex
BIBTEX ?= bibtex

.PHONY: all clean

all: main.pdf

main.pdf: main.tex references.bib sections/*.tex algorithms/*.tex
	$(PDFLATEX) main.tex
	$(BIBTEX) main
	$(PDFLATEX) main.tex
	$(PDFLATEX) main.tex

clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.pdf *.toc
