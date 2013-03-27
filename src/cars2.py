
def guido_to_nx(graph):
    G = nx.Digraph()
    for node in graph:
        for tgt, cap in graph[node]:
            G.add_edge(node, tgt, capacity=cap)
    return G

class Simulation(object):

    def __init__(self, graph, arrival_params, weight_fns):
        self.graph = guido_to_nx(graph)
        self.exits = 0
        self.arrivals = set()
        for node, p in arrival_params.items():
            self.arrivals.update((random.gauss(p[0], p[1]), node)
                                 for _ in xrange(p[2]))
        self.weight_fns = weight_fns
        self.paths = 

    def update_weights(self):
        for s, t in self.graph.edges_iter():
            self.graph[s][t]['weight'] = self.weight_fns[(s, t)]()
            #FIXME

    def calc_lambda(self):
        for s, t, d in self.graph.edges_iter(data=True):
            
