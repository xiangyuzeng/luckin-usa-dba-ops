# Runbook — 新建 AWS Redis (ElastiCache) 实例后接入监控

**用途**：新建 ElastiCache 集群后，把它接入 Grafana 的 **AWS Redis Summary** 看板。
**归属**：DBA / Infrastructure — 曾翔宇 (David Zeng)
**主机**：所有操作在 **dbtools01-prod-usa-aws** 上
**最后更新**：2026-07-15
**关联记忆**：`aws-redis-summary-monitoring-onboarding`、`redis-grafana-dashboard`、`redis-cpu-credit-capacity`
**配套脚本**：`./scripts/sync_redis_monitoring.py`（全自动生成三文件，替代旧 aws-redis.py / diff.py / target_diff.py）

---

## 0. 一句话流程（TL;DR）

> **监控三文件全自动生成，零手工编辑。** 只要集群已建好、且已登记进 ldas `cache_cloud_app`（在营、带密码），跑一条命令即可。

```bash
cd /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64
LDAS_PWD='<ldas只读密码>' python3 sync_redis_monitoring.py           # 预演：拉数据+join+报告，不写
LDAS_PWD='<ldas只读密码>' python3 sync_redis_monitoring.py --apply    # 备份后写回三文件
kill "$(pgrep -f 'redis_exporter .*-web.listen-address=\":9321\"')"; ./start.sh   # 密码文件变了才需重启
# 验证：见 §4
```

---

## 1. 全自动原理

监控三文件**不再手工维护**，由脚本从两个权威数据源 join 生成：

| 数据源 | 提供 | 取法 |
|--------|------|------|
| **AWS ElastiCache** | 每集群 endpoint + **是否 TLS**（`TransitEncryptionEnabled`）+ **是否 AUTH**（`AuthTokenEnabled`） | `describe-replication-groups`（`databasecheck` 有读权限） |
| **ldas CMDB** `luckyus_ozono.cache_cloud_app` | 每在营实例 `host_info`(host:port) + `password` | `WHERE app_status=1` |

- **join 键**：DB 的 `host_info` == AWS 的 `PrimaryEndpoint.Address` + `:` + `Port`（现网 78 个 1:1 对得上）。
- **派生规则（每集群）**：
  - 前缀 `prefix` = `rediss://`（TLS）/ `redis://`（非 TLS）——**真实 TLS，来自 AWS**。
  - 密码 `token` = `AuthTokenEnabled ? DB password : ""`。
    > ⚠️ 关键坑：DB 对**所有** 78 个实例都存了 password，但 7 个非 TLS 的 AWS 是 `auth:false`。给非 AUTH 实例塞密码、用 `redis://` 连接会被 Redis 拒 → **非 AUTH 一律置空**。脚本已按 `AuthTokenEnabled` 处理。

### 1.1 三个文件（同一集群前缀一致）
| 文件 | 位置 | 内容 |
|------|------|------|
| `redis-password.file` | exporter 目录 | `{ "<prefix><host>:<port>": "<token>" }`，写入后置 **0600** |
| exporter `aws-redis-targets.json` | exporter 目录 | `[{"targets": ["<prefix><host>:<port>", ...], "labels": {}}]` |
| prometheus `aws-redis-targets.json` | `/data/prometheus-2.43.0.../` | 同上 |

- **为什么三份前缀现在一致了**：Prometheus 侧 target 决定 `instance` 标签、也决定 exporter 实际拨号用不用 TLS，**必须反映真实 TLS**；exporter 侧那份不参与拨号（拨号目标由 Prometheus 的 `?target=` 传入），历史上被老脚本一刀切成全 `rediss://`，现在统一成按真实 TLS，三处一致更清晰。密码文件 key 也必须与 `?target=` 前缀一致，exporter 才查得到密码。
- **前缀不能全 fleet 统一**：现网 **71 TLS + 7 非 TLS**（`luckyus-auth / authservice / cmdb / ldas / session / waf / web`），非 TLS 的只能 `redis://`（用 `rediss://` 连非 TLS 会 TLS 握手失败）。

