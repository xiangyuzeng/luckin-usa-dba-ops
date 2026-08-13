# RCA — aws-luckyus-scm-ordering-rw Multi-AZ Failover (2026-08-13)

**Alert**: 【DB告警】AWS RDS 发生重启或者主从切换_语音 — P0 (legacy policy id=93)
**Instance**: `aws-luckyus-scm-ordering-rw` | **Verdict**: ✅ **TRUE POSITIVE**
**Investigated**: 2026-08-13 ~22:00–23:15 UTC | **DBA**: 曾翔宇 (David Zeng)
**Version**: v2 (revised 2026-08-13 23:15 UTC)

---

## ⚠️ v2 revision notice (corrections to v1)

Two v1 conclusions were **wrong** and are corrected here:

| Item | v1 claim (❌ wrong) | v2 measured (✅ correct) |
|------|--------------------|--------------------------|
| Recurrence | "credits will exhaust again 06:00–07:00 UTC tonight" | **No recurrence.** The abnormal workload stopped; `EBSByteBalance%` has recovered to 99% |
| Working set | "~800 MB working set, 6× the buffer pool" | **Hot set is only ~114 MB** — the 128 MB pool is not even full. 800 MB is *total schema size*, not the working set |

**Cause of the error**: v1 read the 21:56–22:00 ReadIOPS rise (74→134) as the abnormal workload
resuming. It was **buffer pool warm-up after the restart**. v1 also conflated total schema size
with working set.

**Impact on conclusions**: this is **no longer an emergency change**; the recommended class drops
from db.t4g.medium to db.t4g.small (and is now optional). The failure mechanism itself is unchanged.

---

## 1. Summary

The instance genuinely restarted via a Multi-AZ failover. AWS's own reason was
**"The RDS Multi-AZ primary instance is busy and unresponsive."**

Direct cause: **EBS throughput credit (`EBSByteBalance%`) exhaustion.** From 13:00 UTC an
**abnormal read workload** ran on the instance (ReadIOPS 5–25 → 70–130, sustained), draining
`EBSByteBalance%` from 99% to 0% over 8.5 hours. At zero, EBS I/O was throttled to baseline, the
primary stopped servicing I/O, and RDS failed it over.

CPU (6–11%), memory and connections (13–18) were flat throughout — unrelated to business volume
or lock contention.

**That workload ended at the failover** (most likely interrupted by the restart), credits have
recovered to 99%, and there is **no imminent recurrence risk**. What actually needs solving is
**what the 13:00 UTC workload was**, and **the missing credit alarm**.

---

## 2. Timeline (UTC)

| Time | Event |
|------|-------|
| 03:36–03:39 | Routine automated backup (unrelated) |
| ~13:00 | **Abnormal read workload starts.** ReadIOPS 5–25 → 70–130; ReadThroughput 30–150 KB/s → 400–970 KB/s; slow-query rate 10 → ~90 per 30 min. `EBSByteBalance%` begins monotonic decline from 99% |
| 16:00:24–16:00:52 | 33 × `MAX(dt)` scans on `t_shop_order_calendar_warehouse_history` in 28 seconds, each examining ~150–160K rows. Read peak 3.37 MB/s; 297 slow queries in that 30-min bin |
| 21:30–21:35 | `EBSByteBalance%` reaches **0%** → EBS I/O throttled to baseline |
| 21:39–21:54 | **Metric hole** — instance stops reporting (evidence of unresponsiveness). 1,111 slow queries in the 21:30 bin as all I/O stalls |
| 21:55:26 | Multi-AZ instance failover **started** |
| 21:55:55 | DB instance restarted |
| 21:56:21 | "Primary instance is busy and unresponsive" + **failover completed** |
| 21:57 | Zeus P0 alert fired |
| 21:56–22:05 | Buffer pool warm-up; ReadIOPS briefly rises to 134 (**note: this is NOT the workload resuming**) |
| 22:10 onward | Warm-up ends. **ReadIOPS falls back to 7–20 (the pre-13:00 baseline) — abnormal workload confirmed ended** |
| 22:50 | `EBSByteBalance%` **back to 99%**, fully recovered |

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
| `FreeableMemory` | ~90–108 MB, stable |
| `DatabaseConnections` | 13–18, stable |
| `ReadLatency` | ~0.7 ms, stable until throttle |

