# OpenSearch 集群快速减压方案

**日期**: 2026-04-29
**适用**: `luckylfe-log`（RED 报警）+ `luckyur-log`（Yellow 报警）
**类型**: 即时止损 — 集群级动态参数下发，零中断
**预计耗时**: 5 分钟下发 + 30 分钟观察

---

## 1. 方案概述

通过 `_cluster/settings` PUT 动态调整 7 个内存/熔断器参数，给 JVM 装"保险丝"。原理：让昂贵查询提前失败而不是把堆吃满，避免再次出现"搜索峰值 → JVM 100% → 节点 OOM → RED"的级联。

**特点**：
- ✅ 立即生效（无需重启 / 蓝绿部署）
- ✅ 一句 curl 即可回滚
- ✅ 不改实例规格、不动 EBS、不影响数据
- ⚠️ 部分超大查询会被熔断器拒绝（这是预期 — 让客户端可控降级好过让集群崩）

---

## 2. 执行命令

### 2.1 luckylfe-log

```bash
ENDPOINT='https://vpc-luckylfe-log-eh3n6nwo4c43eofoz36j35kni4.us-east-1.es.amazonaws.com'

curl -XPUT "$ENDPOINT/_cluster/settings" \
  -H 'Content-Type: application/json' \
  -d '{
  "persistent": {
    "indices.breaker.total.limit": "70%",
    "indices.breaker.request.limit": "50%",
    "indices.breaker.fielddata.limit": "25%",
    "indices.fielddata.cache.size": "15%",
    "search.max_buckets": 10000,
    "action.search.shard_count.limit": 500,
    "cluster.routing.allocation.total_shards_per_node": 200
  }
}'

# 处理已有的 26 个未分配分片
curl -XPOST "$ENDPOINT/_cluster/reroute?retry_failed=true"

# 如未恢复，查看根因
curl "$ENDPOINT/_cluster/allocation/explain?pretty"
```

### 2.2 luckyur-log

```bash
ENDPOINT='https://vpc-luckyur-log-<id>.us-east-1.es.amazonaws.com'

curl -XPUT "$ENDPOINT/_cluster/settings" \
  -H 'Content-Type: application/json' \
  -d '{
  "persistent": {
    "indices.breaker.total.limit": "70%",
    "indices.breaker.fielddata.limit": "25%",
    "indices.fielddata.cache.size": "15%",
    "search.max_buckets": 10000,
    "action.search.shard_count.limit": 500
  }
}'
```

> ⚠️ luckyur-log 不下 `cluster.routing.allocation.total_shards_per_node`：
> 当前每节点已 ~914 分片，设 200 会卡住 ILM 创建新索引。

---

## 3. 参数清单与作用

| 参数 | 默认值 | 建议值 | 作用 |
|---|---|---|---|
| `indices.breaker.total.limit` | 95% | **70%** | 总熔断器；超过堆 70% 直接拒新请求 |
| `indices.breaker.request.limit` | 60% | **50%** | 单请求最多用 50% 堆 |
| `indices.breaker.fielddata.limit` | 40% | **25%** | text 字段聚合/排序的内存上限 |
| `indices.fielddata.cache.size` | 不限 | **15%** | **关键** — 默认无上限是 JVM 长期高位主因 |
| `search.max_buckets` | 65536 | **10000** | 聚合桶上限，挡掉超大 aggregation |
| `action.search.shard_count.limit` | 1000 | **500** | 单查询最多扫的分片数 |
| `cluster.routing.allocation.total_shards_per_node` | 1000 | **200** | 单节点分片硬上限（仅 luckylfe-log） |

---

## 4. 影响评估

### 4.1 正面影响（预期收益）

| 维度 | 改善 | 时间 |
|---|---|---|
| JVM 内存压力峰值 | 预计回落 5-10 个百分点 | 30-60 分钟内 |
| OOM 风险 | 显著降低（堆 70% 即熔断，不会再到 100%） | 立即 |
| 长期 fielddata 内存占用 | 缓存上限收紧后逐步释放 | 1-2 小时 |
| 单节点分片失衡（仅 luckylfe-log） | 阻止再次集中堆积到一个节点 | 立即 |

### 4.2 负面影响（需提前知会业务方）

| 影响项 | 表现 | 处理方式 |
|---|---|---|
| **超大聚合查询失败** | HTTP 400 / `too_many_buckets_exception` | 业务方限制聚合 bucket 数（通常 <10000 已够日志类场景） |
| **超复杂查询失败** | HTTP 503 / `circuit_breaking_exception: [request] Data too large` | 业务方简化查询、分批拉取 |
| **跨大量分片查询失败** | HTTP 400 / `Trying to query [N] shards, exceeds limit of 500` | 加时间过滤条件（限制扫的索引/分片范围） |
| **新建索引失败（仅 luckylfe-log）** | 单节点已 200 分片时，新分片无法分配 | 短期内不太会触发；扩容前如有新业务接入需注意 |

### 4.3 业务影响等级评估

| 集群 | 预估影响 | 受影响业务 | 应对 |
|---|---|---|---|
| luckylfe-log | **低** | LFE 平台日志查询、Kibana | Kibana 大跨度查询可能 503，加时间过滤后可恢复 |
| luckyur-log | **极低** | 用户日志查询 | 仅极少数全索引扫描场景受影响 |

**建议执行时机**：业务低峰期（建议 UTC 18:00 后 / 北京时间凌晨）。

**通知模板**（执行前发 Slack）：

