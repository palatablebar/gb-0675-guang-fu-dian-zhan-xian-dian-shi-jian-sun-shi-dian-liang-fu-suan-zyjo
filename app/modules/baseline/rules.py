from decimal import Decimal
from app.coerce import number,instant
from app.capacity import resolve, resolve_at, credentials_for

def estimate(segment,records,context):
    base={**segment,'baseline_kw':None,'reference_ids':[],'capacity_ref':None,'capacity_source':None,'capacity_candidates':[]}
    cred,capacity_code,candidates=resolve(context,segment['device'],instant(segment['start']),instant(segment['end']))
    if capacity_code!='CAPACITY_OK':
        # 容量取值冲突或有效期空档：不按任一铭牌硬算，片段保持待复核。
        return {**base,'capacity_candidates':candidates,'code':capacity_code}
    target_capacity=number(cred['capacity_kw'])
    base={**base,'capacity_ref':cred['id'],'capacity_source':cred.get('source','')}
    if segment['actual_kw'] is None:return {**base,'code':'TARGET_GAP'}
    if segment['status']!='健康':return {**base,'code':'TARGET_FAULT'}
    target=context['devices'][segment['device']];width=number(context['irradiance_bin']);target_bin=number(segment['irradiance'])//width
    references=[];reference_capacity={}
    for row in records:
        if row['kind']!='TELEMETRY' or row['device']==segment['device']:continue
        device=context['devices'][row['device']]
        if not device['reference'] or device['zone']!=segment['zone'] or row['status']!='健康' or row['at']!=segment['sample_at']:continue
        if number(row['irradiance'])//width!=target_bin:continue
        if any(e['kind']=='EVENT' and e['device']==row['device'] and instant(e['start'])<=instant(row['at'])<instant(e['end']) for e in records):continue
        ref_cred,ref_code,_=resolve_at(context,row['device'],instant(row['at']),context['cadence_seconds'])
        if ref_code!='CAPACITY_OK':continue
        capacity=number(ref_cred['capacity_kw'])
        if capacity<=0:continue
        references.append((number(row['power_kw'])/capacity,row['id']));reference_capacity[row['id']]=ref_cred['id']
    if len(references)<context['min_references']:return {**base,'reference_ids':[x[1] for x in references],'code':'NO_REFERENCE'}
    ratios=sorted(x[0] for x in references);mid=len(ratios)//2;ratio=ratios[mid] if len(ratios)%2 else (ratios[mid-1]+ratios[mid])/2
    baseline=min(target_capacity,ratio*target_capacity)
    return {**base,'baseline_kw':str(baseline),'reference_ids':sorted(x[1] for x in references),'reference_capacity_ids':sorted(reference_capacity.values()),'code':'ESTIMATED'}

def capacity_evidence(estimates,context):
    index={}
    for device in context['devices']:
        for cred in credentials_for(context,device):index[cred['id']]=cred
    used={}
    def touch(ref,role):
        if ref not in used:
            cred=index[ref]
            used[ref]={'id':ref,'device':cred['device'],'capacity_kw':str(number(cred['capacity_kw'])),'source':cred.get('source',''),'valid_from':cred.get('valid_from') or '','valid_to':cred.get('valid_to') or '','role':role,'segments':0}
        used[ref]['segments']+=1
    for row in estimates:
        if row.get('capacity_ref'):touch(row['capacity_ref'],'目标')
        for ref in row.get('reference_capacity_ids',[]):touch(ref,'对照')
    return [used[k] for k in sorted(used)]

def apply(state):
    estimates=[estimate(s,state['records'],state['context']) for s in state['segments']];state['estimates']=estimates
    state['capacity_evidence']=capacity_evidence(estimates,state['context'])
    state['views']['baseline']={'title':'对照基线','rows':estimates,'metrics':{'可估计':sum(r['code']=='ESTIMATED' for r in estimates),'未定':sum(r['code']!='ESTIMATED' for r in estimates),'容量待复核':sum(r['code'] in ('CAPACITY_CONFLICT','CAPACITY_GAP') for r in estimates),'对照下限':state['context']['min_references']}}
