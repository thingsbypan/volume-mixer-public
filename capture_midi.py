"""Bounded read-only MIDI capture. Never imports the audio module."""
import time, json, sys
import winmidi
names=winmidi.get_input_names(); print('Ports:',names,flush=True)
if not names: sys.exit('No MIDI input')
port=winmidi.open_input(names[int(sys.argv[1]) if len(sys.argv)>1 else 0])
print('Read-only capture for 20 seconds: move only the requested control.',flush=True)
records=[]; end=time.monotonic()+20
try:
    while time.monotonic()<end:
        for message in port.iter_pending():
            record=vars(message); records.append(record); print(record,flush=True)
        time.sleep(.02)
finally: port.close()
with open('midi-capture.json','w') as f: json.dump(records,f,indent=2)
print('Released MIDI port; captured',len(records),'messages')
