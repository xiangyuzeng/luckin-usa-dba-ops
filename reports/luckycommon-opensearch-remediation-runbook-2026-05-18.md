# luckycommon OpenSearch 配置整改执行手册

**集群**: luckycommon (AWS OpenSearch / Elasticsearch 6.8)
**账号**: 257394478466 (us-east-1)
**VPC**: vpc-0dce7ca7770422d33
**负责人**: 曾翔宇 (David Zeng)
**生成日期**: 2026-05-18
**关联事件**: LCNA-INC-2026-008 (3/8), 2026-04-20, LCNA-INC-2026-026 (5/17)

---

## 一、背景与整改依据

### 1. 事件回顾

luckycommon OpenSearch 集群在 **3 个月内连续发生 3 次 RED 状态事件**：

| 日期 (UTC) | 编号 | 直接触发机制 | RED 持续 | 应用影响 |
|---|---|---|---|---|
| 2026-03-08 07:00 | LCNA-INC-2026-008 | ISM 一次性删除 41GB / 4M docs（占集群 26%），节点 merge I/O 饱和掉线 | ~1 min（总恢复 7 min） | 3 个 5xx, 55 个 4xx, 搜索延迟 1.8→8.1ms |
| 2026-04-20 18:18 | （未编号） | 瞬态主节点选举抖动 / 极短分片状态转换 | <1 min（亚分钟级） | 无可观测影响 |
| 2026-05-17 13:22 | LCNA-INC-2026-026 | 数据节点 `WZNuw2r0TKWIWzUWVKboUQ` (m5.large) CPU 飙至 89%，JVM 指标采样缺失（指向长时 STW GC 暂停或进程僵死）；5 个 `replicas=0` 索引的 5 个 primary 因无副本不可恢复 | ~2 min（CloudWatch 红色窗口），总恢复 14 min（13:22→13:36） | 4.21M docs 不可搜索 2 min；`writes_blocked=0`, `5xx=0`，应用层未感知 |

### 2. 共同结构性根因

所有 3 次事件指向同一组配置层面问题，**它们之间互相放大**：

| 编号 | 根因 | 当前状态 | 影响事件 |
|---|---|---|---|
| R1 | **5 个生产索引 `number_of_replicas=0`**（5/17 已确认）：`chronus_task_sharding_log` + `es_task_2026-05-14/15/16/17`，占总索引数 19 的 26%；总分片框架仍为 59 primary + 41 replica = 100 shards（AWS Cluster Insight "Misconfigured Replica" MEDIUM 长期 ACTIVE） | **直接触发 5/17 RED**：5 个 primary 因节点抖动不可恢复（59→54）；同一脆弱性也是 3/8 事件升级到 RED 的根因 |
| R2 | **ISM 一次性大批量删除** | 3/8 事件中 41GB / 2 min 删除 | 直接触发 3/8 事件 |
| R3 | **慢性 JVM 锯齿波（74–76% 峰值）** | AutoTune DISABLED, 每 4–8h Major GC 一次 | 提高所有事件的发生概率 |
| R4 | **merge throttle 实际生效值需经 P0-1 拉取确认** | ES 6.8 原生默认 unlimited；AWS OpenSearch 托管层是否覆盖默认值需通过 `GET /_cluster/settings?include_defaults=true` 直接核对（P0-1 完成后执行） | 若实际受限，会拖长删除后节点高压窗口（3/9 验证报告观测到 25–49 min） |
| R5 | **es_task 系列日索引每天以 0 副本生成** | 5/17 报告 §6.5 确认每日 rollover 仍以 replicas=0 创建（5 个 0 副本索引中 4 个为 es_task 日索引），需通过 P0-1 拉取实际 template/ISM 进一步定位是 template 还是 ISM rollover 配置 | 即便修复现有 0 副本，**次日 es_task 当日索引仍以 0 副本创建**，RED 风险快速积累回来 |
| R6 | **DBA 无 VPC 内 REST API 访问权限** | access policy 未授权 databasecheck IAM 用户 | 3/9 验证报告、4/23 分析报告都因此无法完成 — 阻塞所有整改 |

### 3. 整改策略说明

本手册聚焦**配置级整改**，定位为"用现有资源把可消除的风险先消除"：

- **R1、R5**：通过修改 `number_of_replicas` 和 index template → 消除 0 副本结构性脆弱点
- **R2**：通过 ISM 策略调整（rollover + 调度低峰）→ 消除批量删除触发器
- **R3**：通过启用 AutoTune → 让 AWS 自动调优 JVM
- **R4**：通过 cluster setting 显式调整 → 缩短节点高压窗口
- **R6**：通过 access policy 追加 → 解锁所有后续运维操作

实例规格升级（master t3.small → m5.large，数据节点 m5.large → r5.large）和引擎升级（ES 6.8 → OpenSearch 2.x）**不在本手册范围内**，作为单独项目规划。

### 4. 历史建议执行情况

3/8 和 4/23 两份报告共提出 12 项整改建议，截至昨日 **0 项执行**（4/20 报告附录已确认）。本手册是这些建议中**可在 1–2 周内独立完成**部分的合集，目的是先把"能做的"做了，避免同一事件第 4 次发生。

