import networkx as nx
import sqlite3

SEPTA_DB = "septa.db"

def make_guido_graph(dbfile):
    connection = sqlite3.connect(
            dbfile, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = self.connection.cursor()
    cursor.execute('SELECT DISTINCT origin, departure '
                   'FROM septa')
    nodes = cursor.fetchall()
    cursor.execute('SELECT DISTINCT destination, arrival '
                   'FROM septa')
    nodes.extend(cursor.fetchall())
    nodes = sorted(set(nodes))
    
    graph = {}
    for i, node in enumerate(nodes):
        cursor.execute('SELECT destination, arrival, type'
                       'WHERE origin = ? AND departure = ?',
                       node)
        dests, arrs, types = zip(*cursor.fetchall())
        costs = [(arr - node[1]).seconds for arr in arrs]
        
        graph[node] = set(zip(zip(dests, arrs), costs, types))
        try:
            name, time = nodes[i+1]
        except IndexError:
            pass
        else:
            if name == node[0]:
                cost = (time - node[1]).seconds
                t = 'wait'
                graph[node].add((nodes[i+1], cost, t))

    return graph
    
def guido_to_nx(graph):
    G = nx.Digraph()
    for node in graph:
        for tgt, cost, t in graph[node]:
            G.add_edge(node, tgt, weight=cost, kind=t)
    return G

def simplex(graph, demand, capacity):
    for node in graph.nodes_iter():
        graph.node[node]['demand'] = demand.get(node, 0)
        try:
            graph.node[node]['capacity'] = capacity[node]
        except KeyError:
            pass
    return graph.network_simplex()
