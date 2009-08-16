# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals, with_statement

import re
import keyword

import wx
from wx import stc

if wx.Platform == '__WXMSW__':
    faces = { 'mono' : 'Courier New',
              'helv' : 'Arial',
              'size' : 11,
              'size2': 8,
             }
elif wx.Platform == '__WXMAC__':
    faces = { 'mono' : 'Courier New',
              'helv' : 'Arial',
              'size' : 16,
              'size2': 10,
             }
else:
    faces = { 'mono' : 'Courier',
              'helv' : 'Helvetica',
              'size' : 11,
              'size2': 9,
             }

class PythonEditor(stc.StyledTextCtrl):
    MARK_RUNNING = 7

    _styleSpecs = [
        (stc.STC_P_DEFAULT,
            "fore:#000000,face:%(mono)s,size:%(size)d"),
        (stc.STC_P_COMMENTLINE,
            "fore:#009900,face:%(mono)s,size:%(size)d"),
        (stc.STC_P_NUMBER,
            "fore:#FF0000,bold,size:%(size)d"),
        (stc.STC_P_STRING,
            "fore:#660066,face:%(mono)s,size:%(size)d"),
        (stc.STC_P_CHARACTER, # Single quoted string
            "fore:#660066,face:%(mono)s,size:%(size)d"),
        (stc.STC_P_WORD, # Keyword
            "fore:#336699,bold,face:%(mono)s,size:%(size)d"),
        (stc.STC_P_TRIPLE, # Triple quotes
            "fore:#660066,size:%(size)d"),
        (stc.STC_P_TRIPLEDOUBLE, # Triple double quotes
            "fore:#660066,size:%(size)d"),
        (stc.STC_P_CLASSNAME, # Class name definition
            "fore:#000099,bold,underline,face:%(mono)s,size:%(size)d"),
        (stc.STC_P_DEFNAME, # Function or method name definition
            "fore:#3333ff,bold,face:%(mono)s,size:%(size)d"),
        (stc.STC_P_OPERATOR,
            "bold,size:%(size)d"),
        (stc.STC_P_IDENTIFIER,
            "fore:#000000,face:%(mono)s,size:%(size)d"),
        (stc.STC_P_COMMENTBLOCK,
            "fore:#7F7F7F,size:%(size)d"),
        (stc.STC_P_STRINGEOL, # End of line where string is not closed
            "fore:#000000,face:%(mono)s,back:#E0C0E0,eol,size:%(size)d"),
        (stc.STC_STYLE_INDENTGUIDE, "fore:#333333"),
        (stc.STC_STYLE_LINENUMBER,
            "back:#99AACC,face:%(helv)s,size:%(size2)d"),
    ]

    def __init__(self, *a, **kw):
        stc.StyledTextCtrl.__init__(self, *a, **kw)
        self.MarkerDefine(self.MARK_RUNNING,
            stc.STC_MARK_BACKGROUND, 'white', 'wheat')
        self.UseHorizontalScrollBar = False
        self.Margins = (2, 2)
        self.SetMarginType(1, stc.STC_MARGIN_NUMBER)
        # Reasonable (?) value for 4 digits using a small mono font (33 pixels)
        self.SetMarginWidth(1, 33)
        self.SetProperty("fold", "1")
        self.SetProperty("tab.timmy.whinge.level", "1")
        for styleNum, spec in self._styleSpecs:
            self.StyleSetSpec(styleNum, spec % faces),
        # Python styles ----------------------------------------
        self.SetLexer(stc.STC_LEX_PYTHON)
        kl = set(keyword.kwlist) | set(['None', 'True', 'False'])
        kl.remove('print')
        self.SetKeyWords(0, " ".join(kl))
        self.Indent = 4
        self.IndentationGuides = True
        self.BackSpaceUnIndents = True
        self.TabIndents = True
        self.TabWidth = 4
        self.UseTabs = False

        self._mark = None
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

    def OnKeyPressed(self, event):
        key = event.GetKeyCode()
        # Indentation
        if key == wx.WXK_RETURN:
            ind = "\n"
            m = re.match(" +", self.CurLine[0])
            if m:
                ind += m.group(0)
            if chr(self.GetCharAt(self.GetCurrentPos()-1)) == ":":
                ind += "    "
            self.AddText(ind)
        else:
            event.Skip(True)

    def modifyHook(self,opener):
        self.Bind(wx.stc.EVT_STC_MODIFIED, lambda e: opener.update(), self)

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
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
            "face:%(mono)s,size:%(size)d" % faces)

    def write(self, s):
        self.ReadOnly = False
        self.AddText(s)
        self.ReadOnly = True
        self.EnsureCaretVisible()
        
    def clear(self):
        self.ReadOnly = False
        self.SetText("")
        self.ReadOnly = True


