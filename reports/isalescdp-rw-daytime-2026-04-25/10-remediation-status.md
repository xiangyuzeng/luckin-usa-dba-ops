# Phase 3 — Remediation verification (post-April-14-16 incident)

## Summary scorecard

| # | Recommendation | Status | Evidence |
|---|----------------|--------|----------|
| 1 | App-side soft-delete redesign on `t_user_event` / `t_user_event_track` | **NOT DONE** | No `is_deleted` column in either table. AUTO_INCREMENT=395M vs TABLE_ROWS=110K → 99.97% of historic rows hard-deleted. |
| 2 | OPTIMIZE TABLE post-batch | **PARTIAL — only on `t_user_event`** | `t_user_event` frag 1005% → 173% (rebuilt; CREATE_TIME 2026-03-13). `t_user_event_track` frag 234% → 202% (no rebuild visible). |
| 3 | Raise `long_query_time` from 0.1s to 1.0s | **NOT DONE** | `SHOW VARIABLES`: `long_query_time = 0.100000`. Slow-log noise during D1 (757 entries) is mostly 0.10-0.20s queries that would not log under 1.0s. |
| 4 | Connection-pool ceiling audit on top callers | **CANNOT VERIFY FROM DB SIDE** | `max_connections=4000` server side. Application pool sizes need confirmation from app team. |

## 3A — Fragmentation, current state
```
TABLE_SCHEMA          TABLE             TABLE_ROWS  data_mb  idx_mb  free_mb  frag_pct  UPDATE_TIME
luckyus_isales_cdp    t_user_event_track   147,295    30.1    11.0     83.0    201.9%   2026-04-25 18:16
luckyus_isales_cdp    t_user_event         110,538    13.5    36.1     86.0    173.2%   2026-04-25 18:16
```
- `t_user_event` improved (1005% → 173%) — table was rebuilt 2026-03-13. Fragmentation
  is already growing back, indicating continuous DELETE churn (consistent with #1 not done).
- `t_user_event_track` barely improved (234% → 202%) — **never rebuilt or optimized**.
  Both UPDATE_TIME stamps are within the last 5 minutes, so both tables are still hot.

## 3B — Soft-delete adoption check
`SHOW CREATE TABLE luckyus_isales_cdp.t_user_event`:
```
Columns: id, user_no, event_type, event_sub_type, event_value,
         event_time, tenant, create_time, modify_time, msg_id, event_state_value
```
**No `is_deleted`, no `deleted_at`, no `state` column for soft-delete.**

`SHOW CREATE TABLE luckyus_isales_cdp.t_user_event_track`:
```
Columns: id, user_no, event_type, event_name, p_os, channel, p_wifi,
         p_network_type, platform, p_referrer_title, p_device_id, p_os_version,
         p_is_first_day, p_app_version, p_title, p_screen_name, event_time,
         msg_id, event_id, tenant, create_time, modify_time
```
**No soft-delete column either.**

In the slow log: every DELETE on these tables (and `t_user_state`) is hard `DELETE FROM ...`
— no `UPDATE ... SET is_deleted=1` form anywhere.

## 3C — Parameter sanity
```
long_query_time                = 0.100000           [STILL 0.1s — rec #3 not applied]
innodb_buffer_pool_size        = 2147483648 (2 GB)  [50% of 4GB instance — sane]
max_connections                = 4000               [generous; not the bottleneck]
innodb_lock_wait_timeout       = 20                 [s — fine; no timeouts seen]
innodb_io_capacity             = 200                [LOW — gp3 provides 3000 IOPS]
innodb_io_capacity_max         = 2000               [also low vs 3000 provisioned]
innodb_thread_concurrency      = 0                  [unlimited — fine]
innodb_flush_log_at_trx_commit = 1                  [durable; commit cost present]
sync_binlog                    = 1                  [durable; commit cost present]
transaction_isolation          = READ-COMMITTED     [appropriate]
innodb_log_file_size           = 134217728 (128 MB) [conservative for write-heavy]
innodb_log_files_in_group      = 2
```

**Two parameter concerns surface during write spikes**:
- `innodb_io_capacity=200` and `_max=2000` against a gp3 volume provisioned for **3000 IOPS**
  means dirty-page flushing is throttled below the storage limit. During the D1 burst,
  observed WriteIOPS peaked at **1115** — below `_max` 2000 so this is not strictly limiting,
  but raising to `1500/3000` would let dirty pages drain faster after a burst.
- `innodb_log_file_size=128MB × 2 files = 256MB total` — small. With ~1000 WriteIOPS
  sustained, redo-log roll-over is frequent, contributing to the post-burst tail
  (WriteIOPS held ~440 for 8 min after the burst — checkpoint flushing).

## 3D — InnoDB history list / undo bloat
```
trx_rseg_history_len           = 0   (METRIC DISABLED — not real value)
trx_undo_slots_used            = 0   (METRIC DISABLED)
trx_active_transactions        = 0   (METRIC DISABLED)
trx_commits_insert_update      = 0   (METRIC DISABLED)
```
These zeros are **the metric module being disabled**, not literal values.
To enable: `SET GLOBAL innodb_monitor_enable = 'all'` (write — not done in this read-only investigation).

Inferred answer: no long-running readers were observed (innodb_trx empty at inspection).
Undo growth is unlikely to be the issue given the workload is short transactions (`commit`
appears in slow log every ~0.1-0.2s, indicating quick fsync turnover).

## Conclusions for Phase 4

- **Hypothesis 4 (remediation not applied)** evaluates to **YES, partially**:
  - #1 not done at all
  - #2 done once on the smaller table; never on the bigger fragmented one
  - #3 not done
  - #4 unknown
- **Independent finding**: `innodb_io_capacity` is misconfigured for the storage profile
  (200 vs 3000 IOPS available) — not in the original recommendation list. Adding to action plan.
