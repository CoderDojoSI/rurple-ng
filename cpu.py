import sys
import thread
import Queue
import wx

def proxyFunction(f):
    def callF(*a, **kw):
        q = Queue.Queue()
        wx.CallAfter(f, q, *a, **kw)
        return q.get()
    return callF

class CPU(object):
    def __init__(self):
        self._functions = {}
        
    def SetTrace(self, f):
        self._trace = proxyFunction(f)
    
    def SetProgram(self, p):
        self._program = p

    def AddFunction(self, name, f):
        self._functions[name] = proxyFunction(f)
    
    def Start(self):
        thread.start_new_thread(self._start, tuple([]))
    
    def _start(self):
        sys.settrace(self._tracefunc)
        exec self._program in self._functions
        sys.settrace(None)
    
    def _tracefunc(self, frame, event, arg):
        #print frame, event, arg, frame.f_code.co_filename, frame.f_lineno
        if event == "line" and "<string>" in frame.f_code.co_filename:
            self._trace(frame.f_lineno)
        return self._tracefunc
