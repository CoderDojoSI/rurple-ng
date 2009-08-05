from __future__ import division, print_function

import sys
import math
import wx
from wx.lib.scrolledpanel import ScrolledPanel
import wx.stc

from rurple import maze, cpu

def toBitmap(name):
    return wx.Image('images/%s.png' % name, wx.BITMAP_TYPE_PNG).ConvertToBitmap()

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
        self._cpu = cpu.CPU(self)
        mymaze = maze.Maze(10, 10)
        self._robot = maze.Robot(mymaze)
        mymaze.AddObject(self._robot)
        
        sash = wx.SplitterWindow(self)
        self._stc = PythonEditor(sash)
        self._stc.AddText("""
for i in range(4):
    move()
    turn_left()
""")
        hsash = wx.SplitterWindow(sash)
        sp = ScrolledPanel(hsash)
        maze.EditableMazeWindow(sp, size=(900,900), maze=mymaze)
        sash.SplitVertically(self._stc, hsash)
        hsash.SplitHorizontally(sp, PythonEditor(hsash))
        sp.SetupScrolling()
        
        self.CreateStatusBar()
        menuBar = wx.MenuBar()
        filemenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnAbout,
            filemenu.Append(wx.ID_ABOUT, "&About..."," Information about this program"))
        filemenu.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.OnExit,
            filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program"))
        menuBar.Append(filemenu,"&File")
        self.SetMenuBar(menuBar)
        self._toolbar = self.CreateToolBar()
        tsize = (24,24)
        self._toolbar.SetToolBitmapSize(tsize)
        self._playTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY, "Play",
            toBitmap('play'), shortHelp="Play")
        self.Bind(wx.EVT_TOOL, (lambda e: self._cpu.Play()), self._playTool)
        self._pauseTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY, "pause",
            toBitmap('pause'), shortHelp="pause")
        self.Bind(wx.EVT_TOOL, (lambda e: self._cpu.Pause()), self._pauseTool)
        self._stopTool = self._toolbar.AddRadioLabelTool(wx.ID_ANY, "stop",
            toBitmap('stop'), shortHelp="stop")
        self.Bind(wx.EVT_TOOL, (lambda e: self._cpu.Stop()), self._stopTool)
        self._stepTool = self._toolbar.AddLabelTool(wx.ID_ANY, "step",
            toBitmap('step'), shortHelp="step")
        self.Bind(wx.EVT_TOOL, self.OnStep, self._stepTool)
        self._toolbar.ToggleTool(self._stopTool.Id, True)
        self._slideScale = LogScale(100, 3000, 100)
        self._slider = wx.Slider(self._toolbar, size=(250,-1), 
            value=int(0.5 +  self._slideScale.toTicks(1000)))
        self.Bind(wx.EVT_SLIDER, self.OnSlide, self._slider)
        self.OnSlide(None)
        self._toolbar.AddControl(self._slider)
        
    def OnAbout(self, e):
        d = wx.MessageDialog(self, " A test application \n"
                            " in wxPython","About test app", wx.OK)
        d.ShowModal()
        d.Destroy()
    
    def OnExit(self, e):
        self.Close(True)

    def OnStep(self, e):
        # FIXME: bit inelegant this
        self._toolbar.ToggleTool(self._pauseTool.Id, True)
        self._cpu.Step()

    def OnSlide(self, e):
        #print(e, dir(e))
        self._cpu.setLineTime(int(0.5 + self._slideScale.fromTicks(self._slider.Value)))

    def program(self):
        return self._stc.GetText()

    def getGlobals(self, t):
        return {
            "move": t.ProxyFunction(self._robot.move),
            "turn_left": t.ProxyFunction(self._robot.turn_left)
        }

    def traceLine(self, line):
        self._stc.mark(line)
    
    def done(self, e):
        print("Done, exception:", e)
        self._toolbar.ToggleTool(self._stopTool.Id, True)

class App(wx.App):
    def OnInit(self):
        frame = RurFrame(None, title="This is a test", size=(900,1000))
        frame.Show(True)
        self.SetTopWindow(frame)
        return True

def main():
    app = App(0)
    app.MainLoop()

