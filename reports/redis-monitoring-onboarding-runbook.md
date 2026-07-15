# Runbook — 新建 AWS Redis (ElastiCache) 实例后接入监控

**用途**：每当新建一个 ElastiCache replication group（或继承一个未监控的集群），按此流程把它接入 Grafana 的 **AWS Redis Summary** 看板。
**归属**：DBA / Infrastructure — 曾翔宇 (David Zeng)
**主机**：所有操作在 **dbtools01-prod-usa-aws** 上
**最后更新**：2026-07-15
**关联记忆**：`aws-redis-summary-monitoring-onboarding`、`redis-grafana-dashboard`、`redis-cpu-credit-capacity`

---

## 0. 次序总览（TL;DR）

接入顺序**不能颠倒**——先配 exporter（含密码），再配 Prometheus，最后验证：

| 步骤 | 目录 | 改什么 | 是否重启 |
|------|------|--------|----------|
| **① redis_exporter** | `/data/redis-exporter/redis_exporter-v1.74.0.linux-amd64/` | `aws-redis-targets.json` 加 endpoint + `redis-password.file` 加密码 | **要重启 exporter**（密码文件启动时才读） |
| **② Prometheus** | `/data/prometheus-2.43.0.linux-amd64/` | `aws-redis-targets.json` 加 endpoint | 不重启（file_sd 热加载） |
| **③ 验证** | — | Prometheus targets / PromQL / 看板 | — |

