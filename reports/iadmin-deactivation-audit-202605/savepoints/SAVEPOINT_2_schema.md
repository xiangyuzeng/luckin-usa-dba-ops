# SAVEPOINT 2 — Schema inspection

## `luckyus_iehr.t_ehr_employee` (employee master)
Key columns:
| Column | Type | Notes |
|---|---|---|
| id | bigint unsigned PK | |
| emp_no | varchar(40) | UNIQUE business key — `US{YYYYMMDD}{NNNN}` for North America |
| name | varchar(400) | "First Last" display name |
| first_name / last_name | varchar(128) | |
| email | varchar(100) | |
| **status** | tinyint NOT NULL | **1 = active, 0 = deactivated** (distribution: 1184 active / 280 deactivated) |
| belong_dept_id | bigint | FK → `t_ehr_department.id` |
| tenant | varchar(4) | `LKUS` for US tenant |
| create_time / modify_time | datetime | TZ = UTC |
| modify_account | bigint | last operator's auth account id |

## `luckyus_iehr.t_ehr_employee_modify_record` (audit log) — **discrete columns + JSON blob**
| Column | Type | Notes |
|---|---|---|
| id | bigint unsigned PK | |
| emp_no | varchar(40) | target employee |
| before_value | varchar(4096) | JSON snapshot of prior state |
| after_value | varchar(4096) | JSON snapshot of new state |
| **oper_source** | tinyint | observed: only value `2` exists across 4181 rows since 2025-03-14 — likely "web UI / iEMP backend". No batch/`1` rows in this table. |
| **oper_account** | bigint | auth account id of the actor |
| **oper_time** | datetime | UTC |
| remark | varchar(400) | usually `""` or NULL |
| tenant | varchar(4) | |

Status field lives **inside** the JSON blob (`$.status`). Extracted via `JSON_EXTRACT(before_value,'$.status')`. **No** `field_name` / `operator_ip` / `user_agent` / `request_id` columns — those metadata fields are **not** recorded in this schema.

## `luckyus_ipermission.t_luckyauth_account` (auth account)
Key columns: id PK, emp_no UNIQUE, employee_name, email, phone, **status** (1=active 1011 / 2=pending? 284 / 0=disabled 194), create_time, **delete_time** (nullable — soft-delete), last_modify_time, tenant_code.

## `luckyus_ipermission.t_permission_account_history`
Columns: id PK, account_id (FK to t_luckyauth_account.id), before_value (JSON), create_time, creator_name, create_account, tenant, modify_time, modify_account. **No `field_name` or `after_value`.**

## `luckyus_iehr.t_ehr_employee_dimission_application` (offboarding workflow)
Columns: id, application_no, **dimission_emp_no**, dept_code, post_code, dimission_reason_code, **last_working_day**, **effective_date**, **effective_status**, operation_source (1=A2-legacy import / 2=UI-entered), create_time, create_account, modify_time, modify_account.

## `luckyus_iehr.t_ehr_department`
Columns: id PK, name, code, parent_code, status, **path_by_name** (slash-delimited dept hierarchy), belong_city, leader_emp_no.

## Sample rows confirmed for shape
- Audit row `id=13173` (Becky Carreon, 2026-05-15 15:32:35 UTC) — `bv.status=1`, `av.status=0`, oper_account 10220, oper_source 2. JSON shape confirmed (snake_case → camelCase mapping in JSON: `belongDeptId`, `joinDate`, `leaderEmpNo`, etc.).
