# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals, with_statement

import sys
import math
import os
import os.path
import json
import wx
import wx.lib.scrolledpanel

from rurple import maze, cpu, world, textctrl

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
        self._dotPath = os.path.expanduser("~/.rurple")
        if not os.path.isdir(self._dotPath):
            os.mkdir(self._dotPath)
        self._sharePath = "share"
        self._cpu = cpu.CPU(self)
        sash = wx.SplitterWindow(self)
        self._editor = textctrl.PythonEditor(sash)
        dp = os.path.join(self._dotPath, "program.rur")
        if os.path.exists(dp):
            self._openProgram(dp)
        hsash = wx.SplitterWindow(sash)
        self._worldParent = wx.lib.scrolledpanel.ScrolledPanel(hsash)
        self._worldWindow = None
        sash.SplitVertically(self._editor, hsash)
        self._logWindow = textctrl.LogWindow(hsash)
        hsash.SplitHorizontally(self._worldParent, self._logWindow)
        self._worldParent.SetupScrolling()
        
        self._statusBar = self.CreateStatusBar()
        self._statusBar.SetFieldsCount(2)
        self._statusBar.SetStatusWidths([-1,-1])
        menuBar = wx.MenuBar()
        filemenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnNew,
            filemenu.Append(wx.ID_NEW,"&New", "Start a new program"))
        self.Bind(wx.EVT_MENU, self.OnOpen,
            filemenu.Append(wx.ID_OPEN,"&Open...", "Open a program"))
        #self.Bind(wx.EVT_MENU, self.OnSave,
        #    filemenu.Append(wx.ID_SAVE,"&Save", "Save the current program"))
        self.Bind(wx.EVT_MENU, self.OnSaveAs,
            filemenu.Append(wx.ID_SAVEAS,"Save &As...", "Save the current program with a different filename"))
        filemenu.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.OnExit,
            filemenu.Append(wx.ID_EXIT,"E&xit","Close RUR-PLE"))
        menuBar.Append(filemenu,"&File")
        runmenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnPlay,
            runmenu.Append(wx.ID_ANY,"&Play", "Start the program running"))
        self.Bind(wx.EVT_MENU, self.OnPause,
            runmenu.Append(wx.ID_ANY,"P&ause", "Pause the program"))
        self.Bind(wx.EVT_MENU, self.OnStop,
            runmenu.Append(wx.ID_ANY,"S&top", "Stop the program"))
        self.Bind(wx.EVT_MENU, self.OnStep,
            runmenu.Append(wx.ID_ANY,"&Step", "Step one line of the program"))
        menuBar.Append(runmenu,"&Run")
        
        self._worldMenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnWorldNew,
            self._worldMenu.Append(wx.ID_ANY,"&New...", "Start a new world"))
        self.Bind(wx.EVT_MENU, self.OnWorldOpen,
            self._worldMenu.Append(wx.ID_ANY,"&Open...", "Open a world"))
        #self.Bind(wx.EVT_MENU, self.OnWorldSave,
        #    self._worldMenu.Append(wx.ID_ANY,"&Save", "Save the current world"))
        self.Bind(wx.EVT_MENU, self.OnWorldSaveAs,
            self._worldMenu.Append(wx.ID_ANY,"Save &As...", "Save the current world with a different filename"))
        self._worldMenu.AppendSeparator()
        self._worldMenuItems = self._worldMenu.MenuItemCount
        menuBar.Append(self._worldMenu,"&World")
        helpmenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnAbout,
            helpmenu.Append(wx.ID_ABOUT, "&About..."," Information about RUR-PLE"))
        menuBar.Append(helpmenu,"&Help")
        self.SetMenuBar(menuBar)
        self._toolbar = self.CreateToolBar()
        tsize = (24,24)
        self._toolbar.SetToolBitmapSize(tsize)
        self.Bind(wx.EVT_TOOL, lambda e: self._reset(),
            self._toolbar.AddLabelTool(wx.ID_ANY, "Reset",
                self._toBitmap('reset_world')))
        self._playTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY, "Play",
            self._toBitmap('play'), shortHelp="Play")
        self.Bind(wx.EVT_TOOL, self.OnPlay, self._playTool)
        self._pauseTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY, "pause",
            self._toBitmap('pause'), shortHelp="pause")
        self.Bind(wx.EVT_TOOL, self.OnPause, self._pauseTool)
        self._stopTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY, "stop",
            self._toBitmap('stop'), shortHelp="stop")
        self.Bind(wx.EVT_TOOL, self.OnStop, self._stopTool)
        self._stepTool = self._toolbar.AddLabelTool(wx.ID_ANY, "step",
            self._toBitmap('step'), shortHelp="step")
        self.Bind(wx.EVT_TOOL, self.OnStep, self._stepTool)
        self._toolbar.ToggleTool(self._stopTool.Id, True)
        self._slideScale = LogScale(100, 3000, 100)
        self._slider = wx.Slider(self._toolbar, size=(250,-1), 
            value=int(0.5 +  self._slideScale.toTicks(300)))
        self.Bind(wx.EVT_SLIDER, self.OnSlide, self._slider)
        self.OnSlide(None)
        self._toolbar.AddControl(self._slider)
        self._reset()

    def _toBitmap(self, name):
        f = os.path.join(self._sharePath, 'images', '%s.png' % name)
        return wx.Image(f, wx.BITMAP_TYPE_PNG).ConvertToBitmap()

    def _reset(self):
        dw = os.path.join(self._dotPath, "world.wld")
        if os.path.exists(dw):
            self._openWorld(dw)
        else:
            self.world = maze.World(self)

    def OnNew(self, e):
        self._cpu.stop()
        self._editor.Text = ""

    def _openProgram(self, fn):
        with open(fn) as f:
            p = f.read()
        self._cpu.stop()
        self._editor.Text = p

    def _saveProgram(self, fn):
        with open(fn, "w") as f:
            f.write(self._editor.Text)

    def _openWorld(self, fn):
        with open(fn) as f:
            w = json.load(f)
        self._cpu.stop()
        self.world = maze.World(self, w)

    def _saveWorld(self, fn):
        with open(fn, "w") as f:
            json.dump(self.world.staterep, f,
                indent=4, sort_keys = True)

    def OnOpen(self, e):
        dlg = wx.FileDialog(self,
            message="Open program...",
            wildcard="RUR programs (*.rur)|*.rur",
            style = wx.OPEN | wx.CHANGE_DIR)
        if dlg.ShowModal() != wx.ID_OK:
            return
        self._openProgram(dlg.GetPath())
        dlg.Destroy()
        
    def OnSave(self, e):
        pass
    
    def OnSaveAs(self, e):
        dlg = wx.FileDialog(self,
            message="Save program as...",
            wildcard="RUR programs (*.rur)|*.rur",
            style = wx.SAVE | wx.CHANGE_DIR)
        if dlg.ShowModal() != wx.ID_OK:
            return
        self._saveProgram(dlg.GetPath())
        dlg.Destroy()
        
    def OnExit(self, e):
        self.Close(True)

    def OnPlay(self, e):
        self._cpu.play()
    
    def OnPause(self, e):
        self._cpu.pause()

    def OnStop(self, e):
        self._cpu.stop()

    def OnStep(self, e):
        self._cpu.step()

    def OnWorldNew(self, e):
        self._world.newDialog()
        
    def OnWorldOpen(self, e):
        dlg = wx.FileDialog(self,
            message="Open world...",
            wildcard="Worlds (*.wld)|*.wld",
            style = wx.OPEN | wx.CHANGE_DIR)
        if dlg.ShowModal() != wx.ID_OK:
            return
        self._openWorld(dlg.GetPath())
        self._saveWorld(os.path.join(self._dotPath, "world.wld"))
        dlg.Destroy()
        
    def OnWorldSave(self, e):
        pass
    
    def OnWorldSaveAs(self, e):
        dlg = wx.FileDialog(self,
            message="Save world as...",
            wildcard="Worlds (*.wld)|*.wld",
            style = wx.SAVE | wx.CHANGE_DIR)
        if dlg.ShowModal() != wx.ID_OK:
            return
        self._saveWorld(dlg.GetPath())
        dlg.Destroy()
        
    def OnAbout(self, e):
        d = wx.MessageDialog(self, "RUR-PLE 2, A Python Learning Environment \n"
                            "by André Roberge and Paul Crowley","About RUR-PLE 2", wx.OK)
        d.ShowModal()
        d.Destroy()
    
    def OnSlide(self, e):
        self._cpu.setLineTime(int(0.5 + self._slideScale.fromTicks(self._slider.Value)))

    # read by world
    @property
    def log(self):
        return self._logWindow

    # read by cpu
    @property
    def program(self):
        return self._editor.Text

    # read by cpu
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
            mi = self._worldMenu.FindItemByPosition(self._worldMenuItems)
            if mi is None:
                break
            self._worldMenu.Delete(mi.Id)
        for b, e in self._world.menu(self._worldMenu):
            self.Bind(wx.EVT_MENU, b, e)
        #sps.SetSizeHints(sp)

    # called by cpu
    def traceLine(self, line):
        self._editor.mark = line
    
    # called by cpu
    def starting(self):
        self._world.editable = False
        self._editor.ReadOnly = True
        self._saveProgram(os.path.join(self._dotPath, "program.rur"))
        self._saveWorld(os.path.join(self._dotPath, "world.wld"))
        self._logWindow.clear()
        self._world.runStart()

    # called by cpu
    def playing(self):    
        self._toolbar.ToggleTool(self._playTool.Id, True)

    def pausing(self):
        self._toolbar.ToggleTool(self._pauseTool.Id, True)
    
    # called by cpu
    def stopped(self):
        self._toolbar.ToggleTool(self._stopTool.Id, True)
        self._editor.mark = None
        self._world.editable = True
        self._editor.ReadOnly = False

    # called by cpu
    def done(self):
        d = wx.MessageDialog(self, message="Your program finished",
            caption = "Program finished",
            style=wx.ICON_INFORMATION | wx.OK)
        d.ShowModal()
        self.stopped()
    
    # called by cpu
    def failed(self, e):
        if isinstance(e, world.WorldException):
            print("Exception on line %s:" % self._editor._mark, 
                e, file=self._logWindow)
            self._world.handleException(self, e)
        else:
            # exceptions are where isinstance is allowed
            if (isinstance(e, SyntaxError) 
                and self._editor.mark is None
                and e.filename == "<string>"):
                self._editor.mark = e.lineno
            print("Exception on line %s:" % self._editor._mark, 
                e, file=self._logWindow)
            d = wx.MessageDialog(self, message=str(e),
                caption = "Error running your program",
                style=wx.ICON_EXCLAMATION | wx.OK)
            d.ShowModal()
        self.stopped()

    # called by world
    def setWorldStatus(self, s):   
        self._statusBar.SetStatusText(s, 1)

class App(wx.App):
    def OnInit(self):
        frame = RurFrame(None, title="RUR-PLE", size=(900,1000))
        frame.Show(True)
        self.SetTopWindow(frame)
        return True

def main():
    app = App(0)
    app.MainLoop()

