# Runbook — 新建 AWS Redis (ElastiCache) 实例后接入监控

**用途**：每当新建一个 ElastiCache replication group（或从别处继承一个未监控的集群），按此流程把它接入 Grafana 的 **AWS Redis Summary** 看板。
**归属**：DBA / Infrastructure — 曾翔宇 (David Zeng)
**最后更新**：2026-07-15
**关联记忆**：`aws-redis-summary-monitoring-onboarding`、`redis-grafana-dashboard`、`redis-cpu-credit-capacity`

---

## 0. 一句话结论（TL;DR）

> **接入 = 往 dbtools01 的 `aws-redis-targets.json` 里追加一行 ElastiCache 主节点 endpoint，存盘即可。**
> 不需要新建 exporter、不需要改 job、不需要 reload Prometheus、不需要改 Grafana 看板。file_sd 会在几分钟内自动热加载。

如果你只想快速做完，直接跳到 [第 3 节：操作步骤](#3-操作步骤)。其余章节解释为什么这样做以及怎么排错。

---

## 1. 监控架构（先理解，再动手）

看板数据流是**单向、无过滤**的，所以任何"看不到集群"的问题都只可能出在抓取端，绝不是看板端。

```
ElastiCache 集群 (primary endpoint)
        │
        │  aws-redis-targets.json  (targets 数组，dbtools01 上)
        ▼
Prometheus  aws-redis-job   ── file_sd_configs 读该 json
  (dbtools01-prod-usa-aws)     metrics_path=/scrape
        │                      relabel: __address__ → __param_target → instance
        │                      __address__ 改写为共享 exporter 10.238.3.136:9321
        ▼
共享 redis_exporter  10.238.3.136:9321   (multi-target 模式，一个 exporter 服务所有集群)
        │  实际拨号连到 endpoint，拉 redis_* 指标
        ▼
Prometheus-DB  http://10.238.3.136:9090   (datasource uid r_ZpVoYHz)
        │
        ▼
Grafana 看板
  · AWS Redis Summary   uid gy7wsBsnk   (DBA folder)  ← 概览，所有面板 UNFILTERED
  · AWS Redis Detail    uid kxTd1QEddd  (var-cluster 联动)  ← 单集群下钻
```

### 关键机制点
- **共享 exporter，多目标（multi-target）**：所有集群共用一个 `redis_exporter`（`10.238.3.136:9321`）。Prometheus 把目标 endpoint 作为 `?target=` 参数传给它，exporter 现场去拨号。**所以新增集群不需要起新 exporter。**
- **`instance` 标签 = 你填进 json 的 endpoint URL**，例如
  `rediss://master.luckyus-isales-coupon.vyllrs.use1.cache.amazonaws.com:6379`
- **所有概览面板都是 UNFILTERED**（`redis_memory_max_bytes{} by(instance)` 之类）。任何被抓到的 target 会自动出现在看板上。→ **"集群不在看板上" 永远等于 "Prometheus 没抓到它"，不是看板过滤问题。**
- **file_sd 热加载**：`aws-redis-targets.json` 是 `file_sd_configs` 源，Prometheus 自动侦测文件变更，**无需 SIGHUP / `/-/reload`**，几分钟内生效。

---

## 2. 前置信息采集

动手前先拿到集群的**真实** endpoint 和 TLS 状态。不要凭记忆猜 endpoint 里的随机 token（如 `vyllrs.use1`，它是**每个 replication group 唯一**的）。

```bash
aws elasticache describe-replication-groups \
  --region us-east-1 \
  --replication-group-id luckyus-<service> \
  --query 'ReplicationGroups[0].{
      Name:ReplicationGroupId,
      TLS:TransitEncryptionEnabled,
      PrimaryEndpoint:NodeGroups[0].PrimaryEndpoint.Address,
      Port:NodeGroups[0].PrimaryEndpoint.Port
  }'
```

从输出确定两件事：
1. **主节点 endpoint 地址**（`PrimaryEndpoint.Address`），形如 `master.luckyus-<service>.<token>.use1.cache.amazonaws.com`。
   - 注意：新版 ElastiCache 主 endpoint 常是 `master.<rg>...`；也可能返回 `clustercfg.<rg>...`（cluster-mode）。用 API 返回值，别手拼。
2. **是否开启传输加密**（`TransitEncryptionEnabled`）：
   - `true`  → 用 `rediss://`（两个 s，TLS）
   - `false` → 用 `redis://`（一个 s，明文）

拼出最终 target 字符串：

```
TLS 集群:   rediss://<PrimaryEndpoint>:6379
非 TLS 集群: redis://<PrimaryEndpoint>:6379
```

---

## 3. 操作步骤

> 在 **dbtools01-prod-usa-aws** 上操作（Prometheus + 共享 exporter 所在主机）。
> 目标文件：`prometheus-2.43.0.linux-amd64/aws-redis-targets.json`（与 `prometheus.yml` 同目录，`prometheus.yml` 第 ~41 行 `file_sd_configs` 引用它）。

### 3.1 备份并查看现有目标
```bash
cd ~/prometheus-2.43.0.linux-amd64      # 路径以现场为准
cp aws-redis-targets.json aws-redis-targets.json.bak.$(date +%Y%m%d-%H%M%S)
python3 -m json.tool aws-redis-targets.json | head -50
```

文件结构类似（file_sd 标准格式）：
```json
[
  {
    "targets": [
      "rediss://master.luckyus-isales-coupon.vyllrs.use1.cache.amazonaws.com:6379",
      "redis://master.luckyus-someservice.abcdef.use1.cache.amazonaws.com:6379"
    ],
    "labels": { "job": "aws-redis-job" }
  }
]
```
（现场可能是单个对象或多对象数组；只需往 `targets` 数组里加字符串。）

### 3.2 追加新集群 endpoint
把第 2 节拼好的字符串加进 `targets` 数组。**手工编辑后务必用 JSON 校验**，一个漏掉的逗号会让整个文件解析失败、拖垮所有集群的抓取。

安全的做法（用 Python 改，避免手抖）：
```bash
python3 - <<'PY'
import json, io
f = "aws-redis-targets.json"
new_target = "rediss://master.luckyus-<service>.<token>.use1.cache.amazonaws.com:6379"  # ← 改这里
data = json.load(open(f))
# 结构可能是 [ {targets:[...], labels:{...}} ]，取第一个块的 targets
block = data[0]
if new_target not in block["targets"]:
    block["targets"].append(new_target)
    block["targets"].sort()            # 保持有序，便于 review
    json.dump(data, open(f, "w"), indent=2)
    print("ADDED:", new_target)
else:
    print("ALREADY PRESENT:", new_target)
PY
python3 -m json.tool aws-redis-targets.json >/dev/null && echo "JSON OK"
```

### 3.3 等待热加载（无需 reload）
file_sd 会自动感知文件变更。几分钟后验证（见第 4 节）。**不要**重启 Prometheus，也不要发 `/-/reload`——多余且有中断风险。

---

## 4. 验证接入成功

### 4.1 看 Prometheus target 是否 up
Targets 页面：`http://10.238.3.136:9090/targets` → 找 `aws-redis-job` → 新 endpoint 应 `UP`。

或用 PromQL（prometheus MCP / Grafana Explore）：
```promql
up{job="aws-redis-job", instance=~".*luckyus-<service>.*"}
```
期望 `= 1`。

### 4.2 确认指标在流入
```promql
redis_up{instance=~".*luckyus-<service>.*"}
redis_memory_used_bytes{instance=~".*luckyus-<service>.*"}
redis_db_keys{instance=~".*luckyus-<service>.*"}
```

### 4.3 看板确认
打开 **AWS Redis Summary**（uid `gy7wsBsnk`）。因所有面板 UNFILTERED，新集群应自动出现在各 Top-N / by(instance) 面板里。下钻用 **AWS Redis Detail**（uid `kxTd1QEddd`），`var-cluster` 选新集群。

`instance` 标签是完整 URL；看板已用
`label_replace(<v>,"instance","$1","instance",".*?(luckyus-[a-z0-9-]+?)\\..*")`
清洗成短名，不用管。

---

## 5. 常见坑（昨天真实踩过的）

| 现象 | 根因 | 处理 |
|------|------|------|
| 加了还是"看不到"，找 `coupondata` 找不到 | **命名不一致**：真实 RG 名是 `luckyus-isales-coupon`（连字符），不是下划线/别名 | 命名规范一律 `luckyus-<service>`，用连字符；以 `describe-replication-groups` 返回的 `ReplicationGroupId` 为准 |
| 某 target 永久 `up=0`，DNS 解析失败 | endpoint 字符串里有**尾随空格**（如 `...luckyus-iopenlinkeradmin .vyllrs...`），DNS 拿不到该主机 | 去掉空格。粘贴时特别小心行尾/多余空白 |
| 编辑后**所有**集群一起掉 | json 语法错误（漏逗号/多逗号），file_sd 解析失败整个文件被丢弃 | `python3 -m json.tool` 校验；用 3.2 的 Python 脚本改而非手改；有 `.bak` 可回滚 |
| target UP 但看板短时无数据 | cloudwatch-exporter 侧指标（`aws_elasticache_*`）有 5–10 分钟延迟；瞬时查询命中 Prometheus 5m staleness | 等几分钟；Top-N 瞬时表用 `last_over_time(<sel>[15m])` 兜底 |
| 选中集群 CPU 积分面板 "No data" | 该集群是 **非 burstable**（如 `luckyus-isales-market` = `m6g.large`），无 CPU-credit 机制，CloudWatch 不产 `CPUCreditBalance` | 正常现象，不是 bug。只有 T3/T4g 才有积分指标 |

---

## 6. 补充：CPU 积分与其它监控口径

- 本 runbook 只覆盖 **AWS Redis Summary** 看板（Prometheus `redis_exporter` 口径）的接入。
- **CPU 积分（CPU Credits）** 不在 Prometheus 里，走 `ldas` MySQL 采集表 `t_dba_collect_redis_cluster_metrics`（由 `collect_cloudwatch.py --tasks redis_metrics --write` 喂）。新集群积分要出现在自建的 unified 看板上，需采集器配置里带上它并跑一次。详见记忆 `redis-grafana-dashboard` / `redis-cpu-credit-capacity`。
- 建议告警（避开生命周期误报）：`CPUCreditBalance < 50(micro)/100(small)` **且** `CPUUtilization > baseline` 持续 1h。刚 failover/重建的节点从 0 积分起充（~9.4/hr 净充），不是过载 —— 务必用 `describe-events` 交叉验证。

---

## 7. 检查清单（Checklist）

- [ ] `describe-replication-groups` 拿到真实 endpoint + TLS 状态
- [ ] 按 TLS 选对 `rediss://` / `redis://` 前缀，端口 6379
- [ ] 备份 `aws-redis-targets.json`
- [ ] 追加 endpoint（用 Python 脚本），**无尾随空格**
- [ ] `python3 -m json.tool` 校验通过
- [ ] 不做 reload，等待 file_sd 热加载
- [ ] `up{job="aws-redis-job"}=1` 且 `redis_up=1`
- [ ] 集群出现在 AWS Redis Summary 看板
- [ ] （如需积分）确认走 ldas 采集器口径另行接入
