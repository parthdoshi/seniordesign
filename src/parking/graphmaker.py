
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

from PIL import Image, ImageDraw
import Tkinter
import ImageTk
import tkFileDialog
import dragbox
import csv

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
            raise KeyError("%s is already in graph!" % str(node))
        self.graph[node] = {}

    def create_edge(self, node1, node2, length):
        """
        Creates a new edge.

        :param node1: first node of the edge.
        :param node2: second node of the edge.
        :param length: length or cost of the edge.
        """
        if node2 in self.graph[node1]:
            raise ValueError("%r is already in graph" % tuple(node1, node2))
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
        if self.is_directed():
            del self.graph[node2][node1]

    def is_directed(self):
        """
        Whether the graph is directed or not.
        """
        return self._is_directed

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
        self.pain_edge(node1, node2)

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
                self.paint_line(node, dest)


class PILGraph(Graph):

    NODE_RADIUS = 5

    def __init__(self, image, **kw):
        self.image = image
        self.draw = ImageDraw.Draw(image)
        super(PILGraph, self).__init__(**kw)

    def create_node(self, node):
        """
        Create a node.

        :param node: a tuple ``(x, y)`` of image coordinates.
        """
        super(PILGraph, self).create_node(node)
        x, y = node
        r = PILGraph.NODE_RADIUS
        self.draw.ellipse(
            (x - r, y - r, x + r, y + r),
            fill='black', outline='white')

    def create_edge(self, node1, node2, length):
        """
        Create an edge.

        :param node1: tuple of image coordinates ``(x1, y1)`` for first node
        :param node2: tuple of image coordinates ``(x2, y2)`` for second node
        """
        super(PILGraph, self).create_edge(node1, node2, length)
        x1, y1 = node1
        x2, y2 = node2
        if self.is_directed():
            arrow = 'last'
        else:
            arrow = 'both'
        self.draw_arrow((x1, y1, x2, y2), arrow=arrow, fill='yellow')

    def draw_arrow(self, xy, arrow='both', fill='black', width=1):
        """
        Draw an arrow between the two points.

        :param arrow: One of ``'first'``, ``'last'``, ``'both'``
        """
        import math
        def rotate(x, y, theta):
            return (math.cos(theta) * x - math.sin(theta) * y,
                    math.sin(theta) * x - math.sin(theta) * x)
        def tri(x, y, theta, scale=1):
            pts = [(0, 2), (2, 0), (0, -2)]
            pts = [rotate(i, j, theta) for i, j in pts]
            return [(x + i * scale, y + j * scale) for i, j in pts]

        self.draw.line(xy, fill, width)
        x1, y1, x2, y2 = xy
        theta = math.atan2(y2 - y1, x2 - x1)
        if arrow in {'both', 'last'}:
            self.draw.polygon(tri(x2, y2, theta, width), fill=fill)
        if arrow in {'both', 'first'}:
            self.draw.polygon(tri(x1, y1, math.pi + theta, width), fill=fill)

    def dump(self, imagefilename):
        """Save the image to a file."""
        self.image.save(imagefilename)


class ImageGraph(PILGraph, TkGraph):

    def __init__(self):
        self.root = Tkinter.Tk()
        self.root.title("graphmaker")

        message = "Select background image"
        bgfilename = tkFileDialog.askopenfilename(parent=self.root,
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
        self.make_widgets(width, height, cwidth, cheight, bgfilename)
        super(ImageGraph, self).__init__(image=im,
                                         canvas=self.canvas,
                                         directed=True)

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
        """Save the image and graph files."""
        message = "Save the graph CSV file"
        graphname = tkFileDialog.asksaveasfilename(parent=self.root,
                                                   title=message)
        if graphname:
            Graph.dump(self, graphname)
        message = "Save the image file"
        imagename = tkFileDialog.asksaveasfilename(parent=self.root,
                                                   title=message)
        if imagename:
            PILGraph.dump(self, imagename)

    def make_widgets(self, width, height, cwidth, cheight, bg):
        """Make the necessary widgets and bindings."""
        self.dir_var.set(1)
        frame = Tkinter.Frame(self.root)
        frame.pack(side=Tkinter.TOP)
        Tkinter.Checkbutton(frame,
                            text="Directed Arcs?",
                            variable=self.dir_var).pack(side=Tkinter.LEFT)
        Tkinter.Button(frame, text="Save to File", command=self.save).pack()
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

    def __init__(self):
        super(NodeMaker, self).__init__()
        self.startnode_id = None
        self.canvas.bind("<Button-1>", self.mouse_click)


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

    def __init__(self, nodefile):
        super(EdgeMaker, self).__init__()
        nodes = eval(open(nodefile).read())
        for node in nodes:
            self.create_node(node)
        self.box = dragbox.DragBox(self.canvas)
        self.box.release_hook = self.select_nodes
        self.selection = []
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
        for base, target in zip(self.selection, self.selection[1:]):
            n1 = self.get_node_center(base)
            n2 = self.get_node_center(target)
            length = self.segment_length(n1, n2)
            self.create_edge(n1, n2, length)
        self.deselect()

    def deselect(self):
        for node_id in self.selection:
            self.canvas.itemconfig(node_id, fill='black')
            self.canvas.delete('text')
            self.canvas.dtag(node_id, 'selected')
        self.selection = []


class EdgePurger(ImageGraph):

    def __init__(self, graphfile):
        super(EdgePurger, self).__init__()
        self.load_file(graphfile)
        self.selected = None
        self.canvas.bind("<Button-1>", self.mouse_click)

    def load_file(self, graphfile):
        graph = {}
        with open(graphfile, 'rb') as csvfile:
            reader =  csv.reader(csvfile)
            nodes = map(eval, next(reader)[1:])
            for line in reader:
                base = eval(line.pop(0))
                graph[base] = dict((n1, n2)
                                   for n1, n2 in zip(nodes, map(float, line))
                                   if n2 > 0)
        self.load(graph)

    def remove_edge(self, edge_id):
        """Remove an edge from the graph."""
        nodes = self.get_edge_nodes(edge_id)
        self.delete_edge(nodes)

    def get_edge_nodes(self, edge):
        """Get the nodes (as tuples) at the edge vertices."""
        x1, y1, x2, y2 = self.canvas.coords(edge)
        assert (x1, y1) in self.graph
        assert (x2, y2) in self.graph
        return (x1, y1), (x2, y2)

    def mouse_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        print "%f, %f" % (x, y)
        edges = list(self.select_items(x, y, 'edge'))
        if edges:
            self.select_edge(edges[0])
        else:
            self.deselect()
        if len(edges) > 1:
            self.root.bind('r', self.multiple_edges_callback(edges))

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
        self.selected = edge_id

    def deselect(self):
        """Deselect edge."""
        self.canvas.itemconfig('selected', fill='red', width=1)
        self.canvas.dtag('selected', 'selected')
        self.selected = None


if __name__ == "__main__":
    try:
        app = EdgePurger('graph.csv')
    except ValueError:
        pass
    else:
        app.start()
