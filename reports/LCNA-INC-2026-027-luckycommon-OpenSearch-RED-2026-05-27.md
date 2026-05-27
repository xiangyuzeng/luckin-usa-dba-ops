# LCNA-INC-2026-027 luckycommon OpenSearch RED 故障处置手册

> **事件编号**: LCNA-INC-2026-027
> **集群**: luckycommon (AWS OpenSearch / Elasticsearch 6.8)
> **账号**: 257394478466 (us-east-1)
> **VPC Endpoint**: `vpc-luckycommon-6td25pij3j45l572katgsdp2ty.us-east-1.es.amazonaws.com`
> **告警时间**: 2026-05-27 09:07 UTC
> **RED 持续**: 2026-05-27 09:03 → 12:42 UTC (**3h39m**)
> **当前状态**: GREEN（已自愈，但根因未解决）
> **关联事件**: LCNA-INC-2026-008 (3/8), 2026-04-20, LCNA-INC-2026-026 (5/17)
> **处置负责人**: 曾翔宇 (David Zeng)
> **生成时间**: 2026-05-27 13:00 UTC

---

## 0. TL;DR — 必读

1. **集群已自愈到 GREEN**（12:42 UTC），但**这是 3 个月内第 3 次 RED**，根因完全相同：**5 个 `replicas=0` 索引**任何节点抖动都会直接 RED。
2. 5/18 已经写好的整改手册 `/app/runbooks/luckycommon-opensearch-remediation/RUNBOOK.md` **9 天来一项都没执行**，今天就再次应验。
3. **今晚 UTC 02:00–05:00 必须完成 3 项 P0 整改**，否则未来 1–2 周内必然再 RED 一次：
   - P0-A: 给所有 `replicas=0` 索引加副本
   - P0-B: 修 index template 防止明天的日索引继续以 0 副本创建
   - P0-C: 前置磁盘 watermark（今天 09:18–09:42 磁盘被灌到 0 MB 加剧了故障，**这是 5/17 没有出现的新风险点**）
4. 如果本次 RED 复发，按 §3 决策树立即处置，目标 30 分钟内恢复。

---

## 一、故障概览

### 1.1 时间线

| UTC 时间 | 事件 | 数据 |
|---|---|---|
| 09:03 | 数据节点脱离集群 | Nodes 7→6, 24 shards 进入 Unassigned |
| 09:06 | 剩余节点开始分片重平衡 | I/O 飙升 |
| 09:07 | **告警发出** | `[FIRING][P0] 集群状态Red_语音` |
| 09:18 | **最小节点 FreeStorage 跌至 0 MB** | 磁盘写满，写入冻结 |
| 09:21 | 脱离节点重新加入 | Nodes 6→7 |
| 09:42 | 最小节点磁盘空间恢复 | FreeStorage 回到 ~27 GB |
| 09:54 | 19 个分片完成再分配 | Unassigned 24→5 |
| 10:00–12:31 | **5 个 primary 卡死无法分配** | RED 持续 |
| 12:31 | 自动重试逐步推进 | Unassigned 5→1 |
| 12:42 | **集群转 GREEN** | ActivePrimary 50→47（净失 12 个主分片，对应被删除的索引） |
| 12:48 | 完全稳定 | Unassigned=0, RED=0 |

### 1.2 三次 RED 事件对照

| 日期 | 编号 | 偶发触发器 | 共同根因 | 持续 |
|---|---|---|---|---|
| 2026-03-08 | LCNA-INC-2026-008 | ISM 一次性删 41GB → merge I/O 把节点压掉线 | **5 个 `replicas=0` 索引** | 7 min |
| 2026-05-17 | LCNA-INC-2026-026 | 节点 JVM STW pause → 短暂不可达 | **5 个 `replicas=0` 索引** | 14 min |
| **2026-05-27** | **LCNA-INC-2026-027 (本次)** | 节点脱离 + 重平衡 I/O 把单节点磁盘灌到 **0 MB** | **5 个 `replicas=0` 索引 + 磁盘 watermark 过松** | **3h39m** |

> **本次故障 vs 5/17 的关键差异**：今天叠加了"磁盘写满"这个新加剧因素。flood_stage 默认 95%，但 EBS 单卷 125 GB 的情况下，重平衡瞬间可以把单节点从 27 GB 灌到 0 — 这意味着 watermark 必须前置。

### 1.3 涉及索引（5/17 已精确定位）

