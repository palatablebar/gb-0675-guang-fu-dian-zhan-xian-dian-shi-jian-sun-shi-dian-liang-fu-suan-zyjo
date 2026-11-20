from app.coerce import number,instant
from app.errors import BusinessError
from app.reasons import reject
from collections import defaultdict

def normalize(row,context):
    if row['device'] not in context['devices']:raise BusinessError('UNKNOWN_DEVICE','设备不存在')
    device=context['devices'][row['device']]
    if row['kind']=='EVENT':
        start,end=instant(row['start']),instant(row['end'])
        if not start<end or (end-start).total_seconds()>86400:raise BusinessError('INVALID_RANGE','限电区间无效或超过24小时')
        return {**row,'start':start.isoformat(),'end':end.isoformat(),'zone':device['zone']}
    if row['kind']!='TELEMETRY':raise BusinessError('BAD_KIND','记录类型无效')
    factor={'kW':1,'MW':1000}.get(row['unit'])
    if factor is None:raise BusinessError('BAD_UNIT','功率单位无效')
    power=number(row['power'])*factor;irr=number(row['irradiance'])
    if power<0 or irr<0 or power>number(device['capacity_kw'])*number('1.2'):raise BusinessError('INVALID_RANGE','功率或辐照度超出范围')
    if row['status'] not in {'健康','故障'}:raise BusinessError('BAD_STATUS','设备状态无效')
    return {**row,'at':instant(row['at']).isoformat(),'power_kw':str(power),'irradiance':str(irr),'zone':device['zone']}
def apply(state):
    good=[]
    for row in state['records']:
        try:good.append(normalize(row,state['context']))
        except BusinessError as e:reject(state,row,e.code,e.message)
    grouped=defaultdict(list)
    for row in good:
        if row['kind']=='TELEMETRY':grouped[(row['device'],row['at'])].append(row)
    bad_ids=set()
    for rows in grouped.values():
        if len(rows)>1:
            identities={(r['power_kw'],r['irradiance'],r['status']) for r in rows}
            victims=rows if len(identities)>1 else sorted(rows,key=lambda r:r['id'])[1:]
            for row in victims:reject(state,row,'SAMPLE_CONFLICT' if len(identities)>1 else 'SAMPLE_DUPLICATE','设备同一时刻存在重复观测');bad_ids.add(row['id'])
    state['records']=[r for r in good if r['id'] not in bad_ids]
    state['views']['devices']={'title':'设备与单位','rows':state['records'],'metrics':{'设备':len(state['context']['devices']),'规范记录':len(state['records']),'隔离':len(state['quarantine'])}}
