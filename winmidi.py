import ctypes as c
from collections import deque
from types import SimpleNamespace
w = c.WinDLL('winmm')
class Caps(c.Structure):
    _fields_ = [('mid',c.c_ushort),('pid',c.c_ushort),('version',c.c_uint),('name',c.c_wchar*32),('support',c.c_uint)]
def get_input_names():
    names=[]
    for i in range(w.midiInGetNumDevs()):
        caps=Caps()
        if w.midiInGetDevCapsW(c.c_size_t(i),c.byref(caps),c.sizeof(caps)) == 0:
            base=caps.name
            name=base; occurrence=2
            while name in names:
                name=base+' #'+str(occurrence); occurrence+=1
            names.append(name)
    return names
class Port:
    def __init__(self,name):
        self.queue=deque(maxlen=512)
        self.handle=c.c_void_p()
        self.callback=c.WINFUNCTYPE(None,c.c_void_p,c.c_uint,c.c_size_t,c.c_size_t,c.c_size_t)(self.receive)
        index=get_input_names().index(name)
        result=w.midiInOpen(c.byref(self.handle),index,self.callback,c.c_size_t(0),0x30000)
        if result: raise OSError('WinMM MIDI open error '+str(result)+' (port may be busy)')
        if w.midiInStart(self.handle):
            self.close()
            raise OSError('MIDI start failed')
    def receive(self,h,msg,instance,data,timestamp):
        if msg != 0x3C3: return
        status=data&255; number=(data>>8)&127; value=(data>>16)&127
        kind={0xB0:'control_change',0x90:'note_on',0x80:'note_off'}.get(status&0xF0)
        if kind:
            self.queue.append(SimpleNamespace(type=kind,channel=status&15,control=number,note=number,value=value,velocity=value))
    def iter_pending(self):
        while self.queue: yield self.queue.popleft()
    def close(self):
        if self.handle.value:
            w.midiInStop(self.handle); w.midiInReset(self.handle); w.midiInClose(self.handle)
            self.handle=c.c_void_p()
def open_input(name): return Port(name)
