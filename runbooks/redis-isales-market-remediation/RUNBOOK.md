# Executable Runbook: Redis Memory Remediation — `luckyus-isales-market`

**Cluster:** `luckyus-isales-market` (AWS ElastiCache, `cache.t4g.medium`)
**Endpoint:** `rediss://master.luckyus-isales-market.vyllrs.use1.cache.amazonaws.com:6379`
**Region:** us-east-1 | **Nodes:** 2 (primary + replica, Multi-AZ)
**Date Created:** 2026-02-12
**Owner:** SRE / DevOps DBA, Luckin Coffee US

---

## Table of Contents

1. [Current Status Check](#1-current-status-check)
2. [TTL Remediation Scripts](#2-ttl-remediation-scripts)
3. [Scaling Recommendation](#3-scaling-recommendation)
4. [Policy Change Analysis](#4-policy-change-analysis)
5. [Monitoring Configs](#5-monitoring-configs)
6. [Communication Template](#6-communication-template)
7. [2026-06-29 No-TTL Audit + Command Cheat-Sheet](#7-2026-06-29-no-ttl-audit--command-cheat-sheet)

---

## 1. Current Status Check

### 1.1 Live Memory Status (as of 2026-02-12 ~14:35 UTC)

| Metric | Value | Trend |
|--------|-------|-------|
| used_memory_human | **1.96 G** | Dropping (was 2.01G 30 min ago) |
| maxmemory | 2.32 G | — |
| Memory % | **84.6%** | Recovering from 87.5% peak |
| evicted_keys | 0 | No evictions triggered |
| Total keys | 6,658,630 | Dropping (was 6,700,023) |
| Keys with TTL | 4,034,921 (60.6%) | Burst keys expiring |
| Keys WITHOUT TTL | **2,623,709 (39.4%)** | **Chronic — unchanged** |
| ops/sec | 212 | Down from 3,817 during burst |

### 1.2 CloudWatch Memory Trend (13:00 – 14:28 UTC)

```
13:00  ████████████████████████████████                                61.3%
13:16  ████████████████████████████████                                61.1%
13:32  ████████████████████████████████                                61.2%
13:48  ████████████████████████████████                                61.2%
13:52  ████████████████████████████████                                61.5%  ← first uptick
13:56  ████████████████████████████████                                61.5%
14:00  █████████████████████████████████████████                       71.0%  ← BURST START
14:04  ██████████████████████████████████████████████████              81.4%
14:08  ██████████████████████████████████████████████████████████      87.5%  ← PEAK
14:12  █████████████████████████████████████████████████████████       87.3%
14:16  ██████████████████████████████████████████████████████████████  89.4%  ← absolute max
14:20  █████████████████████████████████████████████████████████       87.7%
14:24  ████████████████████████████████████████████████████████        86.8%
14:28  ███████████████████████████████████████████████████████         85.5%  ← recovering
```

**Verdict:** Burst keys (11–29 min TTL) are expiring. Memory is recovering. **No immediate emergency action needed**, but the chronic no-TTL problem must be fixed to prevent recurrence.

### 1.3 Verify Recovery Commands

```bash
# Check current memory via AWS CLI (run every 5 minutes until <75%)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name DatabaseMemoryUsagePercentage \
  --dimensions Name=CacheClusterId,Value=luckyus-isales-market-001 \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Maximum \
  --region us-east-1

# Quick Redis memory check
redis-cli -h master.luckyus-isales-market.vyllrs.use1.cache.amazonaws.com \
  -p 6379 --tls --no-auth-warning INFO memory | grep -E 'used_memory_human|maxmemory_human'
```

### 1.4 If Memory Stays >85% — Find Burst Source

```bash
# Query CloudWatch Logs Insights for isales-market services around spike time (13:57 UTC)
aws logs start-query \
  --log-group-name '/ecs/luckyus-isales-market' \
  --start-time $(date -d '2026-02-12T13:45:00Z' +%s) \
  --end-time $(date -d '2026-02-12T14:15:00Z' +%s) \
  --query-string 'fields @timestamp, @message
    | filter @message like /(?i)(redis|cache|SET|SADD|contact|marketing|campaign)/
    | stats count() as cmd_count by bin(1m)
    | sort cmd_count desc
    | limit 20' \
  --region us-east-1

# Check for scheduled cron/batch jobs
aws events list-rules --region us-east-1 \
  --query "Rules[?contains(Name, 'isales') || contains(Name, 'marketing') || contains(Name, 'contact')].[Name,ScheduleExpression,State]" \
  --output table

# Check ECS task activity around spike time
aws ecs list-tasks --cluster luckyus-prod \
  --service-name isales-market-service \
  --desired-status RUNNING \
  --region us-east-1
```

---

## 2. TTL Remediation Scripts

All scripts are in [`./scripts/`](./scripts/) directory.

### Prerequisites

```bash
pip install redis
```

### Script Inventory

| Script | Target Pattern | Keys Affected | Proposed TTL | Risk |
|--------|---------------|---------------|-------------|------|
| [`fix_ttl_coupon_unread.py`](./scripts/fix_ttl_coupon_unread.py) | `MARKETING:COUPON:UNREAD:*` | 147,111 | 60 days | LOW — read-heavy, regenerated on coupon events |
| [`fix_ttl_user_group_label.py`](./scripts/fix_ttl_user_group_label.py) | `contact:userGroupLabel:set:*` | 177,450 | 30 days | MEDIUM — verify group label rebuild logic |
| [`fix_ttl_exchange_price.py`](./scripts/fix_ttl_exchange_price.py) | `exchange:coupon:high:commodity:price:*` | 473 | 7 days | LOW — small count, price cache |
| [`fix_ttl_last_activity.py`](./scripts/fix_ttl_last_activity.py) | `contact:last:activity:*` | 374,639 | 90 days (reduce from 364d) | LOW — reduces existing TTL |
| [`fix_ttl_contact_freq.py`](./scripts/fix_ttl_contact_freq.py) ⭐ | `CONTACT_day_* / CONTACT_week_* / CONTACT_month_* / CONTACT_<member>_*` | **~10.8 M** (≈95% of all no-TTL) | **date-aware**: day 14d / week 35d / month 60d / bare 30d, measured from the date in the key | MEDIUM — confirm with iSales dev that freq-control only needs recent windows |

> ⭐ **Added 2026-06-29.** This family was NOT in the original (2026-02) runbook because at that
> time total keys were 6.66M with 39% no-TTL. The cluster has since grown to **15.7M keys / 72.5%
> no-TTL**, and sampling (Section 7) shows the legacy `CONTACT_*` frequency-control counters are the
> dominant driver. **This is now the highest-impact script — run it first.**

### Execution Order

```bash
# Step 1: Dry-run ALL scripts first (read-only, counts keys and checks TTL)
python scripts/fix_ttl_contact_freq.py      --dry-run    # ⭐ the big one (~10.8M keys)
python scripts/fix_ttl_coupon_unread.py     --dry-run
python scripts/fix_ttl_user_group_label.py  --dry-run
python scripts/fix_ttl_exchange_price.py    --dry-run
python scripts/fix_ttl_last_activity.py     --dry-run

# Step 2: Review dry-run output — confirm key counts match expectations
# Step 3: Execute — biggest memory win first, then smallest-impact cleanups
python scripts/fix_ttl_contact_freq.py                # ⭐ ~10.8M keys (date-aware EXPIREAT)
python scripts/fix_ttl_exchange_price.py              # 473 keys
python scripts/fix_ttl_coupon_unread.py               # 147K keys
python scripts/fix_ttl_last_activity.py               # 374K keys
python scripts/fix_ttl_user_group_label.py            # 177K keys

# Step 4: Verify memory improvement
redis-cli -h master.luckyus-isales-market.vyllrs.use1.cache.amazonaws.com \
  -p 6379 --tls INFO memory | grep used_memory_human
```

> **Note on `fix_ttl_contact_freq.py`:** stale (past-due) keys are NOT mass-deleted — each gets a
> randomized 6h–3d grace TTL so the ~9M expirations drain gradually instead of a thundering-herd
> purge that could spike CPU/latency. Recent-dated keys get a rolling EXPIREAT. Run during off-peak.

---

## 3. Scaling Recommendation

### Current Cluster Configuration

| Property | Value |
|----------|-------|
| Node Type | `cache.t4g.medium` |
| Memory (instance) | 3.09 GiB |
| maxmemory (Redis) | 2.32 GiB |
| vCPU | 2 |
| Network | Up to 5 Gbps |
| Nodes | 2 (primary + replica, Multi-AZ) |
| Auto-Failover | Enabled |

### Cost Comparison Table (us-east-1, On-Demand, 2 nodes)

| Node Type | Memory | maxmemory (est.) | vCPU | $/hr/node | Monthly (2 nodes) | Delta vs Current |
|-----------|--------|-------------------|------|-----------|-------------------|-----------------|
| **cache.t4g.medium** (current) | 3.09 GiB | **2.32 G** | 2 | $0.065 | **$94.90** | — |
| **cache.m7g.large** | 6.38 GiB | ~4.8 G | 2 | $0.158 | **$230.68** | +$135.78 (+143%) |
| **cache.r6g.large** | 13.07 GiB | ~9.8 G | 2 | $0.206 | **$300.76** | +$205.86 (+217%) |
| **cache.r7g.large** | 13.07 GiB | ~9.8 G | 2 | $0.219 | **$319.74** | +$224.84 (+237%) |

> **Note:** Monthly cost = price/hr × 730 hrs × 2 nodes. `maxmemory` is approximately 75% of instance memory for ElastiCache.

### Recommendation

**Option A (Preferred): Fix TTLs first, then reassess.**
After applying TTL remediation scripts (Step 2), the 2.6M no-TTL keys will begin expiring over 7–90 days. This could free ~0.4–0.6G of memory, bringing baseline usage to ~55–60%. This may be sufficient on the current `cache.t4g.medium`.

**Option B: Scale to `cache.m7g.large` if TTL fix alone is insufficient.**
This doubles maxmemory to ~4.8G at +$135.78/month. Best balance of cost and headroom. The `t4g` → `m7g` migration involves a brief failover (~30s with Multi-AZ).

### Scaling Command (if needed)

```bash
# Online vertical scaling — triggers a brief failover (~30 seconds)
aws elasticache modify-replication-group \
  --replication-group-id luckyus-isales-market \
  --cache-node-type cache.m7g.large \
  --apply-immediately \
  --region us-east-1

# Monitor scaling progress
watch -n 10 "aws elasticache describe-replication-groups \
  --replication-group-id luckyus-isales-market \
  --query 'ReplicationGroups[0].{Status:Status,NodeType:CacheNodeType}' \
  --region us-east-1"
```

> **Downtime:** ElastiCache online vertical scaling with Multi-AZ performs a failover. Expect ~10-30 seconds of write unavailability. Schedule during low-traffic window.

---

## 4. Policy Change Analysis: `volatile-lfu` → `allkeys-lfu`

### Current Policy: `volatile-lfu`

| Behavior | Detail |
|----------|--------|
| Eviction scope | **Only keys with TTL set** |
| No-TTL keys | **Never evicted** — immune to memory pressure |
| Current eviction candidates | 4,034,921 keys (60.6%) |
| Non-evictable keys | 2,623,709 keys (39.4%) |

### Proposed Policy: `allkeys-lfu`

| Behavior | Detail |
|----------|--------|
| Eviction scope | **ALL keys**, regardless of TTL |
| No-TTL keys | **Can be evicted** based on access frequency |
| Eviction candidates | 6,658,630 keys (100%) |

### Risk/Benefit Analysis

| Factor | `volatile-lfu` (current) | `allkeys-lfu` (proposed) |
|--------|--------------------------|--------------------------|
| **Safety** | No-TTL keys are protected | No-TTL keys CAN be evicted |
| **Memory ceiling** | Grows unboundedly with no-TTL keys | Self-managing under pressure |
| **Data loss risk** | None for no-TTL keys | Possible — LFU may evict infrequently-accessed but important keys |
| **Suitable when** | All keys have proper TTLs | Some keys intentionally lack TTL |

### Specific Risks

| Key Pattern | Risk if Evicted | Likelihood under `allkeys-lfu` |
|-------------|----------------|-------------------------------|
| `contact:userGroupLabel:set:*` | User group labels lost; requires rebuild from DB | MEDIUM — accessed periodically during campaigns |
| `MARKETING:COUPON:UNREAD:*` | Coupon unread flags lost; users may see stale badge counts | LOW — accessed on every app open |
| `exchange:coupon:high:commodity:price:*` | Price cache miss → DB fallback | LOW — frequently accessed |

### Recommendation

> **Do NOT switch to `allkeys-lfu` yet.** Apply TTL remediation first (Step 2). Once all key patterns have proper TTLs, `volatile-lfu` will cover 100% of keys and the policy distinction becomes moot. Switching prematurely risks silent data loss for keys that the application expects to be persistent.
>
> **Revisit in 2 weeks** after TTL scripts have been running. If no-TTL keys still exist due to application code not being updated, THEN consider `allkeys-lfu` as a safety net.

### Policy Change Command (for future reference)

```bash
# ONLY execute after confirming all key patterns have TTLs
aws elasticache modify-replication-group \
  --replication-group-id luckyus-isales-market \
  --cache-parameter-group-name <new-param-group-with-allkeys-lfu> \
  --apply-immediately \
  --region us-east-1
```

---

## 5. Monitoring Configs

### 5.1 Prometheus Alerting Rules

File: [`./monitoring/redis-memory-alerts.yaml`](./monitoring/redis-memory-alerts.yaml)

Two-tier alerting: **Warning at 60%**, **Critical at 70%** (current rule).

### 5.2 Grafana Dashboard Panel

File: [`./monitoring/redis-memory-dashboard.json`](./monitoring/redis-memory-dashboard.json)

Panels:
1. **Memory Usage %** — time series with 60%/70%/85% thresholds
2. **Keys: With TTL vs Without TTL** — stacked bar
3. **Eviction Rate** — time series
4. **Key Count by Prefix** — table/bar chart

---

## 6. Communication Template

### Slack Message to iSales Marketing Dev Team

File: [`./COMMUNICATION.md`](./COMMUNICATION.md)

Bilingual (English + Chinese) message with:
- Incident summary
- Root cause
- Required application code changes
- TTL policy table
- Timeline

---

## Execution Checklist

- [ ] **Step 1:** Verify memory recovery (Section 1) — monitor until <75%
- [ ] **Step 2:** Run TTL scripts in dry-run mode (Section 2) — **start with `fix_ttl_contact_freq.py`**
- [ ] **Step 3:** Share dry-run results with iSales dev team for sign-off
- [ ] **Step 4:** Execute TTL scripts in production (off-peak hours)
- [ ] **Step 5:** Send communication to dev team (Section 6) — request app code TTL changes (+ migrate legacy `CONTACT_*` → `cfc:v2:*`)
- [ ] **Step 6:** Deploy Prometheus alerts (Section 5.1) + Grafana dashboard (Section 5.2)
- [ ] **Step 7:** Monitor for 2 weeks — reassess if scaling or policy change needed
- [ ] **Step 8:** If memory still >75% after 2 weeks → scale to `cache.m7g.large` (Section 3)

---

## 7. 2026-06-29 No-TTL Audit + Command Cheat-Sheet

### 7.1 What changed since 2026-02

| Metric | 2026-02-12 | 2026-06-29 | Δ |
|--------|-----------|-----------|---|
| Total keys | 6,658,630 | **15,703,473** | +136% |
| Keys WITHOUT TTL | 2,623,709 (39.4%) | **~11,385,117 (72.5%)** | +334% |
| used_memory / maxmemory | 1.96G / 2.32G (84.6%) | 3.31G / 4.79G (~68%) | cluster was scaled up since |
| evicted_keys | 0 | 0 | unchanged |

> The cluster was already scaled (maxmemory 2.32G → 4.79G), so current memory % (~68%) is healthy
> with no evictions and **no active alarm**. But the no-TTL key count nearly 4×'d — the chronic
> problem got worse, not better. Day-to-day memory now oscillates 62–68% (daily write sawtooth);
> alerts that fire are transient threshold grazes, not true exhaustion.

### 7.2 No-TTL key composition (SCAN sampling, n = 58,812 distinct keys)

Sampling method: chained-cursor `SCAN ... COUNT 20000` (never `KEYS`), 3 non-overlapping batches.
No-TTL share measured at **74.3%** (vs 72.5% global keyspace — representative). Three independent
sample sizes (1k / 20k / 59k) all converged on the same distribution.

| Key family | Share of no-TTL | Extrapolated count | TTL (verified) |
|------------|----------------|--------------------|----------------|
| `CONTACT_day_<member>_<date>_<n>` | 79.6% | **~9.06 M** | -1 (confirmed across 2025-12 … 2026-06 dates) |
| `CONTACT_<member>_<n>_<n>` (bare) | 7.8% | ~0.89 M | -1 |
| `CONTACT_week_<member>_<date>_<n>` | 5.4% | ~0.61 M | -1 |
| `CONTACT_month_<member>_<ym>_<n>` | 2.1% | ~0.24 M | -1 |
| **CONTACT_\* subtotal** | **94.8%** | **~10.8 M** | all no-TTL |
| `contact:userGroupLabel:set:<member>` | 2.7% | ~0.31 M | -1 |
| `MARKETING:COUPON:UNREAD:<member>:coupon` | 2.5% | ~0.28 M | -1 |

Families that ALREADY have TTL (no action): `realtime:ug:event:*` (~20h),
`contact:user:contacted:activity:one:day:*` (~42h), `user:activity:Category:FreqCtrl:*` (~29d),
`isales:realtime:usergroup:koala:message:*` (~22h), `c:a:r:u:*` (~8d), `popupfrq:*` (~1.5h),
`contact:last:activity:*` (~365d, over-long — see `fix_ttl_last_activity.py`).

**Root cause:** legacy code path (uppercase `CONTACT_`) writes dated frequency-control counters
with no `EXPIRE`. The newer `cfc:v2:*` namespace (seen rarely in the sample) does it correctly →
the long-term fix is to migrate writers to `cfc:v2:*`; this runbook backfills the legacy debt.

### 7.3 Read-only diagnostics (copy-paste, safe on prod)

> **MCP gateway gotcha:** `mcp-db-gateway` maps args **positionally** to redis-py
> `scan(cursor, match, count)`. Pass `SCAN <cursor> <match> <count>` — e.g. `["0", "*", "20000"]`.
> `["0","COUNT","1000"]` is WRONG (it matches keys literally named `COUNT`). `EVAL`, `MEMORY`,
> `RANDOMKEY` are **denied** by the gateway — use `SCAN`/`TTL`/`INFO`/`DBSIZE` only.

```bash
H=master.luckyus-isales-market.vyllrs.use1.cache.amazonaws.com
RC="redis-cli -h $H -p 6379 --tls --no-auth-warning"

# Memory + keyspace snapshot
$RC INFO memory   | grep -E 'used_memory_human|maxmemory_human|maxmemory_policy'
$RC INFO keyspace                       # db0: keys=, expires=  (no-TTL = keys - expires)
$RC INFO stats    | grep -E 'evicted_keys|expired_keys'

# Estimate no-TTL share by family WITHOUT blocking (random sampling, native to redis-cli).
# --memkeys-samples / scan-based; here a simple no-TTL prefix tally over a SCAN sample:
$RC --scan --pattern 'CONTACT_day_*'  --count 1000 | head -100000 | wc -l   # rough magnitude
for p in CONTACT_day_ CONTACT_week_ CONTACT_month_ 'contact:userGroupLabel:set:' 'MARKETING:COUPON:UNREAD:'; do
  k=$($RC --scan --pattern "${p}*" --count 1000 | head -1)
  printf '%-32s sample_key=%s ttl=%s\n' "$p" "$k" "$($RC TTL "$k")"
done
```

### 7.4 Backfill commands (WRITE — needs an account with write perms; `databasecheck` is read-only)

```bash
# 1) DRY-RUN everything first — counts no-TTL keys per family, writes nothing
python scripts/fix_ttl_contact_freq.py --dry-run

# (optional) scope the dry-run / apply to one sub-family at a time
python scripts/fix_ttl_contact_freq.py --pattern day   --dry-run
python scripts/fix_ttl_contact_freq.py --pattern week  --dry-run
python scripts/fix_ttl_contact_freq.py --pattern month --dry-run
python scripts/fix_ttl_contact_freq.py --pattern bare  --dry-run

# 2) APPLY (off-peak). Date-aware: rolling EXPIREAT for recent keys,
#    jittered 6h–3d grace TTL for past-due keys (gradual drain, no mass DEL).
python scripts/fix_ttl_contact_freq.py                 # all four CONTACT_* families

# 3) Watch the drain (no-TTL count should fall, used_memory should drop over hours/days)
watch -n 300 "$RC INFO keyspace; $RC INFO memory | grep used_memory_human"
```

**Pure-redis-cli equivalent** (if you cannot run the Python script — flat TTL, NOT date-aware;
prefer the script). Adds a 14-day TTL only to `CONTACT_day_*` keys that currently have none:

```bash
H=master.luckyus-isales-market.vyllrs.use1.cache.amazonaws.com
RC="redis-cli -h $H -p 6379 --tls --no-auth-warning"
$RC --scan --pattern 'CONTACT_day_*' --count 500 | while read -r k; do
  [ "$($RC TTL "$k")" = "-1" ] && $RC EXPIRE "$k" 1209600 >/dev/null   # 14d
done
# Repeat with CONTACT_week_* (3024000 = 35d) and CONTACT_month_* (5184000 = 60d).
# Throttle on a busy cluster: insert `sleep 0.05` inside the loop.
```

### 7.5 Expected outcome

- `CONTACT_*` no-TTL count (~10.8M) drains over the retention windows; stale (pre-retention) keys
  clear within ~3 days via the jittered grace TTL.
- No-TTL share should fall from ~72% toward the ~5% residual (the genuinely-needs-TTL-from-app keys),
  daily memory sawtooth peak drops well below current ~68%, and `volatile-lfu` regains the ability to
  evict under pressure.
- Re-run the Section 7.3 diagnostics after 72h and again at 2 weeks to confirm.
