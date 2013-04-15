
from __future__ import division
from matplotlib import nxutils

import sqlite3
import numpy
import tempfile
import os
import subprocess
import re

LINK_DB = "final.db"
STOPS_DB = "stops.db"
DEMAND_FILE = "demand.csv"
OUTPUT = "septa-results.csv"
STADIUM_STOP_ID = 0
GAMETIME

def main():
    # There's an if __name__ == "__main__": main() at the bottom
    main_sim(GAMETIME)

def main_sim(gametime):
    print "Starting"
    capacity = get_capacity()
    print "Loaded the network's capacity"
    demand = get_demand(gametime)
    print "Loaded the network's demand"
    flow = simplex(graph, demand, capacity)
    print "Found the optimal flow"
    flow_to_csv(flow, OUTPUT)
    print "Wrote the results to %s" % OUTPUT

def get_capacity():
    """Load the capacity of each link."""
    raise NotImplementedError

def get_demand(gametime):
    """
    Get the time and space varying demand.

    The input is CSV with eight columns and one header row:

        Zip Code,(-80:-60),(-60:-40),(-40:-20),(-20:0),(0:20),(20:40),(40:60)

    where each row indicates the number of people from each zip code arriving
    at the specified interval in minutes relative to the game start time.

    The output is a mapping
    """
    csv = [l.split(',') for l in open(DEMAND_FILE).read().split('\n')]
    demand = {}
    for row in csv:
        demand[row[0]] = sum(map(int, row[1]))
        time = gametime - 80
        for v in map(int, row[1:]):
            val = int(v / 4)
            for _ in xrange(4):
                time += 5
                try:
                    demand[(STADIUM_STOP_ID, time)] -= val
                except KeyError:
                    demand[(STADIUM_STOP_ID, time)] = -val
    return demand