5 个 `number_of_replicas=0` 生产索引（占总数 19 的 26%）：

| 索引名 | 类型 | 风险 |
|---|---|---|
| `chronus_task_sharding_log` | 应用任务调度日志 | 单实例无冗余 |
| `es_task_2026-05-2X` (日索引 4 个) | es_task 系列 | 每天新增 1 个 0 副本索引 |

---

## 二、当前实时状态（2026-05-27 12:48 UTC）

```
ClusterStatus.red      = 0       ✓ GREEN
Shards.unassigned      = 0       ✓
Shards.activePrimary   = 47      ⚠️ 比 09:00 时 59 少 12（已删除部分索引解锁卡死分片）
FreeStorageSpace (min) = ~26 GB  ✓ 已恢复
Nodes                  = 7       ✓
JVM / CPU              = 健康（46-56% / 14-56%）
```

> **重要**：activePrimary 从 50 → 47 的下降，结合 unassigned 同时清零，强烈提示**最后那个卡死的 primary 是被删索引解锁的**（运维操作 or ISM 清理）。需要在 §3.5 中向业务方确认这 3 个索引的数据是否需要从上游重放。

---

## 三、第一阶段：故障恢复（已完成 / 复发应急）

### 3.1 复发判定

任何时候出现以下任一情况，立即按本节执行：
- 收到 `[FIRING][P0] 【DB告警】AWS-ES 集群状态Red_语音` 告警
- CloudWatch `ClusterStatus.red = 1` 持续 > 2 分钟
- `_cluster/health` 返回 `status: red`

### 3.2 前置：建立 REST API 访问通道（30 秒）

```bash
# 在 VPC 内跳板机或 VPC-attached Lambda 上执行
export ENDPOINT=$(aws opensearch describe-domain --domain-name luckycommon \
  --region us-east-1 --query 'DomainStatus.Endpoints.vpc' --output text)

# 测试连通性
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cluster/health?pretty"
```

> Access policy 当前为 `Principal: *, Action: es:*`（VPC 网络层隔离），无需追加 IAM 授权，**仅需在 VPC 内**。

### 3.3 定位卡死分片

```bash
# 1) 全局视角：看哪些分片未分配 + 原因码
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason,unassigned.details" \
  | grep -v STARTED

# 2) 逐个分片诊断（替换 <INDEX> 和 <SHARD>）
awscurl --service es --region us-east-1 \
  -X POST -H "Content-Type: application/json" \
  -d '{"index":"<INDEX>","shard":<SHARD>,"primary":true}' \
  "https://${ENDPOINT}/_cluster/allocation/explain?pretty"
```

重点看返回的：
- `unassigned_info.reason` — 失败原因
- `unassigned_info.failed_allocation_attempts` — 是否到上限
- `node_allocation_decisions[].store.in_sync` — 数据是否完整
- `node_allocation_decisions[].store.allocation_id` — 用于 stale primary 恢复

### 3.4 三场景决策树

```
allocation/explain 的 unassigned_info.reason 是什么？
│
├─ ALLOCATION_FAILED + decisions 显示 max_retries exceeded
│  → 场景 A（90% 情况）：重试即可，零数据丢失
│
├─ NODE_LEFT 或 EXISTING_INDEX_RESTORED + 至少 1 节点有 in_sync=true store
│  → 场景 A：重试即可
│
├─ 所有节点 store 都是 stale (in_sync=false)，但都有 store
│  → 场景 B：强制接受 stale primary，可能少量数据丢失
│
└─ 所有节点都返回 store=null（数据完全丢失）
   → 场景 C：empty primary（整索引清空，需业务方批准）
```

---

#### 场景 A — 自动重试（首选）

```bash
# 全局重试所有失败分片
awscurl --service es --region us-east-1 \
  -X POST "https://${ENDPOINT}/_cluster/reroute?retry_failed=true&pretty"

# 同时把 max_retries 兜底拉高，防止再次卡死（针对涉及索引）
awscurl --service es --region us-east-1 -X PUT -H "Content-Type: application/json" \
  -d '{"index.allocation.max_retries":10}' \
  "https://${ENDPOINT}/<INDEX>/_settings"

# 等待 5 分钟，重新检查健康
sleep 300
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cluster/health?pretty"
```

**成功标准**：`status: green`, `unassigned_shards: 0`

#### 场景 B — Stale Primary（场景 A 失败时）

