#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
July 2026 QA store-inspection — DATA PACK builder.
Consumes build_core (CSVs + derived aggregates) and writes:
  july2026_qa_datapack.md    (section-keyed, human-readable — primary)
  july2026_qa_datapack.json  (same content, structured — backup)
Real numbers only. No report prose / no docx.
"""
import json
from collections import defaultdict, Counter
from pathlib import Path
import build_core as B

HERE = Path(__file__).resolve().parent
SEVP = B.SEV_POINTS
CANON = B.CANON_MODULES
NPRIM = len(B.PRIMARY)   # 21

PRIOR_AVG = 88.7          # June 2026 primary average (published LCNA-QA-2026-006)
PRIOR_N   = 18            # June comparable store baseline
PRIOR_TOTAL_INSP = 85     # June analytical inspections

# ---- convenience views -------------------------------------------------
SUMMARY   = B.SUMMARY
ITEMS     = B.ITEMS
PRIMARY   = B.PRIMARY               # store_code -> summary row
PRIM_IIDS = B.PRIMARY_IIDS
PITEMS    = [it for it in ITEMS if it["inspection_id"] in PRIM_IIDS]     # 主巡检 findings
JUNP      = B.JUNE_PRIMARY

SNAME_BY_CODE = {s["shop_no"]: s["shop_name"] for s in B.STO}
OPEN_BY_CODE  = {s["shop_no"]: (s.get("set_up_time") or "")[:10] for s in B.STO}
def storename(code): return SNAME_BY_CODE.get(code, code)
def disp(code): return f"{storename(code)}({code})"
def fmt_scores(v):
    lab={"门店自检_avg":"自检","QA审计":"QA","区经检查":"区经"}
    return " / ".join(f"{lab.get(k,k)} {val}" for k,val in v.items())

def _cell(c):
    if c is None: return ""
    s = str(c).replace("\r\n"," / ").replace("\n"," / ").replace("\r"," / ").replace("|","/")
    return s.strip()
def mdtable(headers, rows):
    out = ["| " + " | ".join(_cell(h) for h in headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        out.append("| " + " | ".join(_cell(c) for c in r) + " |")
    return "\n".join(out)

MD = []
PACK = {}
def sec(title): MD.append("\n## " + title + "\n")
def p(s=""): MD.append(s)

# ======================================================================
# COVER / 文档信息
# ======================================================================
qa_auditors = Counter(r["inspector_name"] for r in SUMMARY if r["inspection_type"]=="QA审计")
area_insp   = Counter(r["inspector_name"] for r in SUMMARY if r["inspection_type"]=="区经检查")
self_insp   = Counter(r["inspector_name"] for r in SUMMARY if r["inspection_type"]=="门店自检")
fm_sev = Counter(it["severity"] for it in ITEMS)
pm_sev = Counter(it["severity"] for it in PITEMS)
appeals = [r for r in SUMMARY if r["is_appealed"]]
ap_by = Counter(r["appeal_status"] for r in appeals)
prim_scores = [p_["adjusted_total_score"] for p_ in PRIMARY.values() if isinstance(p_["adjusted_total_score"],int)]
prim_avg = round(sum(prim_scores)/len(prim_scores),1)

# stores newly entering the primary-inspection scope this month
NEW_STORES = sorted([c for c in PRIMARY if c not in JUNP])

# per-type date tempo (data-driven)
def tempo_range(typ_):
    ds = sorted(r["inspection_date"] for r in SUMMARY if r["inspection_type"]==typ_)
    return (ds[0], ds[-1]) if ds else ("","")

cover = {
  "doc_id":"LCNA-QA-2026-007","report_period":"2026年7月",
  "date_range":"2026-07-01 .. 2026-07-31","days":31,
  "active_stores_operational":NPRIM,
  "active_stores_total":NPRIM+len(B.OPENED_NOT_INSPECTED),
  "opened_not_inspected":B.OPENED_NOT_INSPECTED,
  "new_stores_this_month":[{"store":c,"name":storename(c),"open_date":OPEN_BY_CODE.get(c,"")} for c in NEW_STORES],
  "type_counts":{"门店自检":self_insp.total(),"QA审计":qa_auditors.total(),"区经检查":area_insp.total(),
                 "total":len(SUMMARY)},
  "misfiled_dropped":len(B.MISFILED),
  "findings_full_month":{"S":fm_sev["S"],"M":fm_sev["M"],"G":fm_sev["G"],"L":fm_sev["L"],"total":sum(fm_sev.values())},
  "findings_primary":{"S":pm_sev["S"],"M":pm_sev["M"],"G":pm_sev["G"],"L":pm_sev["L"],"total":sum(pm_sev.values())},
  "appeals":{"total":len(appeals),"approved":ap_by.get("approved",0),"denied":ap_by.get("denied",0),"pending":ap_by.get("pending",0)},
  "qa_staffing":dict(qa_auditors),"area_staffing":dict(area_insp),
  "primary_avg":prim_avg,"coverage":f"{NPRIM}/{NPRIM}",
  "tempo":{t:tempo_range(t) for t in ["门店自检","QA审计","区经检查"]},
}
PACK["cover"]=cover
sec("[COVER/文档信息]")
p(f"- 文档编号：**LCNA-QA-2026-007**　报告期：**2026年7月**（2026-07-01 .. 2026-07-31，31 天）")
p(f"- 活跃门店：**{NPRIM} 家运营在营门店**（主巡检口径），全部完成巡检；未巡检门店 {len(B.OPENED_NOT_INSPECTED)} 家")
p(f"  - 计数口径：t_shop_info status=1 且非测试厨房（SL12/US999xx/US00000），open_date≤2026-07-31")
_new_txt = "，".join("{} 开业{}".format(disp(c), OPEN_BY_CODE.get(c, "")) for c in NEW_STORES) or "无"
p(f"  - 本月新纳入主巡检门店（6月无主巡检基准）：{_new_txt}")
p(f"- 巡检类型次数：门店自检 {self_insp.total()} / QA审计 {qa_auditors.total()} / 区经检查 {area_insp.total()} = **共 {len(SUMMARY)} 次**（{len(SUMMARY)+len(B.MISFILED)} 次提交 − {len(B.MISFILED)} 误提交）")
p(f"- 全月发现项：S {fm_sev['S']} / M {fm_sev['M']} / G {fm_sev['G']} / L {fm_sev['L']} = **{sum(fm_sev.values())}**")
p(f"- 主巡检发现项：S {pm_sev['S']} / M {pm_sev['M']} / G {pm_sev['G']} / L {pm_sev['L']} = **{sum(pm_sev.values())}**")
p(f"- 申诉：**{len(appeals)} 起立案（{ap_by.get('approved',0)} 获批 / {ap_by.get('denied',0)} 驳回 / {ap_by.get('pending',0)} 审批中）**")
p(f"- QA 审计人员：{', '.join(f'{k} {v} 次' for k,v in qa_auditors.items())}（Senior QA Manager）")
p(f"- 区经检查人员：{', '.join(f'{k} {v} 次' for k,v in area_insp.items())}（Area Operations Manager）")
p(f"- 节奏区间：" + "；".join(f"{t} {a}~{b}" for t,(a,b) in cover["tempo"].items()))

# ======================================================================
# §管理摘要
# ======================================================================
s_items = [it for it in ITEMS if it["severity"]=="S"]
s_by_sub = defaultdict(lambda:{"n":0,"stores":set()})
for it in s_items:
    s_by_sub[it["sub_item"]]["n"]+=1; s_by_sub[it["sub_item"]]["stores"].add(it["store_code"])
top_s = sorted(s_by_sub.items(), key=lambda kv:(-kv[1]["n"],-len(kv[1]["stores"])))
biggest_s = top_s[0]

def store_type_scores():
    d = defaultdict(dict)
    self_scores = defaultdict(list)
    for r in SUMMARY:
        if r["inspection_type"]=="门店自检":
            if isinstance(r["adjusted_total_score"],int): self_scores[r["store_code"]].append(r["adjusted_total_score"])
        else:
            d[r["store_code"]][r["inspection_type"]] = r["adjusted_total_score"]
    for c,v in self_scores.items():
        d[c]["门店自检_avg"] = round(sum(v)/len(v),1)
    return d
STS = store_type_scores()
divergences=[]
for c,v in STS.items():
    vals = {k:val for k,val in v.items() if isinstance(val,(int,float))}
    if len(vals)>=2 and (max(vals.values())-min(vals.values()))>=20:
        divergences.append((c,vals,round(max(vals.values())-min(vals.values()),1)))
divergences.sort(key=lambda x:-x[2])

movers=[]
for c,pr in PRIMARY.items():
    if isinstance(pr["adjusted_total_score"],int) and isinstance(JUNP.get(c),int):
        movers.append((c, JUNP[c], pr["adjusted_total_score"], pr["adjusted_total_score"]-JUNP[c]))
improvers=sorted([m for m in movers if m[3]>0], key=lambda x:-x[3])
decliners=sorted([m for m in movers if m[3]<0], key=lambda x:x[3])
flat=[m for m in movers if m[3]==0]

# like-for-like average across the 18 stores that also had a June primary
ll_scores=[pr["adjusted_total_score"] for c,pr in PRIMARY.items() if c in JUNP and isinstance(pr["adjusted_total_score"],int)]
ll_avg=round(sum(ll_scores)/len(ll_scores),1) if ll_scores else None

mgmt = {
 "primary_avg":prim_avg,"coverage":f"{NPRIM}/{NPRIM}=100%","prior_primary_avg":PRIOR_AVG,"prior_baseline_n":PRIOR_N,
 "like_for_like_avg":ll_avg,"like_for_like_n":len(ll_scores),
 "total_findings_full_month":sum(fm_sev.values()),
 "callout_a":f"巡检量 {len(SUMMARY)}（6月{PRIOR_TOTAL_INSP}），主巡检均分 {prim_avg}（6月{PRIOR_AVG}），覆盖 {NPRIM}/{NPRIM}=100%",
 "callout_b":{"sub_item":biggest_s[0],"count":biggest_s[1]["n"],"stores":len(biggest_s[1]["stores"])},
 "callout_c":{"divergences_ge20":[{"store":c,"scores":v,"gap":g} for c,v,g in divergences]},
 "biggest_improver":improvers[0] if improvers else None,
 "biggest_decliner":decliners[0] if decliners else None,
 "new_stores":NEW_STORES,
}
PACK["mgmt_summary"]=mgmt
sec("[§管理摘要]")
p(f"- 主巡检均分 **{prim_avg}**（6月 {PRIOR_AVG}，**{prim_avg-PRIOR_AVG:+.1f}**）；门店覆盖 **{NPRIM}/{NPRIM} = 100%**（6月基准 {PRIOR_N} 家，本月 +{NPRIM-PRIOR_N} 家新店纳管）")
p(f"- 同口径（仅 6 月有主巡检的 {len(ll_scores)} 家）均分 **{ll_avg}**（6月 {PRIOR_AVG}，{ll_avg-PRIOR_AVG:+.1f}）")
p(f"- 全月发现项合计 **{sum(fm_sev.values())}**（主巡检 {sum(pm_sev.values())}）")
p(f"- (a) 体系 vs 6月：巡检量 {PRIOR_TOTAL_INSP}→{len(SUMMARY)}（{len(SUMMARY)-PRIOR_TOTAL_INSP:+d} 次）；主巡检均分 {PRIOR_AVG}→{prim_avg}（**{prim_avg-PRIOR_AVG:+.1f}**）；覆盖率维持 100%")
p(f"- (b) 最大系统性 S 项集群：**{biggest_s[0]}** — {biggest_s[1]['n']} 项 S，涉及 {len(biggest_s[1]['stores'])} 家门店")
if divergences:
    p(f"- (c) 巡检员一致性旗标：{len(divergences)} 家门店存在同店跨类型 ≥20 分背离 → " +
      "；".join(f"{disp(c)} [{fmt_scores(v)}]（差 {g}）" for c,v,g in divergences))
else:
    p(f"- (c) 巡检员一致性旗标：无同店跨类型 ≥20 分背离")
if improvers: p(f"  - 最大改善：{disp(improvers[0][0])} {improvers[0][1]}→{improvers[0][2]}（+{improvers[0][3]}）")
if decliners: p(f"  - 最大下滑：{disp(decliners[0][0])} {decliners[0][1]}→{decliners[0][2]}（{decliners[0][3]}）")

# ======================================================================
# §1.1
# ======================================================================
prim_sorted = sorted(PRIMARY.items(), key=lambda kv:(-(kv[1]["adjusted_total_score"] if isinstance(kv[1]["adjusted_total_score"],int) else -1)))
highest = prim_sorted[0]; lowest = prim_sorted[-1]
s_stores = {it["store_code"] for it in PITEMS if it["severity"]=="S"}
below80 = [(c,pr["adjusted_total_score"]) for c,pr in PRIMARY.items() if isinstance(pr["adjusted_total_score"],int) and pr["adjusted_total_score"]<80]
s11 = {
 "highest":{"store":highest[0],"score":highest[1]["adjusted_total_score"]},
 "lowest":{"store":lowest[0],"score":lowest[1]["adjusted_total_score"]},
 "stores_with_S":sorted(s_stores),"n_stores_with_S":len(s_stores),
 "stores_below_80":sorted(below80,key=lambda x:x[1]),"coverage":f"{NPRIM}/{NPRIM}=100%","prior_coverage":f"{PRIOR_N}/{PRIOR_N}=100%",
}
PACK["s1_1"]=s11
sec("[§1.1] 主巡检概览")
p(f"- 最高分门店：**{disp(highest[0])} = {highest[1]['adjusted_total_score']}**")
p(f"- 最低分门店：**{disp(lowest[0])} = {lowest[1]['adjusted_total_score']}**")
p(f"- S 项门店数：**{len(s_stores)}** 家（{', '.join(disp(c) for c in sorted(s_stores))}）")
p(f"- <80 分门店数：**{len(below80)}** 家（{', '.join(f'{disp(c)} {sc}' for c,sc in sorted(below80,key=lambda x:x[1]))}）")
p(f"- 覆盖率：**{NPRIM}/{NPRIM} = 100%**（6月 {PRIOR_N}/{PRIOR_N} = 100%）")

# ======================================================================
# §1.2 full per-store primary table
# ======================================================================
rows12=[]; pack12=[]
for i,(c,pr) in enumerate(prim_sorted,1):
    nomded = pr["original_total_deduction"]
    star = "※" if pr["appeal_status"]=="approved" else ""
    rows12.append([i,storename(c),c,pr["adjusted_total_score"],pr["inspection_type"],nomded,
                   pr["S_count"],pr["M_count"],pr["G_count"],pr["L_count"],pr["inspector_name"],star])
    pack12.append({"rank":i,"store":c,"name":storename(c),"score":pr["adjusted_total_score"],
                   "type":pr["inspection_type"],"deduction":nomded,"S":pr["S_count"],"M":pr["M_count"],
                   "G":pr["G_count"],"L":pr["L_count"],"inspector":pr["inspector_name"],
                   "appeal_adjusted":star=="※","date":pr["inspection_date"],
                   "prior":JUNP.get(c),"is_new":c in NEW_STORES})
PACK["s1_2"]=pack12
sec("[§1.2] 主巡检全门店明细（按得分降序）")
p(mdtable(["#","门店","编号","得分","巡检类型","扣分","S","M","G","L","巡检员","※"], rows12))
p(f"\n注：扣分=名义扣分（Σ score_config，与 S/M/G/L 计数一致，不随申诉变动）；得分=官方调整后分（申诉获批已反映，含 S 项 −20 惩罚）；※=申诉获批调整。")

# ======================================================================
# §1.3 bands, cross-month, appeals, divergence, self-check S
# ======================================================================
bands = {"≥85":0,"80-84":0,"<80":0}
for c,pr in PRIMARY.items():
    s=pr["adjusted_total_score"]
    if not isinstance(s,int): continue
    bands["≥85"]+= s>=85; bands["80-84"]+= 80<=s<85; bands["<80"]+= s<80
selfcheck_S = [it for it in ITEMS if it["severity"]=="S" and it["inspection_type"]=="门店自检"]
s13={
 "bands":bands,"s_distribution":{"n_stores_with_S_primary":len(s_stores)},
 "improvers":[{"store":c,"jun":a,"jul":b,"delta":d} for c,a,b,d in improvers],
 "decliners":[{"store":c,"jun":a,"jul":b,"delta":d} for c,a,b,d in decliners],
 "flat":[{"store":c,"jun":a,"jul":b} for c,a,b,d in flat],
 "biggest_mover":{"improver":improvers[0][0] if improvers else None,"decliner":decliners[0][0] if decliners else None},
 "appeal_adjusted_stores":[c for c,pr in PRIMARY.items() if pr["appeal_status"]=="approved"],
 "cross_type_divergence":[{"store":c,"scores":v,"gap":g} for c,v,g in divergences],
 "selfcheck_S_discoveries":[{"store":it["store_code"],"sub_item":it["sub_item"],"desc":it["description"],"inspector":it["inspector_name"],"date":it["inspection_date"]} for it in selfcheck_S],
 "new_stores":[{"store":c,"score":PRIMARY[c]["adjusted_total_score"],"type":PRIMARY[c]["inspection_type"],
                "open_date":OPEN_BY_CODE.get(c,"")} for c in NEW_STORES],
}
PACK["s1_3"]=s13
sec("[§1.3] 分数带 / 跨月 / 申诉 / 背离 / 自检 S 项")
p(f"- 分数带：≥85 **{bands['≥85']}** 家 / 80–84 **{bands['80-84']}** 家 / <80 **{bands['<80']}** 家")
p(f"- S 项分布：{len(s_stores)} 家主巡检含 S 项")
p(f"- 环比改善（{len(improvers)} 家）：" + ("，".join(f"{disp(c)} {a}→{b}(+{d})" for c,a,b,d in improvers) or "无"))
p(f"- 环比下滑（{len(decliners)} 家）：" + ("，".join(f"{disp(c)} {a}→{b}({d})" for c,a,b,d in decliners) or "无"))
p(f"- 环比持平（{len(flat)} 家）：" + ("，".join(f"{disp(c)} {a}" for c,a,b,d in flat) or "无"))
p(f"- 新纳管门店（无 6 月基准，{len(NEW_STORES)} 家）：" + ("，".join(f"{disp(c)} {PRIMARY[c]['adjusted_total_score']}（{PRIMARY[c]['inspection_type']}，开业{OPEN_BY_CODE.get(c,'')}）" for c in NEW_STORES) or "无"))
if improvers and decliners: p(f"- 最大变动：改善 {disp(improvers[0][0])} +{improvers[0][3]}；下滑 {disp(decliners[0][0])} {decliners[0][3]}")
p(f"- 申诉调整门店（{len(s13['appeal_adjusted_stores'])} 家 ※）：{', '.join(disp(c) for c in s13['appeal_adjusted_stores'])}")
if divergences:
    p(f"- 同店跨类型背离（≥20分）：" + "；".join(f"{disp(c)} [{fmt_scores(v)}](差{g})" for c,v,g in divergences))
else:
    p(f"- 同店跨类型背离（≥20分）：无")
p(f"- 自检发现 S 项（{len(selfcheck_S)} 项）：" + ("；".join(f"{disp(it['store_code'])} {it['sub_item']} “{it['description'][:40]}”" for it in selfcheck_S) or "无"))

# ======================================================================
# module aggregation on 主巡检  (§2.1 §2.2 §2.3 §4.5)
# ======================================================================
mod_agg = {}
for m in CANON:
    its=[it for it in PITEMS if it["module"]==m]
    stores={it["store_code"] for it in its}
    sev=Counter(it["severity"] for it in its)
    ded=sum(it["deduction"] for it in its)
    cov=len(stores)/NPRIM
    risk="🔴" if cov>=0.5 else ("🟡" if cov>=0.3 else "🟢")
    mod_agg[m]={"problems":len(its),"deduction":ded,"stores":len(stores),"coverage":round(cov*100,1),
                "S":sev["S"],"M":sev["M"],"G":sev["G"],"L":sev["L"],"risk":risk,"store_set":sorted(stores)}
mods_by_ded=sorted(CANON,key=lambda m:mod_agg[m]["deduction"])   # most negative first
PACK["module_agg_primary"]=mod_agg

sec("[§2.1] 模块风险分层（主巡检覆盖率）")
for band,lbl in [("🔴","≥50% 门店"),("🟡","30–49% 门店"),("🟢","<30% 门店")]:
    ms=[m for m in CANON if mod_agg[m]["risk"]==band and mod_agg[m]["problems"]>0]
    covs=", ".join(f"{m}({mod_agg[m]['coverage']}%)" for m in ms) or "无"
    p(f"- {band} {lbl}：{covs}")
p(f"- 主巡检无扣分模块（未列示）：{', '.join(m for m in CANON if mod_agg[m]['problems']==0) or '无'}")

sec("[§2.2] 模块排名（主巡检，按扣分）")
rows22=[]
for m in mods_by_ded:
    a=mod_agg[m]
    if a["problems"]==0: continue
    rows22.append([m,a["problems"],a["deduction"],f"{a['stores']}/{NPRIM}",f"{a['coverage']}%",
                   a["S"],a["M"],a["G"],a["L"],a["risk"]])
p(mdtable(["模块","问题数","扣分","门店(n/N)","覆盖率","S","M","G","L","风险"],rows22))
p(f"\nΣ主巡检模块扣分 = {sum(mod_agg[m]['deduction'] for m in CANON)}")

sec("[§2.3] 扣分 Top5 模块逐条发现（主巡检，原文）")
top5=[m for m in mods_by_ded if mod_agg[m]["problems"]>0][:5]
s23={}
sevrank={"S":0,"M":1,"G":2,"L":3}
for m in top5:
    its=[it for it in PITEMS if it["module"]==m]
    its_ne=[it for it in its if it["description"] and len(it["description"].strip())>0]
    skipped=len(its)-len(its_ne)
    its_ne.sort(key=lambda it:(sevrank[it["severity"]], it["deduction"]))
    cap=its_ne[:20]; omitted=len(its_ne)-len(cap)
    p(f"\n**{m}**（{mod_agg[m]['problems']} 项，扣分 {mod_agg[m]['deduction']}；空描述跳过 {skipped}，超额省略 {omitted}）")
    rows=[[disp(it["store_code"]),it["sub_item"],it["severity"],it["deduction"],it["description"]] for it in cap]
    p(mdtable(["门店(code)","子项","严重度","扣分","描述原文"],rows))
    s23[m]={"problems":mod_agg[m]["problems"],"deduction":mod_agg[m]["deduction"],"skipped_empty":skipped,"omitted":omitted,
            "findings":[{"store":it["store_code"],"sub_item":it["sub_item"],"severity":it["severity"],
                         "deduction":it["deduction"],"description":it["description"]} for it in cap]}
PACK["s2_3"]=s23

# ======================================================================
# §3.1 severity distribution (primary)
# ======================================================================
SLA={"S":"2 天","M":"7 天","G":"14 天","L":"14 天"}
tot_pm=sum(pm_sev.values())
rows31=[]; s31={}
mod_by_sev=defaultdict(Counter)
for it in PITEMS: mod_by_sev[it["severity"]][it["module"]]+=1
for sv in ["S","M","G","L"]:
    main=mod_by_sev[sv].most_common(5)
    rows31.append([sv,pm_sev[sv],f"{round(pm_sev[sv]/tot_pm*100,1)}%",SLA[sv],
                   "、".join(f"{k}({v})" for k,v in main)])
    s31[sv]={"count":pm_sev[sv],"pct":round(pm_sev[sv]/tot_pm*100,1),"sla":SLA[sv],"main_modules":dict(main)}
PACK["s3_1"]=s31
sec("[§3.1] 严重度分布（主巡检）")
p(mdtable(["严重度","数量","占比","SLA","主要模块"],rows31))

# ======================================================================
# §3.2 S-item detail (primary)
# ======================================================================
sec("[§3.2] S 项明细（主巡检）")
prim_S=[it for it in PITEMS if it["severity"]=="S"]
rows32=[]; s32=[]
for i,it in enumerate(sorted(prim_S,key=lambda x:x["store_code"]),1):
    rows32.append([i,disp(it["store_code"]),f"{it['module']}/{it['sub_item']}",it["description"],
                   it["deduction"],it["inspection_type"],it["inspector_name"]])
    s32.append({"store":it["store_code"],"module":it["module"],"sub_item":it["sub_item"],
                "description":it["description"],"deduction":it["deduction"],"type":it["inspection_type"],
                "inspector":it["inspector_name"],"is_appealed_finding":it["is_appealed_finding"],"opp_status":it["_opp_status"]})
p(mdtable(["#","门店(code)","模块/子项","描述原文","扣分","巡检类型","巡检员"],rows32))
PACK["s3_2"]=s32

# ======================================================================
# §3.3 full-month S-item summary by sub-item
# ======================================================================
sec("[§3.3] 全月 S 项汇总（按子项）")
fm_S=[it for it in ITEMS if it["severity"]=="S"]
by_sub=defaultdict(lambda:{"n":0,"stores":set(),"mod":"","desc":[]})
for it in fm_S:
    b=by_sub[it["sub_item"]]; b["n"]+=1; b["stores"].add(it["store_code"]); b["mod"]=it["module"]
    if it["description"]: b["desc"].append(it["description"])
rows33=[]; s33=[]
for sub,b in sorted(by_sub.items(),key=lambda kv:-kv[1]["n"]):
    typ=(b["desc"][0][:60] if b["desc"] else "")
    rows33.append([f"{sub}[{b['mod']}]",b["n"],len(b["stores"]),typ])
    s33.append({"sub_item":sub,"module":b["mod"],"S_count":b["n"],"stores":len(b["stores"]),"typical":typ,
                "store_list":sorted(b["stores"])})
p(mdtable(["子项[模块]","S项数","门店数","典型问题(截取)"],rows33))
p(f"\n全月 S/M/G/L 合计：S {fm_sev['S']} / M {fm_sev['M']} / G {fm_sev['G']} / L {fm_sev['L']} = {sum(fm_sev.values())}")
p(f"主巡检 vs 全月：S 项 {pm_sev['S']}/{fm_sev['S']}；全部发现 {sum(pm_sev.values())}/{sum(fm_sev.values())}")
PACK["s3_3"]={"by_sub_item":s33,"full_month_sev":{k:fm_sev[k] for k in ['S','M','G','L']},
              "full_month_total":sum(fm_sev.values()),"primary_total":sum(pm_sev.values())}

# ======================================================================
# §3.4 M-item detail (primary)  §3.5 G/L by module
# ======================================================================
sec("[§3.4] M 项明细（主巡检）")
prim_M=[it for it in PITEMS if it["severity"]=="M"]
rows34=[]; s34=[]
for i,it in enumerate(sorted(prim_M,key=lambda x:x["store_code"]),1):
    rows34.append([i,disp(it["store_code"]),f"{it['module']}/{it['sub_item']}",it["description"],it["deduction"]])
    s34.append({"store":it["store_code"],"module":it["module"],"sub_item":it["sub_item"],"description":it["description"],"deduction":it["deduction"]})
p(mdtable(["#","门店(code)","模块/子项","描述原文","扣分"],rows34))
PACK["s3_4"]=s34

sec("[§3.5] G/L 项按模块计数（主巡检）")
g_by=Counter(it["module"] for it in PITEMS if it["severity"]=="G")
l_by=Counter(it["module"] for it in PITEMS if it["severity"]=="L")
p("- G 项：" + "，".join(f"{m}({g_by[m]})" for m in CANON if g_by[m]) )
p("- L 项：" + "，".join(f"{m}({l_by[m]})" for m in CANON if l_by[m]) )
PACK["s3_5"]={"G_by_module":dict(g_by),"L_by_module":dict(l_by)}

# ======================================================================
# §4.1 store × module deduction matrix (primary)
# ======================================================================
sec("[§4.1] 门店 × 模块 扣分矩阵（主巡检）")
cell=defaultdict(lambda:defaultdict(int))
for it in PITEMS: cell[it["store_code"]][it["module"]]+=it["deduction"]
store_tot={c:sum(cell[c].values()) for c in PRIMARY}
order=sorted(PRIMARY.keys(), key=lambda c:store_tot[c])   # most negative first
hdr=["门店(code)"]+CANON+["合计"]
rows41=[]
for c in order:
    row=[disp(c)]+[(cell[c][m] if cell[c][m]!=0 else "") for m in CANON]+[store_tot[c]]
    rows41.append(row)
tot_row=["合计"]+[sum(cell[c][m] for c in PRIMARY) or "" for m in CANON]+[sum(store_tot.values())]
rows41.append(tot_row)
p(mdtable(hdr,rows41))
full_cov_mods=[m for m in CANON if mod_agg[m]["stores"]==NPRIM]
p(f"\n100% 门店命中的模块：{', '.join(full_cov_mods) or '无'}")
PACK["s4_1"]={"matrix":{c:{m:cell[c][m] for m in CANON if cell[c][m]} for c in PRIMARY},
             "store_total":store_tot,"grand_total":sum(store_tot.values()),"full_coverage_modules":full_cov_mods}

# ======================================================================
# §4.2 lowest store attribution
# ======================================================================
sec("[§4.2] 最低分门店归因")
s42=[]
for lc,lp in prim_sorted[-2:][::-1] if len(prim_sorted)>=2 else prim_sorted:
    pass
def attrib_store(lc, lp):
    lmods=Counter(); ls=[]
    for it in PITEMS:
        if it["store_code"]==lc:
            lmods[it["module"]]+=it["deduction"]
            if it["severity"]=="S": ls.append(it)
    p(f"- 门店：**{disp(lc)}**　主巡检得分 **{lp['adjusted_total_score']}**（{lp['inspection_type']}，{lp['inspection_date']}，{lp['inspector_name']}）")
    p(f"  - 模块扣分构成：" + "，".join(f"{m} {v}" for m,v in sorted(lmods.items(),key=lambda x:x[1])))
    p(f"  - S 项：" + ("；".join(f"{it['sub_item']} “{it['description']}”" for it in ls) or "无"))
    p(f"  - 新店？{'是' if lc not in JUNP else '否'}（6月主巡检基准 {JUNP.get(lc,'—')}，环比 {lp['adjusted_total_score']-JUNP[lc] if lc in JUNP else 'n/a'}；开业 {OPEN_BY_CODE.get(lc,'')}）")
    return {"store":lc,"score":lp["adjusted_total_score"],"type":lp["inspection_type"],"date":lp["inspection_date"],
            "inspector":lp["inspector_name"],"module_breakdown":dict(lmods),
            "S_items":[{"sub_item":it["sub_item"],"desc":it["description"]} for it in ls],
            "is_new":lc not in JUNP,"prior_baseline":JUNP.get(lc),"open_date":OPEN_BY_CODE.get(lc,"")}
for c,pr in [(c,pr) for c,pr in prim_sorted if isinstance(pr["adjusted_total_score"],int) and pr["adjusted_total_score"]<80]:
    s42.append(attrib_store(c,pr))
if not s42:
    s42.append(attrib_store(lowest[0],lowest[1]))
PACK["s4_2"]=s42

# ======================================================================
# §4.3 appeals table (full scope)
# ======================================================================
sec("[§4.3] 申诉明细（全量）")
rows43=[]; s43=[]
for r in sorted(appeals,key=lambda x:(x["appeal_status"],x["store_code"])):
    resmap={"approved":"获批※","denied":"驳回","pending":"审批中"}
    rows43.append([disp(r["store_code"]),r["inspection_type"],resmap.get(r["appeal_status"],r["appeal_status"]),
                   r["inspection_date"],f"{r['original_total_score']}→{r['adjusted_total_score']}",r["inspector_name"]])
    s43.append({"store":r["store_code"],"type":r["inspection_type"],"result":r["appeal_status"],
                "date":r["inspection_date"],"orig":r["original_total_score"],"adj":r["adjusted_total_score"],
                "inspector":r["inspector_name"],"is_primary":r["inspection_id"] in PRIM_IIDS})
p(mdtable(["门店(code)","巡检类型","申诉结果","日期","分数变动(orig→adj)","巡检员"],rows43))
p(f"\n合计 **{len(appeals)} 起（{ap_by.get('approved',0)} 获批 / {ap_by.get('denied',0)} 驳回 / {ap_by.get('pending',0)} 审批中）**")
appealed_findings=sum(1 for it in ITEMS if it["is_appealed_finding"])
p(f"申诉相关 finding 条数：{appealed_findings}")
PACK["s4_3"]={"rows":s43,"total":len(appeals),"approved":ap_by.get("approved",0),"denied":ap_by.get("denied",0),
              "pending":ap_by.get("pending",0),"appealed_findings":appealed_findings}

# ======================================================================
# §4.4 same-store cross-type divergence
# ======================================================================
sec("[§4.4] 同店跨类型背离（≥20分）")
rows44=[]; s44=[]
for c,v,g in divergences:
    lo=min(v,key=v.get); hi=max(v,key=v.get)
    lab={"门店自检_avg":"自检","QA审计":"QA","区经检查":"区经"}
    lo_l,hi_l=lab.get(lo,lo),lab.get(hi,hi)
    if hi=="门店自检_avg":   note=f"自检({v[hi]})显著宽松，{lo_l}({v[lo]})暴露更多问题"
    elif lo=="门店自检_avg": note=f"自检({v[lo]})偏严于{hi_l}({v[hi]})，一线自查更保守"
    else:                    note=f"{lo_l}({v[lo]})较{hi_l}({v[hi]})严格，正式巡检间尺度差异"
    rows44.append([disp(c),f"{lo_l}({v[lo]})",f"{hi_l}({v[hi]})",g,note])
    s44.append({"store":c,"lower":{lo:v[lo]},"higher":{hi:v[hi]},"gap":g})
p(mdtable(["门店(code)","较低类型(分)","较高类型(分)","差值","一句解读"],rows44) if rows44 else "无 ≥20 分背离。")
PACK["s4_4"]=s44

# ======================================================================
# §4.5 module coverage table (primary)
# ======================================================================
sec("[§4.5] 模块覆盖表（主巡检）")
rows45=[]
for m in mods_by_ded:
    a=mod_agg[m]
    if a["problems"]==0: continue
    rows45.append([m,f"{a['stores']}/{NPRIM}",f"{a['coverage']}%",a["deduction"],a["risk"]])
p(mdtable(["模块","影响门店(n/N)","覆盖率","扣分","风险"],rows45))
PACK["s4_5"]=[{"module":m,"stores":mod_agg[m]["stores"],"coverage":mod_agg[m]["coverage"],
              "deduction":mod_agg[m]["deduction"],"risk":mod_agg[m]["risk"]} for m in mods_by_ded if mod_agg[m]["problems"]>0]

# ======================================================================
# §5.1 keyword attribution (all findings)
# ======================================================================
def attribute(text):
    t=(text or "").strip().lower()
    if len(t)<10: return "未知"
    pipe=["pipe","sink","leak","airgap","air gap","drain","plumbing","fixture","light","ceiling","floor","wall","grease","faucet","door","seal","caulk"]
    sup=["license","sign","no smoking","permit","document","expiration date","certificate","supplier"]
    if any(k in t for k in pipe): return "机修+营建"
    if any(k in t for k in sup):  return "供应链+行政"
    return "门店"
attr=Counter(attribute(it["description"]) for it in ITEMS)
attr_tot=sum(attr.values())
empty=sum(1 for it in ITEMS if len((it["description"] or "").strip())<10)
empty_self=sum(1 for it in ITEMS if len((it["description"] or "").strip())<10 and it["inspection_type"]=="门店自检")
sec("[§5.1] 关键词归因（全部发现）")
typ={"门店":"日常清洁、消毒、标签、储存卫生","机修+营建":"sinks and pipes / air gap / 油脂阱 / 灯具 / 门",
     "供应链+行政":"license / certificate / 文件记录 / no smoking sign","未知":"描述缺失或少于 10 字符"}
rows51=[]
for cat in ["门店","机修+营建","供应链+行政","未知"]:
    rows51.append([cat,attr.get(cat,0),f"{attr.get(cat,0)/attr_tot*100:.1f}%",typ[cat]])
p(mdtable(["归因类别","数量","占比","典型问题"],rows51))
p(f"\n空/短描述（<10字符）占比：{empty}/{attr_tot} = {empty/attr_tot*100:.1f}%（其中门店自检 {empty_self} 条）")
PACK["s5_1"]={"attribution":dict(attr),"empty_short":empty,"empty_short_selfcheck":empty_self,
              "total":attr_tot,"empty_pct":round(empty/attr_tot*100,1)}

# ======================================================================
# §7.1 three-type overview
# ======================================================================
sec("[§7.1] 三类巡检总览")
rows71=[]; s71={}
for typ_ in ["门店自检","QA审计","区经检查"]:
    sub=[r for r in SUMMARY if r["inspection_type"]==typ_]
    stores={r["store_code"] for r in sub}
    insps={r["inspector_name"] for r in sub}
    scs=[r["adjusted_total_score"] for r in sub if isinstance(r["adjusted_total_score"],int)]
    S=sum(r["S_count"] for r in sub); M=sum(r["M_count"] for r in sub)
    a,b=tempo_range(typ_)
    rows71.append([typ_,len(sub),f"{len(stores)}/{NPRIM}",len(insps),round(sum(scs)/len(scs),1) if scs else "—",S,M,f"{a}~{b}"])
    s71[typ_]={"count":len(sub),"stores":len(stores),"inspectors":len(insps),
               "avg":round(sum(scs)/len(scs),1) if scs else None,"S":S,"M":M,"first":a,"last":b}
p(mdtable(["巡检类型","次数","覆盖门店(n/N)","巡检员数","平均分","S项","M项","日期区间"],rows71))
PACK["s7_1"]=s71

# ======================================================================
# §7.2 same-store three-type comparison
# ======================================================================
sec("[§7.2] 同店三类对比")
rows72=[]; s72=[]
for c in sorted(PRIMARY.keys()):
    v=STS.get(c,{})
    sc=v.get("门店自检_avg"); qa=v.get("QA审计"); ar=v.get("区经检查")
    diff=round(qa-sc,1) if (isinstance(qa,(int,float)) and isinstance(sc,(int,float))) else ""
    rows72.append([disp(c),sc if sc is not None else "",qa if qa is not None else "",ar if ar is not None else "",diff])
    s72.append({"store":c,"selfcheck_avg":sc,"QA":qa,"area":ar,"QA_minus_self":diff})
p(mdtable(["门店(code)","自检均分","QA审计","区经检查","QA-自检差"],rows72))
PACK["s7_2"]=s72

# ======================================================================
# §7.3 self-check consistency
# ======================================================================
sec("[§7.3] 自检一致性（同员同店≥2次）")
grp=defaultdict(list)
for r in SUMMARY:
    if r["inspection_type"]=="门店自检" and isinstance(r["adjusted_total_score"],int):
        grp[(r["inspector_name"],r["store_code"])].append((r["inspection_date"],r["adjusted_total_score"]))
rows73=[]; s73=[]
for (insp,c),v in grp.items():
    if len(v)<2: continue
    v.sort()
    scs=[x[1] for x in v]; swing=max(scs)-min(scs)
    rows73.append([insp,disp(c),len(v),"→".join(str(x) for x in scs),swing])
    s73.append({"inspector":insp,"store":c,"n":len(v),"scores":scs,"swing":swing})
rows73.sort(key=lambda x:-x[4]); s73.sort(key=lambda x:-x["swing"])
p(mdtable(["巡检员","门店(code)","次数","历次得分","摆动(max-min)"],rows73) if rows73 else "无同员同店≥2次自检。")
if s73: p(f"\n最大摆动：{s73[0]['inspector']} @ {disp(s73[0]['store'])} 摆动 {s73[0]['swing']}")
PACK["s7_3"]=s73

# ======================================================================
# §7.4 inspector strictness
# ======================================================================
sec("[§7.4] 巡检员尺度（≥2次）")
gi=defaultdict(list)
for r in SUMMARY:
    if isinstance(r["adjusted_total_score"],int):
        gi[(r["inspector_name"],r["inspector_position"],r["inspection_type"])].append(r["adjusted_total_score"])
rows74=[]; s74=[]
for (insp,role,typ_),v in gi.items():
    if len(v)<2: continue
    avg=round(sum(v)/len(v),1)
    scale="偏严(<70)" if avg<70 else ("偏宽(>92)" if avg>92 else "正常")
    rows74.append([insp,role,typ_,len(v),avg,scale])
    s74.append({"inspector":insp,"role":role,"type":typ_,"n":len(v),"avg":avg,"scale":scale})
rows74.sort(key=lambda x:x[4]); s74.sort(key=lambda x:x["avg"])
p(mdtable(["巡检员","角色","巡检类型","次数","均分","尺度"],rows74))
PACK["s7_4"]=s74

# ======================================================================
# §7.5 coverage trend Jan-Jul
# ======================================================================
sec("[§7.5] 覆盖趋势（1–7月）")
tmap=defaultdict(dict)
for r in B.TREND_SUM:
    tmap[r["month"]][r["inspection_type"]]={"n":r["inspection_count"],"avg":r["avg_score"]}
rows75=[]; s75=[]
for m in ["2026-01","2026-02","2026-03","2026-04","2026-05","2026-06","2026-07"]:
    d=tmap.get(m,{})
    sc=d.get("门店自检",{}); qa=d.get("QA审计",{}); ar=d.get("区经检查",{})
    tot=sc.get("n",0)+qa.get("n",0)+ar.get("n",0)
    rows75.append([m,sc.get("n",0),qa.get("n",0),ar.get("n",0),tot,
                   sc.get("avg","") or "",qa.get("avg","") or "",ar.get("avg","") or ""])
    s75.append({"month":m,"self":sc.get("n",0),"QA":qa.get("n",0),"area":ar.get("n",0),"total":tot,
                "self_avg":sc.get("avg"),"QA_avg":qa.get("avg"),"area_avg":ar.get("avg")})
p(mdtable(["月份","自检","QA","区经","合计","自检均分","QA均分","区经均分"],rows75))
PACK["s7_5"]=s75

# ======================================================================
# §7.6 three-type findings difference
# ======================================================================
sec("[§7.6] 三类发现差异")
rows76=[]; s76=[]
val={"门店自检":"高频暴露（日常一线自查）","QA审计":"专业定级 / 结构性 S 项（air gap 等）","区经检查":"全覆盖复核"}
for typ_ in ["门店自检","QA审计","区经检查"]:
    sub=[it for it in ITEMS if it["inspection_type"]==typ_]
    S=sum(1 for it in sub if it["severity"]=="S"); M=sum(1 for it in sub if it["severity"]=="M")
    rows76.append([typ_,S,M,val[typ_]])
    s76.append({"type":typ_,"S":S,"M":M,"value":val[typ_]})
p(mdtable(["巡检类型","S项","M项","价值说明"],rows76))
PACK["s7_6"]=s76

# ======================================================================
# extra: cross-month S sub-item comparison (June vs July) for §6/§7.7
# ======================================================================
sec("[§X] 跨月 S 项子项对比（6月 vs 7月，全月口径）")
import csv as _csv
jpath=Path("/app/reports/june2026-qa-inspection/june2026_inspection_items.csv")
jun_S=defaultdict(lambda:{"n":0,"stores":set()})
if jpath.exists():
    for r in _csv.DictReader(open(jpath,encoding="utf-8-sig")):
        if r["severity"]=="S":
            jun_S[r["sub_item"]]["n"]+=1; jun_S[r["sub_item"]]["stores"].add(r["store_code"])
rowsx=[]; sx=[]
allsub=sorted(set(list(by_sub.keys())+list(jun_S.keys())))
for sub in allsub:
    j=jun_S.get(sub,{"n":0,"stores":set()}); k=by_sub.get(sub,{"n":0,"stores":set()})
    rowsx.append([sub,j["n"],len(j["stores"]),k["n"],len(k["stores"]),k["n"]-j["n"]])
    sx.append({"sub_item":sub,"jun_S":j["n"],"jun_stores":len(j["stores"]),
               "jul_S":k["n"],"jul_stores":len(k["stores"]),"delta":k["n"]-j["n"]})
rowsx.sort(key=lambda x:-x[3])
p(mdtable(["子项","6月S项","6月门店","7月S项","7月门店","Δ"],rowsx))
PACK["sX_cross_month_S"]=sx

# repeat-offender stores for the biggest S cluster (June vs July)
pipe_sub = biggest_s[0]
jun_pipe_stores = sorted(jun_S.get(pipe_sub,{"stores":set()})["stores"])
jul_pipe_stores = sorted(by_sub.get(pipe_sub,{"stores":set()})["stores"])
repeat = sorted(set(jun_pipe_stores) & set(jul_pipe_stores))
p(f"\n**{pipe_sub}** 跨月门店：6月 {len(jun_pipe_stores)} 家、7月 {len(jul_pipe_stores)} 家、连续两月复现 **{len(repeat)}** 家 → {', '.join(disp(c) for c in repeat) or '无'}")
p(f"7月新增（6月无）：{', '.join(disp(c) for c in sorted(set(jul_pipe_stores)-set(jun_pipe_stores))) or '无'}")
p(f"7月已消除（6月有）：{', '.join(disp(c) for c in sorted(set(jun_pipe_stores)-set(jul_pipe_stores))) or '无'}")
PACK["sX_repeat_offenders"]={"sub_item":pipe_sub,"jun_stores":jun_pipe_stores,"jul_stores":jul_pipe_stores,
                            "repeat":repeat,"new":sorted(set(jul_pipe_stores)-set(jun_pipe_stores)),
                            "cleared":sorted(set(jun_pipe_stores)-set(jul_pipe_stores))}

# ======================================================================
# WRITE
# ======================================================================
header=f"""# July 2026 QA 门店稽核 — 数据包 (DATA PACK)
- Doc: **LCNA-QA-2026-007**  ·  Source: aws-luckyus-opqualitycontrol-rw / luckyus_opqualitycontrol
- Window: 2026-07-01 .. 2026-07-31 (31 天, closed month)  ·  Built by DBA data-collection agent
- Scope locks: 主巡检 (QA审计>区经检查>门店自检, latest) for §2.2/§2.3/§3.1/§3.2/§3.4/§3.5/§4.1/§4.5/§7 per-type; 全月 for §3.3/§7.x totals
- Module mapping: "Site Security" → 职业安全 (carried from 2026-07-01 resolution); UNMAPPED this month: {B.UNMAPPED or 'NONE'}
"""
(HERE/"july2026_qa_datapack.md").write_text(header+"\n".join(MD), encoding="utf-8")
(HERE/"july2026_qa_datapack.json").write_text(json.dumps(PACK, ensure_ascii=False, indent=1), encoding="utf-8")
print("WROTE july2026_qa_datapack.md  + .json")
print(f"  sections in PACK: {len(PACK)}")
print(f"  Σ主巡检模块扣分 = {sum(mod_agg[m]['deduction'] for m in CANON)}  | Σ store 合计 = {sum(store_tot.values())}")
print(f"  improvers={len(improvers)} decliners={len(decliners)} flat={len(flat)} new={len(NEW_STORES)} divergences_ge20={len(divergences)}")
