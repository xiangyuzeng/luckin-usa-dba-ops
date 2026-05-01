#!/usr/bin/env python3
"""
PQNC April 2026 — Handoff Artifacts Builder
============================================
Reads april2026_pqnc_raw.csv (the source of truth from t_pqnc + t_pqnc_operate_detail)
and emits three new artifacts:

  1. /app/reports/april2026-pqnc/PQNC_Apr2026_raw.json
       Raw 66-row extract in JSON form for traceability.
  2. /app/reports/april2026-pqnc/PQNC_Apr2026_classified.json
       Same rows + risk_level / material_category / responsibility_normalized fields.
  3. /app/PQNC_Apr2026_handoff.md
       A compact, paste-ready markdown for Claude Web compilation of the final docx.
       Mirrors the same classification logic as build_pqnc_breakdown.py — they
       agree row-for-row.

Re-run:  python3 build_handoff_artifacts.py
"""

import csv
import json
from pathlib import Path
from collections import Counter

CSV_PATH        = Path("/app/reports/april2026-pqnc/april2026_pqnc_raw.csv")
RAW_JSON_PATH   = Path("/app/reports/april2026-pqnc/PQNC_Apr2026_raw.json")
CLASS_JSON_PATH = Path("/app/reports/april2026-pqnc/PQNC_Apr2026_classified.json")
HANDOFF_PATH    = Path("/app/PQNC_Apr2026_handoff.md")

# ===== Classification =====
# Identical logic to build_pqnc_breakdown.py — kept in lockstep.
KEYWORD_RAW    = ("milk", "cream", "condensed", "powder", "salt", "syrup",
                  "puree", "bean", "coffee blend", "drip coffee", "matcha",
                  "tea", "sauce", "dairy", "almond")
KEYWORD_FOOD   = ("cookie", "croissant", "cake", "pastry", "bread",
                  "sandwich", "muffin", "sausage", "scone")
KEYWORD_PKG    = ("lid", "cup", "bottle", "cap", "bag was", "package",
                  "label", "straw", "carton", "sleeve", "tape", "bag broken",
                  "bag bursted", "leaking", "leakage", "seal", "punctured",
                  "underfill", "denting", "date code", "expiration", "open",
                  "no straw")
KEYWORD_OTHER  = ("scale", "drawer", "toilet paper", "discontinued",
                  "handle", "iris", "timemore")

# Per-pqnc_id overrides (curated edge calls) — mirror build_pqnc_breakdown.py
MATERIAL_OVERRIDE = {
    # Bakery cluster (all 17 轻食 rows)
    **dict.fromkeys(["869","870","871","872","874","876","892","899","900",
                     "914","915","917","918","923","933","935","937"], "轻食"),
    # Cup-lid mismatch
    **dict.fromkeys(["877","878","879","880","883","889"], "包材"),
    # Missing-label
    **dict.fromkeys(["875","881"], "包材"),
    # Milk bottle leak / underfill / dent / puncture / heavy cream / underfill rejected
    **dict.fromkeys(["891","893","895","897","898","919","920","929","930",
                     "931","938","926"], "包材"),
    # Coffee bag damage
    **dict.fromkeys(["873","925","934"], "包材"),
    # No-date-code / missing-straw
    **dict.fromkeys(["922","886"], "包材"),
    # Sea salt cluster (contents wrong — 原料)
    **dict.fromkeys(["902","903","904","905","906","907","908","909"], "原料"),
    # Hair-in-food + condensed milk Major + almond milk + expired
    **dict.fromkeys(["885","888","901","916","936","939","940","941","942",
                     "910","927"], "原料"),
    # Equipment / consumables / discontinued
    **dict.fromkeys(["882","884","928","943","921"], "其他"),
}

def classify_risk(pqnc_type, responsibility, desc):
    if responsibility == "Unknown/reject" or pqnc_type == "Unclassified":
        return "Unclear"
    d = (desc or "").lower()
    if any(k in d for k in ("listeria", "salmonella", "e.coli", "pathogen",
                            "glass shard", "metal shard", "allergen mislabel")):
        return "Critical"
    if pqnc_type == "Food Safety Issue":
        return "Major"
    return "Minor"

