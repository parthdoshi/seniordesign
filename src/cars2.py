
import networkx as nx
import bisect
import collections
import random

def guido_to_nx(graph):
    """
    Convert a simple python grah into a networkx Digraph.

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

    @property
    def in_system(self):
        """How many cars are in the system."""
        return self.__init_num - len(self.exits)

    def update_weights(self):
        """
        Updates the cost of each edge based on the current flow distribution.
        """
        for s, t in self.graph.edges_iter():
            self.graph[s][t]['weight'] = NotImplemented # FIXME

    def get_edge_lambdas(self):
        """Calculate the overall lambda for all intersections."""
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
        if (not self.arrivals) or dt <= self.arrivals[0]:
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

    def run(self):
        while self.in_system:
            self.update_weights()
            self.calc_path()
            self.next_event()
