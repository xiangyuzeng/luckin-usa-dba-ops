# iAdmin 门店排班 (Store Schedule) — Extraction Report

**Page:** 运营系统 → 考勤 → 排班 → 门店排班 (Operations → Attendance → Scheduling → Store Schedule)
**Schedule week:** 2026-06-08 → 2026-06-14 (第24周, all 7 days)
**Store scope:** all LKUS stores with `status=1` (已开业) — 21 records (18 operating + 3 internal test kitchens)
**Tenant:** `LKUS`
**Run date:** 2026-06-12 · **Mode:** strictly read-only (SELECT/SHOW only via mcp-db-gateway)
**Output dir:** `/app/output/store_schedule_w24/`

---

## 1. Access & guardrail note

All databases are reachable **only** through the read-only `mcp-db-gateway` MCP server; every endpoint is named `aws-luckyus-*-rw` but the gateway permits SELECT/SHOW/EXPLAIN only — there is no separate replica DSN reachable from this host, and the three master tables live on **three separate RDS instances** (no cross-server JOIN possible). Per the read-replica guardrail this is documented rather than silently assumed: no writer-side DML path was used or available. The schedule grid backing data lives **entirely in MySQL** (not behind a service API), with one exception — see §7 (排班商品数).

Because the gateway returns results in-band as JSON, large pulls were staged to disk and transformed client-side (`build_csvs.py`); masters were pulled per-instance and joined in Python on `dept_id` / `emp_no`.

## 2. Source databases & tables

| Entity | Server (mcp-db-gateway) | Schema.Table | Join key |
|---|---|---|---|
| Schedule detail (per emp/day) | `aws-luckyus-opempefficiency-rw` | `luckyus_opempefficiency.t_emp_scheduling` | `scheduling_dept_id`, `emp_no`, `scheduling_date` |
| Store master | `aws-luckyus-opshop-rw` | `luckyus_opshop.t_shop_info` | `dept_id` |
| Employee master | `aws-luckyus-iehr-rw` | `luckyus_iehr.t_ehr_employee` | `emp_no` |
| Theoretical hours (target) | `aws-luckyus-opempefficiency-rw` | `luckyus_opempefficiency.t_summary_data` (`code='national_work_hours'`) | `dept_id`, `target_time` |
| Attendance (actuals — NOT the schedule) | `aws-luckyus-opempefficiency-rw` | `t_attendance_shift`, `t_clock_in` | reference only |

## 3. Field mapping (UI → schema)

| UI label | Field | Source |
|---|---|---|
| 门店序号 (store code) | `store_code` | `t_shop_info.shop_no` (e.g. `US00001`) |
| 门店名称 | `store_name` | `t_shop_info.shop_name` |
| 当前门店状态 | `store_status` | `t_shop_info.status` (1 = 已开业) |
| 门店内部主键 | `dept_id` | `t_shop_info.dept_id` = `t_emp_scheduling.scheduling_dept_id` |
| 排班日期 | `schedule_date` | `t_emp_scheduling.scheduling_date` (DATE, local store date) |
| FT/PT badge | `employment_type` | `t_ehr_employee.property` → **0=FT(全职), 1=PT(兼职)**, 2=intern, 3=outsourced |
| 姓名 | `employee_name` | `t_ehr_employee.name` (keyed by `emp_no`) |
| 员工编号 | `employee_id` | `t_emp_scheduling.emp_no` |
| 排班工时 | `daily_scheduled_hours` | `t_emp_scheduling.effect_hours` (= `effect_minutes/60`, rest excluded) |
| 排班时段 (班) | `scheduling_times` | `t_emp_scheduling.scheduling_times` (`HH:mm~HH:mm`, comma-sep) |
| 排休时段 (休) | `rest_times` | `t_emp_scheduling.rest_times` |
| grid per-slot status | `status_code` | **derived** by exploding `scheduling_times` (班) / `rest_times` (休) into 48×30-min slots |
| 排班人员数 (per slot) | `slot_headcount` | **derived** = count of on-duty (班) employees overlapping the slot |
| 排班商品数 (per slot) | `slot_product_qty` | **NOT persisted in reachable DBs** — see §7 |
| 排班总工时 (per store/day) | `store_day_total_hours` | `SUM(effect_hours)` per `scheduling_dept_id`+`scheduling_date` |

