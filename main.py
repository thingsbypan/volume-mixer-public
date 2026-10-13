import sys, os, json, time
from pathlib import Path
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QTimer, QFileInfo, QLockFile
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from audio import Audio
from midi import Midi, Pickup
import winmidi
from levels import LevelDisplay
from presets import atomic_write,read_setup
from sessions import resolve_session

STYLE = 'QWidget{background:#080808;color:#edf2f7;font-family:Segoe UI;font-size:12px} QPushButton,QComboBox{background:#283340;border:1px solid #3d4b5b;border-radius:4px;padding:3px 6px} QPushButton:hover{background:#3b4d60} QGroupBox{border:1px solid #3d4b5b;border-radius:6px;margin-top:10px;padding-top:12px} QSlider::groove:horizontal{height:5px;background:#384454;border-radius:2px} QSlider::sub-page:horizontal{background:#62d4bb} QSlider::handle:horizontal{width:14px;margin:-5px 0;background:#edf2f7;border-radius:7px} QScrollArea{border:0} QPushButton:checked{background:#347969;border-color:#62d4bb} QSlider::groove:vertical{width:6px;background:#384454;border-radius:3px} QSlider::add-page:vertical{background:#62d4bb;border-radius:4px} QSlider::handle:vertical{height:16px;margin:0 -7px;background:#edf2f7;border-radius:4px}'

CONFIG = Path(os.environ['LOCALAPPDATA'])/'TrayMixer'/'mapping.json'
PRESET = CONFIG.parent/'working-setup.json'

class Strip(QWidget):
    def __init__(self, key, name, path, owner):
        super().__init__(); self.key=key; self.owner=owner
        self.setObjectName('faderStrip'); self.setStyleSheet('QWidget#faderStrip{background:#111b20;border:1px solid #26343c;border-radius:6px;}')
        layout=QVBoxLayout(self); layout.setContentsMargins(7,6,7,6); layout.setSpacing(4)
        self.label=QLabel(name); self.label.setAlignment(Qt.AlignCenter); layout.addWidget(self.label)
        self.selector=QComboBox(); self.selector.setMinimumContentsLength(8); self.selector.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.selector.setFixedWidth(130)
        if key=='master':
            self.selector.addItems(['Speakers','Headphones']); self.selector.setCurrentText(owner.output_role)
            self.selector.activated.connect(lambda: owner.select_output(self.selector.currentText()))
        else: self.selector.activated.connect(lambda: owner.assign(key,self.selector.currentData()))
        control=QHBoxLayout(); control.setSpacing(7); control.addStretch()
        self.slider=QSlider(Qt.Vertical); self.slider.setRange(0,100); self.slider.setMinimumHeight(60); control.addWidget(self.slider)
        self.level=LevelDisplay(name,vertical=True); self.level.setFixedWidth(14); control.addWidget(self.level); control.addStretch(); layout.addLayout(control,1)
        self.percent=QLabel(); self.percent.setAlignment(Qt.AlignCenter); layout.addWidget(self.percent)
        self.mute=QPushButton(); self.mute.setFixedWidth(54); layout.addWidget(self.mute)
        self.slider.valueChanged.connect(lambda value: owner.write(key,value/100))
        self.mute.clicked.connect(lambda: owner.toggle(key))
    def refresh(self,v,m):
        if not self.slider.isSliderDown():
            self.slider.blockSignals(True); self.slider.setValue(round(v*100)); self.slider.blockSignals(False)
        self.percent.setText(str(round(v*100))+'%'); self.mute.setText('Unmute' if m else 'Mute')

