# Phase 0 — Anchor

## Instance identifiers
- **Topology**: standalone RDS MySQL (NOT Aurora, NOT a cluster).
  `aws rds describe-db-clusters` returns `DBClusterNotFoundFault`. The string `aws-luckyus-isalescdp-rw` is the DB **instance** identifier itself.
- **DBInstanceIdentifier**: `aws-luckyus-isalescdp-rw`
- **Class**: `db.t4g.medium` (2 vCPU, 4 GiB RAM, ARM Graviton2)
- **Engine**: MySQL 8.0.40, ARM (`aarch64`)
- **AZ**: `us-east-1b`
- **Storage**: 40 GiB gp3, IOPS 3000
- **Parameter group**: `luckyus-prod-80-new` (in-sync; no pending changes)
- **Performance Insights**: **DISABLED** ⚠ — Phase 1B not feasible; substitute via slow-log + perf_schema below.
- **Logs exported to CloudWatch**: only `slowquery` (no general/error/audit).
- **Time zone**: server `@@global.time_zone = UTC` — all timestamps in this report are UTC.

## D1 — the alert under investigation
- **Fire start**: 2026-04-25 13:01 UTC (CPU first inflection 13:01:00, connections jump 13:01)
- **Peak**: 2026-04-25 13:05-13:06 UTC — 55 active threads, ~250 connections, 86% CPU, 1115 WriteIOPS
- **Auto-recover**: 2026-04-25 13:08:05 UTC
- **Local equivalents**: 09:01-09:08 EDT / 06:01-06:08 PDT — clear NA business hours
- **Cross-clock**: 21:01-21:08 Beijing time (CN evening peak — relevant only to Hypothesis 3)
- **Alert system**: not a CloudWatch alarm (none exist with `isalescdp` in name); managed via Prometheus/Grafana / migrated legacy strategy id=67.

## Baseline windows for differential (B1, B2, B3)
Based on 14-day CPU MAX history (CloudWatch, 1h aggregation):

| Code | Window UTC | Peak CPU | Notes |
|------|------------|----------|-------|
| **B1** | 2026-04-22 06:26 | 84.6% | Slow-log peak 164/min @ 06:36 — clearest recent nighttime fire (separate from 03-04h backup) |
| **B2** | 2026-04-15 05:40 | 85.3% | Nightly fire candidate (separate from backup) |
| **B3** | 2026-04-21 04:00 | 82.2% | Right after backup window; possibly post-backup compounding |
| **D1** | 2026-04-25 13:05 | 86.0% | THIS investigation |

The 14d CPU series also shows **two recent daytime precursor spikes** that are not in the original B1-B3 baseline but pin the trend:
- 2026-04-19 14:23 UTC — CPU 73%
- 2026-04-24 11:18 UTC — CPU 81%

D1 is therefore the **3rd daytime saturation event in 7 days**, not an isolated outlier.

## Strategy migration check (id=67 → new)
Cannot be verified from inside MySQL (alert rule lives in Grafana/Prometheus, not RDS).
**Open question for Phase 4**: is the new strategy threshold the same 24-active-threads / 2-min as legacy id=67? Tracked as Hypothesis 6 (unverifiable here).

## RDS / CloudTrail events, last 7 days
**Empty except for daily routine backups (03:51-03:57 UTC).**
No parameter changes, no reboots, no failover, no instance-class change, no manual modification. So nothing on the RDS side has changed in the past week — the spike is workload-driven.
