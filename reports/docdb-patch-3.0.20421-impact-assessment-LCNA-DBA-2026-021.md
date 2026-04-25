# DocumentDB Engine Patch 3.0.20421 — Impact Assessment

**Document ID:** LCNA-DBA-2026-021
**Date:** 2026-04-25
**Author:** David Zeng (Senior DBA, Luckin Coffee NA)
**Status:** Draft
**Classification:** Internal — Infrastructure Operations

---

## Executive Summary

AWS Health event `AWS_DOCDB_DB_PATCH_UPGRADE_MAINTENANCE_SCHEDULED` covers **4 DocumentDB 5.0.0 clusters** in account 257394478466 / us-east-1, all targeted to engine patch **3.0.20421** ("Bug Fixes"). Topology is favorable: every cluster is **3-instance Multi-AZ** with `DeletionProtection=true`, so write interruption during AWS-orchestrated failover is expected to be **~30 seconds** rather than the multi-minute downtime that would apply to a single-instance cluster.

**Risk distribution:** **1 LOW** (`docdb-devops` — internal DBA tooling, non-prod), **3 MEDIUM** (`docdb-gia`, `docdb-iot`, `docdb-luckyus-iluckychaindep` — production-class, no failover demonstration in last 7 days; `docdb-luckyus-iluckychaindep` has an AZ-distribution gap with two instances in `us-east-1b` and a recent CPU saturation event hitting 100%; `docdb-gia` has asymmetric instance classes — t4g.medium writer with r6g.large readers).

**Recommended action: self-apply on a controlled schedule between 2026-04-26 and 2026-04-27 (this weekend).** The hard deadline is **`docdb-iot` at 2026-04-28 05:43 UTC** (Tue 01:43 ET) — its scheduled CurrentApplyDate is the soonest of the four. If we do nothing, that cluster will be auto-patched in its preferred window (Tue 05:43 UTC) within ~3 days. Self-applying gives us snapshot-before-patch control, app-owner notification lead time, and the ability to pick a low-load window from the 14-day CloudWatch baseline.

**Per-cluster recommended self-apply slots** (Sun 2026-04-26 → Mon 2026-04-27, all UTC / ET):
- `docdb-iot` — **Sun 2026-04-26 05:00-09:00 UTC / Sun 01:00-05:00 ET** (overnight ET, lowest IoT write IOPS); deadline Tue 01:43 ET
- `docdb-devops` — **Sun 2026-04-26 19:00-23:00 UTC / Sun 15:00-19:00 ET**
- `docdb-luckyus-iluckychaindep` — **Sun 2026-04-27 09:00-13:00 UTC / Sun 05:00-09:00 ET** (post 05 UTC daily batch peak)
- `docdb-gia` — **Sun 2026-04-27 22:00 → Mon 2026-04-28 02:00 UTC / Sun 18:00-22:00 ET**

> **Discrepancy flagged:** AWS Health event references "DB_PATCH_UPGRADE", but `describe-pending-maintenance-actions` shows `Action=system-update` (description "Bug Fixes"), not `Action=db-upgrade`. This is consistent with how AWS classifies DocumentDB **engine patches** vs. **major-version upgrades** (PostgreSQL Dify cluster correctly shows `Action=db-upgrade` for its 16.8.R2 bump in the same API call). Treating this as the engine patch referenced by the Health event. Verified in §3.

---

## 1. Cluster Inventory

| Cluster ID | Current Engine | Target | Instances | Multi-AZ | Instance Class(es) | Cluster Maint Window (UTC) | CurrentApplyDate (UTC) | Risk Tier |
|---|---|---|---|---|---|---|---|---|
| `docdb-devops` | 5.0.0 | 3.0.20421 | 3 | ✅ (1a/1b/1c) | db.t3.medium × 3 | Fri 03:05-03:35 | 2026-05-01 03:05 | **LOW** |
| `docdb-gia` | 5.0.0 | 3.0.20421 | 3 | ✅ (1a/1b/1c) | t4g.medium (W) + r6g.large × 2 (R) | Sun 08:06-08:36 | 2026-05-03 08:06 | **MEDIUM** |
| `docdb-iot` | 5.0.0 | 3.0.20421 | 3 | ✅ (1a/1b/1c) | db.t3.medium × 3 | Tue 05:43-06:13 | **2026-04-28 05:43** | **MEDIUM** |
| `docdb-luckyus-iluckychaindep` | 5.0.0 | 3.0.20421 | 3 | ✅ (1b/1b/1c — gap) | db.t3.medium × 3 | Sun 03:52-04:22 | 2026-05-03 03:52 | **MEDIUM** |

