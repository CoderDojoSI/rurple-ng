from __future__ import division, print_function, unicode_literals, with_statement

import math
import wx
import wx.lib.wxcairo
import cairo

from rurple import world

class Observable(object):
    def __init__(self):
        self._listeners = set()
    
    def addListener(self, l):
        self._listeners.add(l)
        
    def removeListener(self, l):
        self._listeners.remove(l)

    def triggerListeners(self, *args, **kw):
        for l in self._listeners:
            l(self, *args, **kw)

class Robot(object):
    def __init__(self, maze, state):
        self._maze = maze
        self._name = state['name']
        self._x = state['x']
        self._y = state['y']
        self._dir = state['dir']
        self._beepers = state['beepers']
        self._maze.addRobot(self)
        self._maze.triggerListeners(self._x, self._y, 1, 1)

    def paint(self, ctx):
        x, y = self._maze.coordinates(self._x + .5, self._y + .5)
        ctx.translate(x, y)
        ctx.rotate(-math.pi * 0.5 * self._dir)
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
            if (self._x +1, self._y, 'v') in self._maze._walls:
                raise world.WorldException("Hit a wall")
            self._x += 1
            self._maze.triggerListeners(self._x -1, self._y, 2, 1)
        elif self._dir == 1:
            if (self._x, self._y +1, 'h') in self._maze._walls:
                raise world.WorldException("Hit a wall")
            self._y += 1
            self._maze.triggerListeners(self._x, self._y -1, 1, 2)
        elif self._dir == 2:
            if (self._x, self._y, 'v') in self._maze._walls:
                raise world.WorldException("Hit a wall")
            self._x -= 1
            self._maze.triggerListeners(self._x, self._y, 2, 1)
        else:
            if (self._x, self._y, 'h') in self._maze._walls:
                raise world.WorldException("Hit a wall")
            self._y -= 1
            self._maze.triggerListeners(self._x, self._y, 1, 2)
    
    def turn_left(self):
        self._dir += 1
        self._dir %= 4
        self._maze.triggerListeners(self._x, self._y, 1, 1)

    def pick_beeper(self):
        self._maze.pickBeeper(self._x, self._y)
        self._beepers += 1

    def put_beeper(self):
        if self._beepers == 0:
            raise world.WorldException("I don't have any beepers")
        self._beepers -= 1
        self._maze.putBeeper(self._x, self._y)

    @property
    def name(self):
        return self._name
    
    @property
    def beepers(self):
        return self._beepers
    
    @beepers.setter
    def beepers(self, x):
        assert x >= 0
        assert x == int(x)
        self._beepers = int(x)
    
    @property
    def staterep(self):
        return {
            "name": self._name,
            "x": self._x, "y": self._y, "dir": self._dir, 
            "beepers": self._beepers,
        }

