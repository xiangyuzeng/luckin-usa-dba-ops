# Phase A Execution Plan — MySQL 8.0.40/41 → 8.0.45 Minor Version Upgrade

**Date**: 2026-04-11
**Operator**: David Zeng (DBA), Luckin Coffee North America
**Account**: 257394478466 | Region: us-east-1
**Target Version**: **8.0.45** (dynamically confirmed as latest available 8.0.x)
**Deadline**: May 31, 2026 (AWS forced auto-upgrade of 8.0.40/8.0.41)

---

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| Total MySQL RDS instances | 63 |
| Category A — MUST UPGRADE (8.0.40/8.0.41) | **59** |
| Category B — Already Safe (8.0.42/8.0.44) | 2 |
| Category C — On 8.4 (skip) | 2 |
| Pre-flight blockers | **0** |
| Upgrade path validated | **YES** (8.0.40→8.0.45, 8.0.41→8.0.45) |
| Estimated total time | ~11.2 hours across 3-4 evenings |
| Upgrade window | 06:00-10:00 UTC (01:00-05:00 EST) |

### Version Distribution (Current)

| Version | Count | Status |
|---------|-------|--------|
| 8.0.40 | 58 | **MUST UPGRADE** — affected by 5/31 EOL |
| 8.0.41 | 1 (ldas01) | **MUST UPGRADE** — affected by 5/31 EOL |
| 8.0.42 | 1 (dbatest) | Safe from 5/31 |
| 8.0.44 | 1 (iluckyams) | Safe from 5/31 |
| 8.4.7 | 2 (dba84test, datalink-84test) | Already on 8.4 |

### Instance Class Distribution

| Class | Count | RAM | Upgrade Time Est. |
|-------|-------|-----|-------------------|
| db.t4g.micro | 42 | 1 GB | ~6 min |
| db.t3.small | 1 | 2 GB | ~8 min |
| db.t4g.medium | 17 | 4 GB | ~10 min |
| db.t4g.large | 2 | 8 GB | ~12 min |
| db.t4g.xlarge | 1 | 16 GB | ~15 min |

---

## 2. Health Assessment — OOM Risk Evaluation

**Period**: Past 24 hours (2026-04-10 20:41 UTC to 2026-04-11 20:41 UTC)
**Method**: Single batched CloudWatch `get-metric-data` call (118 queries)

| Risk Level | Count | Criteria | Action |
|------------|-------|----------|--------|
| **RED** | **39** | FreeableMemory min < 150 MB | Proceed with caution — systemic for 1GB tier |
| **YELLOW** | **1** | FreeableMemory min 150-300 MB | Monitor closely |
| **GREEN** | **19** | FreeableMemory min > 300 MB | Safe |

### Risk Assessment

**39 RED instances are almost entirely db.t4g.micro (1GB RAM)**. This is a systemic fleet-wide condition, not an upgrade-specific risk. Key observations:

- All 42 micro instances have FreeableMemory between 46-104 MB with SwapUsage 380-1224 MB
- This is the normal operating state for these instances (chronic memory pressure)
- **iluckyams-rw (now 8.0.44) already successfully survived a minor version auto-upgrade on March 31** with similar memory conditions (83-148 MB free, 437 MB swap) — proving minor upgrades work even under memory pressure
- Minor version upgrades are in-place restarts with Multi-AZ failover, not data migrations
- The primary risk is post-restart buffer pool reduction (as seen in Jan 31 iworkflowmidlayer and Mar 12 isalescdp incidents)

### Critical Watch Instances

| Instance | Class | RAM | FreeMemMin | SwapAvg | Notes |
|----------|-------|-----|-----------|---------|-------|
| iluckyhealth | db.t3.small | 2GB | **46 MB** | 870 MB | WORST in fleet. 2GB RAM but behaves like micro |
| opqualitycontrol | db.t4g.micro | 1GB | 63 MB | 746 MB | Second worst |
| iriskcontrolservice | db.t4g.micro | 1GB | 90 MB | **1224 MB** | Highest swap in fleet |
| upush | db.t4g.medium | 4GB | 251 MB | 328 MB | YELLOW — only medium with memory concern |

