import networkx as nx
import sqlite3

SEPTA_DB = "septa.db"
OUTPUT = "septa-results.csv"

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
            dbfile, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = self.connection.cursor()
    
    # Build the node list as origin,departure-time and
    # destination,arrival-time pairs
    cursor.execute('SELECT DISTINCT origin, departure '
                   'FROM septa')
    nodes = map(tuple, cursor.fetchall())
    cursor.execute('SELECT DISTINCT destination, arrival '
                   'FROM septa')
    nodes.extend(map(tuple, cursor.fetchall()))
    
    # Use sorting to insert waiting links of the form
    #      ('xxx', 12:00:00) -> ('xxx', 12:03:00)
    # ensuring the links are only among consecutive nodes
    nodes = sorted(set(nodes))
    graph = {}
    for i, node in enumerate(nodes):
        cursor.execute('SELECT destination, arrival, type'
                       'WHERE origin = ? AND departure = ?',
                       node)
        dests, arrs, types = zip(*cursor.fetchall())
        costs = [(arr - node[1]).seconds for arr in arrs]
        dapairs = map(tuple, zip(dests, arrs))
        graph[node] = set(zip(dapairs, costs, types))

        try:  # This entire block is for the waiting links
            name, time = nodes[i+1]  # Reason for sorting
        except IndexError:
            pass
        else:
            if name == node[0]:
                cost = (time - node[1]).seconds
                t = 'wait'
                graph[node].add((nodes[i+1], cost, t))
    return graph
    
def guido_to_nx(graph):
    """
    Convert a python graph to a networkx directed graph.
    
    Input should be a mapping of the form
    
        {
          source-node:
              set({
                    [dest-node-1, cost, type],
                    ... ,
                    [dest-node-2, cost, type],
              })
        }
    
    which (by construction) exactly matches that of make_guido_graph
    """
    G = nx.Digraph()
    for node in graph:
        for tgt, cost, t in graph[node]:
            G.add_edge(node, tgt, weight=cost, kind=t)
    return G

def simplex(graph, demand, capacity):
    """
    Run the network simplex algorithm on a graph.
    
    :param graph: a networkx Digraph
    :param demand: a mapping {node: demand}. Note that demands should sum 
                   to 0. If a node isn't in ``demand``, it is assumed to
                   have 0 demand
    :param capacity: a mapping {node: capacity}. If a node isn't in
                     ``capaciy`` it is assumed to have unlimited capacity.

    :returns: a double mapping ``flow_dict`` of the form 
              ``{base: {target1: flow, target2: flow}}`` so that
              ``flow_dict[node1][node2]`` is the flow across edge 
              ``(node1, node2)``
    """
    for node in graph.nodes_iter():
        graph.node[node]['demand'] = demand.get(node, 0)
        try:
            graph.node[node]['capacity'] = capacity[node]
        except KeyError:
            pass
    return graph.network_simplex()

def flow_to_csv(flow, filename):
    nodes = list(flow)
    with open(filename, 'wt') as f:
        f.write(',' + ','.join('"%s"' % str(n) for n in nodes))
        f.write('\n')
        for node in nodes:
            f.write('"%s",' % str(node))
            f.write(','.join(int(flow[node].get(n2, -1))
                             for n2 in nodes))
                f.write('\n')    

if __name__ == "__main__":
    print "Starting"
    graph = make_guido_graph(SEPTA_DB)
    print "Loaded the DB into a graph"
    nxgraph = guido_to_nx(graph)
    print "Made the NetworkX graph"
    flow = simplex(nxgraph)
    print "Found the optimal flow"
    flow_to_csv(flow, OUTPUT)
    print "Wrote the results to %s" % OUTPUT