class Maze(Observable):
    def __init__(self, state):
        Observable.__init__(self)
        self._spacing = 20
        self._offset = 20
        self._width = state['width']
        self._height = state['height']
        self._walls = (
            set((x, 0, 'h') for x in range(self._width))
            | set((x, self._height, 'h') for x in range(self._width))
            | set((0, y, 'v') for y in range(self._height))
            | set((self._width, y, 'v') for y in range(self._height))
            | set(
                tuple(w) for w in state['walls']
                if self.isInterior(*w)))
        self._beepers = dict(
            (tuple(k), v) for k, v in state['beepers'])
        self._robots = {}
        for r in state['robots']:
            Robot(self, r)
    
    def isInterior(self, x, y, d):
        if x >= self._width or y >= self._height:
            return False
        if d == 'h':
            return x >= 0 and y > 0
        elif d == 'v':
            return x > 0 and y >= 0

    def toggleWall(self, x, y, d):
        if not self.isInterior(x, y, d):
            return
        self._walls ^= set([(x, y, d)])
        if d == 'h':
            self.triggerListeners(x, y, 1, 0)
        else:
            self.triggerListeners(x, y, 0, 1)

    def addRobot(self, r):
        n = r.name
        if n in self._robots:
            raise world.WorldException("Already got a robot called %s" % n)
        self._robots[n] = r
        self._defaultRobot = r

    def pickBeeper(self, x, y):
        b = self._beepers.get((x, y), 0)
        if b == 0:
            raise world.WorldException("I'm not next to a beeper")
        b -= 1
        self.setBeepers(x, y, b)

    def putBeeper(self, x, y):
        self.setBeepers(x, y, 1 + self._beepers.get((x, y), 0))

    def setBeepers(self, x, y, i):
        assert i >= 0
        if i == 0:
            if (x, y) in self._beepers:
                del self._beepers[(x, y)]
        else:
            self._beepers[(x, y)] = i
        self.triggerListeners(x, y, 1, 1)

    def coordinates(self, x, y):
        return self._offset + self._spacing*2*x, self._offset + self._spacing*2*(self._height - y)
        
    def nearest(self, x, y):
        x -= self._offset
        y -= self._offset
        xx = (x % (self._spacing*2)) - self._spacing
        yy = -((y % (self._spacing*2)) - self._spacing)
        x = x // (self._spacing*2)
        y = self._height - (y // (self._spacing*2)) -1
        if max(abs(xx), abs(yy)) < self._spacing * 0.58:
            return (x, y)
        elif xx >= yy and xx >= -yy:
            return (x +1, y, 'v')
        elif xx <= yy and xx <= -yy:
            return (x, y, 'v')
        elif yy >= 0:
            return (x, y +1, 'h')
        else:
            return (x, y, 'h')

    def paint(self, ctx):
        ctx.select_font_face("DejaVu Sans",
            cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(0.3)
        for i in range(self._height +1):
            ctx.move_to(*self.coordinates(0, i))
            ctx.line_to(*self.coordinates(self._width, i))
        for i in range(self._width +1):
            ctx.move_to(*self.coordinates(i, 0))
            ctx.line_to(*self.coordinates(i, self._width))
        ctx.stroke()
        ctx.set_line_cap(cairo.LINE_CAP_SQUARE)
        for x, y, d in self._walls:
            ctx.move_to(*self.coordinates(x, y))
            if d == 'v':
               ctx.line_to(*self.coordinates(x, y+1))
            else:
               ctx.line_to(*self.coordinates(x+1, y))
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(10)
        ctx.stroke_preserve()    
        ctx.set_source_rgb(1, 0, 0)
        ctx.set_line_width(4)
        ctx.stroke()
        ctx.set_font_size(15)
        for k, v in self._beepers.iteritems():
            x, y = self.coordinates(k[0] + 0.5, k[1] + 0.5)
            ctx.set_source_rgb(0.7, 0.7, 1)
            ctx.arc(x, y, 14, 0, 2*math.pi)
            ctx.fill()
            ctx.set_source_rgb(1, 1, 1)
            ctx.arc(x, y, 11, 0, 2*math.pi)
            ctx.fill()
            ctx.set_source_rgb(0, 0, 0)
            t = str(v)
            exts = ctx.text_extents(t)
            ctx.move_to(x - exts[0] - 0.5*exts[2], y - exts[1] - 0.5*exts[3])
            ctx.show_text(t)
        for r in self._robots.itervalues():
            ctx.save()
            r.paint(ctx)
            ctx.restore()

    def paintSquares(self, ctx, x, y, w, h):
        ctx.rectangle(*(self.coordinates(x-0.5, y + h + 0.5) + self.coordinates(x + w + 0.5, y - 0.5)))
        ctx.clip()
        self.paint(ctx)

    def size(self):
        return (2*self._offset + 2*self._width*self._spacing,
            2*self._offset + 2*self._height*self._spacing)

    @property
    def defaultRobot(self):
        return self._defaultRobot

    @property
    def staterep(self):
        return {
            "width": self._width,
            "height": self._height,
            "walls": list(self._walls),
            "beepers": [(k, v) for k, v in self._beepers.iteritems()],
            "robots": [v.staterep for v in self._robots.itervalues()],
        }
    
    def proxyRobot(self, name):
        return eval(
            "lambda *a, **kw: self.defaultRobot.%s(*a, **kw)" % name,
            {"self": self})

class MazeWindow(wx.PyControl):
    def __init__(self, *args, **kw):
        self._maze = kw['maze']
        del kw['maze']
        wx.Window.__init__(self, *args, **kw)
        self.SetBestSize(self._maze.size())
        wx.EVT_PAINT(self, self.OnPaint)
        self._maze.addListener(self.onMazeChange)
    
    def OnPaint(self, e):
        self.paint(self.GetUpdateRegion().GetBox())
        
    def paint(self, box):
        ctx = wx.lib.wxcairo.ContextFromDC(wx.PaintDC(self))
        ctx.rectangle(box.GetX(), box.GetY(), box.GetWidth(), box.GetHeight())
        ctx.clip()
        self._maze.paint(ctx)
                
    def onMazeChange(self, maze, *args, **kw):
        ctx = wx.lib.wxcairo.ContextFromDC(wx.PaintDC(self))
        self._maze.paintSquares(ctx, *args, **kw)

class EditableMazeWindow(MazeWindow):
    def __init__(self, *args, **kw):
        MazeWindow.__init__(self, *args, **kw)
        wx.EVT_LEFT_DOWN(self, self.OnClick)

    def _beeperSetter(self, x, y, i):
        def f(e):
            self._maze.setBeepers(x, y, i)
        return f

    def OnClick(self, e):
        near = self._maze.nearest(e.GetX(), e.GetY())
        if len(near) == 3:
            self._maze.toggleWall(*near)
        else:
            x, y = near
            menu = wx.Menu()
            for i in range(10):
                self.Bind(wx.EVT_MENU, 
                    self._beeperSetter(x, y, i),
                    menu.Append(wx.ID_ANY, str(i)))
            self.PopupMenu(menu, e.GetPosition())

class BeeperDialog(wx.Dialog):
    def __init__(self, *a, **kw):
        self._maze = kw['maze']
        del kw['maze']
        wx.Dialog.__init__(self, *a, **kw)

        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, wx.ID_ANY, "Beepers for robot to start with")
        sizer.Add(label, 0, wx.ALL, 5)

        self._spin = wx.SpinCtrl(self,
            initial=self._maze.defaultRobot.beepers)
        sizer.Add(self._spin, 0, wx.ALL, 5)

        # This line doesn't grow horizontally.  Who knows why?
        line = wx.StaticLine(self, wx.ID_ANY,
            size=(1,-1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, 
            wx.GROW|wx.ALIGN_CENTER_VERTICAL, 5)
        
        btnsizer = wx.StdDialogButtonSizer()
                
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.OnOK, btn)
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        
        sizer.Layout()
        sizer.Fit(self)
    
    def OnOK(self, e):
        self._maze.defaultRobot.beepers = self._spin.Value
        e.Skip()

class NewDialog(wx.Dialog):
    def __init__(self, *a, **kw):
        self._world = kw['world']
        del kw['world']
        wx.Dialog.__init__(self, *a, **kw)

        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, wx.ID_ANY, "Width and height of new maze")
        sizer.Add(label, 0, wx.ALL, 5)

        # Cheat - look into private members
        spinsizer = wx.BoxSizer(wx.HORIZONTAL)
        self._w = wx.SpinCtrl(self,
            initial=self._world._maze._width)
        spinsizer.Add(self._w, 0, wx.ALL, 5)
        self._h = wx.SpinCtrl(self,
            initial=self._world._maze._height)
        spinsizer.Add(self._h, 0, wx.ALL, 5)
        
        sizer.Add(spinsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        line = wx.StaticLine(self, wx.ID_ANY,
            size=(1,-1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, 
            wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)
        
        btnsizer = wx.StdDialogButtonSizer()
                
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.OnOK, btn)
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        
        sizer.Layout()
        sizer.Fit(self)
    
    def OnOK(self, e):
        self._world.replace(self._w.Value, self._h.Value)
        e.Skip()

class World(object):
    def __init__(self, ui, state=None):
        if state is None:
            state = self._initstate(10, 10)
        self._ui = ui
        self._maze = Maze(state)

    def _initstate(self, w, h):
        return {
            "width": w, 
            "walls": [], 
            "beepers": [], 
            "robots": [
                {"name": "robot", "y": 0, "x": 0, "dir": 0, "beepers": 0}
            ],
            "height": h
        }
    
    @property
    def staterep(self):
        return self._maze.staterep 
        
    def makeWindow(self, parent):
        return EditableMazeWindow(parent, maze=self._maze)

    def menu(self, menu):
        return [
            (self.OnBeeperMenu, menu.Append(wx.ID_ANY, "Set beepers...")),
            (self.OnNewMenu, menu.Append(wx.ID_ANY, "New...")),
        ]

    def OnBeeperMenu(self, e):
        d = BeeperDialog(self._ui, maze=self._maze)
        d.ShowModal()

    def OnNewMenu(self, e):
        d = NewDialog(self._ui, world=self)
        d.ShowModal()

    def replace(self, w, h):
        self._ui.world = World(self._ui, self._initstate(w, h))

    def getGlobals(self, t):
        res = {}
        res.update(dict([
            (name, t.proxyFunction(self._maze.proxyRobot(name)))
            for name in [
                "move", "turn_left", 
                "pick_beeper", "put_beeper"
            ]]))
        res.update({
            "print": t.proxyFunction(
                lambda *a, **kw: print(*a, file=self._ui.log, **kw))
        })
        return res

    def handleException(self, frame, e):
        d = wx.MessageDialog(frame, message=str(e),
            caption = "Not right with the world",
            style=wx.ICON_EXCLAMATION | wx.OK)
        d.ShowModal()
    
