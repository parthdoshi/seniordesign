
"""
Author: Felipe Ochoa
Date: 9 April 2012
Name: Tkinter Drag Box

An object to create simple drag boxes on a Tkinter Canvas.
"""

class DragBox(object):

    """
    A container object to implement a dragbox on a Tkinter Canvas.

    The only parameter it takes is the canvas object, which is the
    canvas on which to set up the box.

    It provides three hooks with its methods ``click_hook``,
    ``drag_hook``, and ``release_hook``. Each of those methods is called
    after  handling its respective event with a single positional
    parameter `coords`, which is a tuple ``(x1, y1, x2, y2)`` of the
    box's coordinates at that point.

    The default action for each method is to pass, so they may safely be
    overriden with direct assignment. I.e.,

        db = DragBox(canvas)
        db.release_hook = my_function

    where ``my_function`` takes a single parameter.

    ``DragBox`` objects have a boolean attribute ``active`` to
    determine whether it is operating or not.
    """

    def __init__(self, canvas):
        self.canvas = canvas
        self.mouse_x = 0
        self.mouse_y = 0
        self.box = canvas.create_rectangle(0, 0, 0, 0)
        canvas.itemconfig(self.box,
                          dash=(5,5),
                          fill='',
                          state='hidden',
                          outline='gray')
        self.active = True
        self.rebind()

    def coords(self, event):
        """Convert event coordinates into canvas coordinates."""
        return self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

    def rebind(self):
        """Used to reestablish the event bindings."""
        self.canvas.bind("<Button-1>", self.mouse_click, add='+')
        self.canvas.bind("<ButtonRelease-1>", self.mouse_up, add='+')
        self.canvas.bind("<B1-Motion>", self.mouse_drag, add='+')

    def mouse_click(self, event):
        if self.active:
            self.canvas._root().config(cursor='tcross')
            self.mouse_x, self.mouse_y = self.coords(event)
            self.canvas.coords(self.box, self.mouse_x, self.mouse_y,
                               self.mouse_x, self.mouse_y)
            self.canvas.itemconfig(self.box, state='normal')
            self.canvas.tag_raise(self.box, 'all')
            self.click_hook((self.mouse_x, self.mouse_y) * 2)

    def mouse_drag(self, event):
        if self.active:
            x, y = self.coords(event)
            self.canvas.coords(self.box, self.mouse_x, self.mouse_y, x, y)
            self.drag_hook((self.mouse_x, self.mouse_y, x, y))

    def mouse_up(self, event):
        if self.active:
            self.canvas._root().config(cursor='arrow')
            self.canvas.itemconfig(self.box, state='hidden')
            self.release_hook(tuple(self.canvas.coords(self.box)))

    def click_hook(self, coords):
        """Hook, called after handling mouse click event."""
        pass

    def drag_hook(self, coords):
        """Hook, called after handling the drag event."""
        pass

    def release_hook(self, coords):
        """Hook, called after handling the mouse release event."""
        pass


if __name__ == "__main__":
    import Tkinter
    root = Tkinter.Tk()
    canvas = Tkinter.Canvas(root, width=200, height=200, bg='white')
    canvas.pack()
    d = DragBox(canvas)
    def f(c): print c
    d.release_hook = f
    root.mainloop()
