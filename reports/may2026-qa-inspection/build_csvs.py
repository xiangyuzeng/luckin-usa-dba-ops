#!/usr/bin/env python3
"""
Build May 2026 inspection-export CSVs from LIVE data pulled via mcp-db-gateway.

This bundle adds appeal-aware columns vs the April v2 bundle:

  may2026_inspection_summary.csv
    - is_appealed (0|1)                         per-inspection any-appeal flag
    - original_total_score / adjusted_total_score
    - original_total_deduction / adjusted_total_deduction

  may2026_inspection_items.csv
    - is_appealed_finding (0|1)                 per-finding appeal flag

  may2026_store_master.csv
    - open_date (YYYY-MM-DD)                    from t_shop_info.set_up_time

The same enhanced summary is also exported for April:

  april2026_inspection_summary.csv  (re-export with the new columns)

Source: aws-luckyus-opqualitycontrol-rw / luckyus_opqualitycontrol
Tables: t_shopcheck_data, t_shopcheck_opportunity, t_shopcheck_report,
        t_shopcheck_item_config, t_shopcheck_category_config
Store master: aws-luckyus-opshop-rw / luckyus_opshop.t_shop_info

Inspection-type mapping (large_category_id):
  1084 -> 门店自检 (Store food safety self-check)
  1134 -> QA审计   (Store food safety audit)
  1184 -> 区经检查 (Area food safety Check)

Severity mapping (deduction_type):
  1 -> S, 2 -> G, 3 -> M, 4 -> L

Appeal mechanics (per-finding, per-inspection)
==============================================
- An opportunity row is APPEALED when first_appeal_detail or second_appeal_detail
  is non-empty in t_shopcheck_opportunity.
- An APPROVED appeal flips opportunity.status from 1 -> 0 and zeroes that item's
  contribution to deductionScore in t_shopcheck_report.opportunity_desc JSON.
- A DENIED / pending appeal leaves status=1; the deductionScore is unchanged.
- 'is_appealed_finding' = 1 if either appeal_detail is non-empty (file-was-filed
  semantics), regardless of approval outcome.
- 'is_appealed' (inspection-level) = 1 if any of its findings has
  is_appealed_finding = 1.

Score formula (production / non-IQA2Test data)
==============================================
  adjusted_total_deduction = SUM(deductionScore) over types in opportunity_desc
  adjusted_total_score     = report.score
  original_total_deduction = SUM(opportunity.score_config) over non-deleted rows
                             (regardless of opp.status)
  S_penalty(x)             = -20 if any type=1 contribution < 0 in x else 0
  original_total_score     = 100 + original_total_deduction
                             + S_penalty(original)
  (Validated: matches report.score for adjusted side on all production rows.)
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
OUT = HERE
RAW = HERE / "raw"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TYPE_MAP = {
    1084: ("门店自检", "Store food safety self-check"),
    1134: ("QA审计",   "Store food safety audit"),
    1184: ("区经检查", "Area food safety Check"),
}
SEV_MAP = {1: "S", 2: "G", 3: "M", 4: "L"}

POSTCODE_ROLE = {
    "LKUS00000076": "Area Operations Manager",
    "LKUS00000078": "Senior QA Manager",
    "LKUS00000223": "Senior QA Manager",
    "LKUS00000082": "Store Manager",
    "LKUS00000083": "Assistant Store Manager",
    "LKUS00000098": "Shift Supervisor / Trainer",
}
ROLE_FALLBACK = {
    "门店自检": "Store Manager",
    "QA审计":   "Senior QA Manager",
    "区经检查": "Area Operations Manager",
}

# ---------------------------------------------------------------------------
# Load raw inputs
# ---------------------------------------------------------------------------
HEADERS = json.loads((RAW / "headers.json").read_text(encoding="utf-8"))
REPORTS = json.loads((RAW / "reports.json").read_text(encoding="utf-8"))
Q1_DEDS = json.loads((RAW / "q1_deductions.json").read_text(encoding="utf-8"))
STORES  = json.loads((RAW / "stores.json").read_text(encoding="utf-8"))
APRMAY_OPPS = json.loads((RAW / "aprmay_opportunities.json").read_text(encoding="utf-8"))

print(f"[load] {len(HEADERS):>4d} headers (Jan-May 2026)")
print(f"[load] {len(REPORTS):>4d} reports (Apr+May 2026)")
print(f"[load] {len(Q1_DEDS):>4d} q1_deduction summary rows")
print(f"[load] {len(STORES):>4d} stores")
print(f"[load] {len(APRMAY_OPPS):>4d} Apr+May opportunity items")

HEADER_BY_ID = {h["id"]: h for h in HEADERS}
REPORTS_APRMAY_BY_DATA_ID = {r["shopcheck_data_id"]: r for r in REPORTS}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
STORE_BY_DEPT = {s["dept_id"]: s for s in STORES}

def store_code(dept_id):
    s = STORE_BY_DEPT.get(dept_id)
    return s["shop_no"] if s else f"DEPT-{dept_id}"

def store_name(dept_id):
    s = STORE_BY_DEPT.get(dept_id)
    return s["shop_name"] if s else f"(unknown dept {dept_id})"

def role_for(post_code, inspection_type, name=None):
    if post_code and post_code in POSTCODE_ROLE:
        return POSTCODE_ROLE[post_code]
    return ROLE_FALLBACK.get(inspection_type, "Unknown")

def parse_dt_counts(opp_desc_json):
    if not opp_desc_json:
        return {}
    try:
        arr = json.loads(opp_desc_json)
    except Exception:
        return {}
    out = defaultdict(int)
    for x in arr:
        out[x.get("deductionType")] += x.get("count", 0)
    return out

def parse_dt_scores(opp_desc_json):
    """Return dict {deductionType: deductionScore} from the report JSON."""
    if not opp_desc_json:
        return {}
    try:
        arr = json.loads(opp_desc_json)
    except Exception:
        return {}
    out = defaultdict(int)
    for x in arr:
        out[x.get("deductionType")] += x.get("deductionScore", 0)
    return out

def parse_total_deduction(opp_desc_json):
    return sum(parse_dt_scores(opp_desc_json).values())

# ---------------------------------------------------------------------------
# Per-inspection appeal + original-score computation
# ---------------------------------------------------------------------------
OPPS_BY_IID = defaultdict(list)
for o in APRMAY_OPPS:
    OPPS_BY_IID[o["shopcheck_data_id"]].append(o)

def appeal_summary_for(iid):
    """Return (is_appealed:int, original_total_deduction:int, original_s_present:bool)
    derived from t_shopcheck_opportunity rows for this inspection."""
    opps = OPPS_BY_IID.get(iid, [])
    is_appealed = 0
    orig_ded = 0
    orig_s_present = False
    for o in opps:
        if o["has_first_appeal"] or o["has_second_appeal"]:
            is_appealed = 1
        sc = o.get("score_config") or 0
        orig_ded += sc
        if o.get("deduction_type") == 1 and sc < 0:
            orig_s_present = True
    return is_appealed, orig_ded, orig_s_present

# ---------------------------------------------------------------------------
# Misubmission filter (Darwin Coronel duplicate self-check rule, carried over from April v2)
# ---------------------------------------------------------------------------
def parse_iid_count(iid):
    rep = REPORTS_APRMAY_BY_DATA_ID.get(iid)
    if not rep:
        return 0, None
    cnts = parse_dt_counts(rep["opportunity_desc"])
    return sum(cnts.values()), rep["score"]

def compute_misubmission_exclusions():
    grp = defaultdict(list)
    for h in HEADERS:
        if h["status"] != 1:
            continue
        if h["check_date"][:7] not in ("2026-04", "2026-05"):
            continue
        iid = h["id"]
        ic, sc = parse_iid_count(iid)
        key = (h["checker_id"], h["dept_id"], h["check_date"])
        grp[key].append({"iid": iid, "item_count": ic, "score": sc, "header": h})
    exclude = {}
    for arr in grp.values():
        if len(arr) < 2:
            continue
        if not any(x["item_count"] > 0 for x in arr):
            continue
        for x in arr:
            if x["score"] == 100 and x["item_count"] == 0:
                h = x["header"]
                exclude[x["iid"]] = {
                    "inspector": h["checker_name"],
                    "checker_id": h["checker_id"],
                    "dept_id": h["dept_id"],
                    "store_code": store_code(h["dept_id"]),
                    "date": h["check_date"],
                    "siblings": [s["iid"] for s in arr if s["iid"] != x["iid"]],
                }
    return exclude

EXCLUDE = compute_misubmission_exclusions()
print(f"[filter] misubmission exclusions (Apr+May): {len(EXCLUDE)} inspection(s)")
for iid, info in sorted(EXCLUDE.items()):
    print(f"  - drop iid={iid}  inspector={info['inspector']}  store={info['store_code']}  date={info['date']}  siblings={info['siblings']}")

# ---------------------------------------------------------------------------
# CSV builder: inspection summary (parametrised by month)
# ---------------------------------------------------------------------------
def build_summary_rows(month_prefix):
    """month_prefix like '2026-04' or '2026-05'."""
    rows = []
    for h in HEADERS:
        if h["check_date"][:7] != month_prefix:
            continue
        if h["status"] != 1:
            continue
        iid = h["id"]
        if iid in EXCLUDE:
            continue
        # skip non-production inspection types (test categories don't appear in TYPE_MAP)
        if h["large_category_id"] not in TYPE_MAP:
            continue
        rep = REPORTS_APRMAY_BY_DATA_ID.get(iid)
        type_zh, type_raw = TYPE_MAP[h["large_category_id"]]
        post = rep["checker_post_code"] if rep else None

        if rep:
            cnts = parse_dt_counts(rep["opportunity_desc"])
            adjusted_score = rep["score"]
            adjusted_ded   = parse_total_deduction(rep["opportunity_desc"])
        else:
            cnts = {}
            adjusted_score = ""
            adjusted_ded   = ""

        s_c = cnts.get(1, 0); m_c = cnts.get(3, 0); g_c = cnts.get(2, 0); l_c = cnts.get(4, 0)

        is_appealed, orig_ded, orig_s_present = appeal_summary_for(iid)
        if is_appealed and rep:
            # original score uses canonical opportunity rows (status=0 OR 1)
            # plus -20 if any S item was originally deducted
            original_total_score = 100 + orig_ded + (-20 if orig_s_present else 0)
            original_total_ded   = orig_ded
        else:
            original_total_score = adjusted_score
            original_total_ded   = adjusted_ded

        rows.append({
            "inspection_id": iid,
            "store_code": store_code(h["dept_id"]),
            "store_name": store_name(h["dept_id"]),
            "inspection_date": h["check_date"],
            "inspection_type": type_zh,
            "inspection_type_raw": type_raw,
            "inspector_name": h["checker_name"],
            "inspector_role": role_for(post, type_zh, h["checker_name"]),
            "is_appealed": is_appealed,
            "adjusted_total_score": adjusted_score,
            "original_total_score": original_total_score,
            "adjusted_total_deduction": adjusted_ded,
            "original_total_deduction": original_total_ded,
            "item_count": s_c + m_c + g_c + l_c,
            "s_count": s_c, "m_count": m_c, "g_count": g_c, "l_count": l_c,
        })
    rows.sort(key=lambda r: (r["store_code"], r["inspection_date"], r["inspection_id"]))
    return rows

def write_summary(rows, filename):
    path = OUT / filename
    fields = ["inspection_id","store_code","store_name","inspection_date","inspection_type",
              "inspection_type_raw","inspector_name","inspector_role",
              "is_appealed",
              "adjusted_total_score","original_total_score",
              "adjusted_total_deduction","original_total_deduction",
              "item_count","s_count","m_count","g_count","l_count"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# CSV builder: inspection items (parametrised by month)
# ---------------------------------------------------------------------------
def write_items(month_prefix, filename, excluded_ids):
    path = OUT / filename
    rows = []
    sev_order = {"S": 0, "M": 1, "G": 2, "L": 3}
    for opp in APRMAY_OPPS:
        iid = opp["shopcheck_data_id"]
        if iid in excluded_ids:
            continue
        h = HEADER_BY_ID.get(iid)
        if not h or h["status"] != 1:
            continue
        if h["check_date"][:7] != month_prefix:
            continue
        if h["large_category_id"] not in TYPE_MAP:
            continue
        type_zh, _ = TYPE_MAP[h["large_category_id"]]
        sev = SEV_MAP.get(opp.get("deduction_type"), str(opp.get("deduction_type")))
        desc = opp.get("remark")
        if desc is None or str(desc).strip() == "":
            desc = "(无描述)"
        is_appealed_finding = 1 if (opp.get("has_first_appeal") or opp.get("has_second_appeal")) else 0
        rows.append({
            "item_id": opp["opp_id"],
            "inspection_id": iid,
            "store_code": store_code(h["dept_id"]),
            "store_name": store_name(h["dept_id"]),
            "inspection_date": h["check_date"],
            "inspection_type": type_zh,
            "inspector_name": h["checker_name"],
            "module_name": opp.get("module_name") or "",
            "module_subcategory": opp.get("leaf_cat_name") or "",
            "clause_number": str(opp["check_item_id"]),
            "issue_description": desc,
            "severity": sev,
            "deduction_points": opp.get("score_config"),
            "is_appealed_finding": is_appealed_finding,
        })
    rows.sort(key=lambda r: (
        r["store_code"], r["inspection_date"],
        sev_order.get(r["severity"], 99),
        (r["deduction_points"] if isinstance(r["deduction_points"], (int, float)) else 0),
    ))
    fields = ["item_id","inspection_id","store_code","store_name","inspection_date",
              "inspection_type","inspector_name","module_name","module_subcategory",
              "clause_number","issue_description","severity","deduction_points",
              "is_appealed_finding"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# CSV: store master with open_date
# ---------------------------------------------------------------------------
def write_store_master():
    path = OUT / "may2026_store_master.csv"
    inspected_may = {h["dept_id"] for h in HEADERS
                     if h["check_date"][:7] == "2026-05" and h["status"] == 1
                     and h["id"] not in EXCLUDE}
    rows = []
    for s in STORES:
        if s["tenant"] != "LKUS" and s["dept_id"] not in inspected_may:
            continue
        if s["tenant"] == "LKUS" and not (s["shop_no"] or "").startswith("US"):
            continue
        st = s["status"]
        status_label = "active" if st == 1 else ("inactive" if st == 2 else "closed")
        if s.get("test_flag") == 1 or s["shop_no"].startswith("US999") or s["shop_no"].startswith("CK"):
            status_label += " (test/internal)"
        opening = s.get("set_up_time") or ""
        if opening:
            opening = opening[:10]
        rows.append({
            "store_id": s["id"],
            "store_code": s["shop_no"],
            "store_name": s["shop_name"],
            "address": s.get("address") or "",
            "status": status_label,
            "open_date": opening,
            "region": s.get("operation_area") or "",
            "inspected_in_may": "Yes" if s["dept_id"] in inspected_may else "No",
        })
    rows.sort(key=lambda r: r["store_code"])
    fields = ["store_id","store_code","store_name","address","status",
              "open_date","region","inspected_in_may"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# CSV: inspector trend (Jan-May)
# ---------------------------------------------------------------------------
def write_inspector_trend():
    path = OUT / "may2026_inspector_trend.csv"
    counters = defaultdict(lambda: {"jan":0,"feb":0,"mar":0,"apr":0,"may":0,
                                    "types": defaultdict(int)})
    bucket_for = {"2026-01":"jan","2026-02":"feb","2026-03":"mar","2026-04":"apr","2026-05":"may"}
    for h in HEADERS:
        if h["status"] != 1:
            continue
        if h["check_date"][:7] in ("2026-04","2026-05") and h["id"] in EXCLUDE:
            continue
        if h["large_category_id"] not in TYPE_MAP:
            continue
        ym = h["check_date"][:7]
        bk = bucket_for.get(ym)
        if not bk:
            continue
        type_zh, _ = TYPE_MAP[h["large_category_id"]]
        counters[h["checker_name"]][bk] += 1
        counters[h["checker_name"]]["types"][type_zh] += 1

    name_post = {}
    for r in REPORTS:
        h = HEADER_BY_ID.get(r["shopcheck_data_id"])
        if h and h["checker_name"] and r.get("checker_post_code"):
            name_post.setdefault(h["checker_name"], r["checker_post_code"])

    rows = []
    for name, c in counters.items():
        total = c["jan"] + c["feb"] + c["mar"] + c["apr"] + c["may"]
        typical = max(c["types"], key=c["types"].get) if c["types"] else ""
        rows.append({
            "inspector_name": name,
            "inspector_role": role_for(name_post.get(name), typical, name),
            "jan_count": c["jan"], "feb_count": c["feb"],
            "mar_count": c["mar"], "apr_count": c["apr"], "may_count": c["may"],
            "total_q1_to_may": total,
            "typical_inspection_type": typical,
        })
    rows.sort(key=lambda r: (-r["total_q1_to_may"], r["inspector_name"]))
    fields = ["inspector_name","inspector_role","jan_count","feb_count","mar_count",
              "apr_count","may_count","total_q1_to_may","typical_inspection_type"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# CSV: trend summary Jan-May
# ---------------------------------------------------------------------------
def write_trend_summary():
    path = OUT / "jan_to_may2026_trend_summary.csv"
    by_key = defaultdict(lambda: {"insp_ids": set(), "stores": set(),
                                  "scores": [], "S":0,"M":0,"G":0,"L":0,"items":0})

    q1_by_iid = defaultdict(dict)
    for d in Q1_DEDS:
        q1_by_iid[d["shopcheck_data_id"]][d["deduction_type"]] = d["cnt"]

    for h in HEADERS:
        if h["status"] != 1:
            continue
        if h["check_date"][:7] in ("2026-04","2026-05") and h["id"] in EXCLUDE:
            continue
        if h["large_category_id"] not in TYPE_MAP:
            continue
        ym = h["check_date"][:7]
        if ym not in {"2026-01","2026-02","2026-03","2026-04","2026-05"}:
            continue
        type_zh, _ = TYPE_MAP[h["large_category_id"]]
        rep = REPORTS_APRMAY_BY_DATA_ID.get(h["id"])
        if rep:
            cnts = parse_dt_counts(rep["opportunity_desc"])
            score = rep["score"]
        else:
            cnts = q1_by_iid.get(h["id"], {})
            score = None
        s_c = cnts.get(1,0); m_c = cnts.get(3,0); g_c = cnts.get(2,0); l_c = cnts.get(4,0)

        b = by_key[(ym, type_zh)]
        b["insp_ids"].add(h["id"])
        b["stores"].add(h["dept_id"])
        if score is not None:
            b["scores"].append(score)
        b["S"] += s_c; b["M"] += m_c; b["G"] += g_c; b["L"] += l_c
        b["items"] += s_c + m_c + g_c + l_c

    rows = []
    for m in ["2026-01","2026-02","2026-03","2026-04","2026-05"]:
        for t in ["门店自检","QA审计","区经检查"]:
            b = by_key.get((m, t))
            if b is None:
                rows.append({"month":m,"inspection_type":t,"inspection_count":0,
                             "stores_covered":0,"avg_score":"",
                             "s_total":0,"m_total":0,"g_total":0,"l_total":0,
                             "total_deduction_items":0})
            else:
                avg = round(sum(b["scores"])/len(b["scores"]), 1) if b["scores"] else ""
                rows.append({"month":m,"inspection_type":t,
                             "inspection_count": len(b["insp_ids"]),
                             "stores_covered": len(b["stores"]),
                             "avg_score": avg,
                             "s_total": b["S"], "m_total": b["M"], "g_total": b["G"], "l_total": b["L"],
                             "total_deduction_items": b["items"]})
    fields = ["month","inspection_type","inspection_count","stores_covered","avg_score",
              "s_total","m_total","g_total","l_total","total_deduction_items"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# Schema notes
# ---------------------------------------------------------------------------
SCHEMA_NOTES = """\
May 2026 Inspection Export — Schema Notes (built 2026-06-01, full closed month 05-01..05-31)

