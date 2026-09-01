# L0 慢 SQL 复查 —— 按执行账号回溯 `diagtools`

| 项目 | 内容 |
|------|------|
| 报告编号 | LCNA-DBA-SQL-2026-0901-C |
| 前序报告 | -0901（TOP3）、-0901-B（剩余 9 条） |
| 出具日期 | 2026-09-01 |
| 出具人 | 曾翔宇（DBA / Infrastructure） |
| 问题 | L0 TOP10 里还有没有我们自己（`diagtools`）执行的 |
| 数据窗口 | 2026-08-25 ~ 2026-09-01（7 天） |
| 数据来源 | CloudWatch Logs Insights（15 台 L0 实例慢日志原文，按 `User@Host` 聚合）+ `ldas01` 采集表榜单 + 现场 `EXPLAIN` |

---

## 结论

**榜单口径：TOP10 里我们自己的只有已修的 3 条**，其余全部是应用账号，无新增。

**但换成按账号回溯，发现一条比它们都大、却从来没上过任何榜单的 —— 也是我们自己的。**
`avgPrepTime` 每小时全表扫 `t_order_make` 145 万行，7 天 1.95 亿行，是今天上午刚修的
store-ops SPU 采集（2,700 万行）的 **4.6 倍**。它躲过了所有分析，因为**平均 0.62 秒**，
低于采集表 ≥1s 的收录门槛。

---

## 一、榜单口径（`t_dba_collect_slow_query`，7 天日差分）

| # | 实例 | 指纹 | DB时间 | 次数 | 均耗 | 执行账号 | 是否我们 |
|---|---|---|---:|---:|---:|---|---|
| 1 | opshopsale | `00259408` | 4,976.9s | 768 | 6.48s | `iopshopsaleservice_A_o` | 否 |
| 2 | salespayment | `fe67d6b5` | 3,780.6s | 2,304 | 1.64s | `isalespmtadmin_A_o` | 否 |
| 3 | salesmarketing | `9919be27` | 371.2s | 8 | 46.40s | `isalescouponservice_A_o` | 否 |
| 4 | cdpactivity | `142b98a6` | 191.7s | 104 | 1.84s | `icdpactivityengine_A_o` | 否 |
| 5 | salesorder | `e5a8e692` | 179.8s | 6 | 29.96s | **`diagtools`** | **是（已修）** |
| 6 | salesorder | `09d7feb6` | 142.1s | 6 | 23.69s | **`diagtools`** | **是（已修）** |
| 7 | salesorder | `792aa5a0` | 93.9s | 80 | 1.17s | `isalesorderservice_A_o` | 否 |
| 8 | salesorder | `8d07ade5` | 84.3s | 14 | 6.02s | `isalesorderservice_A_o` | 否 |
| 9 | salesorder | `ba25fea5` | 80.2s | 16 | 5.01s | `isalesorderservice_A_o` | 否 |
| 10 | salesorder | `397899b0` | 55.7s | 13 | 4.29s | `isalesorderservice_A_o` | 否（已停跑） |
| 11 | salesorder | `e2b527f7` | 44.6s | 6 | 7.44s | **`diagtools`** | **是（已修）** |
| 12 | salespayment | `18f0b86c` | 27.6s | 8 | 3.45s | `isalespmtadmin_A_o` | 否 |
| NEW | scm-shopstock | `6051c0d1` | 20.4s | 16 | 1.27s | 应用（`UPDATE`） | 否 |

本周唯一 NEW 是 `t_shop_goods_expired_batch` 上的 `UPDATE`（写操作），归属国际供应链 / 方思扬，
我们只读，不可能是我们的。

> 第 5/6/11 三条的 `LAST_SEEN` 停在 2026-09-01 05:00，即部署前最后一次运行；19:00 起已由合并后的
> 单条扫描取代（209 万行 / 24.78 秒，替代原先两条 419 万行 / 59.94 秒）。

---

## 二、账号口径：`diagtools` 7 天在 L0 上的全部足迹

不看 ≥1s 榜单，直接按 `User@Host` 聚合 15 台 L0 慢日志：**3,382 次 / 1,784.1 秒**。
按来源 IP 分成三处，全部是我们自己的机器：

| 来源 IP | 主机 | 次数 | DB时间 | 扫描行数 | 是什么 |
|---|---|---:|---:|---:|---|
| 10.238.3.43 | dbtools02-prod-usa-aws | 481 | 894.2s | **315,123,941** | 看板采集容器 + mcp-db-gateway 临时查询 |
| 10.238.10.251 | **idbcollect01-prod-usc-aws** | 2,899 | 889.6s | ~50 万 | DBA 采集平台 |
| 10.238.3.136 | dbtools01-prod-usa-aws | 2 | 0.3s | 0 | 零星 |

### 2.1 dbtools02（315,123,941 行）拆解

| 归属 | 次数 | DB时间 | 最大 | 扫描行数 |
|---|---:|---:|---:|---:|
| 🔴 **ops-dashboard 制作时长（`avg_min`）** | 140 | 87.4s | 3.62s | **195,134,850** |
| 其余（ops-dashboard 各查询 + 临时分析） | 213 | 208.3s | 14.82s | 51,875,624 |
| store-ops SPU（`spu_name`/`spu_code`） | 15 | 309.3s | 48.42s | 27,045,622 |
| ops-dashboard 30 天趋势 | 86 | 164.1s | 17.51s | 16,520,909 |
| store-ops 效能（90 天窗口） | 7 | 52.0s | 9.67s | 12,943,415 |

