import csv, io, hashlib
from app.errors import BusinessError
from app.reasons import reject

def read_source(state, fields, aliases):
    raw=state['raw_bytes']
    if not raw: raise BusinessError('EMPTY_FILE','请选择非空文件')
    if not raw.strip(b'\xef\xbb\xbf\r\n \t'): raise BusinessError('BLANK_FILE','文件只有空行')
    text=None
    for encoding in ('utf-8-sig','gb18030'):
        try: text=raw.decode(encoding);break
        except UnicodeDecodeError: continue
    if text is None: raise BusinessError('BAD_ENCODING','文件编码无法识别')
    stream=csv.reader(io.StringIO(text,newline=''),strict=True)
    try:
        original=next(stream)
        header=[aliases.get(v.strip(),v.strip()) for v in original]
        if header!=fields: raise BusinessError('BAD_HEADER','字段或顺序不匹配')
        state['counts']={'input':0,'blank':0,'repeated_header':0,'duplicate':0}
        records=[]
        for cells in stream:
            line=stream.line_num
            state['counts']['input']+=1
            if not cells or not any(v.strip() for v in cells):
                state['counts']['blank']+=1;continue
            if cells==original:
                state['counts']['repeated_header']+=1;continue
            row=dict(zip(header,cells));row['_line']=line
            if len(cells)!=len(header): reject(state,row,'COLUMN_COUNT',f'需要{len(header)}列，实际{len(cells)}列');continue
            if not row.get('id','').strip(): reject(state,row,'MISSING_ID','编号不能为空');continue
            row['id']=row['id'].strip();records.append(row)
    except csv.Error:
        raise BusinessError('BROKEN_CSV','CSV引号或末行损坏')
    if not state['counts']['input']: raise BusinessError('HEADER_ONLY','文件只有表头')
    by_id={}
    for row in records: by_id.setdefault(row['id'],[]).append(row)
    selected=[]
    for key,rows in by_id.items():
        identities={tuple((k,v) for k,v in r.items() if k!='_line') for r in rows}
        if len(identities)>1:
            for row in rows: reject(state,row,'DUPLICATE_CONFLICT','同一编号存在不同原值')
        else:
            selected.append(rows[0]);state['counts']['duplicate']+=len(rows)-1
    state['records']=selected
    state['encoding']=encoding
    state['views'][state['context']['keys'][0]]={'rows':[dict(r) for r in selected], 'metrics':{'采信行':len(selected),'隔离行':len(state['quarantine']),'重复行':state['counts']['duplicate']},'title':'原始证据'}