---

## 二、变更概述

本手册覆盖 **6 项配置级整改措施**，分两批执行：

| 阶段 | 编号 | 措施 | 风险 | 预计耗时 |
|---|---|---|---|---|
| **P0** | 1 | VPC 内 REST API 访问通道 | 低 | 30 min |
| **P0** | 2 | 5 个 0 副本索引添加副本（chronus_task_sharding_log + 4 个 es_task 日索引） | 中（产生数据复制 I/O） | 30–60 min |
| **P0** | 3 | ISM 删除策略改小批次 + 调度到低峰窗口 | 低 | 30 min |
| **P1** | 4 | 启用 AutoTune | 低 | 5 min（AWS Console） |
| **P1** | 5 | 调高 `indices.store.throttle.max_bytes_per_sec` | 低 | 5 min |
| **P1** | 6 | 修改 index template 默认 `replicas=1` | 低 | 10 min |

**变更窗口建议**：
- P0 全部安排在 **UTC 02:00–05:00**（美东 EST 22:00–01:00 业务低峰）
- P1 可在任意时段执行（配置级变更，无数据移动）

**关键前置条件**：
- DBA IAM 用户 `databasecheck` 需被加入 luckycommon 域 access policy（见 P0-1）
- 准备好可访问 VPC 的跳板机或 Lambda（见 P0-1）

---

## 三、前置检查（执行任何步骤前必做）

### 2.1 集群健康基线检查

```bash
# 通过 AWS CLI 检查域配置
aws opensearch describe-domain \
  --domain-name luckycommon \
  --region us-east-1 \
  --query 'DomainStatus.{Endpoint:Endpoints.vpc,Engine:EngineVersion,Processing:Processing,AutoTune:AutoTuneOptions.State}'

# 检查 CloudWatch 即时健康状态（5 分钟前 → 现在）
aws cloudwatch get-metric-data --region us-east-1 \
  --metric-data-queries '[
    {"Id":"red","MetricStat":{"Metric":{"Namespace":"AWS/ES","MetricName":"ClusterStatus.red","Dimensions":[{"Name":"DomainName","Value":"luckycommon"},{"Name":"ClientId","Value":"257394478466"}]},"Period":60,"Stat":"Maximum"}},
    {"Id":"yellow","MetricStat":{"Metric":{"Namespace":"AWS/ES","MetricName":"ClusterStatus.yellow","Dimensions":[{"Name":"DomainName","Value":"luckycommon"},{"Name":"ClientId","Value":"257394478466"}]},"Period":60,"Stat":"Maximum"}},
    {"Id":"nodes","MetricStat":{"Metric":{"Namespace":"AWS/ES","MetricName":"Nodes","Dimensions":[{"Name":"DomainName","Value":"luckycommon"},{"Name":"ClientId","Value":"257394478466"}]},"Period":60,"Stat":"Minimum"}},
    {"Id":"jvm","MetricStat":{"Metric":{"Namespace":"AWS/ES","MetricName":"JVMMemoryPressure","Dimensions":[{"Name":"DomainName","Value":"luckycommon"},{"Name":"ClientId","Value":"257394478466"}]},"Period":300,"Stat":"Maximum"}}
  ]' \
  --start-time $(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S)
```

**通过标准**：
- `ClusterStatus.red = 0`
- `ClusterStatus.yellow = 0`
- `Nodes = 7`
- `JVMMemoryPressure < 70%`
- `Processing = false`（无正在进行的域更新）

**任一不通过则停止，不得执行任何变更。**

### 2.2 备份当前配置

```bash
mkdir -p ~/temp/luckycommon-remediation-$(date -u +%Y%m%d)
cd ~/temp/luckycommon-remediation-$(date -u +%Y%m%d)

# 备份域配置
aws opensearch describe-domain --domain-name luckycommon --region us-east-1 \
  > describe-domain-before.json

# 备份 access policy
aws opensearch describe-domain-config --domain-name luckycommon --region us-east-1 \
  --query 'DomainConfig.AccessPolicies' > access-policy-before.json
```

---

## 四、P0 措施执行（本周内，UTC 02:00–05:00 窗口）

### P0-1: 打通 VPC 内 REST API 访问通道

**解决的问题**: DBA IAM 用户 `databasecheck` 未被 luckycommon 域的 access policy 授权，无法调用 OpenSearch REST API。3 次事件的事后调查（3/9 验证报告、4/23 升级成本分析、5/17 昨日事件）都因此**未能审计 ISM 策略、分片配置、index template** —— 所有后续整改步骤都依赖这条通道。

**修改原因**: 3/9 验证报告 R1 明确指出："Enable cluster API access for the DBA IAM role via the domain's access policy ... This unblocks all Phase 3 B1–B9 queries and prevents future investigations from being stalled." 该建议 2 个月未执行，导致 4/20 和 5/17 事件再次受阻。

**预期效果**: 解锁 `_cluster/health`、`_cat/indices`、`_opendistro/_ism/*`、`_template` 等所有运维 API。后续 P0-2/P0-3/P1-5/P1-6 步骤都依赖此通道。

**方案选择**（按优先级）：

