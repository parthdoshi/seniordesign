
from __future__ import division
from matplotlib import nxutils

import networkx as nx
import sqlite3
import numpy


LINK_DB = "final.db"
STOPS_DB = "stops.db"
DEMAND_FILE = "demand.csv"
OUTPUT = "septa-results.csv"

def main():
    # There's an if __name__ == "__main__": main() at the bottom
    main_sim()

def main_sim():
    print "Starting"
    graph = make_guido_graph(LINK_DB)
    print "Loaded the DB into a graph"
    nxgraph = guido_to_nx(graph)
    print "Made the NetworkX graph"
    capacity = get_capacity(graph)
    print "Loaded the network's capacity"
    demand = get_demand()
    print "Loaded the network's demand"
    flow = simplex(nxgraph, demand, capacity)
    print "Found the optimal flow"
    flow_to_csv(flow, OUTPUT)
    print "Wrote the results to %s" % OUTPUT

def get_capacity(graph):
    """Load the capacity of each link."""
    raise NotImplementedError

def get_demand():
    """
    Get the time and space varying demand.

    The output is a dictionary of the form {(stop_id, time): demand}
    """
    csv = [l.split(',') for l in open(DEMAND_FILE).read().split('\n')]
    zipcodes = set(zip(*csv)[0])
    zipdemand = {z: {} for z in zipcodes}
    for zipcode, time, d in csv:
        zipdemand[zipcode][time] = d
    connection = sqlite3.connect(STOPS_DB,
                                 detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()

    stopdemand = {}
    for zipcode, times in zipdemand.items():
        cursor.execute('SELECT stop_id FROM stops WHERE zipcode=?',
                       (zipcode,))
        stops = cursor.fetchall()
        for time, d in times.items():
            perstopd = d / len(stops)
            stopdemand.update({(stop, time): perstopd for stop in stops})
    return stopdemand

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

    # Build the node list as origin,departure-time and
    # destination,arrival-time pairs
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
                       'WHERE origin = ? AND departure = ?',
                       node)
        dests, arrs, types = zip(*cursor.fetchall())
        costs = [(arr - node[1]).seconds for arr in arrs]
        dapairs = map(tuple, zip(dests, arrs))
        graph[node] = set(zip(dapairs, costs, types))

        try:  # This entire block is for the waiting links
            name, time = nodes[i+1]  # Reason for sorting
        except IndexError:
            pass
        else:
            if name == node[0]:
                cost = (time - node[1]).seconds
                t = 'wait'
                graph[node].add((nodes[i+1], cost, t))
    return graph

def guido_to_nx(graph):
    """
    Convert a python graph to a networkx directed graph.

    Input should be a mapping of the form

        {
          source-node:
              set({
                    [dest-node-1, cost, type],
                    ... ,
                    [dest-node-2, cost, type],
              })
        }

    which (by construction) exactly matches that of make_guido_graph
    """
    G = nx.Digraph()
    for node in graph:
        for tgt, cost, t in graph[node]:
            G.add_edge(node, tgt, weight=cost, kind=t)
    return G

def simplex(graph, demand, capacity):
    """
    Run the network simplex algorithm on a graph.

    :param graph: a networkx Digraph
    :param demand: a mapping {node: demand}. Note that demands should sum
                   to 0. If a node isn't in ``demand``, it is assumed to
                   have 0 demand
    :param capacity: a mapping {node: capacity}. If a node isn't in
                     ``capaciy`` it is assumed to have unlimited capacity.

    :returns: a double mapping ``flow_dict`` of the form
              ``{base: {target1: flow, target2: flow}}`` so that
              ``flow_dict[node1][node2]`` is the flow across edge
              ``(node1, node2)``
    """
    for node in graph.nodes_iter():
        graph.node[node]['demand'] = demand.get(node, 0)
        try:
            graph.node[node]['capacity'] = capacity[node]
        except KeyError:
            pass
    return graph.network_simplex()

def flow_to_csv(flow, filename):
    nodes = list(flow)
    with open(filename, 'wt') as f:
        f.write(',' + ','.join('"%s"' % str(n) for n in nodes))
        f.write('\n')
        for node in nodes:
            f.write('"%s",' % str(node))
            f.write(','.join(int(flow[node].get(n2, -1))
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
        print "Committed

if __name__ == "__main__":
    main()
