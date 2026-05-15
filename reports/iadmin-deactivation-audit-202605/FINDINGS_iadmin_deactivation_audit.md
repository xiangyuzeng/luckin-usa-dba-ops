# FINDINGS — iadmin / iEMP Deactivation Audit

**Audit date:** 2026-05-15 (UTC)
**Auditor:** DBA / Infrastructure (databasecheck)
**Cluster scope:** `aws-luckyus-iehr-rw` + `aws-luckyus-ipermission-rw` (read-only)
**Tenant:** `LKUS` (Luckin USA)
**Branch / output:** `/app/FINDINGS_iadmin_deactivation_audit.md` (+ savepoints under `/app/savepoints/`)

---

## 1. Executive Summary

The HR stakeholder's hunch was correct — the timing is more than "a little" off. **All four employees were flipped from `status=1` (active) to `status=0` (deactivated) in the iEHR master employee table within a 2-minute-40-second window today, 2026-05-15 between 11:29:55 and 11:32:35 EDT (15:29:55–15:32:35 UTC)**, by the same HR Business Partner (auth account `1**20`, Nadia Betancur). The reported separation dates (05/02, 05/04, 05/08, 05/11) lag the actual DB flip by **4 to 13 calendar days**, meaning iEMP carried these employees as "active" long after they presumably stopped working. In addition, **none of the four went through the proper offboarding workflow** (`t_ehr_employee_dimission_application` has zero matching rows), and **their auth accounts in `t_luckyauth_account` were never touched** (`delete_time` still NULL, `status` still `2`). One row (Tyla Baxter) also has an internal inconsistency where the employee row's `modify_account` shows account `1**` (Yanwen Zhou — herself now status=0) while the matching audit log shows oper_account `1**20` (Nadia) — likely an application bug rather than misuse.

---

## 2. Investigation Scope & Method

**Scope.** Reconcile reported deactivation dates against authoritative database state for 4 named employees, identify the operator behind each status change, surface anomalies, and assess process compliance.

**Method.** READ-ONLY `SELECT` queries via `mcp-db-gateway` against:
- `aws-luckyus-iehr-rw` (iEHR — master employee + audit log + dimission applications)
- `aws-luckyus-ipermission-rw` (iEMP auth / permission state)

No `INSERT`/`UPDATE`/`DELETE`/DDL statements were issued. All queries used `LIMIT` or narrowly-scoped `WHERE` filters. TZ was verified before pulling timestamped results.

**Checkpoint methodology (per prompt):**
1. Cluster + schema discovery → `SAVEPOINT_1_discovery.md`
2. Schema inspection → `SAVEPOINT_2_schema.md`
3. Locate the 4 target user records → `SAVEPOINT_3_users.md`
4. Pull full status-change audit trail → `SAVEPOINT_4_audit.md`
5. Resolve operators + reconcile timing → `SAVEPOINT_5_reconciliation.md`

---

## 3. Environment Confirmation

### 3.1 System identification
The phrase "iadmin / iEMP" maps to **two cooperating databases**, not one:
- `luckyus_iehr` (on `aws-luckyus-iehr-rw`) — the master employee record (1497 rows). `status` here is the canonical "active/deactivated" flag.
- `luckyus_ipermission` (on `aws-luckyus-ipermission-rw`) — the login/auth account record (1503 rows).
- `luckyus_iadmin` (on `aws-luckyus-iadmin-rw`) is a separate workflow/approval database with **no user table** — it does not store employee status.

### 3.2 TZ verbatim (iEHR cluster)
```
SELECT @@global.time_zone, @@session.time_zone, @@system_time_zone, NOW(), UTC_TIMESTAMP();
```
| global_tz | session_tz | system_tz | NOW() | UTC_TIMESTAMP() | host | version |
|---|---|---|---|---|---|---|
| UTC | UTC | UTC | 2026-05-15T16:37:02 | 2026-05-15T16:37:02 | ip-172-17-0-245 | 8.0.45 |

**All datetime columns are stored in UTC.** Conversion to PT/ET is done manually in this report (May 2026: PDT = UTC−7, EDT = UTC−4).

