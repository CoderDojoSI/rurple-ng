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

from rurple import share, cpu, world, textctrl
import rurple.worlds.maze

class LogScale(object):
    def __init__(self, ticks, lo, hi):
        self._lo = math.log(lo)
        self._r = (math.log(hi) - self._lo) / ticks

    def toTicks(self, x):
        return (math.log(x) - self._lo) / self._r
    
    def fromTicks(self, x):
        return math.exp(x * self._r + self._lo)

# This class is currently a very close friend of ui,
# might be desirable to change that

class Openable(object):
    def __init__(self, ui):
        self._ui = ui
        self._path = None
        self._canSave = False

    @property
    def _wildcard(self):
        return "%s (*.%s)|*.%s" % (
            self._typetext, self._suffix, self._suffix)

    @property
    def _dotfile(self):
        return os.path.join(self._ui._dotPath,
            "%s.%s"% (self._type, self._suffix))

    def opendot(self):
        if not self._openGuard():
            return
        if os.path.isfile(self._dotfile):
            self._open(self._dotfile)
        else:
            self._blankStart()
    
    def savedot(self):
        self._save(self._dotfile)
    
    def _openSample(self, name):
        self._open(share.path("%ss" % self._type, 
            "%s.%s" % (name, self._suffix)))

    # This is annoying - it should just STOP.
    # But only on success.
    def _openGuard(self):
        if self._ui._cpu.state != cpu.STOP:
            self._ui._cpu.pause()
            wx.MessageDialog(self._ui, caption="Program running",
                message = "Please press STOP before doing that\nCannot modify %s while program is running" 
                    % self._type,
                style=wx.ICON_ERROR | wx.OK).ShowModal()
            return False
        return True
        
    def update(self):
        if self._path is not None:
            text = os.path.basename(self._path)
        else:
            text = "None"
        if self._modified():
            prefix = "*"
        else:
            prefix = ""
        #ugly!
        self._ui._statusBar.SetStatusText("%s%s: %s" %
            (prefix, self._type.capitalize(), text), self._statusPos)
    
    def OnNew(self, e):
        if not self._openGuard():
            return
        if self._new():
            self._path = None
            self.update()

    def OnOpen(self, e):
        if not self._openGuard():
            return
        dlg = wx.FileDialog(self._ui,
            message="Open %s..." % self._type,
            wildcard=self._wildcard,
            style = wx.OPEN | wx.CHANGE_DIR)
        if dlg.ShowModal() != wx.ID_OK:
            return
        path = dlg.GetPath()
        dlg.Destroy()
        self._open(path)
        self._path = path
        self._canSave = True
        self.update()

    def OnOpenSample(self, e):
        if not self._openGuard():
            return
        dlg = wx.FileDialog(self._ui,
            message="Open sample %s..." % self._type,
            wildcard=self._wildcard,
            defaultDir = share.path(self._type + "s"), style = wx.OPEN)
        if dlg.ShowModal() != wx.ID_OK:
            return
        path = dlg.GetPath()
        dlg.Destroy()
        self._open(path)
        self._path = path
        self._canSave = False
        self.update()
        
    def OnSave(self, e):
        if self._canSave:
            self._save(self._path)
            self.update()
        else:
            self.OnSaveAs(e)
    
    def OnSaveAs(self, e):
        dlg = wx.FileDialog(self._ui,
            message="Save %s as..." % self._type,
            wildcard=self._wildcard,
            style = wx.SAVE | wx.CHANGE_DIR)
        if dlg.ShowModal() != wx.ID_OK:
            return
        path = dlg.GetPath()
        dlg.Destroy()
        self._save(path)
        self._path = path
        self._canSave = True
        self.update()

class ProgramOpen(Openable):
    _type = "program"
    _typetext = "RUR programs"
    _suffix = "rur"
    _statusPos = 0
    
    def _new(self):
        self._ui._editor.Text = ""
        return True

    def _modified(self):
        return self._ui._editor.Modify
        
    def _open(self, fn):
        self._ui._editor.LoadFile(fn)

    def _save(self, fn):
        self._ui._editor.SaveFile(fn)

    def _blankStart(self):
        self._ui._editor.Text = ""
            
    
class WorldOpen(Openable):
    _type = "world"
    _typetext = "Worlds"
    _suffix = "wld"
    _statusPos = 1

    def _new(self):
        d = rurple.worlds.maze.NewDialog(self._ui)
        if d.ShowModal() != wx.ID_OK:
            return False
        self._ui.world = d.makeWorld(self._ui)
        return True

    def _modified(self):
        return self._ui.world.modified()

    def _open(self, fn):
        with open(fn) as f:
            w = json.load(f)
        w = rurple.worlds.maze.World(self._ui, w)
        w.modifyHook(self)
        self._ui.world = w

    def _save(self, fn):
        with open(fn, "w") as f:
            json.dump(self._ui.world.staterep, f,
                indent=4, sort_keys = True)
        self._ui.world.setModified(False)

    def _blankStart(self):
        self._openSample("blank")        

