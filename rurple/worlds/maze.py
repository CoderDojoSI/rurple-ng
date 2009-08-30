from __future__ import division, print_function, unicode_literals, with_statement

import math
import random
import wx

import rurple.world, rurple.share

class MazeException(rurple.world.WorldException):
    def __init__(self, message):
        rurple.world.WorldException.__init__(self, message)
        self._text = message
    
    @property
    def title(self):
        return "Something didn't work"

    @property    
    def text(self):
        return self._text

class Robot(object):
    def __init__(self, maze, state):
        self._maze = maze
        self._name = state['name']
        self._x = state['x']
        self._y = state['y']
        self._dir = state['dir']
        self._stones = state['stones']

        self.runStart()
        self._maze.addRobot(self)
        self._maze.repaintSquares(self._x, self._y, 1, 1)

    def runStart(self):
        self._trail = [(self._x, self._y, self._dir)]
    
    def move(self):
        if not self.front_is_clear():
            raise MazeException("Hit a wall")
        if self._dir == 0:
            self._x += 1
            self._trail.append((self._x, self._y, self._dir))
            self._maze.repaintSquares(self._x -1, self._y, 2, 1)
        elif self._dir == 1:
            self._y += 1
            self._trail.append((self._x, self._y, self._dir))
            self._maze.repaintSquares(self._x, self._y -1, 1, 2)
        elif self._dir == 2:
            self._x -= 1
            self._trail.append((self._x, self._y, self._dir))
            self._maze.repaintSquares(self._x, self._y, 2, 1)
        else:
            self._y -= 1
            self._trail.append((self._x, self._y, self._dir))
            self._maze.repaintSquares(self._x, self._y, 1, 2)
        self._maze.setModified()
    
    def turn_left(self):
        self._dir += 1
        self._dir %= 4
        self._trail.append((self._x, self._y, self._dir))
        self._maze.repaintSquares(self._x, self._y, 1, 1)
        self._maze.setModified()

    def pick_stone(self):
        self._maze.pickStone(self._x, self._y)
        self._stones += 1
        self._maze.statusChanged()

    def put_stone(self):
        if self._stones == 0:
            raise MazeException("I don't have any stones")
        self._stones -= 1
        self._maze.putStone(self._x, self._y)
        self._maze.statusChanged()

    def on_stone(self):
        return self._maze.countStones(self._x, self._y) != 0

    def got_stone(self):
        return self._stones != 0
    
    def front_is_clear(self):
        return self._maze.isPassable(self._x, self._y, self._dir)

    def left_is_clear(self):
        return self._maze.isPassable(self._x, self._y,
            (self._dir +1) % 4)

    def right_is_clear(self):
        return self._maze.isPassable(self._x, self._y,
            (self._dir -1) % 4)

    def facing_north(self):
        return self._dir == 1

    @property
    def name(self): return self._name
    
    @property
    def x(self): return self._x
        
    @property
    def y(self): return self._y
        
    @property
    def dir(self): return self._dir
        
    @property
    def stones(self): return self._stones
    
    @stones.setter
    def stones(self, x):
        assert x >= 0
        assert x == int(x)
        self._stones = int(x)
        self._maze.statusChanged()
    
    @property
    def trail(self): return self._trail
    
    @property
    def staterep(self):
        return {
            "name": self._name,
            "x": self._x, "y": self._y, "dir": self._dir,
            "stones": self._stones,
        }

