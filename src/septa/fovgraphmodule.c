
#include <Python.h>
#include <stdint.h>
#include <glpk.h>

PyObject* addressof;

typedef struct { double low, cap, cost, x; } a_data;

int extract_glp_graph(PyObject* pygraph, glp_graph** graph){
  /* Extract the glp_graph located in pygraph.graph_ptr */
  PyObject* ctypes_ptr;
  PyObject* graph_obj;
  PyObject* addr_obj;

  ctypes_ptr = PyObject_GetAttrString(pygraph, "graph_ptr");
  if (ctypes_ptr == NULL)
    return 0;

  graph_obj = PyObject_GetAttrString(ctypes_ptr, "contents");
  Py_DECREF(ctypes_ptr);
  if (graph_obj == NULL)
    return 0;

  addr_obj = PyObject_CallFunction(addressof, "O", graph_obj);
  Py_DECREF(graph_obj);
  if (addr_obj == NULL)
    return 0;

  *graph = (glp_graph*) PyLong_AsVoidPtr(addr_obj);
  if (*graph == NULL)
    return 0;
  Py_DECREF(addr_obj);
  return 1;
}


static PyObject* fov_add_edges(PyObject* self, PyObject* args){

  glp_graph* graph;
  int head, tail;
  glp_arc *a;
  a_data data = {.low=0, .cap=0, .cost=0};

  PyObject *pygraph, *edge_iter, *edge, *edge_data;
  PyObject *empty_dict = PyDict_New();
  PyObject *empty_tup = PyTuple_New(0);
  static char *kws[] = {"low", "cap", "cost", NULL};

  if (!PyArg_ParseTuple(args, "OO", &pygraph, &edge_iter))
    return NULL;
  edge_iter = PyObject_GetIter(edge_iter);
  if (edge_iter == NULL)
    return NULL;
  if (!extract_glp_graph(pygraph, &graph))
    return NULL;
  Py_DECREF(pygraph);

  while ((edge = PyIter_Next(edge_iter))){
    /* Split the item into a (tail, head) pair and a data dict */
    if (!PyArg_ParseTuple(edge, "(ii)O", &tail, &head, &edge_data)) {
      if (!PyArg_ParseTuple(edge, "ii", &tail, &head)) {
	  PyErr_SetString(PyExc_TypeError,
			  "each edge must be a 2-sequence of integers!");
	  return NULL;
      }
      edge_data = empty_dict;
      Py_INCREF(edge_data);
    }
    /* Now parse the data dict into a struct, with default values */
    data.low = 0;
    data.cap = (double) INT_MAX; //  cap = MAXINT???;
    data.cost = 0;

    if (!PyArg_ParseTupleAndKeywords(empty_tup, edge_data, "|iii", kws,
				     &data.low, &data.cap, &data.cost)) {
      PyErr_SetString(PyExc_KeyError,
		      "Edges only support 'low', 'cap', and 'cost' data");
      return NULL;
    }
    /* And add the arc and data to the graph */
    Py_DECREF(edge);
    Py_DECREF(edge_data);
    Py_DECREF(empty_tup);
    Py_DECREF(empty_dict);
    a = glp_add_arc(graph, tail, head);
    memcpy(a->data, &data, sizeof(data));
  }
  Py_DECREF(edge_iter);
  if (PyErr_Occurred())
    return NULL;
  Py_DECREF(edge_iter);
  Py_RETURN_NONE;
}

static PyMethodDef GraphMethods[] = {
    {"add_edges",  fov_add_edges, METH_VARARGS,
     "add_edges(graph, edges)\nAdd edges to the graph object."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

PyMODINIT_FUNC
initfovgraph(void) {
  PyObject* ctypes = PyImport_ImportModule("ctypes");
  if (ctypes == NULL)
    return;
  addressof = PyObject_GetAttrString(ctypes, "addressof");
  Py_DECREF(ctypes);
  (void) Py_InitModule("fovgraph", GraphMethods);
}
