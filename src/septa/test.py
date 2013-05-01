
import pyglpk
import unittest
import random

from fovgraph import INT_MAX

def get_random_edges(low, high):
    for i in xrange(low, high):
        n = random.randrange(high - low)
        for j in random.sample(range(low, high), n):
            yield (i, j)


class BasicTest(unittest.TestCase):

    def setUp(self):
        self.graph = pyglpk.Graph()
        self.graph.add_vertices(10)

    def test_has_nodes(self):
        for i in xrange(1, 11):
            self.assertTrue(self.graph.has_node(i))
        for i in xrange(11, 20):
            self.assertFalse(self.graph.has_node(i))

    def test_has_edge(self):
        for i in xrange(1, 10):
            for j in xrange(1, 10):
                self.graph.add_edge(i, j)
                self.assertTrue(self.graph.has_edge((i, j)))
            for j in xrange(11, 20):
                self.assertFalse(self.graph.has_edge((i, j)))

    def test_add_edge(self):
        for i in xrange(1, 10):
            n = random.randrange(10)
            vals = random.sample(xrange(1, 10), n)
            for j in vals:
                self.graph.add_edge(i, j)
            for j in xrange(1, 10):
                self.assertTrue(self.graph.has_edge((i, j)) or
                                j not in vals)

    def test_add_edges_with_data(self):
        edges = [(e, {'cap': random.randrange(1, 10),
                      'cost': random.randrange(1, 10)})
                  for e in get_random_edges(1, 10)]
        self.graph.add_edges(edges)
        for edge, data in edges:
            self.assertTrue(self.graph.has_edge(edge))
            gdata = self.graph.get_edge_data(edge)
            self.assertTrue(gdata.cap == data['cap'])
            self.assertTrue(gdata.cost == data['cost'])
            self.assertTrue(gdata.low == 0)

    def test_add_edges_missing_data(self):
        def get_edges():
            for e in get_random_edges(1, 10):
                d = {}
                if random.getrandbits(1):
                    d['cap'] = random.randrange(1, 10)
                if random.getrandbits(1):
                    d['cost'] = random.randrange(1, 10)
                yield (e, d)
        edges = get_edges()
        self.graph.add_edges(edges)
        for edge, data in edges:
            self.assertTrue(self.graph.has_edge(edge))
            gdata = self.graph.get_edge_data(edge)
            self.assertTrue(gdata.cap == data.get('cap', INT_MAX))
            self.assertTrue(gdata.cost == data.get('cost', 0))
            self.assertTrue(gdata.low == 0)

    def test_add_edges(self):
        edges = list(get_random_edges(1, 10))
        self.graph.add_edges(edges)
        for edge in edges:
            self.assertTrue(self.graph.has_edge(edge))

    def test_raises(self):
        edges = [((1,2), {'test':4})]
        self.assertRaises(KeyError, self.graph.add_edges, edges)



class AlgoTest(unittest.TestCase):

    # Graph is set up like so: (cap, cost) above edges
    #
    #          (1, 1)        (1, 1)        (1, 1)        (1, 1)
    #      1 ----------> 2 ----------> 3 ----------> 4 ----------> 5
    #      |                                                       ^
    #      |                    (infty, 5)                         |
    #      +-------------------------------------------------------+
    #
    #          (1, 0)        (1, 0)
    #      6 <---------> 7 <---------> 8
    #
    #          (1, 1)
    #      9 <---------> 10
    #

    def setUp(self):
        self.graph = pyglpk.Graph()
        self.graph.add_vertices(10)
        edges = [(1, 2), (2, 3), (3, 4), (4, 5),
                 (6, 7), (7, 6), (8, 7), (7, 8),
                 (9, 10), (10, 9)]
        costs = [1, 1, 1, 1,
                 0, 0, 0, 0,
                 1, 1]
        caps = [1] * len(costs)
        assert len(edges) == len(costs) == len(caps)
        self.graph.add_edges((e, {'cap': cap, 'cost': cost})
                             for e, cap, cost in zip(edges, caps, costs))
        self.graph.add_edges([((1, 5), {'cost': 5})])


class IOTest(AlgoTest):

    def setUp(self):
        super(IOTest, self).setUp()
        import tempfile, os
        self.__tempfile = tempfile
        self.__os = os
        self.__names = []

    def tearDown(self):
        super(IOTest, self).tearDown()
        for name in self.__names:
            self.__os.unlink(name)

    def get_name(self):
        fd, name = self.__tempfile.mkstemp()
        self.__os.close(fd)
        self.__names.append(name)
        return name

    def test_plain_io(self):
        name = self.get_name()
        self.graph.write_graph(name)
        g = pyglpk.Graph.read_graph(name)
        for edge in self.graph.iter_edges():
            self.assertTrue(g.has_edge(edge))
        for edge in g.iter_edges():
            self.assertTrue(self.graph.has_edge(edge))

    def test_mincost_io(self):
        name = self.get_name()
        self.graph.write_mincost(name)
        g = pyglpk.Graph.read_mincost(name)
        self.assertEqual(g.num_nodes, self.graph.num_nodes)
        for node, data in self.graph.iter_nodes(True):
            gdata = g.get_node_data(node)
            self.assertEqual(data['demand'], gdata.rhs)
        for edge, data in self.graph.iter_edges(True):
            self.assertTrue(g.has_edge(edge))
            gdata = g.get_edge_data(edge)
            for key in 'cap', 'cost', 'low':
                self.assertEqual(data[key], getattr(gdata, key))


class MinCostTest(AlgoTest):

    # Graph is set up as above, with following demands:
    #
    # flow  dir  node
    #   1    =>    1
    #   1    <=    5
    #   1    <=    9
    #   1    =>    10

    def setUp(self):
        super(MinCostTest, self).setUp()
        self.graph.set_demand(5, -1)
        self.graph.set_demand(1, 1)
        self.graph.set_demand(9, -1)
        self.graph.set_demand(10, 1)

    def test_flow(self):
        flow, cost = self.graph.mincost_okalg()
        self.assertEqual(flow, {1:{2: 1}, 2:{3:1}, 3:{4:1}, 4:{5:1},
                                10:{9: 1}})
        self.assertEqual(cost, 5)

    def test_infeasible(self):
        self.graph.set_demand(2, 1)
        self.assertRaises(ValueError, self.graph.mincost_okalg)
        self.graph.set_demand(2, 0)
        self.graph.set_demand(2, 2)
        self.graph.set_demand(5, 3)
        self.assertRaises(ValueError, self.graph.mincost_okalg)


if __name__ == "__main__":
    unittest.main()

