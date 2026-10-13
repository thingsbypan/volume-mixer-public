import gc,time,tracemalloc,psutil
from audio import Audio
p=psutil.Process(); a=Audio(); devices=a.devices(); tracemalloc.start()
def report(i):
 gc.collect(); m=p.memory_info(); print(i,'private_MB',round(m.private/1048576,2),'python_MB',round(tracemalloc.get_traced_memory()[0]/1048576,2),flush=True)
report(0)
for i in range(1,601):
 for d in devices: endpoint,rows=a.snapshot(d.id)
 if i%100==0: report(i)
