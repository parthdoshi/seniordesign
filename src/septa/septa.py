
from __future__ import division

import sqlite3
import pyglpk

LINK_DB = "final.db"           # Path to database
TABLE_NAME = "links"           # Name of link table in database
DEMAND_FILE = "demand.csv"     # Path to demand CSV
OUTPUT = "results.csv"         # Where to output results
OVERFLOW = 60 * 24             # Cost of overflow links (0 for infinity)
GAMETIME = 19 * 60 + 5         # In minutes since midnigth

STADIUM_NODE = 0
STADIUM_STOPS = {
    21349: 4,   # 11th St & Zinkoff
    28170: 7,   # 7th St & Pattison
    31461: 9,   # 10th St & Packer Av
    29432: 9,   # 10th St & Packer Av  FS
    356: 6,     # Broad St & Pattison Av 1
    31487: 6,   # Broad St & Pattison Av 2 - FS
    363: 6,     # Pattison Av & Broad St - FS
    152: 6,     # Broad St & Hartranft St
    28169: 6,   # Pattison Av & 7th St
    }

def main():
    # There's an if __name__ == "__main__": main() at the bottom
    main_sim(GAMETIME, LINK_DB, OUTPUT)

def main_sim(gametime, dbfilename, outfilename):
    print "Starting"
    graph = make_guido_graph(dbfilename)
    print "Made the python graph."
    capacity = get_capacity()
    print "Loaded the network's capacity"
    demand = get_demand(gametime)
    print "Loaded the network's demand"
    flow = run_ook(graph, demand, capacity)
    print "Found the optimal flow, size %d" % len(flow)
    flow_to_csv(flow, outfilename)
    print "Wrote the results to %s" % OUTPUT

