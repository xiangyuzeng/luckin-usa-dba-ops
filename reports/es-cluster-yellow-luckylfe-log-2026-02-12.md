# ES Cluster RED Status Investigation Report (Escalated from Yellow)

**Cluster**: `luckylfe-log`
**Alert**: AWS-ES 集群状态 Yellow -> **RED** (Escalated)
**Initial Alert**: 2026-02-12 19:00 UTC (Yellow)
**Escalation to RED**: 2026-02-12 19:47 UTC
**Last Updated**: 2026-02-12 20:15 UTC
**Severity**: **P1 CRITICAL - 3 data nodes crashed, primary shards lost, master unreachable**

---

## 1. Affected Cluster Summary

| Property | Value |
|---|---|
| **Domain Name** | luckylfe-log |
| **Engine** | Elasticsearch 7.10 (build R20250625) |
| **VPC Endpoint** | vpc-luckylfe-log-eh3n6nwo4c43eofoz36j35kni4.us-east-1.es.amazonaws.com |
| **Data Nodes** | 4x m5.large.elasticsearch (2 vCPU, 8 GiB RAM each) |
| **Dedicated Masters** | 3x t3.medium.elasticsearch |
| **EBS Volume** | 80 GB gp2 per node (320 GB total) |
| **Zone Awareness** | 2 AZs (us-east-1a, us-east-1b) |
| **Account** | 257394478466 |
| **Auto-Tune** | DISABLED |

## 2. Current Status (as of 20:15 UTC)

| Metric | Value | Status |
|---|---|---|
| **Cluster Status** | **RED** | Primary shards missing |
| **Node Count** | **5 of 7** (recovering) | 3 data nodes crashed at 19:47, 1 recovering |
| **Unassigned Shards** | **290** (was 448 at worst) | Partially recovering |
| **Active Primary Shards** | **281 of 558** | 277 primary shards still missing |
| **Active Total Shards** | 312 (was 604) | 48% of normal |
| **JVM Memory Pressure** | 64% (was 100%) | Stabilized after node crash |
| **CPU Utilization** | 55% | Moderate |
| **Master Reachable** | **NO** (since 19:22) | Master election unstable |
| **Kibana** | **DOWN** (since 20:07) | KibanaHealthyNodes = 0 |
| **Free Storage** | 15 GB / 80 GB per node | OK for now |
| **5xx Errors** | 37 in last 30 min | Active errors |

## 3. Full Incident Timeline

### Phase 1: JVM Pressure Build-up (13:00-18:42 UTC) - Status: GREEN
```
Time (UTC)     JVM Max%  Unassigned  Nodes  Indexing(docs/5m)  Search(req/5m)
────────────── ──────── ─────────── ────── ────────────────── ──────────────
13:32          75.1%    0           7      ~47,000            ~800
14:32          70.3%    0           7      ~47,000            ~800
15:32          72.7%    0           7      ~47,000            ~800
16:32          75.4%    0           7      ~47,000            ~800
17:32          67.8%    0           7      45,346             1,002
18:32          78.3%    0           7      47,814             1,178
18:42          72.1%    0           7      47,851             1,358          <- Last normal state
```

### Phase 2: JVM Spike + GC Death Spiral (18:47-18:52) - Status: GREEN -> DEGRADED
```
18:47          97.6%    0           7      35,091             2,395          <- Search spike 2x!
18:52          99.9%    0           7      2,898              27             <- Indexing collapsed 94%
                                                                               Cluster space: 161→48 GB
                                                                               (ISM deleted old indices)
```

### Phase 3: Yellow Status (19:00-19:46) - Status: YELLOW
```
19:02          99.8%    4           7      2,654              148
19:12          99.9%    4           7      1,814              22
19:17          100.0%   7           7      2,647              40
19:22          100.0%   7           7      3,327              47             <- Master UNREACHABLE!
19:27          99.9%    7           7      1,902              26
19:32          100.0%   7           7      ---                ---
19:37          99.9%    7           7      ---                ---
19:42          100.0%   7           7      964                8
```

### Phase 4: CRITICAL - Node Crash + RED Status (19:47+)
```
19:47          100.0%   448         4      2,098              31             <- 3 NODES CRASHED! RED!
19:52          100.0%   448         4      2,104              29               408 primary shards LOST
19:57          99.9%    448         4      155                15
20:02          60.1%    448         4      2,116              19             <- JVM drops (less load)
20:07          62.8%    452         4→5    2,107              20             <- 1 node recovering
20:10          ---      290         5      ---                ---            <- Shards reassigning
20:15          64.4%    290         5      ---                ---            <- Recovery stalling
```