### 3.2 Self-recovered after the failover (new in v2)

| Time (UTC) | 21:55 | 22:00 | 22:10 | 22:25 | 22:40 | 22:50 |
|---|---|---|---|---|---|---|
| `EBSByteBalance%` | 99 | 98 | 97 | 98 | 98 | **99** |
| ReadIOPS | 74 | 134 | 27 | 45 | 18 | **7** |
| ReadThroughput | 467 KB/s | 887 | 154 | 259 | 104 | **41 KB/s** |

Credits dipped to 97% then **recovered to 99%**; ReadIOPS returned to 7–20, the pre-13:00 baseline.
Confirmed internally: only **308 InnoDB physical reads in the 52 minutes** after the failover
(~0.1/sec).

### 3.3 Instance sizing assessment (major v2 correction)

| Item | Value |
|------|-------|
| Instance class | `db.t4g.micro` (1 GB RAM, 2 vCPU) |
| `innodb_buffer_pool_size` | 128 MB (8,192 pages × 16 KB) |
| **Steady-state data pages** | **7,123 pages ≈ 114 MB** |
| **Free pages** | **1,068 — the pool is not even full** |
| Steady-state hit ratio | **98.3%** |
| Total schema size | ~800 MB (includes cold data; *not* the working set) |
| Largest table `t_auto_order_small_log` | 243.6 MB (1.69M rows) |

**Conclusion: there is no memory bottleneck in steady state.** The ~114 MB hot set fits in the
128 MB pool with room to spare.

> v1 recorded a 92.9% hit ratio — that was sampled 385 s after the restart with a cold cache and
> is not representative of steady state.

**On the 128 MB pool:** this is *not* a parameter-group defect. `luckyus-prod-84` leaves
`innodb_buffer_pool_size` unset and MySQL auto-sizes it from detected RAM (verified by
counter-example: `aws-luckyus-salesmarketing-rw`, db.t4g.xlarge on the *same* group, runs an
11,520 MB pool).

### 3.4 EBS bandwidth arithmetic (new in v2)

Verified against AWS published specs:

| Class | EBS baseline bandwidth | Baseline throughput | Burst max |
|-------|------------------------|---------------------|-----------|
| t4g.micro (current) | 87 Mbps | **10.88 MB/s** | 260.62 MB/s |
| t4g.small | 174 Mbps | ~21.7 MB/s | 260.62 MB/s |
| t4g.medium | 347 Mbps | 43.38 MB/s | 260.62 MB/s |

**Measured during the incident: 0.4–0.97 MB/s average, 1-minute peak only 3.37 MB/s** — under
one third of the micro baseline (10.88 MB/s).

**Therefore the exhaustion cannot be explained by minute-averaged throughput exceeding baseline.**
It must come from **sub-minute bursts** that minute-level averaging hides. That mechanism is not
fully explained, so **"we need more baseline bandwidth" is not a sound justification for scaling up.**

### 3.5 Query-level offenders (still valid)

**(a) Missing composite index — `t_shop_order_calendar_warehouse_history` (260K rows)**

```sql
SELECT max(dt) FROM t_shop_order_calendar_warehouse_history
WHERE shop_dept_id = ? AND wh_dept_id = ? AND tenant = 'LKUS';
-- Rows_examined: 152,951–160,384   Rows_sent: 1
```
All indexes are **single-column**: `idx_shop`(card 24), `idx_warehouse`(card 4), `idx_dt`(card 113),
`idx_operated_time`. With no composite index the optimizer walks `idx_dt` descending and filters,
examining ~60% of the table to return one value. Called in a per-store loop.

