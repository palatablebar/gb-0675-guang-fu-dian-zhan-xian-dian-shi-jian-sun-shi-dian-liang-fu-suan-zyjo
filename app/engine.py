from importlib import import_module
from pathlib import Path
from copy import deepcopy
import json, time, base64
from app.config import ROOT, MODULES, MAX_BYTES
from app.errors import BusinessError
from app.manifest import digest, make_manifest

DATASETS={'dirty','clean','legacy','retrofit'}

def merge(base,overlay):
    out=deepcopy(base)
    for key,value in overlay.items():
        if isinstance(value,dict) and isinstance(out.get(key),dict):out[key]=merge(out[key],value)
        else:out[key]=deepcopy(value)
    return out

def load_context(dataset):
    context=json.loads((ROOT/'sample_data/context.json').read_text())
    overlay=ROOT/'sample_data'/f'{dataset}.context.json'
    if overlay.exists():context=merge(context,json.loads(overlay.read_text()))
    return context

def evaluate(payload=None, until=7, snapshot=None):
    payload=payload or {}
    dataset=payload.get('dataset','dirty')
    if dataset not in DATASETS: raise BusinessError('BAD_DATASET','样例名称无效')
    if not isinstance(payload.get('overrides',{}),dict): raise BusinessError('BAD_CONTEXT','参数须为对象')
    raw=(base64.b64decode(snapshot['bytes_b64'],validate=True) if snapshot is not None else (str(payload['csv_text']).encode() if 'csv_text' in payload else (ROOT/'sample_data'/f'{dataset}.csv').read_bytes()))
    if len(raw)>MAX_BYTES: raise BusinessError('TOO_LARGE','文件超过2MB',413)
    context=deepcopy(snapshot['context']) if snapshot is not None else load_context(dataset)
    context.update(deepcopy(payload.get('overrides',{})))
    start=time.perf_counter()
    state={'raw_bytes':raw,'context':context,'records':[],'quarantine':[], 'counts':{},'views':{},'source':dataset}
    for index,key in enumerate(MODULES,1):
        if index>until: break
        import_module(f'app.modules.{key}.rules').apply(state)
    state['input_snapshot']={'bytes_b64':base64.b64encode(raw).decode(),'context':deepcopy(context)}
    state.pop('raw_bytes',None)
    state['manifest']=make_manifest(digest(raw,context),dataset,time.perf_counter()-start)
    return state