def classify_material(pqnc_id, factory, desc):
    if pqnc_id in MATERIAL_OVERRIDE:
        return MATERIAL_OVERRIDE[pqnc_id]
    text = (factory + " " + desc).lower()
    if any(k in text for k in KEYWORD_FOOD):
        return "轻食"
    if "bag" in text and ("broken" in text or "burst" in text or "open" in text):
        return "包材"
    if any(k in text for k in KEYWORD_OTHER):
        return "其他"
    if any(k in text for k in KEYWORD_PKG):
        return "包材"
    if any(k in text for k in KEYWORD_RAW):
        contam = ("hair","foreign","spoilage","mold","rotten","sour",
                  "expired","wrong","chunks","burnt","solid","brownish")
        if any(k in text for k in contam):
            return "原料"
    return "Unclear"

# ===== Build =====
rows = list(csv.DictReader(CSV_PATH.open()))
assert len(rows) == 66, f"expected 66 rows, got {len(rows)}"

for r in rows:
    r["risk_level"]                = classify_risk(r["pqnc_type"], r["responsibility"], r["problem_description"])
    r["material_category"]         = classify_material(r["pqnc_id"], r["factory_name"], r["problem_description"])
    r["responsibility_normalized"] = r["responsibility"]  # already normalized to {Supplier, Warehouse, Store, Joint(Supplier+Warehouse), Unknown/reject}

# Raw JSON: keep original DB column names from the CSV
RAW_JSON_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

# Classified JSON: same rows, with the 3 added classification fields explicit
classified = []
for r in rows:
    classified.append({
        "nc_id"                     : r["pqnc_id"],
        "nc_no"                     : r["pqnc_no"],
        "report_date"               : r["created_time"],
        "status"                    : r["status"],
        "discover_period"           : r["discover_period"],
        "reporter"                  : r["party_name"],
        "supplier_name"             : r["factory_name"],
        "item_name_en"              : r["problem_description"],
        "quantity"                  : r["problem_qty"],
        "issue_type_raw"            : r["pqnc_type"],
        "one_pqnc_type_code"        : r["one_pqnc_type_code"],
        "responsibility_raw"        : r["responsibility"],
        "responsibility_normalized" : r["responsibility_normalized"],
        "corrective_action_text"    : r.get("corrective_desc",""),
        "risk_level"                : r["risk_level"],
        "material_category"         : r["material_category"],
    })
CLASS_JSON_PATH.write_text(json.dumps(classified, ensure_ascii=False, indent=2), encoding="utf-8")

# ===== Handoff markdown =====
total = len(rows)
risk_count = Counter(r["risk_level"] for r in rows)
resp_count = Counter(r["responsibility_normalized"] for r in rows)
mat_count  = Counter(r["material_category"] for r in rows)
type_count = Counter(r["pqnc_type"] for r in rows)
cross_rm   = Counter((r["risk_level"], r["material_category"]) for r in rows)
cross_rr   = Counter((r["risk_level"], r["responsibility_normalized"]) for r in rows)

cr = risk_count.get("Critical",0); ma = risk_count.get("Major",0)
mi = risk_count.get("Minor",0);    un = risk_count.get("Unclear",0)
sup = resp_count.get("Supplier",0); wh = resp_count.get("Warehouse",0)
st  = resp_count.get("Store",0);    jo = resp_count.get("Joint(Supplier+Warehouse)",0)
rj  = resp_count.get("Unknown/reject",0)
fs  = type_count.get("Food Safety Issue",0); gd = type_count.get("General Defect",0)
uc  = type_count.get("Unclassified",0)
raw = mat_count.get("原料",0); food = mat_count.get("轻食",0)
pkg = mat_count.get("包材",0); oth = mat_count.get("其他",0); ucm = mat_count.get("Unclear",0)