### 3.3 Audit table shape
`luckyus_iehr.t_ehr_employee_modify_record` — discrete columns + **JSON blobs** for the field-level diff:
- `id`, `emp_no`, `before_value` (JSON), `after_value` (JSON), `oper_source` tinyint, `oper_account` bigint, `oper_time` datetime, `remark`, `tenant`, `create_time`, `modify_time`.
- Status changes are detected with `JSON_EXTRACT(before_value,'$.status')` vs `JSON_EXTRACT(after_value,'$.status')`.
- **No `field_name`, `operator_ip`, `user_agent`, or `request_id` columns exist** — channel attribution is limited to `oper_source` (only value present in 4181 rows is `2`).

`luckyus_ipermission.t_permission_account_history` — has `before_value` only (no `after_value`), keyed on `account_id`, with `create_time`, `modify_time`, `create_account`, `modify_account`, `creator_name`.

---

## 4. Target User Confirmation

All 4 employees located. None hard-deleted. All on tenant `LKUS`. All currently `status=0` in iEHR; all currently `status=2` in `t_luckyauth_account` with `delete_time IS NULL`.

| iEHR `id` | `emp_no` | name | post | store / dept | iEHR.status | auth.id | auth.status | auth.delete_time |
|---|---|---|---|---|---|---|---|---|
| 4873 | US202511180007 | **Alina Roberts** | Shift Supervisor Trainee | 1127 — 8th & Broadway | 0 | 10371 | 2 | NULL |
| 5113 | US202603030007 | **Becky Carreon** | Barista | 1141 — 54th & 8th | 0 | 10615 | 2 | NULL |
| 5134 | US202603100008 | **Tyla Baxter** | Shift Supervisor Trainee | 20027 — 21st & 3rd | 0 | 10638 | 2 | NULL |
| 5251 | US202604280001 | **Danielle Davidson** | Assistant Store Manager Trainee | 20010 — 102 Fulton | 0 | 10756 | 2 | NULL |

All four are **store-level operations staff** (Manhattan): Operations Department > Store Operations > Area 1.

---

## 5. Deactivation Timeline (chronological, per user, UTC + PT + ET)

### 5.1 Alina Roberts (US202511180007) — full audit history
| modify_record.id | UTC | PDT | EDT | oper_source | oper_account (masked) | bv.status | av.status | event |
|---|---|---|---|---|---|---|---|---|
| 10961 | 2025-11-18 15:59:56 | 2025-11-18 08:59:56 | 2025-11-18 10:59:56 EST | 2 | 1**20 | NULL | 1 | creation |
| 10974 | 2025-11-19 18:25:40 | 2025-11-19 10:25:40 | 2025-11-19 13:25:40 EST | 2 | 1**20 | 1 | 1 | edit |
| 12055 | 2026-03-18 20:44:13 | 2026-03-18 13:44:13 | 2026-03-18 16:44:13 EDT | 2 | 1** | 1 | 1 | edit |
| 12180 | 2026-04-02 15:10:35 | 2026-04-02 08:10:35 | 2026-04-02 11:10:35 EDT | 2 | 1**20 | 1 | 1 | edit |
| 12209 | 2026-04-04 15:03:54 | 2026-04-04 08:03:54 | 2026-04-04 11:03:54 EDT | 2 | 1**20 | 1 | 1 | edit |
| 12908 | 2026-04-23 22:08:56 | 2026-04-23 15:08:56 | 2026-04-23 18:08:56 EDT | 2 | 1**20 | 1 | 1 | edit |
| **13171** | **2026-05-15 15:31:20** | **2026-05-15 08:31:20** | **2026-05-15 11:31:20 EDT** | **2** | **1**20** | **1** | **0** | **DEACTIVATION** |

