
from __future__ import division

import sqlite3
import tempfile
import os
import subprocess
import re
import datetime

LINK_DB = "final.db"
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
    capacity = get_capacity(graph)
    print "Loaded the network's capacity"
    demand = get_demand(gametime)
    print "Loaded the network's demand"
    flow = simplex(graph, demand, capacity)
    print "Found the optimal flow"
    flow_to_csv(flow, OUTPUT)
    print "Wrote the results to %s" % OUTPUT

def get_capacity(graph):
    """Load the capacity of each link."""
    capacity = {}
    for node, neighbors in graph.items():
        capacity[node] = {node2: 100  # FIXME
                          for node2, _, _ in neighbors}
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
                    demand[(STADIUM_NODE, time)] -= val
                except KeyError:
                    demand[(STADIUM_NODE, time)] = -val
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
                   'FROM links_temp;')
    nodes = map(tuple, cursor.fetchall())
    cursor.execute('SELECT DISTINCT dest, arrival '
                   'FROM links_temp;')
    nodes.extend(map(tuple, cursor.fetchall()))

    # Use sorting to insert waiting links of the form
    #      ('xxx', 12:00:00) -> ('xxx', 12:03:00)
    # ensuring the links are only among consecutive nodes
    nodes = sorted(set(nodes))
    graph = {}
    stadium_nodes = []
    print "Node count: %d, starting to make edges" % len(nodes)
    for i, node in enumerate(nodes):
        cursor.execute('SELECT dest, arrival, duration, type '
                       'FROM links_temp '
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
                cost = int((time - node[1]).seconds / 60)
                t = 'wait'
                graph[node].add((nodes[i+1], cost, t))

        # Now we (potentially) add the links to the stadium
        if node[0] in STADIUM_STOPS:
            cost = STADIUM_STOPS[node[0]]
            time = node[1] + cost
            graph[node].add(((STADIUM_NODE, time), cost, 'walk'))
            stadium_nodes.append((STADIUM_NODE, time))

        if not (i+1) % 1000:
            print "Processed 1000 nodes"
    # Now add the waiting links for the stadium nodes
    stadium_nodes.sort()
    print "Node count: %d, making stadium nodes" % len(graph)
    for n1, n2 in zip(stadium_nodes, stadium_nodes[1:]):
        cost = n2[1] - n1[1]
        graph[n1] = set([(n2, cost, 'wait')])
    try:
        graph[stadium_nodes[-1]] = set()
    except IndexError:
        pass
    # Now we add the zipcode nodes
    print "Going to make zipcode nodes"
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
    print "Node count: %d, finished making graph" % len(graph)
    return graph

def simplex(graph, demand, capacity):
    """
    Run the network simplex algorithm on a graph.

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
    fd, name = tempfile.mkstemp()
    f = os.fdopen(fd, 'w', 1024 * 1024)
    node_ids = make_dimacs(graph, demand, capacity, f)
    print "Made DIMACS file %s" % name
    f.close()
    flow = run_ook(name)
    output = {}
    for i, d in flow.items():
        node = node_ids[i]
        output[node] = {node_ids[j]: f for j, f in d.items()}
    return output

def run_ook(filename):
    """
    Run the Ford-Fulkerson algorithm on a DIMACS file.

    Returns a double mapping ``flowdict`` such that ``flowdict[i][j]``
    is the amount of flow across edge ``(i, j)``.
    """
    output = subprocess.Popen(['./ook.exe', filename],
                              stdout=subprocess.PIPE)
    arcline = re.compile('arc ([0-9]+)->([0-9]+): x = +(-?[0-9]+); '
                         'lambda = +-?[0-9]+')
    flowdict = {}
    for line in output.stdout:
        m = arcline.match(line)
        try:
            src, dest, flow = map(int, m.groups())
        except AttributeError:
            continue
        try:
            flowdict[src][dest] = flow
        except KeyError:
            flowdict[src] = {dest: flow}
    return flowdict

def make_dimacs(graph, demand, capacity, filelike):
    """
    Write a DIMACS file of a graph.

    Returns a mapping of ``node_id``\ s written to the file to the
    corresponding python object.
    """
    num_nodes = len(graph)
    arcs = sum(map(len, graph.values()))
    filelike.write('p min %d %d' % (num_nodes, arcs))
    print "Going to begin writing %d nodes and %d arcs" % (num_nodes, arcs)
    nodes = sorted(graph.keys())
    for i, node in enumerate(nodes):
        if demand.get(node, 0):
            filelike.write('n %d %d' % (i, demand[node]))
        if not (i+1) % 1000:
            print "Wrote 1000 nodes"

    e = 0
    for i, node in enumerate(nodes):
        for target, cost, _ in graph[node]:
            try:
                j = nodes.index(target)
            except ValueError:  # FIXME: DYN IN FINAL VERSION??
                nodes.append(target)
                graph[node] = set()
                j = len(nodes) - 1
                #print "Node not in dict!"
            filelike.write('a %d %d 0 %d %d' %
                           (i,
                            j,
                            capacity.get((node, target), -1),
                            cost))
            e += 1
        if not e % 1000:
            print "Wrote 1000 edges"
    return dict(enumerate(nodes))

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

class TimeStamp(datetime.datetime):

    @staticmethod
    def to_str(stamp):
        return stamp.strftime("%H:%M:%S")

    @staticmethod
    def from_str(string):
        h = int(string[:2])
        h = h % 24
        string = format(h, '0>2d') + string[2:]
        return TimeStamp.strptime(string, "%H:%M:%S")

sqlite3.register_adapter(TimeStamp, TimeStamp.to_str)
sqlite3.register_converter("TimeStamp", TimeStamp.from_str)

if __name__ == "__main__":
    main()
