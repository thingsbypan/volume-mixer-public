"""One local working preset. Stores assignments, never audio levels."""
import json, os
from pathlib import Path

def atomic_write(path,config):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(config,indent=2),encoding='utf-8')
    os.replace(temporary,path)

def read_setup(path):
    config=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(config,dict) or not isinstance(config.get('port'),str) or not isinstance(config.get('bindings'),list):
        raise ValueError('Invalid setup file')
    if config.get('output_role','Speakers') not in ('Speakers','Headphones'): raise ValueError('Invalid output role')
    for field in ('slots','outputs'):
        values=config.get(field,{})
        if not isinstance(values,dict) or any(not isinstance(k,str) or v is not None and not isinstance(v,str) for k,v in values.items()):
            raise ValueError('Invalid '+field)
    for b in config['bindings']:
        if not isinstance(b,dict) or b.get('action') not in ('volume','mute') or any(not isinstance(b.get(k),str) for k in ('target','label','device')) or type(b.get('channel')) is not int or not 0<=b['channel']<=15 or type(b.get('number')) is not int or not 0<=b['number']<=127:
            raise ValueError('Invalid MIDI binding')
    identities=config.get('slot_identities',{})
    if not isinstance(identities,dict) or any(not isinstance(v,dict) or not all(isinstance(v.get(k),str) for k in ('identifier','device')) for v in identities.values()):
        raise ValueError('Invalid session identities')
    labels=config.get('slot_labels',{})
    if not isinstance(labels,dict) or any(not isinstance(v,str) for v in labels.values()): raise ValueError('Invalid app labels')
    return config
