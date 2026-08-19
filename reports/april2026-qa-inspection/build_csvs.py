#!/usr/bin/env python3
"""
Build April 2026 inspection-export CSVs from LIVE data pulled via mcp-db-gateway.

This is the v2 refresh of the April 2026 QA bundle. Differences from v1:
  - HEADERS / REPORTS / Q1_DEDUCTIONS / STORES are loaded from raw/*.json
    (live snapshot pulled via MCP) instead of being embedded in the script body.
  - Applies a misubmission filter to drop duplicate self-checks where
    score=100 AND item_count=0 AND another inspection by the same inspector
    on the same date+store has item_count>0 (Darwin Coronel 4/21 case).
  - Generates a REFRESH DELTAS section in the validation file by comparing
    the refreshed CSV state against the prior published CSV.

Source: aws-luckyus-opqualitycontrol-rw / luckyus_opqualitycontrol
Tables: t_shopcheck_data (header), t_shopcheck_opportunity (deductions),
        t_shopcheck_report (scores), t_shopcheck_item_config, t_shopcheck_category_config
Store master: aws-luckyus-opshop-rw / luckyus_opshop.t_shop_info

Inspection-type mapping (large_category_id):
  1084 -> 门店自检 (Store food safety self-check)
  1134 -> QA审计   (Store food safety audit)
  1184 -> 区经检查 (Area food safety Check)

Severity mapping (deduction_type):
  1 -> S, 2 -> G, 3 -> M, 4 -> L
"""

import csv
import json
import os
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
OUT = HERE
RAW = HERE / "raw"
PRIOR_DIR = Path("/app/reports/april2026-qa-inspection")  # for delta comparison

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
HEADERS    = json.loads((RAW / "headers.json").read_text(encoding="utf-8"))
REPORTS    = json.loads((RAW / "reports.json").read_text(encoding="utf-8"))
Q1_DEDS    = json.loads((RAW / "q1_deductions.json").read_text(encoding="utf-8"))
STORES     = json.loads((RAW / "stores.json").read_text(encoding="utf-8"))
APR_OPPS   = json.loads((RAW / "april_opportunities.json").read_text(encoding="utf-8"))

print(f"[load] {len(HEADERS):>4d} headers (Jan-Apr 2026)")
print(f"[load] {len(REPORTS):>4d} reports (Jan-Apr 2026)")
print(f"[load] {len(Q1_DEDS):>4d} q1_deduction summary rows")
print(f"[load] {len(STORES):>4d} stores")
print(f"[load] {len(APR_OPPS):>4d} April opportunity items")

# Split reports into Q1 and Apr by header check_date (need to look it up)
HEADER_BY_ID = {h["id"]: h for h in HEADERS}
REPORTS_APR = []
REPORTS_Q1  = []
for r in REPORTS:
    h = HEADER_BY_ID.get(r["shopcheck_data_id"])
    if not h:
        continue
    if h["check_date"][:7] == "2026-04":
        REPORTS_APR.append(r)
    else:
        REPORTS_Q1.append(r)
print(f"[split] {len(REPORTS_APR):>4d} April reports, {len(REPORTS_Q1):>4d} Q1 reports")

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

def parse_total_deduction(opp_desc_json):
    if not opp_desc_json:
        return 0
    try:
        arr = json.loads(opp_desc_json)
    except Exception:
        return 0
    return sum(x.get("deductionScore", 0) for x in arr)

REPORT_BY_DATA_ID_APR = {r["shopcheck_data_id"]: r for r in REPORTS_APR}
REPORT_BY_DATA_ID_Q1  = {r["shopcheck_data_id"]: r for r in REPORTS_Q1}

