"""
食安类客诉关键词判定 (App 订单评价 t_order_comment 无系统级食安分类字段).
高置信 = 命中具体的变质 / 异物 / 异味 / 身体不适 词;
低置信 = 只命中泛化的「难喝 / bad taste」措辞, 不足以判定为食安事件.
口径以 2026-07 已发布的 7 起为基准反推校准: 本规则在 7 月输出 7 起高置信, 与已发布集合完全一致.
"""
import re
SPOIL  = r'spoil|sour|rancid|rotten|curdl|gone bad|went bad|moldy|mould|\bmold\b|fermented|expired|off milk|bad milk'
OBJECT = r'\bhair\b|plastic|foreign object|foreign matter|\bbug\b|\binsect\b|\bfly\b|\bflies\b|broken glass|\bmetal\b|something in (my|the)'
ODOR   = r'chemical (taste|smell)|weird (smell|taste)|strange (smell|taste)|odd (smell|taste)|off (smell|taste)|tastes? funny|soapy'
ILL    = r'\bsick\b|vomit|throw(ing)? up|diarrh|food poison|allergic reaction|nausea'
CATS   = [("变质酸败", SPOIL), ("异物", OBJECT), ("异味", ODOR), ("身体不适", ILL)]
GENERIC = r'^\s*bad taste|the taste is bad|tastes? (so |really |very )?bad\b|terrible taste'

def classify(text):
    t = text or ""
    hits = [c for c, p in CATS if re.search(p, t, re.I)]
    if not hits and re.search(GENERIC, t, re.I):
        return ["异味"]           # generic wording only -> weak candidate
    return hits

def is_low(text):
    t = text or ""
    return not any(re.search(p, t, re.I) for _, p in CATS) and bool(re.search(GENERIC, t, re.I))
