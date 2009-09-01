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

from rurple import share, cpu, world, textctrl, listctrl
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

    def _suffixPath(self, path):
        s = "." + self._suffix
        if path.endswith(s):
            return path
        return path + s

    def _tildeSave(self, path):
        if os.path.exists(path):
            t = path + "~"
            if os.path.exists(t):
                os.remove(t)
            os.rename(path, t)
            self._tildeSave(path)
        self._save(path)
    
    def opendot_again(self):
        if not self._openGuard():
            return
        self.opendot_init()

    def opendot_init(self):
        if os.path.isfile(self._dotfile):
            self._open(self._dotfile)
        else:
            self._blankStart()
        self.update()
    
    def savedot(self):
        self._tildeSave(self._dotfile)
    
    def _openSample(self, name):
        self._open(share.path("%ss" % self._type, 
            "%s.%s" % (name, self._suffix)))

    # This is annoying - it should just STOP.
    # But only on success...
    def _openGuard(self):
        if self._ui._cpu.state == cpu.STOP:
            return True
        self._ui._cpu.pause()
        wx.MessageDialog(self._ui, caption="Program running",
            message = "Please press STOP before doing that\nCannot modify %s while program is running" 
                % self._type,
            style=wx.ICON_ERROR | wx.OK).ShowModal()
        return False
       
    def _modGuard(self):
        if not self._modified():
            return True
        code = wx.MessageDialog(self._ui, caption="Save %s first?" % self._type,
            message = "Save your changes to the %s before replacing it?" 
                % self._type,
            style=wx.ICON_EXCLAMATION | wx.YES_NO | wx.CANCEL).ShowModal()
        if code == wx.ID_CANCEL:
            return False
        elif code == wx.ID_NO:
            return True
        else:
            return self.OnSave(None)
            

    def _exception(self, t, e):
        wx.MessageDialog(self._ui, 
            caption="%s failed" % t.capitalize(),
            message = str(e),
            style=wx.ICON_ERROR | wx.OK).ShowModal()
        
    def update(self):
        if self._modified():
            prefix = "*"
        else:
            prefix = ""
        if self._path is not None:
            text = "%s%s: %s" % (prefix, self._type.capitalize(),
                os.path.basename(self._path))
        else:
            text = "%sNo %s open" % (prefix, self._type)
        #ugly!
        self._ui._statusBar.SetStatusText(text, self._statusPos)
    
    def OnNew(self, e):
        if not self._openGuard() or not self._modGuard():
            return
        if self._new():
            self._path = None
            self._clearModified()

    def OnOpen(self, e):
        if not self._openGuard() or not self._modGuard():
            return
        dlg = wx.FileDialog(self._ui,
            message="Open %s..." % self._type,
            wildcard=self._wildcard,
            style = wx.OPEN | wx.CHANGE_DIR)
        if dlg.ShowModal() != wx.ID_OK:
            return
        path = self._suffixPath(dlg.GetPath())
        dlg.Destroy()
        try:
            self._open(path)
        except Exception, e:
            self._exception("open", e)
        else:
            self._path = path
            self._canSave = True
            self._clearModified()

    def OnOpenSample(self, e):
        if not self._openGuard() or not self._modGuard():
            return
        dlg = wx.FileDialog(self._ui,
            message="Open sample %s..." % self._type,
            wildcard=self._wildcard,
            defaultDir = share.path(self._type + "s"), style = wx.OPEN)
        if dlg.ShowModal() != wx.ID_OK:
            return
        path = self._suffixPath(dlg.GetPath())
        dlg.Destroy()
        try:
           self._open(path)
        except Exception, e:
            self._exception("open", e)
        else:
            self._path = path
            self._canSave = False
            self._clearModified()
            
    def OnSave(self, e):
        if self._canSave:
            self._tildeSave(self._path)
            self._clearModified()
            return True
        else:
            return self.OnSaveAs(e)
    
    def OnSaveAs(self, e):
        dlg = wx.FileDialog(self._ui,
            message="Save %s as..." % self._type,
            wildcard=self._wildcard,
            style = wx.SAVE | wx.CHANGE_DIR)
        if dlg.ShowModal() != wx.ID_OK:
            return False
        path = self._suffixPath(dlg.GetPath())
        dlg.Destroy()
        if os.path.exists(path):
            d = wx.MessageDialog(self._ui, 
                caption="Overwrite file?",
                message = "There already is a %s of that name. Replace it with your %s?"
                    % (self._type, self._type),
                style=wx.ICON_QUESTION | wx.OK | wx.CANCEL)
            if d.ShowModal() != wx.ID_OK:
                return False
        try:
            self._tildeSave(path)
        except Exception, e:
            self._exception("save", e)
        else:
            self._path = path
            self._canSave = True
            self._clearModified()
            return True