### 5.2 Becky Carreon (US202603030007) — full audit history
| modify_record.id | UTC | PDT | EDT | oper_source | oper_account (masked) | bv.status | av.status | event |
|---|---|---|---|---|---|---|---|---|
| 11882 | 2026-03-03 20:38:24 | 2026-03-03 12:38:24 | 2026-03-03 15:38:24 EST | 2 | 1** | NULL | 1 | creation |
| 12214 | 2026-04-06 13:59:50 | 2026-04-06 06:59:50 | 2026-04-06 09:59:50 EDT | 2 | 1** | 1 | 1 | edit |
| 13017 | 2026-05-04 21:53:19 | 2026-05-04 14:53:19 | 2026-05-04 17:53:19 EDT | 2 | 1**20 | 1 | 1 | **edit on reported date** — status NOT changed |
| **13173** | **2026-05-15 15:32:35** | **2026-05-15 08:32:35** | **2026-05-15 11:32:35 EDT** | **2** | **1**20** | **1** | **0** | **DEACTIVATION** |

### 5.3 Tyla Baxter (US202603100008) — full audit history
| modify_record.id | UTC | PDT | EDT | oper_source | oper_account (masked) | bv.status | av.status | event |
|---|---|---|---|---|---|---|---|---|
| 11940 | 2026-03-10 19:25:51 | 2026-03-10 11:25:51 | 2026-03-10 15:25:51 EST | 2 | 1** | NULL | 1 | creation |
| **13172** | **2026-05-15 15:31:43** | **2026-05-15 08:31:43** | **2026-05-15 11:31:43 EDT** | **2** | **1**20** | **1** | **0** | **DEACTIVATION** — but `t_ehr_employee.modify_account = 1**` (mismatch, see §8 A2) |

### 5.4 Danielle Davidson (US202604280001) — full audit history
| modify_record.id | UTC | PDT | EDT | oper_source | oper_account (masked) | bv.status | av.status | event |
|---|---|---|---|---|---|---|---|---|
| 12983 | 2026-04-28 14:18:49 | 2026-04-28 07:18:49 | 2026-04-28 10:18:49 EDT | 2 | 1**20 | NULL | 1 | creation |
| **13170** | **2026-05-15 15:29:55** | **2026-05-15 08:29:55** | **2026-05-15 11:29:55 EDT** | **2** | **1**20** | **1** | **0** | **DEACTIVATION** |

### 5.5 Cross-cutting view of the 4 deactivations (today)
| Order | UTC | EDT | Employee | Δ to prior |
|---|---|---|---|---|
| 1 | 2026-05-15 15:29:55 | 11:29:55 | Danielle Davidson | — |
| 2 | 2026-05-15 15:31:20 | 11:31:20 | Alina Roberts | +85 s |
| 3 | 2026-05-15 15:31:43 | 11:31:43 | Tyla Baxter | +23 s |
| 4 | 2026-05-15 15:32:35 | 11:32:35 | Becky Carreon | +52 s |

Total window: **2 min 40 s**. Inter-action gaps of 23–85 s suggest **manual click-by-click** in a web UI, not a programmatic bulk call.

---

## 6. Operator Identity Resolution

Two distinct auth account ids appear across the 4 audit trails. **Masked by default** per the audit rules; un-masked under §9 because Finding A2 requires escalation context.

| Masked id | Unmasked | iEHR emp_no | Real name | Post / Role | Department | Email | iEHR.status today |
|---|---|---|---|---|---|---|---|
| `1**20` | 10220 | US202509220001 | Nadia Betancur | HR Business Partner | 1114 — Human Resources Department (US) | nadia.betancur@luckincoffee.us | 1 (active) |
| `1**` | 131 | US202504260001 | Yanwen Zhou | HR Business Partner | 1114 — Human Resources Department (US) | yolanda.zhou@luckincoffee.us | **0 (deactivated)** |

**Both operators are/were HR Business Partners in the US HR department** — appropriate authority for deactivation. **No service / system / root account** appears in the audit trail. **`1**20` (Nadia) performed all four status flips today.** `1**` (Yanwen Zhou) appears as the operator on several pre-2026-04-25 edits and shows up anomalously on Tyla's `t_ehr_employee.modify_account` field — see Finding A2.

---

## 7. Timing Reconciliation