```bash
# 替换 <INDEX>/<SHARD>/<NODE_NAME>
# NODE_NAME 来自 allocation/explain 输出里 in_sync=false 但 store 不为 null 的节点
awscurl --service es --region us-east-1 -X POST -H "Content-Type: application/json" \
  -d '{
    "commands":[
      {
        "allocate_stale_primary":{
          "index":"<INDEX>",
          "shard":<SHARD>,
          "node":"<NODE_NAME>",
          "accept_data_loss":true
        }
      }
    ]
  }' \
  "https://${ENDPOINT}/_cluster/reroute?pretty"
```

> ⚠️ **`accept_data_loss=true` 意味着**该分片在磁盘满期间未刷盘的数据将丢失。
> - 对 `es_task_*` 日索引：通常业务可接受（任务流水有上游 MQ 重放能力）
> - 对 `chronus_task_sharding_log`：**先联系业务方**确认能否接受，必要时从上游消息队列重放

#### 场景 C — Empty Primary（最后手段）

```bash
# 整个索引被清空，需要业务方明确批准
awscurl --service es --region us-east-1 -X POST -H "Content-Type: application/json" \
  -d '{
    "commands":[
      {
        "allocate_empty_primary":{
          "index":"<INDEX>",
          "shard":<SHARD>,
          "node":"<NODE_NAME>",
          "accept_data_loss":true
        }
      }
    ]
  }' \
  "https://${ENDPOINT}/_cluster/reroute?pretty"
```

> 仅当业务方书面确认可清空该索引数据时使用。后续需从上游全量回填。

### 3.5 恢复后必做：数据完整性核查

```bash
# 1) 列出 RED 期间所有发生 unassigned 的索引
# 在 09:18–09:42 UTC 磁盘归零期间，相关索引写入可能中断

# 2) 业务方核实清单
echo "请业务方（语音/common 服务）核实以下索引在 09:18–09:42 UTC 期间的数据完整性："
echo "  - chronus_task_sharding_log"
echo "  - es_task_2026-05-27（当日索引）"
echo "  - 其他在 _cat/shards 中显示曾失败的索引"

# 3) 如发现数据丢失，从上游 Kafka/MQ 重放该时段消息
```

---

## 四、第二阶段：本日 P0 防复发（必做，UTC 02:00–05:00 窗口）

**这一节是本份手册的核心。不做这 3 项，下次 RED 一定会再来。**

### 4.1 P0-A：给所有 `replicas=0` 索引加副本

#### 步骤 1：审计现状

```bash
export ENDPOINT=$(aws opensearch describe-domain --domain-name luckycommon \
  --region us-east-1 --query 'DomainStatus.Endpoints.vpc' --output text)

# 列出所有 replicas=0 的索引
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cat/indices?h=index,pri,rep,docs.count,store.size&v" \
  | awk 'NR==1 || $3==0' \
  | tee /tmp/zero-replica-indices-$(date +%Y%m%d).txt

# 估算新增存储需求
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cat/indices?h=index,rep,store.size&bytes=b" \
  | awk '$2==0 {sum+=$3} END {printf "需新增副本存储: %.1f GB\n", sum/1024/1024/1024}'
```

**通过标准**：新增存储 < 100 GB（当前 EBS 总 500 GB / 4 节点，单节点 125 GB，需保留 30% 余量）

#### 步骤 2：逐个加副本（避免 I/O 峰值）