### Healthy Instances (GREEN)

All medium/large/xlarge instances are GREEN except upush (YELLOW):
- framework01: 1584 MB free
- framework02: 1001 MB free
- salescrm: 1790 MB free
- salespayment: 1683 MB free
- salesmarketing: 1460 MB free (xlarge, 16GB)
- ldas: 1026 MB free (large, 8GB)
- ldas01: 599 MB free (large, 8GB)
- isalescdp: 1018 MB free (confirmed upsized to medium post-OOM)

---

## 3. Recent Incidents (Past 7 Days)

| Instance | Date | Event |
|----------|------|-------|
| luckyus-datalink-84test | 2026-04-09 13:33 UTC | DB instance restarted |
| aws-luckyus-dba84test-rw | 2026-04-09 14:21 UTC | DB instance restarted |
| aws-luckyus-datalink-84test-rw | 2026-04-09 14:47 UTC | DB instance restarted |

**All 3 events are on 8.4 test instances only** — no incidents on any Category A production instance in the past 7 days. Fleet is stable.

---

## 4. Parameter Groups (Pre-Upgrade Reference)

### luckyus-prod (2 instances: devops-rw, ldas-rw)
22 custom parameters. Key differences vs luckyus-prod-80-new:
- **Missing**: `log_bin_trust_function_creators`, `lower_case_table_names`
- Same: `max_connections=4000`, `long_query_time=0.1`, `transaction_isolation=READ-COMMITTED`

### luckyus-prod-80-new (56 instances)
25 custom parameters including:
- `log_bin_trust_function_creators=1`
- `lower_case_table_names=1`
- `max_connections=4000`
- `performance_schema=1`
- `optimizer_switch` with `prefer_ordering_index=off`

### luckyus-prod-80-new-groupconcatmaxlen (1 instance: salesorder-rw)
26 custom parameters — identical to luckyus-prod-80-new plus:
- **`group_concat_max_len=1048576`** (must verify after upgrade)

---

## 5. Batch Plan

### Batch 1 — PILOT (DBA Internal Analytics) — 2 instances | ~40 min

| # | Instance | Version | Class | RAM | Storage | ParamGroup | FreeMem | Risk |
|---|----------|---------|-------|-----|---------|------------|---------|------|
| 1 | ldas | 8.0.40 | db.t4g.large | 8GB | 30GB | luckyus-prod | 1026 MB | GREEN |
| 2 | ldas01 | 8.0.41 | db.t4g.large | 8GB | 128GB | luckyus-prod-80-new | 599 MB | GREEN |

**Purpose**: Validate upgrade procedure and timing on DBA-internal instances with zero business impact.

### Batch 2 — LOW-RISK INTERNAL TOOLS — 37 instances | ~5.7 hr

All 37 are db.t4g.micro (1GB RAM), all RED memory status. Internal tools, SCM, and low-traffic services.

<details>
<summary>Full instance list (click to expand)</summary>

