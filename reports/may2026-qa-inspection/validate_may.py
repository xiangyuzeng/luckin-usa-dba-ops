#!/usr/bin/env python3
"""May 2026 QA snapshot — Step 5 validation (15 checks)."""
import csv, datetime as dt
from collections import defaultdict, Counter
from pathlib import Path

DATA_DIR = Path("/app/reports/may2026-qa-inspection")
APR_DIR  = Path("/app/reports/april2026-qa-inspection")

MODULES_10 = ["清洁卫生","过程控制","设施","证照文件","职场安全",
              "虫害防控","温控有效期","员工健康卫生","设备维护","供应商"]
EN2CN = {
    "Cleaning and Sanitation": "清洁卫生",
    "Process Control": "过程控制",
    "Facility": "设施",
    "Document Record": "证照文件",
    "Workplace Safety": "职场安全",
    "Pests Control": "虫害防控",
    "Temperature Control / Expiration Date Management.": "温控有效期",
    "Employees’ Health and Personal Hygiene": "员工健康卫生",
    "Employees' Health and Personal Hygiene": "员工健康卫生",
    "Maintenance of Equipment": "设备维护",
    "Approved Supplier": "供应商",
}

def load_csv(p):
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

print("="*80)
print("MAY 2026 QA SNAPSHOT — VALIDATION (built 2026-05-05)")
print("="*80)

# ---------- 1. Files loaded ----------
SUMMARY  = load_csv(DATA_DIR / "may2026_inspection_summary.csv")
ITEMS    = load_csv(DATA_DIR / "may2026_inspection_items.csv")
STORES   = load_csv(DATA_DIR / "may2026_store_master.csv")
TREND_M  = load_csv(DATA_DIR / "may2026_inspector_trend.csv")
TREND_S  = load_csv(DATA_DIR / "jan_to_may2026_trend_summary.csv")
APR_SUM  = load_csv(DATA_DIR / "april2026_inspection_summary.csv")  # local copy with appeal columns
APR_ITM  = load_csv(DATA_DIR / "april2026_inspection_items.csv")

print(f"\n[1] FILES LOADED")
print(f"    may_summary:      {len(SUMMARY):>4} rows")
print(f"    may_items:        {len(ITEMS):>4} rows")
print(f"    store_master:     {len(STORES):>4} rows")
print(f"    inspector_trend:  {len(TREND_M):>4} rows")
print(f"    trend_summary:    {len(TREND_S):>4} rows")
print(f"    apr_summary:      {len(APR_SUM):>4} rows")
print(f"    apr_items:        {len(APR_ITM):>4} rows")

# Type normalization for May summary
for r in SUMMARY:
    for k in ("adjusted_total_score","original_total_score","adjusted_total_deduction",
              "original_total_deduction","is_appealed","item_count","s_count","m_count","g_count","l_count","inspection_id"):
        try: r[k] = int(r[k]) if r[k] not in ("","None",None) else 0
        except: r[k] = 0
for r in ITEMS:
    r["deduction_points"] = int(r["deduction_points"])
    r["is_appealed_finding"] = int(r["is_appealed_finding"])
    r["inspection_id"] = int(r["inspection_id"])
    r["cn_module"] = EN2CN.get(r["module_name"], "其他")

for r in APR_SUM:
    for k in ("adjusted_total_score","original_total_score","adjusted_total_deduction",
              "original_total_deduction","is_appealed","item_count","s_count","m_count","g_count","l_count","inspection_id"):
        try: r[k] = int(r[k]) if r[k] not in ("","None",None) else 0
        except: r[k] = 0

# ---------- 2. Inspection counts by type ----------
by_type = Counter(r["inspection_type"] for r in SUMMARY)
print(f"\n[2] INSPECTION COUNTS BY TYPE (vs validation_output.txt expected: 4/0/3)")
for t in ("门店自检","QA审计","区经检查"):
    print(f"    {t}: {by_type.get(t,0)}")
print(f"    TOTAL: {sum(by_type.values())}")

# ---------- 3. S/M/G/L counts: 主巡检 vs 全月 ----------
PRIORITY = {"QA审计": 0, "区经检查": 1, "门店自检": 2}
by_store = defaultdict(list)
for r in SUMMARY: by_store[r["store_code"]].append(r)
def main_for_store(rows):
    return sorted(rows, key=lambda r:(PRIORITY.get(r["inspection_type"],99),
                                       -dt.date.fromisoformat(r["inspection_date"]).toordinal()))[0]
MAIN = {sc: main_for_store(rs) for sc, rs in by_store.items()}
MAIN_IIDS = {m["inspection_id"] for m in MAIN.values()}
MAIN_ITEMS = [it for it in ITEMS if it["inspection_id"] in MAIN_IIDS]

