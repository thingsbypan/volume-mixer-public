"""No audio ownership here. Explicit learned bindings; no guessed channel or CC."""
import time
import winmidi as mido


class Pickup:
    def __init__(self):
        self.previous = None
        self.latched = False
        self.last_written = None

    def accept(self, value, current):
        if self.last_written is not None and abs(current-self.last_written) > .005:
            self.latched = False
            self.previous = None
            self.last_written = None
        near = abs(value-current) <= .015
        crossed = self.previous is not None and min(self.previous,value) <= current <= max(self.previous,value)
        self.previous = value
        self.latched = self.latched or near or crossed
        if self.latched:
            self.last_written = value
        return self.latched


class Midi:
    def __init__(self):
        self.port = None
        self.name = None
        self.status = 'MIDI disabled — select a port'
        self.pickups = {}
        self.retry = 0

    def select(self, name):
        self.close()
        self.name = name or None

    def poll(self):
        if not self.name:
            return []
        try:
            if self.name not in mido.get_input_names():
                self.close()
                self.status = 'Controller disconnected'
                return []
            if self.port is None and time.monotonic() >= self.retry:
                self.port = mido.open_input(self.name)
                self.pickups.clear()
            if self.port:
                self.status = 'Mixer mode • '+self.name
                return list(self.port.iter_pending())[:256]
        except Exception as exc:
            self.close()
            self.retry = time.monotonic()+3
            self.status = 'MIDI unavailable: '+str(exc)
        return []

    def close(self):
        if self.port:
            self.port.close()
        self.port = None
        self.pickups.clear()
