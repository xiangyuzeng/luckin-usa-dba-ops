# AWS Redis 监控自动同步脚本 — 说明文档

**脚本**：`scripts/sync_redis_monitoring.py`（全自动生成监控三文件）+ `scripts/cron_reconcile.sh`（定时对账告警）
**归属**：DBA / Infrastructure — 曾翔宇 (David Zeng)
**主机**：**dbtools01-prod-usa-aws**
**最后更新**：2026-07-15
**关联记忆**：`aws-redis-summary-monitoring-onboarding`、`redis-grafana-dashboard`、`redis-cpu-credit-capacity`

> 本文档取代旧的「新建 Redis 接入监控流程」手册——接入已全自动化，不再需要手工编辑任何监控文件。**维护好 ozono 纳管数据，跑脚本即可。**

---

## 1. 这个脚本做什么

从两个**权威数据源** join 生成 AWS Redis 监控的三个文件，无需手工维护：

| 数据源 | 提供 | 取法 |
|--------|------|------|
| **AWS ElastiCache** | 每集群 endpoint + 是否 TLS（`TransitEncryptionEnabled`）+ 是否 AUTH（`AuthTokenEnabled`） | `describe-replication-groups`（`databasecheck` 有读权限） |
| **ozono CMDB** `luckyus_ozono.cache_cloud_app` | 每在营实例 `host_info`(host:port) + `password` | `WHERE app_status=1` |

- **join 键**：`host_info == PrimaryEndpoint.Address + ":" + Port`（现网 78 个 1:1 对齐）。
- **派生规则（每集群）**：
  - 前缀 = `rediss://`（TLS）/ `redis://`（非 TLS）——真实 TLS，取自 AWS。
  - 密码 = `AuthTokenEnabled ? ozono里的password : ""`（非 AUTH 实例即使 ozono 存了密码也丢弃，否则用 `redis://` 连会被 Redis 拒）。

### 生成的三个文件（同一集群前缀一致）
| 文件 | 位置 | 内容 |
|------|------|------|
| `redis-password.file` | exporter 目录 | `{ "<prefix><host>:<port>": "<token>" }`，写入置 **0600** |
| exporter `aws-redis-targets.json` | exporter 目录 | `[{"targets":[...],"labels":{}}]` |
| prometheus `aws-redis-targets.json` | `/data/prometheus-2.43.0.../` | 同上 |

---

## 2. 运行前提

- 主机装了 `python3` + `pymysql`，`aws` cli 且已配置 `databasecheck` 凭证（region us-east-1）。
- 环境变量 **`LDAS_PWD`** = ldas 只读密码（脚本不硬编码密码）。
- 脚本顶部 4 个路径常量（`EXPORTER_DIR` / `PASSWORD_FILE` / `EXPORTER_TARGETS` / `PROMETHEUS_TARGETS`）与 `REGION` 按主机实际核对。

---

## 3. 手动使用

```bash
cd /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64

# 预演：拉 AWS + ozono、join、报告将发生的变化，不写文件
LDAS_PWD='<ldas只读密码>' python3 sync_redis_monitoring.py

# 确认无误后写回三文件（自动 .bak 备份；密码文件 0600）
LDAS_PWD='<ldas只读密码>' python3 sync_redis_monitoring.py --apply

# 仅当 redis-password.file 有变化时，重启 exporter 使新密码生效
kill "$(pgrep -f 'redis_exporter .*-web.listen-address=\":9321\"')"; ./start.sh
```