```bash
# 先处理 chronus_task_sharding_log（单一索引，shard 数较多，先观察）
awscurl --service es --region us-east-1 \
  -X PUT -H "Content-Type: application/json" \
  -d '{"index": {"number_of_replicas": 1}}' \
  "https://${ENDPOINT}/chronus_task_sharding_log/_settings"

# 等待该索引复制完成（每 30s 检查一次，最多 30 分钟）
for i in $(seq 1 60); do
  H=$(awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cluster/health")
  UNASSIGNED=$(echo "$H" | python3 -c "import sys,json; print(json.load(sys.stdin)['unassigned_shards'])")
  STATUS=$(echo "$H" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "$(date -u +%H:%M:%S) status=$STATUS unassigned=$UNASSIGNED"
  [ "$UNASSIGNED" = "0" ] && [ "$STATUS" = "green" ] && echo "✓ chronus 复制完成" && break
  sleep 30
done

# 批量处理 es_task 日索引（含明天的 5/28）
for IDX in $(awk 'NR>1 {print $1}' /tmp/zero-replica-indices-$(date +%Y%m%d).txt | grep -E '^es_task_'); do
  echo "Setting replicas=1 on $IDX"
  awscurl --service es --region us-east-1 \
    -X PUT -H "Content-Type: application/json" \
    -d '{"index": {"number_of_replicas": 1}}' \
    "https://${ENDPOINT}/${IDX}/_settings"
  sleep 5
done

# 等待全部复制完成
for i in $(seq 1 120); do
  H=$(awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cluster/health")
  echo "$(date -u +%H:%M:%S) $H" | python3 -c "
import sys,json
line=sys.stdin.read().split(' ',1)
t,d=line[0],json.loads(line[1])
print(f\"{t} status={d['status']} init={d['initializing_shards']} reloc={d['relocating_shards']} unassigned={d['unassigned_shards']} active%={d['active_shards_percent_as_number']}\")
"
  echo "$H" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d['status']=='green' and d['unassigned_shards']==0 else 1)" && break
  sleep 30
done
```

#### 步骤 3：观察指标（变更期间另开终端）

```bash
# CloudWatch 关键指标实时打印
watch -n 60 'aws cloudwatch get-metric-data --region us-east-1 \
  --metric-data-queries "[
    {\"Id\":\"jvm\",\"MetricStat\":{\"Metric\":{\"Namespace\":\"AWS/ES\",\"MetricName\":\"JVMMemoryPressure\",\"Dimensions\":[{\"Name\":\"DomainName\",\"Value\":\"luckycommon\"},{\"Name\":\"ClientId\",\"Value\":\"257394478466\"}]},\"Period\":60,\"Stat\":\"Maximum\"}},
    {\"Id\":\"cpu\",\"MetricStat\":{\"Metric\":{\"Namespace\":\"AWS/ES\",\"MetricName\":\"CPUUtilization\",\"Dimensions\":[{\"Name\":\"DomainName\",\"Value\":\"luckycommon\"},{\"Name\":\"ClientId\",\"Value\":\"257394478466\"}]},\"Period\":60,\"Stat\":\"Maximum\"}}
  ]" \
  --start-time $(date -u -d "5 minutes ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S)'
```

**中止条件**（任一即停止后续变更，回滚）：
- JVM > 85%
- CPU > 80%
- 出现新的 RED 或节点掉线

### 4.2 P0-B：修 index template 防止次日索引继续 0 副本

#### 步骤 1：审计现有 templates

```bash
# 备份所有 templates
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_template?pretty" > /tmp/templates-before-$(date +%Y%m%d).json

# 找出 replicas=0 的 template
python3 <<'EOF'
import json
with open(f'/tmp/templates-before-{__import__("datetime").date.today().strftime("%Y%m%d")}.json') as f:
    data = json.load(f)
for name, tmpl in data.items():
    replicas = tmpl.get('settings', {}).get('index', {}).get('number_of_replicas')
    patterns = tmpl.get('index_patterns', tmpl.get('template'))
    print(f"{name}: patterns={patterns} replicas={replicas} {'❌ NEEDS FIX' if replicas in ('0', 0, None) else '✓'}")
EOF
```

**重点关注 patterns 包含 `es_task*`、`chronus*`、`logs-*` 的 template**。

#### 步骤 2：修复 template

```bash
# 示例：修复名为 "es_task_template" 的 template
# ⚠️ 必须从备份完整复制原 JSON，只改 number_of_replicas，不动 mappings/aliases
TPL_NAME=es_task_template
ORIGINAL=$(python3 -c "
import json
d=json.load(open('/tmp/templates-before-$(date +%Y%m%d).json'))
t=d['$TPL_NAME']
t.setdefault('settings',{}).setdefault('index',{})['number_of_replicas']='1'
print(json.dumps(t))
")

awscurl --service es --region us-east-1 \
  -X PUT -H "Content-Type: application/json" \
  -d "$ORIGINAL" \
  "https://${ENDPOINT}/_template/${TPL_NAME}"
```

#### 步骤 3：验证

```bash
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_template" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
bad = [n for n,t in d.items() if t.get('settings',{}).get('index',{}).get('number_of_replicas') in ('0',0,None)]
print('Templates with replicas=0:', bad if bad else 'NONE ✓')
"
```

> **注意**：template 修改只影响**未来创建**的索引。已有索引在 4.1 节已修复。