**按扫描行数排，第一名不是今天修的那两条，而是 `avgPrepTime`。**

---

## 三、🔴 新发现：`avgPrepTime` 每小时全表扫 145 万行

### 现象

`ops-dashboard`（`luckin-ops-pipeline`，每小时 ET 09:00–22:00 共 14 次/天）的两条查询：

```sql
-- _AVG_PREP_TIME（今日）与 _AVG_PREP_LAST_WEEK（上周同期），仅窗口不同
SELECT ROUND(AVG(TIMESTAMPDIFF(SECOND, accept_time, finish_time)) / 60, 1) AS avg_min
FROM luckyus_sales_order.t_order_make
WHERE create_time >= <ET 当日零点>
  AND finish_time IS NOT NULL AND accept_time IS NOT NULL
```

7 天实测：**140 次 / 87.4 秒 / 195,134,850 行**，单次扫 139 万行只为算一个平均值。

### 根因

`t_order_make`（1,447,423 行 / 213.8 MB）**只有两个索引**：

| 索引名 | 列 |
|---|---|
| PRIMARY | id |
| uniq_order_id | order_id, tenant |

`create_time` 无索引 → `EXPLAIN`：`type=ALL, possible_keys=NULL, rows=1,449,315`。

### 为什么一直没被发现

采集表 `t_dba_collect_slow_query` **只收 `avg_sec ≥ 1s` 的指纹**，而这条平均 **0.62 秒**。
于是它从未进入过任何榜单、任何周度分诊、任何报告 —— 尽管它的扫描量是榜单第 5、6 名之和的 4.6 倍。

> **这是台账机制的一个盲区**：按「单次耗时」筛选会漏掉「单次不慢但次数多、扫描量巨大」的查询。
> 按 DB 时间排它只有 87 秒（第 12 名开外），按扫描行数排它是我们自己的第一名。

### 修复（已合并 `740db42`）

改为过滤订单表、走 `idx_create_time`，再按 `uniq_order_id` join 回来 —— 与同文件的
`_STORE_PREP_TIME` 保持一致（那条本来就是这么写的，只有这两条是例外）：

```sql
SELECT ROUND(AVG(TIMESTAMPDIFF(SECOND, m.accept_time, m.finish_time)) / 60, 1) AS avg_min
FROM luckyus_sales_order.t_order o
JOIN luckyus_sales_order.t_order_make m ON m.order_id = o.id
WHERE o.create_time >= <ET 当日零点>
  AND m.finish_time IS NOT NULL AND m.accept_time IS NOT NULL
```

`EXPLAIN`：`o` 走 `idx_create_time`（range，4,853 行，Using index），`m` 走 `uniq_order_id`
（ref，每单 1 行）→ **约 1 万行，降幅约 145 倍**。

**口径未变，改前逐项核对过**：今日 3.3 分钟 / 4,745 行，上周 2.8 分钟 / 33,667 行 —— 新旧两种写法
结果与行数完全一致（每条制作记录与其订单落在同一个 ET 日）。

新增回归测试：遍历所有涉及 `t_order_make` 的 SQL 常量，凡直接过滤该表而不 join 订单表的一律失败。

**⚠️ 待部署**：需在 dbtools02 上跑 `pipeline/restart.sh` 后生效。

---

## 四、idbcollect01 的采集流量（不是故障，但值得知道）

DBA 采集平台 `idbcollect01-prod-usc-aws`（c6i.large，10.238.10.251）用 `diagtools` 轮询全部 15 台
L0，7 天在慢日志里留下 **2,899 条 / 889.6 秒**。

| 分类 | 条数 | DB时间 | 平均 | 最大 |
|---|---:|---:|---:|---:|
| 采集查询（innodb_trx 长事务、各实例指标） | 2,280 | 706.3s | 0.310s | 3.26s |
| **连接握手语句** | 619 | 183.3s | 0.296s | 2.94s |

握手语句指 `SELECT VERSION()`、`SELECT DATABASE()`、`SELECT @@sql_mode`、
`SELECT @@transaction_isolation`、`SET AUTOCOMMIT = 0` —— 这些本该是微秒级的语句，
**平均 0.30 秒、最高 2.94 秒**，占了该主机全部慢日志条目的 21%。

两点判断：

1. 两类语句的平均耗时几乎相同（0.310 vs 0.296 秒）。**如果是数据库慢，`SELECT VERSION()` 不该跟
   长事务扫描一样慢**；耗时与语句复杂度无关，说明瓶颈在该主机侧或连接建立路径，不在被查的库。
2. 出现握手语句本身说明**每次轮询都新建连接**（没有连接池复用）。

影响可控（没有一条超过 3.3 秒，扫描行数总计仅约 50 万），但它每周往全 fleet 慢日志里写 2,899 条噪声
——**采集平台污染了它自己采集的数据**。建议后续核实该主机的连接复用配置，本次不做变更。

---

## 五、行动项

| 编号 | 事项 | 优先级 | 归属 | 状态 |
|---|---|---|---|---|
| C-01 | `avgPrepTime` 两条改 join 订单表走索引 | P1 | DBA（本仓库） | **已合并 `740db42`，待 dbtools02 重启容器** |
| C-02 | 周度分诊补一个「扫描行数」维度，覆盖 <1s 但高扫描量的查询 | P2 | DBA | 待做 |
| C-03 | 核实 idbcollect01 是否每次轮询新建连接，评估连接池复用 | P3 | DBA | 待做 |
| — | L0 TOP10 中其余 7 条均为应用账号，处置见 -0901 / -0901-B | — | 张晓松等 | 不变 |