### 1.2 脚本 `sync_redis_monitoring.py` 行为
1. 拉 AWS RG 加密/AUTH 状态；拉 ldas 在营实例。
2. join + 派生 entries（前缀、token）。
3. 报告：`[!] DB 在营但 AWS 无对应 RG`（改名/非 ElastiCache，**硬问题**，退出码 1）、`[?] AWS 有 RG 但 DB 未纳管`。
4. 生成三文件；写前 `.bak` 备份，无变化则跳过；密码文件置 0600。
5. 默认 **dry-run**，`--apply` 才写。
6. 需环境变量 `LDAS_PWD`；AWS 走本机 aws cli 凭证。

> 旧 `aws-redis.py`（全 rediss://，因 CMDB 给不出 TLS 才一刀切）、`diff.py`、`target_diff.py` 均已被取代。

---

## 2. 接入操作

### 2.0 前提
1. 集群已在 AWS 建好（`describe-replication-groups` 能查到、`Available`）。
2. 集群已登记进 ldas `cache_cloud_app`：`app_status=1`、`host_info` = `<primary-endpoint>:6379`、加密集群的 `password` = 其 AUTH token。**这是唯一需要确保的"数据录入"，通常由建站/纳管流程完成**；监控这边不手改任何文件。

> 快速核对集群是否已具备条件：
> ```bash
> aws elasticache describe-replication-groups --region us-east-1 \
>   --replication-group-id luckyus-<service> \
>   --query 'ReplicationGroups[0].{tls:TransitEncryptionEnabled,auth:AuthTokenEnabled,ep:NodeGroups[0].PrimaryEndpoint.Address}'
> ```

### 2.1 预演（dry-run）
```bash
cd /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64
LDAS_PWD='<ldas只读密码>' python3 sync_redis_monitoring.py
```
确认：新集群出现在 entries、前缀符合其 TLS、无 `[!]` 硬问题、三文件将各 +1 项。
- 若报 `[!] DB 在营但 AWS 无对应 RG` → 多半 `host_info` 与 AWS endpoint 不一致（改名/拼写），先在 CMDB 修正。
- 若新集群没出现 → 它还没在 `cache_cloud_app` 里 `app_status=1`，先补登记。

### 2.2 写回
```bash
LDAS_PWD='<ldas只读密码>' python3 sync_redis_monitoring.py --apply
```
三文件各生成 `.bak` 后写入；密码文件 0600。Prometheus file_sd 自动热加载，**无需 reload**。

### 2.3 重启 exporter（仅当密码文件变化）
密码文件启动时才读，新增/改动了密码就要重启（脚本会提示是否变化）：
```bash
pgrep -af 'redis_exporter .*:9321'
kill "$(pgrep -f 'redis_exporter .*-web.listen-address=\":9321\"')"
sleep 2 && ./start.sh
sleep 2 && curl -s http://localhost:9321/metrics | head -1 && echo "exporter up"
```
> 重启期间 `:9321` 短暂中断 → 所有集群 `redis_*` 指标有一个抓取周期缺口，属正常，挑低峰做。

---

## 3. 定期对账（可选）

因为源是权威的 AWS + CMDB，随时可跑 dry-run 做全量对账，发现漂移（新集群没纳管、僵尸项、TLS 改动）：
```bash
LDAS_PWD='<ldas只读密码>' python3 sync_redis_monitoring.py
```
`[!]`=需处理的硬问题（退出码 1，可挂 cron 告警），`[?]`=AWS 有但 CMDB 未纳管（视情况）。

---

## 4. 验证

### 4.1 target UP + 指标流入
```promql
up{job="aws-redis_exporter", instance=~".*luckyus-<service>.*"}       # 1
redis_up{instance=~".*luckyus-<service>.*"}                            # 1 = 连上且认证成功
redis_memory_used_bytes{instance=~".*luckyus-<service>.*"}
```
`up=1` 但 `redis_up=0` / 无 `redis_*` → 密码错、前缀不匹配、或改密码后没重启 exporter。