def make_guido_graph(dbfile):
    """
    Reads in the septa database and outputs a space-time graph.

    Output is a mapping of the form

        {
          (node-name, time-object):
                  set({
                    [(node-name, time-object), cost, type],
                    ... ,
                    [(node-name, time-object), cost, type],
                  })
        }

    where one node is in the set of another node iff there is a
    direct link between them, the cost is simply the difference
    in seconds of their time coordinate, and type refers to the
    SEPTA API type to distinguish between buses, trolleys, etc.
    There is the addition of the type 'wait' for waiting links.
    """
    connection = sqlite3.connect(
            dbfile, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()

    # Build the node list as (origin,departure-time) and
    # (destination,arrival-time) pairs and zipcode source
    # nodes
    cursor.execute('SELECT DISTINCT origin, departure '
                   'FROM septa')
    nodes = map(tuple, cursor.fetchall())
    cursor.execute('SELECT DISTINCT destination, arrival '
                   'FROM septa')
    nodes.extend(map(tuple, cursor.fetchall()))

    # Use sorting to insert waiting links of the form
    #      ('xxx', 12:00:00) -> ('xxx', 12:03:00)
    # ensuring the links are only among consecutive nodes
    nodes = sorted(set(nodes))
    graph = {}
    for i, node in enumerate(nodes):
        cursor.execute('SELECT destination, arrival, type'
                       'FROM links'
                       'WHERE origin = ? AND departure = ?',
                       node)
        dests, arrs, types = zip(*cursor.fetchall())
        costs = [int((arr - node[1]).seconds / 60) for arr in arrs]
        dapairs = map(tuple, zip(dests, arrs))
        graph[node] = set(zip(dapairs, costs, types))

        try:  # This entire block is for the waiting links
            name, time = nodes[i+1]  # Reason for sorting
        except IndexError:
            pass
        else:
            if name == node[0]:
                cost = int((time - node[1]).seconds / 60)
                t = 'wait'
                graph[node].add((nodes[i+1], cost, t))
    cursor.execute('SELECT DISTINCT zipcode FROM stops')
    zipcodes = map(int, zip(*cursor.fetchall())[0])
    for zipcode in zipcodes:
        cursor.execute('SELECT links.origin, links.departure '
                       'FROM links '
                       'INNER JOIN stops '
                       'ON links.origin=stops.stop_id '
                       'WHERE stops.zipcode=?',
                       str(zipcode))
        graph[zipcode] = set((tuple(r), 0, 'init')
                             for r in cursor.fetchall())
    return graph

def simplex(graph, demand, capacity):
    """
    Run the network simplex algorithm on a graph.

    :param graph: a python graph as returned by make_guido_graph
    :param demand: a mapping {node: demand}. Note that demands should sum
                   to 0. If a node isn't in ``demand``, it is assumed to
                   have 0 demand
    :param capacity: a mapping {node: capacity}. If a node isn't in
                     ``capacity`` it is assumed to have unlimited capacity.

    :returns: a double mapping ``flow_dict`` of the form
              ``{base: {target1: flow, target2: flow}}`` so that
              ``flow_dict[node1][node2]`` is the flow across edge
              ``(node1, node2)``
    """
    fd, name = tempfile.mkstemp
    f = os.fdopen(fd)
    node_ids = make_dimacs(graph, demand, capacity, f)
    f.close()
    flow = run_ook(name)
    output = {}
    for i, d in flow.items():
        node = node_ids[i]
        output[node] = {node_ids[j]: f for j, f in d.items()}
    return output

def run_ook(filename):
    """
    Run the Ford-Fulkerson algorithm on a DIMACS file.

    Returns a double mapping ``flowdict`` such that ``flowdict[i][j]``
    is the amount of flow across edge ``(i, j)``.
    """
    output = subprocess.Popen(['./ook.exe', filename],
                              stdout=subprocess.PIPE)
    arcline = re.compile('arc ([0-9]+)->([0-9]+): x = +(-?[0-9]+); '
                         'lambda = +-?[0-9]+')
    flowdict = {}
    for line in output.stdout:
        m = arcline.match(line)
        try:
            src, dest, flow = map(int, m.groups())
        except AttributeError:
            continue
        try:
            flowdict[src][dest] = flow
        except KeyError:
            flowdict[src] = {dest: flow}
    return flowdict

def make_dimacs(graph, demand, capacity, filelike):
    """
    Write a DIMACS file of a graph.

    Returns a mapping of ``node_id``\ s written to the file to the
    corresponding python object.
    """
    num_nodes = len(graph)
    arcs = sum(map(len(graph.values())))
    filelike.write('p min %d %d' % (num_nodes, arcs))
    nodes = sorted(graph)
    for i, node in enumerate(nodes):
        if not demand.get(node, 0):
            continue
        filelike.write('n %d %d' % (i, demand[node]))

    for i, node in enumerate(nodes):
        for target, cost, _ in graph[node]:
            j = nodes.index(target)
            filelike.write('a %d %d 0 %d %d' %
                           (i,
                            j,
                            capacity.get((node, target), -1),
                            cost))
    return dict(enumerate(nodes))

def flow_to_csv(flow, filename):
    """
    Write a flow vector to a CSV.

    The input ``flow`` is a double mapping ``{node-i : {node_j : flow_ij}}``
    The output format is

        \  N1  N2  N3  ...  Nk
       N1  x   x   x        x
       N2  x   x   x        x
       N3  x   x   x        x
      ...
       Nk  x   x   x        x

    where the entry in the i-th row and j-th column represents the flow
    from the i-th to the j-th node.

    Entries not in the flow vector are left blank.
    """
    nodes = list(flow)
    with open(filename, 'wt') as f:
        f.write(',' + ','.join('"%s"' % str(n) for n in nodes))
        f.write('\n')
        for node in nodes:
            f.write('"%s",' % str(node))
            f.write(','.join(str(flow[node].get(n2, ''))
                             for n2 in nodes))
            f.write('\n')

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
            self.containers = containers
        self.vertex_in = {}
        self.bake_verteces()

    def bake_verteces(self):
        """Populate the vertex_in dictionary."""
        self.vertex_in = {}
        for id_, container in self.containers.items():
            for shape in container:
                for poly in shape:
                    for x, y in poly:
                        if (x, y) in self.vertex_in:
                            self.vertex_in[(x, y)].add(id_)
                        else:
                            self.vertex_in[(x, y)] = set([id_])

    def get_match(self, x, y):
        """Return the id of the containing shape."""
        node = self.get_nearest_node(x, y)
        for container in self.vertex_in[node]:
            if self.contains(self.containers[container], (x, y)):
                return container

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
        return min(self.vertex_in.keys(),
                   key=lambda n: self.get_length((x, y), n))

    def load(self, filename):
        """Load the zipcode file into the object."""
        self.containers = {}
        with open(filename) as f:
            for line in f:
                id_, container = line.split(":")
                id_ = int(id_)
                container = eval(container)
                self.containers[id_] = container
        self.bake_verteces()

    @staticmethod
    def get_length(n1, n2):
        """Get the length of a segment."""
        x1, y1 = n1
        x2, y2 = n2
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** .5


def set_station_zips(zipcodefile):
    """
    Set the zipcodes in the septa stop db.
    """
    matcher = Matcher()
    matcher.load(zipcodefile)
    connection = sqlite3.connect(STOPS_DB,
                                 detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()

    cursor.execute('SELECT stop_id, stop_lat, stop_lon '
                   'FROM stops'
                   "WHERE zipcode=''"
        )
    stops = cursor.fetchall()
    i = 0
    for id_, lat, lon in stops:
        zipcode = matcher.get_match(lat, lon)
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

if __name__ == "__main__":
    main()
