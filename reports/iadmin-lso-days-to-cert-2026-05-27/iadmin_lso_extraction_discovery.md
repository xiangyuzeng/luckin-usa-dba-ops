# iadmin LSO Days-to-Cert — Extraction Discovery Log

**Run timestamp**: 2026-05-27 UTC
**Window**: 2025-05-27 → 2026-05-27 inclusive, filtered on **certification acquisition date**
**Filter (UTC, after PT-to-UTC conversion)**: `obtaining_date >= '2025-05-27 07:00:00' AND obtaining_date <= '2026-05-28 06:59:59'`

## 1. Data source resolution

| Item | Value |
|---|---|
| MCP DB Gateway server | `aws-luckyus-iadmin-rw` — checked, **does NOT contain HR data** |
| MCP DB Gateway server (actual) | **`aws-luckyus-iehr-rw`** |
| Schema | `luckyus_iehr` |
| Employee master table | `t_ehr_employee` (1,524 rows total; 858 in LKUS tenant) |
| Qualification table (long format) | `t_ehr_employee_qualification_info` (388 rows total; long EAV format — one row per (emp, cert) pair) |
| Cert master used in production | **`t_ehr_yxt_certificate`** (Yunxuetang LMS-managed) — **NOT** the older `t_ehr_certificate` |
| Department lookup | `t_ehr_department` (joined for `dept_name`) |
| Position lookup | `t_ehr_employee_post_relation` (relation_type=0 = primary post) → `t_ehr_post` |

The iadmin UI label refers to a portal that **routes HR features to the iehr backend**. The iadmin RDS schema (`luckyus_iadmin`) contains only workflow/approval tables — no HR data.

## 2. Column name mapping (request → actual)

| Logical name | Actual column |
|---|---|
| `employee_no` | `t_ehr_employee.emp_no` (varchar(40)) |
| `full_name` | `t_ehr_employee.name` |
| `email` | `t_ehr_employee.email` |
| `hire_date` | **`t_ehr_employee.join_date`** (varchar(10), format `YYYY-MM-DD`) — Chinese label `入职日期` |
| `acquired_date` | **`t_ehr_employee_qualification_info.obtaining_date`** (varchar(30), format `YYYY-MM-DD HH:MM:SS`) — Chinese label `获取日期` |
| `cert_code` join | `t_ehr_employee_qualification_info.cer_id` (UUID) → `t_ehr_yxt_certificate.cer_id` |
| `cert_name` | `t_ehr_yxt_certificate.qualification_certificate` |
| `dept_name` | `t_ehr_department.name` via `t_ehr_employee.belong_dept_id` |
| `current_position_code/name` | `t_ehr_post.code` / `t_ehr_post.name` via `t_ehr_employee_post_relation` (primary post) |
| `employee_status` | `t_ehr_employee.status` (1 = Active / 在职; 0 = Separated / 离职) |
| `store_id` | **NOT AVAILABLE** as a discrete column on `t_ehr_employee`. Emitted as NULL; `dept_name` carries the store identifier (most LKUS depts are named after the store cross-street, e.g. `33rd & 10th`, `8th & Broadway`, `100 Maiden Ln`). |
| `tenant` filter | `tenant='LKUS'` everywhere (`IQA2` is the QA test tenant) |

## 3. LSO code → cer_id mapping (canonical, from `t_ehr_yxt_certificate`)

| LSO level | cer_id | template_no | Chinese role |
|---|---|---|---|
| **LSO100** | `83a7b425-40ec-4c86-b766-1f0488843787` | KFS | 咖啡师 (Barista) |
| **LSO200** | `35a26709-b4a0-49ae-96f5-723f0f448d76` | ZBZG | 值班主管 (Shift Supervisor) |
| **LSO300** | `7bab460e-360e-462b-bac9-1300331b2176` | FDZ | 副店长 (Assistant Manager) |
| **LSO400** | `09fe6ae9-78ac-4447-9958-99c834e6a4d3` | DZ | 店长 (Store Manager) |

**Stray legacy cer_id** detected for LSO300: `803c8627-5bef-4aa6-b563-0062b13f3b13` (from the older `t_ehr_certificate` master). 1 emp matched it (US202505280001, obtained 2025-08-04 16:23:08). Included in the LSO300 filter so this row is not lost.

**Excluded** cer_ids:
- 4 `* In Training` cer_ids (training-in-progress markers, not earned certs): `5fc3deb0…`, `615ebeac…`, `39009271…`, `59c1e692…`
- `26890039-aa93-4789-bfd4-ba61524c190d` (LSO500) — out of scope
- `4fe8eaeb-00e2-40c8-bfab-3b6a4f85d5af` (Operational Manager) — out of scope

## 4. Timezone confirmation (CHECKPOINT 3 echo)
```
@@global.time_zone  = UTC
@@session.time_zone = UTC
NOW()               = 2026-05-27 22:19:30
UTC_TIMESTAMP()     = 2026-05-27 22:19:30
```
Server is UTC. The `obtaining_date` column is `varchar(30)` storing ISO datetime strings in UTC (LMS callback writes them server-side). String comparison is equivalent to chronological comparison for this format. Window bounds use the PT-to-UTC translation: `>= '2025-05-27 07:00:00'` and `<= '2026-05-28 06:59:59'`.