class Panel(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowTitle('Tray Mixer v1'); self.resize(560,240); self.setMinimumSize(510,220)
        pix=QPixmap(32,32); pix.fill(QColor('#202832')); painter=QPainter(pix); painter.setPen(QColor('#62d4bb'))
        for x,h in [(8,10),(15,22),(22,15)]: painter.drawLine(x,26,x,26-h)
        painter.end(); self.icon=QIcon(pix); self.setWindowIcon(self.icon)
        self.audio=Audio(); self.midi=Midi(); self.endpoint=None; self.sessions={}; self.rows={}; self.learning=None; self.learn_until=0; self.audio_error=''; self.first_device=True; self.learn_values=set(); self.learn_message=None; self.session_numbers={}; self.next_number=1
        try: self.config=json.loads(CONFIG.read_text())
        except (OSError,ValueError): self.config={'port':'','bindings':[]}
        if not isinstance(self.config,dict): self.config={}
        self.config['port']=self.config.get('port','') if isinstance(self.config.get('port',''),str) else ''
        bindings=self.config.get('bindings',[])
        self.config['bindings']=[b for b in bindings if isinstance(b,dict) and b.get('action') in ('volume','mute') and all(isinstance(b.get(k),str) for k in ('target','label','device')) and isinstance(b.get('channel'),int) and 0<=b['channel']<=15 and isinstance(b.get('number'),int) and 0<=b['number']<=127] if isinstance(bindings,list) else []
        if not isinstance(self.config.get('slot_identities',{}),dict): self.config['slot_identities']={}
        if not isinstance(self.config.get('slot_labels',{}),dict): self.config['slot_labels']={}
        self.midi.select(self.config.get('port',''))
        root=QVBoxLayout(self); root.setSpacing(6); root.setContentsMargins(10,10,10,10)
        header=QHBoxLayout(); title=QLabel('TRAY MIXER v1'); title.setStyleSheet('font-size:14px;font-weight:600'); header.addWidget(title); header.addStretch(); root.addLayout(header)
        self.devices=QComboBox(); self.output_choices={}; self.output_buttons={}
        self.output_role=self.config.get('output_role','Speakers')
        if self.output_role not in ('Speakers','Headphones'): self.output_role='Speakers'
        output_row=QHBoxLayout(); button_group=QButtonGroup(self); self.output_group=button_group
        output_settings=QDialog(self); output_settings.setWindowTitle('Output assignments'); form=QFormLayout(output_settings)
        for role in ('Speakers','Headphones'):
            button=QPushButton(role); button.setCheckable(True); button.setChecked(role==self.output_role)
            button_group.addButton(button); output_row.addWidget(button); self.output_buttons[role]=button
            button.clicked.connect(lambda checked=False,r=role: self.select_output(r))
            choice=QComboBox(); self.output_choices[role]=choice; form.addRow(role,choice)
            choice.activated.connect(lambda index,r=role: self.assign_output(r))
        setup=QPushButton('Outputs'); setup.clicked.connect(output_settings.show); header.addWidget(setup)
        self.default_label=QLabel()
        settings=QPushButton('Windows Sound'); settings.clicked.connect(lambda: os.startfile('ms-settings:sound')); form.addRow(settings)
        self.config.setdefault('slots',{})
        if not isinstance(self.config['slots'],dict): self.config['slots']={}
        mixer=QHBoxLayout(); choices=QVBoxLayout(); choices.setSpacing(6); choices.addStretch(); mixer.addLayout(choices)
        faders=QHBoxLayout(); faders.setSpacing(5)
        strips={}
        for key,name in [('app3','App 3'),('app2','App 2'),('app1','App 1'),('master','Master')]:
            row=Strip(key,name,'',self); faders.addWidget(row,1)
            strips[key]=row
            if key=='master': self.master=row
            else: self.rows[key]=row
        for key,name in [('master','Master'),('app1','App 1'),('app2','App 2'),('app3','App 3')]:
            choice_row=QHBoxLayout(); label=QLabel(name); label.setFixedWidth(48); choice_row.addWidget(label); choice_row.addWidget(strips[key].selector); choices.addLayout(choice_row)
        choices.addStretch()
        self.levels={key:row.level for key,row in strips.items()}; self.meter_device=None; self.output_meter=None
        mixer.addSpacing(12)
        bank=QWidget(); bank.setLayout(faders); faders.setContentsMargins(0,0,0,0); mixer.addWidget(bank,1); root.addLayout(mixer,1)
        self.status=QLabel(); self.status.setWordWrap(False); self.status.setMinimumWidth(0); self.status.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred); root.addWidget(self.status)
        group=QDialog(self); group.setWindowTitle('K3 assignments'); group.resize(440,320); gl=QVBoxLayout(group)
        self.ports=QComboBox(); self.ports.addItem('Disabled',''); gl.addWidget(self.ports); self.ports.activated.connect(self.port_changed)
        controls=QVBoxLayout(); self.targets=QComboBox(); controls.addWidget(self.targets,1); self.action=QComboBox(); self.action.addItems(['Volume (absolute CC)','Mute (note button)']); controls.addWidget(self.action)
        learn=QPushButton('Learn 15s'); learn.clicked.connect(self.learn); controls.addWidget(learn); gl.addLayout(controls)
        self.mapping=QLabel(); self.mapping.setWordWrap(True); gl.addWidget(self.mapping)
        clear=QPushButton('Clear mappings'); clear.clicked.connect(self.clear); gl.addWidget(clear)
        configure=QPushButton('K3'); configure.clicked.connect(group.show); header.addWidget(configure)
        preset_button=QPushButton('Setup'); preset_menu=QMenu(preset_button)
        preset_menu.addAction('Save working setup',self.save_setup); preset_menu.addAction('Restore working setup',self.restore_setup)
        preset_button.setMenu(preset_menu); header.addWidget(preset_button)
        self.tray=QSystemTrayIcon(self.icon,self); menu=QMenu(); menu.addAction('Open mixer',self.open); menu.addAction('Quit',self.quit); self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda why: self.open() if why in (QSystemTrayIcon.Trigger,QSystemTrayIcon.DoubleClick) else None); self.tray.setToolTip('Tray Mixer v1'); self.tray.show()
        self.device_cache=[]; self.device_scan_due=0; self.resolved_targets={}
        self.timer=QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(80)
        self.mtimer=QTimer(self); self.mtimer.timeout.connect(self.midi_tick); self.mtimer.start(25); self.tick()
        self.level_timer=QTimer(self); self.level_timer.timeout.connect(self.level_tick); self.level_timer.start(40)
    def level_tick(self):
        if not self.isVisible(): return
        for key,display in self.levels.items():
            try:
                meter=self.output_meter if key=='master' and self.endpoint else self.sessions.get(self.resolve(key),{}).get('meter')
                peak=float(meter.GetPeakValue()) if meter else None
            except Exception:
                peak=None
                if key=='master': self.meter_device=None
            display.feed(peak)
    def save(self):
        atomic_write(CONFIG,self.config)
    def save_setup(self):
        if self.learning:
            QMessageBox.information(self,'Learning in progress','Wait for MIDI learning to finish before saving a setup.'); return
        if PRESET.exists() and QMessageBox.question(self,'Replace working setup?',
            'Replace your saved working setup with the current app assignments and MIDI mappings?',
            QMessageBox.Yes|QMessageBox.Cancel,QMessageBox.Cancel)!=QMessageBox.Yes: return
        try:
            atomic_write(PRESET,self.config)
            QMessageBox.information(self,'Setup saved','Your app, output and MIDI assignments are saved.\nAudio levels are not part of this preset.')
        except Exception as exc: QMessageBox.warning(self,'Could not save setup',str(exc))
    def restore_setup(self):
        if self.learning:
            QMessageBox.information(self,'Learning in progress','Wait for MIDI learning to finish before restoring a setup.'); return
        try: restored=read_setup(PRESET)
        except Exception as exc:
            QMessageBox.warning(self,'Could not restore setup','Save a working setup first, or check the preset file.\n'+str(exc)); return
        if QMessageBox.question(self,'Restore working setup?',
            'Restore your saved app, output and MIDI assignments?\nCurrent assignments will be backed up. Volumes will not change.\nClosed or replaced app sessions will need reassignment.',
            QMessageBox.Yes|QMessageBox.Cancel,QMessageBox.Cancel)!=QMessageBox.Yes: return
        try:
            atomic_write(CONFIG.parent/'before-restore.json',self.config)
            atomic_write(CONFIG,restored)
        except Exception as exc: QMessageBox.warning(self,'Could not restore setup',str(exc)); return
        self.config=restored; self.config.setdefault('slots',{})
        self.output_role=self.config.get('output_role','Speakers'); self.master.selector.setCurrentText(self.output_role)
        for role,button in self.output_buttons.items(): button.setChecked(role==self.output_role)
        self.midi.select(self.config['port']); self.ports.setCurrentIndex(max(0,self.ports.findData(self.config['port'])))
        self.device_scan_due=0; self.meter_device=None; self.device_changed()
        QMessageBox.information(self,'Setup restored','Assignments restored. Move each absolute control to its current volume to pick it up.\nUnavailable app sessions require reassignment.')
    def clear(self):
        answer=QMessageBox.question(self,'Clear MIDI mappings?',
            'Are you sure you want to clear all learned MIDI mappings?\nYou will need to learn the controls again.',
            QMessageBox.Yes|QMessageBox.Cancel,QMessageBox.Cancel)
        if answer!=QMessageBox.Yes: return
        self.config['bindings']=[]; self.midi.pickups.clear(); self.save()
    def port_changed(self):
        self.config['port']=self.ports.currentData(); self.midi.select(self.config['port']); self.save()
    def device_changed(self):
        self.endpoint=None; self.sessions={}; self.midi.pickups.clear(); self.tick()
    def select_output(self,role):
        self.output_role=role; self.master.selector.setCurrentText(role); self.config['output_role']=role; self.save(); self.device_changed()
    def assign_output(self,role):
        self.config.setdefault('outputs',{})[role]=self.output_choices[role].currentData(); self.save(); self.device_changed()
    def assign(self,slot,key):
        identities=self.config.setdefault('slot_identities',{})
        labels=self.config.setdefault('slot_labels',{})
        session=self.sessions.get(key)
        if session:
            identities[slot]={'identifier':session['identifier'],'device':session['device_id']}; labels[slot]=session['name']
        else: identities.pop(slot,None); labels.pop(slot,None)
        self.config['slots'][slot]=key; self.midi.pickups.clear(); self.save(); self.tick()
    def resolve(self,key):
        target=self.config['slots'].get(key) if key in self.rows else key
        identities=self.config.get('slot_identities',{})
        identity=identities.get(key) if isinstance(identities,dict) else None
        return resolve_session(target,self.sessions,identity)
    def api(self,key):
        return self.endpoint if key=='master' else self.sessions[self.resolve(key)]['volume']
    def state(self,key):
        api=self.api(key)
        return (api.GetMasterVolumeLevelScalar(),bool(api.GetMute())) if key=='master' else (api.GetMasterVolume(),bool(api.GetMute()))
    def write(self,key,v):
        try:
            api=self.api(key)
            if key=='master': api.SetMasterVolumeLevelScalar(max(0,min(1,v)),None)
            else: api.SetMasterVolume(max(0,min(1,v)),None)
            row=self.master if key=='master' else self.rows.get(key)
            if row: row.refresh(*self.state(key))
        except Exception as exc: self.status.setText('Audio unavailable: '+str(exc))
    def toggle(self,key):
        try:
            self.api(key).SetMute(not self.state(key)[1],None)
            row=self.master if key=='master' else self.rows.get(key)
            if row: row.refresh(*self.state(key))
        except Exception as exc: self.status.setText('Audio unavailable: '+str(exc))
    def tick(self):
        try:
            if time.monotonic()>=self.device_scan_due:
                self.device_cache=self.audio.devices(); self.device_scan_due=time.monotonic()+2
            devices=self.device_cache; ids=[d.id for d in devices]; old=self.devices.currentData()
            if ids != [self.devices.itemData(i) for i in range(self.devices.count())]:
                self.devices.clear()
                for d in devices: self.devices.addItem(d.FriendlyName,d.id)
                default_id=AudioUtilities.GetSpeakers().id if self.first_device else None
                self.devices.setCurrentIndex(ids.index(old) if old in ids else ids.index(default_id) if default_id in ids else 0); self.midi.pickups.clear(); self.first_device=False
            outputs=self.config.get('outputs',{})
            if not isinstance(outputs,dict): outputs={}
            for role,choice in self.output_choices.items():
                target=outputs.get(role)
                if role not in outputs:
                    terms=('headphone','headset') if role=='Headphones' else ('speaker',)
                    target=next((d.id for d in devices if any(t in d.FriendlyName.lower() for t in terms)),None)
                if [None]+ids!=[choice.itemData(i) for i in range(choice.count())]:
                    choice.blockSignals(True); choice.clear(); choice.addItem('Choose output...',None)
                    for d in devices: choice.addItem(d.FriendlyName,d.id)
                    choice.blockSignals(False)
                choice.blockSignals(True); choice.setCurrentIndex(max(0,choice.findData(target))); choice.blockSignals(False)
            selected=self.output_choices[self.output_role].currentData(); self.devices.setCurrentIndex(self.devices.findData(selected))
            self.default_label.setText(self.output_role+': '+(self.devices.currentText() or 'Assign a device below')+' | Master controls this output. App slots control their own listed output.')
            self.master.selector.setToolTip(self.default_label.text())
            if not selected: raise RuntimeError('Choose a device in Output assignments.')
            self.endpoint,selected_sessions=self.audio.snapshot(selected); self.sessions=dict(selected_sessions); self.audio_error=''
            for device in devices:
                try:
                    found=selected_sessions if device.id==selected else self.audio.snapshot(device.id)[1]
                    for session in found.values():
                        session['device_id']=device.id; session['device_name']=device.FriendlyName
                    if device.id!=selected: self.sessions.update(found)
                except Exception: continue
            if selected!=self.meter_device:
                self.meter_device=selected
                try: self.output_meter=self.audio.meter(selected)
                except Exception: self.output_meter=None
            self.master.setEnabled(True); self.master.refresh(*self.state('master'))
            resolved={slot:self.resolve(slot) for slot in self.rows}
            if resolved!=self.resolved_targets:
                self.midi.pickups.clear(); self.resolved_targets=resolved
            for key in self.sessions:
                if key not in self.session_numbers: self.session_numbers[key]=self.next_number; self.next_number+=1
            for slot,row in self.rows.items():
                stored=self.config['slots'].get(slot)
                if stored in self.sessions:
                    session=self.sessions[stored]
                    self.config.setdefault('slot_identities',{})[slot]={'identifier':session['identifier'],'device':session['device_id']}
                    self.config.setdefault('slot_labels',{})[slot]=session['name']
                choice=row.selector; assigned=self.config['slots'].get(slot); previous=self.resolve(slot)
                entries=[(None,'Choose application...')]+[(key,v['name']+' / '+str(self.session_numbers[key])+(' • active' if v['state']==1 else ' • idle')+' — '+v.get('device_name','Output')) for key,v in self.sessions.items()]
                if assigned and previous is None:
                    previous=assigned
                    label=self.config.get('slot_labels',{}).get(slot,'Assigned app')
                    identity=self.config.get('slot_identities',{}).get(slot,{})
                    count=sum(v['identifier']==identity.get('identifier') and v['device_id']==identity.get('device') for v in self.sessions.values())
                    entries.append((previous,label+(' • multiple sessions / choose' if count>1 else ' • no audio session')))
                if entries!=[(choice.itemData(i),choice.itemText(i)) for i in range(choice.count())]:
                    choice.blockSignals(True); choice.clear()
                    for key,label in entries: choice.addItem(label,key)
                    choice.setCurrentIndex(max(0,choice.findData(previous))); choice.blockSignals(False)
                choice.blockSignals(True); choice.setCurrentIndex(max(0,choice.findData(previous))); choice.blockSignals(False)
                available=previous in self.sessions; row.slider.setEnabled(available); row.mute.setEnabled(available)
                row.selector.setToolTip(choice.currentText())
                if available: row.refresh(*self.state(slot))
                else: row.percent.setText('—'); row.mute.setText('Mute')
            if self.targets.count()==0:
                for label,key in [('App 3','app3'),('App 2','app2'),('App 1','app1'),('Master','master')]: self.targets.addItem(label,key)
        except Exception as exc:
            self.endpoint=None; self.sessions={}; self.master.setEnabled(False)
            for row in self.rows.values(): row.slider.setEnabled(False); row.mute.setEnabled(False)
            self.audio_error='Output unavailable: '+str(exc)
        names=winmidi.get_input_names(); desired=['']+names
        if desired != [self.ports.itemData(i) for i in range(self.ports.count())]:
            self.ports.clear(); self.ports.addItem('Disabled','')
            for name in names: self.ports.addItem(name,name)
            self.ports.setCurrentIndex(max(0,self.ports.findData(self.config.get('port',''))))
        self.mapping.setText('\n'.join(b['label']+' → '+b['action']+' ch '+str(b['channel']+1)+' #'+str(b['number'])+(' (unavailable)' if b['target']!='master' and self.resolve(b['target']) not in self.sessions else '') for b in self.config['bindings']) or 'No mappings. Learn only the intended fader or button; do not learn an encoder.')
    def learn(self):
        if not self.midi.name: self.status.setText('Select a MIDI input first.'); return
        self.learning={'target':self.targets.currentData(),'label':self.targets.currentText(),'action':'volume' if self.action.currentIndex()==0 else 'mute','device':self.devices.currentData()}
        self.learn_until=time.monotonic()+15; self.midi.pickups.clear(); self.learn_values=set(); self.learn_message=None
    def midi_tick(self):
        messages=self.midi.poll()
        if self.learning and time.monotonic()>self.learn_until:
            if self.learn_message and (self.learning['action']=='mute' or len(self.learn_values)>=8 and max(self.learn_values)-min(self.learn_values)>=32):
                b=dict(self.learning,channel=self.learn_message.channel,number=self.learn_message.control if self.learning['action']=='volume' else self.learn_message.note)
                self.config['bindings']=[x for x in self.config['bindings'] if not (x['channel']==b['channel'] and x['number']==b['number'] and x['action']==b['action'])]+[b]; self.save()
            self.learning=None
        self.status.setText('Learning • move ONLY the intended absolute fader, or press mute button' if self.learning else self.audio_error or self.midi.status)
        for msg in messages:
            if self.learning:
                if (self.learning['action']=='volume' and msg.type=='control_change') or (self.learning['action']=='mute' and msg.type=='note_on' and msg.velocity>0):
                    if self.learn_message is None: self.learn_message=msg
                    number=msg.control if msg.type=='control_change' else msg.note
                    first=self.learn_message.control if msg.type=='control_change' else self.learn_message.note
                    if msg.channel==self.learn_message.channel and number==first: self.learn_values.add(msg.value)
                continue
            for i,b in enumerate(self.config['bindings']):
                if msg.channel!=b['channel']: continue
                if b['target'] not in ('master','app1','app2','app3') and b['device']!=self.devices.currentData(): continue
                if b['target']!='master' and self.resolve(b['target']) not in self.sessions:
                    self.midi.pickups.pop(i,None); continue
                try:
                    if b['action']=='volume' and msg.type=='control_change' and msg.control==b['number']:
                        pickup=self.midi.pickups.setdefault(i,Pickup()); value=msg.value/127
                        if pickup.accept(value,self.state(b['target'])[0]): self.write(b['target'],value)
                    elif b['action']=='mute' and msg.type=='note_on' and msg.velocity>0 and msg.note==b['number']: self.toggle(b['target'])
                except Exception: self.midi.pickups.pop(i,None)
    def open(self):
        self.showNormal()
        self.anchor()
        QTimer.singleShot(60,self.anchor)
        self.raise_(); self.activateWindow()
    def anchor(self):
        screens=QApplication.screens()
        if screens:
            screen=min(screens,key=lambda s:s.geometry().left()); area=screen.availableGeometry()
            self.windowHandle().setScreen(screen)
            self.resize(min(560,max(self.minimumWidth(),area.width()-40)),240); frame=self.frameGeometry()
            self.move(area.right()-frame.width()+1-12,area.bottom()-frame.height()+1-12)
    def closeEvent(self,event): event.ignore(); self.hide()
    def keyPressEvent(self,event):
        if event.key()==Qt.Key_Escape: self.hide(); event.accept()
        else: super().keyPressEvent(event)
    def quit(self):
        self.timer.stop(); self.mtimer.stop(); self.level_timer.stop(); self.output_meter=None; self.midi.close(); self.endpoint=None; self.sessions.clear(); self.tray.hide(); QApplication.instance().quit()