### 4.3 P0-C：前置磁盘 Watermark（本次故障新增）

**为什么必加**：今天 09:18–09:42 期间最小节点 FreeStorage 跌至 **0 MB**，flood_stage 默认 95% 触发太晚 —— 在 125 GB EBS 上，从 27 GB 到 0 仅用了 ~12 分钟的重平衡 I/O。前置 watermark 给系统留出缓冲。

```bash
awscurl --service es --region us-east-1 \
  -X PUT -H "Content-Type: application/json" \
  -d '{
    "persistent": {
      "cluster.routing.allocation.disk.watermark.low":         "75%",
      "cluster.routing.allocation.disk.watermark.high":        "80%",
      "cluster.routing.allocation.disk.watermark.flood_stage": "85%",
      "cluster.info.update.interval":                          "30s"
    }
  }' \
  "https://${ENDPOINT}/_cluster/settings?pretty"

# 验证
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cluster/settings?flat_settings=true&pretty" \
  | grep watermark
```

**效果**：
- 任何节点磁盘使用率 > 75%：停止向该节点分配**新**分片
- > 80%：尝试**迁出**该节点已有分片到其他节点
- > 85%：所有索引转为只读（**保护数据完整性**，比写满到 0 MB 强百倍）

**搭配 CloudWatch 告警阈值前置**（同步在 Console 操作）：
- `FreeStorageSpace < 30 GB` → P2 Warning
- `FreeStorageSpace < 15 GB` → P1 Critical
- `FreeStorageSpace < 5 GB` → P0 Critical（当前阈值，太晚）

---

## 五、第三阶段：本周内 P1 跟进（可分批执行）

### 5.1 P1-D：ISM 删除策略小批量化

**问题**：3/8 事件 ISM 一次删 41GB → merge 把节点压掉线。当前 ISM 策略未改。

```bash
# 列出所有 ISM 策略
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_opendistro/_ism/policies?pretty" \
  > /tmp/ism-policies-before.json

# 关键改动（对每个含 delete action 的策略）：
# 1) 添加 rollover (min_size=5gb) 让单索引体量受控
# 2) schedule.interval.start_time 设置到 UTC 02:00（业务低峰）
```

完整 JSON 模板见 `/app/runbooks/luckycommon-opensearch-remediation/RUNBOOK.md` §P0-3。

### 5.2 P1-E：启用 AutoTune

**问题**：JVM 锯齿波（峰值 74-76%），AutoTune 当前 DISABLED。

```bash
aws opensearch update-domain-config \
  --domain-name luckycommon \
  --region us-east-1 \
  --auto-tune-options '{
    "DesiredState": "ENABLED",
    "MaintenanceSchedules": [
      {
        "StartAt": '"$(date -u -d 'next tuesday 05:29' +%s)"'000,
        "Duration": {"Value": 2, "Unit": "HOURS"},
        "CronExpressionForRecurrence": "cron(29 5 ? * TUE *)"
      }
    ]
  }'
```

效果：AWS 在维护窗口（与现有 Tue 05:29 UTC 维护窗对齐）自动调 JVM heap / GC，无业务中断。

### 5.3 P1-F：调高 Merge Throttle

**问题**：删除产生大量待合并 segment，merge 速率限制延长节点高压时间至 25–49 分钟。

```bash
# 先看当前值
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cluster/settings?include_defaults=true&flat_settings=true&pretty" \
  | grep -i throttle

# 如果不是 unlimited，调高
awscurl --service es --region us-east-1 \
  -X PUT -H "Content-Type: application/json" \
  -d '{"persistent":{"indices.store.throttle.max_bytes_per_sec":"100mb","indices.store.throttle.type":"merge"}}' \
  "https://${ENDPOINT}/_cluster/settings"
```

---

## 六、完整验证清单

P0 全部执行后跑一遍，**全部通过**才算整改完成：

