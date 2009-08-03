import sys
import threading
import Queue
import wx

class CPU(object):
    def __init__(self):
        self._functions = {}
        
    def NonblockingProxyFunction(self, f):
        def callF(*a, **kw):
            q = Queue.Queue()
            wx.CallAfter(f, q.put, *a, **kw)
            res, exc = q.get()
            if exc is not None:
                raise exc
            return res
        return callF

    def ProxyFunction(self, f):
        def callBlocking(rcb, *a, **kw):
            try:
                rcb((f(*a, **kw), None))
            except Exception, e:
                rcb((None, e))
        return self.NonblockingProxyFunction(callBlocking)

    def SetTrace(self, f):
        self._trace = self.NonblockingProxyFunction(f)
    
    def SetProgram(self, p):
        self._program = p

    def AddFunction(self, name, f):
        self._functions[name] = self.ProxyFunction(f)
    
    def Start(self):
        t = threading.Thread(target = self._start)
        t.start()
    
    def _start(self):
        try:
            sys.settrace(self._tracefunc)
            try:
                exec self._program in self._functions
                wx.CallAfter(self._done, None)
            except Exception, e:
                wx.CallAfter(self._done, e)
        finally:
            sys.settrace(None)
    
    def _tracefunc(self, frame, event, arg):
        #print frame, event, arg, frame.f_code.co_filename, frame.f_lineno
        if "<string>" in frame.f_code.co_filename:
            if event == "line":
                self._trace(frame.f_lineno)
        return self._tracefunc
            
    def _done(self, e):
        print "Done, exception:", e

