from __future__ import division, print_function, unicode_literals, with_statement

import sys
import threading
import Queue
import wx

class TraceThread(threading.Thread):
    def __init__(self, cpu, world, program):
        threading.Thread.__init__(self)
        self._cpu = cpu
        self._world = world
        self._globals = self._world.getGlobals(self)
        self._program = program
        self._stopped = False
        self._traceProxy = self.threadAwareProxyFunction(self._cpu.trace)
    
    def _done(self):
        if not self._stopped:
            self._cpu.done()
    
    def _failed(self, e):
        if not self._stopped:
            self._cpu.failed(e)
    
    def run(self):
        try:
            sys.settrace(self._tracefunc)
            try:
                exec self._program in self._globals
                wx.CallAfter(self._done)
            except BaseException, e:
                wx.CallAfter(self._failed, e)
        finally:
            # not really necessary - thread's done anyway
            sys.settrace(None)

    # FIXME: leak threads on stop()
    def stop(self):
        self._stopped = True
        
    def threadAwareProxyFunction(self, f):
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

    def proxyFunction(self, f):
        def callBlocking(rcb, *a, **kw):
            try:
                rcb((f(*a, **kw), None))
            except Exception, e:
                rcb((None, e))
        return self.threadAwareProxyFunction(callBlocking)

    def _tracefunc(self, frame, event, arg):
        # FIXME: shame to stop only on the lines in string if stopped
        #print frame, event, arg, frame.f_code.co_filename, frame.f_lineno
        if "<string>" in frame.f_code.co_filename:
            if event == "line":
                self._traceProxy(frame.f_lineno)
        return self._tracefunc

STOP = 1
PAUSE = 2
RUN = 3

class CPU(object):
    def __init__(self, ui):
        self._ui = ui
        self._lineTime = 1000
        self._clear()
    
    def _clear(self):
        self._state = STOP
        self._timer = None
        self._thread = None
        self._rcb = None
    
    def _start(self):
        world = self._ui.world
        self._ui.starting()
        self._thread = TraceThread(self, world, self._ui.program)
        self._thread.start()

    def _release(self):
        r = self._rcb
        if r is not None:
            self._rcb = None
            self._timer = None
            r((None, None))
    
    def _stopTimer(self):
        if self._timer is not None:
            self._timer.Stop()
            self._timer = None
    
    # ----- Thread methods ------

    def trace(self, rcb, lineno):
        if self._state == STOP:
            return # FIXME: assert out
        self._ui.traceLine(lineno)
        self._rcb = rcb
        if self._state == RUN:
            self._timer = wx.CallLater(self._lineTime, self._release)
    
    def done(self):
        self._clear()
        self._ui.done()

    def failed(self, e):
        self._clear()
        self._ui.failed(e)

    # ----- UI methods -----

    @property
    def state(self):
        return self._state
    
    def run(self):
        if self._state == STOP:
            self._state = RUN
            self._ui.running()
            self._start()
        elif self._state == PAUSE:
            self._state = RUN
            self._ui.running()
            self._release()
    
    def pause(self):
        if self._state == STOP:
            self._state = PAUSE
            self._ui.pausing()
            self._start()
        elif self._state == RUN:
            self._state = PAUSE
            self._ui.pausing()
            self._stopTimer()
    
    def stop(self):
        if self._state == STOP:
            return
        self._stopTimer()
        if self._thread:
            self._thread.stop()
        self._clear()
        self._ui.stopped()
        
    def step(self):
        self.pause()
        self._release()

    def setLineTime(self, t):
        self._lineTime = t
        if self._timer is not None:
            self._timer.Stop()
            self._timer = wx.CallLater(self._lineTime, self._release)
    
__all__ = [STOP, PAUSE, RUN, CPU]