# ---------------------------------------------------------------------------
# Misubmission filter (Darwin Coronel duplicate self-check rule)
#
# Rule: drop any inspection where
#   score = 100 AND item_count = 0
#   AND there exists another inspection by the same inspector (checker_id),
#       same store (dept_id), same date with item_count > 0.
#
# Applied as a post-query filter so the rule is documented and reproducible.
# Applies ONLY to summary CSV + items CSV + report-layer counts;
# the underlying DB and the inspector trend / monthly trend rows reflect this filter.
# ---------------------------------------------------------------------------
def compute_misubmission_exclusions():
    """Return set of inspection_ids to exclude. Only considers status=1 (submitted)
    rows so the filter aligns with the published view."""
    # build map: (checker_id, dept_id, date) -> [(iid, item_count), ...]
    grp = defaultdict(list)
    for h in HEADERS:
        if h["status"] != 1:
            continue
        iid = h["id"]
        rep = REPORT_BY_DATA_ID_APR.get(iid) or REPORT_BY_DATA_ID_Q1.get(iid)
        if not rep:
            ic = 0
            sc = None
        else:
            cnts = parse_dt_counts(rep["opportunity_desc"])
            ic = sum(cnts.values())
            sc = rep["score"]
        key = (h["checker_id"], h["dept_id"], h["check_date"])
        grp[key].append({"iid": iid, "item_count": ic, "score": sc, "header": h})

    exclude = {}
    for key, arr in grp.items():
        if len(arr) < 2:
            continue
        has_real = any(x["item_count"] > 0 for x in arr)
        if not has_real:
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
print(f"[filter] misubmission exclusions: {len(EXCLUDE)} inspection(s)")
for iid, info in sorted(EXCLUDE.items()):
    print(f"  - drop inspection_id={iid}  inspector={info['inspector']}  "
          f"store={info['store_code']}  date={info['date']}  "
          f"reason=score=100 item_count=0; sibling(s) {info['siblings']} have items")


# ---------------------------------------------------------------------------
# CSV 1: april2026_inspection_summary.csv
# ---------------------------------------------------------------------------
def build_summary_rows():
    rows = []
    for h in HEADERS:
        if h["check_date"][:7] != "2026-04":
            continue
        if h["status"] != 1:           # status=1 (submitted) view
            continue
        iid = h["id"]
        if iid in EXCLUDE:
            continue
        rep = REPORT_BY_DATA_ID_APR.get(iid)
        type_zh, type_raw = TYPE_MAP[h["large_category_id"]]
        post = rep["checker_post_code"] if rep else None
        if rep:
            cnts = parse_dt_counts(rep["opportunity_desc"])
            score = rep["score"]
            total_ded = parse_total_deduction(rep["opportunity_desc"])
        else:
            cnts = {}; score = ""; total_ded = ""
        s_c = cnts.get(1, 0)
        m_c = cnts.get(3, 0)
        g_c = cnts.get(2, 0)
        l_c = cnts.get(4, 0)
        rows.append({
            "inspection_id": iid,
            "store_code": store_code(h["dept_id"]),
            "store_name": store_name(h["dept_id"]),
            "inspection_date": h["check_date"],
            "inspection_type": type_zh,
            "inspection_type_raw": type_raw,
            "inspector_name": h["checker_name"],
            "inspector_role": role_for(post, type_zh, h["checker_name"]),
            "total_score": score,
            "total_deduction": total_ded,
            "item_count": s_c + m_c + g_c + l_c,
            "s_count": s_c, "m_count": m_c, "g_count": g_c, "l_count": l_c,
        })
    rows.sort(key=lambda r: (r["store_code"], r["inspection_date"], r["inspection_id"]))
    return rows