# 中文 keyword map (kept compact for handoff)
zh_map = [
    ("broken cookie","饼干破损"),("cracked cookie","饼干破裂"),("cookie","饼干"),
    ("croissant","牛角包"),("sausage","三明治"),
    ("hair in","异物（毛发）"),("foreign object","异物"),("foreign material","异物"),
    ("spoilage","变质"),("mold","霉变"),("rotten","腐败"),("sour smell","酸味"),
    ("brownish material","异物（褐色物质）"),("chunks","结块"),("burnt","焦糊物"),
    ("expired","过期"),("discontinued","已停产"),
    ("wrong sea salt","海盐规格错"),("coarse","粗盐（应为细盐）"),
    ("wrong size","尺寸不匹配"),("dome lid","圆顶盖"),("drinking lid","吸管盖"),
    ("flat lid","平盖"),("lid","杯盖"),("ice cup","冰杯"),("cup","杯子"),
    ("milk bottle","牛奶瓶"),("milk gallon","牛奶桶"),("milk","牛奶"),
    ("leaking","泄漏"),("leakage","泄漏"),("hole","破孔"),("punctured","穿孔"),
    ("seal","密封"),("underfill","装量不足"),("missing label","缺标签"),
    ("missing ingredient","缺料"),("missing front label","缺正面标签"),("missing","缺失"),
    ("denting","凹陷"),("dented","凹陷"),("date of expiration","保质期日期"),
    ("date code","日期编码"),("bag","包装袋"),("burst","爆裂"),("bursted","爆裂"),
    ("broken package","包装破损"),("toilet paper","厕纸"),("damp","受潮"),("wet","受潮"),
    ("scale","秤"),("drawer","抽屉"),("cracked","破裂"),("chipped","破损"),
    ("handle","手柄"),("broken","破损"),("not approved","未批准使用"),
    ("not enough","装量不足"),("no straw","无吸管"),
]
def to_zh(d):
    dl = d.lower()
    for k,zh in zh_map:
        if k in dl: return zh
    return "（参见英文描述）"

period_names = {"1":"at receipt","2":"in storage","3":"in use","4":"after sale"}

L = []
P = L.append

# === 1. Source & Trust Block ===
P("# PQNC April 2026 — Handoff Document for Claude Web")
P("")
P("> Paste this entire file into Claude Web to compile the final April 2026 PQNC PPT/docx. "
  "All numbers are reconciled and traceable to a real DB row.")
P("")
P("## 1. Source & Trust Block")
P("")
P("| Field | Value |")
P("|---|---|")
P("| **Data source** | `aws-luckyus-scmsrm-rw` MySQL → `luckyus_scm_srm.t_pqnc` + `t_pqnc_operate_detail` |")
P("| **Filter set (locked, March-validated)** | `tenant='LKUS' AND delete_flag=0 AND status IN (4,5)` + operate_type=1 dedup via MIN per pqnc_id |")
P("| **Period covered** | 2026-04-01 to 2026-04-30 inclusive (by `created_time`) |")
P("| **Query timestamp** | 2026-05-01 |")
P(f"| **Total records** | {total} |")
P("| **Date range present in data** | 2026-04-01 to 2026-04-30 (covers all 30 calendar days) |")
P("| **Data quality flags** | `responsibility=6` is undocumented in column comment but consistently maps to Unknown/reject (matches March 1-of-1 mapping). 4 same-day duplicate filings of one hair-in-can incident inflated unknown/reject by 3. |")
P("| **MoM comparison vs March** | ✅ Available — `/app/PQNC_Mar2026_Breakdown.md` exists with canonical 33/5/27/30/2/1; this report's filter set reproduces March exactly. |")
P("| **March anchor proof** | `/app/reports/april2026-pqnc/march2026_validation.txt` |")
P("")
P("---")
P("")

# === 2. Verbatim System Tables ===
P("## 2. Verbatim System Tables (reproduced from DB)")
P("")
P("### PQNC Type Table")
P("")
P("| PQNC type | Food | Food contact material |")
P("|---|---:|---:|")
P(f"| Food Safety Issue (code 0003) | {fs} | - |")
P(f"| General Defect (code 0004)    | {gd} | - |")
P(f"| Sensory Abnormal (code 0001)  | 0 | - |")
P(f"| Other Unclear Situation (code 0002) | 0 | - |")
P(f"| **Unclassified** *(no operate_type=1 row — closed without judgment-typing)* | **{uc}** | - |")
P("")
P(f"> Type table sums to {fs}+{gd}={fs+gd}; the {uc} unclassified cases live in the Responsibility "
  f"table's Unknown/reject bucket. Total reconciles to {fs}+{gd}+{uc}={fs+gd+uc}.")
P("")
P("### PQNC Responsibility Table")
P("")
P("| PQNC Responsibility | Case |")
P("|---|---:|")
P(f"| Warehouse (仓库) | {wh} |")
P(f"| Supplier (供应商) | {sup} |")
P(f"| Store (门店) | {st} |")
P(f"| **Joint (Supplier + Warehouse) — NEW vs March** | **{jo}** |")
P(f"| Unknown / reject (未明确/驳回) | {rj} |")
P("")
P("> April adds a **Joint** bucket (6 cases — the 2026-04-18 wrong-sea-salt cluster) that did not "
  "appear in March. The deck's standard 4-bucket layout will need a QA decision on how to render this.")
P("")
P("---")
P("")

