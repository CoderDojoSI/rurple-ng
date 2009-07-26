#!/usr/bin/env python

from __future__ import division

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

class Maze(Observable):
    def __init__(self, w, h):
        Observable.__init__(self)
        self.width = w
        self.height = h
        self.walls = set()

    def ToggleWall(self, x, y, d):
        self.walls ^= set([(x, y, d)])
        if d == 'h':
            self.TriggerListeners(x, y, 1, 0)
        else:
            self.TriggerListeners(x, y, 0, 1)

class MazeWindow(wx.Window):
    def __init__(self, *args, **kw):
        self._maze = kw['maze']
        del kw['maze']
        wx.Window.__init__(self, *args, **kw)
        self._spacing = 25
        self._offset = 25
        wx.EVT_PAINT(self, self.OnPaint)
        self._maze.AddListener(self.OnMazeChange)
    
    def OnPaint(self, e):
        self.Paint(self.GetUpdateRegion().GetBox())
        
    def Paint(self, box):
        dc = wx.PaintDC(self)
        ctx = wx.lib.wxcairo.ContextFromDC(dc)
        ctx.rectangle(box.GetX(), box.GetY(), box.GetWidth(), box.GetHeight())
        ctx.clip()
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()
        self.CairoPaint(ctx)
        
    def CairoPaint(self, ctx):
        ctx.translate(self._offset, self._offset)
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(0.3)
        for i in range(self._maze.height +1):
            ctx.move_to(0, self._spacing*2*i)
            ctx.line_to(self._spacing*2*self._maze.width, self._spacing*2*i)
        for i in range(self._maze.width +1):
            ctx.move_to(self._spacing*2*i, 0)
            ctx.line_to(self._spacing*2*i, self._spacing*2 * self._maze.height)
        ctx.stroke()
        ctx.set_line_cap(cairo.LINE_CAP_SQUARE)
        for x, y, d in self._maze.walls:
            ctx.move_to(self._spacing*2*x, self._spacing*2*y)
            if d == 'v':
               ctx.line_to(self._spacing*2*x, self._spacing*(2 + 2*y))
            else:
               ctx.line_to(self._spacing*(2 + 2*x), self._spacing*2*y)
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(10)
        ctx.stroke_preserve()    
        ctx.set_source_rgb(1, 0, 0)
        ctx.set_line_width(4)
        ctx.stroke()
        
    def OnMazeChange(self, maze, x, y, w, h):
        self.Paint(wx.Rect(self._offset + self._spacing*(2*x -1),
                           self._offset + self._spacing*(2*y -1),
                           self._spacing*2*(w+1), self._spacing*2*(h+1)))

class EditableMazeWindow(MazeWindow):
    def __init__(self, *args, **kw):
        MazeWindow.__init__(self, *args, **kw)
        wx.EVT_LEFT_DOWN(self, self.OnClick)

    def OnClick(self, e):
        x = e.m_x - self._offset
        y = e.m_y - self._offset
        xx = (x % (self._spacing*2)) - self._spacing
        yy = (y % (self._spacing*2)) - self._spacing
        x = x // (self._spacing*2)
        y = y // (self._spacing*2)
        if xx >= yy and xx >= -yy:
            self._maze.ToggleWall(x +1, y, 'v')
        elif xx <= yy and xx <= -yy:
            self._maze.ToggleWall(x, y, 'v')
        elif yy >= 0:
            self._maze.ToggleWall(x, y+1, 'h')
        else:
            self._maze.ToggleWall(x, y, 'h')
    