#### 方案 A：跳板机（推荐 — 复用现有资源）

1. 找到现有的内网跳板机（与 vpc-0dce7ca7770422d33 同 VPC 或已 peering）。
2. 在跳板机上确认能解析 VPC endpoint：

```bash
# 在跳板机上执行
ENDPOINT=$(aws opensearch describe-domain --domain-name luckycommon --region us-east-1 \
  --query 'DomainStatus.Endpoints.vpc' --output text)
echo "VPC Endpoint: $ENDPOINT"

# 测试连通性（不带认证，预期返回 403 或 401，说明网络通）
curl -sk -o /dev/null -w "%{http_code}\n" "https://${ENDPOINT}/_cluster/health"
```

3. 修改 access policy 加入 DBA IAM 用户：

```bash
# 当前 access policy（备份后）
aws opensearch describe-domain-config --domain-name luckycommon --region us-east-1 \
  --query 'DomainConfig.AccessPolicies.Options' --output text > current-policy.json

# 编辑 current-policy.json，在 Statement 数组里追加：
```

```json
{
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::257394478466:user/databasecheck"
  },
  "Action": [
    "es:ESHttpGet",
    "es:ESHttpHead"
  ],
  "Resource": "arn:aws:es:us-east-1:257394478466:domain/luckycommon/*"
}
```

> ⚠️ **只授予 GET/HEAD 权限**。需要做副本修改时再临时追加 `es:ESHttpPut`（步骤 P0-2 执行完后立即撤销）。

```bash
# 应用更新后的 policy
aws opensearch update-domain-config \
  --domain-name luckycommon \
  --region us-east-1 \
  --access-policies file://current-policy.json
```

> 该操作会触发域 "Processing" 状态 5–15 分钟，但**不会中断服务**。

4. 验证（在跳板机上，使用 awscurl 或带 SigV4 签名的 curl）：

```bash
pip install awscurl  # 如未安装

# 测试只读 API
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cluster/health?pretty"
```

**预期输出**：JSON 含 `"status": "green"`, `"number_of_nodes": 7`, `"unassigned_shards": 0`

#### 方案 B：Lambda 函数（如无跳板机）

```bash
# 在 VPC 内创建一个轻量 Lambda 用于执行 ES 运维命令
# Runtime: Python 3.11, VPC: vpc-0dce7ca7770422d33
# 同 subnet 和 security group 与 OpenSearch 域一致
```

详细 Lambda 模板见 `/app/runbooks/luckycommon-opensearch-remediation/scripts/lambda-es-proxy.py`（待创建，本次手册暂不展开）。

**P0-1 完成判定**：
- ✅ `awscurl ... /_cluster/health` 返回 GREEN
- ✅ `awscurl ... /_cat/indices?v` 列出索引清单

---

### P0-2: 给 5 个 0 副本索引添加副本

**解决的问题**: 5/17 事件已**精确定位**到 5 个生产索引 `number_of_replicas=0`，占总索引数 19 的 26%（AWS Cluster Insight "Misconfigured Replica" MEDIUM 长期 ACTIVE）：

| 索引名 | 类型 | 5/17 影响 |
|---|---|---|
| `chronus_task_sharding_log` | 应用任务调度日志（单实例） | RED 直接贡献 |
| `es_task_2026-05-14` | es_task 系列日索引 (T-3) | RED 直接贡献 |
| `es_task_2026-05-15` | es_task 系列日索引 (T-2) | RED 直接贡献 |
| `es_task_2026-05-16` | es_task 系列日索引 (T-1) | RED 直接贡献 |
| `es_task_2026-05-17` | es_task 系列日索引 (T, 当日) | RED 直接贡献 |

任何持有这 5 个索引的数据节点出现哪怕极短暂的不可达（如 5/17 的 GC 暂停），相关 primary 分片立即进入 unassigned 状态 → 集群直接 RED。注意：`es_task` 是**日索引**，每天新增 1 个新成员（如未修复 P1-6 template，5/18 当日索引仍会以 0 副本创建）。

**修改原因**: 这是 **3 次 RED 事件最关键的共同结构性根因**：
- 3/8 事件 (LCNA-INC-2026-008)：节点因 41GB 大删除 merge 饱和而短暂掉出集群，0 副本分片瞬间不可用 → RED
- 4/20 事件：根因报告附录第六章明确列为"P0 #1 整改项"；4/23 成本分析方案 D1 确认现有 EBS 余量 177GB 足以容纳新副本
- 5/17 事件 (LCNA-INC-2026-026)：节点 `WZNuw2r0TKWIWzUWVKboUQ` CPU 89%/JVM 心跳中断 2 min，**5 个 primary 因 0 副本不可恢复**，导致 ActivePrimary 59→54 + SearchableDocuments 跌 4.21M
- 5/17 报告 §6.5 明确："INC-008 提出的「将 es_task 系列与 chronus_task_sharding_log 副本数升至 1」整改项在 INC-026 发生时仍未执行 — 因此本次是同一根因的再次显现"

修复后任一持有该索引的节点掉线，副本分片立即接管，**集群最多进入 YELLOW 而不会到 RED**。

