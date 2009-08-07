from __future__ import division, print_function, unicode_literals, with_statement

import math
import wx
import wx.lib.wxcairo
import cairo

class Observable(object):
    def __init__(self):
        self._listeners = set()
    
    def AddListener(self, l):
        self._listeners.add(l)
        
    def RemoveListener(self, l):
        self._listeners.remove(l)

    def TriggerListeners(self, *args, **kw):
        for l in self._listeners:
            l(self, *args, **kw)

class Robot(object):
    def __init__(self, maze):
        self._maze = maze
        self._x = 2
        self._y = 3
        self._dir = 0

    def Paint(self, ctx):
        x, y = self._maze.Coordinates(self._x + .5, self._y + .5)
        ctx.translate(x, y)
        ctx.rotate(math.pi * 0.5 * self._dir)
        ctx.set_source_rgb(0, 0, 1)
        ctx.arc(0, 0, 7, 0, 2*math.pi)
        ctx.fill()
        ctx.move_to(10, -10)
        ctx.line_to(0, -10)
        ctx.line_to(0, 10)
        ctx.line_to(10, 10)
        ctx.set_line_width(4)
        ctx.stroke()
    
    def move(self):
        if self._dir == 0:
            self._x += 1
            self._maze.TriggerListeners(self._x -1, self._y, 2, 1)
        elif self._dir == 1:
            self._y += 1
            self._maze.TriggerListeners(self._x, self._y -1, 1, 2)
        elif self._dir == 2:
            self._x -= 1
            self._maze.TriggerListeners(self._x, self._y, 2, 1)
        else:
            self._y -= 1
            self._maze.TriggerListeners(self._x, self._y, 1, 2)
    
    def turn_left(self):
        self._dir -= 1
        self._dir %= 4
        self._maze.TriggerListeners(self._x, self._y, 1, 1)

class Maze(Observable):
    def __init__(self, w, h):
        Observable.__init__(self)
        self._spacing = 25
        self._offset = 25
        self._width = w
        self._height = h
        self._walls = set()
        self._objects = set()

    def AddObject(self, o):
        self._objects.add(o)
        # TriggerSomething?

    def ToggleWall(self, x, y, d):
        self._walls ^= set([(x, y, d)])
        if d == 'h':
            self.TriggerListeners(x, y, 1, 0)
        else:
            self.TriggerListeners(x, y, 0, 1)

    def Coordinates(self, x, y):
        return self._offset + self._spacing*2*x, self._offset + self._spacing*2*y
        
    def NearestWall(self, x, y):
        x -= self._offset
        y -= self._offset
        xx = (x % (self._spacing*2)) - self._spacing
        yy = (y % (self._spacing*2)) - self._spacing
        x = x // (self._spacing*2)
        y = y // (self._spacing*2)
        if xx >= yy and xx >= -yy:
            return (x +1, y, 'v')
        elif xx <= yy and xx <= -yy:
            return (x, y, 'v')
        elif yy >= 0:
            return (x, y+1, 'h')
        else:
            return (x, y, 'h')

    def Paint(self, ctx):
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(0.3)
        for i in range(self._height +1):
            ctx.move_to(*self.Coordinates(0, i))
            ctx.line_to(*self.Coordinates(self._width, i))
        for i in range(self._width +1):
            ctx.move_to(*self.Coordinates(i, 0))
            ctx.line_to(*self.Coordinates(i, self._width))
        ctx.stroke()
        ctx.set_line_cap(cairo.LINE_CAP_SQUARE)
        for x, y, d in self._walls:
            ctx.move_to(*self.Coordinates(x, y))
            if d == 'v':
               ctx.line_to(*self.Coordinates(x, y+1))
            else:
               ctx.line_to(*self.Coordinates(x+1, y))
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(10)
        ctx.stroke_preserve()    
        ctx.set_source_rgb(1, 0, 0)
        ctx.set_line_width(4)
        ctx.stroke()
        for obj in self._objects:
            ctx.save()
            obj.Paint(ctx)
            ctx.restore()

    def PaintSquares(self, ctx, x, y, w, h):
        ctx.rectangle(*(self.Coordinates(x-0.5, y-0.5) + self.Coordinates(x + w + 0.5, y + h + 0.5)))
        ctx.clip()
        self.Paint(ctx)

class MazeWindow(wx.Window):
    def __init__(self, *args, **kw):
        self._maze = kw['maze']
        del kw['maze']
        wx.Window.__init__(self, *args, **kw)
        wx.EVT_PAINT(self, self.OnPaint)
        self._maze.AddListener(self.OnMazeChange)
    
    def OnPaint(self, e):
        self.Paint(self.GetUpdateRegion().GetBox())
        
    def Paint(self, box):
        ctx = wx.lib.wxcairo.ContextFromDC(wx.PaintDC(self))
        ctx.rectangle(box.GetX(), box.GetY(), box.GetWidth(), box.GetHeight())
        ctx.clip()
        self._maze.Paint(ctx)
                
    def OnMazeChange(self, maze, *args, **kw):
        ctx = wx.lib.wxcairo.ContextFromDC(wx.PaintDC(self))
        self._maze.PaintSquares(ctx, *args, **kw)

class EditableMazeWindow(MazeWindow):
    def __init__(self, *args, **kw):
        MazeWindow.__init__(self, *args, **kw)
        wx.EVT_LEFT_DOWN(self, self.OnClick)

    def OnClick(self, e):
        self._maze.ToggleWall(*self._maze.NearestWall(e.GetX(), e.GetY()))

class World(object):
    def __init__(self, ui):
        self._ui = ui
        self._maze = Maze(10, 10)
        self._robot = Robot(self._maze)
        self._maze.AddObject(self._robot)
        
    def makeWindow(self, parent):
        return EditableMazeWindow(parent, size=(900,900), maze=self._maze)

    def getGlobals(self, t):
        return {
            "move": t.ProxyFunction(self._robot.move),
            "turn_left": t.ProxyFunction(self._robot.turn_left),
            "print": t.ProxyFunction(lambda *a, **kw: print(*a, file=self._ui.getLog(), **kw))
        }



