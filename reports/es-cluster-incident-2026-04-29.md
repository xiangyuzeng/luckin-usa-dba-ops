# OpenSearch 集群告警故障报告

**日期**: 2026-04-29
**涉及集群**: `luckylfe-log`（RED 报警）、`luckyur-log`（两次 Yellow）
**作者**: David Zeng / DBA Infrastructure
**严重级别**: P1（luckylfe-log 持续 Yellow + 26 分片未分配，存在再次升级 RED 风险）

---

## 1. 执行摘要

| 集群 | 当前状态 | 最近 24h 主要异常 | 优先级 |
|---|---|---|---|
| `luckylfe-log` | **持续 Yellow** | 26 个分片长期未分配，单节点 EBS 余量 ~9.4 GB（< 25 GB 安全线），JVM 稳态 75% | **P1** |
| `luckyur-log` | Green（短暂 Yellow） | 15:27 出现一次 Yellow（8 分片，几分钟自愈，ILM 删除典型特征），JVM 稳态 75%，CPU 峰 73% | P3 |

**核心结论**：
1. luckylfe-log 是结构性容量不足问题：分片密度高 + 堆内存吃紧 + 磁盘临近警戒线，需要"先减压、再扩容"两步走。
2. luckyur-log 短暂 Yellow 属于 ILM 正常行为（非故障），但 **3,656 个主分片 / 4 节点**（每节点 ~914 分片）已远超推荐上限，是 JVM 持续高位的根因。
3. 两个集群共性：**ES 7.10（已 EOL）**、**AutoTune 关闭**、**EBS gp2**、**告警阈值未做防误报处理**。

---

## 2. 集群现状

### 2.1 luckylfe-log

| 项目 | 值 |
|---|---|
| Domain | `luckylfe-log` |
| Endpoint | `vpc-luckylfe-log-eh3n6nwo4c43eofoz36j35kni4.us-east-1.es.amazonaws.com` |
| 引擎 | Elasticsearch 7.10 |
| 数据节点 | 4 × `m5.large.search`（2 vCPU / 8 GiB RAM ≈ 4 GB JVM heap） |
| 专用 Master | 3 × `t3.medium.search` |
| EBS | 80 GB **gp2** / 节点（总 320 GB） |
| Zone Awareness | 2 AZ（us-east-1a / 1b） |
| AutoTune | **DISABLED** |
| UltraWarm / Cold | 未启用 |

**最近 24h 关键指标**：

| 指标 | 当前值 | 评估 |
|---|---|---|
| ClusterStatus | Yellow（持续） | ⚠️ |
| Nodes | 7/7 | ✅ |
| Shards.activePrimary | 578 | 数据自然增长 |
| Shards.unassigned | **26**（持续不变） | 🔥 需手动恢复 |
| JVMMemoryPressure（最大） | 74-76% 稳态 | ⚠️ 接近阈值 |
| CPUUtilization（峰） | 60-63% | 中等 |
| FreeStorageSpace（最低节点） | **~9.4 GB** | 🔥 临近警戒线 |

### 2.2 luckyur-log

| 项目 | 值 |
|---|---|
| Domain | `luckyur-log` |
| 引擎 | Elasticsearch 7.10 |
| 数据节点 | 4 × `m5.xlarge.search`（4 vCPU / 16 GiB RAM ≈ 8 GB JVM heap） |
| 专用 Master | 3 × `t3.medium.search` |
| EBS | 500 GB **gp2** / 节点（总 2,000 GB） |
| AutoTune | DISABLED |

**最近 24h 关键指标**：

| 指标 | 当前值 | 评估 |
|---|---|---|
| ClusterStatus | Green（24h 内 1 次 Yellow ~5min） | ✅ |
| Nodes | 7/7 | ✅ |
| Shards.activePrimary | **3,656** | ⚠️ 分片膨胀 |
| Shards.unassigned（峰） | 8（已自愈） | ILM 正常表现 |
| JVMMemoryPressure（最大） | 74-76% 稳态 | ⚠️ 高位 |
| CPUUtilization（峰） | **73%** | ⚠️ |
| FreeStorageSpace（最低节点） | ~155 GB | ✅ |