> **Critical schema finding:** the 48-char bitmap columns `scheduling_slot` / `scheduling_slot_result` (整体排班快照) exist but are **all zeros for every LKUS row** (`SUM(scheduling_slot_result <> REPEAT('0',48)) = 0`). The live per-slot grid must therefore be reconstructed from the `scheduling_times` / `rest_times` HH:mm strings, **not** from the bitmap.

## 4. Hours formula (derived & validated)

```
daily_scheduled_hours (排班工时) = effect_hours = effect_minutes / 60
effect_minutes = Σ(scheduling_times span)  −  Σ(rest_times span)     # rest is NOT paid
```
Worked example (Huichen Jiang, US00001, 2026-06-12): span `06:00~14:30` = 510 min; rest `12:45~13:30` = 45 min → 465 min = **7.75 h** ✓. Breaks are 30 or 45 min depending on shift length (e.g. the 4.5 h shift nets a 30-min break). The stored `effect_minutes` is authoritative and is **not** recomputed from the 30-min grid (see §8 granularity note).

## 5. Status / type enum mapping

`t_emp_scheduling.work_type` + `source_Type` drive the grid status; `rest_times` overrides to 休:

| Grid | code | meaning | Source rule |
|---|---|---|---|
| 班 | on_duty | 在岗 | `work_type='1'`, slot ∈ `scheduling_times`, slot ∉ `rest_times` |
| 休 | rest | 排休 | slot ∈ `rest_times` |
| 训 | training | 训练 | `work_type='4'` (`source_Type='working_time_apply'`) |
| (empty) | — | not scheduled | slot in no segment |

Other UI legend codes (会 meeting, 课 course, 假 leave, 其他 other, 闭店 closed) did **not occur** in this week's LKUS data. Reference enum from `t_attendance_shift.type` (考勤 actuals): 1=考勤, 3=会议, 4=培训, 5=请假, 6=其他, 9=训练.
`t_emp_scheduling.status` (单据状态): **1 = active/published** (extracted), 2 = draft/non-active (excluded — 78 rows; see §9).

## 6. Timezone

`t_shop_info.time_zone = 'America/New_York'` for all stores. `scheduling_date` is a DATE and `scheduling_times`/`rest_times` are local `HH:mm` strings — **all outputs are already in local store time** (US Eastern); no UTC conversion applied. (`set_up_time` open dates are stored UTC, e.g. `04:00:00` = 00:00 EDT — informational only.)

## 7. 排班商品数 (slot product/cup-volume forecast) — gap

Not found in any reachable scheduling table. Searched: all of `luckyus_opempefficiency` (only month-grain `same_quantity`/`national_work_hours` exist; the algorithm table `t_smart_scheduling` has **0 rows** for LKUS) and `luckyus_opshopsale` (only sale-plan config). The per-30-min demand curve the UI overlays (32/96/80…) is a **forecast served at render time** and is not persisted in these operational DBs — it is likely produced by the labor/sales forecasting service (candidate stores not yet confirmed: Redshift / `ldas` / `pubdm`). Per the "stop and report rather than guess" guardrail, `slot_product_qty` is left **blank** in `store_slot_aggregates.csv`. The companion **`slot_headcount` IS derivable** and is populated. Re-run is available on request once the forecast source is confirmed.

## 8. Anchor validation — US00001 (8th & Broadway), Fri 2026-06-12 ✓

| Check | Expected | Got |
|---|---|---|
| Employees scheduled | 7 (prompt said 8; its own named list is 7) | **7** ✓ |
| 排班总工时 | 50 | **50.00** ✓ |
| Per-emp hours | 7.75/6.75/4.5/7.75/7.75/7.75/7.75 | exact match ✓ |
| FT/PT | Huichen FT, Xiao Lan PT, Steven PT, rest FT | exact match ✓ |
| Earliest 班 | 06:00 (Huichen, Xiao Lan) | 06:00 ✓ |
| Headcount 06:00 | ~2 | **2** ✓ |
| Headcount 13:30 | 6 | **6** ✓ |

> The prompt's "8 employees" is a typo — the seven names it lists sum to exactly 50 h and the DB returns exactly those seven.

## 9. Outputs (UTF-8 **with BOM**)

