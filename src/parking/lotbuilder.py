
import networkx as nx
from graphmaker import Graph, ImageGraph

def to_nx(graph):
    G = nx.Graph()
    for node in graph:
        for tgt in graph[node]:
            G.add_edge(node, tgt)
    return G

def sort_cycle(cycle, key=None):
    if key:
        m = min(cycle, key=key)
    else:
        m = min(cycle)
    i = cycle.index(m)
    return cycle[i:] + cycle[:i]

def get_cycles():
    g = Graph()
    g.load_filename('lot-nodes-1.csv')
    ng = to_nx(g)
    cycles = nx.cycle_basis(ng)
    g.load_filename('lot-nodes-2.csv')
    ng = to_nx(g)
    cycles.extend(nx.cycle_basis(ng))
    cycles = set(map(tuple, map(sort_cycle, cycles)))
    return cycles


class LotGraph(ImageGraph):

    def __init__(self, cycles):
        super(LotGraph, self).__init__()
        for cycle in cycles:
            self.draw_cycle(cycle)

    def draw_cycle(self, cycle):
        i = self.canvas.create_polygon(*cycle, tag='lot')
        self.canvas.itemconfig(i, fill='#f99', outline='white')

app = LotGraph(get_cycles())
app.start()
