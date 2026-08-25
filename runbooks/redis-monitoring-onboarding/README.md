# AWS Redis 监控自动同步脚本 — 说明文档

**脚本**：`scripts/sync_redis_monitoring.py`（全自动生成/对账监控三文件，含 `--cron` 定时对账模式）
**归属**：DBA / Infrastructure — 曾翔宇 (David Zeng)
**主机**：**dbtools01-prod-usa-aws**
**最后更新**：2026-08-20
**关联记忆**：`aws-redis-summary-monitoring-onboarding`、`redis-grafana-dashboard`、`redis-cpu-credit-capacity`

> 本文档取代旧的「新建 Redis 接入监控流程」手册——接入已全自动化，不再需要手工编辑任何监控文件。**维护好 ozono 纳管数据，跑脚本即可。**

---

## 1. 这个脚本做什么

从**三个数据源** join 生成 AWS Redis 监控的三个文件，无需手工维护 targets/前缀：

| 数据源 | 提供 | 取法 |
|--------|------|------|
| **AWS ElastiCache** | 每集群 endpoint + 是否 TLS（`TransitEncryptionEnabled`）+ 是否 AUTH（`AuthTokenEnabled`） | `describe-replication-groups`（`databasecheck` 有读权限） |
| **ozono CMDB** `luckyus_ozono.cache_cloud_app` | 每在营实例 `host_info`(host:port)，**仅用于发现集群 + 与 AWS 对账** | `WHERE app_status=1` |
| **现有 `redis-password.file`** | 每集群 **token 的唯一权威来源** | 脚本启动时读取 |

- **join 键**：`host_info == <集群端点>:<Port>`（现网 80 个 1:1 对齐）。
- **集群端点怎么取**（`resolve_rg_endpoint`，两种形态字段互斥）：

  | 集群形态 | AWS 字段 | 例 |
  |----------|----------|-----|
  | cluster mode **关**（现网 79/80） | `NodeGroups[0].PrimaryEndpoint`（此时 `ConfigurationEndpoint` 为 null） | `master.luckyus-iadmin.….cache.amazonaws.com:6379` |
  | cluster mode **开**（分片集群，现网 1/80） | `ConfigurationEndpoint`（此时 `NodeGroups[].PrimaryEndpoint` **全为 null**） | `clustercfg.luckyus-icdpactivityengine.….cache.amazonaws.com:6379` |

  ozono `host_info` 对两种形态登记的都是上表那个地址，所以 join 天然对得上。两个端点都取不到（如 `creating` 中）→ 记入 `no_endpoint` **显式上报**（硬问题，退出码 1）。
  - > 🔴 **分片集群不要拿 clustercfg 当指标来源，加 `--expand-shards`**（见 §3.1）。2026-08-20 实测：`clustercfg.…` 一条 DNS 名解析出**全部 6 个节点的 IP**（3 主 + 3 从），服务端每次查询轮换顺序（30 次采样，落在 6 个节点上近似均匀），客户端连第一个 → **每次 `/scrape` 落到随机节点**。
  - > ⚠️ **2026-08-20 漏监控事故**：老版本只读 `NodeGroups[0].PrimaryEndpoint`，取不到就 `continue` **静默丢弃** → 新建的分片集群 `luckyus-icdpactivityengine` 既不进 `aws_map`（连"未纳管"提示都不会报），又让 ozono 那条在营记录落进 `db_only` 被报成"改名/非 ElastiCache?"，真实原因被完全掩盖。现已按上表取端点，且**任何取不到端点的 RG 都必须上报，不再静默跳过**。
- **派生规则（每集群）**：
  - 前缀 = `rediss://`（TLS）/ `redis://`（非 TLS）——真实 TLS，取自 AWS。
  - **token = 现有 `redis-password.file` 里该集群的 token**（按 `host:port` 查，前缀无关）。非 AUTH 集群一律空；AUTH 集群但文件里没有 → 标 `token_missing`、先写空、**人工补，绝不猜值**。
  - > ⚠️ **token 绝不取自 ozono**。ozono `cache_cloud_app.password` 对 AUTH 集群与真实 AUTH token **不一致**；2026-07-16 曾因 `--apply` 用 ozono 密码覆盖，导致 **71 个 AUTH 集群 `redis_up=0`**（已回滚）。现在脚本只增删 key/前缀、**绝不改动已有 token**，`--apply` 对已纳管集群幂等。

