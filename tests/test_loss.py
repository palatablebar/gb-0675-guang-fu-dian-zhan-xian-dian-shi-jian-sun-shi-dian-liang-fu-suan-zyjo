from app.modules.loss.rules import integrate
from decimal import Decimal

def test_a_loss_20_not_overlap_sum(clean):
    total=sum(Decimal(r['loss_kwh']) for r in clean['energy_rows'] if r['device']=='INV-A');assert total.quantize(Decimal('.0001'))==Decimal('20.0000')
def test_b_loss_real(clean):
    total=sum(Decimal(r['loss_kwh']) for r in clean['energy_rows'] if r['device']=='INV-B');assert total.quantize(Decimal('.0001'))==Decimal('6.6667')
def test_unknown_remains_null(sample):
    assert sum(r['loss_kwh'] is None for r in sample['energy_rows'])==2
def test_above_baseline_zero_loss(clean):
    r=integrate(dict(clean['estimates'][0],actual_kw='110'));assert r['loss_kwh']=='0E-28';assert r['code']=='NO_LOSS'
def test_exact_hour_integral(clean):
    r=integrate(dict(clean['estimates'][0],seconds=3600));assert Decimal(r['loss_kwh'])==Decimal(40)
def test_no_estimate_not_fake_zero(clean):
    r=integrate(dict(clean['estimates'][0],baseline_kw=None));assert r['loss_kwh'] is None;assert r['actual_kwh'] is None
def test_half_hour_integral(clean):
    r=integrate(dict(clean['estimates'][0],seconds=1800));assert Decimal(r['loss_kwh'])==20
