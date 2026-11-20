import pytest
from copy import deepcopy
from decimal import Decimal
from fastapi.testclient import TestClient
from app import main
from app.engine import evaluate
from app.capacity import resolve
from app.coerce import instant
from app.errors import BusinessError
from app.modules.slicing.rules import slice_intervals
from app.modules.devices.rules import normalize
from app.modules.baseline.rules import estimate

@pytest.fixture
def retrofit():
    return evaluate({'dataset':'retrofit'})

def client(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DB_PATH',str(tmp_path/'test.sqlite'));return TestClient(main.app)

def ctx(credentials):
    return {'devices':{'X':{'zone':'Z','capacity_kw':'100','reference':False},'R':{'zone':'Z','capacity_kw':'50','reference':True}},
            'capacity_credentials':credentials,'cadence_seconds':600,'irradiance_bin':'100','min_references':2}

# 裁定规则：冲突、空档、同值取新、台账回退

def test_conflict_two_values_pending():
    c=ctx([{'id':'C1','device':'X','capacity_kw':'100','valid_from':'2026-01-01T00:00:00+08:00','valid_to':None,'source':'铭牌'},
           {'id':'C2','device':'X','capacity_kw':'120','valid_from':'2026-10-01T00:00:00+08:00','valid_to':None,'source':'技改'}])
    cred,code,candidates=resolve(c,'X',instant('2026-10-15T10:00:00+08:00'),instant('2026-10-15T10:10:00+08:00'))
    assert code=='CAPACITY_CONFLICT' and cred is None and [x['id'] for x in candidates]==['C1','C2']

def test_gap_when_validity_expired():
    c=ctx([{'id':'C1','device':'X','capacity_kw':'100','valid_from':None,'valid_to':'2026-10-01T00:00:00+08:00','source':'铭牌'}])
    cred,code,candidates=resolve(c,'X',instant('2026-10-15T10:00:00+08:00'))
    assert code=='CAPACITY_GAP' and cred is None and candidates[0]['id']=='C1'

def test_same_value_picks_newer():
    c=ctx([{'id':'C1','device':'X','capacity_kw':'100','valid_from':'2026-01-01T00:00:00+08:00','valid_to':None,'source':'铭牌'},
           {'id':'C2','device':'X','capacity_kw':'100','valid_from':'2026-10-01T00:00:00+08:00','valid_to':None,'source':'技改确认'}])
    cred,code,_=resolve(c,'X',instant('2026-10-15T10:00:00+08:00'))
    assert code=='CAPACITY_OK' and cred['id']=='C2'

def test_ledger_fallback_without_credentials(clean):
    cred,code,_=resolve(clean['context'],'INV-A',instant('2026-10-15T10:00:00+08:00'))
    assert code=='CAPACITY_OK' and cred['capacity_kw']=='100' and cred['source']=='台账额定'

def test_malformed_validity_rejected():
    c=ctx([{'id':'C1','device':'X','capacity_kw':'100','valid_from':'not-a-time','valid_to':None,'source':'铭牌'}])
    with pytest.raises(BusinessError) as e:resolve(c,'X',instant('2026-10-15T10:00:00+08:00'))
    assert e.value.code=='BAD_CAPACITY_VALIDITY'

# 切片按有效期边界切分

def test_slice_cuts_at_validity_boundary(clean):
    c=deepcopy(clean['context']);c['capacity_credentials']=[{'id':'C-NEW','device':'INV-A','capacity_kw':'100','valid_from':'2026-10-15T10:15:00+08:00','valid_to':None,'source':'技改'}]
    segments,_=slice_intervals(clean['records'],c)
    assert [r['seconds'] for r in segments if r['device']=='INV-A']==[600,300,300,600]

# 设备映射：容量未裁定不拦截遥测，已裁定仍守上限

def test_unresolved_capacity_keeps_telemetry(retrofit):
    row=next(r for r in retrofit['records'] if r['id']=='INV-D-10')
    assert row['power_kw']=='25'

def test_resolved_capacity_enforces_bound(retrofit):
    row=dict(next(r for r in retrofit['records'] if r['id']=='INV-D-00'),power='70')
    with pytest.raises(BusinessError) as e:normalize(row,retrofit['context'])
    assert e.value.code=='INVALID_RANGE'

# 基线裁定

def test_reference_without_covering_credential_skipped(clean):
    c=deepcopy(clean['context']);c['capacity_credentials']=[{'id':'C-A1','device':'REF-A1','capacity_kw':'100','valid_from':None,'valid_to':'2026-10-01T00:00:00+08:00','source':'铭牌'}]
    result=estimate(clean['segments'][0],clean['records'],c)
    assert result['code']=='NO_REFERENCE' and result['reference_ids']==['REF-A2-00']

def test_retrofit_conflict_segments_pending(retrofit):
    rows=[r for r in retrofit['energy_rows'] if r['device']=='INV-C']
    assert len(rows)==2 and all(r['code']=='CAPACITY_CONFLICT' and r['baseline_kw'] is None and r['loss_kwh'] is None for r in rows)
    assert all([c['id'] for c in r['capacity_candidates']]==['CAP-C-PLATE','CAP-C-RETRO'] for r in rows)

def test_retrofit_newer_nameplate_applied_where_valid(retrofit):
    rows=[r for r in retrofit['energy_rows'] if r['device']=='INV-D']
    assert [r['code'] for r in rows]==['LOSS','CAPACITY_GAP','LOSS']
    assert rows[0]['capacity_ref']=='CAP-D-OLD' and Decimal(rows[0]['baseline_kw'])==50
    assert rows[2]['capacity_ref']=='CAP-D-NEW' and Decimal(rows[2]['baseline_kw'])==60
    assert retrofit['balance']['loss_kwh']=='10.0000' and retrofit['balance']['capacity_pending']==3
    assert retrofit['archive']['status']=='待复核'

def test_baseline_and_loss_share_one_credential(retrofit):
    for est,row in zip(retrofit['estimates'],retrofit['energy_rows']):
        assert row['capacity_ref']==est['capacity_ref'] and row['capacity_source']==est['capacity_source']

def test_every_segment_traced_or_pending():
    for dataset in ('dirty','clean','legacy','retrofit'):
        for r in evaluate({'dataset':dataset})['estimates']:
            if r['code'] in ('CAPACITY_CONFLICT','CAPACITY_GAP'):assert r['capacity_ref'] is None and r['capacity_candidates']
            else:assert r['capacity_ref'] and r['capacity_source']

def test_capacity_evidence_covers_target_and_reference(retrofit):
    evidence={e['id']:e for e in retrofit['capacity_evidence']}
    assert evidence['CAP-D-OLD']['role']=='目标' and evidence['CAP-D1-LEDGER']['role']=='对照'
    assert evidence['CAP-D1-LEDGER']['segments']==2 and 'CAP-C-PLATE' not in evidence

# 重跑幂等、已确认保护与失败恢复

def test_rerun_no_duplicate_capacity_evidence(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);run=c.post('/api/runs',json={'dataset':'retrofit'}).json();rid=run['manifest']['run_id']
    for _ in range(2):
        again=c.post(f'/api/runs/{rid}/rerun');assert again.status_code==200 and again.json()['manifest']['run_id']==rid
    stored=c.get(f'/api/runs/{rid}').json()
    assert stored['capacity_evidence']==run['capacity_evidence'] and len(stored['capacity_evidence'])==4
    assert len([r for r in c.get('/api/runs').json() if r['id']==rid])==1

def test_reviewed_result_not_overwritten_by_rerun(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);run=c.post('/api/runs',json={'dataset':'retrofit'}).json();rid=run['manifest']['run_id']
    assert c.post(f'/api/runs/{rid}/review',json={'revision':1}).status_code==200
    c.post(f'/api/runs/{rid}/rerun');c.post('/api/runs',json={'dataset':'retrofit'})
    stored=c.get(f'/api/runs/{rid}').json()
    assert stored['status']=='已复核' and stored['revision']==2

def test_failed_rerun_keeps_old_version(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);run=c.post('/api/runs',json={'dataset':'retrofit'}).json();rid=run['manifest']['run_id']
    original=main.evaluate
    def boom(*a,**k):raise BusinessError('BAD_CAPACITY_VALIDITY','容量凭证有效期无法解析')
    monkeypatch.setattr(main,'evaluate',boom)
    assert c.post(f'/api/runs/{rid}/rerun').status_code==422
    monkeypatch.setattr(main,'evaluate',original)
    stored=c.get(f'/api/runs/{rid}').json()
    assert stored['manifest']['sha256']==run['manifest']['sha256'] and stored['balance']['loss_kwh']=='10.0000'

def test_failed_run_creates_no_batch(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);before=len(c.get('/api/runs').json())
    bad={'dataset':'clean','overrides':{'capacity_credentials':[{'id':'C-X','device':'INV-A','capacity_kw':'120','valid_from':'bad','source':'技改'}]}}
    assert c.post('/api/runs',json=bad).status_code==422
    assert len(c.get('/api/runs').json())==before

def test_conflicting_override_spawns_new_batch_old_untouched(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);original=c.post('/api/runs',json={'dataset':'clean'}).json()
    override={'dataset':'clean','overrides':{'capacity_credentials':[
        {'id':'CAP-A-PLATE','device':'INV-A','capacity_kw':'100','valid_from':'2026-01-01T00:00:00+08:00','valid_to':None,'source':'出厂铭牌'},
        {'id':'CAP-A-RETRO','device':'INV-A','capacity_kw':'120','valid_from':'2026-10-01T00:00:00+08:00','valid_to':None,'source':'技改资料'}]}}
    rerun=c.post('/api/runs',json=override).json()
    assert rerun['manifest']['run_id']!=original['manifest']['run_id']
    assert {r['code'] for r in rerun['estimates'] if r['device']=='INV-A'}=={'CAPACITY_CONFLICT'}
    assert rerun['balance']['loss_kwh']=='6.6667'
    assert c.get(f"/api/runs/{original['manifest']['run_id']}").json()['balance']['loss_kwh']=='26.6667'

# 页面：各段容量来源与待查片段

def test_pages_show_capacity_source_and_pending(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);rid=c.post('/api/runs',json={'dataset':'retrofit'}).json()['manifest']['run_id']
    baseline=c.get(f'/baseline?run_id={rid}').text
    assert '容量凭证' in baseline and 'CAP-D-NEW' in baseline and '容量待查片段' in baseline and 'CAP-C-PLATE' in baseline
    loss=c.get(f'/loss?run_id={rid}').text
    assert '容量来源' in loss and '容量待查片段' in loss and 'CAPACITY_GAP' in loss
    archive=c.get(f'/archive?run_id={rid}').text
    assert '容量凭证' in archive and 'CAP-D-OLD' in archive