**Common attributes (all 4):**
- `Engine=docdb`, `EngineVersion=5.0.0`, `Port=27017`
- `DBClusterParameterGroup=luckyus-prod`
- `DBSubnetGroup=docdb-group` (VPC `vpc-0dce7ca7770422d33`, subnets in 1a/1b/1c)
- `VpcSecurityGroups=[sg-0deaa7cf7437e39c7]` (single shared SG)
- `BackupRetentionPeriod=7`, `PreferredBackupWindow=00:00-00:30 UTC`
- `StorageEncrypted=true` (KMS key `5c5c743d-b79f-4d3a-867f-5e849ee4b52b`)
- `DeletionProtection=true`
- `AutoMinorVersionUpgrade=false` on every instance — patches require explicit apply

---

## 2. Per-Cluster Deep Dive

### 2.1 `docdb-devops`

#### 2.1.1 Topology
| Member | Role | AZ | Class | Instance Maint Window |
|---|---|---|---|---|
| `docdb-devops` | **WRITER** | us-east-1a | db.t3.medium | Sat 03:53-04:23 UTC |
| `docdb-devops2` | reader | us-east-1b | db.t3.medium | Fri 05:51-06:21 UTC |
| `docdb-devops3` | reader | us-east-1c | db.t3.medium | Fri 08:58-09:28 UTC |

All 3 promotion tier 1, distinct AZs (1a/1b/1c), homogeneous instance class. Cluster created 2025-02-12.

#### 2.1.2 Pending Maintenance Status
✅ Confirmed at cluster ARN `arn:aws:rds:us-east-1:257394478466:cluster:docdb-devops`
- Action: `system-update` ("Bug Fixes")
- AutoAppliedAfterDate: `2026-04-28 01:58:59 UTC`
- CurrentApplyDate: `2026-05-01 03:05:00 UTC` (Fri 23:05 ET)
- Plus 3 separate `system-update` ("New OS update") entries on each writer/reader instance — these are separate from the engine patch and stack on top of the same maintenance window.

#### 2.1.3 Workload Pattern (last 14 days, hourly p95)
- DatabaseConnections: avg **109**, max **231**, very flat (~120-130 p95 across all hours — likely steady polling from internal tools)
- CPUUtilization: avg **23%**, max **82%** — instance occasionally CPU-bound at peaks
- WriteIOPS: avg **19/s**, slight bump 07-10 UTC (Tue/Wed batch?)
- ReadIOPS: ~0/s on writer (reads served by reader endpoint, not measured here)
- **Lowest-load 4h window: 19:00-23:00 UTC = 15:00-19:00 ET** (data-driven)

#### 2.1.4 Recent Events (last 7 days)
**No events recorded** at cluster or writer instance level. No failovers, restarts, or parameter changes.

#### 2.1.5 Risk Assessment
**Tier: LOW.** Internal DBA tooling cluster (per naming heuristic — "devops"). Not customer-facing. 3 instances spread across 3 distinct AZs satisfies the LOW criterion. No recent failover demonstration, but blast radius is internal-only and a brief write blip does not affect customers. Connection count of ~109-230 indicates steady internal polling (likely Grafana, Prometheus, internal admin tools). Failover during patch should be transparent to those clients with retry logic.

#### 2.1.6 Recommended Self-Apply Slot
**Sunday 2026-04-26 19:00-23:00 UTC** (Sunday 15:00-19:00 EDT). Selected for: (a) data-driven lowest-load window, (b) weekend lead time, (c) DBA team awake/available, (d) well before 2026-05-01 CurrentApplyDate.

---

### 2.2 `docdb-gia`

