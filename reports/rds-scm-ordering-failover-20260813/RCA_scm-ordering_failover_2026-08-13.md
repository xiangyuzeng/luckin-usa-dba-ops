# RCA — aws-luckyus-scm-ordering-rw Multi-AZ Failover (2026-08-13)

**Alert**: 【DB告警】AWS RDS 发生重启或者主从切换_语音 — P0 (legacy policy id=93)
**Instance**: `aws-luckyus-scm-ordering-rw` | **Verdict**: ✅ **TRUE POSITIVE**
**Investigated**: 2026-08-13 ~22:00–22:45 UTC | **DBA**: 曾翔宇 (David Zeng)

---

## 1. Summary

The instance genuinely restarted via a Multi-AZ failover. AWS's own reason was
**"The RDS Multi-AZ primary instance is busy and unresponsive."**

Root cause: **EBS throughput credit (`EBSByteBalance%`) exhaustion on an undersized
db.t4g.micro.** The instance's 128 MB InnoDB buffer pool cannot hold a ~800 MB working
set, so nearly every read becomes a physical EBS read. A workload step-change at
~13:00 UTC pushed sustained physical reads above the t4g.micro's baseline EBS throughput
allowance; credits drained linearly to zero over 8.5 hours, EBS I/O was throttled to
baseline, the primary stopped servicing I/O, and RDS failed it over.

This is **not** a CPU, memory, connection, or lock event — all of those were flat and normal.

**This is the second instance to fail this exact way today** (`aws-luckyus-iopocp-rw`
failed over earlier on 2026-08-13 with the same signature). Same instance class, same
mechanism.

### ⚠️ Recurrence risk — the workload is still running

Post-failover the credit bucket reset to 99%, but read load resumed immediately
(ReadIOPS 74 → 151) and the balance is **already declining (99% → 98%)**. At the
observed drain rate (~11.6 %/hour) credits exhaust again around
**06:00–07:00 UTC 2026-08-14 (02:00–03:00 EDT)** — another failover overnight unless
action is taken.

---

## 2. Timeline (UTC)

| Time | Event |
|------|-------|
| 03:36–03:39 | Routine automated backup (unrelated) |
| ~13:00 | **Workload step-change.** ReadIOPS 5–25 → 70–130; ReadThroughput 30–150 KB/s → 400–970 KB/s; slow-query rate 10 → ~90 per 30 min. `EBSByteBalance%` begins monotonic decline from 99% |
| 16:00:24–16:00:52 | Burst of 33 × `MAX(dt)` scans on `t_shop_order_calendar_warehouse_history`, each examining ~150–160K rows. Read peak 3.37 MB/s; 297 slow queries in that 30-min bin |
| 21:30–21:35 | `EBSByteBalance%` reaches **0%** → EBS I/O throttled to baseline |
| 21:39–21:54 | **Metric hole** — instance stops reporting (evidence of unresponsiveness). 1,111 slow queries logged in the 21:30 bin as all I/O stalls |
| 21:55:26 | Multi-AZ instance failover **started** |
| 21:55:55 | DB instance restarted |
| 21:56:21 | "Primary instance is busy and unresponsive" + **failover completed** |
| 21:57 | Zeus P0 alert fired |
| 22:00+ | Credits reset to 99%; **ReadIOPS back to 151 — drain restarting** |

**Unavailability: ~55 seconds** (21:55:26 → 21:56:21).

---

## 3. Evidence

### 3.1 It was the byte (throughput) allowance, not IOPS
| Metric | Behaviour 13:00 → 21:35 |
|--------|--------------------------|
| `EBSByteBalance%` | **99% → 0%**, monotonic ← exhausted |
| `EBSIOBalance%` | flat ~74–75% ← never at risk |
| `BurstBalance` | no datapoints (gp3 volume — not applicable) |
| `CPUUtilization` | 6–11%, flat |
| `FreeableMemory` | ~90–108 MB, stable (no leak/drop) |
| `DatabaseConnections` | 13–18, stable |
| `ReadLatency` | ~0.7 ms, stable until throttle |

CPU, memory and connections rule out the usual failover causes. The only metric that
moved to a limit was the EBS byte credit.

### 3.2 The instance is memory-starved
| Fact | Value |
|------|-------|
| Instance class | `db.t4g.micro` (1 GB RAM, 2 vCPU) |
| `innodb_buffer_pool_size` | **128 MB** |
| Schema size (`luckyus_scm_ordering`) | ~800 MB |
| Largest table `t_auto_order_small_log` | **243.6 MB** (1.69M rows; 144 MB of that is index) |
| Buffer pool hit ratio (since restart) | **92.9%** (healthy is >99%) |

The single largest table is ~2× the entire buffer pool. Caching is impossible, so read
traffic goes to EBS continuously.

**Note on the 128 MB pool:** this is *not* a parameter-group defect. `luckyus-prod-84`
leaves `innodb_buffer_pool_size` at the engine default, and MySQL auto-sizes it from
detected RAM (verified: `aws-luckyus-salesmarketing-rw`, db.t4g.xlarge on the *same*
parameter group, runs an 11,520 MB pool). A t4g.micro falls into MySQL's ≤1 GB tier,
which pins the pool at 128 MB. **Therefore scaling the instance class automatically
fixes the buffer pool** — no parameter change needed.

### 3.3 Query-level offenders

