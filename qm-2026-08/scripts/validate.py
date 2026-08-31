#!/usr/bin/env python3
"""July self-check: run the identical derivations on 2026-07 and diff vs the published deck."""
import json, collections, sys, re
from pathlib import Path
sys.path.insert(0,'.')
from fs_kw import classify
RAW=Path('../raw')
def L(n): return json.load(open(RAW/f"{n}.json"))
PRIO={'QA/QC-Store food safety audit':0,'OM-Area food safety Check':1}
MOD={'Cleaning and Sanitation':'清洁卫生','Process Control':'过程控制','Facility':'设施','Document Record':'证照',
 'Workplace Safety':'职业安全','Site Security':'职业安全','Pests Control':'虫害防控',
 'Maintenance of Equipment':'设备维护','Approved Supplier':'供应链'}
def mcn(n):
    if not n: return ''
    n=n.strip()
    if n in MOD: return MOD[n]
    if n.startswith('Employees') and 'Health' in n: return '员工健康卫生'
    if n.startswith('Temperature'): return '温控有效期'
    return f'(未映射){n}'
def kind(n):
    if n.startswith('QA/QC'): return 'QA'
    if n.startswith('OM-'): return 'OM'
    if 'self-check' in n: return 'SELF'
    return 'OTHER'
def frame(m):
    heads={r['check_no']:r for r in L(f"audit_headers_{m}")}
    byrep=collections.defaultdict(list)
    for o in L(f"audit_opps_{m}"): byrep[o['check_no']].append(o)
    fr=[]
    for r in L(f"audit_reports_{m}"):
        h=heads.get(r['check_no'],{})
        os_=[o for o in byrep[r['check_no']] if o['opp_deleted']==0]
        live=[o for o in os_ if o['opp_status']==1]
        sa=[o['score_start'] for o in os_ if o['score_start'] is not None]
        sl=[o['score_start'] for o in live if o['score_start'] is not None]
        fr.append(dict(r=r,h=h,o=os_,pre=(min(sa) if sa else 100)+sum(x['original_score'] or 0 for x in os_),
                       post=(min(sl) if sl else 100)+sum(x['original_score'] or 0 for x in live)))
    return fr
def valid(fr): return [f for f in fr if f['h'].get('submitted')==1 and f['h'].get('deleted')==0]
def main_insp(fr):
    best={}
    for f in valid(fr):
        r=f['r']; d=r['dept_id']; k=(PRIO.get(r['large_category_name'],2),r['check_date'],r['check_no'])
        if d not in best or k[0]<best[d][0][0] or (k[0]==best[d][0][0] and (k[1],k[2])>(best[d][0][1],best[d][0][2])):
            best[d]=(k,f)
    return [v[1] for v in best.values()]
def grade(s): return 'A+' if s>=94 else 'A' if s>=87 else 'B' if s>=80 else 'C'
R={}
for m in ["2026-07","2026-08"]:
    fr=frame(m); vf=valid(fr); out={}
    cnt=collections.defaultdict(lambda:[0,set()])
    for f in vf:
        k=kind(f['r']['large_category_name']); cnt[k][0]+=1; cnt[k][1].add(f['r']['dept_id'])
    out['counts']={k:[v[0],len(v[1])] for k,v in cnt.items()}
    out['total']=sum(v[0] for k,v in cnt.items() if k in('QA','OM','SELF'))
    qa=[f for f in vf if kind(f['r']['large_category_name'])=='QA']
    latest={}
    for f in qa:
        d=f['r']['dept_id']
        if d not in latest or (f['r']['check_date'],f['r']['check_no'])>(latest[d]['r']['check_date'],latest[d]['r']['check_no']): latest[d]=f
    ql=list(latest.values())
    out['qa_avg_post']=round(sum(f['post'] for f in ql)/len(ql),1); out['qa_avg_pre']=round(sum(f['pre'] for f in ql)/len(ql),1)
    out['qa_grade_post']=dict(collections.Counter(grade(f['post']) for f in ql))
    out['qa_grade_pre'] =dict(collections.Counter(grade(f['pre'])  for f in ql))
    sev=collections.Counter()
    for f in qa:
        for o in f['o']: sev[o['deduction_type']]+=1
    out['qa_sev']={'S':sev.get(1,0),'M':sev.get(3,0),'G':sev.get(2,0),'L':sev.get(4,0)}
    st=len({f['r']['dept_id'] for f in qa})
    out['qa_per_store']={k:round(v/st,2) for k,v in out['qa_sev'].items()}
    mi=main_insp(fr); mod=collections.Counter()
    for f in mi:
        for o in f['o']: mod[mcn(o['module_name'])]+=(o['original_score'] or 0)
    out['main_modules']=dict(sorted(mod.items(),key=lambda x:x[1]))
    out['main_n']=len(mi)
    R[m]=out
PUB={'SELF':[54,21],'QA':[19,18],'OM':[21,21]}
print("======= [稽核] 2026-07 自校验 =======")
j=R['2026-07']
for k,lab in [('SELF','门店自检'),('QA','QA稽核'),('OM','区经检查')]:
    g=j['counts'][k]; p=PUB[k]
    print(f"  {lab}: 次数 {g[0]} vs 公布 {p[0]} {'✅' if g[0]==p[0] else '❌'} | 门店 {g[1]} vs {p[1]} {'✅' if g[1]==p[1] else '❌'}")
print(f"  合计 {j['total']} vs 94 {'✅' if j['total']==94 else '❌'}")
print(f"  QA 申诉后均分 {j['qa_avg_post']} vs 92.1 {'✅' if j['qa_avg_post']==92.1 else '❌'} | 申诉前 {j['qa_avg_pre']} vs 76.7 {'✅' if j['qa_avg_pre']==76.7 else '❌'}")
print(f"  QA 分级(后) {j['qa_grade_post']} vs A+8/A8/B2/C0")
print(f"  QA 分级(前) {j['qa_grade_pre']} vs A+0/A7/B1/C10")
print(f"  QA 严重度 {j['qa_sev']} vs 关键13/重点7 | 店均 {j['qa_per_store']} vs S0.62/M0.33/G3.43/L0.71")
print(f"  主巡检模块扣分 (n={j['main_n']}): {j['main_modules']}")
print("     公布: 清洁卫生-118 设施-56 温控-25 过程-24 虫害-11 职安-10 员工-9 设备-6")
print("\n======= [稽核] 2026-08 =======")
a=R['2026-08']
print(f"  {a['counts']}  合计 {a['total']}")
print(f"  QA 均分 后 {a['qa_avg_post']} 前 {a['qa_avg_pre']} | 分级后 {a['qa_grade_post']} 前 {a['qa_grade_pre']}")
print(f"  QA 严重度 {a['qa_sev']} 店均 {a['qa_per_store']}")
print(f"  主巡检模块扣分 (n={a['main_n']}): {a['main_modules']}")
json.dump(R, open(RAW/"_validation.json","w"), ensure_ascii=False, indent=1)
