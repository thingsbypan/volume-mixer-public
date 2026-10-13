"""Live normalized Core Audio peak levels; history is not a waveform or spectrum."""
import math
from collections import deque
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtCore import Qt

class LevelDisplay(QWidget):
    def __init__(self,name,vertical=False):
        super().__init__(); self.name=name; self.vertical=vertical; self.history=deque([0.]*50,maxlen=50); self.peak=None
        self.setMinimumSize(14,60) if vertical else self.setMinimumSize(55,32)
        self.setToolTip(name+' • live audio peak level; not volume position')
    def feed(self,peak):
        self.peak=peak; self.history.append(0 if peak is None else self.scale(peak)); self.update()
    @staticmethod
    def scale(peak): return max(0.,min(1.,(20*math.log10(max(peak,1e-6))+60)/60))
    def paintEvent(self,event):
        painter=QPainter(self); painter.fillRect(self.rect(),QColor('#111b20'))
        if self.vertical:
            count=24; step=(self.height()-4)/count; active=round(self.scale(self.peak or 0)*count)
            for i in range(count):
                color='#ff746e' if i>=22 else '#e4c96f' if i>=19 else '#62d4bb'
                painter.fillRect(3,int(self.height()-2-(i+1)*step),self.width()-6,max(1,int(step)-1),QColor(color if i<active else '#26343c'))
            return
        painter.setPen(QColor('#9eb3bb')); painter.drawText(6,13,self.name)
        value='—' if self.peak is None else '−∞' if self.peak<=.000001 else str(round(20*math.log10(self.peak)))+' dB'
        if self.width()>=105: painter.drawText(self.rect().adjusted(3,1,-5,-1),Qt.AlignTop|Qt.AlignRight,value)
        count=20; width=max(1,(self.width()-12)/count); active=round(self.scale(self.peak or 0)*count)
        for i in range(count):
            color='#ff746e' if i>=18 else '#e4c96f' if i>=15 else '#62d4bb'
            painter.fillRect(int(6+i*width),18,max(1,int(width)-2),5,QColor(color if i<active else '#26343c'))
        painter.setPen(QPen(QColor('#487e78'),1))
        values=list(self.history); bottom=self.height()-3; height=max(2,self.height()-28)
        for i in range(1,len(values)):
            painter.drawLine(int(6+(i-1)*(self.width()-12)/49),int(bottom-values[i-1]*height),int(6+i*(self.width()-12)/49),int(bottom-values[i]*height))
