from app.modules.archive.rules import archive_decision
from app.archive import serialize
from copy import deepcopy
import zipfile,io,json

def test_clean_ready(clean):
    assert clean['archive']['status']=='可归档'
def test_dirty_not_ready(sample):
    assert sample['archive']['status']=='待复核'
def test_segment_count_real(clean):
    assert clean['archive']['segments']==5;assert clean['archive']['unknown']==0
def test_unknown_blocks(clean):
    s=deepcopy(clean);s['balance']['unknown_segments']=1;assert archive_decision(s)['status']=='待复核'
def test_bad_energy_blocks(clean):
    s=deepcopy(clean);s['balance']['energy_balanced']=False;assert archive_decision(s)['status']=='待复核'
def test_bundle_has_isolation(sample):
    z=zipfile.ZipFile(io.BytesIO(serialize(sample)));e=json.loads(z.read('evidence.json'));assert len(e['quarantine'])==5
def test_bundle_manifest(clean):
    z=zipfile.ZipFile(io.BytesIO(serialize(clean)));assert json.loads(z.read('manifest.json'))['sha256']==clean['manifest']['sha256']
