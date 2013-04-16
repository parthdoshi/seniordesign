
"""
This module runs a script to generate the parking lot graph.

It displays an image with all the parking lots and offers two
modes. Under node mode, clicks create new nodes, indicated by
a yellow dot. In edge mode, two clicks create an edge between
nodes.

1.5: Add color guides to selection process
1.4: Automate clearing of entry name
1.3: Prevent empty string from being used as name
1.2: Fixed issue with scrolling coordinates
1.1: Added keyboard/mouse bindings to ease navigation
1.0: Basic Functionality: click & dump
"""

from __future__ import division
from PIL import Image

import Tkinter
import ImageTk
import tkFileDialog
import tkMessageBox
import dragbox
import csv

import xml.etree.ElementTree as ET

class Graph(object):

    def __init__(self, directed=True):
        self.graph = {}
        self._is_directed = directed

    def create_node(self, node):
        """
        Creates a new node.

        :param node: Any hashable object
        """
        if node in self.graph:
            raise KeyError("%s is already in graph!" % repr(node))
        self.graph[node] = {}

    def delete_node(self, node):
        """Removes a node from the graph."""
        del self.graph[node]
        for targets in self.graph.values():
            targets.pop(node, None)

    def create_edge(self, node1, node2, length):
        """
        Creates a new edge.

        :param node1: first node of the edge.
        :param node2: second node of the edge.
        :param length: length or cost of the edge.
        """
        if node2 in self.graph[node1]:
            raise ValueError("%s is already in graph" % repr((node1, node2)))
        self.graph[node1][node2] = length
        if not self.is_directed():
            self.graph[node2][node1] = length

    def delete_edge(self, edge):
        """
        Removes an edge from the graph.

        :param edge: An iterable of the form ``(node1, node2)``
        """
        node1, node2 = edge
        del self.graph[node1][node2]
        if not self.is_directed():
            del self.graph[node2][node1]

    def is_directed(self):
        """
        Whether the graph is directed or not.
        """
        return self._is_directed

    def load_filename(self, filename):
        """
        Create a graph from a csv file and load it.
        """
        graph = {}
        with open(filename, 'rb') as csvfile:
            reader =  csv.reader(csvfile)
            nodes = map(eval, next(reader)[1:])
            for line in reader:
                base = eval(line.pop(0))
                graph[base] = dict((n1, n2)
                                   for n1, n2 in zip(nodes, map(float, line))
                                   if n2 > 0)
        self.load(graph)

    def load(self, graph):
        """
        Replace the current graph with another one.

        No checking is done on graph -- it is assumed to be well formed.
        """
        self.graph = graph

    def dump(self, graphfilename):
        """Write the graph to a file."""
        nodes = list(self.graph)
        with open(graphfilename, 'wt') as f:
            f.write(',' + ','.join('"%s"' % str(n) for n in nodes))
            f.write('\n')
            for node in nodes:
                f.write('"%s",' % str(node))
                f.write(','.join(format(self.graph[node].get(n2, -1), ".3f")
                                 for n2 in nodes))
                f.write('\n')

    def __iter__(self):
        return iter(self.graph)

    def __getitem__(self, item):
        return self.graph[item]

    def __delitem__(self, item):
        del self.graph[item]

    def __setitem__(self, item, value):
        self.graph[item] = value


class TkGraph(Graph):

    NODE_RADIUS = 10

    def __init__(self, canvas, **kw):
        self.canvas = canvas
        super(TkGraph, self).__init__(**kw)

    def create_node(self, node):
        """
        Create a node.

        :param node: a tuple ``(x, y)`` of canvas coordinates.
        """
        super(TkGraph, self).create_node(node)
        self.paint_node(node)

    def paint_node(self, node):
        """Draw the node on the canvas."""
        x, y = node
        r = TkGraph.NODE_RADIUS
        self.canvas.create_oval(
            x - r, y - r, x + r, y + r,
            width=1, fill="black", outline="white", tag='node')

    def create_edge(self, node1, node2, length):
        """
        Create an edge.

        :param node1: tuple of canvas coordinates ``(x1, y1)`` for first node
        :param node2: tuple of canvas coordinates ``(x2, y2)`` for second node
        """
        super(TkGraph, self).create_edge(node1, node2, length)
        self.paint_edge(node1, node2)

    def paint_edge(self, node1, node2):
        """Draw an edge on the canvas."""
        if not self.is_directed():
            arrow = 'both'
        else:
            arrow = 'last'
        x1, y1 = node1
        x2, y2 = node2
        self.canvas.create_line((x1, y1, x2, y2),
                                arrow=arrow,
                                fill="red",
                                tag='edge')

    def load(self, graph):
        """
        Replace the current graph.

        Nodes must be tuples of their coordinates.
        """
        super(TkGraph, self).load(graph)
        self.canvas.delete('node')
        self.canvas.delete('edge')
        for node in graph:
            self.paint_node(node)
        for node in graph:
            for dest in graph[node]:
                self.paint_edge(node, dest)

    def save_ps(self, filename):
        """
        Save the canvas contents to a postscript file.
        """
        self.canvas.postscript(file=filename, colormod='color')


