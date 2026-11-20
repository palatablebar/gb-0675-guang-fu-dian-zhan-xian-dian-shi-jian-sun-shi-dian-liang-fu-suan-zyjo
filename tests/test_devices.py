from app.modules.devices.rules import normalize
from app.errors import BusinessError
import pytest

def test_units_real(clean):
    assert clean['records'][0]['power_kw']=='60'
def test_sentinel_real(sample):
    # TRAP-07
    assert next(r for r in sample['quarantine'] if r['id']=='BAD1')['code']=='MISSING_VALUE'
def test_conflict_both_isolated(sample):
    # TRAP-14
    assert len([r for r in sample['quarantine'] if r['code']=='SAMPLE_CONFLICT'])==2;assert not any(r['id']=='INV-A-20' for r in sample['records'])
def test_megawatt_conversion(clean):
    # TRAP-15
    row=normalize(dict(clean['records'][0],power='0.06',unit='MW'),clean['context']);assert row['power_kw']=='60.00'
def test_fullwidth_number(clean):
    # TRAP-06
    row=normalize(dict(clean['records'][0],irradiance='１,０００'),clean['context']);assert row['irradiance']=='1000'
def test_unknown_device(clean):
    with pytest.raises(BusinessError):normalize(dict(clean['records'][0],device='NONE'),clean['context'])
def test_time_equivalence(clean):
    # TRAP-11
    row=normalize(dict(clean['records'][0],at='2026-10-15T02:00:00Z'),clean['context']);assert row['at']==clean['records'][0]['at']
