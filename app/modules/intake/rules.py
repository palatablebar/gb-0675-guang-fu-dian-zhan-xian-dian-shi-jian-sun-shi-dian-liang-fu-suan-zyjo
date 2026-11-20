from .reader import read_source
FIELDS=['id', 'kind', 'device', 'at', 'power', 'unit', 'irradiance', 'status', 'start', 'end']
def apply(state):read_source(state,FIELDS,{'编号':'id'})