class SVGGraph(Graph):

    NODE_RADIUS = "10"

    def __init__(self, width, height, **kw):
        super(SVGGraph, self).__init__(**kw)
        self.tree = ET.parse("template.svg")
        self.svg = self.tree.getroot()
        self.svg.set('width', str(width))
        self.svg.set('height', str(height))
        tri = ET.SubElement(self.svg, 'marker', id="triangle",
                            viewBox="0 0 10 10", refX="0", refY="5",
                            markerUnits="strokeWidth", markerWidth="4",
                            markerHeight="3", orient="auto")
        ET.SubElement(tri, 'path', d="M 0 0 L 10 5 L 0 10 z")
        self.svg.append(tri)
        self.scene = {}

    def create_node(self, node):
        """
        Add a node to the graph.

        :param node: Should be a pair of coordinates ``(x, y)``
        """
        super(SVGGraph, self).create_node(node)
        self.append_node(node)

    def append_node(self, node):
        if node in self.scene:
            raise KeyError("%s is already in the scene" % repr(node))
        self.scene[node] = ET.SubElement(self.svg, 'circle',
                                         {'cx': str(node[0]),
                                          'cy': str(node[1]),
                                          'r': self.NODE_RADIUS,
                                          'class': 'node'})

    def create_edge(self, node1, node2, length):
        """
        Creates a new edge.

        :param node1: first node of the edge.
        :param node2: second node of the edge.
        """
        super(SVGGraph, self).create_edge(node1, node2, length)
        self.append_edge(node1, node2)

    def append_edge(self, node1, node2):
        if (node1, node2) in self.scene:
            raise KeyError("%s is already in the scene" %
                           repr((node1, node2)))
        self.scene[(node1, node2)] = ET.SubElement(self.svg, 'line',
                                                   {'x1': str(node1[0]),
                                                    'y1':str(node1[1]),
                                                    'x2':str(node2[0]),
                                                    'y2':str(node2[1]),
                                                    'class':'edge'})

    def draw_polygon(self, polygon):
        """Draw a polygon on the svg."""
        points = ["%d,%d" % p for p in polygon]
        ET.SubElement(self.svg, 'polygon',
                      {'points': ' '.join(points),
                       'class': 'lot'})

    def load(self, graph):
        """
        Replace the current graph.
        """
        super(SVGGraph, self).load(graph)
        self.clear()
        for node in graph:
            self.append_node(node)
        for node in graph:
            for n2 in graph[node]:
                self.append_edge(node, n2)

    def clear(self):
        """Clears the current drawing."""
        for _, elem in self.scene.items():
            if elem.get('class') in ('node', 'edge'):
                self.svg.remove(elem)

    def delete_edge(self, edge):
        """Remove an edge from the graph."""
        super(SVGGraph, self).delete_edge(edge)
        elem = self.scene[edge]
        self.svg.remove(elem)
        del self.scene[edge]

    def delete_node(self, node):
        """Remove a node from the graph."""
        super(SVGGraph, self).delete_node(node)
        elem = self.scene[node]
        self.svg.remove(elem)
        del self.scene[node]

    def save_svg(self, filename):
        with open(filename, 'w') as f:
            f.write('<?xml version="1.0"? standalone="no">\n')
            f.write('<?xml-stylesheet href="styles.css" type="text/css"?>\n')
            f.write('<!DOCTYPE svg PUBLIC"-//W3C//DTD SVG 1.1//EN" '
                    '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n')
            self.tree.write(f, encoding='utf-8', xml_declaration=False)