DISCOVERY
=========
- Database server (mcp-db-gateway): aws-luckyus-opqualitycontrol-rw
- Database (MySQL):                  luckyus_opqualitycontrol
- Tables used:
    t_shopcheck_data            inspection header
    t_shopcheck_opportunity     deduction items (with appeal_detail JSON)
    t_shopcheck_report          per-inspection scoring summary
    t_shopcheck_item_config     canonical clause text + score_config / deduction_type
    t_shopcheck_category_config module hierarchy
- Store master:                      aws-luckyus-opshop-rw / luckyus_opshop.t_shop_info

NEW IN MAY BUNDLE (vs April v2)
===============================
- Summary CSV adds is_appealed (0|1), original_total_score, adjusted_total_score,
  original_total_deduction, adjusted_total_deduction.
- Items CSV adds is_appealed_finding (0|1).
- Store master uses 'open_date' (was 'opening_date') for the YYYY-MM-DD set_up_time.
- April summary is RE-EXPORTED with the same enhanced column set
  (april2026_inspection_summary.csv inside this bundle).

INSPECTION-TYPE MAPPING (large_category_id)
===========================================
   1084 'Store food safety self-check'   -> 门店自检
   1134 'Store food safety audit'        -> QA审计
   1184 'Area food safety Check'         -> 区经检查
   (other ids — IQA2Test categories — are excluded from this bundle)

