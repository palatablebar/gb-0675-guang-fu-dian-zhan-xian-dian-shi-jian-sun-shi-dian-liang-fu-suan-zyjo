from decimal import Decimal
from app.coerce import number,instant

def estimate(segment,records,context):
    base={**segment,'baseline_kw':None,'reference_ids':[]}
    if segment['actual_kw'] is None:return {**base,'code':'TARGET_GAP'}
    if segment['status']!='健康':return {**base,'code':'TARGET_FAULT'}
    target=context['devices'][segment['device']];width=number(context['irradiance_bin']);target_bin=number(segment['irradiance'])//width
    references=[]
    for row in records:
        if row['kind']!='TELEMETRY' or row['device']==segment['device']:continue
        device=context['devices'][row['device']]
        if not device['reference'] or device['zone']!=segment['zone'] or row['status']!='健康' or row['at']!=segment['sample_at']:continue
        if number(row['irradiance'])//width!=target_bin:continue
        if any(e['kind']=='EVENT' and e['device']==row['device'] and instant(e['start'])<=instant(row['at'])<instant(e['end']) for e in records):continue
        capacity=number(device['capacity_kw'])
        if capacity<=0:continue
        references.append((number(row['power_kw'])/capacity,row['id']))
    if len(references)<context['min_references']:return {**base,'reference_ids':[x[1] for x in references],'code':'NO_REFERENCE'}
    ratios=sorted(x[0] for x in references);mid=len(ratios)//2;ratio=ratios[mid] if len(ratios)%2 else (ratios[mid-1]+ratios[mid])/2
    baseline=min(number(target['capacity_kw']),ratio*number(target['capacity_kw']))
    return {**base,'baseline_kw':str(baseline),'reference_ids':sorted(x[1] for x in references),'code':'ESTIMATED'}

def apply(state):
    estimates=[estimate(s,state['records'],state['context']) for s in state['segments']];state['estimates']=estimates
    state['views']['baseline']={'title':'对照基线','rows':estimates,'metrics':{'可估计':sum(r['code']=='ESTIMATED' for r in estimates),'未定':sum(r['code']!='ESTIMATED' for r in estimates),'对照下限':state['context']['min_references']}}