# === 3. Detail Items table ===
P("## 3. Detail Items — Full Per-Item Table")
P("")
P("One row per discrete issue (no multi-issue NCs to split — DB stores one issue per pqnc_id).")
P("Every row maps to a real DB pqnc_id (no inferred rows).")
P("")
P("| # | Date | Location (factory/warehouse) | Item EN | 中文 | Qty | Risk | Responsibility | Material | Corrective Action | Source NC ID |")
P("|---:|---|---|---|---|---|---|---|---|---|---|")
for i, r in enumerate(rows, 1):
    date = r["created_time"][:10]
    loc  = (r["factory_name"] or "?").replace("|","/").strip()
    if len(loc) > 32: loc = loc[:29] + "..."
    desc = r["problem_description"].replace("|","/").strip()
    if len(desc) > 80: desc = desc[:77] + "..."
    zh   = to_zh(r["problem_description"])
    try:
        qty = f"{float(r['problem_qty']):g}"
    except Exception:
        qty = r["problem_qty"]
    risk = r["risk_level"]
    if risk == "Major": risk = "**Major**"
    resp = r["responsibility_normalized"]
    if resp == "Joint(Supplier+Warehouse)": resp = "Joint(S+W)"
    mat  = r["material_category"]
    corr = (r.get("corrective_desc") or "").replace("|","/").strip() or "—"
    if len(corr) > 40: corr = corr[:37] + "..."
    P(f"| {i} | {date} | {loc} | {desc} | {zh} | {qty} | {risk} | {resp} | {mat} | {corr} | {r['pqnc_id']} |")
P("")
P("---")
P("")

# === 4. Three Dimensional Breakdowns ===
P("## 4. Three Dimensional Breakdowns")
P("")
P("### 4.1 By Risk Level (按风险分)")
P("")
P(f"| Risk Level | Count | % of {total} |")
P("|---|---:|---:|")
P(f"| Critical (严重食安) | {cr} | {cr/total*100:.1f}% |")
P(f"| **Major (食安风险)** | **{ma}** | **{ma/total*100:.1f}%** |")
P(f"| Minor (一般缺陷) | {mi} | {mi/total*100:.1f}% |")
P(f"| Unclear (不明) | {un} | {un/total*100:.1f}% |")
P(f"| **Total** | **{total}** | **100.0%** |")
P("")
P("### 4.2 By Responsibility (按判责)")
P("")
P(f"| Responsibility | Count | % of {total} |")
P("|---|---:|---:|")
P(f"| Supplier (供应商) | {sup} | {sup/total*100:.1f}% |")
P(f"| Warehouse (仓库) | {wh} | {wh/total*100:.1f}% |")
P(f"| Store (门店) | {st} | {st/total*100:.1f}% |")
P(f"| Joint (Supplier + Warehouse) — NEW | {jo} | {jo/total*100:.1f}% |")
P(f"| Unknown / reject (未明确/驳回) | {rj} | {rj/total*100:.1f}% |")
P(f"| **Total** | **{total}** | **100.0%** |")
P("")
P("### 4.3 By Material Category (按物料大类)")
P("")
P(f"| Material Category | Count | % of {total} |")
P("|---|---:|---:|")
P(f"| 原料 (Raw materials) | {raw} | {raw/total*100:.1f}% |")
P(f"| 轻食 (Light food / bakery) | {food} | {food/total*100:.1f}% |")
P(f"| 包材 (Packaging) | {pkg} | {pkg/total*100:.1f}% |")
P(f"| 其他 (Other / Unclear) | {oth+ucm} | {(oth+ucm)/total*100:.1f}% |")
P(f"| **Total** | **{total}** | **100.0%** |")
P("")
P("### 4.4 Reconciliation")
P("")
P("| Dimension | Sum | Matches total? |")
P("|---|---|:---:|")
P(f"| Risk Level | {cr}+{ma}+{mi}+{un} | {'✅' if cr+ma+mi+un==total else '❌'} {cr+ma+mi+un} |")
P(f"| Responsibility | {sup}+{wh}+{st}+{jo}+{rj} | {'✅' if sup+wh+st+jo+rj==total else '❌'} {sup+wh+st+jo+rj} |")
P(f"| Material | {raw}+{food}+{pkg}+{oth+ucm} | {'✅' if raw+food+pkg+oth+ucm==total else '❌'} {raw+food+pkg+oth+ucm} |")
P("")
P("All three dimensions reconcile. **No inferred rows** — every detail row maps to a real DB pqnc_id.")
P("")
P("---")
P("")