SEVERITY MAPPING (S / M / G / L)
================================
   deduction_type 1 -> S   2 -> G   3 -> M   4 -> L

SUBMITTED VIEW
==============
Published CSVs use status=1 (submitted) only. Drafts (status=0) are excluded.

MISUBMISSION FILTER (post-query)
================================
Drop any inspection where score=100 AND item_count=0 AND there exists another
inspection by the same inspector / store / date with item_count>0. Underlying
DB is not modified — exclusion is applied at the report layer only.

APPEAL SEMANTICS
================
- Per-item: 'is_appealed_finding' = 1 if t_shopcheck_opportunity.first_appeal_detail
  or second_appeal_detail is non-empty (an appeal has been filed regardless of
  outcome).
- Per-inspection: 'is_appealed' = 1 if any of its findings has is_appealed_finding=1.
- Approved appeal -> opportunity.status flips 1->0 AND that item's contribution
  to t_shopcheck_report.opportunity_desc.deductionScore is zeroed. The
  t_shopcheck_opportunity row itself remains, so item_id is still in items.csv
  with severity=S/M/G/L and deduction_points = canonical score_config.
- Denied / pending appeal -> status stays 1; deductionScore unchanged.

SCORE COMPUTATION (validated against report.score for production inspections)
============================================================================
  adjusted_total_deduction = SUM(deductionScore) over deductionTypes in opportunity_desc
  adjusted_total_score     = report.score
  S_penalty(x)             = -20 if any type=1 deductionScore < 0 in x else 0
                             (appears only on production inspections)
  original_total_deduction = SUM(opportunity.score_config) over non-deleted rows
                             (regardless of opp.status, i.e. before appeal)
  original_total_score     = 100 + original_total_deduction + S_penalty(original)