def get_capacity():
    """Load the capacity of each link."""
    connection = sqlite3.connect(
            LINK_DB,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cursor = connection.cursor()
    cursor.execute('SELECT origin, departure, dest, arrival, capacity ' +
                   'FROM %s;' % TABLE_NAME)
    capacity = {}
    for orig, dep, dest, arr, cap in cursor.fetchall():
        try:
            capacity[(orig, dep)][(dest, arr)] = cap
        except KeyError:
            capacity[(orig, dep)] = {(dest, arr): cap}
    return capacity

def get_demand(gametime):
    """
    Get the time and space varying demand.

    The input is CSV with eight columns and one header row:

        Zip Code,(-80:-60),(-60:-40),(-40:-20),(-20:0),(0:20),(20:40),(40:60)

    where each row indicates the number of people from each zip code arriving
    at the specified interval in minutes relative to the game start time.

    The output is a mapping ``{node: demand}``, where ``node`` is either of
    the form ``(id_, time)`` or ``"zipcode"``.
    """
    csv = [l.split(',') for l in open(DEMAND_FILE).read().split('\n') if l]
    demand = {}
    for row in csv[1:]:
        demand[row[0]] = 0
        time = gametime - 80
        for v in map(int, row[1:]):
            val = int(v / 4)
            for _ in xrange(4):
                time += 5
                node = (STADIUM_NODE, GraphMaker.minutes_to_str(time))
                try:
                    demand[node] -= val
                except KeyError:
                    demand[node] = -val
                demand[row[0]] += val
    return demand

def make_guido_graph(dbfile):
    """
    Reads in the septa database and outputs a space-time graph.
    """
    graph_maker = GraphMaker(dbfile, TABLE_NAME, OVERFLOW)
    return graph_maker.make_graph()

def run_ook(graph, demand, capacity):
    """
    Run the Ford-Fulkerson algorithm via GLPK.

    :param graph: a python graph as returned by make_guido_graph
    :param demand: a mapping {node: demand}. Note that demands should sum
                   to 0. If a node isn't in ``demand``, it is assumed to
                   have 0 demand
    :param capacity: a mapping {node: capacity}. If a node isn't in
                     ``capacity`` it is assumed to have unlimited capacity.

    :returns: a double mapping ``flow_dict`` of the form
              ``{base: {target1: flow, target2: flow}}`` so that
              ``flow_dict[node1][node2]`` is the flow across edge
              ``(node1, node2)``

    """
    nodes = set(graph.keys())
    for vals in graph.values():
        nodes.update(vals.keys())
    num_nodes = len(nodes)
    arcs = sum(map(len, graph.values()))
    glpk = pyglpk.Graph()
    glpk.add_vertices(num_nodes)
    print "Going to begin making %d nodes and %d arcs" % (num_nodes, arcs)
    alias = {node: i + 1 for  i, node in enumerate(nodes)}
    assert set(demand.keys()).issubset(nodes)
    total_demand_in = 0
    total_demand_out = 0
    for node in nodes:
        if demand.get(node, 0):
            glpk.set_demand(alias[node], demand[node])
            d = demand[node]
            if d < 0:
                total_demand_in -= d
            else:
                total_demand_out += d
    print "Set the node demands; in, out = %d, %d" % (total_demand_in, total_demand_out)
    assert total_demand_in == total_demand_out
    for node, i in alias.items():
        for target, cost in graph[node].items():
            j = alias[target]
            assert cost >= 0
            glpk.add_edge(i, j)
            glpk.set_edge_properties((i, j),
                                     low=0,
                                     cap=capacity.get((node, target), 90000),
                                     cost=cost)
    w = glpk.weak_comp()[0]
    print "Made GLPK graph object with %d weak components" % w
    if w > 1:
        raise ValueError("The graph is not weakly connected!")
    flowdict = glpk.mincost_okalg()[0]
    print "Flowdict len:%d" % len(flowdict)
    node_ids = {node: i for i, node in alias.items()}
    output = {}
    for i, d in flowdict.items():
        node = node_ids[i]
        output[node] = {node_ids[j]: f for j, f in d.items()}
    return output

def flow_to_csv(flow, filename):
    """
    Write a flow vector to a CSV.

    The input ``flow`` is a double mapping ``{node-i : {node_j : flow_ij}}``
    The output format is

        \  N1  N2  N3  ...  Nk
       N1  x   x   x        x
       N2  x   x   x        x
       N3  x   x   x        x
      ...
       Nk  x   x   x        x

    where the entry in the i-th row and j-th column represents the flow
    from the i-th to the j-th node.

    Entries not in the flow vector are left blank.
    """
    nodes = sorted(list(flow))
    with open(filename, 'wt') as f:
        f.write(',' + ','.join('"%s"' % str(n) for n in nodes))
        f.write('\n')
        for node in nodes:
            f.write('"%s",' % str(node))
            f.write(','.join(str(flow[node].get(n2, ''))
                             for n2 in nodes))
            f.write('\n')

class GraphMaker(object):

    """
    An object to help make the Space-Time SEPTA graph.

    :param dbfilename: path to the database file with the tables of links
                       and stops
    :param table: name of the table with the links. [The stops table is
                  assumed to be ``stops``
    :param overflow: if nonzero, the graph will have "overflow"
                     edges from the zipcode to the stadium at this cost.
                     (Default 0)

    The graph it creates takes the form:

        {
          (node-name, time-object):
                  {
                    (node-name, time-object): cost,
                    ... ,
                    (node-name, time-object): cost,
                  }
        }

    where one node is in the set of another node iff there is a
    direct link between them, the cost is simply the difference
    in minutes of their time coordinate.
    """

    def __init__(self, dbfilename, table, overflow=0):
        self.table = table
        self._connection = sqlite3.connect(dbfilename,
                                        detect_types=sqlite3.PARSE_DECLTYPES)
        self.cursor = self._connection.cursor()
        self.overflow = overflow
        self.stadium_nodes = {}
        self.zip_nodes = {}
        self.septa_nodes = {}

    def make_graph(self):
        """Create the entire graph."""
        self.load_nodes()
        self.load_edges()
        graph = {}
        graph.update(self.stadium_nodes)
        graph.update(self.zip_nodes)
        graph.update(self.septa_nodes)
        return graph

    def execute(self, cmd, query_args=tuple()):
        """Shortcut to execute queries."""
        self.cursor.execute(cmd, query_args)

    def fetchall(self):
        """Shortcut to cursor.fetchall"""
        return self.cursor.fetchall()

    def load_nodes(self):
        """Load all the nodes into their respective attributes."""
        # First the stadium nodes
        self.stadium_nodes = {
            (STADIUM_NODE, self.minutes_to_str(GAMETIME + 5 * i)) : {}
            for i in xrange(-15, 13)}
        self.execute(
            'SELECT dest, arrival FROM %s ' % self.table +
            'WHERE dest IN (%s)' % ','.join('?' * len(STADIUM_STOPS)),
            STADIUM_STOPS.keys())
        for dest, arrival in self.fetchall():
            time = self.minutes_to_str(self.get_delta_mins(arrival) +
                                       STADIUM_STOPS[dest])
            self.stadium_nodes[(STADIUM_NODE, time)] = {}
        # Now the zipcode nodes -- each node is a **string**
        self.execute('SELECT DISTINCT zipcode FROM stops')
        self.zip_nodes = {r[0]: {} for r in self.fetchall()}
        # Finally the SEPTA nodes
        self.execute('SELECT DISTINCT origin, departure '
                     'FROM %s' % self.table)
        nodes = map(tuple, self.fetchall())
        self.execute('SELECT DISTINCT dest, arrival '
                     'FROM %s' % self.table)
        nodes.extend(map(tuple, self.fetchall()))
        self.septa_nodes = {n: {} for n in nodes}

    def load_edges(self):
        """Populate the three dicts with edges."""
        # First the stadium-stadium edges
        nodes = sorted(self.stadium_nodes.keys())
        for n1, n2 in zip(nodes, nodes[1:]):
            t = self.get_delta_mins(n2[1], n1[1])
            self.stadium_nodes[n1][n2] = t
        # now the zipcode-septa edges
        for zipcode, tgs in self.zip_nodes.items():
            self.execute('SELECT origin, departure '
                         'FROM %s ' % self.table +
                         'INNER JOIN stops '
                         'ON origin=stop_id '
                         'WHERE stops.zipcode=?;',
                         (zipcode,))
            tgs.update({(o, d): 0 for o, d in self.fetchall()})
        # now the SEPTA-SEPTA and SEPTA-Stadium edges
        nodes = sorted(self.septa_nodes.keys())
        for i, node in enumerate(nodes):
            self.execute('SELECT dest, arrival, duration ' +
                         'FROM %s ' % self.table +
                         'WHERE origin=? AND departure=?',
                         node)
            try:
                dests, arrs, costs = zip(*self.fetchall())
            except ValueError: # no values
                continue
            dapairs = map(tuple, zip(dests, arrs))
            self.septa_nodes[node].update(zip(dapairs, costs))

            try:  # This entire block is for the waiting links
                next_stop, time = nodes[i+1]
            except IndexError:
                pass
            else:
                if next_stop == node[0]:
                    cost = self.get_delta_mins(time, node[1])
                    self.septa_nodes[node][nodes[i+1]] =  cost

            if node[0] in STADIUM_STOPS:  # This block is for SEPTA-Stadium
                cost = STADIUM_STOPS[node[0]]
                time = self.minutes_to_str(self.get_delta_mins(node[1]) +
                                           cost)
                self.septa_nodes[node][(STADIUM_NODE, time)] = cost
        # finally, the zipcode-stadium edges
        if self.overflow:
            first_stadium = min(self.stadium_nodes.keys())
            for tgts in self.zip_nodes.values():
                tgts[first_stadium] = self.overflow

    @staticmethod
    def get_delta_mins(t2, t1="00:00:00"):
        """Return (t2 - t1) in minutes of two timestamps with format HH:MM:SS."""
        h1, m1, s1 = map(int, t1.split(':'))
        h2, m2, s2 = map(int, t2.split(':'))
        return int(60 * (h2 - h1) + m2 - m1 + (s2 - s1) / 60.0)

    @staticmethod
    def minutes_to_str(mins):
        """Convert the number of minutes since midnight into a string."""
        h = int(mins / 60)
        m = mins % 60
        return "%02d:%02d:00" % (h, m)


if __name__ == "__main__":
    main()
