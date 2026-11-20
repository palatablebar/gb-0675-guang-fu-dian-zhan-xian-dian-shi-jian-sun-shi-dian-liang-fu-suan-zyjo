from decimal import Decimal,ROUND_HALF_UP
from app.coerce import number

def integrate(estimate):
    if estimate['baseline_kw'] is None:return {**estimate,'loss_kwh':None,'actual_kwh':None,'baseline_kwh':None}
    hours=Decimal(estimate['seconds'])/3600;actual=number(estimate['actual_kw']);baseline=number(estimate['baseline_kw']);loss=max(Decimal(0),baseline-actual)*hours
    # 保留计算精度，汇总后再统一保留四位，避免逐段量化制造尾差。
    return {**estimate,'loss_kwh':str(loss),'actual_kwh':str(actual*hours),'baseline_kwh':str((actual+max(Decimal(0),baseline-actual))*hours),'code':'LOSS' if loss else 'NO_LOSS'}

def apply(state):
    rows=[integrate(e) for e in state['estimates']];state['energy_rows']=rows
    total=sum((number(r['loss_kwh']) for r in rows if r['loss_kwh'] is not None),Decimal(0))
    state['views']['loss']={'title':'损失电量','rows':[{k:v for k,v in r.items() if k not in ['sample_at','zone','irradiance','status']} for r in rows],'metrics':{'已确定损失_kWh':str(total.quantize(Decimal('.0001'))),'未定片段':sum(r['loss_kwh'] is None for r in rows)}}