For inspections with no appeal, original == adjusted.

KEY JOIN GRAPH
==============
  t_shopcheck_data.id  ===  t_shopcheck_opportunity.shopcheck_data_id
  t_shopcheck_data.id  ===  t_shopcheck_report.shopcheck_data_id
  t_shopcheck_opportunity.check_item_id  ==  t_shopcheck_item_config.id
  t_shopcheck_item_config.category_config_id  ==  t_shopcheck_category_config.id (leaf)
  t_shopcheck_category_config.parent_id        ==  t_shopcheck_category_config.id (module)
  t_shopcheck_data.dept_id  ==  t_shop_info.dept_id        (store master)
"""

def write_schema_notes():
    path = OUT / "may2026_schema_notes.txt"
    path.write_text(SCHEMA_NOTES, encoding="utf-8")
    return path

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def run_validations(may_summary_rows, apr_summary_rows):
    out_lines = []
    def emit(s=""):
        out_lines.append(s); print(s)

    emit("="*80)
    emit("MAY 2026 INSPECTION DATA — VALIDATION OUTPUT (built 2026-06-01, full closed month)")
    emit("Source: aws-luckyus-opqualitycontrol-rw / luckyus_opqualitycontrol")
    emit("="*80)

    # A: May counts by type
    emit("\n--- A. May inspection count by type (status=1, misubmission-filtered) ---")
    by_t = defaultdict(lambda: {"cnt":0,"stores":set()})
    may_h = [h for h in HEADERS if h["check_date"][:7]=="2026-05" and h["status"]==1
             and h["id"] not in EXCLUDE and h["large_category_id"] in TYPE_MAP]
    for h in may_h:
        t_zh,_ = TYPE_MAP[h["large_category_id"]]
        by_t[t_zh]["cnt"] += 1
        by_t[t_zh]["stores"].add(h["dept_id"])
    emit(f"{'inspection_type':16s} {'cnt':>5s} {'stores':>7s}")
    for t in ["门店自检","QA审计","区经检查"]:
        b = by_t.get(t, {"cnt":0,"stores":set()})
        emit(f"{t:16s} {b['cnt']:5d} {len(b['stores']):7d}")
    emit(f"{'TOTAL':16s} {sum(b['cnt'] for b in by_t.values()):5d}")

    # B: May severity dist
    emit("\n--- B. May severity distribution ---")
    may_iids = {h["id"] for h in may_h}
    sev_cnt = defaultdict(int); sev_ded = defaultdict(int)
    for opp in APRMAY_OPPS:
        if opp["shopcheck_data_id"] not in may_iids:
            continue
        sev = SEV_MAP.get(opp.get("deduction_type"), str(opp.get("deduction_type")))
        sev_cnt[sev] += 1
        sev_ded[sev] += opp.get("score_config") or 0
    emit(f"{'severity':10s} {'cnt':>5s} {'total_deduction':>16s}")
    for s in ["S","M","G","L"]:
        emit(f"{s:10s} {sev_cnt.get(s,0):5d} {sev_ded.get(s,0):16d}")

    # C: appeal coverage May + April (sanity for re-export)
    emit("\n--- C. Appeal coverage ---")
    may_appeal = sum(r["is_appealed"] for r in may_summary_rows)
    apr_appeal = sum(r["is_appealed"] for r in apr_summary_rows)
    emit(f"May 2026: {may_appeal} of {len(may_summary_rows)} inspections have is_appealed=1")
    emit(f"Apr 2026: {apr_appeal} of {len(apr_summary_rows)} inspections have is_appealed=1")

    # D: April rows where original differs from adjusted
    emit("\n--- D. April inspections where original_total_score != adjusted_total_score ---")
    diff = [r for r in apr_summary_rows if r["adjusted_total_score"] != "" and
            r["original_total_score"] != r["adjusted_total_score"]]
    emit(f"{'iid':>5s} {'store':10s} {'date':12s} {'inspector':22s} "
         f"{'orig_score':>10s} {'adj_score':>10s} {'orig_ded':>10s} {'adj_ded':>10s} {'is_app':>6s}")
    for r in diff:
        emit(f"{r['inspection_id']:>5d} {r['store_code']:10s} {r['inspection_date']:12s} "
             f"{r['inspector_name'][:22]:22s} "
             f"{str(r['original_total_score']):>10s} {str(r['adjusted_total_score']):>10s} "
             f"{str(r['original_total_deduction']):>10s} {str(r['adjusted_total_deduction']):>10s} "
             f"{r['is_appealed']:>6d}")
    if not diff:
        emit("(none)")

    # E: Score formula sanity check (production data, status=1)
    emit("\n--- E. Score formula sanity check (LKUS production rows) ---")
    mismatches = 0; checked = 0
    for h in HEADERS:
        if h["check_date"][:7] not in ("2026-04","2026-05"):
            continue
        if h["status"] != 1 or h["id"] in EXCLUDE:
            continue
        if h["large_category_id"] not in TYPE_MAP:
            continue
        rep = REPORTS_APRMAY_BY_DATA_ID.get(h["id"])
        if not rep:
            continue
        adj_ded = parse_total_deduction(rep["opportunity_desc"])
        adj_dt_scores = parse_dt_scores(rep["opportunity_desc"])
        s_pen = -20 if adj_dt_scores.get(1,0) < 0 else 0
        expected = 100 + adj_ded + s_pen
        if expected != rep["score"]:
            mismatches += 1
            emit(f"  iid={h['id']} store={store_code(h['dept_id'])} "
                 f"adj_ded={adj_ded} s_pen={s_pen} expected={expected} actual={rep['score']}")
        checked += 1
    emit(f"checked={checked}  mismatches={mismatches}  {'PASS' if mismatches==0 else 'FAIL'}")

    (OUT / "may2026_validation_output.txt").write_text("\n".join(out_lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    excluded_ids = set(EXCLUDE)

    may_rows = build_summary_rows("2026-05")
    n, p = write_summary(may_rows, "may2026_inspection_summary.csv")
    print(f"WROTE {n} rows -> {p}")

    apr_rows = build_summary_rows("2026-04")
    n, p = write_summary(apr_rows, "april2026_inspection_summary.csv")
    print(f"WROTE {n} rows -> {p}")

    n, p = write_items("2026-05", "may2026_inspection_items.csv", excluded_ids)
    print(f"WROTE {n} rows -> {p}")

    n, p = write_items("2026-04", "april2026_inspection_items.csv", excluded_ids)
    print(f"WROTE {n} rows -> {p}")

    n, p = write_store_master()
    print(f"WROTE {n} rows -> {p}")

    n, p = write_inspector_trend()
    print(f"WROTE {n} rows -> {p}")

    n, p = write_trend_summary()
    print(f"WROTE {n} rows -> {p}")

    p = write_schema_notes()
    print(f"WROTE schema notes  -> {p}")

    print()
    run_validations(may_rows, apr_rows)
