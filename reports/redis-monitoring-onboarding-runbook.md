# Runbook — 新建 AWS Redis (ElastiCache) 实例后接入监控

**用途**：每当新建一个 ElastiCache replication group（或继承一个未监控的集群），按此流程把它接入 Grafana 的 **AWS Redis Summary** 看板。
**归属**：DBA / Infrastructure — 曾翔宇 (David Zeng)
**主机**：所有操作在 **dbtools01-prod-usa-aws** 上
**最后更新**：2026-07-15
**关联记忆**：`aws-redis-summary-monitoring-onboarding`、`redis-grafana-dashboard`、`redis-cpu-credit-capacity`
**配套脚本**：`./scripts/sync_redis_monitoring.py`（一站式维护三文件，替代旧的 aws-redis.py / diff.py / target_diff.py）

---

## 0. 一句话流程（TL;DR）

> **你只手工维护一个文件 `redis-password.file`——加一行 `{uri: token}`，其余交给脚本。**

```bash
cd /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64
# 1. 手工：往 redis-password.file 加一行（uri 前缀 = 真实 TLS）
# 2. 预演（不写文件）
python3 sync_redis_monitoring.py
# 3. 确认无误后写回两个 targets 文件
python3 sync_redis_monitoring.py --apply
# 4. 因为改了密码文件 → 重启 exporter
kill "$(pgrep -f 'redis_exporter .*-web.listen-address=\":9321\"')"; ./start.sh
# 5. 验证（PromQL + 看板，见 §4）
```

Prometheus 侧不用动手、不用 reload——脚本直接写好它的 targets 文件，file_sd 自动热加载。

---

## 1. 监控架构与三文件模型

### 1.1 数据流
```
ElastiCache 集群 (primary endpoint, 带 AUTH token)
        │
        │  redis-password.file  ← 唯一手工维护的文件 {uri: token}，uri 前缀=真实 TLS
        │        │
        │        └── sync_redis_monitoring.py 派生 ↓↓↓
        │
   ┌────┴──────────────────────────────┐
   │ exporter aws-redis-targets.json    │  全部 rediss://（去重排序）
   │ prometheus aws-redis-targets.json  │  原样前缀 redis://redis://
   └───────────────────────────────────┘
        ▼
共享 redis_exporter v1.74.0  <host>:9321  (multi-target；-redis.addr="" -redis.password-file=redis-password.file)
        ▲
        │  Prometheus file_sd 读 prometheus 侧 targets，把 target 作为 ?target= 传给 exporter
        │  relabel: __address__ → __param_target → instance；__address__ 改写为 <host>:9321
        │
Prometheus 2.43.0  http://10.238.3.136:9090  (datasource uid r_ZpVoYHz)
   job: aws-redis_exporter (多目标 /scrape) + redis_exporter (抓自身 :9321/metrics)
        ▼
Grafana:  AWS Redis Summary uid gy7wsBsnk (概览, UNFILTERED)  ·  AWS Redis Detail uid kxTd1QEddd (下钻)
```

### 1.2 三个文件 + 前缀规则（关键）

| 文件 | 位置 | 前缀 | 谁来维护 |
|------|------|------|----------|
| **redis-password.file** | exporter 目录 | key 前缀 = **真实 TLS**：加密 `rediss://` / 非加密 `redis://` | **手工**（唯一源） |
| exporter `aws-redis-targets.json` | exporter 目录 | **一律 `rediss://`** | 脚本生成 |
| prometheus `aws-redis-targets.json` | `/data/prometheus-2.43.0.../` | **按真实 TLS**：`redis://` / `rediss://` | 脚本生成 |

**为什么 exporter 全 `rediss://`、Prometheus 分前缀？**
- Prometheus 侧 target 决定 `instance` 标签，也决定 exporter 实际用不用 TLS 拨号 → 必须反映真实 TLS。
- exporter 那份 targets 不参与实际拨号（拨号目标由 Prometheus 的 `?target=` 传入），历史上仅作密码覆盖核对，故统一 `rediss://` 无妨。
- **TLS 状态只能人工判定**：CMDB 表 `cache_cloud_app` 无 TLS 列（已确认），所以由你在密码文件 key 的前缀里编码。脚本据此把前缀正确地铺到两个 targets 文件。