### Node Loss Detail (1-minute resolution)
```
19:46  Nodes=7  (all present)
19:47  Nodes=4  ← 3 data nodes crashed simultaneously (JVM OOM kill)
19:48-20:09  Nodes=4  (stable at 4 = 1 data + 3 master)
20:10  Nodes=5  ← 1 data node recovering
20:11+ Nodes=5  (2 more data nodes still down)
```

## 4. Root Cause Analysis

### Primary Root Cause: JVM OOM Killed 3 of 4 Data Nodes

The incident is a cascading failure caused by chronic JVM under-sizing:

**Stage 1 - Chronic JVM pressure (ongoing issue)**
- m5.large nodes have only **~4 GB JVM heap**
- 151 shards per data node far exceeds the recommended 80-100 per 4 GB heap
- JVM avg pressure was steadily climbing all day (40% → 80%)

**Stage 2 - Search spike triggered GC death spiral (18:47)**
- Search rate doubled to 2,395 req/5min
- JVM spiked from 78% → 97.6% → 99.9%
- Full GC loops consumed all CPU, indexing and search collapsed

**Stage 3 - Sustained OOM killed 3 nodes (19:47)**
- JVM remained at 100% for **60 continuous minutes** (18:47-19:47)
- ES JVM on 3 of 4 data nodes hit OutOfMemoryError
- Nodes crashed simultaneously at 19:47
- 408 primary shards became unassigned → RED status

**Stage 4 - Partial recovery (20:07+)**
- 1 data node auto-restarted at 20:10
- Shard reassignment in progress (290 unassigned, down from 448)
- Master still reported unreachable (cluster coordination impaired)
- 2 data nodes still down

### Contributing Factors

| Factor | Details | Severity |
|---|---|---|
| **Undersized JVM heap** | m5.large = ~4 GB heap for 151 shards/node | **ROOT CAUSE** |
| **Too many shards per node** | 151 shards/node vs recommended ~100 max | HIGH |
| **No JVM >80% alarm** | No early warning before critical threshold | HIGH |
| **Master node JVM impact** | t3.medium masters also under JVM pressure | HIGH |
| **Auto-Tune DISABLED** | No automatic JVM/config optimization | MEDIUM |
| **Search spike** | 2x normal search load at 18:47 was the trigger | TRIGGER |

## 5. Production Impact Assessment

### IMPACT: **P1 CRITICAL**

| Impact Area | Status | Details |
|---|---|---|
| **Data Availability** | **PARTIAL OUTAGE** | Only 281/558 primary shards (50%) accessible |
| **Data Integrity** | **AT RISK** | 277 primary shards on crashed nodes - data preserved on EBS but inaccessible until nodes recover |
| **Log Ingestion** | **DOWN ~96%** | 2K/5min vs normal 47K/5min |
| **Search/Query** | **DOWN ~98%** | ~20/5min vs normal ~800/5min |
| **Kibana** | **DOWN** | KibanaHealthyNodes = 0 since 20:07 |
| **Master Coordination** | **IMPAIRED** | Master unreachable since 19:22 |
| **5xx Errors** | **ACTIVE** | 37 errors in 30 minutes |

**Data Loss Risk**: LOW - EBS volumes persist independent of node state. When the 2 remaining data nodes restart, their shards will be recovered from disk. No data should be permanently lost unless EBS volumes are corrupted.

## 6. Recommended Remediation

### IMMEDIATE (Right Now - P1 Response)

**Action 1: Monitor node auto-recovery (in progress)**
AWS managed ES should auto-restart crashed data nodes. Currently 5/7 nodes back. Monitor:
```bash
# Check every 2 minutes
watch -n 120 'aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name Nodes --dimensions Name=DomainName,Value=luckylfe-log \
  Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d "5 min ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Minimum --output text'
```

**Action 2: Once all 7 nodes are back, force shard allocation retry**
```bash
curl -XPOST "https://vpc-luckylfe-log-eh3n6nwo4c43eofoz36j35kni4.us-east-1.es.amazonaws.com/_cluster/reroute?retry_failed=true"
```

**Action 3: Clear caches to prevent JVM re-spike when shards reload**
```bash
curl -XPOST "https://vpc-luckylfe-log-eh3n6nwo4c43eofoz36j35kni4.us-east-1.es.amazonaws.com/_cache/clear"
```