| Employee | Reported (stakeholder) | DB flip (UTC) | DB flip (PDT) | DB flip (EDT) | Δ days reported → DB | Operator (audit row) | Operator (employee row) | Channel | Status flips total | Dimission application? |
|---|---|---|---|---|---|---|---|---|---|---|
| Tyla Baxter | 2026-05-11 | 2026-05-15 15:31:43 | 2026-05-15 08:31:43 PDT | 2026-05-15 11:31:43 EDT | **+4** | 1**20 (Nadia Betancur) | 1** (Yanwen Zhou) ⚠ | oper_source=2 (UI/backend) | 1 (1→0) | **NO** |
| Alina Roberts | 2026-05-08 | 2026-05-15 15:31:20 | 2026-05-15 08:31:20 PDT | 2026-05-15 11:31:20 EDT | **+7** | 1**20 (Nadia Betancur) | 1**20 (consistent) | oper_source=2 (UI/backend) | 1 (1→0) | **NO** |
| Becky Carreon | 2026-05-04 | 2026-05-15 15:32:35 | 2026-05-15 08:32:35 PDT | 2026-05-15 11:32:35 EDT | **+11** | 1**20 (Nadia Betancur) | 1**20 (consistent) | oper_source=2 (UI/backend) | 1 (1→0); plus a no-status edit on 2026-05-04 21:53 UTC | **NO** |
| Danielle Davidson | 2026-05-02 | 2026-05-15 15:29:55 | 2026-05-15 08:29:55 PDT | 2026-05-15 11:29:55 EDT | **+13** | 1**20 (Nadia Betancur) | 1**20 (consistent) | oper_source=2 (UI/backend) | 1 (1→0) | **NO** |

**Interpretation.** The reported dates are almost certainly the **operational separation dates** (last shift worked at the store). The DB record was back-filled today, **4–13 calendar days after the fact**, in a single short clicking session by Nadia. Becky's 05/04 21:53 UTC touch may have been an attempted-but-aborted termination — Nadia opened the record on the reported date but the actual `status=1→0` only landed today.

---

## 8. Anomaly Findings & Flags

### A1 — **HIGH** — Reported dates ≠ actual DB dates; iEMP carried stale "active" employees for up to 13 days
**Evidence:** §5, §7, audit rows 13170/13171/13172/13173.
**Impact.**
- Any downstream consumer of `t_ehr_employee.status` (payroll exports, scheduling, badge/access, store rosters) saw these employees as active up to today.
- External audit or compliance review will see a 1→0 transition on 05/15, not on the actual separation dates — creating a paper-trail divergence from the reported HR record.
**Action:** confirm with HR whether the reported dates are "last working day" — if yes, see Recommendation R1 (run the dimission-application workflow retroactively so `last_working_day` and `effective_date` are recorded for the four).

### A2 — **MEDIUM** — Operator-attribution mismatch on Tyla Baxter
**Evidence:**
- `t_ehr_employee_modify_record.id=13172` → `oper_account = 10220` (Nadia)
- `t_ehr_employee.id=5134.modify_account = 131` (Yanwen Zhou — herself now `status=0`)
- The other three employees have matching `modify_account` and `oper_account` (both = 10220).
- Tyla's record had only **one prior modify_record row** (the 2026-03-10 creation by 131); there was no intervening UPDATE between then and today.
**Most likely root cause.** An application bug in the iEMP service layer: the UPDATE path that flips `status` from 1→0 (or the dedicated "deactivate" endpoint) **fails to refresh `modify_account` to the current actor** when the prior value was the creator. The audit row correctly captures Nadia via the API request context, but the row update reuses the existing `modify_account` value (Yanwen) because Tyla had never been edited since creation. The other three employees were edited multiple times by Nadia in March/April, which had already refreshed their `modify_account` to 10220 — masking the bug there.
**Why this matters even if it's a bug.** Any downstream report that joins on `t_ehr_employee.modify_account` (rather than on the audit log) would attribute Tyla's deactivation to a deactivated HR BP — corrupting any "who deactivated whom" report.
**Not sufficient to assert misuse.** No evidence of impersonation or session sharing. But un-masking under §9 is warranted for HRIT escalation.