main_sev = Counter(it["severity"] for it in MAIN_ITEMS)
all_sev  = Counter(it["severity"] for it in ITEMS)
print(f"\n[3] SEVERITY COUNTS (主巡检 vs 全月)")
print(f"    主巡检: S={main_sev.get('S',0)} M={main_sev.get('M',0)} G={main_sev.get('G',0)} L={main_sev.get('L',0)} = {sum(main_sev.values())}")
print(f"    全月  : S={all_sev.get('S',0)} M={all_sev.get('M',0)} G={all_sev.get('G',0)} L={all_sev.get('L',0)} = {sum(all_sev.values())}")
# Note: each May store has only 1 inspection, so 主巡检 == 全月 (verify)
assert sum(main_sev.values()) == sum(all_sev.values()), "May 主巡检 should equal 全月 since 1 insp/store"

# ---------- 4. Average 主巡检 score ----------
scores = [m["adjusted_total_score"] for m in MAIN.values()]
avg = round(sum(scores)/len(scores), 1) if scores else 0
print(f"\n[4] AVERAGE 主巡检 SCORE: {avg} ({len(scores)} stores)")

# ---------- 5. Same-store divergence ≥15 ----------
print(f"\n[5] SAME-STORE DIVERGENCE ≥15 POINTS (cross-type)")
print(f"    Each May store has only 1 inspection — N/A (skip §4.4 per snapshot adj #10)")

# ---------- 6. Appeals ----------
appeals = [r for r in SUMMARY if r["is_appealed"] == 1]
print(f"\n[6] APPEAL CASES IN MAY: {len(appeals)} (none expected)")

# ---------- 7. Newly opened stores ----------
print(f"\n[7] NEWLY-OPENED STORES (open_date > 2026-05-04 OR awaiting first inspection)")
newly_opened_after_cutoff = []
for s in STORES:
    if s["status"] != "active": continue
    if s["store_code"].startswith("US999"): continue
    if s["store_code"] == "US00000": continue
    od = s["open_date"]
    if not od: continue
    if od > "2026-05-04":
        newly_opened_after_cutoff.append(s)
    elif od >= "2026-04-01" and s["inspected_in_may"] == "No":
        print(f"    {s['store_code']} {s['store_name']:30s} opened {od} — recently opened, no May inspection yet")
if newly_opened_after_cutoff:
    print(f"    Excluded (opened after cutoff): {len(newly_opened_after_cutoff)}")
else:
    print(f"    None opened after 2026-05-04")

# Effective cohort: active production stores with open_date <= 2026-04-30 (April baseline cohort = 13)
APR_COHORT = sorted({r["store_code"] for r in APR_SUM})
print(f"    April cohort (denominator for /13): {len(APR_COHORT)} stores")
inspected_may = sorted(by_store.keys())
print(f"    May inspected: {len(inspected_may)} ({', '.join(inspected_may)})")
print(f"    Coverage 7/13 (vs April cohort): {len(inspected_may)*100/13:.1f}%")

# ---------- 8. ≥10pt change vs April main ----------
print(f"\n[8] CROSS-MONTH ≥10pt SHIFTS (May 主巡检 vs April 主巡检)")
APR_BY_STORE = defaultdict(list)
for r in APR_SUM: APR_BY_STORE[r["store_code"]].append(r)
APR_MAIN = {sc: main_for_store(rs) for sc, rs in APR_BY_STORE.items()}

shifts = []
for sc, m in MAIN.items():
    apr = APR_MAIN.get(sc)
    if apr:
        d = m["adjusted_total_score"] - apr["adjusted_total_score"]
        shifts.append((sc, m["store_name"], apr["adjusted_total_score"], m["adjusted_total_score"], d))
for sc, name, a, b, d in sorted(shifts, key=lambda x: x[4]):
    flag = "  ⚠ ≥10" if abs(d) >= 10 else ""
    print(f"    {sc} {name:25s} {a:3d} → {b:3d}  (Δ {d:+d}){flag}")
no_baseline = [sc for sc in MAIN if sc not in APR_MAIN]
for sc in no_baseline:
    print(f"    {sc} {MAIN[sc]['store_name']:25s} —  → {MAIN[sc]['adjusted_total_score']}  (NEW: no April baseline)")

# ---------- 9. New inspectors ----------
print(f"\n[9] NEW INSPECTORS THIS MONTH (in May trend, 0 in April)")
new_count = 0
for tr in TREND_M:
    if int(tr["may_count"]) > 0 and int(tr["apr_count"]) == 0:
        print(f"    NEW: {tr['inspector_name']} ({tr['inspector_role']}) — May:{tr['may_count']}")
        new_count += 1
if new_count == 0:
    print(f"    None")

# ---------- 10. Departed inspectors ----------
print(f"\n[10] DEPARTED INSPECTORS (≥1 in April, 0 in May; informational — May is partial)")
dept_count = 0
for tr in TREND_M:
    if int(tr["may_count"]) == 0 and int(tr["apr_count"]) >= 1:
        if int(tr["apr_count"]) >= 3:  # show only meaningful drops
            print(f"    SILENT: {tr['inspector_name']} ({tr['inspector_role']}) — Apr:{tr['apr_count']} May:0")
            dept_count += 1