**预期效果**:
- 消除单节点抖动直接触发 RED 的路径（结构性根除最大风险）
- 新增约 18 个副本分片（5 个索引中 chronus 含多 primary），存储占用从 ~223 GB 增至 ~291 GB（仍在 400 GB EBS 总容量内）
- 副本同时分担查询负载，对搜索性能略有正向收益

**前置确认**：

```bash
# 步骤 1: 列出所有 0 副本索引（与 5/17 报告的 5 个交叉核验）
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cat/indices?h=index,pri,rep,docs.count,store.size&v" \
  | awk 'NR==1 || $3==0' \
  | tee zero-replica-indices.txt

# 步骤 2: 确认 5/17 已知的 5 个索引都在清单中
EXPECTED='chronus_task_sharding_log es_task_2026-05-14 es_task_2026-05-15 es_task_2026-05-16 es_task_2026-05-17'
for IDX in $EXPECTED; do
  grep -q "^$IDX " zero-replica-indices.txt && echo "✓ $IDX" || echo "✗ $IDX (MISSING — 已被修复或已 rollover?)"
done

# 步骤 3: 检查是否有"新增"的 0 副本索引（如 es_task_2026-05-18 等当日索引）
echo "All zero-replica indices currently:"
awk 'NR>1 {print "  " $1}' zero-replica-indices.txt

# 步骤 4: 估算新增存储需求（应 < 现有 EBS 余量 177 GB）
awk 'NR>1 {gsub(/gb|mb|kb/,"",$5); sum+=$5} END {print "Estimated additional storage: " sum " (单位混合，需复核)"}' zero-replica-indices.txt
```

**通过标准**：
- 5/17 报告的 5 个索引应在清单中（如已 rollover 或已被修复则可少）
- 总数应在 5–10 区间（含 es_task 系列每日新增的索引）
- 估算新增存储 < 100 GB（保留 80GB 安全余量）

**执行变更**：

```bash
# 临时追加 PUT 权限到 access policy（执行前）
# 在 current-policy.json 的 DBA Statement 里 Action 数组追加 "es:ESHttpPut"
aws opensearch update-domain-config \
  --domain-name luckycommon \
  --region us-east-1 \
  --access-policies file://current-policy.json
# 等待 Processing 完成（5–15 分钟）

# 方案 A（推荐）：先处理 chronus_task_sharding_log（单索引，shard 数较多）
# 观察其复制完成、unassigned=0 后，再处理 es_task 系列
awscurl --service es --region us-east-1 \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{"index": {"number_of_replicas": 1}}' \
  "https://${ENDPOINT}/chronus_task_sharding_log/_settings"

# 等待该索引复制完成（每 30s 检查一次）
while true; do
  UNASSIGNED=$(awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cluster/health" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['unassigned_shards'])")
  echo "$(date -u +%H:%M:%S) unassigned_shards=$UNASSIGNED"
  [ "$UNASSIGNED" = "0" ] && break
  sleep 30
done

# 方案 A 续：批量处理 es_task 日索引（每条间隔 5s）
for IDX in es_task_2026-05-14 es_task_2026-05-15 es_task_2026-05-16 es_task_2026-05-17 es_task_2026-05-18; do
  echo "Setting replicas=1 on $IDX"
  awscurl --service es --region us-east-1 \
    -X PUT \
    -H "Content-Type: application/json" \
    -d '{"index": {"number_of_replicas": 1}}' \
    "https://${ENDPOINT}/${IDX}/_settings" 2>&1 | grep -v "index_not_found"
  sleep 5
done

# 方案 B（兜底）：从清单批量处理（如方案 A 之外还发现其他 0 副本索引）
while read -r INDEX; do
  [ -z "$INDEX" ] && continue
  echo "Setting replicas=1 on $INDEX"
  awscurl --service es --region us-east-1 \
    -X PUT \
    -H "Content-Type: application/json" \
    -d '{"index": {"number_of_replicas": 1}}' \
    "https://${ENDPOINT}/${INDEX}/_settings"
  sleep 5
done < <(awk 'NR>1 {print $1}' zero-replica-indices.txt)
```

**观察集群恢复**：

```bash
# 监控分片恢复进度（每 30 秒打印一次，持续 30 分钟）
for i in $(seq 1 60); do
  echo "=== $(date -u +%H:%M:%S) ==="
  awscurl --service es --region us-east-1 \
    "https://${ENDPOINT}/_cluster/health" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Status={d['status']} InitShards={d['initializing_shards']} RelocShards={d['relocating_shards']} UnassignedShards={d['unassigned_shards']} ActiveShards%={d['active_shards_percent_as_number']}\")"
  sleep 30
done
```

**期间监控**（另一个终端）：
- CloudWatch `JVMMemoryPressure` 不应超过 85%
- `CPUUtilization` 不应超过 80%
- `ClusterUsedSpace` 缓慢上升，最终增量应在 50–80 GB

**完成判定**：
- ✅ `status = green`
- ✅ `unassigned_shards = 0`
- ✅ `_cat/indices` 中 `rep` 列全部 ≥ 1

**变更后立即撤销 PUT 权限**：
```bash
# 从 current-policy.json 移除 "es:ESHttpPut"
aws opensearch update-domain-config --domain-name luckycommon --region us-east-1 \
  --access-policies file://current-policy.json
```

