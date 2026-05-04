---
Incident ID:          LCNA-DBA-2026-024
Report Type:          Post-Upgrade Verification + Weekend Burst RCA
Subject:              isalescdp post-upgrade health check — weekend CPU spikes traced to iCDP write burst
RDS Instance:         aws-luckyus-isalescdp-rw
Database:             luckyus_isales_cdp
Instance Class:       db.t4g.large (2 vCPU / 8 GB / burstable Graviton)  [upgraded from db.t4g.medium 2026-04-30]
Engine:               MySQL 8.0.40
Multi-AZ:             Yes
Region:               us-east-1
AWS Account:          257394478466
Investigation Window: 2026-05-02 00:00 UTC → 2026-05-04 18:00 UTC (weekend)
Severity:             L2 — investigation-only, no service impact
Investigator:         曾翔宇 David Zeng (Senior DBA)
Report Date:          2026-05-04
Related Documents:    /app/reports/LCNA-DBA-2026-023-isalescdp-active-threads.md
                      /app/reports/LCNA-DBA-2026-022-phase-a-upgrade-plan.md
---

# LCNA-DBA-2026-024 — isalescdp Post-Upgrade Verification & Weekend Write-Burst RCA

## 1. Executive Summary

Following the 2026-04-30 upgrade from `db.t4g.medium` (4 GB) to `db.t4g.large` (8 GB), weekend monitoring on 2026-05-02 to 2026-05-04 generated **CPU alerts** despite the additional capacity. This investigation confirms:

1. **Upgrade is working as intended.** Memory pressure (the original failure mode driving recurrences #1-#5) is fully resolved — FreeableMemory holds steady at 5.0-5.4 GB across the weekend.
2. **Weekend alerts are short-burst CPU spikes**, not memory exhaustion. They originate from two distinct sources, both pre-existing patterns now exposed by tighter monitoring on the upgraded instance.
3. **No service impact.** No restarts, no failovers, no connection saturation.

The remaining CPU pattern is **application-side**, not a database capacity issue. Recommendation: tune alert thresholds and address the iCDP single-row write pattern at the application layer rather than further upgrading the instance.

---

## 2. Upgrade Verification

| Check | Result |
|---|---|
| Instance class change applied | ✅ `db.t4g.large` (effective 2026-04-30 01:33 UTC) |
| Multi-AZ failover clean | ✅ Failover started 01:27, completed 01:28 UTC |
| Post-upgrade FreeableMemory | ✅ 5.0-5.4 GB stable (was <500 MB pre-upgrade) |
| Post-upgrade DatabaseConnections | ✅ Normal range 50-150, no saturation |
| Active CloudWatch alarms | ✅ None |
| Incident recurrence (memory-driven) | ✅ Zero since upgrade |

---

## 3. Weekend CPU Pattern (2026-05-02 to 2026-05-04)

### 3.1 Two distinct spike patterns observed

| Pattern | Timing | Max CPU | Frequency | Root Cause |
|---|---|---|---|---|
| **A: Daily batch + backup** | 04:00 UTC daily | 79-86% | Recurring every day | Backup window 03:51-03:58 UTC overlaps with 00:00 EST batch jobs |
| **B: Saturday write burst** | 2026-05-02 13:00-13:06 UTC | 85.3% | One-off (not on Sun/Mon) | iCDP real-time event pipeline burst |

### 3.2 CPU timeline (Maximum, 40-min buckets)

| Time (UTC) | 5/2 | 5/3 | 5/4 |
|---|---|---|---|
| 04:00 | **85.8%** | **85.4%** | 79.4% |
| 10:00 | 52.8% | 52.0% | 53.4% |
| 12:40 | **85.3%** | 7.9% | 16.3% |
| Other | 6-15% | 6-15% | 6-15% |

The 5/2 12:40 bucket is the only weekend anomaly that does not repeat.

---

## 4. Root Cause: 2026-05-02 13:00-13:06 UTC Write Burst

### 4.1 Source

- **Account:** `icdprealtimeuge_A_w` (iCDP Real-time User Growth Engine writer)
- **Share of slow log during burst:** 267 / 276 records (97%)
- **Tables touched:** `t_user_state`, `t_user_event`
- **SQL pattern:** Single-row INSERT and DELETE, every statement individually committed

Representative statements (from `/aws/rds/instance/aws-luckyus-isalescdp-rw/slowquery`):
```sql
INSERT INTO t_user_state (user_no, event_type, event_state_value, event_time, msg_id, tenant)
  VALUES ('3616413288449', 6, '3.00', '2026-05-02 13:02:59.984',
          'realtime:ug:event:6:3616413288449:1777726903977', 'LKUS');

DELETE FROM t_user_state
  WHERE user_no = '3598409582593' AND event_type = 8 AND tenant = 'LKUS';

INSERT INTO t_user_event (user_no, event_type, event_sub_type, event_time, tenant, msg_id)
  VALUES ('3588836329473', 10, 11, '2026-05-02 13:02:00.014', 'LKUS',
          'contact:ug:event:1:3588836329473:1777726920014');
```

Each individual query: 0.15-0.22 s. Each query is **simple and indexed** — they are slow only because the instance is saturated.

### 4.2 Burst profile

| Time (UTC) | Slow Queries / min | WriteIOPS (avg) | Notes |
|---|---|---|---|
| 12:51 | 2 | 61 | Baseline |
| 12:54 | 0 | 62 | Baseline |
| 12:57 | 0 | 64 | Baseline |
| **13:00** | 10 | **516** | Burst begins |
| 13:01 | 10 | — | |
| **13:02** | **61** | — | |
| **13:03** | 41 | **912** | |
| **13:04** | **93** | — | **Peak (CPU 85.3%)** |
| 13:05 | 40 | — | |
| 13:06 | 24 | **1093** | **18× normal IOPS** |
| 13:09 | 1 | 466 | Recovery |
| 13:12 | 0 | 242 | |
| 13:18 | 0 | 148 | |
| 13:21 | 0 | 72 | Fully recovered |

Burst duration: ~6 minutes. Estimated total writes during window: ~5,000-10,000 single-row statements (lower bound from slow log alone is 268; actual is much higher since most stayed under `long_query_time`).

### 4.3 Why it saturated a 2 vCPU instance

The bottleneck is **not raw query cost** — each statement is trivially indexed. The bottleneck is per-statement overhead at high concurrency:

- Every INSERT/DELETE issues an individual `commit;` (binlog flush, redo log flush)
- Single-row DELETE-then-INSERT pattern is used where `INSERT ... ON DUPLICATE KEY UPDATE` would do (doubles statement count)
- 2 vCPU instance has limited headroom for this transactional commit overhead at >80 stmt/s

WriteIOPS climbing from 60 → 1,093 confirms the load came from the application, not from internal MySQL maintenance.

### 4.4 Why this pattern fires irregularly

- 5/3 same time slot: CPU 7.9% (no burst)
- 5/4 same time slot: CPU 16.3% (no burst)

The Saturday 13:00 UTC window aligns with **end-of-week marketing event processing** for the iCDP user-growth pipeline. Likely triggers: promotional campaign wrap-up, weekend cohort batch, or upstream Kafka backlog drain. This is not a database scheduling artifact.

---

## 5. Daily 04:00 UTC Pattern (Pre-existing, Expected)

The 04:00 UTC daily 79-86% CPU is the **automated backup window (03:51-03:58 UTC) overlapping with 00:00 EST batch jobs**. This is documented in CLAUDE.md as a known cluster-wide pattern. With db.t4g.large it remains visible but does not cause failures.

DatabaseConnections at 04:00 UTC: ~200 (vs 50-100 baseline) — also confirms application-side batch jobs, not a database internal issue.

---

## 6. Recommendations

### 6.1 Immediate — Alert Tuning (DBA owns, low cost)
- **Change CPU alert** from instantaneous `> 80%` to `> 80% sustained for 5 minutes`. This eliminates noise from the 6-min Saturday burst and the 8-min daily backup spike, while still catching genuine sustained pressure.
- Optionally, **silence 04:00-04:30 UTC** for `aws-luckyus-isalescdp-rw` CPU alerts since the pattern is known and benign post-upgrade.

### 6.2 Application — iCDP Pipeline (Sales/CDP team owns, highest leverage)
- **Replace `DELETE + INSERT` with `INSERT ... ON DUPLICATE KEY UPDATE`** on `t_user_state`. Halves write count and removes redundant binlog entries.
- **Batch commits** in the iCDP writer: group N statements per transaction (e.g., N=50) instead of per-row autocommit. Reduces commit overhead by ~50×.
- Investigate why 13:00 UTC Saturday produced a burst — most likely an upstream Kafka consumer that accumulated backlog and replayed; if so, configure consumer lag monitoring to catch buildup before drain.

### 6.3 Capacity — No Action Recommended
The current `db.t4g.large` is **adequately sized** for steady-state load. Further upgrading to `db.r6g.large` (4 vCPU) would handle bursts but at ~2× cost; the application-side fixes above eliminate the bursts entirely at no marginal cost.

---

## 7. Evidence References

- RDS events: `aws rds describe-events --source-identifier aws-luckyus-isalescdp-rw --duration 10080`
- Slow query log: CloudWatch `/aws/rds/instance/aws-luckyus-isalescdp-rw/slowquery`, window 2026-05-02 12:20-13:30 UTC
- CloudWatch metrics: `AWS/RDS` namespace, dimension `DBInstanceIdentifier=aws-luckyus-isalescdp-rw`
  - `CPUUtilization` (Maximum)
  - `FreeableMemory` (Minimum)
  - `WriteIOPS` (Average)
  - `DatabaseConnections` (Maximum)

---

## 8. Status

| Item | Status |
|---|---|
| Upgrade outcome | ✅ Successful — memory issue closed |
| Weekend alerts | ✅ Investigated, no service impact |
| Daily 04:00 UTC pattern | ⚠️ Known, benign; recommend alert tuning |
| 5/2 13:00 UTC burst | ⚠️ Application-side; handed to iCDP team |
| Further DBA action | None pending |

Closing LCNA-DBA-2026-024.
