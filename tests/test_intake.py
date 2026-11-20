from app.engine import evaluate
from app.errors import BusinessError
from app.config import ROOT
import pytest

def test_bom_source(sample):
    # TRAP-02
    assert sample['records'][0]['id']=='INV-A-00'
def test_legacy_source():
    # TRAP-01
    s=evaluate({'dataset':'legacy'});assert s['encoding']=='gb18030';assert s['records'][0]['status']=='健康'
def test_segment_header(sample):
    # TRAP-04
    assert sample['counts']['repeated_header']==1
def test_bad_column(sample):
    # TRAP-05
    assert next(r for r in sample['quarantine'] if r['id']=='COLUMN')['code']=='COLUMN_COUNT'
def test_same_source_duplicate(sample):
    assert sample['counts']['duplicate']==1
def test_three_empty_types():
    # TRAP-18
    for text,code in [('', 'EMPTY_FILE'),('\n\n','BLANK_FILE'),((ROOT/'sample_data/clean.csv').read_text().splitlines()[0]+'\n','HEADER_ONLY')]:
        with pytest.raises(BusinessError) as e:evaluate({'csv_text':text})
        assert e.value.code==code
def test_source_rows_real(clean):
    assert clean['counts']['input']==33
