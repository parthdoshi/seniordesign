#! /usr/bin/env/python3

"""
stations.py reads in an xml file containing a list
of station elements with name and url subelements.
It fetches those urls and tries to extract the lines
serving those stations from the websites. It updates
the xml and saves the updated list into a (potentially)
new file.

usage: $ python stations.py xml-file-name [output-name]

"""

import xml.etree.cElementTree as ET
import urllib.request
import re

LINES_RE = re.compile("<p>This station is served by:<br />"
                      "([^<]+)</p>")
class Station:
    
    def __init__(self, element):
        self.element = element
        assert (self.element.find('url') is not None)

    @property
    def url(self):
        return self.element.find('url').text

    def set_lines(self):
        html = self.get_html(self.url)
        lines = self.get_lines(html)
        for line in lines:
            el = ET.SubElement(self.element, 'line')
            el.text = line

    def get_html(self, url):
        # UTF-8 encoded checked by hand on a couple of urls
        return urllib.request.urlopen(url).read().decode('utf8')

    @staticmethod
    def get_lines(html):
        try:
            section = LINES_RE.find(html).group(1)
        except AttributeError:
            # "None has no group attribute" -> no match found
            return ["FIXME"]
        section = section.strip().replace('<br />', '\n')
        return section.split()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 3:
        print(__doc__)
        sys.exit(1)
    try:
        xmlfilename = sys.argv[1]
    except IndexError:
        print(__doc__)
        sys.exit(1)
    try:
        outname = sys.argv[2]
    except IndexError:
        outname = xmlfilename
        
    tree = ET.parse(xmlfilename)
    stations = [Station(e) for e in tree.iter(tag='station')]
    for station in stations:
        station.set_lines()
    tree.write(outname)
