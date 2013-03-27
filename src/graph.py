
"""
This package provides a graph class that implements the
Dijkstra algorithm. The Dijkstra code was lifted from
code.activestate.com/recipes/119466-dijkstras-algorithm-for-shortest-paths/
posted by David Eppstein (http://www.ics.uci.edu/~eppstein/)
"""

import heapq


class PriorityQueue(object):

    """
    A priority queue based on heapq.
    """

    REMOVED = '<removed-task>'  #: placeholder for a removed task

    def __init__(self):
        self.heap = []  #: the priority sorted heap
        self.entry_finder = {}  #: mapping of tasks to entries
        self.count = 0  # used to break ties for equi-priority tasks

    def add_task(self, task, priority=0):
        '''Add a new task or update the priority of an existing task'''
        try:
            self.remove_task(task)
        except KeyError:
            pass
        entry = [priority, self.count, task]
        self.count += 1
        self.entry_finder[task] = entry
        heapq.heappush(self.heap, entry)

    def remove_task(self, task):
        '''
        Mark an existing task as REMOVED.

        :param task: The (hashable) task to remove.

        Raises ``KeyError`` if the task is not in the heap.
        '''
        # This roundabout way is necessary since heaps don't directly
        # support removing entries
        entry = self.entry_finder.pop(task)
        entry[-1] = self.REMOVED

    def pop_task(self):
        '''Remove and return the lowest priority task.'''
        while self.heap:
            priority, _, task = heapq.heappop(self.heap)
            if task is not self.REMOVED:
                del self.entry_finder[task]
                return task, priority
        raise KeyError('Tried to pop from an empty priority queue')

    def __getitem__(self, key):
        return self.entry_finder[key][2]

    def __contains__(self, key):
        return self.entry_finder.get(key) and (
                    self.entry_finder[key][2] != self.REMOVED)

    def __iter__(self):
        while True:
            try:
                yield self.pop_task()
            except KeyError:
                break


class Graph(object):

    """
    A directed graph.

    iter(graph) yields all the nodes.
    iter(graph[u]) yields all the downstream neighbours of u.
    graph[u][v] is the cost of edge (u, v).

    The graph implements a cache of calculated paths to
    reduce duplication of calculation. Memory use increases
    in exchange for speed. If you want to avoid this behaviour,
    a simple dictionary
        {start_node1 : {end_node : cost, ... , end_node : cost}
            ...
         start_nodeM : {end_node : cost, ... , end_node : cost}
    provides nearly the same functionality without the overhead.
    See Guido van Rossum's thoughts at
       <http://www.python.org/doc/essays/graphs.html>
    where he suggests representing graphs as dictionaries mapping
    vertices to lists of neighbours.

    """

    def __init__(self, graph):
        self.graph = graph

    def add_node(self, node):
        """
        Add a new node to the graph.

        :param node: any hashable object can be used as a node.
        """
        if not node in self.nodes:
            self.graph[node] = {}
        else:
            raise KeyError(repr(node) + " is already in graph!")

    def add_edge(self, start, end, cost=0):
        """
        Add a new edge to the graph.

        :param start: initial node in the edge
        :param end: final node in the edge
        :param cost: edge length. (Default 0)

        .. note:: Both ``start`` and ``end`` must already be in the
                  in the graph or the method will raise ``KeyError``
        """
        for node in (start, end):
            if node not in self.nodes:
                raise KeyError(repr(node) + " is not in the graph!")
        self.graph[start][end] = cost

    def complete(self, cost=0):
        """
        Fill in the missing arcs in the graph.

        :param cost: cost value to use for the missing nodes
        """
        for node1, neighbors in self.graph.items():
            for node2 in self.nodes:
                if node2 not in neighbors:
                    self.graph[node1][node2] = cost

    def dijkstra(self, base, dest=None):
        """
        Find shortest paths from base to any vertex.

        (Not quite all -- only those closer than destination).

        Returns distances and parents where
        distances[v] is the distance from base to v and
        parents[v] is the predecessor of v along the
        shortest path from v to base.

        Dijkstra's algorithm is only guaranteed to work correctly
        when all edge lengths are positive. This code does not
        verify this property for all edges (only the edges seen
         before the end vertex is reached), but will correctly
        compute shortest paths even for some graphs with negative
        edges, and will raise an exception if it discovers that
        a negative edge has caused it to make a mistake.
        """
        distances = {}
        parents = {}
        queue = PriorityQueue()
        queue.add_task(base, 0)

        for vertex, distance in queue:
            # The queue ensures we are iterating over the shortest
            # distance values. As soon as we find a match, we are
            # therefore guaranteed that it is the shortest distance
            distances[vertex] = distance
            if dest is not None and vertex == dest:
                return distances, parents
            for neighbor in self.graph.get(vertex, []):
                cost = self.graph[vertex][neighbor]
                if cost < 0:
                    raise ValueError("Dijkstra requires positive costs!")
                distance += cost
                if neighbor not in distances:
                    if (neighbor not in queue or distance < queue[neighbor]):
                        queue.add_task(neighbor, distance)
                        parents[neighbor] = vertex
        if dest is not None:
            raise ValueError("No path found between %r and %r" %
                             (base, dest))

    def get_shortest_path(self, origin, dest):
        """
        Find a shortest path from origin to end.

        :param origin: Initial node
        :param dest: End node

        :returns: ``(path, distance)``, where ``path`` is a list of the
                  vertices in order along the shortest path, starting with
                  ``origin`` and ending with ``dest`` and ``distance`` is
                  the total path length
        """
        distances, parents = self.dijkstra(origin, dest)
        path = [dest]
        while path[-1] != origin:
            path.append(parents[path[-1]])
        return (distances[dest], path[::-1])

    def path_length(self, path):
        """Return the length of a given path."""
        total = 0
        for node1, node2 in zip(path, path[1:]):
            total += self.graph[node1][node2]
        return total

    def get_min_distance(self, origin, dest):
        """
        Return the length of the shortest path from ``origin`` to ``dest``.
        """
        return self.get_shortest_path(origin, dest)[0]

    @property
    def nodes(self):
        """A set with all of the graph nodes."""
        return set(self.graph.keys())

    def __iter__(self):
        return iter(self.graph)

    def __getitem__(self, item):
        return self.graph[item]

    def __setitem__(self, item, val):
        self.graph[item] = val

    def __delitem__(self, item):
        del self.graph[item]