class Maze(object):
    def __init__(self, world, state):
        self._world = world
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
        self._stones = dict(
            (tuple(k), v) for k, v in state['stones'])
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

    def isPassable(self, x, y, d):
        if d == 0:
            return (x +1, y, 'v') not in self._walls
        elif d == 1:
            return (x, y +1, 'h') not in self._walls
        elif d == 2:
            return (x, y, 'v') not in self._walls
        else:
            return (x, y, 'h') not in self._walls

    def toggleWall(self, x, y, d):
        if not self.isInterior(x, y, d):
            return
        self._walls ^= set([(x, y, d)])
        if d == 'h':
            self.repaintSquares(x-0.5, y-0.5, 2, 1)
        else:
            self.repaintSquares(x-0.5, y-0.5, 1, 2)
        self.setModified()

    def addRobot(self, r):
        n = r.name
        if n in self._robots:
            raise MazeException("Already got a robot called %s" % n)
        self._robots[n] = r
        self._defaultRobot = r
        self.statusChanged()

    def pickStone(self, x, y):
        b = self.countStones(x, y)
        if b == 0:
            raise MazeException("I'm not next to a stone")
        b -= 1
        self.setStones(x, y, b)

    def putStone(self, x, y):
        self.setStones(x, y, 1 + self.countStones(x, y))

    def setStones(self, x, y, i):
        assert i >= 0
        if i == 0:
            if (x, y) in self._stones:
                del self._stones[(x, y)]
        else:
            self._stones[(x, y)] = i
        self.repaintSquares(x, y, 1, 1)

    def countStones(self, x, y):
        return self._stones.get((x, y), 0)

    @property
    def width(self): return self._width

    @property
    def height(self): return self._height

    @property
    def walls(self): return self._walls

    @property
    def robots(self): return self._robots

    @property
    def stones(self): return self._stones

    @property
    def defaultRobot(self): return self._defaultRobot

    @property
    def staterep(self):
        p = "rurple.worlds."
        n =  __name__
        if not n.startswith(p):
            raise Exception("Module in wrong namespace, can't save")
        return {
            "world": n[len(p):],
            "width": self._width,
            "height": self._height,
            "walls": list(w for w in self._walls if self.isInterior(*w)),
            "stones": [(k, v) for k, v in self._stones.iteritems()],
            "robots": [v.staterep for v in self._robots.itervalues()],
        }
    
    def proxyRobot(self, name):
        return eval(
            "lambda *a, **kw: self.defaultRobot.%s(*a, **kw)" % name,
            {"self": self})

    def runStart(self):
        for r in self._robots.itervalues():
            r.runStart()
        # after deleting ink trails, redraw all
        self.repaintSquares(0, 0, self._width, self._height)

    def repaintSquares(self, x, y, w, h):
        self._world.repaintSquares(x, y, w, h)

    def setModified(self):
        self._world.modified = True
        
    def statusChanged(self):
        self._world.statusChanged()
        self.setModified()