**(a) Missing composite index — `t_shop_order_calendar_warehouse_history` (260K rows)**

```sql
SELECT max(dt) FROM t_shop_order_calendar_warehouse_history
WHERE shop_dept_id = ? AND wh_dept_id = ? AND tenant = 'LKUS';
-- Rows_examined: 152,951–160,384   Rows_sent: 1
```
Existing indexes are all **single-column**: `idx_shop`(card 24), `idx_warehouse`(card 4),
`idx_dt`(card 113), `idx_operated_time`. With no composite index the optimizer walks
`idx_dt` descending and filters, examining ~60% of the table to return one value. Run in
a per-store loop (33 executions in 28 seconds at 16:00).

**(b) Unusable index prefix — `t_auto_order_small_log` (1.69M rows, 243.6 MB)**

```sql
SELECT small_class_mid FROM t_auto_order_small_log
WHERE shop_dept_id = ? AND order_date = ? AND tenant = ?;
-- 143 ms average per execution, ~214 rows returned
```
The only secondary index is `uniq_shop_small_order_date` =
`(shop_dept_id, small_class_mid, order_date, tenant)`. The query does **not** filter on
`small_class_mid` (position 2), so only the `shop_dept_id` prefix is usable; MySQL then
scans every entry for that shop. This is the **top table by reads** (14,133 reads since
restart — more than all other tables combined).

### 3.4 Honest limitation

I could not attribute the full sustained 80–150 ReadIOPS to a single statement.
`performance_schema` was reset by the 21:55 restart (only ~20 min of history survives),
and `long_query_time = 0.1` means the slow log cannot see the many sub-100 ms statements
that make up the bulk of the I/O. The dominant *table* is unambiguous
(`t_auto_order_small_log`), and the two queries above are confirmed offenders, but the
precise trigger for the 13:00 UTC step-change is not pinned down.

**→ Action for Ops team:** was anything deployed, or did any batch/job schedule change,
around **13:00 UTC (09:00 EDT) on 2026-08-13**?

### 3.5 Fleet check — no other instance at risk right now

Swept `EBSByteBalance%` across all RDS instances (lowest 15). `scm-ordering` is the sole
outlier at 0–5%; **every other instance sits at 99–100%**, including `iopocp` (recovered).
61 instances share parameter group `luckyus-prod-84`, of which **32 are db.t4g.micro** —
the same class that has now caused two failovers in one day.

---

## 4. Recommendations

| Pri | Action | Owner | When |
|-----|--------|-------|------|
| **P0** | **Scale `aws-luckyus-scm-ordering-rw` → `db.t4g.medium`.** 4 GB RAM lifts the buffer pool to ~2 GB (caches the whole ~800 MB working set → physical reads collapse) *and* raises the EBS baseline throughput. Multi-AZ, so apply as a rolling modify (~1 min interruption). `db.t4g.small` is the bare minimum; medium gives headroom. | DBA + Michael | **Before 02:00 EDT tonight** |
| **P1** | Add composite index — turns the 160K-row scan into a single seek:<br>`ALTER TABLE t_shop_order_calendar_warehouse_history ADD INDEX idx_shop_wh_tenant_dt (shop_dept_id, wh_dept_id, tenant, dt);` | DBA | After scale-up, low-traffic window |
| **P1** | Add covering index — makes the hot query index-only:<br>`ALTER TABLE t_auto_order_small_log ADD INDEX idx_shop_date_tenant_class (shop_dept_id, order_date, tenant, small_class_mid);` | DBA | After scale-up, low-traffic window |
| **P1** | Confirm the 13:00 UTC workload change with Ops (deploy? job schedule?) | Ops | 24 h |
| **P2** | Retention/archival for `t_auto_order_small_log` (243.6 MB of log data, 144 MB of it index). Trimming it shrinks the working set more than any other single change. | DBA + SCM dev | 1 week |
| **P2** | **Add CloudWatch alarm `EBSByteBalance% < 30%` on all burstable RDS instances.** Today's drain gave ~5 hours of warning that nobody saw, and this one metric predicted *both* of today's failovers. Highest-value monitoring gap. | DBA | 1 week |
| **P2** | Review the other 31 `db.t4g.micro` instances for any carrying >1 GB working sets | DBA | 2 weeks |

> Do the DDL **after** the scale-up: both `ALTER`s are online (`ALGORITHM=INPLACE`) but
> I/O-heavy, and running them on the current t4g.micro would burn the very credits we are
> trying to protect.

---

## 5. Key diagnostic lessons

1. **A metric hole is evidence, not missing data.** The 21:39–21:54 gap in every
   CloudWatch series *is* the unresponsiveness.
2. **Slow-query count can be a symptom, not a cause.** With `long_query_time = 0.1`,
   trivial statements (`SELECT 1`, `SELECT @@session.transaction_read_only`) flood the log
   once I/O stalls. The 1,111-query spike at 21:30 was the throttle, not the trigger.
3. **On burstable instances, check the credit metrics before CPU.** Both failovers today
   showed normal CPU/memory; only `EBSByteBalance%` moved.
4. **Small instance class → small buffer pool → amplified physical I/O.** On t4g.micro the
   128 MB pool turns an ordinary query mix into a sustained EBS load.

---
*Investigation completed 2026-08-13 22:45 UTC. Skill: RDS Alert Investigation SOP v2.0.*
