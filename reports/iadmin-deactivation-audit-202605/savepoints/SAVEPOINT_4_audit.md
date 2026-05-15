# SAVEPOINT 4 — Status-change audit trail

Pulled all `t_ehr_employee_modify_record` rows for the 4 target emp_nos (no date filter — full history). Status flip = the row where `JSON_EXTRACT(before_value,'$.status') = 1` AND `JSON_EXTRACT(after_value,'$.status') = 0`.

## Full audit history (UTC)

### Alina Roberts (US202511180007) — 7 rows
| id | oper_time UTC | oper_source | oper_account | bv.status | av.status | note |
|---|---|---|---|---|---|---|
| 10961 | 2025-11-18 15:59:56 | 2 | 10220 | NULL | 1 | creation |
| 10974 | 2025-11-19 18:25:40 | 2 | 10220 | 1 | 1 | edit (no status change) |
| 12055 | 2026-03-18 20:44:13 | 2 | 131 | 1 | 1 | edit (no status change) |
| 12180 | 2026-04-02 15:10:35 | 2 | 10220 | 1 | 1 | edit (no status change) |
| 12209 | 2026-04-04 15:03:54 | 2 | 10220 | 1 | 1 | edit (no status change) |
| 12908 | 2026-04-23 22:08:56 | 2 | 10220 | 1 | 1 | edit (no status change) |
| **13171** | **2026-05-15 15:31:20** | **2** | **10220** | **1** | **0** | **DEACTIVATION** |

### Becky Carreon (US202603030007) — 4 rows
| id | oper_time UTC | oper_source | oper_account | bv.status | av.status | note |
|---|---|---|---|---|---|---|
| 11882 | 2026-03-03 20:38:24 | 2 | 131 | NULL | 1 | creation |
| 12214 | 2026-04-06 13:59:50 | 2 | 131 | 1 | 1 | edit |
| 13017 | 2026-05-04 21:53:19 | 2 | 10220 | 1 | 1 | edit — note: matches **reported** 05/04 date but status was NOT changed |
| **13173** | **2026-05-15 15:32:35** | **2** | **10220** | **1** | **0** | **DEACTIVATION** |

### Tyla Baxter (US202603100008) — 2 rows
| id | oper_time UTC | oper_source | oper_account | bv.status | av.status | note |
|---|---|---|---|---|---|---|
| 11940 | 2026-03-10 19:25:51 | 2 | 131 | NULL | 1 | creation |
| **13172** | **2026-05-15 15:31:43** | **2** | **10220** | **1** | **0** | **DEACTIVATION** — audit oper_account=10220 but t_ehr_employee.modify_account=131 ⚠ |

### Danielle Davidson (US202604280001) — 2 rows
| id | oper_time UTC | oper_source | oper_account | bv.status | av.status | note |
|---|---|---|---|---|---|---|
| 12983 | 2026-04-28 14:18:49 | 2 | 10220 | NULL | 1 | creation |
| **13170** | **2026-05-15 15:29:55** | **2** | **10220** | **1** | **0** | **DEACTIVATION** |

## Key observations
1. **All four flips (1→0) happened today, 2026-05-15, between 15:29:55 and 15:32:35 UTC.** That is a 2-minute 40-second window.
2. **oper_account=10220 for all four flips** in the audit log (Tyla has a `t_ehr_employee.modify_account` discordance — see SAVEPOINT 5).
3. **oper_source=2** for every flip — same source channel as every other modify across the table (no batch/script source distinguished).
4. **No reactivations** in the history. Each user transitioned `1 → 0` exactly once.
5. **No flips occurred on the reported dates** (05/02, 05/04, 05/08, 05/11). The only nearby touchpoint is Becky's 05/04 21:53 UTC edit, where status remained 1.
6. **`t_ehr_employee_dimission_application` has zero rows** for any of these emp_nos — offboarding workflow bypassed.
7. **`t_permission_account_history` and `t_luckyauth_account` show no deactivation** — auth accounts retain `status=2`, `delete_time IS NULL`, and `last_modify_time = create_time`. Permission/login state was **not** changed.

## Permission-side history (`t_permission_account_history`)
- Account 10371 (Alina): 5 history rows, all with `modify_time = 2026-05-08 05:59:16` and `modify_account = 0` → batch backfill.
- Account 10615 (Becky): 1 history row, same batch backfill stamp.
- Accounts 10638 (Tyla), 10756 (Danielle): **zero** history rows.

The 2026-05-08 05:59:16 timestamp matches the `t_ehr_employee_dimission_application` backfill (every row in that table has `create_time = 2026-05-08 05:58:59`, `create_account = 0`, except one Nadia-entered application for a different employee). This batch is unrelated to the 4 deactivations.
