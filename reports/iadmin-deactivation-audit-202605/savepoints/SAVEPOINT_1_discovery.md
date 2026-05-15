# SAVEPOINT 1 — Cluster + schema discovery

## MCP server inventory
- `mcp__mcp-db-gateway__list_servers` returned 62 MySQL servers, 3 Postgres, 78 Redis.
- Candidate iadmin/iEMP-class clusters identified:
  - `aws-luckyus-iadmin-rw` → DB `luckyus_iadmin` — workflow/approval/admin-task tables only; **no user/employee tables**.
  - `aws-luckyus-iehr-rw` → DB `luckyus_iehr` — master HR/employee records (1497 employees, 3010 modify_record rows). **Primary system of record for employee deactivation.**
  - `aws-luckyus-ipermission-rw` → DB `luckyus_ipermission` — login/auth accounts (1503 rows) + history (1071 rows). **Secondary — permission/login state.**
  - `aws-luckyus-iluckyauthapi-rw` → DB `luckyus_iluckyauthapi` — no user/account/audit tables in this database.

## Conclusion
"iadmin / iEMP" = the **iEHR + ipermission** pair. The `luckyus_iadmin` schema itself only holds approval-workflow tables; the canonical employee status lives in `luckyus_iehr.t_ehr_employee` and the matching auth account lives in `luckyus_ipermission.t_luckyauth_account`.

## TZ confirmation (iEHR cluster)
```sql
SELECT @@global.time_zone, @@session.time_zone, @@system_time_zone, NOW(), UTC_TIMESTAMP();
```
| global_tz | session_tz | system_tz | now_local | now_utc | host | version |
|---|---|---|---|---|---|---|
| UTC | UTC | UTC | 2026-05-15T16:37:02 | 2026-05-15T16:37:02 | ip-172-17-0-245 | 8.0.45 |

iadmin host: `ip-172-17-0-245`, iEHR host: `ip-172-17-4-180`. **All datetime fields stored as UTC. Conversion to PT/ET applied manually in report.**

## Candidate user tables (luckyus_iehr)
- `t_ehr_employee` (1497) — primary employee record, has `status`, `modify_time`, `modify_account`.
- `t_ehr_employee_modify_record` (3010) — audit log with `oper_account`, `oper_source`, `oper_time`, full before/after JSON.
- `t_ehr_employee_dimission_application` (48) — offboarding-workflow applications with `last_working_day`, `effective_date`, `effective_status`.
- `t_ehr_department` (referenced by `belong_dept_id` on the employee row).

## Candidate user tables (luckyus_ipermission)
- `t_luckyauth_account` (1503) — login accounts (PK = `id`, links to `emp_no`).
- `t_permission_account_history` (1071) — account history.
