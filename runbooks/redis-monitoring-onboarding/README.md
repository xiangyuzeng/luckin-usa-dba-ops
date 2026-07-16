# AWS Redis 监控自动同步脚本 — 说明文档

**脚本**：`scripts/sync_redis_monitoring.py`（全自动生成/对账监控三文件，含 `--cron` 定时对账模式）
**归属**：DBA / Infrastructure — 曾翔宇 (David Zeng)
**主机**：**dbtools01-prod-usa-aws**
**最后更新**：2026-07-16
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
- **ldas 连接配置文件** `ldas.conf`（单文件，`endpoint/port/user/password/database` 放在一起，**0600**）。
  从模板生成，不再有裸密码文件、也不再靠环境变量传密码：
  ```bash
  cd /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64
  cp ldas.conf.example ldas.conf
  chmod 600 ldas.conf
  # 编辑 ldas.conf，把 password 填成 ldas 只读密码
  ```
  - 默认读 `<EXPORTER_DIR>/ldas.conf`，可用 `--ldas-conf <path>` 或环境变量 `LDAS_CONF` 指定别的路径。
  - 若走密管/CI 注入、不想把密码落进 `ldas.conf`：把 `password` 留空，改由环境变量 **`LDAS_PASSWORD`** 覆盖。
  - 缺文件 / 缺 `[ldas]` 段 / 缺任一字段 → 脚本直接 FATAL 退出，绝不半路裸奔连库。
- 脚本顶部 4 个路径常量（`EXPORTER_DIR` / `PASSWORD_FILE` / `EXPORTER_TARGETS` / `PROMETHEUS_TARGETS`）与 `REGION` 按主机实际核对。

---

## 3. 手动使用

```bash
cd /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64

# 预演：拉 AWS + ozono、join、报告将发生的变化，不写文件（读 ldas.conf）
python3 sync_redis_monitoring.py

# 确认无误后写回三文件（自动 .bak 备份；密码文件 0600）
python3 sync_redis_monitoring.py --apply

# 仅当 redis-password.file 有变化时，重启 exporter 使新密码生效
kill "$(pgrep -f 'redis_exporter .*-web.listen-address=\":9321\"')"; ./start.sh
```