### 输出语义
- `[!] DB 在营但 AWS 无对应 RG` — 硬问题（`host_info` 与 AWS endpoint 不符：改名/拼写/尾随空格）。脚本**退出码 1**。
- `[?] AWS 有 RG 但 DB 未登记在营` — AWS 有集群但 ozono 未纳管，视情况处理。
- `[~] … 将更新` / `[=] … 无变化` — 每个文件是否需要写。
- 「非TLS(redis://) N: [...]」— 本次识别到的非加密集群。

---

## 4. 配置到 crontab（定时对账）

推荐把 **dry-run 对账**挂 cron：每天跑一次，只在"现网与 AWS+ozono 不同步"或"有硬问题"时告警；真正 `--apply` + 重启 exporter 仍由人确认后执行（避免无人值守时 exporter 重启造成指标缺口）。

### 4.1 准备密码文件（不要把密码写进 crontab）
```bash
cd /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64
printf '%s' '<ldas只读密码>' > .ldas_pwd
chmod 600 .ldas_pwd && chown root:root .ldas_pwd
```
`cron_reconcile.sh` 会从这个 0600 文件读 `LDAS_PWD`。再按现网把脚本里的告警渠道改好（邮件地址，或改用 webhook / 你的 alert-mailserver）。

### 4.2 装 crontab
```bash
chmod +x /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64/cron_reconcile.sh
crontab -e
```
加一行（每天 14:00 UTC ≈ 09/10 点 EST/EDT，**避开 05:00 UTC 批量窗口**）：
```cron
# 每天对账 AWS Redis 监控，有漂移/异常才告警
0 14 * * * /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64/cron_reconcile.sh >> /var/log/redis-mon-sync.log 2>&1
```
验证：`crontab -l` 能看到；手动跑一遍 `bash cron_reconcile.sh; echo rc=$?` 确认无报错、告警渠道通。

### 4.3 （可选）无人值守全自动
若确实想让 cron 直接 `--apply`（连三文件都自动写），把 `cron_reconcile.sh` 里的 `python3 "$SCRIPT"` 改成 `python3 "$SCRIPT" --apply`。⚠️ 但**加了 AUTH 集群会改动密码文件、需重启 exporter**——无人值守重启会造成一次抓取周期的指标缺口，且有拉起失败风险。建议保留"cron 只对账告警、人来 apply+重启"的分工，除非你能接受自动重启。

---

## 5. 验证

```promql
up{job="aws-redis_exporter", instance=~".*luckyus-<service>.*"}      # 1
redis_up{instance=~".*luckyus-<service>.*"}                           # 1 = 连上且认证成功
```
`up=1` 但 `redis_up=0` → 密码错/前缀不匹配/改密码后没重启 exporter。
看板 **AWS Redis Summary**（uid `gy7wsBsnk`，面板 UNFILTERED，自动出现）；下钻 **AWS Redis Detail**（uid `kxTd1QEddd`）。

---

## 6. 数据源事实（2026-07-15 核对，供参考）

- ElastiCache RG 共 **78** = ozono 在营 **78**，`host_info == endpoint:6379` 1:1。
- **71 TLS / 7 非 TLS**（非 TLS：`luckyus-auth / authservice / cmdb / ldas / session / waf / web`，endpoint 无 `master.` 前缀、带 `.ng.0001.`）。
- `TransitEncryptionEnabled` 与 `AuthTokenEnabled` 完全一致（AWS 规则：开 AUTH 必须开 TLS）。
- CMDB 无 TLS 列、`password` 列对 78 个全填充 → **TLS 必取自 AWS**，非 AUTH 实例 DB 密码要丢弃。
- CMDB `app_name` 用下划线且可能与真实 RG 名不符（如 `luckyus_isales_coupondata` → RG/endpoint `luckyus-isales-coupon`）→ **join 用 host_info，不用 app_name**。

---

## 7. 脚本清单

| 脚本 | 作用 |
|------|------|
| `scripts/sync_redis_monitoring.py` | 全自动：AWS + ozono → 生成/对账三文件。dry-run 默认，`--apply` 写回。核心 `build_plan`/`render_files` 为纯函数、已单测。 |
| `scripts/cron_reconcile.sh` | crontab 包装：dry-run 对账，仅漂移/异常时告警；密码从 `.ldas_pwd`(0600) 读。 |

（主机原件在 `/data/redis-exporter/redis_exporter-v1.74.0.linux-amd64/`。旧的 `aws-redis.py` / `diff.py` / `target_diff.py` 已被 `sync_redis_monitoring.py` 取代。）