### A3 — **HIGH** — Standard offboarding workflow bypassed (4/4)
**Evidence:**
```sql
SELECT COUNT(*) FROM luckyus_iehr.t_ehr_employee_dimission_application
 WHERE dimission_emp_no IN ('US202511180007','US202603030007','US202603100008','US202604280001');
-- 0
```
Other recent terminations (e.g., US202604280004, entered by Nadia on 2026-05-11) **do** go through `t_ehr_employee_dimission_application` with `last_working_day`, `effective_date`, `dimission_reason_code`, etc. The four in scope here went through a **direct status flip** instead. Consequence: there is no recorded reason, no last_working_day, no handover_emp_no, no attachment — all of which the iEMP UI is supposed to capture during offboarding.

### A4 — **MEDIUM** — Auth accounts not deactivated alongside employee records
**Evidence:** all four `t_luckyauth_account` rows still show `status=2`, `delete_time = NULL`, and `last_modify_time = create_time`. No `t_permission_account_history` rows reflect a deactivation.
**Impact.** If `t_luckyauth_account.status=2` permits authentication (semantics need confirmation from the auth-API team), these four former employees retain a path to authenticate. If `status=2` blocks login, the impact is purely cosmetic. **Auth team confirmation needed.**

### A5 — **LOW** — Non-status touch on Becky on the reported date
Becky's audit row `id=13017` shows a 2026-05-04 21:53:19 UTC edit by Nadia (oper_account 10220) that did **not** change status (1→1). This explains why the HR stakeholder remembers 05/04 for Becky — Nadia did open the record that day. The actual deactivation only landed 11 days later (today).

### A6 — **INFO** — Operator role appropriateness
Both operators are/were HR Business Partners in the US HR department (dept 1114). No service/system account (`svc_*`, `system`, `admin`, `root`) appears in the trail. No cross-functional operator (e.g., someone from store ops directly flipping their own report). From an "who was authorized" standpoint, this is clean.

### A7 — **INFO** — Schema limitations
`t_ehr_employee_modify_record` does **not** capture `operator_ip`, `user_agent`, or `request_id`. `oper_source` has only one observed value (`2`) across the entire 4181-row table. We **cannot** distinguish web UI vs API client vs direct SQL from the audit evidence alone. If those metadata fields are needed, they would have to come from upstream app logs (iEMP backend logs / API gateway logs), not from the database.

### A8 — **INFO** — No reactivations
None of the four employees has a 0→1 transition in history. The 1→0 flip is final per the current data.

---

## 9. Recommended Next Steps

### R1 — Retroactively file dimission applications (HIGH)
For each of the 4, have HR file a `t_ehr_employee_dimission_application` with the **operationally-correct** `last_working_day` (the stakeholder-reported date) and a reason code, so the formal record matches reality. This is the only way the HR-system-of-record carries the right separation dates.
- Tyla → last_working_day 2026-05-11
- Alina → last_working_day 2026-05-08
- Becky → last_working_day 2026-05-04
- Danielle → last_working_day 2026-05-02

### R2 — Deactivate the auth accounts (HIGH if `status=2` permits login)
Confirm `t_luckyauth_account.status=2` semantics with the auth-API team. If `status=2` does not block authentication, set status to `0` (or whatever the "disabled" code is) and populate `delete_time = NOW()` for the 4 auth accounts (ids 10371, 10615, 10638, 10756). **This is a write the DBA does NOT have authority to make from this audit; it should be done via the iEMP UI by HR.**

### R3 — Escalate Finding A2 to HRIT (MEDIUM)
Un-masking under this section (justified by A2):
- The mismatched row is for Tyla Baxter (iEHR id 5134, emp_no US202603100008).
- Audit oper_account = **10220 (Nadia Betancur)**.
- Employee row modify_account = **131 (Yanwen Zhou)** — herself currently `status=0`.
Ask HRIT / the iEMP service team to review the UPDATE path for the deactivate operation: it appears to leave `t_ehr_employee.modify_account` untouched when the prior value was the creator and no intervening edits occurred. This is a low-severity application bug but it **corrupts attribution reports**.

### R4 — Operational SLA on iEMP back-filling (MEDIUM)
The 4–13 day gap between reported separation and DB record indicates HR is doing batch back-fills rather than same-day data entry. Recommend establishing a **same-day or next-business-day SLA** for iEMP deactivation, gated by the dimission_application workflow (R1) rather than a direct status flip.