**(b) Unusable index prefix — `t_auto_order_small_log` (1.69M rows, 243.6 MB)**

```sql
SELECT small_class_mid FROM t_auto_order_small_log
WHERE shop_dept_id = ? AND order_date = ? AND tenant = ?;
-- 143 ms average per execution, ~214 rows returned
```
The only secondary index is `uniq_shop_small_order_date` =
`(shop_dept_id, small_class_mid, order_date, tenant)`. The query does not filter `small_class_mid`
(position 2), so only the `shop_dept_id` prefix is usable.

### 3.6 What remains unexplained (stated honestly)

1. **The source of the 13:00 UTC workload is not identified.** `performance_schema` was wiped by
   the 21:55 restart (~20 min of history survives) and `long_query_time = 0.1` hides the sub-100 ms
   statements doing the bulk of the I/O. **This is the largest open item.**
2. **The precise sub-minute burst mechanism that drained the credits** (see 3.4).

**→ Action for Ops:** was anything deployed, or did any batch/job schedule change, around
**13:00 UTC (09:00 EDT) on 2026-08-13**? The workload ran ~9 hours and ended with the restart.

### 3.7 Fleet check — no instance at risk

Swept `EBSByteBalance%` across all RDS instances. `scm-ordering` was the sole outlier (now
recovered to 99%); **every other instance sits at 99–100%**, including `iopocp`, which failed the
same way earlier today. 61 instances share `luckyus-prod-84`, of which **32 are db.t4g.micro**.

---

## 4. Recommendations (re-prioritised in v2)

| Pri | Action | Owner | When |
|-----|--------|-------|------|
| **P1** | **Identify the 13:00 UTC workload** (deploy? batch job? data backfill?). This is the real problem — if the same workload runs again it will repeat | Ops + DBA | 24–48 h |
| **P1** | **Add `EBSByteBalance% < 30%` alarm on all burstable RDS instances.** There was an **8.5-hour** window between the start of the decline and the failover with zero alarm coverage — same for `iopocp` today. An alarm allows intervention before a failover | DBA | 1 week |
| **P2** | Add the two indexes (online DDL, low-traffic window):<br>`ALTER TABLE t_shop_order_calendar_warehouse_history ADD INDEX idx_shop_wh_tenant_dt (shop_dept_id, wh_dept_id, tenant, dt);`<br>`ALTER TABLE t_auto_order_small_log ADD INDEX idx_shop_date_tenant_class (shop_dept_id, order_date, tenant, small_class_mid);` | DBA | 1–2 weeks |
| **P3** | **(Optional)** Scale to `db.t4g.small` for headroom. **Not required** — no steady-state memory bottleneck. Re-evaluate after P1/P2 | DBA + Michael | After evaluation |
| **P3** | Review the other 31 db.t4g.micro instances for any whose *hot set* genuinely exceeds 128 MB | DBA | 2–4 weeks |

---

## 5. Diagnostic lessons

1. **A metric hole is evidence, not missing data.** The 21:39–21:54 gap *is* the unresponsiveness.
2. **A post-restart metric rise is cache warm-up, not resumed load.** This caused the v1 error —
   when judging whether risk persists after a failover, **wait until warm-up completes (~15–30 min)**
   before concluding.
3. **Total schema size ≠ working set.** Judge memory pressure from
   `Innodb_buffer_pool_pages_data` / `pages_free` / steady-state hit ratio, not from
   `information_schema.tables` totals. **Free pages in the pool = memory is not the bottleneck.**
4. **Slow-query count can be a symptom, not a cause.** With `long_query_time = 0.1`, trivial
   statements flood the log once I/O stalls. The 1,111 spike at 21:30 was the throttle, not the trigger.
5. **On burstable instances, check credit metrics before CPU.** Both of today's failovers showed
   entirely normal CPU and memory.

---
*v1 completed 2026-08-13 22:45 UTC; v2 revised 2026-08-13 23:15 UTC.*
