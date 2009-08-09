# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals, with_statement

import sys
import math
import os
import os.path
import json
import wx
from wx.lib.scrolledpanel import ScrolledPanel
import wx.stc

from rurple import maze, cpu, world

def toBitmap(name):
    return wx.Image('images/%s.png' % name, wx.BITMAP_TYPE_PNG).ConvertToBitmap()

class DotDir(object):
    def __init__(self, path):
        self._path = path
    
    def read(self, name, default=None):
        f = os.path.join(self._path, name)
        if os.path.exists(f):
            with open(f) as h:
                return h.read()
        else:
            return default
    
    def write(self, name, text):
        if not os.path.isdir(self._path):
            os.mkdir(self._path)
        f = os.path.join(self._path, name)
        with open(f, "w") as h:
            h.write(text)

class PythonEditor(wx.stc.StyledTextCtrl):
    MARK_RUNNING = 7

    def __init__(self, *a, **kw):
        wx.stc.StyledTextCtrl.__init__(self, *a, **kw)
        self.MarkerDefine(self.MARK_RUNNING, wx.stc.STC_MARK_BACKGROUND, 'white', 'wheat')
        self._marked = None

    def mark(self, line):
        if self._marked is not None:
            self.MarkerDelete(self._marked -1, self.MARK_RUNNING)
        self._marked = line
        if self._marked is not None:
            self.MarkerAdd(self._marked -1, self.MARK_RUNNING)

class LogWindow(wx.stc.StyledTextCtrl):
    def write(self, s):
        self.AddText(s)
        self.EnsureCaretVisible()
        
    def clear(self):
        self.SetText("")

class LogScale(object):
    def __init__(self, ticks, lo, hi):
        self._lo = math.log(lo)
        self._r = (math.log(hi) - self._lo) / ticks

    def toTicks(self, x):
        return (math.log(x) - self._lo) / self._r
    
    def fromTicks(self, x):
        return math.exp(x * self._r + self._lo)

class RurFrame(wx.Frame):
    def __init__(self, *args, **kw):
        wx.Frame.__init__(self, *args, **kw)
        # FIXME: not right for Windows or MacOS X
        self._dotPath = DotDir(os.path.expanduser("~/.rurple"))
        self._cpu = cpu.CPU(self)
        sash = wx.SplitterWindow(self)
        self._stc = PythonEditor(sash)
        self._stc.AddText(self._dotPath.read("program.rur", ""))
        hsash = wx.SplitterWindow(sash)
        self._worldParent = ScrolledPanel(hsash)
        self._worldWindow = None
        sash.SplitVertically(self._stc, hsash)
        self._logWindow = LogWindow(hsash)
        hsash.SplitHorizontally(self._worldParent, self._logWindow)
        self._worldParent.SetupScrolling()
        
        #self.CreateStatusBar()
        menuBar = wx.MenuBar()
        filemenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnAbout,
            filemenu.Append(wx.ID_ABOUT, "&About..."," Information about this program"))
        filemenu.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.OnExit,
            filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program"))
        menuBar.Append(filemenu,"&File")
        self._worldMenu = wx.Menu()
        menuBar.Append(self._worldMenu,"&World")
        self.SetMenuBar(menuBar)
        self._toolbar = self.CreateToolBar()
        tsize = (24,24)
        self._toolbar.SetToolBitmapSize(tsize)
        self.Bind(wx.EVT_TOOL, lambda e: self.reset(),
            self._toolbar.AddLabelTool(wx.ID_ANY, "Reset",
                toBitmap('reset_world')))
        self._playTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY, "Play",
            toBitmap('play'), shortHelp="Play")
        self.Bind(wx.EVT_TOOL, (lambda e: self._cpu.play()), self._playTool)
        self._pauseTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY, "pause",
            toBitmap('pause'), shortHelp="pause")
        self.Bind(wx.EVT_TOOL, (lambda e: self._cpu.pause()), self._pauseTool)
        self._stopTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY, "stop",
            toBitmap('stop'), shortHelp="stop")
        self.Bind(wx.EVT_TOOL, (lambda e: self._cpu.stop()), self._stopTool)
        self._stepTool = self._toolbar.AddLabelTool(wx.ID_ANY, "step",
            toBitmap('step'), shortHelp="step")
        self.Bind(wx.EVT_TOOL, self.OnStep, self._stepTool)
        self._toolbar.ToggleTool(self._stopTool.Id, True)
        self._slideScale = LogScale(100, 3000, 100)
        self._slider = wx.Slider(self._toolbar, size=(250,-1), 
            value=int(0.5 +  self._slideScale.toTicks(300)))
        self.Bind(wx.EVT_SLIDER, self.OnSlide, self._slider)
        self.OnSlide(None)
        self._toolbar.AddControl(self._slider)
        self.reset()

    def reset(self):
        self.world = maze.World(self, 
            json.loads(self._dotPath.read("world.wld")))
        
    def OnAbout(self, e):
        d = wx.MessageDialog(self, " A Python Learning Environment \n"
                            " by André Roberge and Paul Crowley","About RUR-PLE 2", wx.OK)
        d.ShowModal()
        d.Destroy()
    
    def OnExit(self, e):
        self.Close(True)

    def OnStep(self, e):
        # FIXME: bit inelegant this
        self._toolbar.ToggleTool(self._pauseTool.Id, True)
        self._cpu.step()

    def OnSlide(self, e):
        #print(e, dir(e))
        self._cpu.setLineTime(int(0.5 + self._slideScale.fromTicks(self._slider.Value)))

    @property
    def log(self):
        return self._logWindow

    @property
    def program(self):
        return self._stc.GetText()

    @property
    def world(self):
        return self._world

    @world.setter
    def world(self, world):
        if self._worldWindow is not None:
            self._worldWindow.Destroy()
            self._worldWindow = None
        self._world = world
        sps = wx.BoxSizer()
        self._worldWindow = self._world.makeWindow(self._worldParent)
        sps.Add(self._worldWindow)
        self._worldParent.SetSizer(sps)
        while True:
            mi = self._worldMenu.FindItemByPosition(0)
            if mi is None:
                break
            self._worldMenu.Delete(mi.Id)
        for b, e in self._world.menu(self._worldMenu):
            self.Bind(wx.EVT_MENU, b, e)
        #sps.SetSizeHints(sp)

    def traceLine(self, line):
        self._stc.mark(line)
    
    def starting(self):
        self._dotPath.write("program.rur", self.program)
        sr = self.world.staterep
        self._dotPath.write("world.wld", 
            json.dumps(sr,
                indent=4, sort_keys = True))
        self._logWindow.clear()
    
    def done(self, e):
        #print("Done, exception:", e)
        self._toolbar.ToggleTool(self._stopTool.Id, True)
        if e is None:
            d = wx.MessageDialog(self, message="Your program finished",
                caption = "Program finished",
                style=wx.ICON_INFORMATION | wx.OK)
            d.ShowModal()
        elif isinstance(e, world.WorldException):
            self._world.handleException(self, e)
        else: 
            d = wx.MessageDialog(self, message=str(e),
                caption = "Error running your program",
                style=wx.ICON_EXCLAMATION | wx.OK)
            d.ShowModal()

class App(wx.App):
    def OnInit(self):
        frame = RurFrame(None, title="RUR-PLE 2", size=(900,1000))
        frame.Show(True)
        self.SetTopWindow(frame)
        return True

def main():
    app = App(0)
    app.MainLoop()

