from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioSessionManager2
from pycaw.constants import DEVICE_STATE, EDataFlow
from ctypes import HRESULT, POINTER, c_float, c_wchar_p, c_void_p, byref, cast, windll
from comtypes import IUnknown, GUID, COMMETHOD

_free = windll.ole32.CoTaskMemFree
_free.argtypes = [c_void_p]
_free.restype = None

def owned_string(interface, declaring_interface, method):
    """Copy a Core Audio task-allocated LPWSTR, then release its native buffer.

    pycaw's convenience getter converts LPWSTR to str and loses the pointer.
    Use comtypes' raw ABI method so allocation ownership stays explicit.
    """
    value = c_wchar_p()
    try:
        getattr(interface, f'_{declaring_interface}__com_{method}')(byref(value))
        return value.value or ''
    finally:
        if cast(value, c_void_p).value:
            _free(cast(value, c_void_p))

class _OwnedDevice:
    """Keep pycaw device metadata, but free the native GetId result."""
    def __init__(self, device):
        self._device = device
    def GetId(self):
        return owned_string(self._device, 'IMMDevice', 'GetId')
    def __getattr__(self, name):
        return getattr(self._device, name)

class IAudioMeterInformation(IUnknown):
    _iid_ = GUID('{C02216F6-8C67-4B5B-9D00-D008E73E0064}')
    _methods_ = [COMMETHOD([], HRESULT, 'GetPeakValue', (['out'], POINTER(c_float), 'peak'))]


class Audio:
    def meter(self,device_id):
        dev=AudioUtilities.GetDeviceEnumerator().GetDevice(device_id)
        return dev.Activate(IAudioMeterInformation._iid_,CLSCTX_ALL,None).QueryInterface(IAudioMeterInformation)
    def devices(self):
        collection = AudioUtilities.GetDeviceEnumerator().EnumAudioEndpoints(
            EDataFlow.eRender.value, DEVICE_STATE.ACTIVE.value)
        return [AudioUtilities.CreateDevice(_OwnedDevice(collection.Item(i)))
                for i in range(collection.GetCount())]

    def snapshot(self, device_id):
        dev = AudioUtilities.GetDeviceEnumerator().GetDevice(device_id)
        from pycaw.pycaw import IAudioEndpointVolume
        endpoint = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None).QueryInterface(IAudioEndpointVolume)
        manager = dev.Activate(IAudioSessionManager2._iid_, CLSCTX_ALL, None).QueryInterface(IAudioSessionManager2)
        enumerator = manager.GetSessionEnumerator()
        from pycaw.pycaw import AudioSession
        from pycaw.api.audiopolicy import IAudioSessionControl2
        rows = {}
        for i in range(enumerator.GetCount()):
            session = AudioSession(enumerator.GetSession(i).QueryInterface(IAudioSessionControl2))
            state=session.State
            if state == 2:
                continue
            process = session.Process
            try:
                path = process.exe() if process else ''
                name = process.name() if process else 'System sounds' if session.ProcessId == 0 else owned_string(session._ctl, 'IAudioSessionControl', 'GetDisplayName') or 'Audio session'
            except Exception:
                path = ''
                name = owned_string(session._ctl, 'IAudioSessionControl', 'GetDisplayName') or 'Unavailable process'
            key = owned_string(session._ctl, 'IAudioSessionControl2', 'GetSessionInstanceIdentifier')
            try: meter=session._ctl.QueryInterface(IAudioMeterInformation)
            except Exception: meter=None
            rows[key] = dict(key=key, identifier=owned_string(session._ctl, 'IAudioSessionControl2', 'GetSessionIdentifier'), device_id=device_id, state=state, name=name, path=path, pid=session.ProcessId, volume=session.SimpleAudioVolume, session=session, meter=meter)
        return endpoint, rows