---

### P0-3: ISM 删除策略改小批次 + 调度到低峰窗口

**解决的问题**: 当前 ISM 策略在业务高峰时段（3/8 事件触发时间为 07:00 UTC = 美东 03:00 EST 凌晨批量任务窗口）一次性删除超过 41GB / 4M docs。删除产生的 segment merge I/O 在 m5.large 数据节点（2 vCPU, 仅 ~4GB JVM heap）上持续 25–49 分钟，期间节点处于高压状态，**任一节点掉出集群叠加 R1（0 副本分片）即触发 RED**。

**修改原因**:
- 3/8 验证报告 (LCNA-INC-2026-008) 直接归因："Large single-batch index deletion — 41 GB deleted in ~2 min, no throttling — **ROOT CAUSE**"
- 3/8 Action 1 建议：reduce batch size + schedule to maintenance window + low-traffic windows — **2 个月未执行**
- 3/9 验证报告 R5 建议 raise merge throttle 上限同向印证（本手册 P1-5 配套执行）

**预期效果**:
- 单次 ISM 周期删除量从 41GB / 4M docs 降至每索引 ≤ 5GB / ≤ 200K docs（通过 rollover 控制单索引体量）
- 删除调度移至业务低峰（UTC 02:00），即便发生节点抖动也不影响应用层
- 配合 P1-5 调高 merge throttle，节点高压窗口从 25–49 min 缩短至 < 5 min

#### 步骤 1: 审计现有 ISM 策略

```bash
# 列出所有 ISM 策略
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_opendistro/_ism/policies?pretty" \
  > ism-policies-before.json

# 提取所有含 "delete" action 的策略
python3 <<'EOF'
import json
with open('ism-policies-before.json') as f:
    data = json.load(f)
for p in data.get('policies', []):
    policy = p['policy']
    pid = p['_id']
    for state in policy.get('states', []):
        for action in state.get('actions', []):
            if 'delete' in action:
                print(f"Policy {pid} → state {state['name']}: delete action")
EOF
```

#### 步骤 2: 修改删除策略（每个 delete 策略都要改）

对每个含 `delete` 的策略，调整两点：

**(a) 加 condition：仅在低峰时段执行**

ISM 6.8 不直接支持 cron，但可以通过 `transitions` 加 `min_index_age` + 错峰来近似：

```json
{
  "policy": {
    "policy_id": "log_rotation_policy",
    "description": "Delete logs after 30 days, throttled, low-traffic window only",
    "default_state": "hot",
    "schedule": {
      "interval": {
        "period": 1,
        "unit": "Hours",
        "start_time": 1716098400000   // ← 设置为某天 02:00 UTC 的 Unix epoch ms
      }
    },
    "states": [
      {
        "name": "hot",
        "actions": [],
        "transitions": [
          {
            "state_name": "delete",
            "conditions": {
              "min_index_age": "30d"
            }
          }
        ]
      },
      {
        "name": "delete",
        "actions": [
          {
            "delete": {}
          }
        ],
        "transitions": []
      }
    ]
  }
}
```

**关键参数**：
- `schedule.interval.start_time`: 设置成 UTC 02:00 的某个具体时间戳（业务低峰）
- `schedule.interval.period: 1` `unit: Hours`: ISM job 每小时只检查一次，不会被频繁触发
- 在 ES 6.8 OpenDistro 中**无法直接限制每次批量删除的数量**，但可通过：
  - 缩短 `min_index_age` 差异（让一次 ISM 周期内可删除的索引数变少）
  - 把单个大索引拆分成多个小索引（rollover by size，例如 5GB/索引）

**(b) 推荐：添加 rollover 让单索引体量受控**

```json
{
  "states": [
    {
      "name": "hot",
      "actions": [
        {
          "rollover": {
            "min_size": "5gb",
            "min_doc_count": 200000
          }
        }
      ],
      "transitions": [...]
    },
    ...
  ]
}
```

> 这样每个索引最多 5GB，即便 ISM 一次扫描出多个待删索引，单次删除影响也可控。

#### 步骤 3: 应用更新

```bash
# 更新单个策略
awscurl --service es --region us-east-1 \
  -X PUT \
  -H "Content-Type: application/json" \
  -d @new-policy.json \
  "https://${ENDPOINT}/_opendistro/_ism/policies/log_rotation_policy?if_seq_no=<N>&if_primary_term=<M>"
# seq_no 和 primary_term 从 ism-policies-before.json 里读取
```

#### 步骤 4: 验证

```bash
# 确认策略已生效
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_opendistro/_ism/policies/log_rotation_policy?pretty"

# 查看具体索引的 ISM 状态
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_opendistro/_ism/explain/<INDEX_NAME>?pretty"
```

**完成判定**：
- ✅ 所有 delete 策略含 rollover + 02:00 UTC 调度
- ✅ ISM explain 显示策略已绑定到目标索引

---

## 五、P1 措施执行（两周内，任意时段）

### P1-4: 启用 AutoTune