#### 2.2.1 Topology
| Member | Role | AZ | Class | Instance Maint Window |
|---|---|---|---|---|
| `docdb-gia2` | **WRITER** | us-east-1c | **db.t4g.medium** | Fri 06:51-07:21 UTC |
| `docdb-gia` | reader | us-east-1b | **db.r6g.large** | Mon 03:23-03:53 UTC |
| `docdb-gia3` | reader | us-east-1a | **db.r6g.large** | Thu 04:01-04:31 UTC |

All distinct AZs (1a/1b/1c). **Class asymmetry**: writer is t4g.medium (2 vCPU, 4 GiB, burst-capable), readers are r6g.large (2 vCPU, 16 GiB, sustained). Promotion tiers all 1. Cluster created 2025-03-07.

#### 2.2.2 Pending Maintenance Status
✅ Confirmed at cluster ARN `arn:aws:rds:us-east-1:257394478466:cluster:docdb-gia`
- Action: `system-update` ("Bug Fixes")
- AutoAppliedAfterDate: `2026-04-27 06:57:43 UTC` ← **earliest auto-apply of the four**
- CurrentApplyDate: `2026-05-03 08:06:00 UTC` (Sun 04:06 ET)

#### 2.2.3 Workload Pattern (last 14 days, hourly p95)
- DatabaseConnections: avg **12**, max **16** — flat across all hours
- CPUUtilization: avg **14%**, max **65%** — moderate transient spikes
- WriteIOPS: avg **2/s**, slight peak hours **15-16 UTC** (~2.35/s)
- Cluster is **lightly loaded**, but the 65% CPU max indicates occasional bursty workloads
- **Lowest-load 4h window: 22:00-02:00 UTC = 18:00-22:00 ET** (data-driven)

#### 2.2.4 Recent Events (last 7 days)
**No events recorded.** No failovers, restarts, or parameter changes.

#### 2.2.5 Risk Assessment
**Tier: MEDIUM.** Reasoning:
- Production GIA app (per naming heuristic — likely the "GIA" application stack)
- Multi-AZ across 3 distinct AZs — strong topology
- **Class asymmetry** is the elevation factor: when AWS fails over the t4g.medium writer to a reader, the cluster will land on a reader (r6g.large). On failback, performance can degrade if traffic outgrows t4g burst budget. AWS picks the highest-tier eligible promoted reader; both are tier 1 r6g.large, so the cluster would actually become MORE capable post-failover until the writer is patched and rejoins.
- No demonstrated successful failover in 7d window — first patch failover will be the validation.

#### 2.2.6 Recommended Self-Apply Slot
**Sunday 2026-04-27 22:00 UTC → Monday 2026-04-28 02:00 UTC** (Sunday 18:00-22:00 EDT). Selected for: (a) data-driven lowest-load window, (b) Sunday US evening = lowest user activity, (c) buffer of ~5 days before CurrentApplyDate. **Coordinate with GIA app owner** — see §3.

---

### 2.3 `docdb-iot`

#### 2.3.1 Topology
| Member | Role | AZ | Class | Instance Maint Window |
|---|---|---|---|---|
| `docdb-iot2` | **WRITER** | us-east-1c | db.t3.medium | Sun 05:59-06:29 UTC |
| `docdb-iot` | reader | us-east-1b | db.t3.medium | Thu 09:42-10:12 UTC |
| `docdb-iot3` | reader | us-east-1a | db.t3.medium | Mon 06:08-06:38 UTC |

All 3 distinct AZs, homogeneous t3.medium. Cluster created 2025-03-10.

#### 2.3.2 Pending Maintenance Status
✅ Confirmed at cluster ARN `arn:aws:rds:us-east-1:257394478466:cluster:docdb-iot`
- Action: `system-update` ("Bug Fixes")
- AutoAppliedAfterDate: `2026-04-28 01:58:59 UTC`
- CurrentApplyDate: **`2026-04-28 05:43:00 UTC` (Tue 01:43 ET)** ← **earliest scheduled apply of the four**

#### 2.3.3 Workload Pattern (last 14 days, hourly p95)
- DatabaseConnections: constant **8** across all hours (likely connection pool from IoT ingest service)
- CPUUtilization: avg **20%**, max **70.8%** — short transient spikes
- WriteIOPS: avg **9/s**, peak hours **14, 15, 18, 19 UTC** (~13/s) — likely device check-in cycles
- ReadIOPS: 0
- **Lowest-load 4h window: 05:00-09:00 UTC = 01:00-05:00 ET** (data-driven, overnight ET)

