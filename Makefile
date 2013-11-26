recipe-book.pdf: *.tex */*.tex
	rm -f recipe-book.aux
	pdflatex -halt-on-error recipe-book.tex
	pdflatex recipe-book.tex
