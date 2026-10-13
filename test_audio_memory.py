import ctypes, unittest
from unittest.mock import patch
from audio import owned_string
class OwnedStringTests(unittest.TestCase):
 def test_copy_and_free(self):
  buffer=ctypes.create_unicode_buffer('exact Windows session identity')
  class Interface:
   def _IAudioSessionControl2__com_GetSessionIdentifier(self,out):
    ctypes.cast(out,ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.addressof(buffer)
  freed=[]
  with patch('audio._free',lambda pointer:freed.append(pointer.value)):
   self.assertEqual(owned_string(Interface(),'IAudioSessionControl2','GetSessionIdentifier'),buffer.value)
  self.assertEqual(freed,[ctypes.addressof(buffer)])
 def test_free_on_error(self):
  buffer=ctypes.create_unicode_buffer('allocated before failure')
  class Interface:
   def _IAudioSessionControl2__com_GetSessionIdentifier(self,out):
    ctypes.cast(out,ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.addressof(buffer)
    raise OSError('disconnected')
  freed=[]
  with patch('audio._free',lambda pointer:freed.append(pointer.value)):
   with self.assertRaises(OSError):owned_string(Interface(),'IAudioSessionControl2','GetSessionIdentifier')
  self.assertEqual(freed,[ctypes.addressof(buffer)])
 def test_null_not_freed(self):
  class Interface:
   def _IMMDevice__com_GetId(self,out):pass
  with patch('audio._free') as free:
   self.assertEqual(owned_string(Interface(),'IMMDevice','GetId'),'');free.assert_not_called()
if __name__=='__main__':unittest.main()