class RurFrame(wx.Frame):
    def __init__(self, *args, **kw):
        wx.Frame.__init__(self, *args, **kw)
        # FIXME: not right for Windows or MacOS X
        self._dotPath = os.path.expanduser("~/.rurple")
        if not os.path.isdir(self._dotPath):
            os.mkdir(self._dotPath)
        self._programFile = None
        self._worldFile = None
        self._cpu = cpu.CPU(self)
        self._vsash = wx.SplitterWindow(self)
        self._editor = textctrl.PythonEditor(self._vsash)
        self._editor.CodePage = 65001
        self._hsash = wx.SplitterWindow(self._vsash)
        self._worldParent = wx.lib.scrolledpanel.ScrolledPanel(self._hsash)
        self._worldWindow = None
        self._vsash.SplitVertically(self._editor, self._hsash)
        self._logWindow = textctrl.LogWindow(self._hsash)
        self._hsash.SplitHorizontally(self._worldParent, self._logWindow)
        self._worldParent.SetupScrolling()
        
        self._statusBar = self.CreateStatusBar()
        self._statusBar.SetFieldsCount(3)
        self._programO = ProgramOpen(self)
        self._worldO = WorldOpen(self)
        self._programO.opendot()
        self._editor.modifyHook(self._programO)
        menuBar = wx.MenuBar()
        filemenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self._programO.OnNew,
            filemenu.Append(wx.ID_NEW, "&New", "Start a new program"))
        self.Bind(wx.EVT_MENU, self._programO.OnOpen,
            filemenu.Append(wx.ID_OPEN, "&Open...", "Open a program"))
        self.Bind(wx.EVT_MENU, self._programO.OnOpenSample,
            filemenu.Append(wx.ID_ANY, "Open sa&mple...",
                "Open a sample program"))
        self.Bind(wx.EVT_MENU, self._programO.OnSave,
            filemenu.Append(wx.ID_SAVE,"&Save",
                "Save the current program"))
        self.Bind(wx.EVT_MENU, self._programO.OnSaveAs,
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
        self.Bind(wx.EVT_MENU, self._worldO.OnNew,
            self._worldMenu.Append(wx.ID_ANY,"&New...",
                "Start a new world"))
        self.Bind(wx.EVT_MENU, self._worldO.OnOpen,
            self._worldMenu.Append(wx.ID_ANY,"&Open...", "Open a world"))
        self.Bind(wx.EVT_MENU, self._worldO.OnOpenSample,
            self._worldMenu.Append(wx.ID_ANY, "Open sa&mple...",
                "Open a sample world"))
        self.Bind(wx.EVT_MENU, self._worldO.OnSave,
            self._worldMenu.Append(wx.ID_ANY,"&Save",
                "Save the current world"))
        self.Bind(wx.EVT_MENU, self._worldO.OnSaveAs,
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
                share.toBitmap('reset_world'),
                shortHelp = "Reset world (Ctrl+R)"))
        self._runTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY,
            "Run", share.toBitmap('run'),
            shortHelp="Run program (F8)")
        self.Bind(wx.EVT_TOOL, self.OnRun, self._runTool)
        self._pauseTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY,
             "Pause", share.toBitmap('pause'),
             shortHelp="Pause program")
        self.Bind(wx.EVT_TOOL, self.OnPause, self._pauseTool)
        self._stopTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY,
             "Stop", share.toBitmap('stop'),
             shortHelp="Stop program (Ctrl+F2)")
        self.Bind(wx.EVT_TOOL, self.OnStop, self._stopTool)
        self.Bind(wx.EVT_TOOL, self.OnStep,
            self._toolbar.AddLabelTool(wx.ID_ANY, "step",
                share.toBitmap('step'),
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

    def _reset(self):
        self._worldO.opendot()

    # Should be some sort of onClose
    def OnExit(self, e):
        #self._saveProgram(os.path.join(self._dotPath, "program.rur"))
        #self._saveWorld(os.path.join(self._dotPath, "world.wld"))
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

    def OnAbout(self, e):
        info = wx.AboutDialogInfo()
        info.Name = "Rurple NG"
        info.Version = "0.1"
        info.Copyright = "Copyright 2009 André Roberge and Paul Crowley"
        info.Description = wx.lib.wordwrap.wordwrap(
            "A friendly learning environment for beginners to programming."
            "To get started, have a look at the manual",
            350, wx.ClientDC(self))
        info.WebSite = (share.path("html", "index.html"), "Rurple NG manual")
        info.Developers = ["André Roberge", "Paul Crowley"]
        with open(share.path("COPYING.txt")) as f:
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
        self._programO.savedot()
        self._worldO.savedot()
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
        self._statusBar.SetStatusText(s, 2)

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