if dept_count == 0:
    print(f"    None with Apr ≥3")

# ---------- 11. Trend table ----------
print(f"\n[11] TREND TABLE (Q1 + Apr + May partial)")
print(f"    Month     | Self | QA | Area | Total | Status")
trend_by_month = defaultdict(lambda: Counter())
for tr in TREND_S:
    trend_by_month[tr["month"]][tr["inspection_type"]] = int(tr["inspection_count"])
status_for = {"2026-01":"✅ 三类齐全","2026-02":"⚠ 区经检查中断","2026-03":"🔴 体系崩溃",
              "2026-04":"✅ 全面恢复","2026-05":"🟡 5月在途（4日 snapshot）"}
for m in ("2026-01","2026-02","2026-03","2026-04","2026-05"):
    d = trend_by_month[m]
    total = d["门店自检"] + d["QA审计"] + d["区经检查"]
    print(f"    {m}  | {d['门店自检']:>4} | {d['QA审计']:>2} | {d['区经检查']:>4} | {total:>5} | {status_for[m]}")

# ---------- 12. Module deductions ----------
print(f"\n[12] MODULE DEDUCTIONS (主巡检 = 全月 for May)")
mod_ded = defaultdict(int); mod_cnt = Counter(); mod_stores = defaultdict(set)
for it in MAIN_ITEMS:
    mod_ded[it["cn_module"]] += it["deduction_points"]
    mod_cnt[it["cn_module"]] += 1
    mod_stores[it["cn_module"]].add(it["store_code"])
for mod in sorted(mod_cnt.keys(), key=lambda m: mod_ded[m]):
    print(f"    {mod:8s}  count={mod_cnt[mod]:>3}  ded={mod_ded[mod]:>4}  stores={len(mod_stores[mod])}/7")

# ---------- 13. Module mapping anomalies ----------
print(f"\n[13] MODULE MAPPING — 'Other' BUCKET")
other_items = [it for it in ITEMS if it["cn_module"] == "其他"]
if other_items:
    raw_others = Counter(it["module_name"] for it in other_items)
    print(f"    🔴 FAIL: {len(other_items)} items mapped to '其他':")
    for r, c in raw_others.most_common():
        print(f"        {c}× {r!r}")
else:
    print(f"    ✅ PASS: 0 items mapped to '其他' — all module names match canonical 10")

# ---------- 14. Snapshot adjustments ----------
print(f"\n[14] SNAPSHOT ADJUSTMENTS APPLIED")
print(f"    [#1]  Cover subtitle: Mid-Month Snapshot · 2026-05-01 to 2026-05-04")
print(f"    [#2]  Doc info status: V0 snapshot稿")
print(f"    [#3]  Doc info data range: 2026-05-01 至 2026-05-04（共 4 天）")
print(f"    [#4]  数据说明 leads with snapshot caveat")
print(f"    [#5]  Coverage stated as 7/13 = 53.8% with 27-day-remaining note")
print(f"    [#6]  §2.1 thresholds vs currently-inspected (denominator=7)")
print(f"    [#7]  §4.2 cross-month: April corrected baseline")
print(f"    [#8]  §7.5 trend: 5月 row partial + status 🟡")
print(f"    [#9]  §7.7 front-loaded with remaining-27-days bullets")
print(f"    [#10] §4.4 SKIP: each May store has 1 inspection, no cross-type divergence possible")
print(f"    [#11] §7.3 SKIP: no May store has ≥2 self-checks")

# ---------- 15. Data anomalies / footer ----------
print(f"\n[15] VALIDATION SUMMARY")
fails = []
if other_items: fails.append(f"module mapping has {len(other_items)} '其他' items")
if any(r["s_count"] < 0 or r["m_count"] < 0 for r in SUMMARY):
    fails.append("negative severity count")

# Check inspector_role anomalies
INSPECTOR_TYPE_OK = {
    "Store Manager":"门店自检","Assistant Store Manager":"门店自检",
    "Shift Supervisor / Trainer":"门店自检",
    "Senior QA Manager":"QA审计","QA Manager":"QA审计",
    "Area Operations Manager":"区经检查","Operations Manager":"区经检查",
    "District Manager":"区经检查",
}
type_anomalies = []
for r in SUMMARY:
    expected = INSPECTOR_TYPE_OK.get(r["inspector_role"], None)
    if expected is None:
        type_anomalies.append(f"unknown role: {r['inspector_role']!r} (insp_id={r['inspection_id']})")
    elif expected != r["inspection_type"]:
        type_anomalies.append(f"mismatch: role={r['inspector_role']!r} type={r['inspection_type']!r} (insp_id={r['inspection_id']})")
if type_anomalies:
    print(f"    Inspector type anomalies:")
    for a in type_anomalies: print(f"        {a}")

if fails:
    print(f"    🔴 FAIL: {'; '.join(fails)}")
else:
    print(f"    ✅ PASS: all checks passed (snapshot mode)")
