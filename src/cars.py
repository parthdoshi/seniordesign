
import numpy as np
import collections
import heapq

from itertools import count

class PriorityQueue(object):

    """
    A priority queue based on heapq.
    """

    REMOVED = '<removed-task>'  # placeholder for a removed task

    def __init__(self):
        self.heap = []  # actual data
        self.entry_finder = {}  # mapping of task ids to entries
        self.count = count()

    def add_task(self, task, priority=0):
        '''Add a new task or update the priority of an existing task'''
        if task in self.entry_finder:
            self.remove_task(task)
        id_ = next(self.count)
        entry = [priority, id_, task]
        self.entry_finder[id_] = entry
        heapq.heappush(self.heap, entry)
        return id_

    def remove_task(self, task_id):
        '''Mark an existing task as REMOVED.'''
        entry = self.entry_finder.pop(task_id)
        entry[-1] = self.REMOVED

    def pop_task(self):
        '''Remove and return the lowest priority task.'''
        while self.heap:
            priority, id_, task = heapq.heappop(self.heap)
            if task is not self.REMOVED:
                del self.entry_finder[id_]
                return task, priority
        raise IndexError('Tried to pop from an empty priority queue')

    def __getitem__(self, key):
        return self.entry_finder[key][2]

    def __contains__(self, key):
        return self.entry_finder.get(key) and (
                    self.entry_finder[key][2] != self.REMOVED)

    def __iter__(self):
        while True:
            try:
                yield self.pop_task()
            except IndexError:
                break

class CarQueue(object):

    """
    A CarQueue is a segment of road.
    
    cars are stored as deques of their paths.
    """

    def __init__(self, capacity):
        self.capacity = capacity
        self.cars = collections.deque()

    @property
    def occupancy(self):
        return len(self.cars)

    def advance(self):
        car = self.cars[0]
        dest = car[0]
        if not dest.is_full():
            car.popleft()
            cars.popleft()
            dest.append(car)
        # FIXME: routing is not dynamic at car-level

    def get_rate(self):
        return 0 + (self.occupancy > 0)
        # FIXME: no dependence on flow rate

    def get_cost(self):
        return 1 # FIXME
        
    def is_full(self):
        return len(self.cars) >= self.capacity

class CarSource(object):

    """
    A parking lot.
    """

    def __init__(self, occupancy, router, mean, stddev):
        self.occupancy = occupancy
        self.router = router
        self.arrivals = np.random.normal(mean, stddev, (occupancy, 1))

    def advance(self):
        car = self.router()
        dest = car[0]
        if not dest.is_full():
            car.popleft()
            dest.append(car)
            self.occupancy -= 1
        
class Simulation(object):

    """
    
    The graph is implemented as a dictionary of dictionaries
        {start_node : {end_node : (cost, capacity)}}
    See Guido van Rossum's thoughts at
       <http://www.python.org/doc/essays/graphs.html>
    where he suggests representing graphs as dictionaries mapping
    vertices to lists of neighbours.
    """

    def __init__(self, graph):
        self.graph = graph
        self.nodes = {}
        self.arrivals = []
        self.time = 0

    def make_graph(self, graph):
        """
        Make a CarQueue graph.
        
        Its input should be a mapping:
            
            {node: (total-demand, 
                    {target-node: (cost, capacity)})}

        where total-demand is the number of cars parked
        there (0 for non-lots), and target-nodes are the
        nodes that are directly linked to from node.
        """
        def get_router(node):
            def router(target):
                path = self.get_path(node, target)
                links = collections.deque()
                for s, t in zip(path, path[1:]):
                    links.append(self.links[(s, t)])
                return links
            return router
        self.nodes = dict((node, CarSource(val[0], get_router(node)))
                          for node, val in graph.items()
                          if val[0] > 0)
        self.arrivals = collections.deque(sorted([
                         (time, node) 
                             for node, source in self.nodes.items()
                             for time in source.arrivals]))
        self.links = dict((base, target), CarQueue(val2[1])))
                          for base, val in graph.items()
                          for target, val2 in val[1].items())
        self.graph = dict((base, target) 
                            for base, val in graph.items()
                            for target in val[1])
        

    def next_event(self):
        rates = np.arra(q.get_rate() for q in self.links)
        cum = rates.cumsum()
        tot = cum[-1]
        inc = np.random.exponential(1/tot, 1)
        next_arr = self.arrivals[0][0]
        if next_arr < self.time + inc:
            node = self.arrivals.popleft()[1]
            self.nodes[node].advance()
            self.time = next_arr
        else:
            u = np.random.random_sample() * tot
            ix = np.where(cum > u)[0][0]
            self.links(ix).advance()
            self.time += inc

    def get_path(base, target):
        """
        Find shortest path from base to target.

        (Not quite all -- only those closer than destination).

        returns a list with the nodes in order of the route.

        Dijkstra's algorithm is only guaranteed to work correctly
        when all edge lengths are positive. This code does not
        verify this property for any edges but will correctly
        compute shortest paths even for some graphs with negative
        edges.
        """
        graph = {node: {target: self.links(node, target).get_cost() 
                        for target in self.graph[node]}
        distances = {}
        parents = {}
        queue = PriorityQueue()
        queue.add_task(base, 0)

        for vertex, distance in queue:
            distances[vertex] = distance
            if vertex == destination:
                break
            for neighbor in graph.get(vertex, {}):
                cost = self[vertex][neighbor]
                if cost < 0:
                    raise ValueError("Dijkstra requires positive costs!")
                distance += cost
                if (neighbor not in distances) and (
                    neighbor not in queue or (
                        distance < queue[neighbor])):
                    queue.add_task(neighbor, distance)
                    parents[neighbor] = vertex
        par_list = [target]
        while par_list[-1] != base:
            par_list.append(parents[par_list[-1]])
        return par_list[::-1]