#### 2.3.4 Recent Events (last 7 days)
**No events recorded.**

#### 2.3.5 Risk Assessment
**Tier: MEDIUM.** Reasoning:
- IoT telemetry workload — likely the **store telemetry / IoT device pings** for the 11 NA stores
- Strong topology (3 instances × 3 distinct AZs, homogeneous class)
- IoT clients often retry transparently on transient network errors — failover should be invisible if SDK retries are configured
- No demonstrated failover in 7d → MEDIUM, not LOW
- **Time pressure is the elevation factor**: only **~3 days** until auto-apply at 2026-04-28 05:43 UTC

#### 2.3.6 Recommended Self-Apply Slot
**Sunday 2026-04-26 05:00-09:00 UTC** (Sunday 01:00-05:00 EDT). **HIGHEST URGENCY** — must be done before Tue 2026-04-28 05:43 UTC. Selected for: (a) data-driven lowest-load (overnight ET = lowest device activity), (b) ~48h buffer to forced apply, (c) Sun overnight ET also coincides with the cluster's natural Sun maintenance window for instance `docdb-iot2` (writer maint Sun 05:59-06:29). Note: forced apply happens during PreferredMaintenanceWindow (`tue:05:43`) regardless of AutoAppliedAfterDate, but we want full control of timing.

---

### 2.4 `docdb-luckyus-iluckychaindep`

#### 2.4.1 Topology
| Member | Role | AZ | Class | Instance Maint Window |
|---|---|---|---|---|
| `docdb-luckyus-iluckychaindep3` | **WRITER** | us-east-1c | db.t3.medium | Thu 07:44-08:14 UTC |
| `docdb-luckyus-iluckychaindep` | reader | **us-east-1b** | db.t3.medium | Sun 04:52-05:22 UTC |
| `docdb-luckyus-iluckychaindep2` | reader | **us-east-1b** | db.t3.medium | Sun 03:09-03:39 UTC |

⚠️ **AZ DISTRIBUTION GAP**: Both readers in `us-east-1b`. Writer alone in `us-east-1c`. **No instance in `us-east-1a`**. Subnet group includes 1a, but no instance is provisioned there.

Cluster created 2026-03-02 (newest of the four — only ~7 weeks old).

#### 2.4.2 Pending Maintenance Status
✅ Confirmed at cluster ARN `arn:aws:rds:us-east-1:257394478466:cluster:docdb-luckyus-iluckychaindep`
- Action: `system-update` ("Bug Fixes")
- AutoAppliedAfterDate: `2026-04-28 01:58:59 UTC`
- CurrentApplyDate: `2026-05-03 03:52:00 UTC` (Sat 23:52 ET)

#### 2.4.3 Workload Pattern (last 14 days, hourly p95)
- DatabaseConnections: avg **8**, max **18**
- CPUUtilization: avg **20.6%**, **max 100%** ⚠️ — sustained CPU saturation events seen
- WriteIOPS: avg **5/s**, **peak 10.7/s at 05 UTC** (01:00 ET — daily batch fingerprint matches the documented `~05:00 UTC` company-wide batch window per CLAUDE.md)
- ReadIOPS: 0
- Peak hours UTC: **5, 6, 8** (early morning ET = batch + early China-overlap traffic)
- **Lowest-load 4h window: 09:00-13:00 UTC = 05:00-09:00 ET** (data-driven, post-batch)

#### 2.4.4 Recent Events (last 7 days)
**No events recorded** at cluster or writer instance level. But CloudWatch shows the 100% CPU spike is recurring — worth a separate investigation outside this patch.

#### 2.4.5 Risk Assessment
**Tier: MEDIUM** (but at the upper end). Elevation factors:
- **AZ distribution gap**: 2 of 3 instances in `us-east-1b`. If 1b zone has a partial impairment during patch, the cluster has only 1 healthy instance (the writer in 1c). AZ-failure resilience is reduced compared to the other 3 clusters.
- **Class homogeneity is OK** (all t3.medium), but the 100% CPU max indicates the cluster runs near saturation during batch — failover during a batch window would be slower than usual.
- **Workload owner**: `iluckychaindep` likely = "Luckyus i-Lucky Chain Dependency" — supply-chain-related service (per Luckyus naming convention in CLAUDE.md). Production, customer-impacting if down during business hours.
- Cluster is only 7 weeks old → no operational track record at all.

