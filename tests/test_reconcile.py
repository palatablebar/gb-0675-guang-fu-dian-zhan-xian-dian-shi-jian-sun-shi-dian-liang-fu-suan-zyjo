from app.modules.reconcile.rules import reconcile
from copy import deepcopy

def test_input_rows_real(sample):
    assert sample['balance']['input']==40;assert sample['balance']['accepted']==32;assert sample['balance']['quarantined']==5;assert sample['balance']['row_balanced']
def test_clean_energy_real(clean):
    assert clean['balance']['loss_kwh']=='26.6667';assert clean['balance']['actual_kwh']=='40.0000';assert clean['balance']['energy_balanced']
def test_unknown_time_real(sample):
    assert sample['balance']['unknown_seconds']==1200;assert sample['balance']['unknown_segments']==2
def test_union_time_conservation(clean):
    assert clean['balance']['union_seconds']==clean['balance']['slice_seconds']==3000
def test_time_tamper(clean):
    s=deepcopy(clean);s['energy_rows'][0]['seconds']+=1;assert reconcile(s)['time_balanced'] is False
def test_energy_tamper(clean):
    s=deepcopy(clean);s['energy_rows'][0]['loss_kwh']='999';assert reconcile(s)['energy_balanced'] is False
def test_record_tamper(sample):
    s=deepcopy(sample);s['records'].pop();assert reconcile(s)['row_balanced'] is False