| # | Instance | FreeMem | SwapAvg |
|---|----------|---------|---------|
| 1 | fichargecontrol | 87 MB | 565 MB |
| 2 | fitax | 93 MB | 394 MB |
| 3 | iadmin | 96 MB | 510 MB |
| 4 | ibillingcentersrv | 90 MB | 680 MB |
| 5 | ibizconfigcenter | 99 MB | 434 MB |
| 6 | iehr | 90 MB | 557 MB |
| 7 | ifiaccounting | 93 MB | 865 MB |
| 8 | igers | 104 MB | 398 MB |
| 9 | ijumpserver-jumpserver | 90 MB | 624 MB |
| 10 | ilsopdevopsdata | 98 MB | 380 MB |
| 11 | iluckyauthapi | 98 MB | 403 MB |
| 12 | iluckydorisops | 95 MB | 407 MB |
| 13 | iluckymedia | 98 MB | 415 MB |
| 14 | iopenadmin | 103 MB | 420 MB |
| 15 | iopenlinker | 90 MB | 502 MB |
| 16 | iopenservice | 96 MB | 406 MB |
| 17 | iopocp | 91 MB | 619 MB |
| 18 | iopshopexpand | 99 MB | 428 MB |
| 19 | ipermission | 90 MB | 591 MB |
| 20 | ireplenishment | 87 MB | 648 MB |
| 21 | iriskcontrolservice | 90 MB | 1224 MB |
| 22 | iunifiedreconcile | 101 MB | 426 MB |
| 23 | mfranchise | 100 MB | 461 MB |
| 24 | opempefficiency | 89 MB | 546 MB |
| 25 | oplog | 93 MB | 409 MB |
| 26 | opproduction | 88 MB | 603 MB |
| 27 | opqualitycontrol | 63 MB | 746 MB |
| 28 | opshopsale | 81 MB | 649 MB |
| 29 | pubdm | 87 MB | 505 MB |
| 30 | scm-asset | 94 MB | 594 MB |
| 31 | scm-openapi | 93 MB | 579 MB |
| 32 | scm-ordering | 83 MB | 765 MB |
| 33 | scm-plan | 93 MB | 470 MB |
| 34 | scm-purchase | 91 MB | 792 MB |
| 35 | scm-wds | 91 MB | 716 MB |
| 36 | scm-wmssimulate | 90 MB | 535 MB |
| 37 | scmsrm | 90 MB | 730 MB |

</details>

**Note**: This batch exceeds a single 4-hour window. Recommend splitting across 2 evenings (~20 + ~17).

### Batch 3 — OPS/FINANCE + MEDIUM INSTANCES — 9 instances | ~2.0 hr

| # | Instance | Version | Class | RAM | Storage | ParamGroup | FreeMem | Risk |
|---|----------|---------|-------|-----|---------|------------|---------|------|
| 1 | isalesmembermarketing | 8.0.40 | db.t4g.micro | 1GB | 20GB | luckyus-prod-80-new | 94 MB | RED |
| 2 | iluckyhealth | 8.0.40 | db.t3.small | 2GB | 50GB | luckyus-prod-80-new | **46 MB** | RED |
| 3 | devops | 8.0.40 | db.t4g.medium | 4GB | 20GB | luckyus-prod | 1600 MB | GREEN |
| 4 | iotplatform | 8.0.40 | db.t4g.medium | 4GB | 20GB | luckyus-prod-80-new | 1496 MB | GREEN |
| 5 | iworkflowmidlayer | 8.0.40 | db.t4g.medium | 4GB | 20GB | luckyus-prod-80-new | 458 MB | GREEN |
| 6 | opshop | 8.0.40 | db.t4g.medium | 4GB | 20GB | luckyus-prod-80-new | 2224 MB | GREEN |
| 7 | scm-shopstock | 8.0.40 | db.t4g.medium | 4GB | 30GB | luckyus-prod-80-new | 461 MB | GREEN |
| 8 | scmcommodity | 8.0.40 | db.t4g.medium | 4GB | 20GB | luckyus-prod-80-new | 2054 MB | GREEN |
| 9 | upush | 8.0.40 | db.t4g.medium | 4GB | 40GB | luckyus-prod-80-new | 251 MB | YELLOW |

**Watch**: iluckyhealth (46 MB free, worst in fleet), upush (YELLOW), iworkflowmidlayer (had P0 OOM Jan 31, now stable on medium)

### Batch 5 — CORE FRAMEWORK (ONE AT A TIME) — 2 instances | ~36 min

| # | Instance | Version | Class | RAM | Storage | ParamGroup | FreeMem | Risk |
|---|----------|---------|-------|-----|---------|------------|---------|------|
| 1 | framework01 | 8.0.40 | db.t4g.medium | 4GB | 20GB | luckyus-prod-80-new | 1584 MB | GREEN |
| 2 | framework02 | 8.0.40 | db.t4g.medium | 4GB | 40GB | luckyus-prod-80-new | 1001 MB | GREEN |