#### 2.4.6 Recommended Self-Apply Slot
**Sunday 2026-04-27 09:00-13:00 UTC** (Sunday 05:00-09:00 EDT). Selected for: (a) data-driven lowest-load window, (b) **after the daily 05:00 UTC batch completes**, (c) Sunday US morning = customer activity is minimal for a B2B/supply-chain workload, (d) 6 days of buffer before CurrentApplyDate. Avoid the 03:00-08:00 UTC window even though it falls in the cluster's preferred maintenance window — that overlaps the company-wide batch peak.

---

## 3. Application Owner Notification Matrix

| Cluster | Likely App / Workload | Security Group | App Owner Lead Time | Notification Channel |
|---|---|---|---|---|
| `docdb-devops` | Internal DBA / DevOps tooling (Grafana, admin panels, internal dashboards) | sg-0deaa7cf7437e39c7 | 24h (DBA team only) | DBA team Slack + ops calendar |
| `docdb-gia` | GIA application (China HQ — confirm with Michael) | sg-0deaa7cf7437e39c7 | 48h | App owner Slack + email |
| `docdb-iot` | IoT telemetry (store device pings, ~11 stores) | sg-0deaa7cf7437e39c7 | 48h | Ops + IoT engineering Slack |
| `docdb-luckyus-iluckychaindep` | Luckyus chain dependency service (supply chain) | sg-0deaa7cf7437e39c7 | 72h | SCM team + Michael |

> **Note**: All 4 clusters share the same VPC security group `sg-0deaa7cf7437e39c7`. Pull `aws ec2 describe-security-groups --group-ids sg-0deaa7cf7437e39c7` and inspect referencing security groups / CIDRs to identify exact app owners before sending notifications.

### Notification Template (Slack/email)

> **Subject:** Scheduled DocumentDB engine patch — `<cluster-id>` — `<UTC slot>` / `<ET slot>`
>
> Hi team — AWS has scheduled an engine patch (DocumentDB 5.0.0 → 3.0.20421, "Bug Fixes") for cluster `<cluster-id>`. We are self-applying on `<date> <UTC slot>` to control timing. Expected impact: ~30 seconds of write interruption while AWS fails over the writer. Reads against the reader endpoint should be unaffected (one reader at a time will be patched, with the writer last).
>
> Please ensure your application's MongoDB driver has retry-on-`NotPrimary` and `retryWrites=true` enabled. If you have any deploys planned during the slot, please move them. Reach out in `#dba-team` with questions.
>
> A pre-patch snapshot will be created at T-1h. Rollback RTO: 30-60 min.

---

## 4. Self-Apply Runbook

### 4.1 T-24h Pre-checks
- [ ] Confirm `DeletionProtection=true` on all 4 clusters (already verified in §2)
- [ ] Confirm latest automated backup is recent: `aws docdb describe-db-clusters --db-cluster-identifier <id> --query 'DBClusters[0].LatestRestorableTime' --region us-east-1` — should be within last hour
- [ ] Notify application owners using template in §3
- [ ] Subscribe to AWS Health EventBridge rule for `AWS_DOCDB_DB_PATCH_UPGRADE_MAINTENANCE_CANCELLED` so we get told if AWS pulls the patch
- [ ] Verify mongosh/CLI client access to each cluster from the bastion or jump host
- [ ] Open a CloudWatch dashboard with `DatabaseConnections`, `WriteIOPS`, `EngineUptime`, `BufferCacheHitRatio` for the 4 clusters

### 4.2 T-1h Manual Snapshot (DOCUMENT — DO NOT EXECUTE NOW)

```bash
# Run for each cluster ~1 hour before the chosen self-apply slot
aws docdb create-db-cluster-snapshot \
  --db-cluster-identifier <cluster-id> \
  --db-cluster-snapshot-identifier <cluster-id>-pre-patch-3-0-20421-20260426 \
  --region us-east-1
```

Snapshot identifier pattern: `<cluster-id>-pre-patch-3-0-20421-<yyyymmdd>`. Example: `docdb-iot-pre-patch-3-0-20421-20260426`.