class ImageGraph(SVGGraph, TkGraph):

    """
    ImageGraph Base class.

    This class provides the following features:

    - Background Image prompt
    - Autosave
    - Directed Checkbox
    - Load Graph
    - Save Graph
    - Save PS
    - Save SVG (broken)
    """

    def __init__(self):
        self.root = Tkinter.Tk()
        self.root.title("graphmaker")

        message = "Select background image"
        types = [('images', '.png'), ('images', '.jpg'),
                 ('images', '.jpeg'), ('all files', '*')]
        bgfilename = tkFileDialog.askopenfilename(parent=self.root,
                                                  filetypes=types,
                                                  title=message)
        if not bgfilename:
            raise ValueError("Invalid background filename")
        im = Image.open(bgfilename)
        width, height = im.size
        cwidth = min(width, self.root.winfo_screenwidth())
        cheight = min(height, self.root.winfo_screenheight() - 200)
        self.root.geometry("%dx%d" % (cwidth, cheight))
        self.root.minsize(cwidth, cheight)
        self.dir_var = Tkinter.IntVar()
        self.autosave_var = Tkinter.IntVar()
        self.make_widgets(width, height, bgfilename)
        super(ImageGraph, self).__init__(width=width,
                                         height=height,
                                         canvas=self.canvas,
                                         directed=True)
        self.root.after(1000 * 60, self.autosave)

    def start(self):
        self.root.mainloop()

    @staticmethod
    def segment_length(n1, n2):
        """Compute the length of a segment."""
        x1, y1 = n1
        x2, y2 = n2
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** .5

    def get_node_center(self, node_id):
        """Computes the center of a node."""
        x1, y1, x2, y2 = self.canvas.coords(node_id)
        return int(.5 * (x1 + x2)), int(.5 * (y1 + y2))

    def is_directed(self):
        """Whether the graph is directed or not."""
        return self.dir_var.get()

    def select_items(self, x, y, tag):
        """Select the items close to (x ,y) with tag."""
        nodes = set(self.canvas.find_overlapping(x-5, y-5, x+5, y+5))
        nodes.remove(self.bg)
        if tag is not None:
            nodes.intersection_update(self.canvas.find_withtag(tag))
        return nodes

    def roll_wheel(self, event):
        if event.num == 4:
            self.canvas.yview('scroll', -1, 'units')
        elif event.num == 5:
            self.canvas.yview('scroll', 1, 'units')
        elif event.num == 6:
            self.canvas.xview('scroll', 1, 'units')
        elif event.num == 7:
            self.canvas.xview('scroll', -1, 'units')

    def save(self):
        """Open a dialog to save the graph file."""
        message = "Save the graph CSV file"
        types = [('csv files', '.csv'), ('all files', '*')]
        graphname = tkFileDialog.asksaveasfilename(parent=self.root,
                                                   filetypes=types,
                                                   title=message)
        if graphname:
            Graph.dump(self, graphname)
            tkMessageBox.showinfo("Success", "Saved graph to %s" % graphname)

    def load_file(self):
        """Open a dialog to load a graph from file."""
        message = "Select the graph to load"
        types = [('csv files', '.csv'), ('all files', '*')]
        graphname = tkFileDialog.askopenfilename(parent=self.root,
                                                 filetypes=types,
                                                 title=message)
        if graphname:
            self.load_filename(graphname)

    def autosave(self):
        if self.autosave_var.get():
            Graph.dump(self, "autosave.csv")
        self.root.after(60 * 1000, self.autosave)

    def save_ps_file(self):
        message = "Select where to save the file"
        types = [('postscript files', '.ps'), ('all files', '*')]
        imagename = tkFileDialog.asksaveasfilename(parent=self.root,
                                                   filetypes=types,
                                                   title=message)
        if imagename:
            self.save_ps(imagename)
            tkMessageBox.showinfo("Success", "Image saved to %s" % imagename)

    def save_svg_file(self):
        message = "Select where to save the file"
        types = [('svg files', '.svg'), ('all files', '*')]
        imagename = tkFileDialog.asksaveasfilename(parent=self.root,
                                                   filetypes=types,
                                                   title=message)
        if imagename:
            self.save_svg(imagename)
            tkMessageBox.showinfo("Success", "Image saved to %s" % imagename)


    def make_widgets(self, width, height, bg):
        """Make the necessary widgets and bindings."""
        self.dir_var.set(1)
        self.topframe = Tkinter.Frame(self.root)
        self.topframe.pack(side=Tkinter.TOP)
        Tkinter.Checkbutton(self.topframe,
                            variable=self.autosave_var,
                            text="Autosave?").pack(side=Tkinter.LEFT)
        Tkinter.Checkbutton(self.topframe,
                            text="Directed Arcs?",
                            variable=self.dir_var).pack(side=Tkinter.LEFT)
        Tkinter.Button(self.topframe, text="Load Graph File",
                       command=self.load_file).pack(side=Tkinter.LEFT)
        Tkinter.Button(self.topframe, text="Save Graph to File",
                       command=self.save).pack(side=Tkinter.LEFT)
        Tkinter.Button(self.topframe, text="Save PS to File",
                       command=self.save_ps_file).pack(side=Tkinter.LEFT)
        Tkinter.Button(self.topframe, text="Save SVG to File",
                       command=self.save_svg_file).pack(side=Tkinter.LEFT)
        frame = Tkinter.Frame(self.root)
        frame.pack(fill='both', expand=True)
        self.vscroll = Tkinter.Scrollbar(frame)
        self.vscroll.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)
        self.hscroll = Tkinter.Scrollbar(frame)
        self.hscroll.pack(side=Tkinter.BOTTOM, fill=Tkinter.X)
        self.canvas = Tkinter.Canvas(frame,
                                     bg="white",
                                     scrollregion=(0,0,width, height),
                                     yscrollcommand=self.vscroll.set,
                                     xscrollcommand=self.hscroll.set)
        self.canvas.pack(fill='both', expand=True)
        self.vscroll.config(command=self.canvas.yview)
        self.hscroll.config(command=self.canvas.xview,
                            orient=Tkinter.HORIZONTAL)
        self.photoimage = ImageTk.PhotoImage(file=bg)
        self.bg = self.canvas.create_image(0, 0, image=self.photoimage,
                                              anchor="nw")
        self.root.bind("<4>", self.roll_wheel)
        self.root.bind("<5>", self.roll_wheel)


