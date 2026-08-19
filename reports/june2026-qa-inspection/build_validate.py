#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
June 2026 QA — PHASE 6 validation + schema notes.
Validates the WRITTEN artifacts (CSVs + datapack.json + derived.json) and emits:
  june2026_validation_output.txt
  june2026_schema_notes.txt
Then prints the console manifest.
"""
import csv, json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
def rd_csv(n): return list(csv.DictReader(open(HERE/n, encoding="utf-8-sig")))
def rd_json(n): return json.loads((HERE/n).read_text(encoding="utf-8"))

SUM = rd_csv("june2026_inspection_summary.csv")
ITM = rd_csv("june2026_inspection_items.csv")
STM = rd_csv("june2026_store_master.csv")
TRD = rd_csv("jan_to_june2026_trend_summary.csv")
INS = rd_csv("june2026_inspector_trend.csv")
PACK = rd_json("june2026_qa_datapack.json")
DERIVED = rd_json("derived.json")

CANON = ["清洁卫生","过程控制","设施","证照","职业安全","虫害防控","温控有效期","员工健康卫生","设备维护","供应链"]
PRIM_IIDS = set(DERIVED["primary_iids"])
for r in SUM:
    for k in ("inspection_id","S_count","M_count","G_count","L_count","is_appealed"):
        r[k]=int(r[k])
for r in ITM:
    r["inspection_id"]=int(r["inspection_id"]); r["deduction"]=int(r["deduction"])
PITEMS=[r for r in ITM if r["inspection_id"] in PRIM_IIDS]

lines=[]
def e(s=""): lines.append(s); print(s)
ok=True
def check(name, cond, detail=""):
    global ok
    status="PASS" if cond else "FAIL"
    if not cond: ok=False
    e(f"  [{status}] {name}{('  '+detail) if detail else ''}")

e("="*74)
e("JUNE 2026 QA INSPECTION — VALIDATION OUTPUT  (LCNA-QA-2026-006)")
e("Source: aws-luckyus-opqualitycontrol-rw / luckyus_opqualitycontrol")
e("Window: 2026-06-01 .. 2026-06-30 (30d, closed month)   Built: 2026-07-01")
e("="*74)

e("\n[1] ROW COUNTS")
e(f"  summary={len(SUM)}  items={len(ITM)}  store_master={len(STM)}  "
  f"trend_summary={len(TRD)}  inspector_trend={len(INS)}")
check("summary rows == 85", len(SUM)==85, f"got {len(SUM)}")
check("items rows == 498", len(ITM)==498, f"got {len(ITM)}")

e("\n[2] STATUS / DRAFT EXCLUSION")
nonsub=sum(1 for r in SUM if int(r["status"])!=1)
check("summary status!=1 == 0", nonsub==0, f"got {nonsub}")

e("\n[3] MISFILED-DUPLICATE DROP")
mis=DERIVED["misfiled"]
e(f"  dropped {len(mis)}: " + ", ".join(f"iid={k} ({v['inspector']} @ {v['store']} {v['date']}, siblings {v['siblings']})" for k,v in mis.items()))
check("misfiled dropped == 1 (iid 2175)", list(mis.keys())==["2175"] or list(map(str,mis.keys()))==["2175"])

e("\n[4] 主巡检 DEDUCTION RECONCILIATION  (§1.2 nominal == §2.2 == §4.1)")
prim_ded_items = sum(it["deduction"] for it in PITEMS)
mod_ded = sum(m["deduction"] for m in PACK["module_agg_primary"].values())
s41_total = PACK["s4_1"]["grand_total"]
s22_from_pack = sum(v["deduction"] for v in PACK["module_agg_primary"].values())
s12_total = sum(r["deduction"] for r in PACK["s1_2"])
e(f"  Σ主巡检 item deductions = {prim_ded_items}")
e(f"  Σ§2.2 module deductions = {mod_ded}")
e(f"  Σ§4.1 store 合计        = {s41_total}")
e(f"  Σ§1.2 扣分 column       = {s12_total}")
check("Σ主巡检 items == Σ§2.2 == Σ§4.1 == Σ§1.2", prim_ded_items==mod_ded==s41_total==s12_total,
      f"{prim_ded_items}/{mod_ded}/{s41_total}/{s12_total}")

e("\n[5] SEVERITY RECONCILIATION (主巡检)")
pm=Counter(it["severity"] for it in PITEMS)
s31={k:v["count"] for k,v in PACK["s3_1"].items()}
s22_sev=Counter()
for m in PACK["module_agg_primary"].values():
    for k in ("S","M","G","L"): s22_sev[k]+=m[k]
e(f"  主巡检 items S/M/G/L = {pm['S']}/{pm['M']}/{pm['G']}/{pm['L']} = {sum(pm.values())}")
e(f"  §3.1 counts          = {s31.get('S')}/{s31.get('M')}/{s31.get('G')}/{s31.get('L')}")
e(f"  Σ§2.2 sev columns    = {s22_sev['S']}/{s22_sev['M']}/{s22_sev['G']}/{s22_sev['L']}")
check("主巡检 items sev == §3.1 == Σ§2.2 sev",
      dict(pm)==s31 and dict(pm)==dict(s22_sev))
# summary S/M/G/L columns for primary rows also match
sum_prim_sev=Counter()
for r in SUM:
    if r["inspection_id"] in PRIM_IIDS:
        sum_prim_sev['S']+=r['S_count']; sum_prim_sev['M']+=r['M_count']; sum_prim_sev['G']+=r['G_count']; sum_prim_sev['L']+=r['L_count']
check("summary S/M/G/L (primary rows) == items", dict(sum_prim_sev)==dict(pm),
      f"summary={dict(sum_prim_sev)} items={dict(pm)}")

e("\n[6] FULL-MONTH SEVERITY (全月)")
fm=Counter(it["severity"] for it in ITM)
e(f"  全月 items S/M/G/L = {fm['S']}/{fm['M']}/{fm['G']}/{fm['L']} = {sum(fm.values())}")
fm_S_33 = PACK["s3_3"]["full_month_sev"]["S"]
check("全月 S total == §3.3 S total", fm["S"]==fm_S_33, f"{fm['S']} vs {fm_S_33}")
check("全月 items total == §3.3 total", sum(fm.values())==PACK["s3_3"]["full_month_total"])
# summary S/M/G/L columns full-month
sum_sev=Counter()
for r in SUM:
    sum_sev['S']+=r['S_count']; sum_sev['M']+=r['M_count']; sum_sev['G']+=r['G_count']; sum_sev['L']+=r['L_count']
check("Σ summary S/M/G/L == 全月 items", dict(sum_sev)==dict(fm), f"summary={dict(sum_sev)} items={dict(fm)}")

e("\n[7] APPEALS RECONCILE (§4.3 vs summary)")
sum_app=[r for r in SUM if r["is_appealed"]==1]
ap_by=Counter(r["appeal_status"] for r in sum_app)
e(f"  summary is_appealed=1 : {len(sum_app)}   {dict(ap_by)}")
e(f"  §4.3 total            : {PACK['s4_3']['total']}  (approved {PACK['s4_3']['approved']} / denied {PACK['s4_3']['denied']} / pending {PACK['s4_3']['pending']})")
check("appeals count summary == §4.3", len(sum_app)==PACK["s4_3"]["total"])
check("approved+denied+pending == total",
      PACK["s4_3"]["approved"]+PACK["s4_3"]["denied"]+PACK["s4_3"]["pending"]==PACK["s4_3"]["total"])
# appealed findings in items
appf=sum(1 for r in ITM if int(r["is_appealed_finding"])==1)
e(f"  appealed FINDINGS in items (is_appealed_finding=1) = {appf}")

e("\n[8] UNMAPPED CHECKS (should all be none)")
bad_mod=sorted({r["module"] for r in ITM if r["module"] not in CANON})
bad_typ=sorted({r["inspection_type"] for r in SUM if r["inspection_type"] not in ("门店自检","QA审计","区经检查")})
bad_sev=sorted({r["severity"] for r in ITM if r["severity"] not in ("S","M","G","L")})
check("no UNMAPPED modules", not bad_mod, str(bad_mod))
check("no unmapped inspection_type", not bad_typ, str(bad_typ))
check("no unmapped severity", not bad_sev, str(bad_sev))
e(f"  (resolution applied: raw 'Site Security' -> 职业安全, user-confirmed 2026-07-01)")

e("\n[9] COVERAGE / 主巡检")
e(f"  主巡检 stores = {len(PACK['s1_2'])} ; composition = " +
  str(dict(Counter(r['type'] for r in PACK['s1_2']))))
prim_scores=[r["score"] for r in PACK["s1_2"] if isinstance(r["score"],int)]
e(f"  主巡检 avg (adjusted) = {round(sum(prim_scores)/len(prim_scores),1)}  (May 85.8)")
e(f"  opened-not-inspected (6/30): " + ", ".join(f"{o['store_code']} {o['store_name']}" for o in DERIVED["opened_not_inspected"]))
check("主巡检 coverage == 18/18", len(PACK['s1_2'])==18)

e("\n[10] SCORE-FORMULA SANITY  (100 + adj_ded + S_penalty == report.score)")
# recompute from raw reports
REP={r["shopcheck_data_id"]:r for r in rd_json("raw/june_reports.json")}
mm=0; ck=0
for r in SUM:
    rep=REP.get(r["inspection_id"])
    if not rep: continue
    dt=defaultdict(int)
    for x in json.loads(rep["opportunity_desc"] or "[]"): dt[x["deductionType"]]+=x["deductionScore"]
    spen=-20 if dt.get(1,0)<0 else 0
    exp=100+sum(dt.values())+spen; ck+=1
    if exp!=rep["score"]: mm+=1; e(f"    MISMATCH iid={r['inspection_id']} exp={exp} act={rep['score']}")
check(f"score-formula (checked {ck})", mm==0, f"mismatches={mm}")

e("\n" + "="*74)
e(f"OVERALL: {'ALL CHECKS PASS' if ok else '*** SOME CHECKS FAILED ***'}")
e("="*74)
(HERE/"june2026_validation_output.txt").write_text("\n".join(lines), encoding="utf-8")

# ---------------------------------------------------------------- schema notes
SCHEMA = """June 2026 Inspection Export — Schema Notes (built 2026-07-01, closed month 06-01..06-30)
Doc: LCNA-QA-2026-006