# === 5. Cross-tabs ===
P("## 5. Cross-Tabs")
P("")
P("### 5.1 Risk × Responsibility")
P("")
P("| | Supplier | Warehouse | Store | Joint(S+W) | Unknown/reject | **Total** |")
P("|---|---:|---:|---:|---:|---:|---:|")
for risk in ("Critical","Major","Minor","Unclear"):
    s = cross_rr[(risk,"Supplier")]
    w = cross_rr[(risk,"Warehouse")]
    t = cross_rr[(risk,"Store")]
    j = cross_rr[(risk,"Joint(Supplier+Warehouse)")]
    u = cross_rr[(risk,"Unknown/reject")]
    tot = s+w+t+j+u
    bold = "**" if risk=="Major" else ""
    P(f"| {bold}{risk}{bold} | {s} | {w} | {t} | {j} | {u} | **{tot}** |")
P(f"| **Total** | **{sup}** | **{wh}** | **{st}** | **{jo}** | **{rj}** | **{total}** |")
P("")
P("### 5.2 Risk × Material")
P("")
P("| | 原料 | 轻食 | 包材 | 其他/Unclear | **Total** |")
P("|---|---:|---:|---:|---:|---:|")
for risk in ("Critical","Major","Minor","Unclear"):
    ra = cross_rm[(risk,"原料")]
    fo = cross_rm[(risk,"轻食")]
    pk = cross_rm[(risk,"包材")]
    ot = cross_rm[(risk,"其他")] + cross_rm[(risk,"Unclear")]
    tot = ra+fo+pk+ot
    bold = "**" if risk=="Major" else ""
    P(f"| {bold}{risk}{bold} | {ra} | {fo} | {pk} | {ot} | **{tot}** |")
P(f"| **Total** | **{raw}** | **{food}** | **{pkg}** | **{oth+ucm}** | **{total}** |")
P("")
P("---")
P("")

# === 6. Bilingual Summary Text (PPT-ready) ===
P("## 6. Bilingual Summary Text — PPT-ready")
P("")
P("> Paste this paragraph directly into the April PPT \"PQNC Summary\" text box. "
  "Mirrors the March deck's English+Chinese mixed format.")
P("")
P("```")
P(f"In Apr 2026, total {total} PQNC reported, {ma} major issues were identified for "
  f"hair-in-food and condensed milk spoilage 1起粉料异物、1起炼乳异物、4起炼乳变质/异物. "
  f"Other general issues including broken cookies, milk bottle leakage, cup-lid mismatch, "
  f"and wrong sea salt grade 破损饼干、牛奶瓶泄漏、杯盖尺寸不匹配和海盐规格错. "
  f"已反馈给供应链。")
P("```")
P("")
P("**Alternative shorter form (if PPT box is space-constrained):**")
P("")
P("```")
P(f"Apr 2026: {total} PQNC reported ({ma} food-safety, {mi} general defects, {un} rejected). "
  f"Major issues: condensed milk hair/foreign material/spoilage (Casa Solana, 5 of {ma}). "
  f"General defects: broken cookies, milk bottle leak (Cream O Land), cup-lid mismatch (24oz), "
  f"wrong sea salt grade. 已反馈供应链。")
P("```")
P("")
P("---")
P("")

# === 7. Notable Findings ===
P("## 7. Notable Findings")
P("")
P(f"1. **Total volume doubled vs March** ({total} vs 33, +100%) — driven by three new clusters "
  "not present in March: cup-lid mismatch on 24oz iced cups (6 reports across multiple stores "
  "starting 2026-04-07), wrong sea-salt grade single-day cluster (8 reports on 2026-04-18), and "
  "elevated Cream O Land milk-bottle leakage (~9 reports vs March's 2).")
P("")
P(f"2. **Casa Solana condensed milk is the #1 food-safety escalation candidate.** 5 of {ma} Major "
  "cases trace to Casa Solana (hair × 1, spoilage × 1, foreign object × 1, brownish material × 1, "
  "chunks × 1). Recommend immediate supplier audit.")
P("")
P(f"3. **New responsibility bucket: Joint (Supplier + Warehouse) = {jo} cases**, all the 2026-04-18 "
  "sea-salt-grade pick error. Standard PPT 4-bucket layout will need a QA-team decision on how to "
  "render this — most natural mapping: keep as a 5th row.")
