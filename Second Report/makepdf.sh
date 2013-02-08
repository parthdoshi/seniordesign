#!/bin/sh

outfile=T13_Phase1_Report.pdf

texcommand()
{
    pdflatex main.tex -interaction=batchmode | \
	grep -v "/usr/share/" | grep -v "This is pdfTeX" | \
	grep -v "write18" | grep -v "entering extended" | \
	grep -v "LaTeX2e" | grep -v "Document Class:" | \
	grep -v "*geometry*" | grep -v "Babel" | grep -v "MPS to PDF" | \
	sed -r 's/<[^<]*>//g' | sed -r 's/\[ ?[0-9][0-9]* ?\]//g' | \
	sed '/^ *$/d'
}

if [ -f main.tex ]
then
  echo "Linking style file into directory"
  ln ../sd.sty .

  echo "Removing LaTeX Garbage"
  rm -f main.aux main.bbl main.bcf main.blg main.log main.run.xml main.toc
  rm $outfile

  echo "LaTeX 1st Pass"
  texcommand > /dev/null

  if [ $? -eq 0 ]; then
      echo "Biber Pass"
      biber -q main
  else exit; fi
  if [ $? -eq 0 ]; then
      echo "LaTeX 2nd Pass"
      texcommand > /dev/null
  else exit; fi
  if [ $? -eq 0 ]; then
      echo "LaTeX 3rd Pass"
      texcommand
  else exit; fi

  echo "Removing LaTeX Garbage"
  rm -f main.aux main.bbl main.bcf main.blg main.log main.run.xml main.toc
  echo "Linking pdf to" "$outfile"
  ln main.pdf $outfile
else
  echo "main.tex not found!"
fi

exit