SOURCE
======
- DB server (mcp-db-gateway SSE): aws-luckyus-opqualitycontrol-rw
- Schema (MySQL):                  luckyus_opqualitycontrol
- Store master:                    aws-luckyus-opshop-rw / luckyus_opshop.t_shop_info
- Pull method: minimal MCP-over-SSE client (mcp_sse_pull.py + pull_all.py) -> raw/*.json (READ-ONLY, SELECT only)

TABLES / JOIN GRAPH
===================
  t_shopcheck_data       inspection header (id, dept_id, large_category_id, check_date, status, deleted, checker_*)
  t_shopcheck_report     per-inspection score summary (shopcheck_data_id, score, opportunity_desc JSON, checker_post_code, shop_level)
  t_shopcheck_opportunity finding rows (shopcheck_data_id, check_item_id, remark, status, first/second_appeal_detail, deleted)
  t_shopcheck_item_config clause config (id == opportunity.check_item_id; deduction_type, score_config, category_config_id)
  t_shopcheck_category_config category tree (leaf.id == item_config.category_config_id; leaf.parent_id == module.id; .name)
  join: opp.check_item_id -> item_config.id -> category_config(leaf) -> parent_id -> category_config(module)
        opp.shopcheck_data_id -> data.id -> report.shopcheck_data_id ; data.dept_id -> t_shop_info.dept_id

INSPECTION-TYPE MAPPING (large_category_id -> canonical)
=======================================================
  1084 'Store food safety self-check' -> 门店自检
  1134 'Store food safety audit'      -> QA审计
  1184 'Area food safety Check'        -> 区经检查
  (June: only these three; tenant=LKUS; no IQA2Test types present -> no unmapped type)

SEVERITY MAPPING (deduction_type -> S/M/G/L) and DEDUCTION CONVENTION
====================================================================
  1 -> S (score_config -5) | 2 -> G (-2) | 3 -> M (-5) | 4 -> L (-1)
  (verified against June item_config: 100% of rows match the convention)

10-MODULE CANONICAL TAXONOMY (raw English module -> canonical Chinese)
=====================================================================
  Cleaning and Sanitation                      -> 清洁卫生
  Process Control                              -> 过程控制
  Facility                                     -> 设施
  Document Record                              -> 证照
  Workplace Safety                             -> 职业安全
  Site Security                                -> 职业安全   *** UNMAPPED RESOLUTION, user-confirmed 2026-07-01 ***
  Pests Control                                -> 虫害防控
  Temperature Control / Expiration Date Mgmt.  -> 温控有效期
  Employees' Health and Personal Hygiene       -> 员工健康卫生  (both U+2019 and ASCII apostrophe)
  Maintenance of Equipment                     -> 设备维护
  Approved Supplier                            -> 供应链        (not present in June)
  No 11th module / no 其他 bucket. Any future unmapped label must STOP for resolution.

SUBMITTED VIEW / CLEANING
=========================
  status=1 (submitted) AND deleted=0 only. Drafts and soft-deleted rows excluded.
  Misfiled-duplicate rule: same inspector + same store + same day self-check with score=100 AND 0 items,
    where a sibling (same inspector/store/day) has >0 items -> drop the blank one.
    June: dropped 1 -> iid 2175 (Tunisia Hayward @ US00004 37th & Broadway 2026-06-12; sibling 2177).
  Result: 86 submitted - 1 misfiled = 85 analytical inspections (self 51 / QA 16 / area 18).

APPEAL SEMANTICS (dual-track)
=============================
  Per finding: appeal filed if first_appeal_detail or second_appeal_detail non-empty.
  Decision lives in appeal_detail JSON 'approveResult':
    approveResult.approve=1  -> approved (opportunity.status flips 1->0; that item's deductionScore zeroed in report JSON)
    approveResult=null       -> pending
    approveResult.approve=0  -> denied
  Inspection-level appeal_status = approved > pending > denied > none.
  Finding COUNTS (S/M/G/L) are RETAINED regardless of appeal outcome (severity kept even when deduction reversed).
  Store 主巡检 SCORE uses adjusted (report.score, reflects approved appeals); ※ marks appeal-adjusted stores.
  June: 10 appealed inspections -> 7 approved / 0 denied / 3 pending ; 13 appealed findings (all QA审计, air-gap/BD themed).

SCORE FORMULA (validated vs report.score, 0 mismatches / 85 rows)
================================================================
  adjusted_total_deduction = Σ deductionScore over opportunity_desc types
  adjusted_total_score     = report.score
  S_penalty(x)             = -20 if any type=1 deductionScore < 0
  original_total_deduction = Σ opportunity.score_config over the inspection's findings (pre-appeal, all statuses)
  original_total_score     = 100 + original_total_deduction + (-20 if any original S)
  total_score/total_deduction (summary CSV) = adjusted (effective/current).

主巡检 (PRIMARY INSPECTION) DERIVATION
=====================================
  Per active operational store: priority QA审计 > 区经检查 > 门店自检, then LATEST date.
  June: 18 operational stores -> 16 QA审计 + 2 区经检查 (US00018, US00022 had no QA).
  Excluded (opened 2026-06-30, no June inspection): US00009 48th & 3rd, US00013 Grand Central Terminal.

CSV OUTPUTS (enhanced June schema; column names authoritative for the web compile step)
=======================================================================================
  june2026_inspection_summary.csv : inspection_id, store_code, store_name, store_level, inspection_date,
      inspection_type, inspector_name, inspector_position, status, total_score, total_deduction,
      original_total_score, adjusted_total_score, original_total_deduction, adjusted_total_deduction,
      is_appealed, appeal_status, S_count, M_count, G_count, L_count
  june2026_inspection_items.csv   : inspection_id, store_code, store_name, inspection_date, inspection_type,
      inspector_name, inspector_position, module, sub_item, severity, deduction, description, is_appealed_finding
  june2026_store_master.csv       : store_code, store_name, address, city, area, store_level, open_date, status
  june2026_inspector_trend.csv    : inspector_name, inspector_position, inspection_type, month, n_inspections, avg_score  (Jan..Jun, long)
  jan_to_june2026_trend_summary.csv: month, inspection_type, inspection_count, stores_covered, avg_score,
      s_total, m_total, g_total, l_total, total_deduction_items  (proven May long format + June)
"""
(HERE/"june2026_schema_notes.txt").write_text(SCHEMA, encoding="utf-8")
print("\nWROTE june2026_validation_output.txt + june2026_schema_notes.txt")