```bash
ENDPOINT=$(aws opensearch describe-domain --domain-name luckycommon --region us-east-1 \
  --query 'DomainStatus.Endpoints.vpc' --output text)

echo "========== 1. 集群健康 =========="
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cluster/health?pretty"

echo "========== 2. 0 副本索引数量 =========="
ZERO=$(awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cat/indices?h=rep" | awk '$1==0' | wc -l)
echo "Zero-replica indices: $ZERO (期望: 0)"

echo "========== 3. Templates 副本配置 =========="
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_template" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
bad = [n for n,t in d.items() if t.get('settings',{}).get('index',{}).get('number_of_replicas') in ('0',0,None)]
print('Templates with replicas=0:', bad if bad else 'NONE ✓')"

echo "========== 4. 磁盘 Watermark 配置 =========="
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cluster/settings?flat_settings=true" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
p = d.get('persistent', {})
print('low:', p.get('cluster.routing.allocation.disk.watermark.low'))
print('high:', p.get('cluster.routing.allocation.disk.watermark.high'))
print('flood_stage:', p.get('cluster.routing.allocation.disk.watermark.flood_stage'))"

echo "========== 5. AutoTune 状态 =========="
aws opensearch describe-domain --domain-name luckycommon --region us-east-1 \
  --query 'DomainStatus.AutoTuneOptions.State'

echo "========== 6. 最小 FreeStorage =========="
aws cloudwatch get-metric-statistics --region us-east-1 \
  --namespace AWS/ES --metric-name FreeStorageSpace \
  --dimensions Name=DomainName,Value=luckycommon Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Minimum \
  --query 'Datapoints[*].Minimum' --output text
```

| 检查项 | 期望值 | 说明 |
|---|---|---|
| Cluster status | `green` | |
| Active shards % | `100.0` | |
| Unassigned shards | `0` | |
| 0 副本索引数 | `0` | P0-A |
| Templates with replicas=0 | `NONE` | P0-B |
| watermark.flood_stage | `85%` | P0-C |
| AutoTune State | `ENABLED` | P1-E |
| FreeStorageSpace | `> 30 GB` | 任一节点 |

---

## 七、回滚方案

### P0-A 回滚（副本添加导致存储压力）

```bash
while read -r INDEX; do
  awscurl --service es --region us-east-1 \
    -X PUT -H "Content-Type: application/json" \
    -d '{"index": {"number_of_replicas": 0}}' \
    "https://${ENDPOINT}/${INDEX}/_settings"
done < /tmp/zero-replica-indices-$(date +%Y%m%d).txt
```

### P0-B 回滚（template 改动出问题）

```bash
# 从备份恢复
python3 << 'EOF'
import json, subprocess, os
backup = f'/tmp/templates-before-{__import__("datetime").date.today().strftime("%Y%m%d")}.json'
with open(backup) as f:
    data = json.load(f)
endpoint = os.environ['ENDPOINT']
for name, tmpl in data.items():
    body = json.dumps(tmpl)
    subprocess.run(['awscurl', '--service', 'es', '--region', 'us-east-1',
                    '-X', 'PUT', '-H', 'Content-Type: application/json',
                    '-d', body, f'https://{endpoint}/_template/{name}'])
EOF
```

### P0-C 回滚（watermark 改动出问题）

```bash
awscurl --service es --region us-east-1 \
  -X PUT -H "Content-Type: application/json" \
  -d '{
    "persistent": {
      "cluster.routing.allocation.disk.watermark.low": null,
      "cluster.routing.allocation.disk.watermark.high": null,
      "cluster.routing.allocation.disk.watermark.flood_stage": null
    }
  }' \
  "https://${ENDPOINT}/_cluster/settings"
```

### P1-E 回滚（关闭 AutoTune）

```bash
aws opensearch update-domain-config \
  --domain-name luckycommon \
  --region us-east-1 \
  --auto-tune-options '{"DesiredState": "DISABLED"}'
```

---

## 八、为什么这是第三次复发

| 维度 | 真相 |
|---|---|
| 根因 | 5 个 `replicas=0` 索引 — 3 次事件**完全相同** |
| 整改手册 | 5/18 已经写完，**9 天来 0 项执行** |
| 历史推荐执行率 | 3/8 + 4/23 + 5/17 共 12 项建议，**0/12** |
| 阻塞理由（已失效） | "DBA 无 REST API 权限" — 实际 access policy 是 `Principal:*`，从跳板机即可调用 |
| 本次新增风险 | 磁盘 watermark 过松 → 重平衡可灌满到 0 MB |

**结论**：故障原因不是技术未知，而是**整改未执行**。本份手册的存在意义只有一个 —— 让 P0 步骤今晚就做完。

---

## 九、变更日志（执行时填写）

