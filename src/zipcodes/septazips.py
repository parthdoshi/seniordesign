#! python

import numpy
import sqlite3
import Tkinter
import time
import urllib2
import json

from matplotlib import nxutils

LINK_DB = "../septa/final.db"
ZIPCODES = 'zipcode-polys.txt'

def main():
    #matcher = GoogleMatcher()
    matcher = make_matcher(ZIPCODES)
    print "Made matcher"
    #import pdb; pdb.set_trace()
    matcher.visualize(5000, 5000)
    set_station_zips(matcher)

def make_matcher(zipcodefile):
    """Makes a matcher object from a zipcode file."""
    matcher = Matcher()
    matcher.load(zipcodefile)
    for zipcode in matcher.containers.keys():
        if int(zipcode) > 19154 or int(zipcode) < 19100:
            matcher.remove_container(zipcode)
    return matcher

class GoogleMatcher(object):

    def get_match(self, latitude, longitude):
        """Get the zipcode of a (latitude, longitude) pair using Google Maps."""
        base = ("http://maps.googleapis.com/maps/api/geocode/json?"
                "latlng=%s,%s&sensor=false")
        final_url = base % (latitude, longitude)
        url = urllib2.urlopen(final_url)
        resp = json.loads(url.read())
        try:
            comps = resp['results'][0]['address_components']
        except KeyError:
            if resp['status'] == 'ZERO_RESULTS':
                raise ValueError('ZERO_RESULTS for (%s,%s)' % (latitude,
                                                               longitude))
            elif resp['status'] == 'NOT_FOUND':
                raise ValueError('(%s,%s) NOT_FOUND' % (latitude,
                                                        longitude))
            else:
                print resp
                raise
        except IndexError:
            if resp['status'] == 'OVER_QUERY_LIMIT':
                print "Sleeping"
                time.sleep(1)
                return self.get_match(latitude, longitude)
        except Exception:
            print resp
            raise
        for comp in comps:
            if 'postal_code' in comp['types']:
                return comp['short_name'].encode('utf-8')

