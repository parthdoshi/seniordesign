#!/bin/sh
outfile=T13_Phase1_Report.pdf
if [ -f main.tex ]
then
    echo "Linking style file into directory"
    ln ../sd.sty .

    echo "Removing LaTeX Garbage"
    rm -f main.aux main.bbl main.bcf main.blg main.log main.run.xml main.toc
    rm $outfile

    echo "Recreating Document"
    pdflatex main.tex -interaction=nonstopmode
    biber main
    pdflatex main.tex -interaction=nonstopmode
    pdflatex main.tex -interaction=nonstopmode

    echo "Removing LaTeX Garbage"
    rm -f main.aux main.bbl main.bcf main.blg main.log main.run.xml main.toc
    echo "Seting proper name for.pdf"
    ln main.pdf $outfile
else
    echo "Change directories and try again"
fi