| 日期 (UTC) | 步骤 | 执行人 | 结果 | 备注 |
|---|---|---|---|---|
| 2026-05-27 09:03 | 故障发生 | — | RED 3h39m | 节点脱离 + 磁盘满 |
| 2026-05-27 12:42 | 集群自愈 GREEN | — | ActivePrimary 59→47（12 个索引被删） | 需业务方核查 |
| | P0-A 加副本 | | | |
| | P0-B 修 template | | | |
| | P0-C 前置 watermark | | | |
| | P1-D ISM 改造 | | | |
| | P1-E AutoTune | | | |
| | P1-F merge throttle | | | |

---

## 十、应急联系

- **DBA 主**：曾翔宇（David Zeng）
- **CTO**：Michael（架构决策 / AWS 账号所有者）
- **业务方对接**：语音 / common 服务负责人
- **应急脚本**：`/app/runbooks/es-emergency-throttle/es-emergency-throttle.sh`
- **完整整改手册**：`/app/runbooks/luckycommon-opensearch-remediation/RUNBOOK.md`（900 行，含 P0-1 至 P1-6 全套）

---

## 附录 A：关键命令快查

```bash
# 设置环境
export ENDPOINT=$(aws opensearch describe-domain --domain-name luckycommon --region us-east-1 \
  --query 'DomainStatus.Endpoints.vpc' --output text)

# 集群健康
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cluster/health?pretty"

# 列出所有索引（副本数）
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cat/indices?v"

# 查未分配分片原因
awscurl --service es --region us-east-1 \
  -X POST -H "Content-Type: application/json" -d '{}' \
  "https://${ENDPOINT}/_cluster/allocation/explain?pretty"

# 强制重试失败分片
awscurl --service es --region us-east-1 \
  -X POST "https://${ENDPOINT}/_cluster/reroute?retry_failed=true&pretty"

# 实时分片状态
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cat/shards?v" | grep -v STARTED

# 查 cluster settings
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cluster/settings?include_defaults=true&flat_settings=true&pretty"

# CloudWatch 集群健康基线
aws cloudwatch get-metric-data --region us-east-1 \
  --metric-data-queries '[
    {"Id":"red","MetricStat":{"Metric":{"Namespace":"AWS/ES","MetricName":"ClusterStatus.red","Dimensions":[{"Name":"DomainName","Value":"luckycommon"},{"Name":"ClientId","Value":"257394478466"}]},"Period":60,"Stat":"Maximum"}}
  ]' \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S)
```

## 附录 B：风险评估

| 步骤 | 主要风险 | 缓解措施 |
|---|---|---|
| P0-A 加副本 | 复制 I/O 飙升 → 节点过载 | 索引间间隔 5s；JVM/CPU 监控；变更窗口选低峰 |
| P0-B 改 template | JSON 错误导致模板失效 | 完整备份 → 仅改 replicas → 验证 |
| P0-C 前置 watermark | 高水位触发只读，业务感知 | 仅 85% 才只读，远高于正常使用率 |
| P1-D 改 ISM | 策略错误导致索引保留超期 | 备份 → 测试索引验证 → 推全 |
| P1-E AutoTune | 维护窗口期重启节点 | 选 Tue 05:29 UTC 已知低峰 |
| P1-F merge throttle | merge 挤占查询 I/O | 100mb 留余量；可秒级回滚 |

---

## 附录 C：参考文档

- 历史事件报告：
  - `/app/reports/es-cluster-red-luckycommon-2026-03-08.md` (LCNA-INC-2026-008)
  - `/app/reports/es-cluster-red-luckycommon-validation-2026-03-09.md`
  - `/app/reports/es-cluster-red-luckycommon-2026-04-20.md`
  - `/app/reports/luckycommon-opensearch-upgrade-cost-analysis-2026-04-23.md`
  - `/app/LCNA-INC-2026-026-luckycommon-OpenSearch-RED-2026-05-17.docx`
- 整改手册：`/app/runbooks/luckycommon-opensearch-remediation/RUNBOOK.md`
- 应急脚本：`/app/runbooks/es-emergency-throttle/es-emergency-throttle.sh`
- AWS 文档：
  - [OpenSearch Access Policies](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ac.html)
  - [Cluster Allocation Explain API](https://www.elastic.co/guide/en/elasticsearch/reference/6.8/cluster-allocation-explain.html)
  - [Disk-based Shard Allocation](https://www.elastic.co/guide/en/elasticsearch/reference/6.8/disk-allocator.html)

---

*手册作者：曾翔宇 (David Zeng) / Claude Code | 版本：v1.0 | 生成日期：2026-05-27*
