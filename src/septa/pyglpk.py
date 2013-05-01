

"""
Library to interface with glpk graph
"""

import ctypes
import itertools
import fovgraph
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

_PATH_TO_SO = '/usr/local/lib/libglpk.so'
_GLPK = ctypes.CDLL(_PATH_TO_SO)

_TermHookFunction = ctypes.CFUNCTYPE(ctypes.c_int,
                                     ctypes.c_void_p, ctypes.c_char_p)

class GLPKStdout(object):

    def __init__(self, set_hook=False):
        self.buffer = StringIO.StringIO()
        self.state = False
        self._term_hook = _TermHookFunction(self._redirect_stdout)
        if set_hook:
            self.set_hook(True)

    def __del__(self):
        self.set_hook(False)

    def set_hook(self, state):
        if (not self.state) and state:
            _GLPK.glp_term_hook(self._term_hook, None)
            self.state = True
        elif self.state and (not state):
            _GLPK.glp_term_hook(None, None)
            self.state = False

    def _redirect_stdout(self, info, s):
        if info:
            raise RuntimeError()
        self.buffer.write(s)
        return 1

    def reset(self):
        self.seek(0)
        self.buffer.truncate()

    def read_all(self):
        self.seek(0)
        return self.read()

    def read(self, q=None):
        if q is None:
            return self.buffer.read()
        else:
            return self.buffer.read(q)

    def readlines(self):
        return self.buffer.readlines()

    def read_last(self, n=1):
        self.seek(0)
        return [l.strip('\n') for l in self.readlines()[-n:]]

    def seek(self, pos):
        self.buffer.seek(pos)


#struct glp_arc
class cArc(ctypes.Structure):
    pass


# struct glp_vertex
class cVertex(ctypes.Structure):
    _fields_ = [('i', ctypes.c_int),
                ('name', ctypes.c_char_p),
                ('entry', ctypes.c_void_p),
                ('data', ctypes.c_void_p),
                ('temp', ctypes.c_void_p),
                ('in', ctypes.POINTER(cArc)),
                ('out', ctypes.POINTER(cArc))]

cArc._fields_ = [('tail', ctypes.POINTER(cVertex)),
                 ('head', ctypes.POINTER(cVertex)),
                 ('data', ctypes.c_void_p),
                 ('temp', ctypes.c_void_p),
                 ('t_prev', ctypes.POINTER(cArc)),
                 ('t_next', ctypes.POINTER(cArc)),
                 ('h_prev', ctypes.POINTER(cArc)),
                 ('h_next', ctypes.POINTER(cArc))]


# struct glp_graph
class cGraph(ctypes.Structure):
    _fields_ = [('pool', ctypes.c_void_p),
                ('name', ctypes.c_char_p),
                ('nv_max', ctypes.c_int),
                ('nv', ctypes.c_int),
                ('na', ctypes.c_int),
                ('v', ctypes.POINTER(ctypes.POINTER(cVertex))),
                ('index', ctypes.c_void_p),
                ('v_size', ctypes.c_int),
                ('a_size', ctypes.c_int)]


class VertexData(ctypes.Structure):
    _fields_ = [("rhs", ctypes.c_double),
                ("pi", ctypes.c_double),
                ('v_num', ctypes.c_int)]


class ArcData(ctypes.Structure):
    _fields_ = [("low", ctypes.c_double),
                ("cap", ctypes.c_double),
                ("cost", ctypes.c_double),
                ("x", ctypes.c_double)]


def _create_graph(v_size, a_size):
    """Create a graph object."""
    p = ctypes.POINTER(cGraph)
    memory = _GLPK.glp_create_graph(v_size, a_size)
    return ctypes.cast(memory, p)


