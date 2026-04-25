# Phase 2E — Lock-wait chain reconstruction at peak

## Result: NO lock contention. The spike was CPU + write-IOPS bound, not lock bound.

## Evidence

### 1. Live state at 18:14 UTC (5h post-spike)
- `information_schema.innodb_trx`: **0 rows** (no active transactions).
- `performance_schema.data_lock_waits`: **0 rows** (no current wait edges).
Live state is cold; this only confirms there is no residual lock at the time of inspection.

### 2. Performance Schema events_waits_history_long
Cannot be queried for the spike window — performance_schema retention is too short
(default 10000 rows; our writer ingested >10K events in 8 minutes during the burst).
Same overwrite problem as `events_statements_summary_by_digest`.

### 3. INNODB_METRICS counters (cumulative)
```
lock_deadlocks         : 0
lock_timeouts          : 0
lock_row_lock_waits    : 2418
lock_row_lock_time_avg : 11   (ms)
trx_active_transactions: 0    (metric module disabled — not literally 0)
trx_rseg_history_len   : 0    (metric module disabled)
```
- `lock_deadlocks=0` AND `lock_timeouts=0` → in the entire instance lifetime
  there has been **no deadlock and no lock-wait timeout**.
  `innodb_lock_wait_timeout=20s` would have fired if a transaction had blocked
  another for 20+ seconds. None did.
- `lock_row_lock_time_avg=11ms` is well below threshold concern.
- `lock_row_lock_waits=2418` over the instance lifetime is low.

### 4. Slow-log fingerprint lock_time values
Every entry sampled from the spike window shows `Lock_time` in the range **0-26 microseconds**.
`Lock_time` was nowhere close to `Query_time`. Specifically:
```
Query_time: 0.220016  Lock_time: 0.000003   Rows_examined: 0
Query_time: 0.140624  Lock_time: 0.000003
Query_time: 0.187914  Lock_time: 0.000026   <-- highest seen
Query_time: 0.151456  Lock_time: 0.000000
Query_time: 0.151794  Lock_time: 0.000001
```
The time was not spent waiting on row locks. It was spent on:
- CPU (parse, plan, B-tree traversal under churn, AUTO_INCREMENT serialization)
- Write to redo log (`innodb_flush_log_at_trx_commit=1`)
- Binlog fsync (`sync_binlog=1`)
- Group-commit coordination (visible as the `commit;` digest taking 0.10-0.20s in the slow log)

### 5. Head blocker?
There is **no head blocker** in the classical sense. The spike is not a single long
transaction blocking many. It is hundreds of short, independent transactions queueing
on durable-write throughput (binlog + redo log).

## Implication

The "active threads > 24" alarm signal is, mechanically, **CPU saturation forcing
threads into runnable state**, not row-lock contention.

This shifts the remediation priority away from "find and break the lock-blocker" and
toward **either reduce volume per second or add CPU + IOPS**.
