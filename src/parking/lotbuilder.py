
from __future__ import division
from graphmaker import Graph, ImageGraph, NodeMaker, EdgeMaker, tkFileDialog
import networkx as nx
import Tkinter

def to_nx(graph):
    """Convert a python graph into a networkx graph."""
    G = nx.Graph()
    for node in graph:
        G.add_node(node)
        for tgt in graph[node]:
            G.add_edge(node, tgt)
    return G

def sort_cycle(cycle, key=None):
    """Rotate a cycle so that the smallest element is first."""
    if key:
        m = min(cycle, key=key)
    else:
        m = min(cycle)
    i = cycle.index(m)
    return cycle[i:] + cycle[:i]

def get_cycles():
    """One-off function used to generate the parking lot polygons."""
    g = Graph()
    g.load_filename('lot-nodes-1.csv')
    ng = to_nx(g)
    cycles = nx.cycle_basis(ng)
    g.load_filename('lot-nodes-2.csv')
    ng = to_nx(g)
    cycles.extend(nx.cycle_basis(ng))
    cycles = set(map(tuple, map(sort_cycle, cycles)))
    return cycles

def purge_loose_nodes():
    """One-off function used to remove disconnected nodes from the graph."""
    g = Graph()
    g.load_filename('graph-full.csv')
    ng = to_nx(g)
    for n in list(g):
        if not ng.neighbors(n):
            del g[n]
    g.dump('graph.csv')


class LotGraph(ImageGraph):

    def __init__(self, total_size):
        super(LotGraph, self).__init__()
        self.total_size = total_size
        Tkinter.Button(self.topframe, text="Load Parking Lots",
                       command=self.load_parking_lots).pack(
                           side=Tkinter.LEFT)

    def load_parking_lots(self):
        """Prompt for a parking lot file and load it."""
        types = [('text files', '.txt'), ('all files', '*')]
        message = "Select a file with parking lot coordinates."
        polygonsfile = tkFileDialog.askopenfilename(parent=self.root,
                                                    filetypes=types,
                                                    title=message)
        self.load_parking_lots_file(polygonsfile)

    def load_parking_lots_file(self, polygonsfile):
        """Load polygon file as parking lots."""
        polygons = map(eval, open(polygonsfile).read().strip().split('\n'))
        self.scale = 1
        self.scale = self.total_size / sum(map(self.calc_area, polygons))
        for polygon in polygons:
            self.draw_polygon(polygon)
            x, y = self.get_centroid(polygon)

    def draw_polygon(self, polygon):
        """
        Draw the polygon on the canvas.

        Draws a polygon  writes its area in the middle.
        """
        super(LotGraph, self).draw_polygon(polygon)
        i = self.canvas.create_polygon(*polygon, tag='lot')
        self.canvas.itemconfig(i, fill='#66f', outline='#fff')
        area = self.calc_area(polygon)
        area *= 2 * (area > 0) - 1
        area = "{0:,.0f}".format(area)
        x, y = self.get_centroid(polygon)
        #self.canvas.create_text(x, y, text=str(area), fill='black')

    @staticmethod
    def get_centroid(polygon):
        """Calculate the centroid of a polygon"""
        x = sum(zip(*polygon)[0]) / len(polygon)
        y = sum(zip(*polygon)[1]) / len(polygon)
        return x, y

    def calc_area(self, polygon):
        polygon = list(polygon)
        def vectorize(points):
            p1, p2 = points
            return p2[0] - p1[0], p2[1] - p1[1]
        segments = map(vectorize, zip(polygon, polygon[1:] + [polygon[0]]))
        adjs = zip(segments, segments[1:] + [segments[0]])
        def crossp(vectors):
            v1, v2 = vectors
            return v1[0] * v2[1] - v1[1] * v2[0]
        return sum(map(crossp, adjs)) * self.scale

def main():
    TOTAL_CAPACITY = 25000
    try:
        app = LotGraph(TOTAL_CAPACITY)
    except ValueError:  # No background image selected
        pass
    else:
        app.start()

if __name__ == "__main__":
    main()