| File | Rows | Contents |
|---|---|---|
| `stores.csv` | 21 | store_code, dept_id, name, status, time_zone, open_date, is_internal |
| `employee_day.csv` | 884 | per emp/day: FT/PT, name, hours, minutes, status, raw times |
| `slot_status_long.csv` | 14,307 | one row per employee-slot (班/休/训); unscheduled slots omitted |
| `store_slot_aggregates.csv` | 3,975 | per store/day/slot: `slot_headcount` (derived); `slot_product_qty` blank (§7) |
| `store_day_summary.csv` | 147 | per store/day: total_hours, employees, ft/pt, first/last slot |
| `slot_status_wide.csv` | 884 | one row per emp/day × 48 slot columns (mirrors the UI grid) |

Raw staged inputs: `_raw_emp_map.txt` (482 emps), `_raw_schedule.json` (962 rows). Build script: `build_csvs.py`.

## 10. Coverage & anomalies

- **18/18 operating stores** present, full **7/7 days** each — no gaps.
- 3 internal test kitchens (US00000, US99998, US99999; `is_internal=Y`) are `status=1` but carry **no schedule** → 0-row store-days (expected; flag, do not treat as missing).
- Store-code gaps in numbering (US00009/11/13/14/16/17/21/23/26) = stores with `status=2` (not-yet-open / 筹建), out of scope.
- **78 draft rows** (`t_emp_scheduling.status=2`) excluded from the board; counted here for transparency.
- 13 employee-days are **training** (训, `work_type=4`) → 156 slot rows.
- Granularity caveat: breaks are 15-min-aligned (e.g. 12:45–13:30) while the grid is 30-min; a slot is marked 休 if a break overlaps it at all, so grid-summed minutes can differ from `effect_minutes`. **`effect_hours` from the DB is authoritative** for 排班工时; the grid is presentational.
- `store_serial` (the prompt's `LKUS00000036` example) has no column in `t_shop_info` (closest are `brand_no='LK001'`, `dept_id`); `shop_no` (`US00001`) is the canonical store code used throughout.

## 11. SQL executed (read-only)

```sql
-- schema discovery
SELECT table_schema,table_name,table_rows,table_comment FROM information_schema.tables
 WHERE table_name REGEXP 'sched|shift|roster|attend|labor|forecast'
    OR table_comment REGEXP '排班|考勤|班次|工时|排休|预测';                 -- per candidate server
SHOW CREATE TABLE luckyus_opempefficiency.t_emp_scheduling;
SHOW CREATE TABLE luckyus_opempefficiency.t_attendance_shift;
SHOW CREATE TABLE luckyus_opempefficiency.t_smart_scheduling;
SHOW CREATE TABLE luckyus_opempefficiency.t_summary_data;
SELECT column_name,column_type,column_comment FROM information_schema.columns
 WHERE table_schema='luckyus_opshop' AND table_name='t_shop_info';
SELECT ... FROM information_schema.columns WHERE table_schema='luckyus_iehr'
   AND table_name='t_ehr_employee';                                          -- FT/PT discovery

-- validation / profiling
SELECT ... FROM t_emp_scheduling WHERE scheduling_date='2026-06-12' ORDER BY scheduling_dept_id,emp_no LIMIT 20;
SELECT source_Type,work_type,status,count(*),sum(scheduling_slot_result<>REPEAT('0',48))
  FROM t_emp_scheduling WHERE tenant='LKUS' AND scheduling_date BETWEEN '2026-06-08' AND '2026-06-14'
 GROUP BY source_Type,work_type,status;                                      -- bitmap all-zero proof
SELECT dept_id,shop_no,shop_name,status,time_zone,internal,DATE(set_up_time)
  FROM t_shop_info WHERE tenant='LKUS' AND status=1 ORDER BY shop_no;

-- extraction (the data pulls)
SELECT CONCAT_WS('|',emp_no,name,property,status) FROM t_ehr_employee WHERE emp_no LIKE 'US%';
SELECT CONCAT_WS('|',scheduling_dept_id,scheduling_date,emp_no,work_type,source_Type,status,
       FORMAT(effect_hours,2),effect_minutes,scheduling_times,rest_times,cross_day_type)
  FROM t_emp_scheduling
 WHERE tenant='LKUS' AND scheduling_date BETWEEN '2026-06-08' AND '2026-06-14'
 ORDER BY scheduling_dept_id,scheduling_date,emp_no;
```

## 12. Reproduce

```
cd /app/output/store_schedule_w24 && python3 build_csvs.py
# re-pull the two raw inputs via mcp-db-gateway (queries above) to refresh, then re-run.
```
