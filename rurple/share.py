from __future__ import division, print_function, unicode_literals, with_statement

import sys
import os
import os.path
import wx

def _toPath(n):
    return os.path.abspath(unicode(n, sys.getfilesystemencoding()))

def _topPath():
    if hasattr(sys, "frozen"):
        return os.path.dirname(_toPath(sys.executable))
    else:
        return os.path.dirname(os.path.dirname(_toPath(__file__)))

_sharePath = os.path.join(_topPath(), "share")
    
def path(*a):
    return os.path.join(_sharePath, *a)

def toBitmap(name):
    return wx.Image(path('images', '%s.png' % name), wx.BITMAP_TYPE_PNG).ConvertToBitmap()

__all__ = [path, toBitmap]
