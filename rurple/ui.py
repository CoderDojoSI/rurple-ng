# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals, with_statement

import sys
import math
import os
import os.path
import codecs
import json
import wx
import wx.lib.scrolledpanel
import wx.lib.wordwrap

from rurple import cpu, world, textctrl
import rurple.worlds.maze

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
        self._sharePath = os.path.abspath("share")
        self._programFile = None
        self._worldFile = None
        self._cpu = cpu.CPU(self)
        self._vsash = wx.SplitterWindow(self)
        self._editor = textctrl.PythonEditor(self._vsash)
        dp = os.path.join(self._dotPath, "program.rur")
        if os.path.exists(dp):
            self._openProgram(dp)
        self._hsash = wx.SplitterWindow(self._vsash)
        self._worldParent = wx.lib.scrolledpanel.ScrolledPanel(self._hsash)
        self._worldWindow = None
        self._vsash.SplitVertically(self._editor, self._hsash)
        self._logWindow = textctrl.LogWindow(self._hsash)
        self._hsash.SplitHorizontally(self._worldParent, self._logWindow)
        self._worldParent.SetupScrolling()
        
        self._statusBar = self.CreateStatusBar()
        self._statusBar.SetFieldsCount(2)
        self._statusBar.SetStatusWidths([-1,-1])
        menuBar = wx.MenuBar()
        filemenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnNew,
            filemenu.Append(wx.ID_NEW, "&New", "Start a new program"))
        self.Bind(wx.EVT_MENU, self.OnOpen,
            filemenu.Append(wx.ID_OPEN, "&Open...", "Open a program"))
        self.Bind(wx.EVT_MENU, self.OnOpenSample,
            filemenu.Append(wx.ID_ANY, "Open sa&mple...",
                "Open a sample program"))
        self.Bind(wx.EVT_MENU, self.OnSave,
            filemenu.Append(wx.ID_SAVE,"&Save",
                "Save the current program"))
        self.Bind(wx.EVT_MENU, self.OnSaveAs,
            filemenu.Append(wx.ID_SAVEAS,"Save &As...",
                "Save the current program with a different filename"))
        filemenu.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.OnExit,
            filemenu.Append(wx.ID_EXIT,"E&xit", "Close Rurple"))
        menuBar.Append(filemenu,"&File")
        runmenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnRun,
            runmenu.Append(wx.ID_ANY,"&Run\tF8",
                "Start the program running"))
        self.Bind(wx.EVT_MENU, self.OnPause,
            runmenu.Append(wx.ID_ANY,"&Pause", "Pause the program"))
        self.Bind(wx.EVT_MENU, self.OnStop,
            runmenu.Append(wx.ID_ANY,"S&top\tCtrl+F2",
                "Stop the program"))
        self.Bind(wx.EVT_MENU, self.OnStep,
            runmenu.Append(wx.ID_ANY,"&Step\tF5",
                "Step one line of the program"))
        menuBar.Append(runmenu,"&Run")
        
        self._worldMenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnWorldReset,
            self._worldMenu.Append(wx.ID_ANY,"&Reset\tCtrl+R",
                "Reset world to before program was run"))
        self._worldMenu.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.OnWorldNew,
            self._worldMenu.Append(wx.ID_ANY,"&New...",
                "Start a new world"))
        self.Bind(wx.EVT_MENU, self.OnWorldOpen,
            self._worldMenu.Append(wx.ID_ANY,"&Open...", "Open a world"))
        self.Bind(wx.EVT_MENU, self.OnWorldOpenSample,
            self._worldMenu.Append(wx.ID_ANY, "Open sa&mple...",
                "Open a sample world"))
        self.Bind(wx.EVT_MENU, self.OnWorldSave,
            self._worldMenu.Append(wx.ID_ANY,"&Save",
                "Save the current world"))
        self.Bind(wx.EVT_MENU, self.OnWorldSaveAs,
            self._worldMenu.Append(wx.ID_ANY,"Save &As...",
                "Save the current world with a different filename"))
        self._worldMenu.AppendSeparator()
        self._worldMenuItems = self._worldMenu.MenuItemCount
        menuBar.Append(self._worldMenu,"&World")
        helpmenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnAbout,
            helpmenu.Append(wx.ID_ABOUT, "&About...\tF1",
                "Information about Rurple"))
        menuBar.Append(helpmenu,"&Help")
        self.SetMenuBar(menuBar)
        self._toolbar = self.CreateToolBar()
        tsize = (24,24)
        self._toolbar.SetToolBitmapSize(tsize)
        self.Bind(wx.EVT_TOOL, self.OnWorldReset,
            self._toolbar.AddLabelTool(wx.ID_ANY, "Reset",
                self._toBitmap('reset_world'),
                shortHelp = "Reset world (Ctrl+R)"))
        self._runTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY,
            "Run", self._toBitmap('run'),
            shortHelp="Run program (F8)")
        self.Bind(wx.EVT_TOOL, self.OnRun, self._runTool)
        self._pauseTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY,
             "Pause", self._toBitmap('pause'),
             shortHelp="Pause program")
        self.Bind(wx.EVT_TOOL, self.OnPause, self._pauseTool)
        self._stopTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY,
             "Stop", self._toBitmap('stop'),
             shortHelp="Stop program (Ctrl+F2)")
        self.Bind(wx.EVT_TOOL, self.OnStop, self._stopTool)
        self.Bind(wx.EVT_TOOL, self.OnStep,
            self._toolbar.AddLabelTool(wx.ID_ANY, "step",
                self._toBitmap('step'),
                shortHelp="Step program (F5)"))
        self._toolbar.ToggleTool(self._stopTool.Id, True)
        self._slideScale = LogScale(100, 3000, 2)
        self._slider = wx.Slider(self._toolbar, size=(250,-1),
            value=int(0.5 +  self._slideScale.toTicks(300)))
        self.Bind(wx.EVT_SLIDER, self.OnSlide, self._slider)
        self.OnSlide(None)
        self._toolbar.AddControl(self._slider)
        self._toolbar.Realize()
        self._reset()
        w, h = self.Size
        dw, dh = self._worldWindow.size()
        self._vsash.SashGravity = 1
        self._hsash.SashPosition = min(h, dh + 20)
        self._vsash.SashPosition = max(0, w - (dw + 30))

    def _toBitmap(self, name):
        f = os.path.join(self._sharePath, 'images', '%s.png' % name)
        return wx.Image(f, wx.BITMAP_TYPE_PNG).ConvertToBitmap()

    def _reset(self):
        dw = os.path.join(self._dotPath, "world.wld")
        if os.path.exists(dw):
            self._openWorld(dw)
        else:
            self._openWorld(os.path.join(self._sharePath,
                "worlds", "blank.wld"))

    def OnNew(self, e):
        self._cpu.stop()
        self._editor.Text = ""

    def _openProgram(self, fn):
        with codecs.open(fn, encoding="utf-8") as f:
            p = f.read()
        self._cpu.stop()
        self._editor.Text = p

    def _saveProgram(self, fn):
        with codecs.open(fn, "w", encoding="utf-8") as f:
            f.write(self.program)

    def _openWorld(self, fn):
        with open(fn) as f:
            w = json.load(f)
        self._cpu.stop()
        self.world = rurple.worlds.maze.World(self, w)

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
        self._programFile = dlg.GetPath()
        self._openProgram(self._programFile)
        dlg.Destroy()
        
    def OnOpenSample(self, e):
        dlg = wx.FileDialog(self,
            message="Open sample program...",
            wildcard="RUR programs (*.rur)|*.rur",
            defaultDir = os.path.join(self._sharePath, "programs"),
            style = wx.OPEN)
        if dlg.ShowModal() != wx.ID_OK:
            return
        self._programFile = None
        self._openProgram(dlg.GetPath())
        dlg.Destroy()
        
    def OnSave(self, e):
        if self._programFile is None:
            self.OnSaveAs(e)
        else:
            self._saveProgram(self._programFile)
    
    def OnSaveAs(self, e):
        dlg = wx.FileDialog(self,
            message="Save program as...",
            wildcard="RUR programs (*.rur)|*.rur",
            style = wx.SAVE | wx.CHANGE_DIR)
        if dlg.ShowModal() != wx.ID_OK:
            return
        self._programFile = dlg.GetPath()
        self._saveProgram(self._programFile)
        dlg.Destroy()
        
    def OnExit(self, e):
        self._saveProgram(os.path.join(self._dotPath, "program.rur"))
        self._saveWorld(os.path.join(self._dotPath, "world.wld"))
        self.Close(True)

    def OnRun(self, e):
        self._cpu.run()
    
    def OnPause(self, e):
        self._cpu.pause()

    def OnStop(self, e):
        self._cpu.stop()

    def OnStep(self, e):
        self._cpu.step()

    def OnWorldReset(self, e):
        self._reset()

    def OnWorldNew(self, e):
        if not self._cpu.state == cpu.STOP:
            wx.MessageDialog(self._ui, caption="Program running",
                message = "Cannot edit world while program is running",
                style=wx.ICON_ERROR | wx.OK).ShowModal()
            return
        d = rurple.worlds.maze.NewDialog(self)
        if d.ShowModal() == wx.ID_OK:
            self.world = d.makeWorld(self)
                
    def OnWorldOpen(self, e):
        dlg = wx.FileDialog(self,
            message="Open world...",
            wildcard="Worlds (*.wld)|*.wld",
            style = wx.OPEN | wx.CHANGE_DIR)
        if dlg.ShowModal() != wx.ID_OK:
            return
        self._worldFile = dlg.GetPath()
        self._openWorld(self._worldFile)
        self._saveWorld(os.path.join(self._dotPath, "world.wld"))
        dlg.Destroy()
        
    def OnWorldOpenSample(self, e):
        dlg = wx.FileDialog(self,
            message="Open sample world...",
            wildcard="Worlds (*.wld)|*.wld",
            defaultDir = os.path.join(self._sharePath, "worlds"),
            style = wx.OPEN)
        if dlg.ShowModal() != wx.ID_OK:
            return
        self._worldFile = None
        self._openWorld(dlg.GetPath())
        self._saveWorld(os.path.join(self._dotPath, "world.wld"))
        dlg.Destroy()
        
    def OnWorldSave(self, e):
        if self._worldFile is None:
            self.OnWorldSaveAs(e)
        else:
            self._saveWorld(self._worldFile)
    
    def OnWorldSaveAs(self, e):
        dlg = wx.FileDialog(self,
            message="Save world as...",
            wildcard="Worlds (*.wld)|*.wld",
            style = wx.SAVE | wx.CHANGE_DIR)
        if dlg.ShowModal() != wx.ID_OK:
            return
        self._worldFile = dlg.GetPath()
        self._saveWorld(self._worldFile)
        dlg.Destroy()
        
    def OnAbout(self, e):
        info = wx.AboutDialogInfo()
        info.Name = "Rurple NG"
        info.Version = "0.1"
        info.Copyright = "Copyright 2009 André Roberge and Paul Crowley"
        info.Description = wx.lib.wordwrap.wordwrap(
            "A friendly learning environment for beginners to programming."
            "To get started, have a look at the manual",
            350, wx.ClientDC(self))
        manual = os.path.join(self._sharePath, "html", "index.html")
        info.WebSite = (manual, "Rurple NG manual")
        info.Developers = ["André Roberge", "Paul Crowley"]
        with open(os.path.join(self._sharePath, "COPYING.txt")) as f:
            #info.License = wx.lib.wordwrap.wordwrap(
            #    f.read(), 500, wx.ClientDC(self))
            info.License = f.read().replace("\f", "")
        wx.AboutBox(info)
        
    def OnSlide(self, e):
        self._cpu.setLineTime(int(0.5 + self._slideScale.fromTicks(self._slider.Value)))

    # read by world
    @property
    def log(self):
        return self._logWindow

    # read by cpu
    @property
    def program(self):
        return self._editor.Text.replace("\r\n", "\n")

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
        while self._worldMenuItems < self._worldMenu.MenuItemCount:
            mi = self._worldMenu.FindItemByPosition(self._worldMenuItems)
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
    def running(self):
        self._toolbar.ToggleTool(self._runTool.Id, True)

    # called by cpu
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
            print("Exception on line %s:" % self._editor.mark,
                e, file=self._logWindow)
            self._world.handleException(self, e)
        else:
            # exceptions are where isinstance is allowed
            if (isinstance(e, SyntaxError)
                and self._editor.mark is None
                and e.filename == "<string>"):
                self._editor.mark = e.lineno
            print("Exception on line %s:" % self._editor.mark,
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
        w, h = wx.DisplaySize()
        frame = RurFrame(None, title="Rurple", size=(int(w*0.85), int(h*0.85)))
        frame.Show(True)
        self.SetTopWindow(frame)
        return True

def main():
    app = App(0)
    app.MainLoop()

