# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals, with_statement

import wx
import wx.stc

class PythonEditor(wx.stc.StyledTextCtrl):
    MARK_RUNNING = 7

    def __init__(self, *a, **kw):
        wx.stc.StyledTextCtrl.__init__(self, *a, **kw)
        self.MarkerDefine(self.MARK_RUNNING, wx.stc.STC_MARK_BACKGROUND, 'white', 'wheat')
        self.UseHorizontalScrollBar = False
        self._mark = None

    @property
    def mark(self):
        return self._mark

    @mark.setter
    def mark(self, line):
        if self._mark is not None:
            self.MarkerDelete(self._mark -1, self.MARK_RUNNING)
        self._mark = line
        if self._mark is not None:
            self.MarkerAdd(self._mark -1, self.MARK_RUNNING)

class LogWindow(wx.stc.StyledTextCtrl):
    def __init__(self, *a, **kw):
        wx.stc.StyledTextCtrl.__init__(self, *a, **kw)
        self.ReadOnly = True
        self.UseHorizontalScrollBar = False

    def write(self, s):
        self.ReadOnly = False
        self.AddText(s)
        self.ReadOnly = True
        self.EnsureCaretVisible()
        
    def clear(self):
        self.SetText("")