class NodeMaker(ImageGraph):

    """
    Useful for adding nodes to graphs.

    This class defines the following additional feature:

    - Mouse-click mapped to node or edge creation intelligently
    - K-Key = delete selected node
    """

    def __init__(self):
        super(NodeMaker, self).__init__()
        self.startnode_id = None
        self.canvas.bind("<Button-1>", self.mouse_click)
        self.root.bind("k", self.kill_node)

    def kill_node(self, _):
        """Remove the selected node, if any."""
        if self.startnode_id:
            self.delete_node(self.get_node_center(self.startnode_id))
            self.canvas.delete(self.startnode_id)
            self.startnode_id = None

    def create_edge_handle(self, node_id):
        """Process a click to create an edge."""
        if self.startnode_id is None:
            self.startnode_id = node_id
            self.canvas.itemconfigure(node_id, fill="red")
            return
        # If we already have a startnode, we need to make an edge
        startnode = self.get_node_center(self.startnode_id)
        node = self.get_node_center(node_id)
        length = self.segment_length(startnode, node)
        try:
            self.create_edge(startnode, node, length)
        except ValueError:
            pass
        else:
            line = self.canvas.find_all()[-1]  # NOT THREAD SAFE!
            self.root.after(500,
                    lambda: self.canvas.itemconfigure(line, fill="yellow"))
        self.canvas.itemconfigure(self.startnode_id, fill='black')
        self.startnode_id = None

    def mouse_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        nodes = self.select_items(x, y, 'node')
        if not nodes and not self.startnode_id:  # Clicked on a new area
            self.create_node((x, y))
        elif nodes:
            def dist(node_id):
                xx, yy = self.get_node_center(node_id)
                return self.segment_length((xx, yy), (x, y))
            node_id = min(nodes, key=dist)
            self.create_edge_handle(node_id)
        else: # cancel selection
            self.canvas.itemconfigure(self.startnode_id, fill='black')
            self.startnode_id = None

