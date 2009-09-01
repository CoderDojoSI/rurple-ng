from __future__ import division, print_function, unicode_literals

import wx

class ListCtrl(wx.ListCtrl):
    def __init__(self, *a, **kw):
        wx.ListCtrl.__init__(self, *a, **kw)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_LIST_COL_END_DRAG, self.OnSize)
    
    def SetItems(self, items):
        for ix, item in enumerate(sorted(items)):
            n = item[0]
            while True:
                if ix >= self.ItemCount:
                    self.InsertStringItem(ix, n)
                    break
                v = self.GetItemText(ix)
                if v < n:
                    self.DeleteItem(ix)
                elif v == n:
                    break
                else:
                    self.InsertStringItem(ix, n)
                    break
            for c, v in enumerate(item[1:]):
                self.SetStringItem(ix, c+1, v)
        ix = len(items)
        while ix < self.ItemCount:
           self.DeleteItem(ix)
         
    def OnSize(self, e):
        e.Skip()
        w, h = self.ClientSize
        cc = self.ColumnCount
        if cc < 1:
            return
        for i in range(cc -1):
            w -= self.GetColumnWidth(i)
        self.SetColumnWidth(cc -1, w)
