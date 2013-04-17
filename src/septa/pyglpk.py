

"""
Library to interface with glpk graph
"""

import ctypes
import itertools

PATH_TO_SO = '/usr/local/lib/libglpk.so'
GLPK = ctypes.CDLL(PATH_TO_SO)

class VertexData(ctypes.Structure):
    _fields_ = [("rhs", ctypes.c_double),
                ("pi", ctypes.c_double)]

class ArcData(ctypes.Structure):
    _fields_ = [("low", ctypes.c_double),
                ("cap", ctypes.c_double),
                ("cost", ctypes.c_double),
                ("x", ctypes.c_double)]


def create_graph(v_size, a_size):
    """Create a graph object."""
    p = ctypes.POINTER(cGraph)
    memory = GLPK.glp_create_graph(v_size, a_size)
    return ctypes.cast(memory, p)

class Graph(object):

    def __init__(self):
        self._vdata = VertexData
        self._adata = ArcData
        self.graphp = create_graph(ctypes.sizeof(self._vdata),
                                   ctypes.sizeof(self._adata))


    def erase_graph(self):
        """Clear the current graph."""
        GLPK.glp_erase_graph(self.graphp,
                             self.graphp[0].v_size,
                             self.graphp[0].a_size)

    def add_vertices(self, num):
        """Add num vertices to the graph."""
        GLPK.glp_add_vertices(self.graphp, ctypes.c_int(num))

    def add_edge(self, base_num, dest_num):
        """Add an edge to the graph."""
        GLPK.glp_add_arc(self.graphp,
                         ctypes.c_int(base_num),
                         ctypes.c_int(dest_num))

    def clear_demand(self):
        """Set all node demand to 0."""
        for nodep in self.iter_nodes():
            self.set_demand(nodep, 0)

    def set_demand(self, nodep, value):
        """Set the demand for a node, given its pointer."""
        data = self.node_data(nodep)
        data.rhs = value
#        val = ctypes.c_double(value)
#        ctypes.memmove(
#            ctypes.cast(ctypes.c_char_p, nodep.value.data) +
#                           self._vdata.rhs.offset,
#            ctypes.byref(val),
#            ctypes.sizeof(ctypes.c_double))

    def set_edge_properties(self, edgep, low=None, cap=None, cost=None):
        """Set the data properties for an arc."""
        data = self.edge_data(edgep)
        if low:
            data.low = low
        if cap:
            data.cap = cap
        if cost:
            data.cost = cost
#        if (a_low >= 0)
#            memcpy((char *)a->data + a_low, &low, sizeof(double));
#        if (a_cap >= 0)
#            memcpy((char *)a->data + a_cap, &cap, sizeof(double));
#        if (a_cost >= 0)
#            memcpy((char *)a->data + a_cost, &cost, sizeof(double))

    def mincost_okalg(self):
        """Run the mincost algorithm."""
        sol = ctypes.c_double(0)
        ret = GLPK.glp_mincost_okalg(self.graphp,
                                     self._vdata.rhs.offset,
                                     self._adata.low.offset,
                                     self._adata.cap.offset,
                                     self._adata.cost.offset,
                                     ctypes.byref(sol),
                                     self._adata.x.offset,
                                     self._vdata.pi.offset)
        if ret:
            raise RuntimeError("Mincost failed with code %d" % ret)
        flow = {}
        for edge_pt in self.iter_edges():
            i = edge_pt[0].tail[0].i
            j = edge_pt[0].head[0].i
            try:
                flow[i][j] = self.edge_data(edge_pt).x
            except KeyError:
                flow[i] = {j: self.edge_data(edge_pt).x}
        return flow, sol.value

    def iter_nodes(self):
        """Iterate over all the node pointers in the graph."""
        return (self.graphp[0].v[i + 1]
                for i in xrange(self.graphp.value.nv))

    def iter_edges(self):
        """Iterate over all the edge pointers in the graph."""
        itertools.chain(self.get_out_edges(node[0])
                        for node in self.iter_nodes())

    def get_out_edges(self, node):
        """Iterate over the outgoing edges from node."""
        a = node.out
        while True:
            try:
                a[0]
            except ValueError:  # NULL pointer access
                break
            yield a
            a = a[0].t_next

    def node_data(self, node_pointer):
        """Return the vdata struct associated with the node data."""
        data = node_pointer[0].data
        return ctypes.cast(data, ctypes.POINTER(self._vdata))

    def edge_data(self, edge_pointer):
        """Return the adata struct associated with the edge data."""
        data = edge_pointer[0].data
        return ctypes.cast(data, ctypes.POINTER(self._adata))


def is_null_p(pt):
    """Check whether a pointer is null."""
    return ctypes.cast(pt, ctypes.c_void_p).value != None


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

cArc._fields_ = [('tail', cVertex),
                 ('head', cVertex),
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


