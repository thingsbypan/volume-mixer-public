import unittest
from unittest.mock import patch
from midi import Midi, Pickup
from types import SimpleNamespace
import winmidi

class Tests(unittest.TestCase):
    def test_pickup_and_external_change(self):
        p=Pickup(); self.assertFalse(p.accept(.9,.3)); self.assertTrue(p.accept(.2,.3))
        self.assertTrue(p.accept(.25,.2)); self.assertFalse(p.accept(.5,.24))
        self.assertTrue(p.accept(.1,.24)); self.assertFalse(Pickup().accept(.5,.1))
    def test_disconnect_reconnect_busy_and_release(self):
        class Port:
            closed=False
            def iter_pending(self): return iter([])
            def close(self): self.closed=True
        p=Port(); m=Midi(); m.select('K3')
        with patch('midi.mido.get_input_names',return_value=['K3']),patch('midi.mido.open_input',return_value=p): m.poll()
        m.pickups['a']=Pickup()
        with patch('midi.mido.get_input_names',return_value=[]): m.poll()
        self.assertTrue(p.closed); self.assertIsNone(m.port); self.assertFalse(m.pickups)
        with patch('midi.mido.get_input_names',return_value=['K3']),patch('midi.mido.open_input',side_effect=OSError('busy')): m.poll()
        self.assertIn('busy',m.status); self.assertIsNone(m.port)
        m.retry=0; p=Port()
        with patch('midi.mido.get_input_names',return_value=['K3']),patch('midi.mido.open_input',return_value=p): m.poll()
        self.assertIs(m.port,p); m.close(); self.assertTrue(p.closed)
    def test_winmm_message_decode(self):
        from collections import deque
        port=object.__new__(winmidi.Port); port.queue=deque()
        port.receive(None,0x3C3,0,0xBE | (17<<8) | (64<<16),0)
        msg=port.queue.popleft(); self.assertEqual((msg.type,msg.channel,msg.control,msg.value),('control_change',14,17,64))
        port.receive(None,0x3C3,0,0x9E | (40<<8) | (127<<16),0)
        self.assertEqual(port.queue.popleft().type,'note_on')

if __name__=='__main__': unittest.main()