### R5 — Schema improvement (LOW)
`t_ehr_employee_modify_record` would be substantially more auditable if it captured `operator_ip`, `user_agent`, `request_id`, and a meaningful `oper_source` (with distinct codes for UI / API / batch / SQL). Currently the table is uniformly `oper_source=2`, which provides zero channel attribution. This is a longer-horizon engineering ask.

### R6 — Data gaps remaining
- Channel of the deactivations (browser vs API client vs direct SQL) — **not derivable from DB schema**; need iEMP backend / API gateway logs from 2026-05-15 15:29–15:33 UTC.
- IP address of Nadia's session during the flips — same upstream-log source.
- Whether `t_luckyauth_account.status=2` permits authentication — auth-API team semantics.

---

## 10. Appendix: Raw Query Log

Every SELECT in execution order. All queries read-only. Server names per `CLAUDE.md`. Row counts as returned.

| # | Server | Query | Rows |
|---|---|---|---|
| 1 | aws-luckyus-iadmin-rw | `SELECT @@global.time_zone, @@session.time_zone, @@system_time_zone, NOW(), UTC_TIMESTAMP(), @@hostname, VERSION();` | 1 |
| 2 | aws-luckyus-iadmin-rw | `SHOW DATABASES;` | 6 |
| 3 | aws-luckyus-iadmin-rw | `SELECT table_name, table_rows, create_time, update_time FROM information_schema.tables WHERE table_schema='luckyus_iadmin' ORDER BY table_name;` | 25 (no user table) |
| 4 | aws-luckyus-iehr-rw | TZ + hostname check | 1 |
| 5 | aws-luckyus-iehr-rw | `SHOW DATABASES;` | 6 |
| 6 | aws-luckyus-ipermission-rw | `SHOW DATABASES;` | 6 |
| 7 | aws-luckyus-iluckyauthapi-rw | `SHOW DATABASES;` | 6 |
| 8 | aws-luckyus-iehr-rw | `SELECT table_name … FROM information_schema.tables WHERE table_schema='luckyus_iehr' AND (table_name LIKE '%user%' OR …) ORDER BY table_name;` | 39 |
| 9 | aws-luckyus-ipermission-rw | same pattern on luckyus_ipermission | 11 |
| 10 | aws-luckyus-iluckyauthapi-rw | same pattern on luckyus_iluckyauthapi | 0 |
| 11 | aws-luckyus-iehr-rw | `SHOW COLUMNS FROM luckyus_iehr.t_ehr_employee;` | 73 |
| 12 | aws-luckyus-iehr-rw | `SHOW COLUMNS FROM luckyus_iehr.t_ehr_employee_modify_record;` | 13 |
| 13 | aws-luckyus-ipermission-rw | `SHOW COLUMNS FROM luckyus_ipermission.t_luckyauth_account;` | 37 |
| 14 | aws-luckyus-ipermission-rw | `SHOW COLUMNS FROM luckyus_ipermission.t_permission_account_history;` | 9 |
| 15 | aws-luckyus-iehr-rw | sample 3 rows from `t_ehr_employee_modify_record` ORDER BY id DESC | 3 (matched 3 of 4 targets — Tyla, Becky, Alina) |
| 16 | aws-luckyus-ipermission-rw | sample 3 rows from `t_permission_account_history` ORDER BY id DESC | 3 |
| 17 | aws-luckyus-iehr-rw | `SELECT … FROM t_ehr_employee WHERE name IN (…) OR (first_name … AND last_name …) OR email LIKE …;` | **4** (all targets) |
| 18 | aws-luckyus-ipermission-rw | `SELECT … FROM t_luckyauth_account WHERE employee_name IN (…) OR email LIKE …;` | **4** (all targets) |
| 19 | aws-luckyus-iehr-rw | full audit history: `SELECT … FROM t_ehr_employee_modify_record WHERE emp_no IN (4 targets) ORDER BY emp_no, oper_time;` | 15 |
| 20 | aws-luckyus-ipermission-rw | `SELECT … FROM t_permission_account_history WHERE account_id IN (10371,10615,10638,10756) ORDER BY account_id, create_time;` | 6 |
| 21 | aws-luckyus-iehr-rw | `SELECT status, COUNT(*) FROM t_ehr_employee GROUP BY status;` | 2 (1: 1184; 0: 280) |
| 22 | aws-luckyus-ipermission-rw | `SELECT status, COUNT(*) FROM t_luckyauth_account GROUP BY status;` | 3 (1: 1011; 2: 284; 0: 194) |
| 23 | aws-luckyus-iehr-rw | `SELECT … JSON_EXTRACT(before_value,'$.status'), JSON_EXTRACT(after_value,'$.status') … FROM t_ehr_employee_modify_record WHERE emp_no IN (4 targets) ORDER BY emp_no, oper_time;` | 15 (status flip confirmed: bv=1, av=0 on the 4 today-rows) |
| 24 | aws-luckyus-iehr-rw | `SHOW COLUMNS FROM t_ehr_employee_dimission_application;` | 21 |
| 25 | aws-luckyus-iehr-rw | `SELECT id, emp_no, after_value FROM t_ehr_employee_modify_record WHERE id IN (13170,13171,13172,13173);` | 4 (full JSON examined — no dimissionDate field exists in employee record) |
| 26 | aws-luckyus-iehr-rw | `SELECT … FROM t_ehr_employee_dimission_application WHERE dimission_emp_no IN (4 targets) …;` | **0** |
| 27 | aws-luckyus-iehr-rw | `SELECT … FROM t_ehr_employee_dimission_application WHERE create_time >= '2026-05-01' ORDER BY create_time;` | 48 (none with target emp_nos; mostly 2026-05-08 05:58:59 backfill) |
| 28 | aws-luckyus-ipermission-rw | `SELECT id, emp_no, employee_name, … FROM t_luckyauth_account WHERE id IN (10220, 131);` | 2 (operator identities) |
| 29 | aws-luckyus-iehr-rw | `SELECT … FROM t_ehr_employee WHERE emp_no IN ('US202509220001','US202504260001');` | 2 (operator iEHR profiles) |
| 30 | aws-luckyus-iehr-rw | `SELECT belong_dept_id, COUNT(*) FROM t_ehr_employee WHERE emp_no IN (operators + 4 targets) GROUP BY belong_dept_id;` | 5 (dept inventory) |
| 31 | aws-luckyus-iehr-rw | `SHOW COLUMNS FROM t_ehr_department;` | 17 |
| 32 | aws-luckyus-iehr-rw | `SHOW COLUMNS FROM t_ehr_post;` | 11 |
| 33 | aws-luckyus-iehr-rw | dept lookup for ids 1114, 1127, 1141, 20010, 20027 | 5 |
| 34 | aws-luckyus-iehr-rw | `SELECT epr.emp_no, p.name AS post_name … FROM t_ehr_employee_post_relation epr LEFT JOIN t_ehr_post p ON p.id=epr.post_id WHERE epr.emp_no IN (6 emp_nos);` | 6 |
| 35 | aws-luckyus-ipermission-rw | `SELECT account_id, dept_id FROM t_permission_account_dept_relation WHERE account_id IN (131,10220);` | 1 (Nadia in dept null; Yanwen has no row) |
| 36 | aws-luckyus-iehr-rw | `SELECT oper_source, COUNT(*), MIN(oper_time), MAX(oper_time) FROM t_ehr_employee_modify_record GROUP BY oper_source;` | 1 (oper_source=2 universally, 4181 rows) |
| 37 | aws-luckyus-iehr-rw | `SELECT … FROM t_ehr_employee_modify_record WHERE oper_time BETWEEN '2026-05-15 15:25:00' AND '2026-05-15 15:35:00';` | 4 (the exact 4 deactivations — no other events in that window) |
| 38 | aws-luckyus-iehr-rw | join `t_ehr_employee` + latest `t_ehr_employee_modify_record` for the 4 targets | 4 (used to spot Tyla's modify_account discordance) |

Savepoints written to `/app/savepoints/`:
- `SAVEPOINT_1_discovery.md`
- `SAVEPOINT_2_schema.md`
- `SAVEPOINT_3_users.md`
- `SAVEPOINT_4_audit.md`
- `SAVEPOINT_5_reconciliation.md`

---

*End of report. Read-only audit. No writes performed.*