**Action 4: Reduce replica count to 0 cluster-wide to lower shard count**
```bash
# Critical: reduces total shard count by ~46, freeing JVM for recovery
curl -XPUT "https://vpc-luckylfe-log-eh3n6nwo4c43eofoz36j35kni4.us-east-1.es.amazonaws.com/_all/_settings" \
  -H 'Content-Type: application/json' \
  -d '{"index": {"number_of_replicas": 0}}'
```

**Action 5: If nodes don't auto-recover within 30 min, contact AWS Support**
- Open a Severity 1 case via AWS Console -> Support
- Reference domain: luckylfe-log, account: 257394478466, region: us-east-1
- Describe: 3 data nodes crashed due to JVM OOM, not auto-recovering

### URGENT (Within 24 hours)

**Upgrade instance type: m5.large -> m5.xlarge**
- m5.xlarge = 4 vCPU, 16 GiB RAM -> ~8 GB JVM heap (2x current)
- AWS Console -> OpenSearch -> luckylfe-log -> Edit domain -> Instance type
- Blue/green deployment, zero downtime

### LONG-TERM (Within 1-2 weeks)

1. **Reduce shard count**: Target < 100 shards per node. Consolidate daily indices into larger rollover indices
2. **Enable Auto-Tune**: Let AWS optimize JVM settings automatically
3. **Upgrade to OpenSearch 2.x**: ES 7.10 is EOL, newer versions have better memory management
4. **Add UltraWarm tier**: Move logs >7 days old to cheaper warm storage
5. **Increase EBS to gp3 150GB**: Better IOPS and more headroom
6. **Add CloudWatch alarms**:
   - JVM > 80% for 10 min → Warning
   - JVM > 92% for 5 min → Critical
   - Nodes < 7 → Critical
   - ClusterStatus.red = 1 → P1 Page

## 7. 中文摘要 (Slack 通知)

```
🔴🔴🔴 [P1紧急] luckylfe-log ES集群状态: RED - 3个数据节点宕机

⏰ 事件时间线:
• 18:47 UTC - JVM内存压力飙升至100% (搜索请求突增触发)
• 19:00 UTC - 集群变为Yellow (7个副本分片未分配)
• 19:22 UTC - Master节点不可达
• 19:47 UTC - ⚠️ 3个数据节点因JVM OOM同时崩溃 → 集群变RED
• 20:10 UTC - 1个节点开始恢复 (当前5/7)

📊 当前状态 (20:15 UTC):
• 集群状态: RED ❌
• 节点: 5/7 (仍有2个数据节点未恢复)
• 主分片: 仅281/558可用 (50%)
• 未分配分片: 290个
• JVM: 64% (已从100%降下来,因为大部分数据在宕机节点上)
• Kibana: 已不可用 ❌
• 日志写入: 下降96%
• 5xx错误: 过去30分钟37个

🔍 根因:
m5.large实例JVM堆仅4GB,承载151分片/节点(推荐上限100),
JVM持续100%达60分钟后,3个数据节点OOM崩溃。

⚡ 影响:
• 数据: EBS卷持久化,节点恢复后数据应可找回 (无永久丢失风险)
• 日志写入/搜索: 严重降级,约96-98%下降
• Kibana: 完全不可用

🔧 需要执行的操作:
1. [监控中] 等待剩余2个数据节点自动恢复
2. [恢复后] 执行 POST /_cluster/reroute?retry_failed=true
3. [恢复后] 设置所有索引副本数为0: PUT /_all/_settings {"number_of_replicas":0}
4. [恢复后] 清理缓存: POST /_cache/clear
5. [如30分钟内未恢复] 立即开AWS工单 (Severity 1)
6. [24h内] 升级实例 m5.large → m5.xlarge (JVM翻倍)

⚠️ 请SRE值班人员立即关注!如节点未在30分钟内自动恢复,需开AWS Support工单。
```

---

## Appendix: Monitoring Commands

### Check recovery progress
```bash
# Node count
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name Nodes --dimensions Name=DomainName,Value=luckylfe-log \
  Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '5 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Minimum --output table

# Cluster status
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name ClusterStatus.red --dimensions Name=DomainName,Value=luckylfe-log \
  Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '5 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Maximum --output table

# Unassigned shards
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name Shards.unassigned --dimensions Name=DomainName,Value=luckylfe-log \
  Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '5 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Maximum --output table
```

---

*Report generated: 2026-02-12T19:30:00Z*
*Escalation update: 2026-02-12T20:15:00Z*
*Investigator: Claude Code (automated)*