class MazeWindow(wx.PyControl):
    def __init__(self, *args, **kw):
        self._world = kw['world']
        del kw['world']
        wx.Window.__init__(self, *args, **kw)
        self._spacing = 20
        self._offset = 20
        self.SetBestSize(self.size())
        wx.EVT_PAINT(self, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnClick, self)
        self.Bind(wx.EVT_CHAR, self.OnKey, self)
        self.SetFocus()

        self._bgBrush = wx.Brush('white')
        self._gridPen = wx.Pen('black')
        self._gridPen.SetWidth(0.3)
        self._gridPen.SetCap(wx.CAP_PROJECTING)
        self._wallPen1 = wx.Pen('black')
        self._wallPen1.SetWidth(6)
        self._wallPen1.SetCap(wx.CAP_PROJECTING)
        self._wallPen2 = wx.Pen('red')
        self._wallPen2.SetWidth(2)
        self._wallPen2.SetCap(wx.CAP_PROJECTING)
        self._stoneBrush1 = wx.Brush('cyan')
        self._stoneBrush2 = wx.Brush('white')
        self._textBrush = wx.Brush('black')
        self._font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self._font.SetWeight(wx.BOLD)
        self._font.SetPointSize(18)
        self._robotBrush = wx.Brush('blue')
        self._robotPen = wx.Pen('blue')
        self._robotPen.SetWidth(4)
        self._robotPen.SetCap(wx.CAP_BUTT)
        self._trailPen = wx.Pen('grey')
        self._trailPen.SetWidth(1)
    
    def OnPaint(self, e):
        dc = wx.PaintDC(self)
        gc = wx.GraphicsContext.Create(dc)
        self.paint(gc, self._world._maze)
                
    def repaintSquares(self, *args, **kw):
        self.RefreshRect(self.paintBounds(*args, **kw))

    def _stoneSetter(self, x, y, i):
        def f(e):
            self._world._maze.setStones(x, y, i)
        return f

    def OnClick(self, e):
        self.SetFocus()        
        if not self._world.editable:
            return
        near = self.nearest(e.GetX(), e.GetY())
        if len(near) == 3:
            self._world._maze.toggleWall(*near)
        else:
            x, y = near
            if (x >= 0 and x < self._world._maze.width
                and y >= 0 and y < self._world._maze.height):
                menu = wx.Menu()
                self.Bind(wx.EVT_MENU,
                    self._stoneSetter(x, y, 0),
                    menu.Append(wx.ID_ANY, "Empty"))
                for i in range(1, 10):
                    self.Bind(wx.EVT_MENU,
                        self._stoneSetter(x, y, i),
                        menu.Append(wx.ID_ANY, str(i)))
                self.PopupMenu(menu, e.GetPosition())

    def OnKey(self, e):
        if not self._world.editable:
            e.Skip()
            return
        code = e.GetKeyCode()
        if code == wx.WXK_UP:
            try:
                self._world._maze.defaultRobot.move()
            except rurple.world.WorldException, e:
                self._world.handleException(self, e)
        elif code == wx.WXK_LEFT:
            try:
                self._world._maze.defaultRobot.turn_left()
            except rurple.world.WorldException, e:
                self._world.handleException(self, e)

    def coordinates(self, x, y):
        m = self._world._maze
        return self._offset + self._spacing*2*x, self._offset + self._spacing*2*(m.height - y)
        
    def nearest(self, x, y):
        m = self._world._maze
        x -= self._offset
        y -= self._offset
        xx = (x % (self._spacing*2)) - self._spacing
        yy = -((y % (self._spacing*2)) - self._spacing)
        x = x // (self._spacing*2)
        y = m.height - (y // (self._spacing*2)) -1
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

    def paintRobot(self, gc, r):
        x, y = self.coordinates(r.x + .5, r.y + .5)
        gc.Translate(x, y)
        gc.Rotate(-math.pi * 0.5 * r.dir)
        gc.SetBrush(self._robotBrush)
        p = gc.CreatePath()
        p.AddCircle(0, 0, 7)
        gc.FillPath(p)
        gc.SetPen(self._robotPen)
        p = gc.CreatePath()
        p.MoveToPoint(10, -10)
        p.AddLineToPoint(0, -10)
        p.AddLineToPoint(0, 10)
        p.AddLineToPoint(10, 10)
        gc.StrokePath(p)

    def _trailPoint(self, p):
        x, y, d = p
        s = 0.1
        if d == 0:
            x -= s; y -= s
        elif d == 1:
            x += s; y -= s
        elif d == 2:
            x += s; y += s
        else:
            x -= s; y += s
        return self.coordinates(x + 0.5, y + 0.5)

    def paintTrail(self, gc, r):
        gc.SetPen(self._trailPen)
        p = gc.CreatePath()
        t = r.trail
        p.MoveToPoint(*self._trailPoint(t[0]))
        for c in t[1:]:
            p.AddLineToPoint(*self._trailPoint(c))
        gc.StrokePath(p)

    def paint(self, gc, maze):
        gc.SetBrush(self._bgBrush)
        x1, y1 = self.coordinates(0, 0)
        x2, y2 =  self.coordinates(maze.width, maze.height)
        gc.DrawRectangle(x1, y2, x2 - x1, y1 - y2)
        gc.SetPen(self._gridPen)
        p = gc.CreatePath()
        for i in range(maze.height +1):
            p.MoveToPoint(*self.coordinates(0, i))
            p.AddLineToPoint(*self.coordinates(maze.width, i))
        for i in range(maze.width +1):
            p.MoveToPoint(*self.coordinates(i, 0))
            p.AddLineToPoint(*self.coordinates(i, maze.height))
        gc.StrokePath(p)
        p = gc.CreatePath()
        for x, y, d in maze.walls:
            p.MoveToPoint(*self.coordinates(x, y))
            if d == 'v':
               p.AddLineToPoint(*self.coordinates(x, y+1))
            else:
               p.AddLineToPoint(*self.coordinates(x+1, y))
        gc.SetPen(self._wallPen1)
        gc.StrokePath(p)
        gc.SetPen(self._wallPen2)
        gc.StrokePath(p)
        for r in maze.robots.itervalues():
            gc.PushState()
            self.paintTrail(gc, r)
            gc.PopState()
        gc.SetFont(self._font)

        for k, v in maze.stones.iteritems():
            x, y = self.coordinates(k[0] + 0.5, k[1] + 0.5)
            gc.SetBrush(self._stoneBrush1)
            p = gc.CreatePath()
            p.AddCircle(x, y, 14)
            gc.FillPath(p)
            gc.SetBrush(self._stoneBrush2)
            p = gc.CreatePath()
            p.AddCircle(x, y, 11)
            gc.FillPath(p)
            gc.SetBrush(self._textBrush)
            t = str(v)
            exts = gc.GetFullTextExtent(t)
            # Correct for mis-centering by hand - bah!
            gc.DrawText(t, x - 0.5*exts[0] -1, y - 0.5*exts[1])
        for r in maze.robots.itervalues():
            gc.PushState()
            self.paintRobot(gc, r)
            gc.PopState()

    def paintBounds(self, x, y, w, h):
        xl, yl = self.coordinates(x, y + h)
        xh, yh = self.coordinates(x + w, y)
        return xl, yl, xh - xl, yh - yl

    def size(self):
        m = self._world._maze
        return (2*self._offset + 2*m.width*self._spacing,
            2*self._offset + 2*m.height*self._spacing)

def extractKey(d, k):
    res = d[k]
    del d[k]
    return res

class ExceptionDialog(wx.Dialog):
    def __init__(self, *a, **kw):
        self._exception = extractKey(kw, 'exception')
        kw[str("title")] = self._exception.title
        wx.Dialog.__init__(self, *a, **kw)

        sizer = wx.BoxSizer(wx.VERTICAL)
        bitmap = wx.StaticBitmap(self,
            bitmap=rurple.share.toBitmap('ouch'))
        sizer.Add(bitmap)
        label = wx.StaticText(self, label=self._exception.text)
        sizer.Add(label, 1, wx.ALL|wx.ALIGN_CENTER, 5)

        sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)

        btnsizer = wx.StdDialogButtonSizer()
                
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.SetAffirmativeButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.EXPAND|wx.ALL, 5)
        
        self.SetSizer(sizer)
        sizer.Fit(self)
        
