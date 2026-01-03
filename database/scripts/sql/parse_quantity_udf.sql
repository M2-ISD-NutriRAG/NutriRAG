CREATE OR REPLACE FUNCTION PARSE_QUANTITY_STRING(s STRING)
RETURNS FLOAT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.9'
HANDLER = 'run'
AS $$
import re, math

VULGAR_TO_ASCII = {
    '¼':'1/4','½':'1/2','¾':'3/4','⅐':'1/7','⅑':'1/9','⅒':'1/10',
    '⅓':'1/3','⅔':'2/3','⅕':'1/5','⅖':'2/5','⅗':'3/5','⅘':'4/5',
    '⅙':'1/6','⅚':'5/6','⅛':'1/8','⅜':'3/8','⅝':'5/8','⅞':'7/8'
}

def normalize_fractions(x: str) -> str:
    if not isinstance(x, str):
        return x
    for k,v in VULGAR_TO_ASCII.items():
        x = x.replace(k,v)
    return x.replace('⁄','/')

def parse_single_expr(expr: str):
    if not isinstance(expr, str):
        return None
    expr = expr.strip()
    if expr == "":
        return None
    m = re.match(r'^(-?\d+)\s+(\d+)/(\d+)$', expr)
    if m:
        return int(m.group(1)) + int(m.group(2))/int(m.group(3))
    m = re.match(r'^(-?\d+)/(\d+)$', expr)
    if m:
        return int(m.group(1))/int(m.group(2))
    m = re.match(r'^-?\d+(?:[.,]\d+)?$', expr)
    if m:
        return float(expr.replace(',', '.'))
    return None

def run(s: str):
    if s is None:
        return None
    s = normalize_fractions(str(s))
    s = s.replace('–','-').replace('—','-')
    s = re.sub(r'\s*-\s*',' - ',s)
    parts = [p.strip() for p in s.split(' - ') if p.strip()]
    vals = [parse_single_expr(p) for p in parts[:2]]
    for i,v in enumerate(vals):
        if v is None and i < len(parts):
            m = re.search(r'(?:(\d+)\s+(\d+/\d+))|(\d+/\d+)|(-?\d+(?:[.,]\d+)?)', parts[i])
            if m:
                vals[i] = parse_single_expr(m.group(0))
    parsed_vals = [v for v in vals if v is not None]
    if not parsed_vals:
        return None
    return sum(parsed_vals)/len(parsed_vals)
$$;