### 生成的三个文件（同一集群前缀一致）
| 文件 | 位置 | 内容 |
|------|------|------|
| `redis-password.file` | exporter 目录 | `{ "<prefix><host>:<port>": "<token>" }`，写入置 **0600** |
| exporter `aws-redis-targets.json` | exporter 目录 | `[{"targets":[...],"labels":{}}]` |
| prometheus `aws-redis-targets.json` | `/data/prometheus-2.43.0.../` | 同上 |

---

## 2. 运行前提

- 主机装了 `python3` + `pymysql`，`aws` cli 且配了一个**有 `elasticache:DescribeReplicationGroups` 权限**的身份（如 `databasecheck`，region us-east-1）。
  - ⚠️ **cron 陷阱**：cron 以 root 跑、`HOME=/root`，读的是 `/root/.aws/credentials` 的 `[default]`；而你 `sudo -s` 手动跑时 `HOME` 可能仍是 `/home/xxx`，读的是**另一份**凭证——两者身份不同会导致"手动能跑、cron 报 AccessDenied"。
  - 最稳做法：在 `ldas.conf` 里加**可选的 `[aws]` 段**（路径固定、与 HOME 无关，见 §2 下方），指定 `profile` 或 `access_key_id`/`secret_access_key`，脚本会把身份注入 `aws` 子进程（密钥只走 env、绝不进命令行）。不写 `[aws]` 段则用主机默认凭证链（现状）。
  - AWS 不可达时（权限/凭证/网络）脚本**不崩溃**：`--cron` 降级为"仅 Prometheus 监控状态检查"并告警、恒退出 0；`--apply`/dry-run 干净退出非 0、绝不用残缺数据写文件。
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
- **可选 `[aws]` 段**（同一个 `ldas.conf`，解决上面的 cron/HOME 凭证陷阱）。二选一，优先 `profile`：
  ```ini
  [aws]
  profile = databasecheck        # ~/.aws/credentials 里的 profile 名（密钥由 aws CLI 托管）
  region  = us-east-1            # 可选
  ```
  或直接写密钥（明文落盘，仅限本 0600 文件；两者必须同时给）：
  ```ini
  [aws]
  access_key_id     = AKIA....
  secret_access_key = ....
  region            = us-east-1
  ```
  - 校验：只给一个 key、或 `profile` 与密钥同时给 = FATAL。用 `env -i HOME=/root PATH=/usr/bin:/bin python3 sync_redis_monitoring.py` 复刻 cron 环境验证（期望 `AWS RG 80`）。
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

### 3.1 `--expand-shards`：分片集群按节点抓（**分片集群必加**）

不加时，一个分片集群只有 `clustercfg` 一个 target，而该 DNS 名轮换指向全部 N 个节点，于是：

| 症状 | 后果 |
|------|------|
| counter 类指标（`redis_commands_processed_total` 等）在同一个 `instance` 下混了 N 个互不相干的计数器 | `rate()`/`increase()` 被当成 counter reset → 凭空尖峰或恒为 0，命令率/命中率全不可信 |
| `redis_memory_used_bytes` / `redis_db_keys` 是单节点值 | 只看得到 1/N 数据且在分片间跳变，容量水位既可能虚低也可能误报 |
| 单个分片挂掉 | 只有约 1/N 的抓取会落在它上面 → 间歇性告警易被当噪声，或被完全掩盖 |
| N 条记录里一半是副本，且分片集群 AWS 不给 `CurrentRole` | 主/从指标混进同一条序列 |

加上 `--expand-shards` 后，脚本调 `describe-cache-clusters --show-cache-node-info` 取每节点端点（`<rg>-000X-00Y.<rg>.….amazonaws.com:6379`，**故障转移只换角色不换端点**，拿来当 target 稳定），把该集群展开成 **N 个独立 target**，一节点一条时间序列。

```bash
python3 sync_redis_monitoring.py --expand-shards            # dry-run
python3 sync_redis_monitoring.py --expand-shards --apply
```

三个必须知道的点：

1. **crontab 的 `--cron` 必须带同样的开关**，否则 cron 算出的 targets 与现网文件不同 → **天天误报漂移**。不带开关而现网有分片集群时，脚本会打 `[!]` 警告提醒。
2. **密码文件会保留 clustercfg 那个父 key**（多一条、对 exporter 无害）。这是**故意**的：token 的权威来源是现有密码文件，若展开后文件里只剩节点 key，下一轮就查不到父 key → 报 `token_missing` 并把 token 置空 → 再 `--apply` 会把 N 个节点的 token 全清掉（7-16 事故的翻版）。有单测 `test_token_roundtrip_is_idempotent_across_runs` + 反证用例守着。
3. 需要 `elasticache:DescribeCacheClusters` 权限。拿不到节点端点时**绝不半写**：`--cron` 降级告警恒退出 0，`--apply`/dry-run 干净退出非 0。

