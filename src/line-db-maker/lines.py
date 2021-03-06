#! /usr/bin/env/python3

"""
stations.py reads in an xml file containing a list
of station elements with name and url subelements.
It fetches those urls and tries to extract the lines
serving those stations from the websites. It updates
the xml and saves the updated list into a (potentially)
new file.

usage: $ python stations.py xml-file-name output-name

"""

import xml.etree.cElementTree as ET
import urllib.request
import re
from urllib.error import HTTPError


class Station:

    LINES_RE = re.compile("<p>This station is served by:<br ?/?>"
                          "(.+?)</p>", re.DOTALL)
    BREAK_RE = re.compile("<br ?/?>")
    PARKING_RE = re.compile('<table[^>]*>\s*<tr>\s*<td[^>]*>'
                            '<h2 class="normal">Parking</h2>'
                            '.*</table>', re.DOTALL)

    def __init__(self, element):
        self.element = element
        assert (self.element.find('url') is not None)
        self._html = ''
        self._lines = []
        self._parking = []

    @property
    def url(self):
        return self.element.find('url').text

    @property
    def html(self):
        if not self._html:
            self.update_html(self.url)
        return self._html

    def update_html(self, url):
        # UTF-8 encoded checked by hand on a couple of urls
        try:
            self._html = urllib.request.urlopen(url).read().decode('utf8')
        except HTTPError as e:
            self._html = "HTTP Error #" + str(e.code)

    @property
    def lines(self):
        if not self._lines:
            self.update_lines()
        return self._lines

    def update_lines(self):
        section = self.LINES_RE.search(self.html)
        try:
            section = section.group(1)
        except AttributeError:  # No match found
            self._lines = ["REGEX ERROR"]
            return
        section = section.strip()
        section = self.BREAK_RE.sub("\n", section)
        # subbing <br>s may result in double newlines, and hence blank "entries"
        # That's why composition below is filtered
        self._lines = [s.strip() for s in section.splitlines() if s.strip()]

    def set_lines(self):
        lines = self.element.find('lines')
        if lines is None:
            lines = ET.SubElement(self.element, 'lines')
        for line in self.lines:
            el = ET.SubElement(lines, 'line')
            el.text = line

    @property
    def parking(self):
        if not self._parking:
            self.update_parking()
        return self._parking

    def update_parking(self):
        section = self.PARKING_RE.search(self.html)
        try:
            section = section.group(0)
        except AttributeError:  # No match found
            self._parking = [("REGEX ERROR", 0, 0)]
            print("Regex error at " + self.url)
            return
        section = lowercase_tags(section).replace('&nbsp;', '')
        try:
            table = ET.fromstring(section)
        except ET.ParseError:
            try:
                # The first row does not appear to be closed properly
                # i.e., the terminal "</tr>" appears as "<tr>" instead
                section = section.replace("<tr>", "</tr>", 2)
                section = section.replace("</tr>", "<tr>", 1)
                table = ET.fromstring(section)
            except ET.ParseError as e:
                self._parking = [("MALFORMED HTML", 0, 0)]
                print("Malformed HTML at " + self.url)
                print(section)
                print(e)
                return
        rows = list(table)[1:]  # :FIXME:
        self._parking = []
        for row in rows:
            if len(row) == 1:
                # There is no parking. HTML should look like
                # <tr><td colspan="4">There is no parking available at this
                # station.</td></tr> with some whitespace thrown in.
                if (row.find('td').text !=
                        "There is no parking available at this station."):
                    raise RuntimeError()
                self._parking = [('N/A', 0, 0)]
            else:
                assert len(row) == 4
                # Entries are: SEPTA, Spaces, Availability, Price
                entries = row.findall('td')
                del entries[2]
                def get_text(e):
                    t = e.text
                    try:
                        return t.strip()
                    except AttributeError:
                        return ''
                self._parking.append(tuple(get_text(td) for td in entries))

    def set_parking(self):
        pt = self.element.find('parking-lots')
        if pt is None:
            pt = ET.SubElement(self.element, 'parking-lots')
        for kind, size, price in self.parking:
            lot = ET.SubElement(pt, 'parking')
            t = ET.SubElement(lot, 'type')
            t.text = kind
            s = ET.SubElement(lot, 'size')
            s.text = size
            p = ET.SubElement(lot, 'price')
            p.text = price or "0"  # Parser ignores zeros, apparently


HTML_TAG = re.compile(r"</?([:_A-Za-z][:_A-Za-z\-]*) ?[^>]*>")
def lowercase_tags(html):
    """Converts all tag names in a block of html to lowercase."""
    def lowerize(match):
        full = match.group(0)
        name = match.group(1)
        return full.replace(name, name.lower())
    return HTML_TAG.sub(lowerize, html)


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
        print(__doc__)
        sys.exit(1)

    tree = ET.parse(xmlfilename)
    stations = [Station(e) for e in tree.iter(tag='station')]
    for station in stations:
        station.set_lines()
#        station.set_parking()
    tree.write(outname)