**解决的问题**: 集群当前 `AutoTuneOptions.DesiredState = DISABLED`（4/23 `describe-domain` 确认）。JVM 内存压力呈典型锯齿波模式：每 4–8 小时 Major GC 一次，压力从 34–42% 爬升至 74–76% 后跌落（4/20 报告附录 C 24 小时趋势）。**JVM 压力慢性偏高使集群对所有外部扰动（删除、merge、查询尖峰）容错性下降**，间接放大 R1/R2 风险。

**修改原因**:
- 3/8 报告长期建议清单：P2 "Enable Auto-Tune — Let AWS optimize JVM and thread pool settings automatically"
- 4/20 报告 P2 重申同样建议
- 数据节点 m5.large 8GB RAM → ~4GB JVM heap 对当前工作负载本就偏小，启用 AutoTune 是在不升级实例前提下可获取的最大 JVM 优化收益

**预期效果**:
- AWS 在维护窗口内自动调整 JVM 参数（heap 分配、GC 策略）和查询/字段数据缓存
- 预期 JVM 峰值压力从 74–76% 降至 60–70% 区间
- 缩短 GC pause 时间，降低节点因 GC 暂停被误判为"不可达"的概率
- 减少手动调优工作量

```bash
# 通过 AWS CLI 启用（推荐）
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

**或通过 AWS Console**：
1. OpenSearch Service → Domains → luckycommon → Cluster configuration → Edit
2. Auto-Tune 区域选 "Enable Auto-Tune"
3. Maintenance schedule 选 Tuesday 05:29 UTC（与现有维护窗口对齐）
4. 保存（域进入 Processing 状态约 10–20 分钟，**无服务中断**）

**注意**：
- 启用后 AutoTune 会在维护窗口内重启节点应用 JVM 调优，建议**周二 05:29 UTC** 时段确保无业务高峰。
- 首次调优建议保留 2 周观察期，期间不应叠加其他变更。

**完成判定**：
```bash
aws opensearch describe-domain --domain-name luckycommon --region us-east-1 \
  --query 'DomainStatus.AutoTuneOptions.State'
# 预期输出: "ENABLED"
```

---

### P1-5: 调高 `indices.store.throttle.max_bytes_per_sec`

**解决的问题**: 大批量删除后产生大量待合并 segment。若 merge I/O 速率被限制在较低值（如 20 MB/s），需要 25–49 分钟才能完成合并；这段时间节点 I/O 持续饱和，CPU/JVM 压力升高，**进一步放大节点掉线 → RED 的概率**。

**修改原因**:
- 3/9 验证报告 R5："The current merge throttle may be too low for the deletion volumes (~260K–1M docs per ISM cycle). Increasing the merge I/O ceiling reduces the duration of post-deletion segment merge windows, shortening node stress periods from the observed 25–49 minutes to < 5 minutes."
- ES 6.8 默认 `indices.store.throttle.type = none`（unlimited），但 AWS OpenSearch 托管层可能有隐式限制
- 该项与 P0-3 是配套关系：P0-3 控制"删多少"，P1-5 控制"合并多快"

**预期效果**:
- 删除后 segment merge 窗口从 25–49 min 缩短至 < 5 min
- 节点高压时间锐减，掉线概率显著下降
- 与 P0-3 配套实施可基本消除 R2 触发路径

> ⚠️ ES 6.8 中此设置已**默认不限制**（`unlimited`）。OpenDistro/AWS 受托管层可能有隐式限制。先确认当前值。

```bash
# 检查当前 cluster setting
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cluster/settings?include_defaults=true&flat_settings=true&pretty" \
  | grep -i throttle
```

**两种情况**：

**情况 A**: 当前显示 `unlimited` → 无需修改，跳过本步骤
**情况 B**: 当前有数值（如 `20mb`）→ 调整

```bash
# 持久化提升至 100 MB/s（gp3 EBS 单卷上限 125 MB/s，留余量）
awscurl --service es --region us-east-1 \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "persistent": {
      "indices.store.throttle.max_bytes_per_sec": "100mb",
      "indices.store.throttle.type": "merge"
    }
  }' \
  "https://${ENDPOINT}/_cluster/settings"
```

**验证**：
```bash
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cluster/settings?flat_settings=true&pretty"
# 预期输出 persistent 区有 "indices.store.throttle.max_bytes_per_sec": "100mb"
```

---

### P1-6: 修改 index template 默认 `replicas=1`

**解决的问题**: P0-2 只修复**现有** 18 个 0 副本索引，但如果 index template 默认 `number_of_replicas=0`，**每天通过 ISM rollover 或应用创建的新索引仍会继续以 0 副本生成**，几周后 RED 风险即可恢复。

**修改原因**:
- 4/20 报告 P1 整改项 #3："审计所有 index template — 确保默认模板包含 `number_of_replicas: 1`，防止新索引继续以 0 副本创建"
- R5（结构性根因第 5 项）的根本治理 — 单次修复无法持续，必须从模板层根除
- P0-2 + P1-6 = 短期修复 + 长期治本，缺一不可

**预期效果**:
- 所有未来通过 template 匹配创建的新索引默认带 1 个副本
- 杜绝 R1 风险在整改后重新积累
- 配合 ISM 的 rollover（P0-3 引入）形成完整的索引生命周期治理

#### 步骤 1: 列出现有 templates

```bash
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_template?pretty" > templates-before.json

