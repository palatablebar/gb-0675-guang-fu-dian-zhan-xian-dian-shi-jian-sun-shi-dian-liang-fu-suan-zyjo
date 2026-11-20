from app.coerce import instant
from datetime import timedelta
from collections import defaultdict

def union_events(events):
    merged=[]
    for row in sorted(events,key=lambda r:(instant(r['start']),instant(r['end']),r['id'])):
        start,end=instant(row['start']),instant(row['end'])
        if merged and start<=merged[-1]['end']:
            merged[-1]['end']=max(end,merged[-1]['end']);merged[-1]['event_ids'].append(row['id'])
        else:merged.append({'start':start,'end':end,'event_ids':[row['id']]})
    return merged

def slice_intervals(records,context):
    event_groups=defaultdict(list);samples=defaultdict(list)
    for row in records:
        if row['kind']=='EVENT':event_groups[row['device']].append(row)
        else:samples[row['device']].append(row)
    segments=[];unions=[];cadence=context['cadence_seconds']
    for device,events in sorted(event_groups.items()):
        readings=sorted(samples[device],key=lambda r:instant(r['at']))
        for merged in union_events(events):
            start,end=merged['start'],merged['end'];boundaries={start,end}
            for row in readings:
                at=instant(row['at']);expires=at+timedelta(seconds=cadence)
                if start<at<end:boundaries.add(at)
                if start<expires<end:boundaries.add(expires)
            ordered=sorted(boundaries);unions.append({'device':device,'start':start.isoformat(),'end':end.isoformat(),'seconds':int((end-start).total_seconds()),'event_ids':merged['event_ids']})
            for a,b in zip(ordered,ordered[1:]):
                available=[r for r in readings if instant(r['at'])<=a<instant(r['at'])+timedelta(seconds=cadence)]
                row=available[-1] if available else None
                segments.append({'device':device,'start':a.isoformat(),'end':b.isoformat(),'seconds':int((b-a).total_seconds()),'sample_id':row['id'] if row else '', 'sample_at':row['at'] if row else '', 'actual_kw':row['power_kw'] if row else None,'irradiance':row['irradiance'] if row else None,'status':row['status'] if row else '缺测','zone':context['devices'][device]['zone'],'event_ids':merged['event_ids']})
    return segments,unions

def apply(state):
    cuts,unions=slice_intervals(state['records'],state['context']);state.update(segments=cuts,event_unions=unions)
    state['views']['slicing']={'title':'限电并集','rows':unions,'metrics':{'并集区间':len(unions),'切片':len(cuts),'限电分钟':sum(r['seconds'] for r in unions)//60}}
