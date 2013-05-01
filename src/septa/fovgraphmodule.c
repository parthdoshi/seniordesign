
#include <Python.h>
#include <stdint.h>
#include <glpk.h>

PyObject* addressof;
PyObject* EMPTY_TUP;
PyObject* EMPTY_DICT;

typedef struct { double low, cap, cost, x; } a_data;

/**********************************************************
 *  Extract the glp_graph located in pygraph.graph_ptr    */
int extract_glp_graph(PyObject* pygraph, glp_graph** graph){
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
  Py_DECREF(addr_obj);
  if (*graph == NULL)
    return 0;
  return 1;
}


/**********************************************************
 * Convert a dictionary entry to a double.
 *
 * int dict_key_to_double(PyObject* dictionary, const char* key, double* d)
 *
 * Roughly equivalent to:
 *     *d = (double) dictionary[key]
 *
 * Returns   Means
 *   -1         KeyError (PyErr set, *d unchanged)
 *    0         Success
 *    1         Exception (PyErr set, *d unchanged)
 */
int dict_key_to_double(PyObject* dictionary, const char* key, double* d) {
  PyObject* temp;
  double tempd;
  if (!(temp = PyString_FromString(key))){
    return 1;
  }

  if (!(temp = PyObject_GetItem(dictionary, temp))) {
    if (PyErr_ExceptionMatches(PyExc_KeyError)){
      return -1;
    }
    return 1;
  }

  tempd = PyLong_AsDouble(temp);
  if (tempd == -1 && PyErr_Occurred()){
    PyErr_Clear();
    tempd = (double) PyInt_AsLong(temp);
    if (tempd == -1 && PyErr_Occurred())
      return 1;
  }
  *d = tempd;
  return 0;
}

/**********************************************************
 * Check that all dictionary keys are in a given set of strings
 *
 * int check_dict_keys(PyObject* dict, const char** kws)
 *
 * dict should be the Python dictionary object and kws should be
 * a NULL terminated array of strings.
 *
 * Returns   Means
 *   -1         Exception (PyErr set)
 *    0         Failure: some keys not in kws
 *    1         Success: all keys in kws
 */

int check_dict_keys(PyObject* dict, const char** kws){
  int i;
  const char* kw;
  PyObject *temp, *allowedkeylist, *key;
  Py_ssize_t pos = 0;

  /* Build a python list of strings with the allowed keys*/
  if (!(allowedkeylist = PyList_New(0))){
    return -1;
  }
  for(kw = kws[i = 0]; kw; kw=kws[i++]){
    if (!(temp = PyString_FromString(kw))){
      return -1;
    }
    if (PyList_Append(allowedkeylist, temp) == -1){
      return -1;
    }
  }

  /* iterate over the dictionary checking each key*/
  while (PyDict_Next(dict, &pos, &key, &temp)) {
    i = PySequence_Contains(allowedkeylist, key);
    if (i == -1 || i == 0)
      return i;
  }
  return 1;
}

static PyObject* fov_add_edges(PyObject* self, PyObject* args){

  glp_graph* graph;
  int head, tail;
  glp_arc *a;

  PyObject *pygraph, *edge_iter, *edge, *edge_data;
  static const char *kws[] = {"low", "cap", "cost", NULL};

  /* Parse args. Need a graph object and an iterable */
  if (!PyArg_ParseTuple(args, "OO", &pygraph, &edge_iter)) {
    PyErr_SetString(PyExc_TypeError,
		    "add_edges() takes exactly 2 arguements");
    return NULL;
  }

  if (!extract_glp_graph(pygraph, &graph))  // pygraph is borrowed
    return NULL;

  edge_iter = PyObject_GetIter(edge_iter);  // edge_iter is borrowed
  if (!edge_iter)
    return NULL;


  /* Now loop through the iterable, adding the edges */
  PyObject *temp;
  int t;
  while ((edge = PyIter_Next(edge_iter))){
    /* Convert the item into a tuple */
    temp = PySequence_Tuple(edge);  // temp is always a new reference
    Py_DECREF(edge);
    edge = temp;
    if (edge == NULL) {
      PyErr_SetString(PyExc_TypeError, "Each item must be a sequence!");
      return NULL;
    }

    /* Split the tuple into a (tail, head) pair and a data dict */
    if (!PyArg_ParseTuple(edge, "(ii)O", &tail, &head, &edge_data)) {
      t = PyArg_ParseTuple(edge, "ii", &tail, &head);
      if (!t) {
	Py_DECREF(edge);
	PyErr_SetString(PyExc_TypeError,
			"Each edge must be a 2-sequence of integers!");
	return NULL;
      }
      PyErr_Clear();
      edge_data = EMPTY_DICT;
    }  // edge_data is a borrowed reference
    Py_DECREF(edge);

    /****** ADD THE ARC TO THE GRAPH *******/
    a = glp_add_arc(graph, tail, head);

    /* Now parse the data dict into the arc data */
    double *temp_d;
    temp_d = (double *) ((char *) a->data + offsetof(a_data, low));
    switch (dict_key_to_double(edge_data, "low", temp_d)){
    case -1: // KeyError
      PyErr_Clear();
      break;
    case 1:
      return NULL;
    }

    temp_d = (double *) ((char *) a->data + offsetof(a_data, cap));
    switch (dict_key_to_double(edge_data, "cap", temp_d)){
    case -1: // KeyError
      PyErr_Clear();
      break;
    case 1:
      return NULL;
    }

    temp_d = (double *) ((char *) a->data + offsetof(a_data, cost));
    switch (dict_key_to_double(edge_data, "cost", temp_d)){
    case -1: // KeyError
      PyErr_Clear();
      break;
    case 1:
      return NULL;
    }

    switch (check_dict_keys(edge_data, kws)){
    case 0:
      PyErr_SetString(PyExc_KeyError,
		      "Edges only support 'low', 'cap', and 'cost' data");
    case -1:
      return NULL;
    }
  }
  if (PyErr_Occurred())  // Check reason for stopping iteration
    return NULL;

  /* Cleanup */
  Py_RETURN_NONE;
}


/*  MODULE DEFINITION STUFF */

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

  EMPTY_DICT = PyDict_New();
  EMPTY_TUP = PyTuple_New(0);

  (void) Py_InitModule("fovgraph", GraphMethods);
}
