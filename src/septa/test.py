
import pyglpk
import fovgraph
import unittest
import random

class MyTest(unittest.TestCase):

    def setUp(self):
        self.graph = pyglpk.Graph()
        self.graph.add_vertices(10)

    def test_has_nodes(self):
        for i in xrange(1, 11):
            self.assertTrue(self.graph.has_node(i))
        for i in xrange(11, 20):
            self.assertFalse(self.graph.has_node(i))

    def test_add_edge(self):
        for i in xrange(1, 10):
            n = random.randrange(10)
            vals = random.sample(xrange(1, 10), n)
            for j in vals:
                self.graph.add_edge(i, j)
            for j in xrange(1, 10):
                try:
                    self.graph.get_edge_data((i, j))
                except KeyError:
                    if j in vals:
                        self.fail("edge not added to the graph")

    def test_add_edges(self):
        edges = []
        for i in xrange(1, 10):
            n = random.randrange(10)
            vals = random.sample(xrange(1, 10), n)
            edges.extend(((i, v), {'cap':5, 'low':3}) for v in vals)
        fovgraph.add_edges(self.graph, edges)

    def test_raises(self):
        edges = [((1,2), {'test':4})]
        self.assertRaises(KeyError, fovgraph.add_edges, self.graph, edges)

if __name__ == "__main__":
    unittest.main()