### 输出语义
- `[!] DB 在营但 AWS 无对应 RG` — 硬问题（`host_info` 与 AWS endpoint 不符：改名/拼写/尾随空格）。脚本**退出码 1**。
- `[?] AWS 有 RG 但 DB 未登记在营` — AWS 有集群但 ozono 未纳管，视情况处理。
- `[~] … 将更新` / `[=] … 无变化` — 每个文件是否需要写。
- 「非TLS(redis://) N: [...]」— 本次识别到的非加密集群。

---

## 4. 配置到 crontab（定时对账，`--cron` 模式）

`--cron` 是脚本内建的定时对账模式，**无需任何 shell 包装**：

- **只读**：恒不写文件（即使同时传了 `--apply` 也忽略），只拉 AWS+ozono、join、比对现网三文件。
- **只在异常时告警**：现网三文件与 AWS+ozono 不同步（有文件"将更新"）、或有硬问题（`db_only`：在营却在 AWS 找不到）时才发；否则静默。
- **告警发飞书**：`--webhook` 传飞书自定义机器人 URL，脚本发 **interactive 交互式卡片**（红色标题栏 = 告警），中文正文不转义（`ensure_ascii=False`）。**没配 webhook 就只打印**（不发邮件、不依赖 cron `MAILTO`）——cron 那行已把输出重定向进日志文件，直接看日志即可。飞书即使 HTTP 200 也可能业务失败，脚本会检查返回体 `code`，非 0 时打 `[WARN]` 并把原文一起打印。
- **签名校验**：若机器人开了"签名校验"，把密钥放环境变量 **`FEISHU_SIGN_SECRET`**，脚本自动叠加 `timestamp`+`sign`（`base64(HMAC-SHA256(key="{ts}\n{secret}", msg=""))`）。不开签名则无需设置。
- **恒退出 0**：告警走飞书/日志，退出码不用于告警，避免上层包装脚本因退出码误判。
- **漂移判据 = 语义比对**：文件内容按 JSON 解析后**忽略 targets 顺序 / 键序 / 缩进**再比（`content_equivalent`）——只在集合/取值**真的不同**时才告警。纯排版/顺序差异不告警。`--apply` 仍会把磁盘归一化成规范格式（dry-run 日志里标 `（仅顺序/排版差异…归一化，不算漂移）`）。判据不再 grep 输出字符串。

真正 `--apply` + 重启 exporter 仍由人确认后执行（避免无人值守时 exporter 重启造成指标缺口）。

### 4.1 装 crontab
密码不进 crontab：`ldas.conf`（0600）已是唯一密码来源，`--cron` 直接读它。
```bash
crontab -e
```
加一行（每天 14:00 UTC ≈ 09/10 点 EST/EDT，**避开 05:00 UTC 批量窗口**）：
```cron
# 每天对账 AWS Redis 监控，有漂移/异常才发飞书告警
FEISHU_SIGN_SECRET=<机器人签名密钥，机器人没开签名校验就删掉这行>
0 14 * * * cd /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64 && python3 sync_redis_monitoring.py --cron --webhook https://open.feishu.cn/open-apis/bot/v2/hook/<机器人token> >> /var/log/redis-mon-sync.log 2>&1
```
- webhook 可省略：不配就只把告警内容打印进上面重定向的日志文件（`/var/log/redis-mon-sync.log`），自己看日志或另接日志监控即可，脚本不发邮件。
- 也可用环境变量 `REDIS_SYNC_WEBHOOK` 代替 `--webhook`。

验证：`crontab -l` 能看到；手动跑一遍 `python3 sync_redis_monitoring.py --cron; echo rc=$?` 确认 rc=0、告警渠道通。

### 4.2 （可选）无人值守全自动
若确实想让 cron 直接写三文件，把 crontab 里的 `--cron` 换成 `--apply`。⚠️ 但**加了 AUTH 集群会改动密码文件、需重启 exporter**——无人值守重启会造成一次抓取周期的指标缺口，且有拉起失败风险。建议保留"cron 只对账告警、人来 apply+重启"的分工，除非你能接受自动重启。

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

| 文件 | 作用 |
|------|------|
| `scripts/sync_redis_monitoring.py` | 全自动：AWS + ozono → 生成/对账三文件。dry-run 默认，`--apply` 写回，`--cron` 定时对账告警。核心 `build_plan`/`render_files`/`load_ldas_conf` 已单测（见下）。 |
| `scripts/ldas.conf.example` | ldas 只读连接配置模板；`cp` 成 `ldas.conf` 填密码、`chmod 600`。**这是唯一的密码来源文件**（可被 `LDAS_PASSWORD` 环境变量覆盖）。 |
| `scripts/test_sync_redis_monitoring.py` | `build_plan`/`render_files`/`load_ldas_conf` 单测（纯 stdlib `unittest`，不碰 AWS/ldas/网络，无需 pymysql 或凭证）。 |

改脚本后先跑单测（覆盖 TLS 前缀取自 AWS、非 AUTH 丢密码、join 用 host_info、共用端点去重、db_only/aws_only 识别、排序、三文件前缀一致、`ldas.conf` 解析与缺字段 FATAL 等易错点）：
```bash
cd runbooks/redis-monitoring-onboarding/scripts   # 或主机 exporter 目录
python3 -m unittest test_sync_redis_monitoring -v
```

（主机原件在 `/data/redis-exporter/redis_exporter-v1.74.0.linux-amd64/`。旧的 `aws-redis.py` / `diff.py` / `target_diff.py` 已被 `sync_redis_monitoring.py` 取代；旧的 `cron_reconcile.sh` shell 包装已被脚本内建的 `--cron` 模式取代，可删。）
