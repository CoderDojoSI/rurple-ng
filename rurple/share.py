from __future__ import division, print_function, unicode_literals, with_statement

import os.path
import wx

_sharePath = os.path.abspath("share")

def path(*a):
    return os.path.join(_sharePath, *a)

def toBitmap(name):
    return wx.Image(path('images', '%s.png' % name), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
