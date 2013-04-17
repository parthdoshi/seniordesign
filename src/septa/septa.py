
from __future__ import division

import sqlite3
import pyglpk

LINK_DB = "final.db"
TABLE_NAME = "links"
DEMAND_FILE = "demand.csv"
OUTPUT = "septa-results.csv"


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
GAMETIME = 16 * 60

def main():
    # There's an if __name__ == "__main__": main() at the bottom
    import cProfile
    cProfile.run('main_sim(GAMETIME)', 'profile.stats')

def main_sim(gametime):
    print "Starting"
    graph = make_guido_graph(LINK_DB)
    print "Made the python graph."
    capacity = get_capacity()
    print "Loaded the network's capacity"
    demand = get_demand(gametime)
    print "Loaded the network's demand"
    flow = run_ook(graph, demand, capacity)
    print "Found the optimal flow, size %d" % len(flow)
    flow_to_csv(flow, OUTPUT)
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
        demand[row[0]] = sum(map(int, row[1]))
        time = gametime - 80
        for v in map(int, row[1:]):
            val = int(v / 4)
            for _ in xrange(4):
                time += 5
                try:
                    demand[(STADIUM_NODE, minutes_to_str(time))] -= val
                except KeyError:
                    demand[(STADIUM_NODE, minutes_to_str(time))] = -val
    return demand

def make_guido_graph(dbfile):
    """
    Reads in the septa database and outputs a space-time graph.

    Output is a mapping of the form

        {
          (node-name, time-object):
                  set({
                    [(node-name, time-object), cost, type],
                    ... ,
                    [(node-name, time-object), cost, type],
                  })
        }

    where one node is in the set of another node iff there is a
    direct link between them, the cost is simply the difference
    in seconds of their time coordinate, and type refers to the
    SEPTA API type to distinguish between buses, trolleys, etc.
    There is the addition of the type 'wait' for waiting links.
    """
    connection = sqlite3.connect(
            dbfile,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cursor = connection.cursor()
    # Build the initial node list as (origin,departure-time) and
    # (destination,arrival-time) pairs
    cursor.execute('SELECT DISTINCT origin, departure '
                   'FROM %s;' % TABLE_NAME)
    nodes = map(tuple, cursor.fetchall())
    cursor.execute('SELECT DISTINCT dest, arrival '
                   'FROM %s;' % TABLE_NAME)
    nodes.extend(map(tuple, cursor.fetchall()))

    # Use sorting to insert waiting links of the form
    #      ('xxx', 12:00:00) -> ('xxx', 12:03:00)
    # ensuring the links are only among consecutive nodes
    nodes = sorted(set(nodes))
    graph = {}
    stadium_nodes = []
    print "Node count: %d, starting to make edges" % len(nodes)
    for i, node in enumerate(nodes):
        cursor.execute('SELECT dest, arrival, duration, type ' +
                       'FROM %s ' % TABLE_NAME +
                       'WHERE origin=? AND departure=?;',
                       node)
        try:
            dests, arrs, costs, types = zip(*cursor.fetchall())
        except ValueError: # no values
            graph[node] = set()
            continue
        dapairs = map(tuple, zip(dests, arrs))
        graph[node] = set(zip(dapairs, costs, types))

        try:  # This entire block is for the waiting links
            next_node, time = nodes[i+1]
        except IndexError:
            pass
        else:
            if next_node == node[0]:
                cost = get_delta_mins(node[1], time)
                t = 'wait'
                graph[node].add((nodes[i+1], cost, t))

        # Now we (potentially) add the links to the stadium
        if node[0] in STADIUM_STOPS:
            cost = STADIUM_STOPS[node[0]]
            time = node[1] + cost
            raise StupidityError
            graph[node].add(((STADIUM_NODE, minutes_to_str(time)),
                             cost, 'walk'))
            stadium_nodes.append((STADIUM_NODE, minutes_to_str(time)))

    # Now add the waiting links for the stadium nodes
    new_nodes = set((STADIUM_NODE, minutes_to_str(GAMETIME + 5 * i))
                    for i in xrange(-15, 13)).difference(stadium_nodes)
    stadium_nodes.extend(new_nodes)
    stadium_nodes.sort()
    print "Node count: %d, making stadium nodes" % len(graph)
    for n1, n2 in zip(stadium_nodes, stadium_nodes[1:]):
        cost = get_delta_mins(n1[1], n2[1])
        graph[n1] = set([(n2, cost, 'wait')])
        print n1
    try:
        graph[stadium_nodes[-1]] = set()
    except IndexError:
        pass
    # Now we add the zipcode nodes
    print "Node count: %d, making zipcode nodes" % len(graph)
    cursor.execute('SELECT DISTINCT zipcode FROM stops')
    zipcodes = zip(*cursor.fetchall())[0]
    for zipcode in zipcodes:
        cursor.execute('SELECT origin, departure '
                       'FROM links '
                       'INNER JOIN stops '
                       'ON origin=stop_id '
                       'WHERE stops.zipcode=?;',
                       (zipcode,))
        graph[zipcode] = set((tuple(r), 0, 'init')
                             for r in cursor.fetchall())
        graph[zipcode].add(((STADIUM_NODE, minutes_to_str(GAMETIME - 75)),
                            1000, 'debug'))
    print "Node count: %d, finished making graph" % len(graph)
    return graph

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
        nodes.update(t[0] for t in vals)
    num_nodes = len(nodes)
    arcs = sum(map(len, graph.values()))
    glpk = pyglpk.Graph()
    glpk.add_vertices(num_nodes)
    print "Going to begin making %d nodes and %d arcs" % (num_nodes, arcs)
    nodes = sorted(nodes)
    alias = {node: i + 1 for  i, node in enumerate(nodes)}
    for node in nodes:
        if demand.get(node, 0):
            glpk.set_demand(alias[node], demand[node])
    print "Set the node demands"
    for node, i in alias.items():
        for target, cost, _ in graph[node]:  # remove .get in final
            j = alias[target]
            glpk.add_edge(i, j)
            glpk.set_edge_properties((i, j), low=0,
                                     cap=capacity.get((node, target), 90000),
                                     cost=cost)
    print "Made GLPK graph object"
    flowdict = glpk.mincost_okalg()[0]
    print "Flowdict len:%d" % len(flowdict)
    node_ids = {i + 1: node for i, node in enumerate(nodes)}
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
    nodes = list(flow)
    with open(filename, 'wt') as f:
        f.write(',' + ','.join('"%s"' % str(n) for n in nodes))
        f.write('\n')
        for node in nodes:
            f.write('"%s",' % str(node))
            f.write(','.join(str(flow[node].get(n2, ''))
                             for n2 in nodes))
            f.write('\n')

def get_delta_mins(t1, t2):
    """Return (t2 - t1) in minutes of two timestamps with format HH:MM:SS."""
    h1, m1, s1 = map(int, t1.split(':'))
    h2, m2, s2 = map(int, t2.split(':'))
    return int(60 * (h2 - h1) + m2 - m1 + (s2 - s1) / 60.0)

def minutes_to_str(mins):
    """Convert the number of minutes since midnight into a string."""
    h = int(mins / 60)
    m = mins % 60
    return "%02d:%02d:00" % (h, m)

if __name__ == "__main__":
    main()