## 5. Format choice
**Long format (EAV)** — one row per (emp_no, cer_id, obtaining_date). Multi-cert employees appear in multiple rows under different `cer_id` values.

## 6. Decision rules applied
- Dedup: `MIN(obtaining_date)` per `(emp_no, cer_level)` — first time the employee earned that cert.
- Tenant: hardcoded `tenant='LKUS'` on every join (employee, qualification, department, post tables).
- Day diff: `DATEDIFF(obtaining_date, join_date)` — relies on MySQL auto-cast of ISO varchar to DATE, returns whole calendar days.
- Position: only `relation_type=0` (primary post) used. Secondary posts ignored.

## 7. Row counts (after window + dedup)

| Level | rows | distinct emps | data_anomaly=Y | days_to_cert range (min / max / avg) |
|---|---|---|---|---|
| **LSO100** | 203 | 203 | 2 | -177 / 180 / 49.8 |
| **LSO200** | 105 | 105 | 1 | -179 / 234 / 79.9 |
| **LSO300** | 40 | 40 | 0 | 30 / 231 / 112.3 |
| **LSO400** | 24 | 24 | 1 | -139 / 280 / 119.5 |
| **TOTAL** | **372** | 210 unique emps | 4 anomaly rows | — |

### Pre-dedup raw counts (sanity)
- LSO100 raw 214 rows / 213 distinct → 203 in window (10 rows pre-window: initial 2025-05-12 hires earned LSO100 May 22-23, before May 27 PT start; 1 dup folded).
- LSO200 raw 106 / 105 distinct → all in window.
- LSO300 raw 41 (40 + 1 legacy-cer_id stray) / 41 distinct → all in window.
- LSO400 raw 26 / 24 distinct → all in window (2 dups folded).

## 8. Overlap matrix
| Levels per emp | Emp count |
|---|---|
| in 1 level only | 107 |
| in 2 levels | 62 |
| in 3 levels | 23 |
| in 4 levels (full pipeline) | 18 |
| **Total distinct emps across all 4 CSVs** | **210** |

## 9. Data anomalies (data_anomaly=Y)
4 rows total across 2 distinct employees — both cases of cert dates earlier than HR hire_date, suggesting cert earned during pre-hire training before HR paperwork finalized:

| emp_no | name | level | hire_date | cert date | days |
|---|---|---|---|---|---|
| US202510060002 | Daniel Chu | LSO100 | 2026-05-04 | 2025-11-08 | -177 |
| US202510060002 | Daniel Chu | LSO200 | 2026-05-04 | 2025-11-06 | -179 |
| US202510060002 | Daniel Chu | LSO400 | 2026-05-04 | 2025-12-16 | -139 |
| US202510140002 | Jocelyn Lopez | LSO100 | 2026-01-18 | 2025-12-19 | -30 |

(Daniel Chu additionally never earned LSO300 — he is the sole "1101" progression pattern. His emp_no prefix `US202510060002` encodes an October-2025 creation, contradicting the 2026-05-04 hire_date stored — likely a re-hire / paperwork lag scenario for HR to resolve.)

## 10. Zero-row checkpoints / schema surprises
- **CHECKPOINT 1 surprise**: iadmin RDS was empty of HR data. The mission spec assumes iadmin holds the HR system but the actual backend is iehr (the iadmin UI is a portal-only layer).
- **CHECKPOINT 2 surprise**: the original `t_ehr_certificate` master is **NOT** the production cert dictionary (only 1 LKUS row references its UUIDs). Production uses `t_ehr_yxt_certificate` (Yunxuetang LMS sync). Without this, a naive filter on `t_ehr_certificate.cer_name='LSO100'` would have yielded 0 LKUS rows.
- **No store_id column** on `t_ehr_employee`. CSV emits NULL for `store_id`. The `dept_name` column carries store identity for the ~85% of cohort employees assigned to a store dept (e.g. `33rd & 10th`).
- **CHECKPOINT 4 LSO100 anomaly**: 10 raw rows fell before the window start due to the initial 2025-05-12 hire cohort earning LSO100 between May 22-23, 2025 (5 days before the May 27 PT window). These appear in the data as "0111" pattern emps (have LSO200/300/400 in window, no LSO100). No data quality issue — just an artifact of the window boundary.

## 11. Output files

| File | Rows | Encoding |
|---|---|---|
| `iadmin_lso100_days_to_cert.csv` | 203 | UTF-8 with BOM |
| `iadmin_lso200_days_to_cert.csv` | 105 | UTF-8 with BOM |
| `iadmin_lso300_days_to_cert.csv` | 40 | UTF-8 with BOM |
| `iadmin_lso400_days_to_cert.csv` | 24 | UTF-8 with BOM |
| `iadmin_lso_all_levels_combined.csv` | 372 | UTF-8 with BOM |
| `iadmin_lso_extraction_discovery.md` | — | this file |

CSV column order: `employee_no, full_name, email, hire_date, lso_acquired_date, days_to_cert, store_id, dept_name, current_position_code, current_position_name, employee_status, data_anomaly, cert_level`.