def set_station_zips(matcher):
    """
    Set the zipcodes in the septa stop db.
    """
    connection = sqlite3.connect(LINK_DB,
                                 detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    cursor.execute('SELECT stop_id, stop_lat, stop_lon '
                   'FROM stops '
                   "WHERE TYPEOF(zipcode)='null' OR zipcode=''")
    stops = cursor.fetchall()
    print "Loaded %d stops from the database" % len(stops)
    i = 0
    for id_, lat, lon in stops:
        try:
            zipcode = matcher.get_match(lat, lon)
        except Exception:
            if i:
                connection.commit()
                print "Committed %d transactions" % i
            raise
        cursor.execute('UPDATE stops '
                       'SET zipcode=? '
                       'WHERE stop_id=? ',
                       (zipcode, id_,))
        i = (i + 1) % 100
        if not i:
            connection.commit()
            print "Commited 100 transactions"
    if i:
        connection.commit()
        print "Committed %d transactions" % i


class Matcher(object):

    """
    Creates an object to match points to their containing region.

    :param containers: a mapping of ids to containers.

    In this representation a container is a sequence of shapes, and a shape
    is a sequence of polygons. The interior of a shape is defined as the
    interior of the first polygon minus the interior of the remaining
    polygons. The interior of a container is defined as the union of the
    interiors of its shapes.
    """

    def __init__(self, containers=None):
        if containers is None:
            self.containers = {}
        else:
            self.containers = {id_:set(container)
                               for id_, container in containers.items()}
        self.vertex_in = {}
        self.bake_verteces()

    def remove_container(self, container_id):
        """Remove a container from the matcher object."""
        del self.containers[container_id]
        for s in self.vertex_in.values():
            s.discard(container_id)

    def bake_verteces(self):
        """Populate the vertex_in dictionary."""
        self.vertex_in = {}
        for id_, container in self.containers.items():
            for shape in container:
                for poly in shape:
                    for x, y in poly:
                        try:
                            self.vertex_in[(x, y)].add(id_)
                        except KeyError:
                            self.vertex_in[(x, y)] = set([id_])

    def get_match(self, x, y):
        """Return the id of the containing shape."""
        nodes = self.get_node_distances(x, y)
        checked = set()
        for node in nodes:
            for container in self.vertex_in[node].difference(checked):
                if self.contains(self.containers[container], (x, y)):
                    return container
                checked.add(container)
        raise ValueError("(%f,%f) is not in the universe." % (x, y))

    def contains(self, container, pt):
        """Check whether a container contains pt."""
        for shape in container:
            if self.shape_contains(shape, pt):
                return True
        return False

    def shape_contains(self, shape, pt):
        """Check whether a shape contains pt."""
        base = shape[0]
        holes = shape[1:]
        if self.poly_contains(base, pt):
            for hole in holes:
                if self.poly_contains(hole, pt):
                    return False
            return True
        return False

    def poly_contains(self, poly, pt):
        """Check whether a polynomial contains pt."""
        poly = numpy.array(poly, float)
        nxutils.pnpoly(pt[0], pt[1], poly)

    def get_nearest_node(self, x, y):
        """Return the nearest node to (x, y) belonging to a polygon."""
        return self.get_node_distances(x ,y)[0]

    def get_node_distances(self, x, y):
        """Get a list of nodes sorted by their distance to (x, y)."""
        nodes = self.vertex_in.keys()
        nodes.sort(key=lambda n: self.get_length((x, y), n))
        return nodes

    def load(self, filename):
        """Load the zipcode file into the object."""
        self.containers = {}
        with open(filename) as f:
            for line in f:
                id_, container = line.split(":")
                id_ = id_
                container = eval(container)
                container = set(map(tuple, container))
                self.containers[id_] = container
        self.bake_verteces()

    @staticmethod
    def get_length(n1, n2):
        """Get the length of a segment."""
        x1, y1 = n1
        x2, y2 = n2
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** .5

    def visualize(self, width, height):
        """Display the regions on a Tkinter Canvas."""
        root = Tkinter.Tk()
        frame = Tkinter.Frame(root)
        frame.pack(fill='both', expand=True)
        vscroll = Tkinter.Scrollbar(frame)
        vscroll.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)
        hscroll = Tkinter.Scrollbar(frame)
        hscroll.pack(side=Tkinter.BOTTOM, fill=Tkinter.X)
        canvas = Tkinter.Canvas(frame,
                                bg="white",
                                bd=2,
                                scrollregion=(0, 0, width,height),
                                yscrollcommand=vscroll.set,
                                xscrollcommand=hscroll.set)
        canvas.pack(fill='both', expand=True)
        vscroll.config(command=canvas.yview)
        hscroll.config(command=canvas.xview,
                            orient=Tkinter.HORIZONTAL)
        nodes = self.vertex_in.keys()
        if not nodes:
            raise KeyError()
        min_x = min(nodes)[0]
        max_x = max(nodes)[0]
        max_y = max(zip(*nodes)[1])
        min_y = min(zip(*nodes)[1])
        scale = min(width / (max_x - min_x), height / (max_y - min_y))
#        for node in nodes:
#            x, y = node
#            x = (x - min_x) * scale
#            y = height - (y - min_y) * scale
#            canvas.create_arc([x-5, y-5, x+5, y+5], fill='black')
        for container in self.containers.values():
            for shape in container:
                self.draw_shape(shape, canvas, scale, height, (min_x, min_y))
        root.mainloop()

    @staticmethod
    def draw_shape(shape, canvas, scale, height, origin):
        """Draw a shape on the canvas."""
        poly = []
        for x, y in shape[0]:
            x = (x - origin[0]) * scale
            y = height - (y - origin[1]) * scale
            poly.extend((x, y))
        canvas.create_polygon(poly, fill='black', outline='black')


if __name__ == "__main__":
    main()