class Graph(object):

    def __init__(self):
        self._vdata = VertexData
        self._adata = ArcData
        self.graph_ptr = _create_graph(ctypes.sizeof(self._vdata),
                                       ctypes.sizeof(self._adata))

    ##################################################
    #         MODIFY GRAPH TOPOLOGY METHODS          #
    ##################################################

    def erase_graph(self):
        """Clear the current graph."""
        _GLPK.glp_erase_graph(self.graph_ptr,
                             self.graph_ptr[0].v_size,
                             self.graph_ptr[0].a_size)

    def add_vertices(self, num):
        """Add num vertices to the graph."""
        _GLPK.glp_add_vertices(self.graph_ptr, num)

    def add_edge(self, base_num, dest_num):
        """Add an edge to the graph."""
        self.assert_has_node(base_num)  # Prevent errors from glpapi15.c
        self.assert_has_node(dest_num)  # at lines 250/253
        _GLPK.glp_add_arc(self.graph_ptr,
                         ctypes.c_int(base_num),
                         ctypes.c_int(dest_num))

    def add_edges(self, edge_iter):
        """
        Adds edges in a batch to the graph.

        edge_iter should be an iterable with items of the form

            ((i, j), {'cap': cap, 'cost': cost, 'low': low})

        where i is the tail node and j is the head node of the edge, cap is
        the edge capacity, cost is the edge cost, and low is the minimum flow
        across the edge.

        The default is 0 for low and cost, and INT_MAX for cap if not
        specified. The entire dictionary can be ommited, in which case the
        item is allowed to be simply (i, j).
        """
        fovgraph.add_edges(self, edge_iter)

    ##################################################
    #          CHECK GRAPH TOPOLOGY METHODS          #
    ##################################################

    @property
    def num_nodes(self):
        """Return the number of nodes in the graph."""
        return self.graph_ptr[0].nv

    def has_node(self, num):
        """Check whether the graph has the given node or not."""
        return 0 < num <= self.num_nodes

    def assert_has_node(self, num):
        """Raise IndexError if the graph does not have the given node."""
        if not self.has_node(num):
            if not num:
                raise IndexError("Node indeces are 1-based.")
            raise IndexError("Node index %d exceeds node count" % num)

    def has_edge(self, edge):
        """Check whether the graph has the given edge or not."""
        #import pdb; pdb.set_trace()
        i, j = edge
        if not (self.has_node(i) and self.has_node(j)):
            return False
        ptr = self.graph_ptr[0].v[i]
        return edge in self.get_out_edges(ptr)

    def assert_has_edge(self, edge):
        if not self.has_edge(edge):
            raise KeyError("Graph does not contain (%d, %d)" % edge)

    ##################################################
    #     GRAPH DATA MODIFICATION/ACCESS METHODS     #
    ##################################################

    def clear_demand(self):
        """Set all node demand to 0."""
        for nodep in self.iter_node_pts():
            self.set_demand(nodep[0].i, 0)

    def set_demand(self, nx, value):
        """Set the demand for a node given its index."""
        self.assert_has_node(nx)  # Necessary to prevent seg fault!
        self._set_demand_unsafe(nx, value)

    def _set_demand_unsafe(self, nx, value):
        """
        Set the demand for a node without checking bounds.

        Can cause a segmentation fault!
        """
        nodep = self.graph_ptr[0].v[nx]  # --> Potential segfault!
        data = self._get_node_data_struct(nodep)
        data.rhs = value

    def set_edge_properties(self, edge, low=None, cap=None, cost=None):
        """Set the data properties for an edge."""
        self.assert_has_node(edge[0])
        self.assert_has_node(edge[1])
        self._set_edge_properties_unsafe(edge, low, cap, cost)

    def _set_edge_properties_unsafe(self, edge, low=None, cap=None, cost=None):
        """
        Set the edge properties without checking node bounds.

        Can cause a segmentation fault!
        """
        data = self.get_edge_data(edge)
        if low:
            data.low = low
        if cap:
            data.cap = cap
        if cost:
            data.cost = cost

    def get_edge_data(self, edge):
        """Get the data struct of an edge."""
        self.assert_has_edge(edge)
        np1 = self.graph_ptr[0].v[edge[0]]
        for edgep in self.get_out_edge_ptrs(np1):
            if edge[1] == edgep[0].head[0].i:
                return self._get_edge_data_struct(edgep)
        raise KeyError("(%d, %d) is not in the graph" % edge)

    def get_node_data(self, node):
        """Get the node data struct."""
        self.assert_has_node(node)
        node_p = self.graph_ptr[0].v[node]
        return self._get_node_data_struct(node_p)


    def _get_node_data_struct(self, node_pointer):
        """Return the vdata struct associated with the node data."""
        data = node_pointer[0].data
        return ctypes.cast(data, ctypes.POINTER(self._vdata))[0]

    def _get_edge_data_struct(self, edge_pointer):
        """Return the adata struct associated with the edge data."""
        data = edge_pointer[0].data
        return ctypes.cast(data, ctypes.POINTER(self._adata))[0]

    ##################################################
    #                GRAPH ALGORITHMS                #
    ##################################################

    def mincost_okalg(self):
        """
        Run the mincost algorithm.

        This code has been adapted from the C version found in the _GLPK
        manual.
        """
        sol = ctypes.c_double(0)
        ret = _GLPK.glp_mincost_okalg(self.graph_ptr,
                                     self._vdata.rhs.offset,
                                     self._adata.low.offset,
                                     self._adata.cap.offset,
                                     self._adata.cost.offset,
                                     ctypes.byref(sol),
                                     self._adata.x.offset,
                                     self._vdata.pi.offset)
        if ret:
            retcodes = {
                10: "No primal feasible solution",
                18: "Problems with data",
                19: "Integer overflow",
                5: "Program failure; report to <bug-glpk@gnu.org>"}
            if ret == 10:
                raise ValueError("No primal feasible solution!")
            raise RuntimeError("Mincost failed with code %d: %s" %
                               (ret, retcodes[ret]))
        flowvec = {}
        for edge_pt in self.iter_edge_pts():
            i = edge_pt[0].tail[0].i
            j = edge_pt[0].head[0].i
            flow = self._get_edge_data_struct(edge_pt).x
            if flow:
                try:
                    flowvec[i][j] = flow
                except KeyError:
                    flowvec[i] = {j: flow}
        return flowvec, sol.value

    def _extract_v_num(self):
        """
        Get a dictionary of {node-index: v_num}.

        Used by weak_comp, strong_comp and topological_sort.
        """
        return {node_p[0].i: self._get_node_data_struct(node_p).v_num
                for node_p in self.iter_node_pts()}

    def weak_comp(self):
        """Calculate the number of weakly connected components."""
        n = _GLPK.glp_weak_comp(self.graph_ptr, self._vdata.v_num.offset)
        comps = self._extract_v_num()
        res = [[] for i in xrange(n)]
        for i, g in comps.items():
            res[g-1].append(i)
        return n, res

    def strong_comp(self):
        """Calculate the number of strongly connected components."""
        n = _GLPK.glp_strong_comp(self.graph_ptr, self._vdata.v_num.offset)
        comps = self._extract_v_num()
        res = [[] for i in xrange(n)]
        for i, g in comps.items():
            res[g-1].append(i)
        return n, res

    def topological_sort(self):
        """
        Calculate a topological sorting of the vertices.

        Raises value error if there are any cycles in the graph.
        """
        n = _GLPK.glp_top_sort(self.graph_ptr, self._vdata.v_num.offset)
        if n:
            raise ValueError("Graph has cycles so can't sort!")
        return self._extract_v_num()

    ##################################################
    #                ITERATOR METHODS                #
    ##################################################

    def iter_nodes(self, data=False):
        """Iterate over all the nodes in the graph."""
        for node_pt in self.iter_node_pts():
            node = node_pt[0]
            if data:
                d = self._get_node_data_struct(node_pt)
                yield (node.i, {'demand': d.rhs, 'name': node.name})
            else:
                yield node.i

    def iter_edges(self, data=False):
        """Iterate over all the edges in the graph."""
        for edge_pt in self.iter_edge_pts():
            edge = (edge_pt[0].tail[0].i, edge_pt[0].head[0].i)
            if data:
                d = self._get_edge_data_struct(edge_pt)
                yield (edge, {'cap': d.cap, 'cost': d.cost, 'low': d.low})
            else:
                yield edge

    def iter_node_pts(self):
        """Iterate over all the node pointers in the graph."""
        return (self.graph_ptr[0].v[i + 1]
                for i in xrange(self.graph_ptr[0].nv))

    def iter_edge_pts(self):
        """Iterate over all the edge pointers in the graph."""
        return itertools.chain(*(self.get_out_edge_ptrs(node_ptr)
                                 for node_ptr in self.iter_node_pts()))

    def get_out_edge_ptrs(self, node_ptr):
        """Iterate over the pointers of the outgoing edges from node."""
        a = node_ptr[0].out
        while True:
            try:
                a[0]
            except ValueError:  # NULL pointer access
                break
            yield a
            a = a[0].t_next

    def get_out_edges(self, node_ptr, data=False):
        """Iterate over the outgoing edges from node."""
        for ptr in self.get_out_edge_ptrs(node_ptr):
            ret = (ptr[0].tail[0].i, ptr[0].head[0].i)
            if data:
                ret += (ctypes.cast(self._adata, ptr[0].data),)
            yield ret

    ##################################################
    #               DIMACS I/O METHODS               #
    ##################################################

    @classmethod
    def read_graph(cls, filename):
        """
        Load a graph from a text file.

        The format is as specified in :attr:`write_graph`.
        """
        graph = cls()
        _GLPK.glp_read_graph(graph.graph_ptr,
                             filename)
        return graph

    def write_graph(self, filename):
        """
        Write the graph to file.

        The file created by the routine glp_write_graph is a plain text file,
        which contains the following information:

        nv na
        i[1] j[1]
        i[2] j[2]
        . . .
        i[na] j[na]

        where: nv is the number of vertices (nodes); na is the number of
        arcs; i[k], k = 1, . . . , na, is the index of tail vertex of arc k;
        j[k], k = 1, . . . , na, is the index of head vertex of arc k.

        """
        stdout = GLPKStdout(True)
        if _GLPK.glp_write_graph(self.graph_ptr, filename):
            raise RuntimeError(stdout.read_last())

    @classmethod
    def read_mincost(cls, filename):
        """Load a graph from a DIMACS file."""
        graph = cls()
        stdout = GLPKStdout(True)
        if _GLPK.glp_read_mincost(graph.graph_ptr,
                                  graph._vdata.rhs.offset,
                                  graph._adata.low.offset,
                                  graph._adata.cap.offset,
                                  graph._adata.cost.offset,
                                  str(filename)):
            raise RuntimeError(stdout.read_last())
        return graph

    def write_mincost(self, filename):
        """Write the minimum cost problem to a DIMACS file."""
        stdout = GLPKStdout(True)
        if _GLPK.glp_write_mincost(self.graph_ptr,
                                   self._vdata.rhs.offset,
                                   self._adata.low.offset,
                                   self._adata.cap.offset,
                                   self._adata.cost.offset,
                                   str(filename)):
            raise RuntimeError(stdout.read_last())

def is_null_p(pt):
    """Check whether a pointer is null."""
    return ctypes.cast(pt, ctypes.c_void_p).value != None
