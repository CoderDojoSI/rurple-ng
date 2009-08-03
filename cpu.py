import sys
import threading
import Queue
import wx

class CPU(object):
    def __init__(self, partner):
        self._partner = partner
        
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

    def Play(self):
        self._globals = self._partner.getGlobals()
        self._program = self._partner.program()
        self._trace = self.NonblockingProxyFunction(self._partner.traceLine)
        t = threading.Thread(target = self._start)
        t.start()
    
    def _start(self):
        try:
            sys.settrace(self._tracefunc)
            try:
                exec self._program in self._globals
                wx.CallAfter(self._done, None)
            except Exception, e:
                wx.CallAfter(self._partner.done, e)
        finally:
            sys.settrace(None)
    
    def _tracefunc(self, frame, event, arg):
        #print frame, event, arg, frame.f_code.co_filename, frame.f_lineno
        if "<string>" in frame.f_code.co_filename:
            if event == "line":
                self._trace(frame.f_lineno)
        return self._tracefunc
    
    def _done(self, e):
        self._partner.done(e)

