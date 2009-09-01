from __future__ import division, print_function, unicode_literals

import wx

class ListCtrl(wx.ListCtrl):
    def __init__(self, *a, **kw):
        wx.ListCtrl.__init__(self, *a, **kw)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_LIST_COL_END_DRAG, self.OnSize)
    
    def OnSize(self, e):
        e.Skip()
        w, h = self.ClientSize
        cc = self.ColumnCount
        if cc < 1:
            return
        for i in range(cc -1):
            w -= self.GetColumnWidth(i)
        self.SetColumnWidth(cc -1, w)
