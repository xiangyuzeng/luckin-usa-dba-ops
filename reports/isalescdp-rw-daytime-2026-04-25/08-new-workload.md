# Phase 2D — New workload introduced in last 7 days?

## Result: NO new workload introduced. Hypothesis 2 is disconfirmed across every dimension.

### 1. New SQL digests (FIRST_SEEN >= 2026-04-18)
- `events_statements_summary_by_digest` was largely empty in the spike window (overwritten — see 03).
- Of the 5 digests captured post-spike, FIRST_SEEN dates are 2026-03-13 to 2026-03-20 → **all 1+ months old**.
- Cross-checked against the slow-log fingerprints: every fingerprint observed in D1
  also appears in the 2026-04-22 nighttime baseline. None first-appeared in the past week.
- **Verdict: no new digest.**

### 2. New MySQL users / privilege changes
```
user                    host    password_last_changed  account_locked
dongyao.wang            10.%    2026-01-30 02:45       N
xiangyu.zeng            10.%    2025-09-18 01:27       N
iluckyhealth_r          10.%    2025-06-18 09:47       N
monitor_exporter        10.%    2025-06-09 05:23       N
isalesmktingadm_A_w     10.%    2025-03-14 02:44       N
isalesmktingadm_A_o     10.%    2025-03-14 02:44       N
icdprealtimeuge_A_w     10.%    2025-03-10 10:00       N   <-- the writer in D1
icdprealtimeuge_A_o     10.%    2025-03-10 10:00       N   <-- the reader in D1
... (all others 2025-03-10 or older)
```
Most recent password change: **2026-01-30** — 85 days ago.
**Verdict: no new MySQL user, no privilege change.**

### 3. New / recently-touched tables
Filtering on `CREATE_TIME >= 2026-04-18` OR `UPDATE_TIME >= 2026-04-18`:
- `t_realtime_user_group_log` — created 2025-03-10 (old), updated continuously
- `t_user_state` — created 2025-03-10 (old), updated continuously
- `t_user_event_track` — created 2026-03-13 (6 weeks old), updated continuously
- `t_user_event` — created 2026-03-13 (6 weeks old), updated continuously

Both `t_user_event` and `t_user_event_track` were rebuilt on 2026-03-13 — *consistent with someone
having dropped/recreated them as part of an OPTIMIZE TABLE-equivalent cleanup* (note that
`t_user_event` AUTO_INCREMENT=395,462,219 confirms it had pre-existed as a table; the row count
of 110,538 means 99.97% of historic ids have been deleted).

No table created or touched within the last 7 days for the first time.
**Verdict: no schema additions, no table-level new workload.**

### 4. App-side deployment correlation
Cannot be verified from inside MySQL. Open question for the app team:
- Were any deployments to the iSales CDP services on/after 2026-04-18?
- Specifically: `icdprealtimeuge` deployment / config change?
- Specifically: changes to push notification fan-out at 09:00 EDT?

Even if a deployment exists, it would have to *only change traffic shape* (volume, timing) —
**not** introduce any new query — because no new digest was observed.

## Closing
Across all 4 dimensions (SQL, users, schema, deployment-correlation by query shape):
**no new workload introduced**. The spike is a volume/timing event on existing workload.