def write_summary(rows):
    path = OUT / "april2026_inspection_summary.csv"
    fields = ["inspection_id","store_code","store_name","inspection_date","inspection_type",
              "inspection_type_raw","inspector_name","inspector_role","total_score",
              "total_deduction","item_count","s_count","m_count","g_count","l_count"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# CSV 2: april2026_inspection_items.csv
# ---------------------------------------------------------------------------
def write_items(excluded_ids):
    path = OUT / "april2026_inspection_items.csv"
    rows = []
    sev_order = {"S": 0, "M": 1, "G": 2, "L": 3}
    for opp in APR_OPPS:
        iid = opp["shopcheck_data_id"]
        if iid in excluded_ids:
            continue
        h = HEADER_BY_ID.get(iid)
        if not h or h["status"] != 1:
            continue
        type_zh, _ = TYPE_MAP[h["large_category_id"]]
        sev = SEV_MAP.get(opp["deduction_type"], str(opp["deduction_type"]))
        desc = opp.get("remark")
        if desc is None or str(desc).strip() == "":
            desc = "(无描述)"
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
            "deduction_points": opp["score_config"],
        })
    rows.sort(key=lambda r: (
        r["store_code"], r["inspection_date"],
        sev_order.get(r["severity"], 99),
        (r["deduction_points"] if isinstance(r["deduction_points"], (int, float)) else 0),
    ))
    fields = ["item_id","inspection_id","store_code","store_name","inspection_date",
              "inspection_type","inspector_name","module_name","module_subcategory",
              "clause_number","issue_description","severity","deduction_points"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# CSV 3: april2026_store_master.csv
# ---------------------------------------------------------------------------
def write_store_master():
    path = OUT / "april2026_store_master.csv"
    inspected_april = {h["dept_id"] for h in HEADERS
                       if h["check_date"][:7] == "2026-04" and h["status"] == 1
                       and h["id"] not in EXCLUDE}

    rows = []
    for s in STORES:
        # Only US-prefixed (LKUS) stores plus any IQA2 dept that had April inspections.
        # Match v1 behavior: include LKUS US-prefixed, exclude others unless inspected.
        if s["tenant"] != "LKUS" and s["dept_id"] not in inspected_april:
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
            "opening_date": opening,
            "region": s.get("operation_area") or "",
            "inspected_in_april": "Yes" if s["dept_id"] in inspected_april else "No",
        })
    rows.sort(key=lambda r: r["store_code"])
    fields = ["store_id","store_code","store_name","address","status",
              "opening_date","region","inspected_in_april"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# CSV 4: april2026_inspector_trend.csv
# ---------------------------------------------------------------------------
def write_inspector_trend():
    path = OUT / "april2026_inspector_trend.csv"
    counters = defaultdict(lambda: {"jan":0, "feb":0, "mar":0, "apr":0,
                                    "types": defaultdict(int)})
    for h in HEADERS:
        # Only published (status=1) inspections; apply misubmission filter to April
        if h["status"] != 1:
            continue
        if h["check_date"][:7] == "2026-04" and h["id"] in EXCLUDE:
            continue
        ym = h["check_date"][:7]
        bucket = {"2026-01":"jan","2026-02":"feb","2026-03":"mar","2026-04":"apr"}.get(ym)
        if not bucket:
            continue
        name = h["checker_name"]
        counters[name][bucket] += 1
        type_zh, _ = TYPE_MAP[h["large_category_id"]]
        counters[name]["types"][type_zh] += 1

    name_post = {}
    for r in REPORTS:
        h = HEADER_BY_ID.get(r["shopcheck_data_id"])
        if h and h["checker_name"] and r.get("checker_post_code"):
            name_post.setdefault(h["checker_name"], r["checker_post_code"])

    rows = []
    for name, c in counters.items():
        total = c["jan"] + c["feb"] + c["mar"] + c["apr"]
        typical = max(c["types"], key=c["types"].get) if c["types"] else ""
        rows.append({
            "inspector_name": name,
            "inspector_role": role_for(name_post.get(name), typical, name),
            "jan_count": c["jan"], "feb_count": c["feb"],
            "mar_count": c["mar"], "apr_count": c["apr"],
            "total_q1_apr": total,
            "typical_inspection_type": typical,
        })
    rows.sort(key=lambda r: (-r["total_q1_apr"], r["inspector_name"]))
    fields = ["inspector_name","inspector_role","jan_count","feb_count",
              "mar_count","apr_count","total_q1_apr","typical_inspection_type"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# CSV 5: jan_to_apr2026_trend_summary.csv
# ---------------------------------------------------------------------------
def write_trend_summary():
    path = OUT / "jan_to_apr2026_trend_summary.csv"
    by_key = defaultdict(lambda: {"insp_ids": set(), "stores": set(),
                                  "scores": [], "S":0, "M":0, "G":0, "L":0, "items":0})

    def get_report(iid):
        return REPORT_BY_DATA_ID_APR.get(iid) or REPORT_BY_DATA_ID_Q1.get(iid)

    q1_by_iid = defaultdict(dict)
    for d in Q1_DEDS:
        q1_by_iid[d["shopcheck_data_id"]][d["deduction_type"]] = d["cnt"]

    for h in HEADERS:
        if h["status"] != 1:
            continue
        if h["check_date"][:7] == "2026-04" and h["id"] in EXCLUDE:
            continue
        ym = h["check_date"][:7]
        if ym not in {"2026-01","2026-02","2026-03","2026-04"}:
            continue
        type_zh, _ = TYPE_MAP[h["large_category_id"]]
        rep = get_report(h["id"])
        if rep:
            cnts = parse_dt_counts(rep["opportunity_desc"])
            score = rep["score"]
        else:
            cnts = q1_by_iid.get(h["id"], {})
            score = None
        s_c = cnts.get(1, 0); m_c = cnts.get(3, 0); g_c = cnts.get(2, 0); l_c = cnts.get(4, 0)

        bucket = by_key[(ym, type_zh)]
        bucket["insp_ids"].add(h["id"])
        bucket["stores"].add(h["dept_id"])
        if score is not None:
            bucket["scores"].append(score)
        bucket["S"] += s_c; bucket["M"] += m_c; bucket["G"] += g_c; bucket["L"] += l_c
        bucket["items"] += s_c + m_c + g_c + l_c

    rows = []
    for m in ["2026-01","2026-02","2026-03","2026-04"]:
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
# Schema notes file (preserved from v1, with v2 refresh annotation)
# ---------------------------------------------------------------------------
SCHEMA_NOTES = """\
April 2026 Inspection Export — Schema Notes (v2 REFRESH 2026-05-01)

DISCOVERY
=========
- Database server (mcp-db-gateway): aws-luckyus-opqualitycontrol-rw
- Database (MySQL):                  luckyus_opqualitycontrol
- Tables found (rows):
    t_shopcheck_data            221 rows  门店检查数据 (inspection header)
    t_shopcheck_opportunity    1113 rows  门店检查机会点 (deduction items)
    t_shopcheck_report          201 rows  门店检查报告 (scoring summary)
    t_shopcheck_item_config    1289 rows  门店检查项配置 (canonical clause text)
    t_shopcheck_category_config 616 rows  门店检查类配置 (module hierarchy)
    t_shopcheck_tag             363 rows  门店检查标签 (English module labels)
    t_shopcheck_config_snapshot 2506 rows  inspection config snapshot per data row
- Store master found at:             aws-luckyus-opshop-rw / luckyus_opshop.t_shop_info  (519 rows)

V2 REFRESH NOTES (2026-05-01)
=============================
- Re-pulled live data via mcp-db-gateway after two known changes:
  1. Inspection 2040 (54th & 8th, 2026-04-30 QA audit by Eamonn Caballar) was
     re-scored from 69 to 94 after store appeal approved. The S item is still
     present on the row but its deductionScore was zeroed (count=1, score=0).
  2. Inspection 2016 and 2017 (Darwin Coronel, 21st & 3rd, 2026-04-21 self-checks)
     were misubmissions (score=100, item_count=0). They are excluded from the
     published CSVs by the misubmission filter rule. The real inspection that day
     is 2018 (score=64, 5 items). DB rows are NOT touched — exclusion is
     applied at the report layer only.

INSPECTION-TYPE MAPPING (large_category_id)
===========================================
   id 1084 'Store food safety self-check'   -> 门店自检   (Store Self-Inspection)
   id 1134 'Store food safety audit'        -> QA审计     (QA Audit)
   id 1184 'Area food safety Check'         -> 区经检查   (Area Manager Inspection)

SEVERITY MAPPING (S / M / G / L)
================================
   deduction_type 1 -> S
   deduction_type 2 -> G
   deduction_type 3 -> M
   deduction_type 4 -> L
   deduction_type 9 -> '9'  (kept literal — only 2 items repo-wide, score_config=0)

SUBMITTED VIEW
==============
Published CSVs use status=1 (submitted) only. Drafts (status=0) are excluded —
this matches the canonical view used by prior monthly reports.

MISUBMISSION FILTER (post-query, v2 only)
=========================================
Exclusion rule:
  drop any inspection where
    score = 100 AND item_count = 0
    AND there exists another inspection by the same inspector (checker_id),
        same store (dept_id), same date with item_count > 0.

Only affects published CSVs and report-layer counts. The underlying DB is NOT
modified. Other clean-100 self-checks (e.g. one-off inspections that day) are
preserved.

INSPECTOR ROLE BY POST CODE
============================
   LKUS00000076 -> Area Operations Manager     (Daniel Chu, Jung Han Liang)
   LKUS00000078 -> Senior QA Manager           (Yu Jiang)
   LKUS00000223 -> Senior QA Manager           (Eamonn Caballar)
   LKUS00000082 -> Store Manager
   LKUS00000083 -> Assistant Store Manager
   LKUS00000098 -> Shift Supervisor / Trainer

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
    path = OUT / "april2026_schema_notes.txt"
    path.write_text(SCHEMA_NOTES, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# REFRESH DELTAS — compare prior CSV vs current
# ---------------------------------------------------------------------------
def load_prior_summary():
    p = PRIOR_DIR / "april2026_inspection_summary.csv"
    if not p.exists():
        return {}
    out = {}
    with p.open() as f:
        for r in csv.DictReader(f):
            iid = int(r["inspection_id"])
            out[iid] = r
    return out

def load_prior_items():
    p = PRIOR_DIR / "april2026_inspection_items.csv"
    if not p.exists():
        return {}
    out = {}
    with p.open() as f:
        for r in csv.DictReader(f):
            iid = int(r["item_id"])
            out[iid] = r
    return out

def fmt_int_or_blank(v):
    if v == "" or v is None:
        return ""
    return str(v)


# ---------------------------------------------------------------------------
# Validation + REFRESH DELTAS
# ---------------------------------------------------------------------------
def run_validations(summary_rows):
    out_lines = []
    def emit(s=""):
        out_lines.append(s)
        print(s)

    emit("="*80)
    emit("APRIL 2026 INSPECTION DATA — VALIDATION OUTPUT (v2 REFRESH 2026-05-01)")
    emit("Source: aws-luckyus-opqualitycontrol-rw / luckyus_opqualitycontrol")
    emit("="*80)

    apr_headers = [h for h in HEADERS if h["check_date"][:7] == "2026-04" and h["status"] == 1
                   and h["id"] not in EXCLUDE]
    apr_h_by_id = {h["id"]: h for h in apr_headers}

    # ---- A. April count by type (post-filter) ----
    emit("\n--- A. April inspection count by type (status=1, misubmission-filtered) ---")
    by_t = defaultdict(lambda: {"cnt":0, "stores":set()})
    for h in apr_headers:
        t_zh, _ = TYPE_MAP[h["large_category_id"]]
        by_t[t_zh]["cnt"] += 1
        by_t[t_zh]["stores"].add(h["dept_id"])
    emit(f"{'inspection_type':16s} {'cnt':>5s} {'stores':>7s}")
    for t in ["门店自检","QA审计","区经检查"]:
        b = by_t.get(t, {"cnt":0,"stores":set()})
        emit(f"{t:16s} {b['cnt']:5d} {len(b['stores']):7d}")
    total = sum(b['cnt'] for b in by_t.values())
    emit(f"{'TOTAL':16s} {total:5d}")

    # ---- B. April severity distribution ----
    emit("\n--- B. April severity distribution (across all deduction items, post-filter) ---")
    sev_cnt = defaultdict(int); sev_ded = defaultdict(int)
    for opp in APR_OPPS:
        if opp["shopcheck_data_id"] not in apr_h_by_id:
            continue
        sev = SEV_MAP.get(opp["deduction_type"], str(opp["deduction_type"]))
        sev_cnt[sev] += 1
        sev_ded[sev] += opp["score_config"] or 0
    emit(f"{'severity':10s} {'cnt':>5s} {'total_deduction':>16s}")
    for s in ["S","M","G","L"]:
        emit(f"{s:10s} {sev_cnt.get(s,0):5d} {sev_ded.get(s,0):16d}")
    other_sev = sum(c for k,c in sev_cnt.items() if k not in {"S","M","G","L"})
    if other_sev:
        emit(f"{'OTHER':10s} {other_sev:5d}")

    # ---- C. April distinct store count ----
    emit("\n--- C. April distinct stores inspected (post-filter) ---")
    apr_depts = {h["dept_id"] for h in apr_headers}
    emit(f"stores_inspected_april = {len(apr_depts)}")

    # ---- D. Same-store cross-type comparisons ----
    emit("\n--- D. Stores with multiple inspection TYPES in April ---")
    by_dept = defaultdict(set)
    for h in apr_headers:
        t_zh, _ = TYPE_MAP[h["large_category_id"]]
        by_dept[h["dept_id"]].add(t_zh)
    multi = [(d, types) for d, types in by_dept.items() if len(types) >= 2]
    multi.sort(key=lambda x: (-len(x[1]), store_code(x[0])))
    emit(f"{'store_code':10s} {'store_name':25s} {'type_variety':12s}  types_seen")
    for d, types in multi:
        emit(f"{store_code(d):10s} {store_name(d)[:25]:25s} {len(types):12d}  {' / '.join(sorted(types))}")
    if not multi:
        emit("(none)")

    # ---- E. Same-day repeats / large score swings ----
    emit("\n--- E. Same-store same-day repeats / large score swings (≥20 pts) ---")
    by_dept_date = defaultdict(list)
    for h in apr_headers:
        rep = REPORT_BY_DATA_ID_APR.get(h["id"])
        score = rep["score"] if rep else None
        by_dept_date[(h["dept_id"], h["check_date"])].append({
            "iid": h["id"], "name": h["checker_name"], "score": score,
            "type": TYPE_MAP[h["large_category_id"]][0]
        })
    flagged = []
    for (dept, date), arr in by_dept_date.items():
        scored = [x["score"] for x in arr if isinstance(x["score"], (int,float))]
        swing = (max(scored) - min(scored)) if len(scored) >= 2 else 0
        if len(arr) >= 2 or swing >= 20:
            flagged.append((dept, date, arr, swing))
    flagged.sort(key=lambda x: (store_code(x[0]), x[1]))
    if flagged:
        emit(f"{'store_code':10s} {'date':12s} {'cnt':>3s} {'swing':>5s}  inspectors / scores")
        for dept, date, arr, swing in flagged:
            insp = " | ".join(f"{x['name']}({x['type']}, score={x['score']})" for x in arr)
            emit(f"{store_code(dept):10s} {date:12s} {len(arr):3d} {swing:5d}  {insp}")
    else:
        emit("(none)")

    # ---- F. Q1+April trend (status=1, post-filter) ----
    emit("\n--- F. Q1+April trend (month × type, status=1 post-filter) ---")
    by_mon_type = defaultdict(lambda: {"cnt":0, "stores":set()})
    for h in HEADERS:
        if h["status"] != 1:
            continue
        if h["check_date"][:7] == "2026-04" and h["id"] in EXCLUDE:
            continue
        ym = h["check_date"][:7]
        if ym not in {"2026-01","2026-02","2026-03","2026-04"}:
            continue
        t_zh, _ = TYPE_MAP[h["large_category_id"]]
        by_mon_type[(ym, t_zh)]["cnt"] += 1
        by_mon_type[(ym, t_zh)]["stores"].add(h["dept_id"])
    emit(f"{'month':10s} {'type':12s} {'cnt':>5s} {'stores':>7s}")
    for ym in ["2026-01","2026-02","2026-03","2026-04"]:
        for t in ["门店自检","QA审计","区经检查"]:
            b = by_mon_type.get((ym, t), {"cnt":0,"stores":set()})
            emit(f"{ym:10s} {t:12s} {b['cnt']:5d} {len(b['stores']):7d}")

    # ---- Special checks ----
    emit("\n" + "="*80)
    emit("SPECIAL CHECKS")
    emit("="*80)
    qa_count = by_t.get("QA审计", {"cnt":0})["cnt"]
    area_count = by_t.get("区经检查", {"cnt":0})["cnt"]
    emit(f"QA审计 count in April = {qa_count}")
    emit(f"区经检查 count in April = {area_count}")

    yj = {ym: 0 for ym in ["2026-01","2026-02","2026-03","2026-04"]}
    ec = dict(yj); dc = dict(yj)
    for h in HEADERS:
        if h["status"] != 1:
            continue
        if h["check_date"][:7] == "2026-04" and h["id"] in EXCLUDE:
            continue
        ym = h["check_date"][:7]
        if ym not in yj: continue
        if h["checker_name"] == "Yu Jiang": yj[ym] += 1
        if h["checker_name"] == "Eamonn Caballar": ec[ym] += 1
        if h["checker_name"] == "Darwin Coronel": dc[ym] += 1
    emit("\nKey inspector workload by month (post-filter):")
    emit(f"  Yu Jiang        : Jan={yj['2026-01']}  Feb={yj['2026-02']}  Mar={yj['2026-03']}  Apr={yj['2026-04']}")
    emit(f"  Eamonn Caballar : Jan={ec['2026-01']}  Feb={ec['2026-02']}  Mar={ec['2026-03']}  Apr={ec['2026-04']}")
    emit(f"  Darwin Coronel  : Jan={dc['2026-01']}  Feb={dc['2026-02']}  Mar={dc['2026-03']}  Apr={dc['2026-04']}")

    # ============================================================
    # REFRESH DELTAS (v2 vs v1)
    # ============================================================
    emit("\n" + "="*80)
    emit("REFRESH DELTAS (v2 live re-pull vs v1 published CSV)")
    emit("="*80)

    prior_summary = load_prior_summary()
    prior_items = load_prior_items()
    cur_summary_by_iid = {r["inspection_id"]: r for r in summary_rows}

    # Score changes
    emit("\n--- Inspection rows with SCORE changes (v1 -> v2) ---")
    score_changes = []
    for iid, prior in prior_summary.items():
        cur = cur_summary_by_iid.get(iid)
        if not cur:
            continue
        prior_score = prior["total_score"]
        cur_score   = str(cur["total_score"])
        if prior_score != cur_score:
            score_changes.append((iid, prior, cur))
    if score_changes:
        emit(f"{'iid':>5s} {'store':10s} {'date':12s} {'inspector':22s} {'v1_score':>8s} -> {'v2_score':>8s}  delta")
        for iid, p, c in sorted(score_changes):
            ps = p["total_score"] or "(blank)"
            cs = str(c["total_score"]) if c["total_score"] != "" else "(blank)"
            try:
                d = int(c["total_score"]) - int(p["total_score"])
                ds = f"{d:+d}"
            except Exception:
                ds = "n/a"
            emit(f"{iid:5d} {p['store_code']:10s} {p['inspection_date']:12s} "
                 f"{p['inspector_name'][:22]:22s} {ps:>8s} -> {cs:>8s}  {ds}")
    else:
        emit("(no score changes)")

    # Item-count changes
    emit("\n--- Inspection rows with ITEM_COUNT changes (v1 -> v2) ---")
    ic_changes = []
    for iid, prior in prior_summary.items():
        cur = cur_summary_by_iid.get(iid)
        if not cur:
            continue
        if str(prior["item_count"]) != str(cur["item_count"]):
            ic_changes.append((iid, prior, cur))
    if ic_changes:
        emit(f"{'iid':>5s} {'store':10s} {'date':12s} {'inspector':22s} v1[S/M/G/L]={{:>11s}}".format("/total") +
             "  v2[S/M/G/L]=/total")
        for iid, p, c in sorted(ic_changes):
            v1 = f"[{p['s_count']}/{p['m_count']}/{p['g_count']}/{p['l_count']}]={p['item_count']}"
            v2 = f"[{c['s_count']}/{c['m_count']}/{c['g_count']}/{c['l_count']}]={c['item_count']}"
            emit(f"{iid:5d} {p['store_code']:10s} {p['inspection_date']:12s} "
                 f"{p['inspector_name'][:22]:22s} {v1:18s}  {v2:18s}")
    else:
        emit("(no item_count changes)")

    # Note on appeal mechanics: appeal approvals at 54th & 8th nullify the
    # deductionScore inside t_shopcheck_report.opportunity_desc JSON (e.g. -5 -> 0)
    # but do NOT remove the t_shopcheck_opportunity row, so item_id stays in items.csv
    # with the canonical score_config. Score changes show up in the SUMMARY total_score
    # / total_deduction columns above.
    emit("\nNOTE on inspection 2040 appeal:")
    emit("  The S item (item_id=9074, 'air gap issue') is STILL PRESENT in items.csv")
    emit("  with severity=S, deduction_points=-5 (the canonical clause default).")
    emit("  The appeal nullified its effective deduction at the REPORT level only:")
    emit("  in t_shopcheck_report.opportunity_desc JSON the deductionScore for type=1")
    emit("  changed from -5 to 0 (count=1 still). Effect: total_score 69 -> 94,")
    emit("  total_deduction -11 -> -6, item_count unchanged at 4.")

    # Item-level changes (item_id removed or severity / deduction_points changed)
    emit("\n--- Deduction items (item_id) REMOVED or CHANGED in severity/deduction_points ---")
    cur_items = {}
    items_path = OUT / "april2026_inspection_items.csv"
    if items_path.exists():
        with items_path.open() as f:
            for r in csv.DictReader(f):
                cur_items[int(r["item_id"])] = r

    item_changes = []
    item_removed = []
    for item_id, prior in prior_items.items():
        cur = cur_items.get(item_id)
        if cur is None:
            item_removed.append(prior)
            continue
        if (prior["severity"] != cur["severity"]
            or str(prior["deduction_points"]) != str(cur["deduction_points"])):
            item_changes.append((item_id, prior, cur))
    if item_removed:
        emit(f"REMOVED ({len(item_removed)}):")
        for p in item_removed[:20]:
            emit(f"  item_id={p['item_id']:>6s}  iid={p['inspection_id']}  "
                 f"store={p['store_code']}  sev={p['severity']}  pts={p['deduction_points']}  "
                 f"clause={p['clause_number']}  reason=row excluded by misubmission filter or DB delete")
        if len(item_removed) > 20:
            emit(f"  ... and {len(item_removed)-20} more")
    else:
        emit("(no item_id removed)")
    if item_changes:
        emit(f"\nCHANGED ({len(item_changes)}):")
        for iid, p, c in item_changes:
            emit(f"  item_id={iid}  iid={p['inspection_id']}  store={p['store_code']}  "
                 f"v1: sev={p['severity']} pts={p['deduction_points']}  ->  "
                 f"v2: sev={c['severity']} pts={c['deduction_points']}")
    else:
        emit("(no item severity/deduction_points changes)")

    # Newly-added inspections (v2 has, v1 didn't)
    new_iids = sorted(set(cur_summary_by_iid) - set(prior_summary))
    if new_iids:
        emit(f"\n--- NEW inspection rows in v2 ({len(new_iids)}) ---")
        for iid in new_iids:
            c = cur_summary_by_iid[iid]
            emit(f"  iid={iid}  store={c['store_code']}  date={c['inspection_date']}  "
                 f"inspector={c['inspector_name']}  type={c['inspection_type']}  "
                 f"score={c['total_score']}  items={c['item_count']}")
    else:
        emit("\n(no new inspection rows)")

    # Rows in v1 but not in v2 (beyond the misubmission filter — status downgrades, DB deletes, etc.)
    dropped = sorted(set(prior_summary) - set(cur_summary_by_iid) - set(EXCLUDE))
    if dropped:
        emit(f"\n--- INSPECTION ROWS IN V1 BUT NOT IN V2 ({len(dropped)}) ---")
        emit("(These are NOT misubmission excludes — they were dropped because"
             " status is no longer 1, or the row was deleted in DB)")
        for iid in dropped:
            p = prior_summary[iid]
            h = HEADER_BY_ID.get(iid)
            reason = "no longer in DB"
            if h:
                if h["status"] != 1:
                    reason = f"status={h['status']} (not submitted)"
                else:
                    reason = "passes filter — investigate"
            emit(f"  iid={iid}  store={p['store_code']}  date={p['inspection_date']}  "
                 f"inspector={p['inspector_name']}  v1_score={p['total_score'] or '(blank)'}  "
                 f"v1_items={p['item_count']}  reason={reason}")
    else:
        emit("\n(no v1-only inspection rows)")

    # Excluded by misubmission rule
    emit(f"\n--- Inspection rows EXCLUDED by misubmission rule ({len(EXCLUDE)}) ---")
    for iid, info in sorted(EXCLUDE.items()):
        emit(f"  iid={iid}  inspector={info['inspector']}  store={info['store_code']}  "
             f"date={info['date']}  "
             f"reason=score=100 AND item_count=0 AND sibling(s) {info['siblings']} have items")

    # Refreshed totals
    emit("\n--- REFRESHED TOTALS (status=1, post-filter) ---")
    emit("April 2026 by type:")
    for t in ["门店自检","QA审计","区经检查"]:
        b = by_t.get(t, {"cnt":0,"stores":set()})
        emit(f"  {t:10s} : {b['cnt']:>3d} inspections, {len(b['stores']):>2d} distinct stores")
    apr_total = sum(b['cnt'] for b in by_t.values())
    emit(f"  TOTAL    : {apr_total:>3d}")

    emit("\nAll months (Jan-Apr 2026) by type:")
    for ym in ["2026-01","2026-02","2026-03","2026-04"]:
        emit(f"  {ym}:")
        m_total = 0
        for t in ["门店自检","QA审计","区经检查"]:
            b = by_mon_type.get((ym,t), {"cnt":0,"stores":set()})
            emit(f"    {t:10s} : {b['cnt']:>3d} inspections, {len(b['stores']):>2d} stores")
            m_total += b["cnt"]
        emit(f"    TOTAL    : {m_total:>3d}")

    (OUT / "april2026_validation_output.txt").write_text("\n".join(out_lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    summary_rows = build_summary_rows()
    summary_n, summary_p = write_summary(summary_rows)
    items_n,   items_p   = write_items(set(EXCLUDE))
    stores_n,  stores_p  = write_store_master()
    insp_n,    insp_p    = write_inspector_trend()
    trend_n,   trend_p   = write_trend_summary()
    schema_p             = write_schema_notes()

    print()
    print(f"WROTE {summary_n} rows -> {summary_p}")
    print(f"WROTE {items_n} rows -> {items_p}")
    print(f"WROTE {stores_n} rows -> {stores_p}")
    print(f"WROTE {insp_n} rows -> {insp_p}")
    print(f"WROTE {trend_n} rows -> {trend_p}")
    print(f"WROTE schema notes  -> {schema_p}")
    print()
    run_validations(summary_rows)