**Protocol**: Upgrade ONE AT A TIME. After each, verify via MCP:
```sql
SELECT @@version, @@sql_mode, @@character_set_server;
SHOW GLOBAL STATUS LIKE 'Threads_connected';
SHOW GLOBAL STATUS LIKE 'Aborted_%';
```

### Batch 6 — SALES + MARKETING CORE (Most Critical, LAST) — 9 instances | ~2.2 hr

| # | Instance | Version | Class | RAM | Storage | ParamGroup | FreeMem | Risk |
|---|----------|---------|-------|-----|---------|------------|---------|------|
| 1 | cdpactivity | 8.0.40 | db.t4g.medium | 4GB | 40GB | luckyus-prod-80-new | 457 MB | GREEN |
| 2 | icyberdata | 8.0.40 | db.t4g.medium | 4GB | 635GB | luckyus-prod-80-new | 567 MB | GREEN |
| 3 | isalescdp | 8.0.40 | db.t4g.medium | 4GB | 40GB | luckyus-prod-80-new | 1018 MB | GREEN |
| 4 | isalesdatamarketing | 8.0.40 | db.t4g.medium | 4GB | 40GB | luckyus-prod-80-new | 619 MB | GREEN |
| 5 | isalesprivatedomain | 8.0.40 | db.t4g.medium | 4GB | 20GB | luckyus-prod-80-new | 639 MB | GREEN |
| 6 | salescrm | 8.0.40 | db.t4g.medium | 4GB | 20GB | luckyus-prod-80-new | 1790 MB | GREEN |
| 7 | salespayment | 8.0.40 | db.t4g.medium | 4GB | 20GB | luckyus-prod-80-new | 1683 MB | GREEN |
| 8 | **salesorder** | 8.0.40 | db.t4g.medium | 4GB | 20GB | **luckyus-prod-80-new-groupconcatmaxlen** | 375 MB | GREEN |
| 9 | **salesmarketing** | 8.0.40 | db.t4g.xlarge | **16GB** | **100GB** | luckyus-prod-80-new | 1460 MB | GREEN |

**Special checks**:
- **salesorder**: Post-upgrade verify `SHOW VARIABLES LIKE 'group_concat_max_len'` = 1048576
- **isalescdp**: Extended CloudWatch FreeableMemory check (post-OOM incident Mar 12)
- **salesmarketing**: Full verification — MCP + CloudWatch CPU/Memory + param group (largest instance)
- **icyberdata**: 635GB storage — in-place upgrade, storage size minimal impact

---

## 6. Upgrade Path Confirmation

| Source Version | Target Version | Valid Path | Major Version Upgrade |
|---------------|---------------|------------|----------------------|
| 8.0.40 | 8.0.45 | **YES** | No (minor) |
| 8.0.41 | 8.0.45 | **YES** | No (minor) |

Validated via `aws rds describe-db-engine-versions --engine-version <ver> --query ValidUpgradeTarget`.

---

## 7. Pre-Flight Blockers

**NONE**. All 59 Category A instances pass:
- Status: `available` (all 59)
- Pending modifications: `NONE` (all 59)
- Parameter apply status: `in-sync` (all 59)

Note: dbatest-rw (Category B, 8.0.42) has `pending-reboot` param status — not a blocker for Phase A.

---

## 8. Recommended Schedule

| Evening | UTC Window | Batches | Instances | Est. Duration |
|---------|-----------|---------|-----------|---------------|
| **Evening 1** | 06:00-10:00 | Batch 1 + Batch 2 (first 20) | 22 | ~3.5 hr |
| **Evening 2** | 06:00-10:00 | Batch 2 (remaining 17) + Batch 3 | 26 | ~3.8 hr |
| **Evening 3** | 06:00-10:00 | Batch 5 + Batch 6 | 11 | ~2.8 hr |