from pycaw.pycaw import AudioUtilities
def main():
    app=QApplication(sys.argv); app.setQuitOnLastWindowClosed(False)
    CONFIG.parent.mkdir(parents=True,exist_ok=True)
    lock=QLockFile(str(CONFIG.parent/'instance.lock'))
    if not lock.tryLock(0):
        socket=QLocalSocket()
        for attempt in range(20):
            socket.abort(); socket.connectToServer('ThingsByPan.TrayMixer.v1')
            if socket.waitForConnected(100): socket.write(b'quit' if '--quit' in sys.argv else b'open'); socket.waitForBytesWritten(500); return
            time.sleep(.1)
        return
    if '--quit' in sys.argv: return
    server=QLocalServer(); QLocalServer.removeServer('ThingsByPan.TrayMixer.v1')
    if not server.listen('ThingsByPan.TrayMixer.v1'): return
    app.setStyleSheet(STYLE)
    panel=Panel()
    def connected():
        peer=server.nextPendingConnection(); peer.waitForReadyRead(500); command=bytes(peer.readAll()); panel.quit() if command==b'quit' else panel.open(); peer.deleteLater()
    server.newConnection.connect(connected)
    if '--hidden' not in sys.argv: panel.open()
    if '--verify-build' in sys.argv:
        def verify_build():
            result={}
            try:
                panel.tick(); assert panel.endpoint is not None,panel.audio_error
                result={'endpoint':panel.devices.currentText(),'sessions':len(panel.sessions),'tray_visible':panel.tray.isVisible()}
                panel.close(); result['close_hidden']=not panel.isVisible(); panel.open(); result['reopen_visible']=panel.isVisible()
                panel.grab().save(str(CONFIG.parent/'build-preview.png'))
            except Exception as exc: result['error']=str(exc)
            finally:
                panel.quit(); result['quit_midi_released']=panel.midi.port is None
                (CONFIG.parent/'build-check.json').write_text(json.dumps(result,indent=2))
        QTimer.singleShot(1000,verify_build)
    app.aboutToQuit.connect(panel.midi.close); app.exec()
if __name__=='__main__': main()