Wait for snapshot status `available` before proceeding:
```bash
aws docdb describe-db-cluster-snapshots \
  --db-cluster-snapshot-identifier <snapshot-id> \
  --region us-east-1 \
  --query 'DBClusterSnapshots[0].Status'
```

### 4.3 T-0 Patch Execution (DOCUMENT — DO NOT EXECUTE NOW)

```bash
aws docdb apply-pending-maintenance-action \
  --resource-identifier <cluster-arn> \
  --apply-action system-update \
  --opt-in-type immediate \
  --region us-east-1
```

> **Note**: `--apply-action` value matches the `Action` field in `describe-pending-maintenance-actions` (here: `system-update`, NOT `db-upgrade`). The example in the task brief used `db-upgrade` — that maps to the **major engine version** API path (e.g. PG dify 16.8.R2). Use `system-update` for this DocDB engine patch. If the team prefers, an alternative is to set `--opt-in-type next-maintenance` to apply at the next preferred maintenance window without changing it — useful if we want to defer rather than expedite.

Cluster ARNs:
- `arn:aws:rds:us-east-1:257394478466:cluster:docdb-devops`
- `arn:aws:rds:us-east-1:257394478466:cluster:docdb-gia`
- `arn:aws:rds:us-east-1:257394478466:cluster:docdb-iot`
- `arn:aws:rds:us-east-1:257394478466:cluster:docdb-luckyus-iluckychaindep`

### 4.4 Validation

During apply (every 30s):
```bash
aws docdb describe-events \
  --source-identifier <cluster-id> \
  --source-type db-cluster \
  --duration 60 \
  --region us-east-1
```

Watch for: `DB cluster is being patched` → `Failed over to <new-writer>` → `DB cluster patch completed`.

Post-patch:
```bash
# Cluster status
aws docdb describe-db-clusters --db-cluster-identifier <id> --region us-east-1 \
  --query 'DBClusters[0].{Status:Status,Engine:EngineVersion}'
# Expect: Status=available, EngineVersion advances (the public version label may stay 5.0.0 — the patch is internal)

# Connect via mongosh from bastion and verify
mongosh "mongodb://<endpoint>:27017/?ssl=true&retryWrites=false" \
  --tls --tlsCAFile /etc/ssl/certs/global-bundle.pem -u root -p "$DOCDB_PASS" \
  --eval 'db.adminCommand({buildInfo:1})'
# Validate: buildInfo response, version string, ok:1

# Smoke test from app side (coordinate with owner)
# - Insert + read a known doc
# - Verify p99 latency unchanged within 10% of baseline
```

Watch CloudWatch for 30 min post-patch:
- `EngineUptime` should reset to ~0 then climb (each instance restarts in turn)
- `DatabaseConnections` should briefly drop, then recover to baseline ±10%
- `BufferCacheHitRatio` should warm back to >0.95 within 15 min

---

## 5. Rollback Plan

**When to rollback:** Patch operation does not complete within 2× typical maintenance window (so >60 min from start) OR app-side smoke tests fail post-patch OR sustained connection errors >5 min after patch completion.

**Pre-patch snapshot ID pattern:** `<cluster-id>-pre-patch-3-0-20421-<yyyymmdd>` (created at T-1h per §4.2)

**Restore command (DOCUMENT — DO NOT EXECUTE NOW):**
```bash
# 1. Restore to a NEW cluster (cannot restore in-place)
aws docdb restore-db-cluster-from-snapshot \
  --db-cluster-identifier <original-cluster-id>-restored \
  --snapshot-identifier <snapshot-id> \
  --engine docdb \
  --vpc-security-group-ids sg-0deaa7cf7437e39c7 \
  --db-subnet-group-name docdb-group \
  --kms-key-id arn:aws:kms:us-east-1:257394478466:key/5c5c743d-b79f-4d3a-867f-5e849ee4b52b \
  --deletion-protection \
  --region us-east-1

# 2. Add 3 instances to match original topology (writer + 2 readers)
# 3. Cutover: update app config to point to new cluster endpoint OR rename via DNS
# 4. Once stable, delete old cluster (only after >24h soak)
```