---

## 3. 根因分析

### 3.1 luckylfe-log — 容量结构性不足

| 维度 | 现状 | 根因 |
|---|---|---|
| **JVM heap** | 4 GB / 节点 | m5.large 内存仅 8 GiB，JVM heap 受 32GB rule 同时被节点其他进程瓜分 |
| **分片密度** | 151 / 节点（≈600 分片 / 4 节点） | 推荐每 4GB heap 上限 100 分片，目前超 1.5 倍 |
| **field data** | 默认无上限 | text 字段排序/聚合无封顶，搜索峰值时直接吃满堆 |
| **EBS 余量** | 9.4 GB / 节点 | 距 AWS 推荐 25 GB 安全线尚有约 15 GB 缓冲，但每天净消耗 0.5-1 GB |
| **分片重平衡** | 26 个未分配 | 长期未自动恢复，可能被 retry_failed 阻塞或副本目标 AZ 容量不足 |

**故障传导链**：高分片密度 → JVM 长期 70-75% → 任何搜索峰值（例如下午高频查询）都可能瞬间冲到 100% → field data 无封顶 → 内存压力锁死 → 分片重平衡失败 → Yellow 长期未恢复。

### 3.2 luckyur-log — 分片爆炸

| 维度 | 现状 | 评估 |
|---|---|---|
| 主分片数 | 3,656 | 平均每节点 914 分片，远超 8GB heap 推荐上限（~200） |
| 索引切分粒度 | 多按小时/天切 | 日志类索引典型问题，长期累积导致小分片膨胀 |
| 删除时机 | ILM 凌晨批量执行 | 单次删除大量分片 → 重平衡 → 短暂 Yellow |
| JVM 稳态 | 75% | field data 无封顶 + 分片描述符占用过大 |

**故障传导链**：分片切粒度过细 → 每分片 segment 元数据占堆 → JVM 长期高位 → ILM 删除瞬间未分配分片暴增 → Yellow（5-10 分钟自愈，业务无影响）。

---

## 4. 分级解决方案

### 4.1 即时减压（今天执行，零中断，可回滚）

**目标**：通过下发集群级动态参数，给堆内存装"保险丝"，避免再次触发级联崩溃。

#### luckylfe-log

```bash
ENDPOINT='https://vpc-luckylfe-log-eh3n6nwo4c43eofoz36j35kni4.us-east-1.es.amazonaws.com'

curl -XPUT "$ENDPOINT/_cluster/settings" -H 'Content-Type: application/json' -d '{
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

# 处理未分配分片
curl -XPOST "$ENDPOINT/_cluster/reroute?retry_failed=true"
curl  "$ENDPOINT/_cluster/allocation/explain?pretty"   # 排查根因
```

#### luckyur-log（不下 `total_shards_per_node`）

```bash
ENDPOINT='https://vpc-luckyur-log-<id>.us-east-1.es.amazonaws.com'

curl -XPUT "$ENDPOINT/_cluster/settings" -H 'Content-Type: application/json' -d '{
  "persistent": {
    "indices.breaker.total.limit": "70%",
    "indices.breaker.fielddata.limit": "25%",
    "indices.fielddata.cache.size": "15%",
    "search.max_buckets": 10000,
    "action.search.shard_count.limit": 500
  }
}'
```

参数说明见快速方案文档（`es-cluster-quick-fix-2026-04-29.md`）。

### 4.2 短期治理（1-2 周）

#### luckylfe-log
| 任务 | 目标 | 影响 |
|---|---|---|
| 实例升级 m5.large → m5.xlarge | JVM heap 4 → 8 GB，分片密度降一半 | 蓝绿部署，零中断，约 30-60 min |
| EBS 80 GB gp2 → 200 GB **gp3** | 容量翻倍，IOPS 从基础提升到 3000 | 滚动更新，零中断 |
| 启用 AutoTune | 自动调优 JVM 参数 | 蓝绿部署，零中断 |
| 旧索引副本数降为 0（保留期内但非关键） | 立即降低 ~40% 分片数 | 降副本期间可用性下降 |