class EdgeMaker(ImageGraph):

    """
    This class provides the following features:

    - Dragbox bound to Mouse-1
    - Cycles Checkbox
    - R-Key = rotate selection labels
    - A-Key = Create edges in selection
    - D-Key = Deselect nodes
    - F-Key = Flip (reverse) selection labels
    """

    def __init__(self):
        super(EdgeMaker, self).__init__()
        self.box = dragbox.DragBox(self.canvas)
        self.box.release_hook = self.select_nodes
        self.selection = []
        self.cycles = Tkinter.IntVar()
        Tkinter.Checkbutton(self.topframe,
                            text="Complete Cycles?",
                            variable=self.cycles).pack(side=Tkinter.LEFT)
        self.root.bind("r", lambda e: self.rotate_labels())
        self.root.bind("a", lambda e: self.apply_edges())
        self.root.bind("d", lambda e: self.deselect())
        self.root.bind("f", lambda e: self.flip_labels())

    def select_nodes(self, box):
        additions = set(self.canvas.find_enclosed(*box))
        additions.difference_update(self.selection)
        additions.intersection_update(self.canvas.find_withtag('node'))
        self.selection.extend(additions)
        for node_id in self.selection:
            self.canvas.itemconfig(node_id, fill='white')
            self.canvas.addtag_withtag('selected', node_id)
        self.label_selection()

    def label_selection(self):
        self.canvas.delete('text')
        for i, node_id in enumerate(self.selection):
            self.label_node(node_id, str(i))

    def label_node(self, node_id, label):
        x, y = self.get_node_center(node_id)
        self.canvas.create_text(x, y, text=label, tag='text')

    def rotate_labels(self):
        self.selection[:] = self.selection[1:] + [self.selection[0]]
        self.label_selection()

    def flip_labels(self):
        self.selection.reverse()
        self.label_selection()

    def apply_edges(self):
        if self.cycles.get():
            pairs = zip(self.selection,
                        self.selection[1:] + [self.selection[0]])
        else:
            pairs = zip(self.selection, self.selection[1:])
        for base, target in pairs:
            n1 = self.get_node_center(base)
            n2 = self.get_node_center(target)
            length = self.segment_length(n1, n2)
            try:
                self.create_edge(n1, n2, length)
            except ValueError:  # Edge already exists
                pass
        self.deselect()

    def deselect(self):
        for node_id in self.selection:
            self.canvas.itemconfig(node_id, fill='black')
            self.canvas.delete('text')
            self.canvas.dtag(node_id, 'selected')
        self.selection = []


class EdgePurger(ImageGraph):

    """
    This class provides the following features:

    - Mouse-1 bound to select/deselect edge
    - K-Key = Delete (kill) the selected edges
    - R-Key = Cycle through nearby edges
    """
    def __init__(self):
        super(EdgePurger, self).__init__()
        self.selected = None
        self.canvas.bind("<Button-1>", self.mouse_click)
        self.root.bind("k", self.remove_edge)

    def remove_edge(self, _):
        """Remove an edge from the graph."""
        if self.selected:
            self.delete_edge(self.selected[1])
            self.canvas.delete(self.selected[0])
            self.root.bind('r', lambda e: 0)
            self.deselect()

    def get_edge_nodes(self, edge):
        """Get the nodes (as tuples) at the edge vertices."""
        x1, y1, x2, y2 = self.canvas.coords(edge)
        self.canvas.create_text(x2, y2, text='X', tag="vanishing",
                                fill='white')
        self.root.after(1000, lambda: self.canvas.delete("vanishing"))
        assert (x1, y1) in self.graph
        assert (x2, y2) in self.graph[(x1, y1)]
        return (x1, y1), (x2, y2)

    def mouse_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        edges = list(self.select_items(x, y, 'edge'))
        if edges:
            self.select_edge(edges[0])
        else:
            self.deselect()
        if len(edges) > 1:
            self.root.bind('r', self.multiple_edges_callback(edges))
        else:
            self.root.bind('r', lambda e: 0)

    def multiple_edges_callback(self, edges):
        """Create a callback to rotate the selected edge."""
        def callback(_):
            edges[:] = edges[1:] + [edges[0]]
            self.select_edge(edges[0])
        return callback

    def select_edge(self, edge_id):
        """Select an edge."""
        self.deselect()
        self.canvas.addtag_withtag('selected', edge_id)
        self.canvas.itemconfig(edge_id, fill='white', width=3)
        self.selected = (edge_id, self.get_edge_nodes(edge_id))

    def deselect(self):
        """Deselect edge."""
        self.canvas.delete("vanishing")
        self.canvas.itemconfig('selected', fill='red', width=1)
        self.canvas.dtag('selected', 'selected')
        self.selected = None


if __name__ == "__main__":
    import sys
    sys.argv.append('')
    kind = {'purger': EdgePurger,
            'edgemaker': EdgeMaker,
            'nodemaker': NodeMaker,
            'plain': ImageGraph}.get(sys.argv[1], ImageGraph)
    try:
        app = kind()
    except ValueError:
        pass
    else:
        app.start()
