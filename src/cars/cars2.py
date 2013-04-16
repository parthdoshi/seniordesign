
import networkx as nx
import csv
import bisect
import collections
import random
import logging

OUTPUT_FILE = 'cars.output'
CAR_LENGTH = 1
TOTAL_CARS = 25000

def guido_to_nx(graph):
    """
    Convert a simple python graph into a networkx Digraph.

    :param graph: a mapping of the form ``node: [(target, capacity)]``,
                  where ``(node, target)`` is an edge in the graph with
                  capacity ``capacity``.
    :returns: :class:`networkx.Digraph`
    """
    G = nx.Digraph()
    for node in graph:
        for tgt, cap in graph[node]:
            G.add_edge(node, tgt, capacity=cap)
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
        #: ``weight``, ``capacity``, ``queue``
        self.graph = graph
        #: The target node for all vehicles
        self.exit_node = 0
        while self.graph.has_node(self.exit_node):
            self.exit_node += 1
        outnodes = [node for node, data in self.graph.nodes_iter(data=True)
                    if data.get('out', False)]
        for n1, n2, d in self.graph.in_edges_iter(outnodes, data=True):
            self.graph.remove_edge(n1, n2)
            self.graph.add_edge(n1, self.exit_node, d)

        arrivals = set()
        for node, p in arrival_params.items():
            arrivals.update((random.gauss(p[0], p[1]), node)
                            for _ in xrange(p[2]))
        self.arrivals = collections.deque(sorted(arrivals))
        self.__init_num = len(self.arrivals)

        self.exits = []
        self.time = 0
        self.path = {}
        logging.basicConfig(filename=OUTPUT_FILE, level=logging.INFO)
        self.logger = logging

    @property
    def in_system(self):
        """How many cars are in the system."""
        return self.__init_num - len(self.exits)

    def update_weights(self):
        """
        Updates the cost of each edge based on the current flow distribution.
        """
        for s, t in self.graph.edges_iter():
            pass
            #self.graph[s][t]['weight'] = NotImplemented # FIXME

    def get_edge_lambdas(self):
        """Calculate the lambda for each intersections."""
        edges = []
        for s, t, d in self.graph.edges_iter(data=True):
            d2 = self.graph[t][self.path[t]]
            if d['queue'] and d2['capacity'] > len(d2['queue']):
                edges.append((s, t), .1)  # 10 vehicles per minute ~ 600 VPH
                # FIXME
        return edges

    def next_event(self):
        edges, lambdas = zip(*self.get_edge_lambdas())
        dt = random.expovariate(sum(lambdas))
        if (not self.arrivals) or (self.time + dt) <= self.arrivals[0][0]:
            n1, node = weighted_choice(zip(edges, lambdas))  # a random edge
            car = self.graph[n1][node]['queue'].popleft()
            self.time += dt
        else:
            self.time, node = self.arrivals.popleft()
            car = []
        car.append((node, self.time))
        try:
            dest = self.path[node]
        except KeyError:  # node is self.exit_node
            self.exits.append(car)
        else:
            self.graph[node][dest]['queue'].append(car)

    def calc_path(self):
        """Calculate the shortest path to exist from every node."""
        rev = self.graph.reverse(copy=True)
        paths = rev.single_source_dijkstra_path(self.exit_node)
        paths.pop(self.exit_node)
        self.path = {n: p[-2] for n, p in paths.items()}

    def log_traffic(self):
        for n1, n2, d in self.graph.edges_iter(data=True):
            self.logger.info("Time: %f, Edge: (%s,%s), Cars: %d",
                             self.time, n1, n2, len(d['queue']))

    def run(self):
        while self.in_system:
            self.log_traffic()
            self.update_weights()
            self.calc_path()
            self.next_event()

    @classmethod
    def from_file(cls, filename, source_filename):
        lengths = {}
        with open(filename, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)[1:]
            for line in reader:
                node = line[0]
                body = [float(length) / CAR_LENGTH for length in line[1:]]
                lengths[node] = {h: l
                                 for h, l in zip(header, body) if l >= 0}
        graph = guido_to_nx(lengths)
        sl = SourceLoader(open(source_filename))
        sources = sl.get_sources(TOTAL_CARS)
        return cls(graph, sources)


class SourceLoader(object):

    SIGMA_FACTOR = .1
    PEDESTRIAN_SPEED = .296  # 20 min/mile =>  v = .296 * (4.5m/s), where
                             # 4.5 is a car length # FIXME

    def __init__(self, source_file):
        sources = map(eval, source_file.read().strip().split('\n'))
        self.origin = sources[0]
        self.sources = sources[1:]

    def get_sources(self, total):
        """Gets the per-source total demand."""
        centroids = map(self.get_centroid, self.sources)
        distances = map(self.get_distance, centroids)
        factors = [self.calc_polygon_area(s) / d ** 2
                   for d, s in zip(distances, self.sources)]
        scale = total / sum(factors)
        times = [d / self.PEDESTRIAN_SPEED for d in distances]
        return {c: (t, self.SIGMA_FACTOR * t, f * scale)
                for c, t, f in zip(centroids, times, factors)}

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
