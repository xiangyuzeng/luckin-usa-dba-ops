# SAVEPOINT 3 — Target user records located

All 4 employees found. None hard-deleted.

## iEHR (`luckyus_iehr.t_ehr_employee`)
| emp_no | id | name | email | status | belong_dept_id | create_time (UTC) | modify_time (UTC) | modify_account |
|---|---|---|---|---|---|---|---|---|
| US202511180007 | 4873 | **Alina Roberts** | alinaroberts93@gmail.com | **0** (deactivated) | 1127 | 2025-11-18 15:59:56 | 2026-05-15 15:31:20 | 10220 |
| US202603030007 | 5113 | **Becky Carreon** | b.carreon.rf@gmail.com | **0** (deactivated) | 1141 | 2026-03-03 20:38:23 | 2026-05-15 15:32:34 | 10220 |
| US202603100008 | 5134 | **Tyla Baxter** | tyla.baxter01@gmail.com | **0** (deactivated) | 20027 | 2026-03-10 19:25:51 | 2026-05-15 15:31:43 | **131** ⚠ |
| US202604280001 | 5251 | **Danielle Davidson** | d.davidson1588@gmail.com | **0** (deactivated) | 20010 | 2026-04-28 14:18:49 | 2026-05-15 15:29:54 | 10220 |

⚠ Tyla's row stores `modify_account=131` but the matching audit row (id 13172) shows `oper_account=10220`. Discrepancy flagged in SAVEPOINT 5.

## Department lookup (`t_ehr_department`)
| dept_id | name | path |
|---|---|---|
| 1127 | 8th & Broadway | Luckin Global > IBU > US > Operations > Store Operations > Area 1 > 8th & Broadway |
| 1141 | 54th & 8th | Luckin Global > IBU > US > Operations > Store Operations > Area 1 > 54th & 8th |
| 20010 | 102 Fulton | Luckin Global > IBU > US > Operations > Store Operations > Area 1 > 102 Fulton |
| 20027 | 21st & 3rd | Luckin Global > IBU > US > Operations > Store Operations > Area 1 > 21st & 3rd |

## Post / role (`t_ehr_employee_post_relation` + `t_ehr_post`)
| emp_no | name | post |
|---|---|---|
| US202511180007 | Alina Roberts | Shift Supervisor Trainee |
| US202603030007 | Becky Carreon | Barista |
| US202603100008 | Tyla Baxter | Shift Supervisor Trainee |
| US202604280001 | Danielle Davidson | Assistant Store Manager Trainee |

## ipermission (`luckyus_ipermission.t_luckyauth_account`)
All 4 have `status=2` (pending/never-fully-activated baseline), `delete_time = NULL` (auth account NOT soft-deleted), `last_modify_time = create_time` (auth account was never touched after creation). **The "deactivation" in iEMP is reflected in iEHR.status, not in the auth account.**

| id | emp_no | employee_name | status | create_time (UTC) | delete_time | last_modify_time |
|---|---|---|---|---|---|---|
| 10371 | US202511180007 | Alina Roberts | 2 | 2025-11-18 15:59:56 | NULL | 2025-11-18 15:59:56 |
| 10615 | US202603030007 | Becky Carreon | 2 | 2026-03-03 20:38:24 | NULL | 2026-03-03 20:38:24 |
| 10638 | US202603100008 | Tyla Baxter | 2 | 2026-03-10 19:25:51 | NULL | 2026-03-10 19:25:51 |
| 10756 | US202604280001 | Danielle Davidson | 2 | 2026-04-28 14:18:50 | NULL | 2026-04-28 14:18:50 |

## Dimission application (`t_ehr_employee_dimission_application`)
```sql
SELECT COUNT(*) FROM t_ehr_employee_dimission_application
 WHERE dimission_emp_no IN ('US202511180007','US202603030007','US202603100008','US202604280001');
-- result: 0
```
**ZERO dimission applications exist for any of the 4. The standard offboarding workflow was bypassed.**
