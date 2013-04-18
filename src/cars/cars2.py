
from __future__ import division

import networkx as nx
import csv
import bisect
import collections
import random
import logging


GRAPH_FILE = 'graph-full.csv'
LOT_FILE = 'lot-data.txt'
METER = 1.0965  # 290m = |(658, 500) - (608, 814)| = 318px => 1m = 1.0965px
CAR_LENGTH = 4.5 * METER
OUTPUT_FILE = 'cars.output'
TOTAL_CARS = 1000


def main():
    # There's an if __name__ == "__main__": main() at the bottom
    logging.basicConfig(filename=OUTPUT_FILE, level=logging.INFO)
    sim = Simulation.from_file(GRAPH_FILE,
                               LOT_FILE,
                               CAR_LENGTH,
                               TOTAL_CARS)
    print "Made Simulation Object. Beginning Sim."
    sim.run(logging)

class Simulation(object):

    """
    This is the main object of the simulation.

    :param graph: A :class:`networkx.Digraph` with edge attributes
                  ``capacity`` stating the total capacity of the edge. In
                  this graph, nodes should represent parking lots and
                  intersections, and edges should represent one-way streets
                  connecting the nodes. Nodes considered outside the system
                  should have an attribute 'out' evaluating to True.
    :param arrival_params: A mapping :math:`\{\mathrm{node}:
                           (\mu, \sigma, n)\}`, where ``node`` is a node in
                           the graph, :math:`\mu, \sigma` are the parameters
                           of the gaussian arrival distribution,
                           and :math:`n` is the number of cars parked at that
                           node.
    """

    def __init__(self, graph, arrival_params):
        #: Contains all the simulation state in its edge attributes,
        #: ``weight``, ``capacity``, ``queue``, ``length``, ``num``
        self.graph = graph
        #: The target node for all vehicles
        self.exit_node = 0
        while self.graph.has_node(self.exit_node):
            self.exit_node += 1
        outnodes = [node for node, data in self.graph.nodes_iter(data=True)
                    if data.get('out', False)]
        assert len(outnodes) > 0
        for n1, n2, d in self.graph.in_edges_iter(outnodes, data=True):
            self.graph.remove_edge(n1, n2)
            self.graph.add_edge(n1, self.exit_node, d)
        self.rev = graph.reverse(copy=True)
        for s, t, d in self.graph.edges_iter(data=True):
            self.rev[t][s] = d
        arrivals = set()
        for node, p in arrival_params.items():
            arrivals.update((random.gauss(p[0], p[1]), node)
                            for _ in xrange(p[2]))
        self.arrivals = collections.deque(sorted(arrivals))
        self.__init_num = len(self.arrivals)

        self.exits = []
        self.time = 0
        self.last_edges = None
        self.path = {}
        self.update_weights()
        self.calc_path()

    @property
    def in_system(self):
        """How many cars are in the system."""
        return self.__init_num - len(self.exits)

    def update_weights(self):
        """
        Updates the cost of each edge based on the current flow distribution.
        """
        J = 1.6 * 8
        T = 1
        t0 = .09   # .09 s/m ~ 40 km / h
        Q = 600
        QT = Q * T
        for base, tgt in self.graph.edges_iter():
            # Formula from Akcelik, R. (1991). Travel time functions for
            # transport planning purposes: Davidson's function, its
            # time-dependent form and an alternative travel time function.
            # Australian Road Research 21 (3), pp. 49-59
            length = self.graph[base][tgt]['length']
            num = self.graph[base][tgt]['num']
            density = num / length
            flow = -11.67 * density + 1850  # density in [30, 90] veh/mi
            x = flow / Q
            z = x - 1
            t = t0 + .25 * T * (z + (z * z + J / QT) ** .5)
            cost = t * length * 3600  # convert to seconds
            self.graph[base][tgt]['weight'] = cost

    def get_edge_lambdas(self):
        """Calculate the lambda for each intersection."""
        edges = []
        for s, t, d in self.graph.edges_iter(data=True):
            try:
                dest = self.path[t]
            except KeyError:
                continue
            d2 = self.graph[t][dest]
            if d['queue'] and d2['capacity'] > d2['num']:
                el = d['length']
                num = d['num']
                density = num / el
                flow = -11.67 * density + 1850  # density in [30, 90] veh/mi
                edges.append(((s, t), 60 / flow))
        return edges

    def next_event(self):
        try:
            edges, lambdas = zip(*self.get_edge_lambdas())
        except ValueError:  # All edges empty
            edges = lambdas = []
            dt = float('inf')
            assert self.arrivals
        else:
            dt = random.expovariate(sum(lambdas))
        if (not self.arrivals) or (self.time + dt) <= self.arrivals[0][0]:
            n1, node = weighted_choice(zip(edges, lambdas))  # a random edge
            car = self.graph[n1][node]['queue'].popleft()
            self.graph[n1][node]['num'] -= 1
            self.time += dt
            self.last_edges = [(n1, node)]
        else:
            self.time, node = self.arrivals.popleft()
            assert node in self.graph
            self.last_edges = []
            car = []
        car.append((node, self.time))
        try:
            dest = self.path[node]
        except KeyError:  # node is self.exit_node
            assert node is self.exit_node
            self.exits.append(car)
        else:
            self.graph[node][dest]['queue'].append(car)
            self.graph[node][dest]['num'] += 1
            self.last_edges.append((node, dest))

    def calc_path(self):
        """Calculate the shortest path to exist from every node."""
        paths = nx.single_source_dijkstra_path(self.rev, self.exit_node)
        paths.pop(self.exit_node)
        self.path = {n: p[-2] for n, p in paths.items()}

    def log_traffic(self, logger):
        for n1, n2 in self.last_edges:
            d = self.graph[n1][n2]
            logger.info("Time: %f, Edge: (%s,%s), Cars: %d",
                        self.time, n1, n2, d['num'])
        print "Time: %f  Cars:%d" % (self.time, self.in_system)

    def run(self, logger):
        while self.in_system:
            self.update_weights()
            self.calc_path()
            self.next_event()
            self.log_traffic(logger)

    @classmethod
    def from_file(cls, graph_filename, source_filename, meter,
                  total_cars):
        """
        Create a Simulation object from two source files.

        :param graph_filename: location of the graph file, which should be a
                               csv file where the top row lists the head
                               nodes and the first column lists the tail
                               nodes of the incidence matrix.
        :param source_filename: location of the parking lot file, whose
                                format is described in :class:`SourceLoader`

        :returns: a :class:`Simulator` object with the loaded data.
        """
        lengths = {}
        with open(graph_filename, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            header = map(eval, next(reader)[1:])
            for line in reader:
                node = eval(line[0])
                body = [float(length) / meter for length in line[1:]]
                lengths[node] = {h: b
                                 for h, b in zip(header, body) if b >= 0}
        graph = guido_to_nx(lengths)
        sl = SourceLoader(open(source_filename))
        sources = sl.get_sources(total_cars, graph.nodes())
        print set(sources.keys()).difference(graph.nodes())
        assert set(sources.keys()).issubset(graph.nodes())
        sl.set_out(graph)
        return cls(graph, sources)


class SourceLoader(object):

    """
    A helper to load the parking lot demands.

    It reads in a file containing polygon information for each lot and a
    one-line header with the coordinates of the origin. The second line
    should be a sequence of coordinates designated exits. Each line after
    that is a polygon.

    Each line should be a valid python expression.
    I.e.:

        (x_o, y_o)
        [(x_e1, y_e2), (x_e1, y_e1), ... (x_ene, y_ene)]
        [(x_00, y_00), (x_01, y_01), ... (x_0n0, y_0n0)]
        [(x_10, y_10), (x_11, y_11), ... (x_1n1, y_1n1)]
        ...
        [(x_m0, y_m0), (x_m1, y_m1), ... (x_mn1, y_mn1)]

    """

    SIGMA_FACTOR = .1

    def __init__(self, source_file):
        sources = map(eval, source_file.read().strip().split('\n'))
        self.origin = sources[0]
        self.outs = sources[1]
        self.sources = sources[2:]
        self.pedestrian_speed = 1.333 * METER
          # 20 min/mile =>  v = 1.333 m/s

    def get_sources(self, total, nodes):
        """Gets the per-source demand."""
        centroids = map(self.get_centroid, self.sources)
        distances = map(self.get_distance, centroids)
        areas = map(self.calc_polygon_area, self.sources)
        factors = [abs(a) / d ** 2
                   for a, d in zip(areas, distances)]
        scale = total / sum(factors)
        nums = [int(f * scale) for f in factors]
        centers = [self.get_closest(nodes, c) for c in centroids]
        assert sum(nums) <= total
        times = [d / self.pedestrian_speed for d in distances]
        return {c: (t, self.SIGMA_FACTOR * t, n)
                for c, t, n in zip(centers, times, nums)}

    def get_closest(self, node_set, target, tolerance=5):
        old_o = self.origin
        self.origin = target
        res = min(node_set, key=self.get_distance)
        self.origin = old_o
        if tolerance >= 0 and self.get_length(target, res) > tolerance:
            raise ValueError("No nearest node for %s" % repr(target))
        return res

    def set_out(self, nx_graph, tolerance=5):
        """Select the node closest to each exit point and label it 'out'."""
        for node in self.outs:
            res = self.get_closest(nx_graph.nodes_iter(), node, tolerance)
            nx_graph.node[res]['out'] = True

    def get_distance(self, point):
        """Get the distance from the origin."""
        return self.get_length(self.origin, point)

    @staticmethod
    def get_length(point1, point2):
        """Get the length of a segment."""
        x = point1[0] - point2[0]
        y = point1[1] - point2[1]
        return (x * x + y * y) ** .5

    @staticmethod
    def calc_polygon_area(polygon):
        polygon = list(polygon)
        def vectorize(points):
            p1, p2 = points
            return p2[0] - p1[0], p2[1] - p1[1]
        segments = map(vectorize, zip(polygon, polygon[1:] + [polygon[0]]))
        adjs = zip(segments, segments[1:] + [segments[0]])
        def crossp(vectors):
            v1, v2 = vectors
            return v1[0] * v2[1] - v1[1] * v2[0]
        return sum(map(crossp, adjs))

    @staticmethod
    def get_centroid(polygon):
        """Calculate the centroid of a polygon"""
        x = sum(zip(*polygon)[0]) / len(polygon)
        y = sum(zip(*polygon)[1]) / len(polygon)
        return x, y

def guido_to_nx(graph):
    """
    Convert a simple python graph into a networkx Digraph.

    :param graph: a mapping of the form ``node: {target: length}``,
                  where ``(node, target)`` is an edge in the graph with
                  length ``length``.
    :returns: :class:`networkx.Digraph`
    """
    G = nx.DiGraph()
    for node in graph:
        for tgt, length in graph[node].items():
            cap = int(length / CAR_LENGTH)
            G.add_edge(node, tgt,
                       capacity=cap,
                       length=length,
                       num=0,
                       queue=collections.deque())
    return G

def weighted_choice(choices):
    """
    Select an element from a finite discrete distribution.

    :param choices: An iterable of ``(element, weight)`` pairs.

    Note---weights are automatically normalized.

    Taken from http://stackoverflow.com/a/4322940

    """
    values, weights = zip(*choices)
    total = 0
    cum_weights = []
    for w in weights:
        total += w
        cum_weights.append(total)
    x = random.random() * total
    i = bisect.bisect(cum_weights, x)
    return values[i]

if __name__ ==  "__main__":
    main()
