"""Creates a silent test session; changes only that session, never master audio."""
import subprocess, sys, time, wave, tempfile, json, psutil
from pathlib import Path
from PySide6.QtWidgets import QApplication
from main import Panel, STYLE
from pycaw.pycaw import AudioUtilities

app=QApplication([]); app.setStyleSheet(STYLE); panel=Panel(); panel.timer.stop(); panel.mtimer.stop()
path=Path(tempfile.gettempdir())/'TrayMixer-silent-test.wav'
with wave.open(str(path),'wb') as f:
    f.setnchannels(1); f.setsampwidth(2); f.setframerate(8000); f.writeframes(b'\0\0'*8000*30)
code = "from PySide6.QtCore import QCoreApplication,QBuffer,QByteArray,QIODevice,QTimer; from PySide6.QtMultimedia import QMediaDevices,QAudioSink; app=QCoreApplication([]); dev=QMediaDevices.defaultAudioOutput(); fmt=dev.preferredFormat(); data=QByteArray(bytes(fmt.bytesForDuration(30000000))); buffer=QBuffer(); buffer.setData(data); buffer.open(QIODevice.ReadOnly); sink=QAudioSink(dev,fmt); sink.start(buffer); QTimer.singleShot(30000,app.quit); app.exec()"
child=subprocess.Popen([sys.executable,'-c',code])
result={}
try:
    deadline=time.monotonic()+8; key=None
    while time.monotonic()<deadline:
        panel.tick(); app.processEvents()
        pids={child.pid}|{p.pid for p in psutil.Process(child.pid).children(recursive=True)}
        key=next((k for k,s in panel.sessions.items() if s['pid'] in pids),None)
        if key: break
        time.sleep(.2)
    assert key, 'Silent test session not enumerated: '+str(child.pid)+' '+repr([(s['name'],s['pid'],k) for k,s in panel.sessions.items()])
    result['session_appearance']=True
    panel.config['slots']['app1']=key; panel.tick()
    panel.api(key).SetMute(False,None)
    panel.write(key,.2); assert abs(panel.state(key)[0]-.2)<.001
    panel.toggle(key); assert panel.state(key)[1]
    panel.tick(); assert panel.rows['app1'].mute.text()=='Unmute'
    panel.toggle(key); assert not panel.state(key)[1]
    panel.sessions[key]['volume'].SetMute(True,None); panel.tick(); assert panel.rows['app1'].mute.text()=='Unmute'
    panel.sessions[key]['volume'].SetMute(False,None); panel.tick(); assert panel.rows['app1'].mute.text()=='Mute'
    panel.sessions[key]['volume'].SetMasterVolume(.13,None); panel.tick(); assert panel.rows['app1'].slider.value()==13
    result['session_volume_mute_external_UI']=True
    # Synthetic MIDI routing to the silent real session, while the panel is hidden.
    from types import SimpleNamespace
    panel.hide()
    original_bindings=panel.config['bindings']; original_poll=panel.midi.poll
    panel.config['bindings']=[dict(target='app1',label='Silent test',action='volume',device=panel.devices.currentData(),channel=0,number=125)]
    panel.midi.poll=lambda: [SimpleNamespace(type='control_change',channel=0,control=125,value=10)]
    panel.midi_tick(); assert abs(panel.state(key)[0]-.13)<.001
    panel.midi.poll=lambda: [SimpleNamespace(type='control_change',channel=0,control=125,value=26)]
    panel.midi_tick(); assert abs(panel.state(key)[0]-26/127)<.001
    result['synthetic_MIDI_hidden_pickup_to_real_session']=True
    panel.config['bindings']=original_bindings; panel.midi.poll=original_poll; panel.midi.pickups.clear()
    # Set exactly the existing master values, proving API access without a loudness change.
    old,mute=panel.state('master'); panel.write('master',old); panel.api('master').SetMute(mute,None)
    assert abs(panel.state('master')[0]-old)<.001 and panel.state('master')[1]==mute
    result['master_API_same_value_roundtrip']=True
    for i in range(panel.devices.count()):
        panel.config.setdefault('outputs',{})['Speakers']=panel.devices.itemData(i); panel.output_role='Speakers'; panel.device_changed(); assert panel.endpoint is not None
    result['all_output_endpoints_selectable']=True
    descendants=psutil.Process(child.pid).children(recursive=True)
    for process in descendants: process.terminate()
    child.terminate(); child.wait(timeout=5)
    panel.config['outputs']['Speakers']=AudioUtilities.GetSpeakers().id; panel.device_changed()
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        panel.tick(); app.processEvents()
        if key not in panel.sessions: break
        time.sleep(.2)
    result['session_disappearance']=key not in panel.sessions
    assert result['session_disappearance']
finally:
    if child.poll() is None:
        for process in psutil.Process(child.pid).children(recursive=True): process.terminate()
        child.terminate(); child.wait(timeout=5)
    panel.quit(); path.unlink(missing_ok=True)
print(json.dumps(result,indent=2))