class ProgramOpen(Openable):
    _type = "program"
    _typetext = "RUR programs"
    _suffix = "rur"
    _statusPos = 0
    
    def _new(self):
        self._ui._editor.Text = ""
        return True

    def _modified(self):
        return self._ui._editor.modified
    
    def _clearModified(self):
        self._ui._editor.clearModified()
        self.update()
    
    def _open(self, fn):
        with codecs.open(fn, encoding="utf-8") as f:
            p = f.read()
        self._ui._editor.Text = p

    def _save(self, fn):
        with codecs.open(fn, "w", encoding="utf-8") as f:
            f.write(self._ui.program)

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
        return self._ui.world.modified
    
    def _clearModified(self):
        self._ui._world.modified = False
        self.update()
    
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
        self._notebook = wx.Notebook(self._hsash)
        self._logWindow = textctrl.LogWindow(self._notebook)
        self._notebook.AddPage(self._logWindow, "Log")
        self._vars = listctrl.ListCtrl(self._notebook, 
            style = wx.LC_REPORT|wx.LC_HRULES)
        self._vars.InsertColumn(0, "Variable")
        self._vars.InsertColumn(1, "Value")
        self._notebook.AddPage(self._vars, "Variables")
        self._hsash.SplitHorizontally(self._worldParent, self._notebook)
        self._worldParent.SetupScrolling()
        self._statusBar = self.CreateStatusBar()    
        self._statusBar.SetFieldsCount(3)
        self._programO = ProgramOpen(self)
        self._worldO = WorldOpen(self)
        self._programO.opendot_init()
        # ugly!
        self._programO._clearModified()
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
                shortHelp = "Reset world (Ctrl+R)",
                longHelp = "Put world back the way it was when your program started"))
        self._toolbar.AddSeparator()
        self._runTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY,
            "Run", share.toBitmap('run'),
            shortHelp="Run program (F8)",
            longHelp="Start your program running")
        self.Bind(wx.EVT_TOOL, self.OnRun, self._runTool)
        self._pauseTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY,
             "Pause", share.toBitmap('pause'),
             shortHelp="Pause program",
             longHelp="Pause your program")
        self.Bind(wx.EVT_TOOL, self.OnPause, self._pauseTool)
        self._stopTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY,
             "Stop", share.toBitmap('stop'),
             shortHelp="Stop program (Ctrl+F2)",
             longHelp="Finish your program early")
        self.Bind(wx.EVT_TOOL, self.OnStop, self._stopTool)
        self.Bind(wx.EVT_TOOL, self.OnStep,
            self._toolbar.AddLabelTool(wx.ID_ANY, "step",
                share.toBitmap('step'),
                shortHelp="Step program (F5)",
                longHelp="Execute only the current line of your program"))
        self._toolbar.ToggleTool(self._stopTool.Id, True)
        self._toolbar.AddSeparator()
        self._toolbar.AddControl(
            wx.StaticText(self._toolbar, label="Speed:"))
        self._slideScale = LogScale(100, 2000, 5)
        self._slider = wx.Slider(self._toolbar, size=(250,-1),
            value=int(0.5 +  self._slideScale.toTicks(300)))
        self.Bind(wx.EVT_SLIDER, self.OnSlide, self._slider)
        self.OnSlide(None)
        self._toolbar.AddControl(self._slider)
        self._toolbar.Realize()
        self._worldO.opendot_init()
        w, h = self.Size
        dw, dh = self._worldWindow.size()
        self._vsash.SashGravity = 1
        self._hsash.SashPosition = min(h, dh + 20)
        self._vsash.SashPosition = max(0, w - (dw + 30))
        self.Bind(wx.EVT_CLOSE, self.OnClose, self)

    def _reset(self):
        self._worldO.opendot_again()

    def OnClose(self, e):
        self._programO.savedot()
        if self._cpu.state == cpu.STOP:
            self._worldO.savedot()
        self.Destroy()

    def OnExit(self, e):
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
        info.Version = "0.5"
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
        self._cpu.setLineTime(self._slideScale.fromTicks(self._slider.Value))

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
    def trace(self, frame):
        self._editor.mark = frame.f_lineno
        self._vars.DeleteAllItems()
        function = type(lambda:None)
        for k in sorted(frame.f_locals.iterkeys()):
            if k.startswith("__"):
                continue
            v = frame.f_locals[k]
            if type(v) == function:
                continue
            idx = self._vars.InsertStringItem(self._vars.ItemCount, k)
            self._vars.SetStringItem(idx, 1, repr(v))
    
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