### 4.2 看板
**AWS Redis Summary**（uid `gy7wsBsnk`）面板 UNFILTERED，新集群自动出现；下钻 **AWS Redis Detail**（uid `kxTd1QEddd`）`var-cluster` 选它。`instance` 是完整 URL，看板已 `label_replace` 清洗成短名。

---

## 5. 常见坑

| 现象 | 根因 | 处理 |
|------|------|------|
| `up=1` 但无 `redis_*` / `redis_up=0` | 密码错/前缀不匹配；改密码后没重启 exporter | 重跑 §2.2 + §2.3 |
| 改了但 Prometheus 抓不到 | 只 dry-run 没 `--apply` | 跑 `--apply` |
| 脚本 `[!] DB 在营但 AWS 无对应 RG` | `host_info` 与 AWS endpoint 不符（改名/拼写/尾随空格） | 在 CMDB 修正 host_info |
| 新集群 dry-run 里没出现 | 未在 `cache_cloud_app` 登记为 `app_status=1` | 补 CMDB 登记 |
| 非 TLS 集群 `redis_up=0` | 误用了 `rediss://`（连非 TLS 会握手失败） | 由脚本按 AWS `TransitEncryptionEnabled` 自动决定，无需手改；若手改过请还原 |
| 找 `coupondata` 找不到 | 命名不一致：CMDB app_name `luckyus_isales_coupondata`，真实 RG/endpoint 是 `luckyus-isales-coupon` | join 用 host_info（真实 endpoint），不用 app_name |
| 选中集群 CPU 积分面板 "No data" | 集群非 burstable（如 `isales-market` = `m6g.large`），无积分机制 | 正常，仅 T3/T4g 有积分 |

---

## 6. 补充：CPU 积分与其它口径

- 本 runbook 只覆盖 **AWS Redis Summary** 看板（Prometheus `redis_exporter` 口径）。
- **CPU 积分** 不在 Prometheus，走 `ldas` 采集表 `t_dba_collect_redis_cluster_metrics`（`collect_cloudwatch.py --tasks redis_metrics --write`）。详见 `redis-grafana-dashboard` / `redis-cpu-credit-capacity`。
- 建议告警：`CPUCreditBalance < 50(micro)/100(small)` 且 `CPUUtilization > baseline` 持续 1h；failover/重建节点从 0 积分起充非过载，用 `describe-events` 交叉验证。

---

## 7. 检查清单

- [ ] 集群 AWS 已 `Available`；`describe-replication-groups` 可查
- [ ] 集群已登记 ldas `cache_cloud_app`：`app_status=1`、`host_info=<endpoint>:6379`、加密集群 `password`=AUTH token
- [ ] `sync_redis_monitoring.py`（dry-run）：新集群出现、前缀正确、无 `[!]`
- [ ] `sync_redis_monitoring.py --apply`：三文件已备份并写回（密码文件 0600）
- [ ] 若密码文件变化 → **重启 exporter**，`:9321/metrics` 恢复
- [ ] `up{job="aws-redis_exporter"}=1` 且 `redis_up=1`
- [ ] 集群出现在 AWS Redis Summary 看板
- [ ] （如需积分）另走 ldas 采集器口径接入

---

## 附录：数据源事实（2026-07-15 核对）

- ElastiCache RG 共 **78** = ldas 在营实例 **78**，`host_info == endpoint:6379` 1:1 对齐。
- **71 TLS / 7 非 TLS**（非 TLS：`luckyus-auth / authservice / cmdb / ldas / session / waf / web`）。
- `TransitEncryptionEnabled` 与 `AuthTokenEnabled` **完全一致**（AWS 规则：开 AUTH 必须开 TLS）。
- CMDB `cache_cloud_app` 无 TLS 列，`password` 列对 78 个全填充 → **TLS 必须取自 AWS**，非 AUTH 实例的 DB 密码要丢弃。
- 脚本 `scripts/sync_redis_monitoring.py`：顶部路径/REGION 常量按主机调整；`LDAS_PWD` 走环境变量不硬编码；核心 `build_plan`/`render_files` 为纯函数、已单测。