### 1.3 脚本 `sync_redis_monitoring.py` 做什么
1. 读 `redis-password.file`（唯一源）。
2. 自检：同一 host 多前缀重复、空密码计数。
3. **旁路校验**（可选，需 `LDAS_PWD`）：对照 ldas `cache_cloud_app(app_status=1)`，报「在营却没进密码文件」和「密码文件里已下线的僵尸项」。
4. 生成并写回两个 targets 文件：exporter 全 `rediss://`、prometheus 原样前缀；写前自动 `.bak` 备份，无变化则跳过。
5. 默认 **dry-run**（只报告不写）；加 `--apply` 才写。

> 旧脚本 `aws-redis.py`（从 CMDB 生成 exporter targets，全 rediss://）、`diff.py`、`target_diff.py` 已被本脚本取代——生成 + 两项一致性校验合一。

---

## 2. 前置信息采集

拿到集群 endpoint、TLS 状态、AUTH token（token 建集群时自设，AWS 里读不到，从记录/密码库取）。

```bash
aws elasticache describe-replication-groups \
  --region us-east-1 \
  --replication-group-id luckyus-<service> \
  --query 'ReplicationGroups[0].{
      Name:ReplicationGroupId,
      TLS:TransitEncryptionEnabled,
      AuthEnabled:AuthTokenEnabled,
      PrimaryEndpoint:NodeGroups[0].PrimaryEndpoint.Address,
      Port:NodeGroups[0].PrimaryEndpoint.Port
  }'
```
- `TransitEncryptionEnabled=true` → 密码文件 key 用 `rediss://`；`false` → 用 `redis://`。
- endpoint 用 API 返回值（`vyllrs.use1` 这类 token 每 RG 唯一，别手拼）。

---

## 3. 接入操作

目录：`/data/redis-exporter/redis_exporter-v1.74.0.linux-amd64/`

### 3.1 手工加一行到 redis-password.file（唯一手工步骤）
JSON `{uri: token}`，一集群一条。**前缀按真实 TLS**，key 的 host:port 必须与 endpoint 完全一致：
```jsonc
{
  // 加密集群（有 AUTH token）
  "rediss://master.luckyus-<service>.<token>.use1.cache.amazonaws.com:6379": "<AUTH-TOKEN>",
  // 非加密 / 无 AUTH 集群 → 前缀 redis://，token 留空串
  "redis://master.luckyus-<plainsvc>.<token>.use1.cache.amazonaws.com:6379": ""
}
```
> 密码文件含明文 token → 文件权限仅 root 可读；本 runbook / 提交 / 日志里**不要**回显真实 token。

### 3.2 预演（dry-run，不写文件）
```bash
cd /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64
LDAS_PWD='<ldas只读密码>' python3 sync_redis_monitoring.py     # 带 LDAS_PWD 才做 CMDB 旁路校验
```
看输出：确认新集群会被加入、无重复、CMDB 校验无 `[!]` 缺失项，两个文件的项数变化符合预期（各 +1）。

### 3.3 写回
```bash
LDAS_PWD='<ldas只读密码>' python3 sync_redis_monitoring.py --apply
```
脚本会给两个 targets 文件各生成 `.bak` 后写入。Prometheus file_sd 自动热加载，**无需 reload**。

### 3.4 重启 exporter（因为改了密码文件）
密码文件启动时才读，改了必须重启：
```bash
pgrep -af 'redis_exporter .*:9321'
kill "$(pgrep -f 'redis_exporter .*-web.listen-address=\":9321\"')"
sleep 2 && ./start.sh
sleep 2 && curl -s http://localhost:9321/metrics | head -1 && echo "exporter up"
```
> 重启期间 `:9321` 短暂中断 → 所有集群 `redis_*` 指标有一个抓取周期缺口，属正常，挑低峰做。

---

## 4. 验证

### 4.1 target UP + 指标流入
```promql
up{job="aws-redis_exporter", instance=~".*luckyus-<service>.*"}       # 1
redis_up{instance=~".*luckyus-<service>.*"}                            # 1 = 连上且认证成功
redis_memory_used_bytes{instance=~".*luckyus-<service>.*"}
```
`up=1` 但 `redis_up=0` / 无 `redis_*` → 密码错、前缀不匹配、或改密码后没重启 exporter。核对密码文件、重跑 §3.4。

