import sys
import threading
import Queue
import wx

class TraceThread(threading.Thread):
    def __init__(self, cpu, partner):
        threading.Thread.__init__(self)
        self._cpu = cpu
        self._partner = partner
        self._globals = self._partner.getGlobals(self)
        self._program = self._partner.program()
        self._stopped = False
        self._traceProxy = self.ThreadAwareProxyFunction(self._cpu.trace)
    
    def run(self):
        try:
            sys.settrace(self._tracefunc)
            try:
                exec self._program in self._globals
                wx.CallAfter(self._cpu.done, None)
            except Exception, e:
                wx.CallAfter(self._cpu.done, e)
        finally:
            # not really necessary - thread's done anyway
            sys.settrace(None)

    # FIXME: leak threads on stop()
    def stop(self):
        self._stopped = True
        
    def ThreadAwareProxyFunction(self, f):
        def guardF(*a, **kw):
            if not self._stopped:
                return f(*a, **kw)
        def callF(*a, **kw):
            q = Queue.Queue()
            wx.CallAfter(guardF, q.put, *a, **kw)
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
        return self.ThreadAwareProxyFunction(callBlocking)

    def _tracefunc(self, frame, event, arg):
        # FIXME: shame to stop only on the lines in string if stopped
        #print frame, event, arg, frame.f_code.co_filename, frame.f_lineno
        if "<string>" in frame.f_code.co_filename:
            if event == "line":
                self._traceProxy(frame.f_lineno)
        return self._tracefunc

class CPU(object):
    def __init__(self, partner):
        self._partner = partner
        self._lineTime = 1000
        self._state = "stop"
        self._timer = None
    
    def setLineTime(self, t):
        self._lineTime = t
        if self._timer is not None:
            self._timer.Stop()
            self._timer = wx.CallLater(self._lineTime, self._release)
    
    def trace(self, rcb, lineno):
        if self._state == "stop":
            return # FIXME: assert out
        self._partner.traceLine(lineno)
        self._rcb = rcb
        if self._state == "play":
            self._timer = wx.CallLater(self._lineTime, self._release)
    
    def _stopTimer(self):
        if self._timer is not None:
            self._timer.Stop()
            self._timer = None
    
    def _release(self):
        r = self._rcb
        if r is not None:
            self._rcb = None
            self._timer = None
            r((None, None))
    
    def done(self, e):
        self._state = "stop"
        self._partner.traceLine(None)
        self._partner.done(e)

    def _start(self):
        self._thread = TraceThread(self, self._partner)
        self._thread.start()
    
    def Play(self):
        if self._state == "stop":
            self._state = "play"
            self._start()
        elif self._state == "pause":
            self._state = "play"
            self._release()
    
    def Pause(self):
        if self._state == "stop":
            self._state = "pause"
            self._start()
        elif self._state == "play":
            self._state = "pause"
            self._stopTimer()
    
    def Stop(self):
        self._state = "stop"
        self._stopTimer()
        if self._thread:
            self._thread.stop()
            self._thread = None
        self._rcb = None
        self._partner.traceLine(None)
        
    def Step(self):
        self.Pause()
        self._release()

