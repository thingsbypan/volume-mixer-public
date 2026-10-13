import gc,psutil,tracemalloc
from PySide6.QtWidgets import QApplication
from main import Panel
app=QApplication([]); panel=Panel(); panel.timer.stop();panel.mtimer.stop();panel.level_timer.stop();panel.midi.close();p=psutil.Process();tracemalloc.start(); warmed=[]
def report(i):
 gc.collect();m=p.memory_info();print(i,round(m.private/1048576,2),round(tracemalloc.get_traced_memory()[0]/1048576,2),flush=True)
report(0)
for i in range(1,10001):
 panel.tick();panel.level_tick();app.processEvents()
 if i%1000==0:
  report(i)
  if i>=2000:warmed.append(p.memory_info().private)
panel.quit()
assert max(warmed)-min(warmed)<4*1048576, warmed
print("PASS: warmed private-memory spread under 4 MB over 10,000 ticks")
