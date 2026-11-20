from app.modules.slicing.rules import union_events,slice_intervals
from app.coerce import instant

def test_overlapping_real(clean):
    # TRAP-23
    a=next(r for r in clean['event_unions'] if r['device']=='INV-A');assert a['seconds']==1800;assert a['event_ids']==['EA1','EA2']
def test_union_not_double_count(clean):
    assert sum(r['seconds'] for r in clean['segments'] if r['device']=='INV-A')==1800
def test_missing_target_real(sample):
    assert any(r['actual_kw'] is None for r in sample['segments'])
def test_adjacent_events_merge(clean):
    e=[r for r in clean['records'] if r['id']=='EA1'][0];other=dict(e,id='EA3',start=e['end'],end='2026-10-15T02:30:00+00:00');u=union_events([other,e]);assert len(u)==1;assert (u[0]['end']-u[0]['start']).total_seconds()==1800
def test_nonoverlap_remains_separate(clean):
    e=[r for r in clean['records'] if r['id']=='EA1'][0];other=dict(e,id='EA3',start='2026-10-15T03:00:00+00:00',end='2026-10-15T03:10:00+00:00');assert len(union_events([e,other]))==2
def test_order_invariant_slice(clean):
    a=slice_intervals(clean['records'],clean['context']);b=slice_intervals(list(reversed(clean['records'])),clean['context']);assert a==b
def test_split_boundary_inside_sample(clean):
    rows=[dict(r) for r in clean['records'] if r['kind']!='EVENT'];rows.append(dict(next(r for r in clean['records'] if r['id']=='EA1'),start='2026-10-15T02:05:00+00:00',end='2026-10-15T02:15:00+00:00'));segments,_=slice_intervals(rows,clean['context']);assert [r['seconds'] for r in segments]==[300,300]