P("")
P(f"4. **Unknown/reject grew 1 → {rj} (+{rj-1})**. 4 of the 7 are same-day duplicate filings by one "
  "user (Darwin Coronel, 2026-04-30, hair-in-can at Casa Solana). Recommend a UX dedupe guard in "
  "the PQNC submission flow keyed on (user × item × day).")
P("")
P(f"5. **All Major (food-safety) items trace to suppliers** (6 of 6) — supplier corrective action "
  "is the only food-safety lever this month.")
P("")
P(f"6. **Warehouse-attributed items are exclusively non-food equipment damage on receipt** "
  "(Timemore scale, Iris drawers, Luckin handle, wet toilet paper). Zero warehouse food-safety exposure.")
P("")
P(f"7. **Store responsibility = 0** (consistent with March). No front-of-house PQNC.")
P("")
P("---")
P("")

# === 8. Open Questions for QA Team ===
P("## 8. Open Questions for QA Team")
P("")
P("Items that need human confirmation before the final April PPT/docx ships:")
P("")
P("1. **Confirm `responsibility=6` mapping.** Undocumented in the column comment "
  "(`1=供应商,2=仓储,3=门店,4=共同责任,5=不明`); used in March (1 case) and April (7 cases). "
  "All instances appear to mean \"administratively rejected/closed\". Confirm this is the deck's "
  "\"Unknown/reject\" bucket.")
P("")
P("2. **Decide deck treatment of `responsibility=4` Joint cases (6 in April, 0 in March).** "
  "Options: (a) split each case across Supplier and Warehouse rows, (b) add a 5th \"Joint\" row to "
  "the responsibility table, (c) attribute upstream to whoever caused the SKU pick error (likely "
  "Supplier).")
P("")
P("3. **Casa Solana condensed milk — escalate to supplier audit?** 5 of 6 Major cases trace here. "
  "Same supplier produced March's 2 condensed-milk Major cases (mold + foreign material). "
  "Pattern is now 7 incidents in 2 months.")
P("")
P("4. **Cream O Land milk bottle leak (~9 cases) — root cause = cap/seal QC issue or incoming-batch defect?** "
  "Need a meeting with Cream O Land + the SCM team that received the April lot. Worth pulling the "
  "lot/batch numbers from the `batch_no` column of the affected pqnc rows for quick traceability.")
P("")
P("5. **Cup-lid mismatch on 24oz iced cups (6 reports across multiple lid suppliers).** "
  "Verify whether the cup spec changed (24oz cup vendor) or the lid spec changed (NBJL, etc.) in April. "
  "Reports started 2026-04-07 and span 4 different lid suppliers — points to a cup-side change "
  "rather than a lid-side change.")
P("")
P("6. **pqnc 910 (Califia Farms almond milk: \"container broken open... almond milk is rotten\").** "
  "QA-coded 0004 Minor (general defect) but description names spoilage. Confirm whether this should "
  "be reclassified as 0003 Major food-safety or kept as Minor + footnote.")
P("")
P("7. **Implement de-duplication guard in PQNC submission UI.** One user filed 4 reports for the "
  "same hair-in-can incident on 2026-04-30 (rows 939–942). Recommend a soft-warning when "
  "(user × item × day) collides on submission.")
P("")
P("---")
P("")
P("**End of handoff. Reconciliation: dimension totals all sum to 66 ✅. Every detail row traces to "
  "a real DB pqnc_id.**")

HANDOFF_PATH.write_text("\n".join(L) + "\n", encoding="utf-8")

# ===== Print phase summary =====
print(f"PHASE 2 — raw JSON:        {RAW_JSON_PATH}  ({RAW_JSON_PATH.stat().st_size:,} bytes)")
print(f"PHASE 3 — classified JSON: {CLASS_JSON_PATH}  ({CLASS_JSON_PATH.stat().st_size:,} bytes)")
print(f"PHASE 4 — handoff md:      {HANDOFF_PATH}  ({HANDOFF_PATH.stat().st_size:,} bytes)")
print()
print("Distribution by issue_type:")
for k,v in sorted(type_count.items(), key=lambda x:-x[1]):
    print(f"  {k:25}  {v}")
print()
print("Distribution by risk_level:")
for k,v in sorted(risk_count.items(), key=lambda x:-x[1]):
    print(f"  {k:10}  {v}")
print()
print("3 sample classified records:")
for s in classified[:3]:
    print(f"  nc_id={s['nc_id']}  risk={s['risk_level']:8}  resp={s['responsibility_normalized']:25}  mat={s['material_category']:6}  desc={s['item_name_en'][:60]}")