class StoneDialog(wx.Dialog):
    def __init__(self, *a, **kw):
        self._maze = extractKey(kw, 'maze')
        wx.Dialog.__init__(self, *a, **kw)

        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, label="Stones for robot to start with")
        sizer.Add(label, 0, wx.ALL, 5)

        self._spin = wx.SpinCtrl(self,
            initial=self._maze.defaultRobot.stones)
        sizer.Add(self._spin, 0, wx.ALL, 5)

        sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        
        btnsizer = wx.StdDialogButtonSizer()
                
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.OnOK, btn)
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        
        self.SetSizer(sizer)
        sizer.Fit(self)
    
    def OnOK(self, e):
        self._maze.defaultRobot.stones = self._spin.Value
        e.Skip()

class NewDialog(wx.Dialog):
    def __init__(self, *a, **kw):
        wx.Dialog.__init__(self, *a, **kw)

        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, label="Width and height of new maze")
        sizer.Add(label, 0, wx.ALL, 5)

        # Cheat - look into private members
        spinsizer = wx.BoxSizer(wx.HORIZONTAL)
        self._w = wx.SpinCtrl(self, min=1,
            initial=10)
        spinsizer.Add(self._w, 0, wx.ALL, 5)
        self._h = wx.SpinCtrl(self, min=1,
            initial=10)
        spinsizer.Add(self._h, 0, wx.ALL, 5)
        
        sizer.Add(spinsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        
        btnsizer = wx.StdDialogButtonSizer()
                
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        #self.Bind(wx.EVT_BUTTON, self.OnOK, btn)
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        
        self.SetSizer(sizer)
        sizer.Fit(self)

    def makeWorld(self, ui):
        return World(ui, self._initstate(self._w.Value, self._h.Value))

    def _initstate(self, w, h):
        return {
            "width": w,
            "walls": [],
            "stones": [],
            "robots": [
                {"name": "robot", "y": 0, "x": 0, "dir": 0, "stones": 0}
            ],
            "height": h
        }
    
class World(object):
    def __init__(self, ui, state):
        self._ui = ui
        self._window = None
        self._modified = False
        self._modifyHook = None
        self._maze = None
        self._maze = Maze(self, state)
        self._modified = False
        # cheat - use a var instead of a property
        self.editable = True


    @property
    def modified(self):
        return self._modified

    @modified.setter
    def modified(self, v):
        if self._modified != v:
            self._modified = v
            if self._modifyHook is not None:
                self._modifyHook.update()

    def modifyHook(self, m):
        self._modifyHook = m

    @property
    def staterep(self):
        return self._maze.staterep
        
    def makeWindow(self, parent):
        self._window = MazeWindow(parent, style=wx.WANTS_CHARS, world=self)
        self.statusChanged()
        return self._window

    def repaintSquares(self, x, y, w, h):
        if self._window is not None:
            self._window.repaintSquares(x, y, w, h)

    def statusChanged(self):
        if self._maze is not None:
            self._ui.setWorldStatus("Robot \"%s\" has %s stones"
                % (self._maze.defaultRobot.name, self._maze.defaultRobot.stones))
            
    def menu(self, menu):
        return [
            (self.OnStoneMenu, menu.Append(wx.ID_ANY, "Set stones...")),
        ]

    def runStart(self):
        self._maze.runStart()

    def OnStoneMenu(self, e):
        if not self.editable:
            wx.MessageDialog(self._ui, caption="Program running",
                message = "Cannot edit world while program is running",
                style=wx.ICON_ERROR | wx.OK).ShowModal()
            return
        d = StoneDialog(self._ui, maze=self._maze)
        d.ShowModal()

    def _print(self, *a, **kw):
        print(*a, file=self._ui.log, **kw)

    def _rollDice(self):
        return random.randint(1, 6)
    
    def _inputInt(self, text='Please enter an integer'):
        dlg = wx.TextEntryDialog(self._ui,
            message=text)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                return int(dlg.GetValue())
            else:
                return None
        finally:
            dlg.Destroy()
        
    def _inputString(self, text='Please enter some text'):
        dlg = wx.TextEntryDialog(self._ui,
            message=text)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                return dlg.GetValue()
            else:
                return None
        finally:
            dlg.Destroy()
    
    def getGlobals(self, t):
        res = {}
        res.update(dict([
            (name, t.proxyFunction(self._maze.proxyRobot(name)))
            for name in [
                "move", "turn_left",
                "pick_stone", "put_stone",
                "on_stone", "got_stone",
                "front_is_clear", "left_is_clear", "right_is_clear",
                "facing_north",
            ]]))
        res.update({
            "print": t.proxyFunction(self._print),
            "roll_dice": t.proxyFunction(self._rollDice),
            "input_int": t.proxyFunction(self._inputInt),
            "input_string": t.proxyFunction(self._inputString),
        })
        return res

    def handleException(self, frame, e):
        d = ExceptionDialog(frame, exception=e)
        d.ShowModal()

__all__ = [World, NewDialog]