# 找出所有 replicas=0 的 template
python3 <<'EOF'
import json
with open('templates-before.json') as f:
    data = json.load(f)
for name, tmpl in data.items():
    replicas = tmpl.get('settings', {}).get('index', {}).get('number_of_replicas')
    if replicas in ('0', 0, None):
        print(f"Template '{name}': replicas={replicas} (NEEDS FIX)")
    else:
        print(f"Template '{name}': replicas={replicas} (OK)")
EOF
```

#### 步骤 2: 修改有问题的 template

对每个 `replicas=0` 的 template：

```bash
# 示例：修改名为 "logs_template" 的 template
awscurl --service es --region us-east-1 \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "index_patterns": ["logs-*"],
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1
    }
  }' \
  "https://${ENDPOINT}/_template/logs_template"
```

> ⚠️ **保留原 template 的其他字段**（如 mappings、aliases）。建议从 `templates-before.json` 完整复制原 JSON，只改 `number_of_replicas`。

#### 步骤 3: 验证

```bash
# 重新拉取 templates
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_template?pretty" \
  > templates-after.json

# 确认所有 template replicas >= 1
python3 -c "
import json
with open('templates-after.json') as f: data = json.load(f)
fail = [n for n, t in data.items() if t.get('settings',{}).get('index',{}).get('number_of_replicas') in ('0', 0, None)]
print('FAIL:', fail) if fail else print('All templates replicas >= 1 ✓')
"
```

> **注意**：修改 template 只影响**未来创建**的索引。已有 0 副本索引在 P0-2 已修复。

---

## 六、完整验证清单（全部执行后）

执行以下所有检查，全部通过才能认为整改完成：

```bash
ENDPOINT=$(aws opensearch describe-domain --domain-name luckycommon --region us-east-1 \
  --query 'DomainStatus.Endpoints.vpc' --output text)

echo "========== Cluster Health =========="
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cluster/health?pretty"

