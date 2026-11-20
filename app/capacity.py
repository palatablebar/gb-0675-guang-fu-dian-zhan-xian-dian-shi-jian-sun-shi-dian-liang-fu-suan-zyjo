from datetime import timedelta
from app.coerce import number, instant
from app.errors import BusinessError

# 容量凭证裁定：每台设备的额定容量以凭证为准（编号、额定kW、生效区间、来源）。
# 观测区间须被唯一取值的凭证完整覆盖才可复算；取值冲突或覆盖空档的片段保持待复核。

def credentials_for(context, device):
    explicit = [dict(c) for c in context.get('capacity_credentials', []) if c.get('device') == device]
    if explicit:
        return explicit
    # 未登凭证的设备回退台账额定，视为全时段有效的隐式凭证。
    return [{'id': f'CAP-{device}-LEDGER', 'device': device,
             'capacity_kw': context['devices'][device]['capacity_kw'],
             'valid_from': None, 'valid_to': None, 'source': '台账额定'}]

def _edge(value):
    if value is None or str(value).strip() == '':
        return None
    try:
        return instant(value)
    except BusinessError:
        raise BusinessError('BAD_CAPACITY_VALIDITY', '容量凭证有效期无法解析')

def edges(cred):
    """凭证生效区间，缺省为开口；无法解析视为配置错误。"""
    return _edge(cred.get('valid_from')), _edge(cred.get('valid_to'))

def _covers(cred, start, end):
    since, until = edges(cred)
    return (since is None or since <= start) and (until is None or end <= until)

def _public(cred):
    return {'id': cred['id'], 'capacity_kw': str(number(cred['capacity_kw'])), 'source': cred.get('source', ''),
            'valid_from': cred.get('valid_from') or '', 'valid_to': cred.get('valid_to') or ''}

def resolve(context, device, start, end=None):
    """裁定覆盖[start,end)的容量凭证，返回(凭证, 原因码, 候选清单)。"""
    end = end if end is not None else start
    creds = credentials_for(context, device)
    covering = [c for c in creds if _covers(c, start, end)]
    values = {str(number(c['capacity_kw'])) for c in covering}
    if not covering:
        return None, 'CAPACITY_GAP', [_public(c) for c in sorted(creds, key=lambda c: c['id'])]
    if len(values) > 1:
        return None, 'CAPACITY_CONFLICT', [_public(c) for c in sorted(covering, key=lambda c: c['id'])]
    # 同值多份不算冲突，取生效最新的一份，结果可重现。
    chosen = sorted(covering, key=lambda c: (str(c.get('valid_from') or ''), c['id']))[-1]
    return chosen, 'CAPACITY_OK', []

def resolve_at(context, device, at, cadence_seconds):
    """按遥测左值保持区间[at, at+cadence)裁定该观测的容量凭证。"""
    return resolve(context, device, at, at + timedelta(seconds=cadence_seconds))