> ⚠️ 两个目录各有一份 `aws-redis-targets.json`，**内容基本相同但有少许差异**（差异见 [§1.1](#11-两个-targets-文件的差异)，**待补充**）。两处都要加新集群。

---

## 1. 监控架构（先理解，再动手）

```
ElastiCache 集群 (primary endpoint, 带 AUTH token)
        │
        │  ① exporter 侧: aws-redis-targets.json (拨号目标) + redis-password.file (URI→密码)
        ▼
共享 redis_exporter  v1.74.0  监听 <host>:9321   (multi-target 模式，一个 exporter 服务所有集群)
   start.sh:  ./redis_exporter -skip-tls-verification -web.listen-address=":9321" \
              -redis.addr="" -redis.password-file=redis-password.file
        ▲
        │  ② Prometheus 侧: file_sd 读 aws-redis-targets.json，把 target 作为 ?target= 传给 exporter
        │     relabel: __address__ → __param_target → instance；__address__ 改写为 <host>:9321
        │
Prometheus 2.43.0  http://10.238.3.136:9090   (datasource uid r_ZpVoYHz)
   两个 job:  aws-redis_exporter (多目标 /scrape)  +  redis_exporter (抓 exporter 自身 :9321/metrics)
        │
        ▼
Grafana 看板
  · AWS Redis Summary   uid gy7wsBsnk   (DBA folder)  ← 概览，所有面板 UNFILTERED
  · AWS Redis Detail    uid kxTd1QEddd  (var-cluster 联动)  ← 单集群下钻
```

### 关键机制点
- **共享 exporter，多目标（multi-target）**：所有集群共用一个 `redis_exporter`（`:9321`）。exporter 以 `-redis.addr=""` 启动，靠 Prometheus 传来的 `?target=` 现场拨号。→ **新增集群不需要起新 exporter**，但**需要**把新集群的密码加进 exporter 的密码文件。
- **密码文件 `redis-password.file`**：JSON，`target URI → AUTH token`，**每集群一条**。exporter 按被抓的 target URI 查对应密码。**exporter 启动时读取该文件**，所以改完必须重启 exporter。
- **`instance` 标签 = 你填进 targets.json 的 endpoint URL**，例如
  `rediss://master.luckyus-isales-coupon.vyllrs.use1.cache.amazonaws.com:6379`
- **所有概览面板 UNFILTERED**（`redis_memory_max_bytes{} by(instance)` 之类），被抓到就自动出现。→ **"集群不在看板上" = "没抓到"**，永远不是看板过滤问题。
- **Prometheus file_sd 热加载**：`aws-redis-targets.json` 变更自动生效，**无需 SIGHUP / `/-/reload`**（几分钟内）。exporter 侧的密码文件**不是**热加载。

### 1.1 两个 targets 文件的差异
> **⚠️ 待补充**：exporter 目录与 prometheus 目录下的 `aws-redis-targets.json` 内容基本相同，但有少许差异。等确认具体差别后填入此处，避免两处直接照抄导致出错。

---

## 2. 前置信息采集

动手前拿到集群的**真实** endpoint、TLS 状态，以及**建集群时设定的 AUTH token**（token 不在 AWS 里能直接读，是创建时自设的，从你的记录/密码库取）。不要凭记忆猜 endpoint 里的随机 token（如 `vyllrs.use1`，每个 RG 唯一）。

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

确定三件事：
1. **主节点 endpoint**（`PrimaryEndpoint.Address`），形如 `master.luckyus-<service>.<token>.use1.cache.amazonaws.com`。用 API 返回值，别手拼。
2. **是否 TLS**（`TransitEncryptionEnabled`）：`true` → `rediss://`（两个 s）；`false` → `redis://`。
3. **是否开 AUTH**（`AuthTokenEnabled`）+ 手上准备好 **AUTH token**（建集群时自设）。若无 AUTH，密码留空。

拼出 target 字符串（后面两个文件都用它）：
```
TLS 集群:   rediss://<PrimaryEndpoint>:6379
非 TLS 集群: redis://<PrimaryEndpoint>:6379
```

---

## 3. 步骤 ① — 配置 redis_exporter

目录：`/data/redis-exporter/redis_exporter-v1.74.0.linux-amd64/`

### 3.1 备份
```bash
cd /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64
cp aws-redis-targets.json aws-redis-targets.json.bak.$(date +%Y%m%d-%H%M%S)
cp redis-password.file   redis-password.file.bak.$(date +%Y%m%d-%H%M%S)
```

### 3.2 加 target endpoint
往 `aws-redis-targets.json` 的 `targets` 数组追加第 2 节拼好的 URL。用 Python 改，避免手抖漏逗号（一个语法错误会让整份文件解析失败、拖垮所有集群）：
```bash
python3 - <<'PY'
import json
f = "aws-redis-targets.json"
new_target = "rediss://master.luckyus-<service>.<token>.use1.cache.amazonaws.com:6379"  # ← 改这里
data = json.load(open(f))
block = data[0]                              # 结构: [ {targets:[...], labels:{...}} ]
if new_target not in block["targets"]:
    block["targets"].append(new_target)
    block["targets"].sort()
    json.dump(data, open(f, "w"), indent=2)
    print("ADDED:", new_target)
else:
    print("ALREADY PRESENT:", new_target)
PY
python3 -m json.tool aws-redis-targets.json >/dev/null && echo "JSON OK"
```

### 3.3 加密码到 redis-password.file
`redis-password.file` 是 **JSON，key = target URI，value = AUTH token，每集群一条**。key 必须和 3.2 填的 target 字符串**完全一致**（含 `rediss://` 前缀和 `:6379`），否则 exporter 拨号时找不到密码、AUTH 失败。
```bash
python3 - <<'PY'
import json
f = "redis-password.file"
uri   = "rediss://master.luckyus-<service>.<token>.use1.cache.amazonaws.com:6379"  # ← 与 3.2 完全一致
token = "<AUTH-TOKEN-建集群时自设>"                                                  # ← 无 AUTH 则填 ""
data = json.load(open(f))
data[uri] = token
json.dump(data, open(f, "w"), indent=2)
print("SET password for:", uri)
PY
python3 -m json.tool redis-password.file >/dev/null && echo "JSON OK"
```
> 密码文件内容含明文 token，注意文件权限（应仅 root 可读）；本 runbook 及任何提交/日志里**不要**回显真实 token。

### 3.4 重启 exporter（密码文件启动时才读，必须重启）
```bash
# 找到并停掉旧进程
pgrep -af 'redis_exporter .*:9321'
kill "$(pgrep -f 'redis_exporter .*-web.listen-address=":9321"')"
sleep 2
# 按 start.sh 重新拉起
./start.sh
# 确认监听恢复
sleep 2 && curl -s http://localhost:9321/metrics | head -1 && echo "exporter up"
```
> 重启期间 `:9321` 短暂中断 → 所有集群的 `redis_*` 指标会有一个抓取周期的缺口，属正常。挑低峰做。

---

## 4. 步骤 ② — 配置 Prometheus

目录：`/data/prometheus-2.43.0.linux-amd64/`

```bash
cd /data/prometheus-2.43.0.linux-amd64
cp aws-redis-targets.json aws-redis-targets.json.bak.$(date +%Y%m%d-%H%M%S)
```
把同一个 target endpoint 追加到**这个目录**的 `aws-redis-targets.json`（注意 [§1.1](#11-两个-targets-文件的差异) 两文件的少许差异）：
```bash
python3 - <<'PY'
import json
f = "aws-redis-targets.json"
new_target = "rediss://master.luckyus-<service>.<token>.use1.cache.amazonaws.com:6379"  # ← 同上
data = json.load(open(f))
block = data[0]
if new_target not in block["targets"]:
    block["targets"].append(new_target); block["targets"].sort()
    json.dump(data, open(f, "w"), indent=2); print("ADDED")
else:
    print("ALREADY PRESENT")
PY
python3 -m json.tool aws-redis-targets.json >/dev/null && echo "JSON OK"
```
**不需要**重启 Prometheus，也不发 `/-/reload`——file_sd 自动热加载，几分钟内生效。

---

## 5. 步骤 ③ — 验证

### 5.1 Prometheus target UP
`http://10.238.3.136:9090/targets` → job `aws-redis_exporter` → 新 endpoint 应 `UP`。或 PromQL：
```promql
up{job="aws-redis_exporter", instance=~".*luckyus-<service>.*"}          # 期望 1
```

### 5.2 指标在流入（说明 AUTH 通了）
```promql
redis_up{instance=~".*luckyus-<service>.*"}                # 1 = 连上且认证成功
redis_memory_used_bytes{instance=~".*luckyus-<service>.*"}
redis_db_keys{instance=~".*luckyus-<service>.*"}
```
> `up=1` 但 `redis_up=0` / 无 `redis_*` 指标 → 多半是**密码错/没加/URI 不匹配**（回到 3.3 核对 key 与 target 完全一致，并确认 3.4 已重启 exporter）。

### 5.3 看板确认
打开 **AWS Redis Summary**（uid `gy7wsBsnk`）。面板 UNFILTERED，新集群自动出现。下钻用 **AWS Redis Detail**（uid `kxTd1QEddd`），`var-cluster` 选新集群。`instance` 是完整 URL，看板已用 `label_replace(...,"instance",".*?(luckyus-[a-z0-9-]+?)\\..*")` 清洗成短名。

---

## 6. 常见坑（真实踩过的）

| 现象 | 根因 | 处理 |
|------|------|------|
| `up=1` 但没有 `redis_*` 指标 / `redis_up=0` | 密码文件没加、token 错、或 key 与 target URI 不一致；或改了密码文件没重启 exporter | 核对 `redis-password.file` 的 key == targets 的 URL（含 `rediss://` 与 `:6379`）；重跑 3.4 重启 exporter |
| 加了还是"看不到"，找 `coupondata` 找不到 | **命名不一致**：真实 RG 名是 `luckyus-isales-coupon`（连字符），不是别名/下划线 | 命名一律 `luckyus-<service>` 连字符；以 `ReplicationGroupId` 为准 |
| 某 target 永久 `up=0`，DNS 解析失败 | endpoint 字符串有**尾随空格**（如 `...luckyus-iopenlinkeradmin .vyllrs...`） | 去掉空格；粘贴时警惕行尾空白 |
| 编辑后**所有**集群一起掉 | 某个 json 语法错（漏/多逗号），file_sd 或 exporter 解析失败丢弃整份文件 | 两份文件都过 `python3 -m json.tool`；用脚本改而非手改；有 `.bak` 回滚 |
| target UP 但看板短时无数据 | cloudwatch-exporter 侧 `aws_elasticache_*` 有 5–10min 延迟；瞬时查询撞 5m staleness | 等几分钟；Top-N 瞬时表用 `last_over_time(<sel>[15m])` |
| 选中集群 CPU 积分面板 "No data" | 该集群**非 burstable**（如 `luckyus-isales-market` = `m6g.large`），无 CPU-credit 机制 | 正常，非 bug。只有 T3/T4g 有积分指标 |

---

## 7. 补充：CPU 积分与其它口径

- 本 runbook 只覆盖 **AWS Redis Summary** 看板（Prometheus `redis_exporter` 口径）。
- **CPU 积分（CPU Credits）** 不在 Prometheus，走 `ldas` MySQL 采集表 `t_dba_collect_redis_cluster_metrics`（`collect_cloudwatch.py --tasks redis_metrics --write` 喂）。新集群要在自建 unified 看板上出积分，需采集器配置带上它并跑一次。详见 `redis-grafana-dashboard` / `redis-cpu-credit-capacity`。
- 建议告警（避开生命周期误报）：`CPUCreditBalance < 50(micro)/100(small)` **且** `CPUUtilization > baseline` 持续 1h。刚 failover/重建的节点从 0 积分起充（~9.4/hr 净充），非过载——用 `describe-events` 交叉验证。

---

## 8. 检查清单（Checklist）

前置
- [ ] `describe-replication-groups` 拿到真实 endpoint + TLS 状态 + AuthTokenEnabled
- [ ] 手上有该集群的 AUTH token（建集群时自设）
- [ ] 按 TLS 选对 `rediss://` / `redis://`，端口 6379

① redis_exporter（`/data/redis-exporter/redis_exporter-v1.74.0.linux-amd64/`）
- [ ] 备份 `aws-redis-targets.json` + `redis-password.file`
- [ ] `aws-redis-targets.json` 追加 endpoint（无尾随空格）→ json.tool 通过
- [ ] `redis-password.file` 追加 `URI:token`（key 与 target 完全一致）→ json.tool 通过
- [ ] **重启 exporter**（kill + `./start.sh`），`:9321/metrics` 恢复

② Prometheus（`/data/prometheus-2.43.0.linux-amd64/`）
- [ ] 备份并在**该目录**的 `aws-redis-targets.json` 追加 endpoint（留意 §1.1 差异）→ json.tool 通过
- [ ] 不 reload，等 file_sd 热加载

③ 验证
- [ ] `up{job="aws-redis_exporter"}=1` 且 `redis_up=1`
- [ ] 集群出现在 AWS Redis Summary 看板
- [ ] （如需积分）另走 ldas 采集器口径接入