#### luckyur-log
| 任务 | 目标 | 影响 |
|---|---|---|
| 索引合并：日级 → 周级 rollover | 分片数 3,656 → 估算 ~600 | 用 `reindex` API 在线合并 |
| 启用 UltraWarm | >7 天日志移至冷层（$0.024/GB·月，比热存储省 ~75%） | 查询冷数据延迟略升 |
| EBS gp2 → gp3 | 同等容量月省约 20% | 滚动更新 |

### 4.3 长期规划（1-3 月）

| 任务 | 范围 | 备注 |
|---|---|---|
| **OpenSearch 2.x 升级** | 双集群 | ES 7.10 已 EOL；OpenSearch 2.x 引入 Search Backpressure，可自动取消高消耗查询 |
| 启用 Fine-grained Access Control | 双集群 | 接入 Cognito / IAM，替换基础认证 |
| 引入 Ingest Pipeline | 写入侧 | 在写入端做字段裁剪，减少 field data 内存占用 |
| 跨 3 AZ 部署 | luckylfe-log | 当前 2 AZ，单 AZ 故障时副本无处可放 |

---

## 5. Grafana 监控与告警建议

### 5.1 现有看板审查

| 看板 | 状态 | 改进建议 |
|---|---|---|
| `AWS OpenSearch 集群存储监控` (UID: `opensearch-storage-monitor`) | 仅覆盖存储/CPU/RED 状态 | 补齐 JVM、节点数、分片数、写入/查询速率、慢查询面板 |

### 5.2 推荐扩展看板（覆盖 7 类指标）

| 行 | 面板 | CloudWatch 指标 | 阈值/可视化 |
|---|---|---|---|
| 1 | 集群健康状态时序 | `ClusterStatus.green/yellow/red` | 红/黄/绿色块时间线 |
| 1 | 节点数 | `Nodes` (Min) | 期望 7，低于即红色 |
| 1 | 未分配分片 | `Shards.unassigned` | >0 黄色，>10 红色 |
| 2 | JVM 内存压力 | `JVMMemoryPressure` (Max) | 75% 警告线、85% 严重线 |
| 2 | CPU | `CPUUtilization` | 70% 警告 |
| 2 | 单节点剩余磁盘 | `FreeStorageSpace` (Min) | 25 GB 警告、15 GB 严重 |
| 3 | 写入速率 | `IndexingRate` 或 `IndexingLatency` | 趋势观察 |
| 3 | 查询速率 | `SearchRate` | 突增标记 |
| 3 | 慢查询 | Logs Insights：`/aws/aes/domains/<name>/search-slow-logs` | 表格 |
| 4 | 5xx 错误 | `5xx` (Sum) | >0 即红 |
| 4 | Master 可达性 | `MasterReachableFromNode` | 0 即 P1 |
| 4 | Kibana 健康 | `KibanaHealthyNodes` | <1 即红 |

### 5.3 告警规则配置

| 规则名 | 表达式 / 条件 | For | 严重 | 通道 |
|---|---|---|---|---|
| ES_ClusterRed | `max_over_time(es_cluster_status_red[5m]) > 0` | 1m | **P1 Page** | Slack #dba-oncall + 短信 |
| ES_ClusterYellow_Sustained | `min_over_time(es_cluster_status_yellow[10m]) == 1` | 10m | P3 | Slack |
| ES_NodeLoss | `min_over_time(es_nodes[5m]) < 7` | 1m | **P1 Page** | Slack + 短信 |
| ES_JVMHigh | `max_over_time(es_jvm_pressure[10m]) > 80` | 10m | P2 | Slack |
| ES_JVMCritical | `max_over_time(es_jvm_pressure[5m]) > 92` | 5m | P1 | Slack + 短信 |
| ES_DiskLow | `min_over_time(es_free_storage_gb[15m]) < 25` | 15m | P2 | Slack |
| ES_DiskCritical | `min_over_time(es_free_storage_gb[5m]) < 15` | 5m | P1 | Slack + 短信 |
| ES_5xxErrors | `sum(rate(es_5xx[5m])) > 0` | 5m | P3 | Slack |
| ES_UnassignedShards_Sustained | `min_over_time(es_shards_unassigned[15m]) > 0` | 15m | P2 | Slack |