**Estimated RTO:** 30-60 min for snapshot restore + endpoint cutover. App-side cutover time depends on owner's deploy process.

**Rollback decision tree:**
| Symptom | Action |
|---|---|
| Patch hung >60 min | Open AWS Support case (Critical) — DO NOT delete cluster; let AWS finish |
| Patch completed, app errors | App-side mitigation first (driver retry config, connection string) |
| Patch completed, persistent perf regression | Hold for 24h with engineering team; rollback only if regression >50% baseline |
| Patch completed, data corruption suspected | Snapshot restore IMMEDIATELY |

---

## 6. Open Questions / Followups

1. **`docdb-luckyus-iluckychaindep` AZ skew**: 2 of 3 instances in us-east-1b. After this patch is done, schedule a separate maintenance to recreate one of the 1b readers in us-east-1a. Tracking: file ticket post-patch.
2. **`docdb-luckyus-iluckychaindep` 100% CPU events**: Independent of patch. Investigate via slow-query log + Prometheus `docdb_cpu_utilization` over the 05 UTC daily batch window. Tracking: separate ticket.
3. **`docdb-gia` instance class asymmetry**: Writer is t4g.medium, readers r6g.large. After patch validation, consider promoting a reader and resizing the original writer to r6g.large to remove burst-credit risk.
4. **Action type discrepancy** (AWS Health says "DB_PATCH_UPGRADE", API shows `Action=system-update`): Open AWS Support case to confirm naming convention. Not blocking for self-apply, but documentation alignment is useful.
5. **AWS Health EventBridge subscription**: Subscribe to `AWS_DOCDB_DB_PATCH_UPGRADE_MAINTENANCE_CANCELLED` so we are notified if AWS revokes the patch.
6. **Performance Insights**: All 4 clusters have `PerformanceInsightsEnabled=false`. Enabling PI on at least the production-tier 3 (gia/iot/iluckychaindep) would substantially improve our ability to validate post-patch performance — consider enabling as part of T-24h prep (note: enabling PI does NOT require a restart on DocDB).
7. **CA certificates**: All instance certs valid through 2027-02 / 2027-03. Not impacted by this patch but worth noting for next year's rotation.
8. **No previous patch history visible**: 7-day events window was empty for all 4 clusters. Check `--duration 43200` (30d) for a longer view — they may have been patched in March.

---

## Appendix A — Raw API Responses

All raw `aws docdb` and `aws cloudwatch` JSON responses archived under `~/luckin-reports/raw/`:

| File pattern | Content |
|---|---|
| `phase1-all-clusters.json` | Initial DocDB cluster list |
| `phase2-cluster-<id>.json` | `describe-db-clusters` per cluster |
| `phase2-instances-<id>.json` | `describe-db-instances` per cluster |
| `phase3-pending-maintenance.json` | `describe-pending-maintenance-actions` (account-wide) |
| `phase4-<cluster>-<metric>.json` | CloudWatch 14d hourly per metric |
| `phase4-analysis.json` | Computed peak/quiet hours + best 4h windows |
| `phase5-events-cluster-<id>.json` | 7d cluster-level events |
| `phase5-events-instance-<writer>.json` | 7d writer-instance events |

Pre-flight: `sts get-caller-identity` returned `AIDATX3PIBWBHOR7ZX46M` / Account `257394478466` / `arn:aws:iam::257394478466:user/databasecheck` — confirmed Luckin NA.

---

## Appendix B — Patch Window Decision Matrix Summary

| Cluster | UTC Window | ET Window | Hard Deadline (UTC) | Slack |
|---|---|---|---|---|
| docdb-iot | **2026-04-26 05:00-09:00** | Sun 01:00-05:00 EDT | 2026-04-28 05:43 | ~44h |
| docdb-devops | 2026-04-26 19:00-23:00 | Sun 15:00-19:00 EDT | 2026-05-01 03:05 | ~4d |
| docdb-luckyus-iluckychaindep | 2026-04-27 09:00-13:00 | Sun 05:00-09:00 EDT | 2026-05-03 03:52 | ~6d |
| docdb-gia | 2026-04-27 22:00 → 04-28 02:00 | Sun 18:00-22:00 EDT | 2026-05-03 08:06 | ~5d |

End of report.
