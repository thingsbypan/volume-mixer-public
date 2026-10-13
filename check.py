"""Read-only GUI/endpoint checks, plus meaningful pickup tests. No audio writes."""
import json, sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from main import Panel, STYLE
from midi import Pickup

def check():
    p=Pickup(); assert not p.accept(.1,.5); assert not p.accept(.3,.5); assert p.accept(.6,.5)
    assert p.accept(.65,.6); assert not p.accept(.7,.2); assert p.accept(.1,.2)
    assert not Pickup().accept(.9,.3)
    app=QApplication([]); app.setStyleSheet(STYLE); app.setQuitOnLastWindowClosed(False)
    window=Panel(); window.timer.stop(); window.mtimer.stop(); window.show(); app.processEvents(); window.tick(); app.processEvents()
    assert window.endpoint is not None, window.audio_error
    result={'devices':window.devices.count(),'sessions':len(window.sessions),'midi_ports':[window.ports.itemText(i) for i in range(window.ports.count())],'sizes':[]}
    from PySide6.QtCore import Qt
    for width,height in [(540,220),(660,240),(800,280)]:
        window.resize(width,height); app.processEvents()
        assert window.master.slider.orientation()==Qt.Vertical
        for row in window.rows.values():
            assert row.slider.orientation()==Qt.Vertical
            assert row.selector is not None
            assert row.selector.mapTo(window,row.selector.rect().topRight()).x()<row.slider.mapTo(window,row.slider.rect().topLeft()).x()
            display=window.levels[row.key]
            assert row.selector.mapTo(window,row.selector.rect().topRight()).x()<display.mapTo(window,display.rect().topLeft()).x()
            assert display.parent() is row
            assert display.mapTo(window,display.rect().topLeft()).x()>row.slider.mapTo(window,row.slider.rect().topRight()).x()
        result['sizes'].append([window.width(),window.height()])
    if window.sessions:
        key=next(iter(window.sessions)); window.config['slots']['app1']=key
        window.tick(); assert window.api('app1') is window.sessions[key]['volume']
        assert window.rows['app1'].selector.currentData()==key
    window.resize(660,240); window.open(); app.processEvents()
    area=min(app.screens(),key=lambda s:s.geometry().left()).availableGeometry()
    assert area.contains(window.frameGeometry()), (area,window.frameGeometry())
    window.level_tick(); window.grab().save('preview.png')
    window.close(); assert not window.isVisible(); assert window.tray.isVisible()
    window.open(); assert window.isVisible()
    window.quit(); assert window.midi.port is None; assert not window.tray.isVisible()
    print(json.dumps(result,indent=2))
if __name__=='__main__': check()