**AVOID**: 04:30-05:30 UTC (daily batch processing at 05:00 UTC / 00:00 EST)

---

## 9. Execution Protocol

### Per-Instance Upgrade Sequence
1. **PRE-CHECK**: Confirm version, status=available, no pending mods, record param group
2. **EXECUTE**: `aws rds modify-db-instance --engine-version 8.0.45 --apply-immediately`
3. **WAIT**: `aws rds wait db-instance-available` (30 min timeout)
4. **VERIFY**: Confirm version=8.0.45, status=available, param group unchanged, param in-sync

### Safety Controls
- **Operator confirmation required before each batch**
- **FreeableMemory < 100 MB at upgrade time → WARN and ask confirmation**
- **Single failure → log, skip, continue within batch**
- **>2 failures in one batch → STOP EVERYTHING**
- **All actions logged with timestamps to execution.log**

### Post-Upgrade Checks (Special)
- **Batch 5 (framework)**: MCP health query after each instance
- **salesorder**: Verify `group_concat_max_len=1048576`
- **isalescdp**: Extended memory monitoring
- **salesmarketing**: Full verification suite
- **Any instance**: If FreeableMemory drops below 100 MB post-upgrade, check `innodb_buffer_pool_size` via MCP for buffer pool reduction (134217728 = 128 MB → CRITICAL)

---

## 10. Category B — Optional Consistency Upgrade

After all Category A upgrades, optionally upgrade for fleet uniformity:

| Instance | Current Version | Recommendation |
|----------|----------------|----------------|
| dbatest-rw | 8.0.42 | Upgrade to 8.0.45 (has pending-reboot — resolve first) |
| iluckyams-rw | 8.0.44 | Upgrade to 8.0.45 (caution: 46-148 MB free memory on micro) |

---

## 11. Phase B Prerequisites (Post-Phase A)

After Phase A eliminates the 5/31 threat:

1. **Create param groups**: `luckyus-prod-84-new` (mysql8.4 family) with 25 params + `mysql_native_password=ON`
2. **Create param group**: `luckyus-prod-84-new-groupconcatmaxlen` for salesorder
3. **Update Prometheus exporter**: `SHOW SLAVE STATUS` completely removed in 8.4 → use `SHOW REPLICA STATUS`
4. **Grant permissions**: `GRANT REPLICATION CLIENT TO diagtools@'%'` on all instances
5. **Evaluate salesorder memory**: 375 MB avg free — consider upsizing before Phase B
6. **Switch test instances**: dba84test/datalink-84test from `default.mysql8.4` to `luckyus-prod-84-new`
7. **Coordinate**: Phase B schedule with Ops team and CTO Michael
8. **Extended Support cost if Phase B delayed past 7/31**: ~$9,957/month ($0.11 x 124 vCPU x 730h)

---

## 12. Output Files

All in `/home/claude/phase-a/`:

| File | Description |
|------|-------------|
| `fleet-inventory.json` | Raw AWS API output (63 instances) |
| `available-80-versions.txt` | All available 8.0.x versions (8.0.40-8.0.45) |
| `upgrade-path-validation.txt` | API confirmation: 8.0.40→8.0.45, 8.0.41→8.0.45 |
| `classification.txt` | Category A/B/C/D breakdown with full details |
| `pre-flight-blockers.txt` | No blockers found |
| `health-assessment.txt` | FreeableMemory/SwapUsage per instance with risk levels |
| `health-raw.json` | Raw CloudWatch metric data (241 KB) |
| `recent-incidents.txt` | Only 8.4 test instance restarts (no production incidents) |
| `param-groups-pre-upgrade.txt` | All 3 param groups' custom settings |
| `batch-plan.txt` | Complete batch assignments with health status |
| `timeline-estimate.txt` | Per-batch and total time estimates |
| `batch-assignments.json` | Machine-readable batch assignments for execution scripts |

---

*Phase A execution plan ready. Review batches, timeline, and health assessment above. Reply YES to begin with Batch 1 (pilot), or specify changes.*
