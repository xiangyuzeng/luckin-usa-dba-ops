import json, collections, re, sys
sys.path.insert(0,'.')
from fs_kw import classify
RAW='../raw'
def L(n): return json.load(open(f"{RAW}/{n}.json"))
sup={s['supplier_mid']:s['supplier_name'] for s in L("suppliers")}
spec={g['spec_mid']:g for g in L("goods_spec")}
def month(tag, ym):
    p=[r for r in L(f"pqnc_{tag}") if str(r['created_time'])[:7]==ym]
    det=collections.defaultdict(list)
    for d in L(f"pqnc_detail_{tag}"): det[d['pqnc_id']].append(d)
    return p, det
SPOIL=re.compile(r'spoil|sour|rancid|rotten|curdl|smell|odor|discolor|mold|foreign|contaminat',re.I)
for tag,ym,pub in [("jul_wide","2026-07",True),("aug_wide","2026-08",False)]:
    p,det=month(tag,ym)
    alive=[r for r in p if r['delete_flag']==0]
    tot=sum(float(r['value_amount'] or 0) for r in alive)
    print(f"\n===== PQNC {ym}: rows={len(p)} (未删除 {len(alive)}, 已删除 {len(p)-len(alive)})  货值 ${tot:.2f}")
    def firstj(r):
        j=sorted([d for d in det[r['pqnc_id']] if d['operate_type']==1], key=lambda x:x['id'])
        return j[0] if j else None
    def lastj(r):
        j=sorted([d for d in det[r['pqnc_id']] if d['operate_type']==1], key=lambda x:x['id'])
        return j[-1] if j else None
    for lab,fn in [("当前 responsibility", lambda r:r['responsibility']),
                   ("首次判责 responsibility", lambda r:(firstj(r) or {}).get('responsibility'))]:
        c=collections.Counter(); a=collections.defaultdict(float)
        for r in alive: c[fn(r)]+=1; a[fn(r)]+=float(r['value_amount'] or 0)
        print(f"  -- {lab}: " + " | ".join(f"{k}:{v}起 ${a[k]:.2f}" for k,v in sorted(c.items(),key=lambda x:str(x[0]))))
    # supplier-responsibility detail on the first-judgment basis
    s1=[r for r in alive if (firstj(r) or {}).get('responsibility')==1]
    print(f"  -- 首次判责=供应商: {len(s1)} 起 ${sum(float(r['value_amount'] or 0) for r in s1):.2f}")
    cs=collections.Counter(); ca=collections.defaultdict(float)
    for r in s1:
        k=spec.get(r['spec_mid'],{}).get('small_class_name') or '(无规格主数据)'
        cs[k]+=1; ca[k]+=float(r['value_amount'] or 0)
    print("      按货物小类: " + " | ".join(f"{k} {v}起 ${ca[k]:.2f}" for k,v in cs.most_common()))
    cv=collections.Counter()
    for r in s1: cv[sup.get(r['supplier_mid'],'(无供应商)')]+=1
    print("      按供应商: " + " | ".join(f"{k} {v}" for k,v in cv.most_common()))
    # type
    tc=collections.Counter(); tl=collections.Counter()
    for r in alive:
        tc[(firstj(r) or {}).get('one_pqnc_type_code')]+=1
        tl[(lastj(r) or {}).get('one_pqnc_type_code')]+=1
    print(f"  -- 类型(首次判责): {dict(tc)}   类型(最新判责): {dict(tl)}")
    fs=[r for r in alive if ((lastj(r) or {}).get('one_pqnc_type_code') in ('0002','0003')
        or (firstj(r) or {}).get('one_pqnc_type_code') in ('0002','0003')
        or SPOIL.search((r['problem_description'] or '')+' '+' '.join(d.get('description') or '' for d in det[r['pqnc_id']])))]
    print(f"  -- 重建口径「食安」: {len(fs)} 起 / 普通 {len(alive)-len(fs)}")
    spoil_cluster=[r for r in alive if any((d.get('description') or '').startswith('Spoilage') for d in det[r['pqnc_id']])]
    major=[r for r in alive if (firstj(r) or {}).get('one_pqnc_type_code') in ('0002','0003')]
    print(f"     其中 判责说明以 'Spoilage' 开头: {len(spoil_cluster)} 起; Major/Critical: {len(major)} 起; 两者合计(去重): {len(set(id(x) for x in spoil_cluster)|set(id(x) for x in major))}")
    rb=collections.Counter()
    for r in alive:
        for d in det[r['pqnc_id']]:
            if d['operate_type']==2: rb[d['return_reason']]+=1
    print(f"  -- 退回操作(operate_type=2)按原因: {dict(rb)}; 涉及单数 {len({d['pqnc_id'] for r in alive for d in det[r['pqnc_id']] if d['operate_type']==2})}")
