# SAVEPOINT 1 — Position-change history table discovery

## t_ehr_employee_post_relation analysis
- **Current-state ONLY**, NOT time-versioned
- 919 rows, 919 distinct emp_no (one row per emp per primary post)
- Columns: id, emp_no, **post_id** (bigint FK to t_ehr_post.id, NOT post_code), relation_type, tenant, create_time, create_account, modify_time, modify_account
- No start_date/end_date/effective_date columns
- ⇒ Cannot recover transition history from this table alone

## Candidate history tables (filtered by name pattern)
| Table | Rows | Comment | Fit |
|---|---|---|---|
| t_ehr_employee_adjustment_snapshot | 2,470 | ehr员工异动快照 | ★ **PRIMARY** — has from_post_code + to_post_code + effective_date |
| t_ehr_employee_adjustment_application | 11 | 员工异动申请单 | Empty for LKUS tenant |
| t_ehr_post_modify_record | 348 | 岗位信息变更记录表 | Post dictionary changes, not employee-post |
| t_ehr_employee_modify_record | 3,104 | 人员信息变更记录表 | Employee profile attrs, not post relation |
| t_ehr_employee_work_history | 0 | 员工工作履历表 | Empty |

## Chosen table: t_ehr_employee_adjustment_snapshot
- 2,324 LKUS rows from 2025-03-31 to 2026-05-26 (current to today)
- Key columns: emp_no, from_post_code, to_post_code, effective_date (VARCHAR YYYY-MM-DD), type, designation_name (JSON), department_name_path (JSON), direct_superior, create_account
- type enum (observed for LKUS): 0=离职(308), 1=入职(919), 2=二次入职(16), 3=调动/Transfer(1081); no explicit 4=Promotion code — promotions appear as type=3 with from_post_code != to_post_code

## Path decision: Path B (dedicated change-log table with from/to codes)