> 各位早，今日 [HH:MM UTC] DBA 将对 luckylfe-log / luckyur-log OpenSearch 集群下发**保护性参数**，避免堆内存被超大查询打满。
> 影响：极少数包含超大聚合 / 跨海量分片的查询会被拒（HTTP 400 / 503），可通过缩小时间窗或限制 bucket 数恢复。
> 数据写入与正常查询不受影响。
> 如果发现服务异常，请立刻 @David。回滚一句话即可。

---

## 5. 验证步骤

### Step 1 — 确认参数已生效（执行后立即）

```bash
curl "$ENDPOINT/_cluster/settings?pretty" | jq '.persistent'
```

**预期输出**：包含上述 7 项 persistent 参数。

### Step 2 — 观察 JVM 回落（30 分钟后）

```bash
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name JVMMemoryPressure \
  --dimensions Name=DomainName,Value=luckylfe-log Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '30 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Maximum \
  --region us-east-1 --output table
```

**预期**：30 分钟内峰值从 75% 降至 65-70%。

### Step 3 — 检查未分配分片（仅 luckylfe-log，1 小时后）

```bash
curl "$ENDPOINT/_cluster/health?pretty"
```

**预期**：`unassigned_shards` 从 26 降至 0，`status` 从 yellow 转 green。

### Step 4 — 抽查 5xx 错误率

```bash
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name 5xx \
  --dimensions Name=DomainName,Value=luckylfe-log Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '30 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Sum --region us-east-1 --output table
```

**预期**：5xx 错误数与下发前相当或略增（增量主要来自被熔断的预期失败）；如急剧上升 → 立即回滚。

---

## 6. 回滚方案

### 触发条件

- 业务方反馈核心查询大量失败（>5% 请求被拒）
- 5xx 错误率较下发前增长超过 10 倍
- 集群状态出现非预期波动

### 回滚命令（一句话）

```bash
curl -XPUT "$ENDPOINT/_cluster/settings" \
  -H 'Content-Type: application/json' \
  -d '{
  "persistent": {
    "indices.breaker.total.limit": null,
    "indices.breaker.request.limit": null,
    "indices.breaker.fielddata.limit": null,
    "indices.fielddata.cache.size": null,
    "search.max_buckets": null,
    "action.search.shard_count.limit": null,
    "cluster.routing.allocation.total_shards_per_node": null
  }
}'
```

> 全部置 `null` 即恢复 ES 默认值，立即生效，无需重启。

---

## 7. 后续动作

参数下发只是**临时止损**，根本性治理见完整故障报告：
👉 `/app/reports/es-cluster-incident-2026-04-29.md`

主要后续：
1. luckylfe-log 实例升级 m5.large → m5.xlarge（1 周内）
2. luckyur-log 索引合并日 → 周（2 周内）
3. Grafana 告警规则增加"持续时间"条件（本周）

---

## 8. 一键执行脚本

```bash
#!/bin/bash
# /app/runbooks/es-emergency-throttle.sh
set -euo pipefail

apply_lfe() {
  local ENDPOINT='https://vpc-luckylfe-log-eh3n6nwo4c43eofoz36j35kni4.us-east-1.es.amazonaws.com'
  echo "[$(date -u +%FT%TZ)] 下发 luckylfe-log 减压参数..."
  curl -sS -XPUT "$ENDPOINT/_cluster/settings" -H 'Content-Type: application/json' -d '{
    "persistent": {
      "indices.breaker.total.limit": "70%",
      "indices.breaker.request.limit": "50%",
      "indices.breaker.fielddata.limit": "25%",
      "indices.fielddata.cache.size": "15%",
      "search.max_buckets": 10000,
      "action.search.shard_count.limit": 500,
      "cluster.routing.allocation.total_shards_per_node": 200
    }}' | jq .
  echo "[$(date -u +%FT%TZ)] 触发未分配分片重试..."
  curl -sS -XPOST "$ENDPOINT/_cluster/reroute?retry_failed=true" | jq '.acknowledged'
}

apply_ur() {
  local ENDPOINT="$LUCKYUR_LOG_ENDPOINT"   # 业务方提供完整 endpoint
  echo "[$(date -u +%FT%TZ)] 下发 luckyur-log 减压参数..."
  curl -sS -XPUT "$ENDPOINT/_cluster/settings" -H 'Content-Type: application/json' -d '{
    "persistent": {
      "indices.breaker.total.limit": "70%",
      "indices.breaker.fielddata.limit": "25%",
      "indices.fielddata.cache.size": "15%",
      "search.max_buckets": 10000,
      "action.search.shard_count.limit": 500
    }}' | jq .
}

rollback() {
  local ENDPOINT="$1"
  curl -sS -XPUT "$ENDPOINT/_cluster/settings" -H 'Content-Type: application/json' -d '{
    "persistent": {
      "indices.breaker.total.limit": null,
      "indices.breaker.request.limit": null,
      "indices.breaker.fielddata.limit": null,
      "indices.fielddata.cache.size": null,
      "search.max_buckets": null,
      "action.search.shard_count.limit": null,
      "cluster.routing.allocation.total_shards_per_node": null
    }}' | jq .
}

case "${1:-help}" in
  apply-lfe) apply_lfe ;;
  apply-ur)  apply_ur ;;
  rollback-lfe) rollback 'https://vpc-luckylfe-log-eh3n6nwo4c43eofoz36j35kni4.us-east-1.es.amazonaws.com' ;;
  rollback-ur)  rollback "$LUCKYUR_LOG_ENDPOINT" ;;
  *) echo "Usage: $0 {apply-lfe|apply-ur|rollback-lfe|rollback-ur}"; exit 2 ;;
esac
```

---

*执行清单：1) 通知业务方 → 2) 执行 apply-lfe → 3) 30 分钟观察 → 4) 执行 apply-ur → 5) 收尾验证*
