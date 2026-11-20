from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone
import unicodedata, re
from app.config import SENTINELS
from app.errors import BusinessError

def number(value, unit=''):
    text = unicodedata.normalize('NFKC', str(value)).strip()
    if text.upper() in SENTINELS or text in SENTINELS:
        raise BusinessError('MISSING_VALUE', '数值缺失')
    if unit and text.endswith(unit):
        text = text[:-len(unit)].strip()
    if ',' in text:
        if not re.fullmatch(r'[+-]?\d{1,3}(,\d{3})+(\.\d+)?', text):
            raise BusinessError('BAD_NUMBER', '千分位格式错误')
        text = text.replace(',', '')
    try:
        val = Decimal(text)
        if not val.is_finite(): raise InvalidOperation
        return val
    except InvalidOperation:
        raise BusinessError('BAD_NUMBER', '数值格式错误')

def money(value):
    return format(Decimal(value).quantize(Decimal('.01'), rounding=ROUND_HALF_UP), 'f')

def instant(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if dt.tzinfo is None: raise ValueError
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        raise BusinessError('BAD_TIME', '时间缺少有效偏移')

def decstr(value):
    return format(value, 'f') if isinstance(value, Decimal) else value