**关键改动**：
- `ClusterStatus.yellow` 加 **10 分钟持续条件**，过滤 ILM 凌晨删除的瞬时抖动（这是 luckyur-log 误报的主要源头）
- `JVMMemoryPressure` 分两档（80% 警告、92% 严重），让稳态高位也能被发现
- `Shards.unassigned > 0 持续 15 分钟` 单独告警，捕捉 luckylfe-log 这类 26 分片长期未分配的隐患

### 5.4 通知路由（Alertmanager / Grafana Contact Points）

```yaml
routes:
  - match: { severity: P1 }
    receiver: dba-oncall-pager   # 短信 + Slack #dba-oncall
    continue: true
  - match: { severity: P2 }
    receiver: dba-slack          # Slack #dba-alerts
  - match: { severity: P3 }
    receiver: dba-slack-low      # Slack #dba-alerts-low (静音工单流)
```

---

## 6. 验证与回滚

### 6.1 即时减压参数生效验证（5-15 分钟内）

```bash
# 1. 确认集群参数已下发
curl "$ENDPOINT/_cluster/settings?include_defaults=false&pretty"

# 2. 观察 JVM 是否回落
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name JVMMemoryPressure \
  --dimensions Name=DomainName,Value=luckylfe-log Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '30 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Maximum --region us-east-1 --output table

# 3. 检查未分配分片
curl "$ENDPOINT/_cluster/health?pretty" | grep unassigned
```

**预期效果**：JVM 峰值在 30-60 分钟内回落 5-10 个百分点；fielddata 缓存大小有限制后会逐步释放。

### 6.2 回滚方案

如果业务方反映搜索接口大量 429 / circuit_breaking_exception：

```bash
curl -XPUT "$ENDPOINT/_cluster/settings" -H 'Content-Type: application/json' -d '{
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

**全部参数置 null 即恢复默认值，立即生效**。

---

## 7. 行动清单

| # | 任务 | 责任 | 截止 | 状态 |
|---|---|---|---|---|
| 1 | 下发 luckylfe-log 集群级减压参数 | DBA | 今日 | 待执行 |
| 2 | luckylfe-log 26 个未分配分片排查与恢复 | DBA | 今日 | 待执行 |
| 3 | 下发 luckyur-log 集群级减压参数 | DBA | 今日 | 待执行 |
| 4 | Grafana 告警规则增加"持续 10 分钟"条件 | DBA | 本周 | 待执行 |
| 5 | luckylfe-log 实例升级 m5.large → m5.xlarge | DBA + Michael | 1 周内 | 待评估 |
| 6 | luckylfe-log EBS 扩容 80 GB → 200 GB（gp3） | DBA | 1 周内 | 待评估 |
| 7 | luckyur-log 索引合并方案制定（日 → 周 rollover） | DBA | 2 周内 | 待评估 |
| 8 | luckyur-log 启用 UltraWarm | DBA + Michael | 2 周内 | 待评估 |
| 9 | OpenSearch 2.x 升级评估 | DBA + Michael | 1 月内 | 待评估 |

---

## 8. 附录

- 即时减压执行手册：`/app/reports/es-cluster-quick-fix-2026-04-29.md`
- 既有 Grafana 看板：`/app/claude-code-output/grafana-opensearch-monitoring.json`
- 历史 luckylfe-log RED 事件：`/app/reports/es-cluster-yellow-luckylfe-log-2026-02-12.md`
- 历史 luckyur-log Yellow（ILM）：`/app/reports/es-cluster-yellow-luckyur-log-20260315.md`
- 历史 luckyur-log 存储扩容：`/app/reports/opensearch-luckyur-log-storage-expansion-2026-03-11.md`

---

*报告生成时间：2026-04-29*
