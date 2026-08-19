#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
June 2026 QA store-inspection — CORE build.
Reuses the proven May extraction logic (tables/joins/score-formula/appeal-semantics)
with the June window, and emits the PROMPT-specified enhanced CSV schema + a derived.json
(consumed by build_datapack.py) + validation output.

Source: aws-luckyus-opqualitycontrol-rw / luckyus_opqualitycontrol  (READ-ONLY pull already done)
"""
import csv, json, re
from collections import defaultdict, Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
OUT = HERE

MONTH = "2026-06"
PRIOR = "2026-05"

# ---------------------------------------------------------------- mappings
TYPE_MAP = {1084: "门店自检", 1134: "QA审计", 1184: "区经检查"}
TYPE_RAW = {1084: "Store food safety self-check", 1134: "Store food safety audit", 1184: "Area food safety Check"}
TYPE_PRIORITY = {"QA审计": 0, "区经检查": 1, "门店自检": 2}   # 主巡检 priority (lower = higher)
SEV_MAP = {1: "S", 2: "G", 3: "M", 4: "L"}
SEV_POINTS = {"S": -5, "M": -5, "G": -2, "L": -1}

CANON_MODULES = ["清洁卫生","过程控制","设施","证照","职业安全",
                 "虫害防控","温控有效期","员工健康卫生","设备维护","供应链"]
EN2CN = {
    "Cleaning and Sanitation": "清洁卫生",
    "Process Control": "过程控制",
    "Facility": "设施",
    "Document Record": "证照",
    "Workplace Safety": "职业安全",
    "Site Security": "职业安全",          # resolved 2026-07-01 (was 其他 in old builder; forbidden this run)
    "Pests Control": "虫害防控",
    "Temperature Control / Expiration Date Management.": "温控有效期",
    "Employees’ Health and Personal Hygiene": "员工健康卫生",
    "Employees' Health and Personal Hygiene": "员工健康卫生",
    "Maintenance of Equipment": "设备维护",
    "Approved Supplier": "供应链",
}
POSTCODE_ROLE = {
    "LKUS00000076": "Area Operations Manager",
    "LKUS00000078": "Senior QA Manager",
    "LKUS00000223": "Senior QA Manager",
    "LKUS00000082": "Store Manager",
    "LKUS00000083": "Assistant Store Manager",
    "LKUS00000098": "Shift Supervisor / Trainer",
}
ROLE_FALLBACK = {"门店自检": "Store Manager", "QA审计": "Senior QA Manager", "区经检查": "Area Operations Manager"}

UNMAPPED = []

def canon_module(en):
    cn = EN2CN.get(en)
    if cn is None:
        UNMAPPED.append(en)
        return "UNMAPPED:" + str(en)
    return cn

# ---------------------------------------------------------------- load raw
def L(name): return json.loads((RAW / name).read_text(encoding="utf-8"))
H   = L("june_headers.json")
REP = L("june_reports.json")
OPP = L("june_opps.json")
APP = L("june_appeals.json")
STO = L("june_stores.json")
JANMAY_H = L("janmay_headers.json")     # Jan-May headers (all statuses)
APRMAY_R = L("aprmay_reports.json")     # Apr-May reports
Q1D      = L("q1_deductions.json")      # Q1 per-inspection severity counts

REP_BY = {r["shopcheck_data_id"]: r for r in REP}
STORE_BY_DEPT = {s["dept_id"]: s for s in STO}

def scode(dept):  s = STORE_BY_DEPT.get(dept);  return s["shop_no"] if s else f"DEPT-{dept}"
def sname(dept):  s = STORE_BY_DEPT.get(dept);  return s["shop_name"] if s else f"(dept {dept})"
def slevel(dept): s = STORE_BY_DEPT.get(dept);  return (s.get("shop_level") or "") if s else ""

# ---------------------------------------------------------------- opp helpers
def parse_dt_scores(js):
    out = defaultdict(int)
    try:
        for x in json.loads(js or "[]"):
            out[x.get("deductionType")] += x.get("deductionScore", 0)
    except Exception:
        pass
    return out
def parse_dt_counts(js):
    out = defaultdict(int)
    try:
        for x in json.loads(js or "[]"):
            out[x.get("deductionType")] += x.get("count", 0)
    except Exception:
        pass
    return out

# opps grouped by inspection
OPP_BY_IID = defaultdict(list)
for o in OPP:
    OPP_BY_IID[o["iid"]].append(o)
ITEM_COUNT = {iid: len(v) for iid, v in OPP_BY_IID.items()}

# ---------------------------------------------------------------- appeal decision parsing
def appeal_decision(detail_json):
    """Return 'approved' | 'denied' | 'pending' from one appeal_detail JSON string."""
    if not detail_json or str(detail_json).strip() == "":
        return None
    try:
        d = json.loads(detail_json)
    except Exception:
        return None
    ar = d.get("approveResult", None)
    if ar is None:
        return "pending"
    ap = ar.get("approve")
    if ap == 1: return "approved"
    if ap == 0: return "denied"
    return "pending"

# per opp_id decision (from appeals detail); per inspection rollup
OPP_DECISION = {}
IID_DECISIONS = defaultdict(list)
for a in APP:
    decs = [appeal_decision(a.get("first_appeal_detail")), appeal_decision(a.get("second_appeal_detail"))]
    decs = [x for x in decs if x]
    # cross-check with opp_status: status==0 => approved
    if a.get("opp_status") == 0 and "approved" not in decs:
        decs.append("approved")
    d = "approved" if "approved" in decs else ("pending" if "pending" in decs else ("denied" if "denied" in decs else None))
    OPP_DECISION[a["opp_id"]] = d
    if d: IID_DECISIONS[a["iid"]].append(d)

def inspection_appeal_status(iid):
    decs = IID_DECISIONS.get(iid, [])
    if not decs: return "none"
    if "approved" in decs: return "approved"
    if "pending"  in decs: return "pending"
    if "denied"   in decs: return "denied"
    return "none"

# ---------------------------------------------------------------- misfiled-duplicate filter
def compute_misfiled():
    grp = defaultdict(list)
    for h in H:
        if h["large_category_id"] != 1084:   # rule is about self-checks
            continue
        grp[(h["checker_id"], h["dept_id"], h["check_date"])].append(h)
    drop = {}
    for key, arr in grp.items():
        if len(arr) < 2: continue
        if not any(ITEM_COUNT.get(x["id"], 0) > 0 for x in arr): continue
        for x in arr:
            rep = REP_BY.get(x["id"])
            sc = rep["score"] if rep else None
            if sc == 100 and ITEM_COUNT.get(x["id"], 0) == 0:
                drop[x["id"]] = {"inspector": x["checker_name"], "dept": x["dept_id"],
                                 "store": scode(x["dept_id"]), "date": x["check_date"],
                                 "siblings": [s["id"] for s in arr if s["id"] != x["id"]]}
    return drop
MISFILED = compute_misfiled()

# ---------------------------------------------------------------- per-inspection summary rows
def build_summary():
    rows = []
    for h in H:
        iid = h["id"]
        if iid in MISFILED: continue
        typ = TYPE_MAP[h["large_category_id"]]
        rep = REP_BY.get(iid)
        opps = OPP_BY_IID.get(iid, [])
        # severity counts unchanged by appeals (count opps directly)
        sc = Counter(SEV_MAP[o["deduction_type"]] for o in opps)
        S, M, G, Lc = sc.get("S",0), sc.get("M",0), sc.get("G",0), sc.get("L",0)
        adj_score = rep["score"] if rep else ""
        adj_ded   = sum(parse_dt_scores(rep["opportunity_desc"]).values()) if rep else ""
        orig_ded  = sum((o.get("score_config") or 0) for o in opps)
        has_orig_S = any(o["deduction_type"] == 1 for o in opps)
        is_app = 1 if any(o["has_first_appeal"] or o["has_second_appeal"] for o in opps) else 0
        astatus = inspection_appeal_status(iid) if is_app else "none"
        if is_app and rep is not None:
            orig_score = 100 + orig_ded + (-20 if has_orig_S else 0)
        else:
            orig_score = adj_score
            orig_ded   = adj_ded
        post = rep["checker_post_code"] if rep else None
        position = POSTCODE_ROLE.get(post) or ROLE_FALLBACK.get(typ, "Unknown")
        rows.append({
            "inspection_id": iid, "store_code": scode(h["dept_id"]), "store_name": sname(h["dept_id"]),
            "store_level": slevel(h["dept_id"]), "inspection_date": h["check_date"],
            "inspection_type": typ, "inspector_name": h["checker_name"], "inspector_position": position,
            "status": h["status"], "total_score": adj_score, "total_deduction": adj_ded,
            "original_total_score": orig_score, "adjusted_total_score": adj_score,
            "original_total_deduction": orig_ded, "adjusted_total_deduction": adj_ded,
            "is_appealed": is_app, "appeal_status": astatus,
            "S_count": S, "M_count": M, "G_count": G, "L_count": Lc,
            "dept_id": h["dept_id"], "large_category_id": h["large_category_id"],
        })
    rows.sort(key=lambda r: (r["store_code"], r["inspection_date"], r["inspection_id"]))
    return rows
SUMMARY = build_summary()
SUMMARY_BY_IID = {r["inspection_id"]: r for r in SUMMARY}

# ---------------------------------------------------------------- item rows
def build_items():
    rows = []
    order = {"S":0,"M":1,"G":2,"L":3}
    for o in OPP:
        iid = o["iid"]
        if iid in MISFILED: continue
        h = next((x for x in H if x["id"] == iid), None)
        if not h: continue
        typ = TYPE_MAP[h["large_category_id"]]
        rep = REP_BY.get(iid)
        post = rep["checker_post_code"] if rep else None
        position = POSTCODE_ROLE.get(post) or ROLE_FALLBACK.get(typ, "Unknown")
        sev = SEV_MAP[o["deduction_type"]]
        desc = (o.get("remark") or "").strip()
        appealed = 1 if (o.get("has_first_appeal") or o.get("has_second_appeal")) else 0
        rows.append({
            "inspection_id": iid, "store_code": scode(h["dept_id"]), "store_name": sname(h["dept_id"]),
            "inspection_date": h["check_date"], "inspection_type": typ,
            "inspector_name": h["checker_name"], "inspector_position": position,
            "module": canon_module(o["module_name"]), "sub_item": o.get("leaf_cat_name") or "",
            "severity": sev, "deduction": o.get("score_config"), "description": desc,
            "is_appealed_finding": appealed,
            "_module_en": o["module_name"], "_opp_id": o["opp_id"], "_opp_status": o.get("opp_status"),
        })
    rows.sort(key=lambda r: (r["store_code"], r["inspection_date"], order[r["severity"]], r["deduction"] or 0))
    return rows
ITEMS = build_items()

# ---------------------------------------------------------------- 主巡检 derivation
ACTIVE_STORES = {}     # store_code -> store row (status=1, non-test, SL02, opened)
for s in STO:
    if s["status"] != 1: continue
    if (s.get("shop_level") == "SL12") or s["shop_no"].startswith("US999") or s["shop_no"] in ("US00000",):
        continue
    if not s.get("set_up_time"): continue
    ACTIVE_STORES[s["shop_no"]] = s

# stores inspected in June (any status=1 non-misfiled)
INSPECTED_DEPTS = {h["dept_id"] for h in H if h["id"] not in MISFILED}
INSPECTED_CODES = {scode(d) for d in INSPECTED_DEPTS}

# operational (inspectable) active stores = active with open_date <= last inspection activity
# stores opened 2026-06-30 with NO June inspection -> excluded from 主巡检, listed separately
OPENED_NOT_INSPECTED = []
OPERATIONAL = {}
for code, s in ACTIVE_STORES.items():
    if code in INSPECTED_CODES:
        OPERATIONAL[code] = s
    else:
        OPENED_NOT_INSPECTED.append({"store_code": code, "store_name": s["shop_name"],
                                     "open_date": (s.get("set_up_time") or "")[:10]})

def primary_inspection_for(code):
    cand = [r for r in SUMMARY if r["store_code"] == code]
    if not cand: return None
    cand.sort(key=lambda r: (TYPE_PRIORITY[r["inspection_type"]], _neg_date(r["inspection_date"]), -r["inspection_id"]))
    return cand[0]
def _neg_date(d):  # later date first -> sort ascending on negated ordinal
    y,m,dd = d.split("-");  return -(int(y)*10000 + int(m)*100 + int(dd))

PRIMARY = {}
for code in OPERATIONAL:
    p = primary_inspection_for(code)
    if p: PRIMARY[code] = p
PRIMARY_IIDS = {p["inspection_id"] for p in PRIMARY.values()}

# ---------------------------------------------------------------- May baseline (from May CSV, actual)
def load_may_primary():
    p = Path("/app/reports/may2026-qa-inspection/may2026_inspection_summary.csv")
    if not p.exists(): return {}
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    by_store = defaultdict(list)
    for r in rows:
        by_store[r["store_code"]].append(r)
    prio = {"QA审计":0,"区经检查":1,"门店自检":2}
    out = {}
    for code, rs in by_store.items():
        rs.sort(key=lambda r: (prio.get(r["inspection_type"],9), _neg_date(r["inspection_date"])))
        top = rs[0]
        out[code] = int(top["adjusted_total_score"]) if top["adjusted_total_score"] not in ("","None") else None
    return out
MAY_PRIMARY = load_may_primary()

# ---------------------------------------------------------------- CSV writers
def w_summary():
    fields = ["inspection_id","store_code","store_name","store_level","inspection_date","inspection_type",
              "inspector_name","inspector_position","status","total_score","total_deduction",
              "original_total_score","adjusted_total_score","original_total_deduction","adjusted_total_deduction",
              "is_appealed","appeal_status","S_count","M_count","G_count","L_count"]
    with (OUT/"june2026_inspection_summary.csv").open("w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader()
        for r in SUMMARY: w.writerow(r)
    return len(SUMMARY)

def w_items():
    fields = ["inspection_id","store_code","store_name","inspection_date","inspection_type",
              "inspector_name","inspector_position","module","sub_item","severity","deduction",
              "description","is_appealed_finding"]
    with (OUT/"june2026_inspection_items.csv").open("w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", quoting=csv.QUOTE_ALL); w.writeheader()
        for r in ITEMS: w.writerow(r)
    return len(ITEMS)

def parse_city(addr):
    segs = [x.strip() for x in (addr or "").split(",")]
    for i,s in enumerate(segs):
        if re.match(r'^(NY|NJ)\b', s) and i>0:
            return segs[i-1]
    return ""

def w_store_master():
    fields = ["store_code","store_name","address","city","area","store_level","open_date","status"]
    smap = {1:"active",2:"inactive",5:"closed"}
    rows = []
    for s in STO:
        st = smap.get(s["status"], f"status{s['status']}")
        if (s.get("shop_level")=="SL12") or s["shop_no"].startswith("US999") or s["shop_no"]=="US00000":
            st += " (test/internal)"
        rows.append({"store_code":s["shop_no"],"store_name":s["shop_name"],"address":s.get("address") or "",
                     "city":parse_city(s.get("address")),"area":s.get("operation_area") or "",
                     "store_level":s.get("shop_level") or "","open_date":(s.get("set_up_time") or "")[:10],
                     "status":st})
    rows.sort(key=lambda r: r["store_code"])
    with (OUT/"june2026_store_master.csv").open("w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows: w.writerow(r)
    return len(rows)

# ---------------------------------------------------------------- trend (Jan-Jun)
BUCKET = {"2026-01":"jan","2026-02":"feb","2026-03":"mar","2026-04":"apr","2026-05":"may","2026-06":"jun"}
def month_of(d): return d[:7]

# unify all headers Jan-Jun with status=1, TYPE_MAP, misfiled-excluded (May's EXCLUDE + June's MISFILED)
# reuse May's misfiled: recompute from janmay via same rule would need may opps; instead reuse May's
# published trend for Jan-May exactly, compute June fresh, then append.
def build_trend_summary():
    # Jan-May: reuse May's published per (month,type) numbers
    may_csv = Path("/app/reports/may2026-qa-inspection/jan_to_may2026_trend_summary.csv")
    rows = list(csv.DictReader(open(may_csv, encoding="utf-8-sig")))
    for r in rows:
        for k in ("inspection_count","stores_covered","s_total","m_total","g_total","l_total","total_deduction_items"):
            r[k] = int(r[k])
        r["avg_score"] = (float(r["avg_score"]) if r["avg_score"] not in ("","None") else "")
    # June per type
    for typ in ["门店自检","QA审计","区经检查"]:
        subset = [r for r in SUMMARY if r["inspection_type"]==typ]
        stores = {r["store_code"] for r in subset}
        scores = [r["adjusted_total_score"] for r in subset if isinstance(r["adjusted_total_score"], int)]
        S=sum(r["S_count"] for r in subset); M=sum(r["M_count"] for r in subset)
        G=sum(r["G_count"] for r in subset); Lc=sum(r["L_count"] for r in subset)
        rows.append({"month":"2026-06","inspection_type":typ,"inspection_count":len(subset),
                     "stores_covered":len(stores),
                     "avg_score":round(sum(scores)/len(scores),1) if scores else "",
                     "s_total":S,"m_total":M,"g_total":G,"l_total":Lc,
                     "total_deduction_items":S+M+G+Lc})
    fields = ["month","inspection_type","inspection_count","stores_covered","avg_score",
              "s_total","m_total","g_total","l_total","total_deduction_items"]
    with (OUT/"jan_to_june2026_trend_summary.csv").open("w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows: w.writerow(r)
    return rows

def build_inspector_trend():
    """Long format: inspector_name, inspector_position, inspection_type, month, n_inspections, avg_score.
    Jan-May from May bundle raw; June fresh."""
    # position lookup from June reports + May inference
    def pos_for(name, typ, post=None):
        return POSTCODE_ROLE.get(post) or ROLE_FALLBACK.get(typ, "Unknown")
    # gather (name,type,month) -> [scores], count
    agg = defaultdict(lambda: {"n":0, "scores":[]})
    postcode_by_name = {}
    # June
    for r in SUMMARY:
        k = (r["inspector_name"], r["inspection_type"], "2026-06")
        agg[k]["n"] += 1
        if isinstance(r["adjusted_total_score"], int): agg[k]["scores"].append(r["adjusted_total_score"])
        postcode_by_name.setdefault(r["inspector_name"], r["inspector_position"])
    # Jan-May from janmay_headers + aprmay_reports + q1 (counts only, scores from reports where present)
    rep_janmay = {r["shopcheck_data_id"]: r for r in APRMAY_R}
    # May misfiled iids to exclude (recompute minimal: score100 & 0 items duplicates) — approximate via reports
    for h in JANMAY_H:
        if h.get("status") != 1: continue
        lc = h.get("large_category_id")
        if lc not in TYPE_MAP: continue
        m = month_of(h["check_date"])
        if m not in BUCKET or m == "2026-06": continue
        typ = TYPE_MAP[lc]
        k = (h["checker_name"], typ, m)
        agg[k]["n"] += 1
        rr = rep_janmay.get(h["id"])
        if rr and rr.get("score") is not None:
            agg[k]["scores"].append(rr["score"])
    rows = []
    for (name, typ, m), v in agg.items():
        rows.append({"inspector_name":name,
                     "inspector_position":postcode_by_name.get(name, ROLE_FALLBACK.get(typ,"Unknown")),
                     "inspection_type":typ,"month":m,"n_inspections":v["n"],
                     "avg_score":round(sum(v["scores"])/len(v["scores"]),1) if v["scores"] else ""})
    rows.sort(key=lambda r:(r["inspector_name"], r["month"], r["inspection_type"]))
    fields = ["inspector_name","inspector_position","inspection_type","month","n_inspections","avg_score"]
    with (OUT/"june2026_inspector_trend.csv").open("w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows: w.writerow(r)
    return rows

# ---------------------------------------------------------------- run
n_sum = w_summary(); n_itm = w_items(); n_sto = w_store_master()
TREND_SUM = build_trend_summary(); INSP_TREND = build_inspector_trend()

# derived aggregates dumped for datapack + validation
derived = {
    "month": MONTH,
    "misfiled": MISFILED,
    "unmapped": sorted(set(UNMAPPED)),
    "counts_full_month": {
        "门店自检": sum(1 for r in SUMMARY if r["inspection_type"]=="门店自检"),
        "QA审计":   sum(1 for r in SUMMARY if r["inspection_type"]=="QA审计"),
        "区经检查": sum(1 for r in SUMMARY if r["inspection_type"]=="区经检查"),
        "total": len(SUMMARY),
    },
    "severity_full_month": dict(Counter(i["severity"] for i in ITEMS)),
    "primary_iids": sorted(PRIMARY_IIDS),
    "primary_by_store": {c:{"iid":p["inspection_id"],"type":p["inspection_type"],
                            "score":p["adjusted_total_score"],"orig":p["original_total_score"],
                            "date":p["inspection_date"],"inspector":p["inspector_name"],
                            "S":p["S_count"],"M":p["M_count"],"G":p["G_count"],"L":p["L_count"],
                            "appeal_status":p["appeal_status"],"is_appealed":p["is_appealed"]}
                         for c,p in PRIMARY.items()},
    "operational_stores": sorted(OPERATIONAL.keys()),
    "opened_not_inspected": OPENED_NOT_INSPECTED,
    "may_primary": MAY_PRIMARY,
}
(OUT/"derived.json").write_text(json.dumps(derived, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------------------------------------------------------------- headline print
if __name__ != "__main__":
    import sys as _sys
    _real_print = print
    def print(*a, **k):  # silence headline on import
        pass
print("="*70)
print("JUNE 2026 QA — CORE BUILD")
print("="*70)
print(f"CSV rows: summary={n_sum} items={n_itm} store_master={n_sto} "
      f"trend_summary={len(TREND_SUM)} inspector_trend={len(INSP_TREND)}")
print(f"misfiled dropped: {list(MISFILED)} ({len(MISFILED)})")
print(f"UNMAPPED modules: {sorted(set(UNMAPPED)) or 'NONE'}")
c = derived["counts_full_month"]
print(f"全月 counts: 自检={c['门店自检']} QA={c['QA审计']} 区经={c['区经检查']} total={c['total']}")
print(f"全月 severity: {derived['severity_full_month']}  total={sum(derived['severity_full_month'].values())}")
prim_scores = [p['adjusted_total_score'] for p in PRIMARY.values() if isinstance(p['adjusted_total_score'],int)]
print(f"主巡检 stores={len(PRIMARY)}  composition={Counter(p['inspection_type'] for p in PRIMARY.values())}")
print(f"主巡检 avg adjusted = {round(sum(prim_scores)/len(prim_scores),1)}")
prim_sev = Counter()
for c_,p in PRIMARY.items():
    prim_sev['S']+=p['S_count']; prim_sev['M']+=p['M_count']; prim_sev['G']+=p['G_count']; prim_sev['L']+=p['L_count']
print(f"主巡检 severity: {dict(prim_sev)}  total={sum(prim_sev.values())}")
print(f"主巡检 <80: {sorted([(p['adjusted_total_score'],c_) for c_,p in PRIMARY.items() if isinstance(p['adjusted_total_score'],int) and p['adjusted_total_score']<80])}")
appeals = [r for r in SUMMARY if r['is_appealed']]
print(f"appeals: {len(appeals)}  " + str(Counter(r['appeal_status'] for r in appeals)))
print(f"operational stores={len(OPERATIONAL)}  opened-not-inspected={OPENED_NOT_INSPECTED}")

# score-formula sanity
mism=0; chk=0
for r in SUMMARY:
    rep = REP_BY.get(r["inspection_id"])
    if not rep: continue
    dt = parse_dt_scores(rep["opportunity_desc"])
    spen = -20 if dt.get(1,0) < 0 else 0
    exp = 100 + sum(dt.values()) + spen
    chk += 1
    if exp != rep["score"]:
        mism += 1; print(f"  MISMATCH iid={r['inspection_id']} exp={exp} act={rep['score']}")
print(f"score-formula sanity: checked={chk} mismatches={mism} {'PASS' if mism==0 else 'FAIL'}")
