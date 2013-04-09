
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
            raise KeyError("%r is already in graph!" % node)
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

    def is_directed(self):
        """
        Whether the graph is directed or not.
        """
        return self._is_directed

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

    NODE_RADIUS = 5

    def __init__(self, canvas, **kw):
        self.canvas = canvas
        super(TkGraph, self).__init__(**kw)

    def create_node(self, node):
        """
        Create a node.

        :param node: a tuple ``(x, y)`` of canvas coordinates.
        """
        super(TkGraph, self).create_node(node)
        x, y = node
        r = TkGraph.NODE_RADIUS
        node = self.canvas.create_oval(
            x - r, y - r, x + r, y + r,
            width=1, fill="black", outline="white")

    def create_edge(self, node1, node2, length):
        """
        Create an edge.

        :param node1: tuple of canvas coordinates ``(x1, y1)`` for first node
        :param node2: tuple of canvas coordinates ``(x2, y2)`` for second node
        """
        super(TkGraph, self).create_edge(node1, node2, length, tag='node')
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
        im = Image.open(bgfilename)
        width, height = im.size
        cwidth = min(width, self.root.winfo_screenwidth() - 200)
        cheight = min(height, self.root.winfo_screenheight() - 200)
        self.root.minsize(cwidth, cheight)

        self.dir_var = Tkinter.IntVar()
        self.make_widgets(width, height, cwidth, cheight, bgfilename)

        self.startnode_id = None
        self.scrollmode = False

        super(ImageGraph, self).__init__(image=im,
                                         canvas=self.canvas,
                                         directed=True)

    def start(self):
        self.root.mainloop()

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
        frame.pack()
        self.vscroll = Tkinter.Scrollbar(frame)
        self.vscroll.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)
        self.hscroll = Tkinter.Scrollbar(frame)
        self.hscroll.pack(side=Tkinter.BOTTOM, fill=Tkinter.X)
        self.canvas = Tkinter.Canvas(frame,
                                     bg="white",
                                     yscrollcommand=self.vscroll.set,
                                     xscrollcommand=self.hscroll.set)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.mouse_click)
        self.vscroll.config(command=self.canvas.yview)
        self.hscroll.config(command=self.canvas.xview,
                            orient=Tkinter.HORIZONTAL)
        self.photoimage = ImageTk.PhotoImage(file=bg)
        self.bg = self.canvas.create_image(0, 0, image=self.photoimage,
                                              anchor="nw")
        self.canvas.config(height=cheight,
                           width=cwidth,
                           scrollregion=(0,0,width, height))
        self.root.bind("<4>", self.roll_wheel)
        self.root.bind("<5>", self.roll_wheel)


if __name__ == "__main__":
    app = ImageGraph()
    app.start()
