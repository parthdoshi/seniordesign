
from __future__ import division

import csv
import networkx as nx
import sqlite3

CONN = sqlite3.connect('final.db')
CURSOR = CONN.cursor()

RESULTS_FILE = "results-to-stadium.csv"
OUTPUT = "congestion.csv"
STADIUM_NODE = 0
GAMETIME = 19 * 60 + 5  # In minutes since midnigth

def main():
    flows = load_flows(RESULTS_FILE)
    zips = [n for n in flows if isinstance(n, int)]
    nxg, dest = guido_to_nx(flows)
    comps = nx.weakly_connected_components(nxg)
    comps.sort(key=len)
    print "%d weakly connected components" % len(comps)
    print "Sizes: " + ', '.join('%d' % len(c) for c in comps)
    print "Comp1: {%r, %r}:" % tuple(comps[0]),
    print flows[19145][(152, u'18:54:00')]
    print "Comp2: {%r, %r}:" % tuple(comps[1]),
    print flows[19114][(31487, u'18:54:00')]
    return
    congestion = {}
    for z in zips:
        congs = []
        try:
            for path in get_paths(nxg, z, dest):
                congs.append(get_congestion(nxg, path))
        except nx.NetworkXNoPath:
            raise ValueError("No path from %d to %r" % (z, dest))
        congestion[z] = sum(congs) / len(congs)
    with open(OUTPUT, 'w') as f:
        for z, c in congestion.items():
            f.write('%d,%f\n' % (z, c))


def load_flows(results_file):
    flows = {}
    with open(results_file, 'rb') as csvfile:
        reader = csv.reader(csvfile)
        header = map(eval, next(reader)[1:])
        for line in reader:
            node = eval(line[0])
            body = line[1:]
            flows[node] = {h: b
                           for h, b in zip(header, body) if b}
    return flows

def guido_to_nx(graph):
    """
    Convert a simple python graph into a networkx Digraph.

    :param graph: a mapping of the form ``node: {target: flow}``,
                  where ``(node, target)`` is an edge in the graph with
                  flow ``flow``.
    :returns: :class:`networkx.Digraph`
    """
    G = nx.DiGraph()
    for node in graph:
        for tgt, flow in graph[node].items():
            if isinstance(node, int):
                G.add_edge(node, tgt)
            elif tgt[0] == STADIUM_NODE:
                G.add_edge(node, tgt,
                           weight=get_delta_mins(tgt[1], node[1]))
            else:
                G.add_edge(node, tgt, flow=float(flow),
                           weight=get_delta_mins(tgt[1], node[1]))
    stadium_nodes = [n for n in G.nodes_iter()
                     if isinstance(n, tuple) and n[0] == STADIUM_NODE]
    stadium_nodes.sort()
    for n1, n2 in zip(stadium_nodes, stadium_nodes[1:]):
        if not G.has_edge(n1, n2):
            G.add_edge(n1, n2, weight=get_delta_mins(n2[1], n1[1]))
    return G, stadium_nodes[-1]

def get_delta_mins(t2, t1="00:00:00"):
    """Return (t2 - t1) in minutes of two timestamps with format HH:MM:SS."""
    h1, m1, s1 = map(int, t1.split(':'))
    h2, m2, s2 = map(int, t2.split(':'))
    return int(60 * (h2 - h1) + m2 - m1 + (s2 - s1) / 60.0)


def get_paths(graph, zipcode, dest):
    return nx.all_shortest_paths(graph, zipcode, dest,
                                    'weight')

def get_congestion(graph, path):
    tot_cap = 0
    tot_flow = 0
    for n1, n2 in zip(path, path[1:]):
        if isinstance(n1, int):
            continue
        CURSOR.execute("SELECT baseline, capacity, duration FROM links "
                       "WHERE origin=? AND departure=? AND dest=? "
                       "AND arrival=? limit 1;",
                       n1 + n2)
        try:
            baseline, capacity, duration = CURSOR.fetchone()
        except TypeError:
            continue
        flow = baseline + graph[n1][n2].get("flow", 0)
        assert baseline < capacity
        tot_flow += flow * duration
        tot_cap += capacity * duration
    return tot_flow / tot_cap

def minutes_to_str(mins):
    """Convert the number of minutes since midnight into a string."""
    h = int(mins / 60)
    m = mins % 60
    return "%02d:%02d:00" % (h, m)

if __name__ == "__main__":
    main()