echo "========== Zero-replica Index Count =========="
ZERO=$(awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cat/indices?h=rep" | awk '$1==0' | wc -l)
echo "Zero-replica indices: $ZERO (expected: 0)"

echo "========== AutoTune State =========="
aws opensearch describe-domain --domain-name luckycommon --region us-east-1 \
  --query 'DomainStatus.AutoTuneOptions.State'

echo "========== Templates Replicas Check =========="
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_template" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); bad=[n for n,t in d.items() if t.get('settings',{}).get('index',{}).get('number_of_replicas') in ('0',0,None)]; print('Templates with replicas=0:', bad if bad else 'NONE ✓')"

echo "========== ISM Policies =========="
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_opendistro/_ism/policies?pretty" \
  | python3 -c "
import sys,json
d = json.load(sys.stdin)
for p in d.get('policies', []):
    pid = p['_id']
    sched = p['policy'].get('schedule', {}).get('interval', {})
    has_rollover = any('rollover' in a for s in p['policy'].get('states',[]) for a in s.get('actions',[]))
    print(f'{pid}: schedule_period={sched.get(\"period\")} {sched.get(\"unit\")}, has_rollover={has_rollover}')
"

echo "========== Merge Throttle =========="
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cluster/settings?include_defaults=true&flat_settings=true" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('throttle.max_bytes_per_sec=', d.get('persistent',{}).get('indices.store.throttle.max_bytes_per_sec') or d.get('defaults',{}).get('indices.store.throttle.max_bytes_per_sec'))"
```

**全部通过标准**：

| 检查项 | 期望值 |
|---|---|
| Cluster status | `green` |
| Active shards % | `100.0` |
| Unassigned shards | `0` |
| Zero-replica index count | `0` |
| AutoTune State | `ENABLED` |
| Templates with replicas=0 | `NONE` |
| ISM 所有 delete 策略 | 含 rollover, schedule 含 02:00 UTC |
| Merge throttle | `100mb` 或 `unlimited` |

---

## 七、回滚方案

### P0-2 回滚（撤销副本添加）

```bash
# 如副本复制导致存储压力，可回退到 replicas=0
while read -r INDEX; do
  awscurl --service es --region us-east-1 \
    -X PUT \
    -H "Content-Type: application/json" \
    -d '{"index": {"number_of_replicas": 0}}' \
    "https://${ENDPOINT}/${INDEX}/_settings"
done < zero-replica-indices.txt
```

### P0-3 回滚（ISM 策略）

```bash
# 从 ism-policies-before.json 恢复原策略
python3 << 'EOF'
import json, subprocess
with open('ism-policies-before.json') as f:
    data = json.load(f)
for p in data['policies']:
    pid = p['_id']
    policy_body = json.dumps({'policy': p['policy']})
    # 调用 awscurl 恢复（这里仅打印命令）
    print(f"awscurl --service es --region us-east-1 -X PUT -H 'Content-Type: application/json' -d '{policy_body}' 'https://${{ENDPOINT}}/_opendistro/_ism/policies/{pid}'")
EOF
```

### P1-4 回滚（关闭 AutoTune）

```bash
aws opensearch update-domain-config \
  --domain-name luckycommon \
  --region us-east-1 \
  --auto-tune-options '{"DesiredState": "DISABLED"}'
```

### P1-5 回滚（merge throttle）

```bash
awscurl --service es --region us-east-1 \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{"persistent": {"indices.store.throttle.max_bytes_per_sec": null}}' \
  "https://${ENDPOINT}/_cluster/settings"
```

### P1-6 回滚（template）

```bash
# 从 templates-before.json 恢复
python3 << 'EOF'
import json
with open('templates-before.json') as f:
    data = json.load(f)
for name, tmpl in data.items():
    body = json.dumps(tmpl)
    print(f"awscurl --service es --region us-east-1 -X PUT -H 'Content-Type: application/json' -d '{body}' 'https://${{ENDPOINT}}/_template/{name}'")
EOF
```

---

## 八、风险评估

| 步骤 | 主要风险 | 缓解措施 |
|---|---|---|
| P0-1 | access policy 错误导致应用断连 | 仅追加 Statement，不删除现有；先在 dev 验证 |
| P0-2 | 18 索引同时复制导致 I/O 飙升 → 节点过载 → RED | 每条 PUT 间隔 5s；监控 JVM/CPU；变更窗口选低峰 |
| P0-3 | ISM 策略 JSON 错误导致策略失效 → 数据保留超期 | 修改前完整备份；先在单个测试索引验证 |
| P1-4 | AutoTune 重启节点 | 设置维护窗口在低峰 Tuesday 05:29 UTC |
| P1-5 | merge 速度过快挤占查询 I/O | 100mb 留有余量；可随时回滚 |
| P1-6 | template 修改影响新索引行为 | 只改 replicas，不动 mappings；保留原始备份 |

**通用应急预案**：
- 任何步骤后出现 RED 或 JVM > 90%，**立即停止后续步骤**，按对应回滚方案处理
- 应急联系：DBA David（曾翔宇）+ Michael (CTO)
- 应急参考：`/app/runbooks/es-emergency-throttle/es-emergency-throttle.sh`

---

## 九、变更后观察期

| 时段 | 观察重点 | 告警阈值 |
|---|---|---|
| 变更后 1 小时 | `JVMMemoryPressure`, `CPUUtilization` | JVM > 85% / CPU > 80% |
| 变更后 24 小时 | `ClusterStatus.red/yellow`, `Nodes` | 任何 RED 或 Nodes < 7 |
| 变更后 7 天 | RED 告警频率（应为 0） | 任何 RED 告警 |
| 变更后 30 天 | JVM 峰值趋势是否下降 | 峰值仍 > 76% → 升级仍需评估 |

**关键 CloudWatch 仪表板**：
- AWS Console → OpenSearch → luckycommon → Cluster health
- Grafana：检查 `D3SA3spNk` Prometheus datasource 是否有 OpenSearch panel

---

## 十、变更日志（执行时填写）

| 日期 (UTC) | 步骤 | 执行人 | 结果 | 备注 |
|---|---|---|---|---|
| | P0-1 | | | |
| | P0-2 | | | |
| | P0-3 | | | |
| | P1-4 | | | |
| | P1-5 | | | |
| | P1-6 | | | |

---

## 附录 A：关键命令快查

```bash
# 设置环境变量
export ENDPOINT=$(aws opensearch describe-domain --domain-name luckycommon --region us-east-1 \
  --query 'DomainStatus.Endpoints.vpc' --output text)

# 集群健康
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cluster/health?pretty"

# 列出所有索引（副本数）
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cat/indices?v"

# 列出所有 ISM 策略
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_opendistro/_ism/policies?pretty"

# 列出所有 template
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_template?pretty"

# 查看 cluster settings
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cluster/settings?include_defaults=true&flat_settings=true&pretty"

# 实时分片状态
awscurl --service es --region us-east-1 "https://${ENDPOINT}/_cat/shards?v"

# 触发监控基线
aws cloudwatch get-metric-statistics --region us-east-1 \
  --namespace AWS/ES \
  --metric-name JVMMemoryPressure \
  --dimensions Name=DomainName,Value=luckycommon Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Maximum
```

## 附录 B：参考文档

- [AWS OpenSearch Access Policies](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ac.html)
- [OpenDistro ISM Documentation](https://opendistro.github.io/for-elasticsearch-docs/docs/im/ism/)
- [Elasticsearch 6.8 Cluster Update Settings](https://www.elastic.co/guide/en/elasticsearch/reference/6.8/cluster-update-settings.html)
- 历史事件报告:
  - `/app/reports/es-cluster-red-luckycommon-2026-03-08.md`
  - `/app/reports/es-cluster-red-luckycommon-validation-2026-03-09.md`
  - `/app/reports/es-cluster-red-luckycommon-2026-04-20.md`
  - `/app/reports/luckycommon-opensearch-upgrade-cost-analysis-2026-04-23.md`
  - `/app/LCNA-INC-2026-026-luckycommon-OpenSearch-RED-2026-05-17.docx`

---

*手册作者: 曾翔宇 (David Zeng) / Claude Code | 版本: v1.0 | 生成日期: 2026-05-18*