### 4.2 看板
**AWS Redis Summary**（uid `gy7wsBsnk`）面板 UNFILTERED，新集群自动出现；下钻用 **AWS Redis Detail**（uid `kxTd1QEddd`）`var-cluster` 选它。`instance` 是完整 URL，看板已 `label_replace` 清洗成短名。

---

## 5. 常见坑

| 现象 | 根因 | 处理 |
|------|------|------|
| `up=1` 但无 `redis_*` / `redis_up=0` | 密码错/前缀不匹配；改密码后没重启 exporter | 核对 `redis-password.file`；重跑 §3.4 |
| Prometheus 抓不到、但你以为加了 | 只改了密码文件没跑 `--apply`（targets 没重生成） | 跑 `sync_redis_monitoring.py --apply` |
| 脚本报「同一 host 多前缀重复」 | 密码文件里同一 host 既有 `redis://` 又有 `rediss://` | 一个 host 只留一条（按真实 TLS） |
| 脚本 CMDB 校验报 `[!]` 缺失 | 在营实例还没进密码文件 | 补 §3.1 那一行 |
| 脚本 CMDB 校验报 `[?]` 僵尸 | 密码文件里的实例已在 CMDB 下线 | 从密码文件删掉该条再 `--apply` |
| 找 `coupondata` 找不到 | 命名不一致：真实 RG 名 `luckyus-isales-coupon`（连字符） | 以 `ReplicationGroupId` 为准 |
| 某 target 永久 `up=0`，DNS 失败 | key 里有**尾随空格** | 去空格；粘贴警惕行尾空白 |
| 选中集群 CPU 积分面板 "No data" | 集群非 burstable（如 `isales-market` = `m6g.large`），无积分机制 | 正常，仅 T3/T4g 有积分 |

---

## 6. 补充：CPU 积分与其它口径

- 本 runbook 只覆盖 **AWS Redis Summary** 看板（Prometheus `redis_exporter` 口径）。
- **CPU 积分** 不在 Prometheus，走 `ldas` 采集表 `t_dba_collect_redis_cluster_metrics`（`collect_cloudwatch.py --tasks redis_metrics --write` 喂）。详见 `redis-grafana-dashboard` / `redis-cpu-credit-capacity`。
- 建议告警：`CPUCreditBalance < 50(micro)/100(small)` 且 `CPUUtilization > baseline` 持续 1h；failover/重建节点从 0 积分起充非过载，用 `describe-events` 交叉验证。

---

## 7. 检查清单

- [ ] `describe-replication-groups` 拿到 endpoint + TransitEncryptionEnabled + AUTH token
- [ ] `redis-password.file` 加一行 `{uri: token}`：**加密 `rediss://` / 非加密 `redis://`**，token（无 AUTH 填 `""`），host:port 与 endpoint 一致，无尾随空格
- [ ] `sync_redis_monitoring.py`（dry-run）：新集群将被加入、无重复、CMDB 无 `[!]`、项数 +1
- [ ] `sync_redis_monitoring.py --apply`：两个 targets 文件已备份并写回
- [ ] **重启 exporter**（kill + `./start.sh`），`:9321/metrics` 恢复
- [ ] `up{job="aws-redis_exporter"}=1` 且 `redis_up=1`
- [ ] 集群出现在 AWS Redis Summary 看板
- [ ] （如需积分）另走 ldas 采集器口径接入

---

## 附录：脚本

`scripts/sync_redis_monitoring.py` — 一站式维护三文件。
- 源：`redis-password.file`（手工）；派生：exporter 全 `rediss://` + prometheus 真实前缀。
- 校验：密码文件自检 + ldas `cache_cloud_app` 旁路校验（需 `LDAS_PWD`）。
- 默认 dry-run，`--apply` 才写；写前 `.bak` 备份。
- 顶部 4 个路径常量按主机实际调整；ldas 密码走环境变量 `LDAS_PWD`，不硬编码。

（主机原件在 `/data/redis-exporter/redis_exporter-v1.74.0.linux-amd64/`。）
