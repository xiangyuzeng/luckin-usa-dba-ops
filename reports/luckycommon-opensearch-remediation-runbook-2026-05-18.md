# luckycommon OpenSearch 配置整改执行手册

**集群**: luckycommon (AWS OpenSearch / Elasticsearch 6.8)
**账号**: 257394478466 (us-east-1)
**VPC**: vpc-0dce7ca7770422d33
**负责人**: 曾翔宇 (David Zeng)
**生成日期**: 2026-05-18
**关联事件**: LCNA-INC-2026-008 (3/8), 2026-04-20, LCNA-INC-2026-026 (5/17)

---

## 一、变更概述

本手册覆盖 **6 项配置级整改措施**（仅修改集群配置和 ISM 策略，不变更实例规格、副本存储扩容等资源），分两批执行：

| 阶段 | 编号 | 措施 | 风险 | 预计耗时 |
|---|---|---|---|---|
| **P0** | 1 | VPC 内 REST API 访问通道 | 低 | 30 min |
| **P0** | 2 | 18 个主分片添加副本 | 中（产生数据复制 I/O） | 30–60 min |
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

## 二、前置检查（执行任何步骤前必做）

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

## 三、P0 措施执行（本周内，UTC 02:00–05:00 窗口）

### P0-1: 打通 VPC 内 REST API 访问通道

**目标**: 让 DBA 能从内网调用 `_cluster/*`、`_cat/*`、`_opendistro/_ism/*` 等 API，否则后续所有步骤无法执行。

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

### P0-2: 给 18 个无副本主分片添加副本

**目标**: 消除 0 副本分片这一 RED 触发器最大单点。

**前置确认**：

```bash
# 步骤 1: 列出所有 0 副本索引
awscurl --service es --region us-east-1 \
  "https://${ENDPOINT}/_cat/indices?h=index,pri,rep,docs.count,store.size&v" \
  | awk 'NR==1 || $3==0' \
  | tee zero-replica-indices.txt

# 步骤 2: 确认数量与上次报告一致（~18 个）
ZERO_REPLICA_COUNT=$(awk 'NR>1' zero-replica-indices.txt | wc -l)
echo "Zero-replica indices count: $ZERO_REPLICA_COUNT"

# 步骤 3: 估算新增存储需求（应 < 现有 EBS 余量 177 GB）
awk 'NR>1 {gsub(/gb|mb|kb/,"",$5); sum+=$5} END {print "Estimated additional storage: " sum " (units mixed - 复核)"}' zero-replica-indices.txt
```

**通过标准**：
- 数量在 15–25 区间（与历史报告一致）
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

# 批量给 0 副本索引加副本
while read -r INDEX; do
  [ -z "$INDEX" ] && continue
  echo "Setting replicas=1 on $INDEX"
  awscurl --service es --region us-east-1 \
    -X PUT \
    -H "Content-Type: application/json" \
    -d '{"index": {"number_of_replicas": 1}}' \
    "https://${ENDPOINT}/${INDEX}/_settings"
  sleep 5  # 给集群留缓冲，避免一次性发起所有复制
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

**目标**: 避免 ISM 一次性删除 >5GB / >100 万文档导致节点超载（3/8 RED 直接根因）。

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

## 四、P1 措施执行（两周内，任意时段）

### P1-4: 启用 AutoTune

**目标**: 让 AWS 自动调优 JVM 参数和查询缓存设置，缓解慢性 JVM 锯齿波（74–76% 峰值）。

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

**目标**: 让 merge I/O 上限更高，缩短删除后段合并窗口（25–49 min → <5 min）。

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

**目标**: 防止未来再有新索引以 0 副本创建（治本，防止 P0-2 整改后又出现新的 0 副本索引）。

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

## 五、完整验证清单（全部执行后）

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

## 六、回滚方案

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

## 七、风险评估

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

## 八、变更后观察期

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

## 九、变更日志（执行时填写）

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