> 容量/趋势建议另配 CloudWatch：`AWS/ElastiCache` 命名空间对每个节点有完整 per-node 指标（`CacheClusterId` 维度）。注：当前 Prometheus 里**没有**任何 cloudwatch-exporter 的 elasticache 指标（查 `aws_elasticache.*` 为空），这条路是空的。

### 输出语义
- `[!] DB 在营但 AWS 无对应 RG` — 硬问题（`host_info` 与 AWS endpoint 不符：改名/拼写/尾随空格）。脚本**退出码 1**。若同时出现下面的 `no_endpoint`，先看它——端点解析失败会连带把对应的在营记录推进 `db_only`。
- `[!] AWS RG 取不到端点` — 硬问题（`no_endpoint`，**退出码 1**）：`PrimaryEndpoint` 和 `ConfigurationEndpoint` 都为空，本轮无法纳管。多为集群仍在 `creating`（等建好再跑一次即可），或 AWS 返回了未知形态（要看 `status=` 与是否 `cluster-mode`）。
- 「cluster-mode 分片集群 N: [...]」— 本次识别到的分片集群。加了 `--expand-shards` 会跟一行「展开后 target M → K」；**没加**则会跟一条 `[!]` 警告（该 target 只能当存活探针，且若现网文件是展开写的会误报漂移）。详见 §3.1。
- `[!] 声明展开却拿不到节点端点` — 硬问题（`expand_missing`，**退出码 1**）：加了 `--expand-shards` 但 `describe-cache-clusters` 里没有该 RG 的节点端点，本轮仍退回 clustercfg 单 target。
- `[!] AUTH 集群但现有密码文件缺 token` — 硬问题（`token_missing`）。**退出码 1**。这是**接入新 AUTH 集群**要做的事：先手工把该集群的真实 AUTH token 写进 `redis-password.file`（key = 集群的目标 URI，如 `rediss://master.<endpoint>:6379`），再 `--apply`+重启 exporter。脚本不会、也不该替你猜这个 token。
- `[?] AWS 有 RG 但 DB 未登记在营` — AWS 有集群但 ozono 未纳管，视情况处理。
- `[~] … 将更新` / `[=] … 无变化` — 每个文件是否需要写。对已纳管集群，`redis-password.file` 应恒为 `[=]`（token 沿用现有值，幂等）。
- 「非TLS(redis://) N: [...]」— 本次识别到的非加密集群。
- `[!] 应监控但未生效（<reason>）` — 步骤 [6] 查 Prometheus 现状发现"应监控却没监控上"的实例（硬问题，**退出码 1**）：
  - `not_scraped` — 计划里该有、但 Prometheus 根本没这个 target（漏纳管 / 漂移未 `--apply` / 名字带空格等）。
  - `scrape_down` — 有 target 但 `up=0`（DNS/网络，exporter 抓不到）。
  - `auth_down` — `up=1` 但 `redis_up=0`（连上但认证/连接失败，通常是缺/错 token）。

### 步骤 [6]：对现有监控状态的检查
每次运行（含 `--cron`）都会查 Prometheus `up{job="aws-redis-job"}` 和 `redis_up{...}`，把"应监控"（本次派生出的 entries）与实际抓取状态比对，挑出上面三类未生效实例并计入告警/退出码。
- Prometheus 地址默认 `http://10.238.3.136:9090`，可用环境变量 **`PROMETHEUS_URL`** 覆盖（脚本顶部亦有常量）。
- **尽力而为**：Prometheus 不可达时只打 `[WARN]` 跳过，不让脚本失败、也不误报。
- `--skip-monitoring-check` 可完全关闭这一步。

---

## 4. 配置到 crontab（定时对账，`--cron` 模式）

`--cron` 是脚本内建的定时对账模式，**无需任何 shell 包装**：

- **只读**：恒不写文件（即使同时传了 `--apply` 也忽略），只拉 AWS+ozono、join、比对现网三文件。
- **只在异常时告警**：任一硬问题时才发，否则静默。硬问题 = 三文件与 AWS+ozono 语义不同步（`drift_paths`）/ `db_only`（在营却在 AWS 找不到）/ `token_missing`（AUTH 缺 token）/ **`not_monitored`（应监控却未有效监控，来自步骤 [6] 查 Prometheus）** / **`no_endpoint`（AWS RG 取不到端点，无法纳管）**。飞书标题会带各类计数 `(files=, db_only=, token_missing=, not_monitored=, no_endpoint=)`。
- **告警发飞书**：`--webhook` 传飞书自定义机器人 URL，脚本发 **interactive 交互式卡片**（红色标题栏 = 告警），中文正文不转义（`ensure_ascii=False`）。**没配 webhook 就只打印**（不发邮件、不依赖 cron `MAILTO`）——cron 那行已把输出重定向进日志文件，直接看日志即可。飞书即使 HTTP 200 也可能业务失败，脚本会检查返回体 `code`，非 0 时打 `[WARN]` 并把原文一起打印。
- **限频重试（2026-08-20 加）**：飞书返回 `code=11232 frequency limited` 时**自动重试**（共 3 次尝试，间隔 2s/6s，每次重签名）。签名错(`19021`)/参数错这类重试也没用的错误则立即放弃。判定见纯函数 `feishu_retryable(code, msg)`——code 与 msg 双判据，因为飞书限频有一族相近 code。
  - > 🔴 **为什么加**：2026-08-20 早晨的 cron 正好带着 `db_only=1`（新分片集群漏监控）去告警，却吃到 `code=11232`，**告警被限频吞掉**、只落进日志没人看 → 漏监控就这么"没人发现"。同一个飞书机器人被 alert-daemon 等多方共用时很容易撞限频。
- **送不出去时留可 grep 的标记**：重试耗尽后日志里打 `[ALERT-UNDELIVERED]`，后面跟完整标题+正文。`--cron` 恒退出 0，日志是唯一线索，建议加一条巡检：`grep -c ALERT-UNDELIVERED /var/log/redis-mon-sync.log`。
- **webhook URL 不进日志**：末段就是机器人 token，日志里一律经 `redact_webhook()` 掩码成 `…/abcd***`（此前成功分支会打完整 URL）。
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
# ⚠️ 现网有分片集群 → 必须带 --expand-shards，与写文件时用的开关保持一致，否则天天误报漂移
FEISHU_SIGN_SECRET=<机器人签名密钥，机器人没开签名校验就删掉这行>
0 14 * * * cd /data/redis-exporter/redis_exporter-v1.74.0.linux-amd64 && python3 sync_redis_monitoring.py --cron --expand-shards --webhook https://open.feishu.cn/open-apis/bot/v2/hook/<机器人token> >> /var/log/redis-mon-sync.log 2>&1
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

## 6. 数据源事实（2026-08-20 复核，供参考）

- ElastiCache RG 共 **80** = ozono 在营 **80**（`app_status=1`，`host_info` 全不重复），`host_info == 集群端点:6379` 1:1，`db_only`/`aws_only` 均为空。
- **形态**：79 个 cluster mode 关；**1 个 cluster mode 开**——`luckyus-icdpactivityengine`（3 分片，`clustercfg.…:6379`，TLS+AUTH）。
- **73 TLS / 7 非 TLS**（非 TLS：`luckyus-auth / authservice / cmdb / ldas / session / waf / web`，endpoint 无 `master.` 前缀、带 `.ng.0001.`）。
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

改脚本后先跑单测（104 个用例，覆盖 TLS 前缀取自 AWS、非 AUTH 丢密码、join 用 host_info、**cluster-mode 端点解析、`--expand-shards` 节点展开与 token 往返幂等、飞书限频重试与 webhook 脱敏**、共用端点去重、db_only/aws_only 识别、排序、三文件前缀一致、`ldas.conf` 解析与缺字段 FATAL 等易错点）：
```bash
cd runbooks/redis-monitoring-onboarding/scripts   # 或主机 exporter 目录
python3 -m unittest test_sync_redis_monitoring -v
```

（主机原件在 `/data/redis-exporter/redis_exporter-v1.74.0.linux-amd64/`。旧的 `aws-redis.py` / `diff.py` / `target_diff.py` 已被 `sync_redis_monitoring.py` 取代；旧的 `cron_reconcile.sh` shell 包装已被脚本内建的 `--cron` 模式取代，可删。）
