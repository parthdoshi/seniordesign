#! /usr/bin/env/python3

"""
map.py accesses the SEPTA website and outputs
an xml file containing in an xml file containing a list
of station elements with name and url subelements.

The output file is called "results.xml"

usage: $ python map.py

"""

import xml.etree.ElementTree as ET
import urllib.request
import re
import sys
from xml.etree.ElementTree import ElementTree

def get_HTML():
	url = "http://www.septa.org/maps/system/index.html"
	# UTF-8 encoded checked by hand on a couple of urls
	return urllib.request.urlopen(url).read().decode('utf8')

def get_element(text):
	stationlist = []

	for line in text:
		if re.match("(.*)coords(.*)", line):
			try:
				idxCoord = line.index("coords")
				firstCoord = line.index("\"", idxCoord) + 1
				secondCoord = line.index("\"", firstCoord)
				foundCoord = line[firstCoord:secondCoord]

				idxHref = line.index("href")
				firstHref = line.index("\"", idxHref) + 1
				secondHref = line.index("\"", firstHref)
				foundHref = line[firstHref:secondHref]

				idxAlt = line.index("alt")
				firstAlt = line.index("\"", idxAlt) + 1
				secondAlt = line.index("\"", firstAlt)
				foundAlt = line[firstAlt:secondAlt]
				
				station = ET.Element('station')
				name	= ET.SubElement(station, 'name')
				coord	= ET.SubElement(station, 'coordinates')
				url		= ET.SubElement(station, 'url')

				name.text = foundAlt
				coord.text = foundCoord
				url.text = "http://www.septa.org/" + foundHref[12:]
				stationlist.append(station)

			except ValueError:
				print("Could not parse " + line)

	return stationlist

if __name__ == "__main__":
	outfile = "results.xml"

	# delete outfile if it exists
	import os
	if (os.path.exists(outfile)):
		os.unlink(outfile)

	if len(sys.argv) > 1:
		print(__doc__)
		sys.exit(1)

	text = get_HTML()
	children = get_element(text.split("\n"))

	tree = ElementTree()
	root = ET.Element('septa-stations')

	tree._setroot(root)

	for child in children:
		root.append(child)

	tree.write(outfile)
