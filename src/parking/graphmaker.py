
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

import Tkinter
import ImageTk
import tkMessageBox

class App(object):

    def __init__(self, backgroundfile):
        self.root = Tkinter.Tk()
        self.root.title("graphmaker")
        frame = Tkinter.Frame(self.root)
        frame.pack()
        self.root.bind("d", self.focus_entry)
        self.root.bind("e", self.button_click)
        self.root.bind("n", self.button_click)
        self.root.bind("<4>", self.roll_wheel)
        self.root.bind("<5>", self.roll_wheel)
        self.button = Tkinter.Button(frame, text="Node", width=50,
                                     command=self.button_click)
        self.button.pack()
        self.entry = Tkinter.Entry(frame)
        self.entry.pack(fill=Tkinter.X)
        self.entry.bind("<FocusIn>", self.clear_entry)
        self.entry.bind("<FocusOut>", self.leave_entry)
        self.entry.insert(0, "Node Name")

        self.vscroll = Tkinter.Scrollbar(frame)
        self.vscroll.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)
        self.hscroll = Tkinter.Scrollbar(frame)
        self.hscroll.pack(side=Tkinter.BOTTOM, fill=Tkinter.X)
        self.canvas = Tkinter.Canvas(frame, bg="white",
                                     width=800, height=650,
                                     yscrollcommand=self.vscroll.set,
                                     xscrollcommand=self.hscroll.set,
                                     scrollregion=(0,0,741, 766))
        self.imsize = (741.0, 766.0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.mouse_click)
        self.vscroll.config(command=self.canvas.yview)
        self.hscroll.config(command=self.canvas.xview, orient=Tkinter.HORIZONTAL)
        self.photoimage = ImageTk.PhotoImage(file=backgroundfile)
        self.image = self.canvas.create_image(0, 0, image=self.photoimage,
                                              anchor="nw")

        self.mode = "NODE"
        self.nodes = {}
        self.startnode = None
        self.names = {}

    def start(self):
        self.root.mainloop()

    def button_click(self):
        if self.mode == "NODE":
            self.mode = "EDGE"
            self.button.config(text="Edge")
        else:
            self.mode = 'NODE'
            self.button.config(text="Node")

    def clear_entry(self, event):
        if self.entry.get() == "Node Name":
            self.entry.delete(0, Tkinter.END)

    def leave_entry(self, event):
        if not self.entry.get():
            self.entry.insert(0, "Node Name")

    def focus_entry(self, event):
        self.entry.focus_set()

    def mouse_click(self, event):
        x = self.canvas.canvasx(event.x) + self.hscroll.get()[0] * self.imsize[0]
        y = self.canvas.canvasx(event.y) + self.vscroll.get()[0] * self.imsize[1]
        nodes = list(self.canvas.find_overlapping(x-5, y-5, x+5, y+5))
        nodes.remove(self.image)
        if self.mode == "NODE":
            name = self.entry.get()
            if not name:
                tkMessageBox.showerror("Invalid Name!",
                                       "Please enter a node name")
                return
            elif name in self.names.values():

                return
            elif nodes:
                tkMessageBox.showerror("Node Exists!",
                                       "Too close to an existing node!")
                return
            node = self.canvas.create_oval(x-5, y-5, x+5, y+5, width=1,
                                    fill="black", outline="white",
                                    tags=(name,))
            tid= self.canvas.create_text(x+10, y, anchor='w')
            self.canvas.insert(tid, 0, name)
            self.entry.delete(0, Tkinter.END)
            if self.root.focus_get() is not self.entry:
                self.entry.insert(0, "Node Name")
            self.nodes[node] = []
            self.names[node] = name
        elif self.mode == "EDGE" and nodes:
            def dist(node):
                x1, y1, x2, y2 = self.canvas.coords(node)
                xx = .5 * (x1 + x2)
                yy = .5 * (y1 + y2)
                return ((xx - x) ** 2 + (yy - y) ** 2) ** .5
            node = min(nodes, key=dist)
            if self.startnode is None:
                self.startnode = node
                self.canvas.itemconfigure(node, fill="red")
                return
            elif node not in self.nodes[self.startnode]:
                x1, y1, x2, y2 = self.canvas.coords(self.startnode)
                xo = .5 * (x1 + x2)
                yo = .5 * (y1 + y2)
                x1, y1, x2, y2 = self.canvas.coords(node)
                xf = .5 * (x1 + x2)
                yf = .5 * (y1 + y2)
                line = self.canvas.create_line((xo, yo, xf, yf),
                                               fill="yellow")
                self.root.after(500, lambda: self.canvas.itemconfigure(
                    line, fill="gray"))
            self.canvas.itemconfigure(self.startnode, fill="black")
            self.nodes[self.startnode].append(node)
            self.nodes[node].append(self.startnode)
            self.startnode = None

    def dump(self, outfile):
        names2nodes = dict((name, node) for node, name in self.names.items())
        names = sorted(self.names.items())
        with open(outfile, 'wt') as f:
            f.write(',' + ','.join(zip(*names)[0]))
            for name, node in names:
                f.write(name + ',')
                for _, node2 in names:
                    f.write(node2 in self.nodes[node])
                    f.write(',')
                f.write('\n')

    def roll_wheel(self, event):
        if event.num == 4:
            self.canvas.yview('scroll', -1, 'units')
        elif event.num == 5:
            self.canvas.yview('scroll', 1, 'units')
        elif event.num == 6:
            self.canvas.xview('scroll', 1, 'units')
        elif event.num == 7:
            self.canvas.xview('scroll', -1, 'units')
