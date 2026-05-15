# SAVEPOINT 5 — Operator resolution + timing reconciliation

## Operator identity

| auth account_id (masked) | unmasked | iEHR emp_no | iEHR name | iEHR status | post | dept | email |
|---|---|---|---|---|---|---|---|
| `1**20` (10220) | 10220 | US202509220001 | Nadia Betancur | 1 (active) | **HR Business Partner** | 1114 — Human Resources Department (US) | nadia.betancur@luckincoffee.us |
| `1**` (131) | 131 | US202504260001 | Yanwen Zhou | **0 (deactivated)** | HR Business Partner | 1114 — Human Resources Department (US) | yolanda.zhou@luckincoffee.us |

Both operators are/were HR Business Partners — the department empowered to deactivate employees. Yanwen Zhou's own employee record went status=0 around 2026-04-25, but her auth account id 131 is still being recorded on Tyla's employee-row `modify_account` field today (see anomaly A2 below).

## Reconciliation table (UTC ↔ PT/ET, May 2026 → PDT UTC-7, EDT UTC-4)

| Employee | Reported | DB UTC (status 1→0) | DB PDT | DB EDT | Δ from reported (calendar days) | Operator (audit) | Operator (employee row) | Channel | # flips | Dimission application? |
|---|---|---|---|---|---|---|---|---|---|---|
| Tyla Baxter | 05/11 | 2026-05-15 15:31:43 | 2026-05-15 08:31:43 PDT | 2026-05-15 11:31:43 EDT | **+4 days late** | 1**20 (Nadia Betancur) | 1** (Yanwen Zhou) ⚠ mismatch | oper_source=2 (UI) | 1 | **NO** |
| Alina Roberts | 05/08 | 2026-05-15 15:31:20 | 2026-05-15 08:31:20 PDT | 2026-05-15 11:31:20 EDT | **+7 days late** | 1**20 (Nadia Betancur) | 1**20 (consistent) | oper_source=2 (UI) | 1 | **NO** |
| Becky Carreon | 05/04 | 2026-05-15 15:32:35 | 2026-05-15 08:32:35 PDT | 2026-05-15 11:32:35 EDT | **+11 days late** | 1**20 (Nadia Betancur) | 1**20 (consistent) | oper_source=2 (UI) | 1 (+ a non-status edit on 05/04 21:53 UTC by same operator) | **NO** |
| Danielle Davidson | 05/02 | 2026-05-15 15:29:55 | 2026-05-15 08:29:55 PDT | 2026-05-15 11:29:55 EDT | **+13 days late** | 1**20 (Nadia Betancur) | 1**20 (consistent) | oper_source=2 (UI) | 1 | **NO** |

## Batch-pattern test (same operator, same minute window?)
- 4/4 share `oper_account = 10220` in the audit log.
- 4/4 fall inside a **2-minute-40-second window** (15:29:55 → 15:32:35 UTC).
- Order observed (suggests UI-driven, sequential, manually-clicked):
  1. 15:29:55 — Danielle Davidson
  2. 15:31:20 — Alina Roberts (85 s after #1)
  3. 15:31:43 — Tyla Baxter (23 s after #2)
  4. 15:32:35 — Becky Carreon (52 s after #3)
- Inter-action gaps (23–85 s) are consistent with **a human navigating a web UI and clicking "deactivate" on each employee one at a time**, not a single bulk API call. So this is a **clustered manual batch**, not a programmatic bulk operation.

## Anomalies / flags

### A1 — CRITICAL: Reported dates ≠ actual DB dates
All four DB deactivations occurred today (2026-05-15 ~11:30 EDT). Reported dates are 4–13 calendar days earlier. Most plausible interpretation: the reported dates are **operational separation dates** (last shift worked at store) and HR is **back-filling iEMP today**. This means iEMP status reflected stale "active" employees for up to 13 days, with downstream blast radius on:
- payroll exports (any system that consumes `t_ehr_employee.status`)
- access-control (auth account `t_luckyauth_account` was never touched — these employees can technically still authenticate if accounts ever activate)
- compliance/audit (an external auditor will see a 1→0 transition on 05/15, not on the actual separation date)

### A2 — WARNING: Operator mismatch on Tyla Baxter
- `t_ehr_employee_modify_record.id=13172.oper_account = 10220` (Nadia)
- `t_ehr_employee.modify_account = 131` (Yanwen — herself currently `status=0`)
- For the other 3, the employee row and the audit row agree.
- Possible explanations:
  - The UPDATE statement wrote `modify_account = 131` (stale value carried from prior INSERT — Tyla was created by 131 in March, and there was no intervening UPDATE to overwrite). Tyla's modify_record table only had 1 prior row (the creation) by 131, and the audit-row insert may have populated `oper_account` from the request context while the employee-row UPDATE used a different field (e.g., the existing modify_account column was never reset to the actor).
  - Less likely: impersonation or session-token reuse by Nadia of Yanwen's old account in some legacy flow.
- This is **not** sufficient to assert misuse; it likely indicates a **service-layer bug** in iEMP — the UPDATE statement either (a) does not always set `modify_account = current_user_id` on every code path, or (b) ran a different path for first-status-flip vs subsequent edits.

### A3 — WARNING: Standard offboarding workflow bypassed (4/4)
No row exists in `t_ehr_employee_dimission_application` for any of the 4. Other recent terminations (e.g., US202604280004 entered by Nadia on 2026-05-11) do go through that table with `last_working_day`, `effective_date`, `dimission_reason_code`. The 4 in question were deactivated by directly flipping `t_ehr_employee.status` without filing a dimission application. This is a **process compliance gap**.

### A4 — INFO: Auth account not touched
`t_luckyauth_account.status` is still `2` for all 4, `delete_time IS NULL`, and `last_modify_time = create_time`. If `status=2` permits login (rather than denying it), these former employees may still have a path to authenticate to internal systems. Worth confirming with the auth-API team.

### A5 — INFO: Same-operator anomalies on Becky's record
Becky has an additional row on **2026-05-04 21:53:19 UTC** by oper_account 10220 (Nadia) where the status remained 1→1. This indicates Nadia opened/saved Becky's record on the reported 05/04 date but did NOT deactivate. The actual deactivation only landed 11 days later. Possible interpretations: a partial edit (e.g., dept change), a UI bug, or an attempted-but-not-completed termination.

### A6 — INFO: Operator role appropriateness
Both operators (Nadia, Yanwen) are/were **HR Business Partners**, which is the correct authority for status changes. **No service/system account** (no `svc_*`, `system`, `root`) was used. No anomalous departmental cross-over. From a who-was-authorized standpoint, this is clean.

### A7 — N/A: Operator IP / user-agent
Schema does not capture `operator_ip`, `user_agent`, or `request_id`. Cannot evidence the channel (browser vs API) beyond `oper_source=2` — which has only one value across the entire 4181-row table and therefore cannot distinguish channels.

## Severity ranking

| Tag | Severity | Finding |
|---|---|---|
| A1 | **HIGH** | DB lags reported dates by 4–13 days for all 4 |
| A2 | **MEDIUM** | Tyla row carries `modify_account=131` while audit row shows `oper_account=10220` |
| A3 | **HIGH** | Offboarding workflow bypassed — no dimission_application rows |
| A4 | **MEDIUM** | Auth accounts (`t_luckyauth_account`) not deactivated alongside employee record |
| A5 | LOW | Non-status edit on Becky on 05/04 by same operator — explains why HR thinks 05/04 |
| A6 | INFO | Operator role appropriate (HR BP, not service account) |
| A7 | INFO | Schema does not capture IP/UA — cannot evidence channel |
