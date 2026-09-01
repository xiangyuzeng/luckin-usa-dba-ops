# LKUS MySQL 慢查询分析报告（续）—— L0 档剩余 9 条

| 项目 | 内容 |
|------|------|
| 报告编号 | LCNA-DBA-SQL-2026-0901-B |
| 前序报告 | LCNA-DBA-SQL-2026-0901（TOP3，`LKUS-slow-query-report-L0-2026-09-01.md`） |
| 出具日期 | 2026-09-01 |
| 出具人 | 曾翔宇（DBA / Infrastructure） |
| 分析对象 | 分析台账中 status=`pending` 的 9 条 L0 慢 SQL 指纹 |
| 数据窗口 | 2026-08-25 ~ 2026-09-01（7 天日差分） |
| 数据来源 | `ldas01` 采集表 + 各实例 `performance_schema` digest + CloudWatch 慢日志原文 + 现场 `EXPLAIN` + CloudWatch `AWS/RDS` + 现场计时复现 |

---

## 摘要

9 条合计 7 天新增 DB 时间 **899.9 秒**，占 L0 全部 ≥1s 慢 SQL DB 时间（10,060.1 s）的 **8.9%**。
按**根因**归并后只剩四类，其中两类是同一批任务的多条 SQL：

| 分组 | 条数 | 7d DB时间 | 占本批 | 共同根因 | 归属 |
|---|---:|---:|---:|---|---|
| **A. 门店运营看板取数** | 3 | 366.5 s | 40.7% | 90 天窗口导致 `t_order` 全表扫；且同一份扫描做了两遍 | **DBA 自有（我们自己）** |
| **B. 02:00 财务对账任务** | 3 | 258.4 s | 28.7% | `checking_date` 无索引，而表上存在名字只差几个字母的 `checking_time` 索引 | 张晓松 |
| **C. 争用受害者** | 1 | 191.7 s | 21.3% | SQL 本身 27 ms，慢在执行时刻（整点）的资源争用 | 张晓松 |
| **D. 已停跑 / 计划合理** | 2 | 83.3 s | 9.3% | 一条 08-28 起已停止执行；一条执行计划本身没问题 | 张晓松 |

**最值得说的三件事**

1. **占比最高的一组是我们自己的。** `store-ops` 看板的取数容器（`diagtools@10.238.3.43` = dbtools02）每天 05:00 UTC 在 `salesorder` 上扫 600 万行，其中 `spu_name` 和 `spu_code` 两条查询**除了 GROUP BY 的那一列完全相同**，同一份 209 万行扫了两遍。代码在我们自己的仓库里，改起来不用求研发。
2. **B 组三条是同一个近似索引陷阱。** `t_finance_receipt` / `t_finance_refund` 上都有 `idx_checking_time_and_status(checking_time, status)`，而查询过滤的是 `checking_date` + `checking_status` —— 列名只差几个字母，索引全部落空，`EXPLAIN` 的 `possible_keys` 直接是 `NULL`。三条加一个索引一起修好。
3. **C 组那条不要去优化 SQL。** `cdpactivity` 的 `DISTINCTROW` 记录均值 1.65 s，我现在连上去连跑三次是 **0.027 / 0.027 / 0.029 秒**，差 60 倍。慢的不是 SQL，是它执行的时刻（每小时整点，与全 fleet 整点批量重合）。

---

# A 组 · 门店运营看板取数（DBA 自有，3 条）

## SQL-05 / SQL-06 · SPU 日销量（`spu_name` 与 `spu_code` 双胞胎）

> 这两条是同一份数据扫两遍，因此合并为一个案卷；台账中仍是两条独立指纹
> `e5a8e692…`（spu_name）与 `09d7feb6…`（spu_code）。

### 1. 所在数据库实例、Schema

| 项目 | 内容 |
|------|------|
| 实例标识 | `aws-luckyus-salesorder-rw` |
| 规格 | db.t4g.medium（2 vCPU / 4 GiB），Multi-AZ，40 GB gp3 / 3000 IOPS |
| 引擎版本 | MySQL 8.4.10 |
| Schema | `luckyus_sales_order` |
| 服务等级 | L0 核心业务（分级表归属：国际营销增长 / 张晓松） |
| **实际调用方** | **DBA 自有** —— 账号 `diagtools`，来源 `10.238.3.43`（dbtools02-prod-usa-aws 上的看板刷新容器） |
| 代码位置 | `/app/luckin-store-ops-dashboard/pipeline/collectors/orders.py`<br>`fetch_spu_daily()` L108 → SQL-05；`fetch_spu_code_daily()` L134 → SQL-06 |
| 调用入口 | `pipeline/frontend_formatter.py` L167，窗口 `RETAIN_DAYS`（环境变量，默认 **90**） |
| 执行频率 | 每天 1 次，**05:00 UTC** |

### 2. SQL 完整内容

CloudWatch 慢日志 `2026-09-01T05:00:34.465821Z`（SQL-05）与 `05:00:56.202126Z`（SQL-06）原文：

```sql
-- SQL-05  Query_time: 20.569473  Rows_sent: 72520  Rows_examined: 2090481
SELECT o.shop_id,
       DATE(CONVERT_TZ(o.pay_time, 'UTC', 'US/Eastern')) AS et_date,
       i.spu_name,
       SUM(i.sku_num)                                    AS qty
  FROM luckyus_sales_order.t_order o
  JOIN luckyus_sales_order.t_order_item i ON i.order_id = o.id
 WHERE o.tenant = 'LKUS' AND o.status = 90
   AND o.pay_time >= UTC_TIMESTAMP() - INTERVAL 90 DAY
   AND i.spu_name IS NOT NULL
 GROUP BY o.shop_id, et_date, i.spu_name
HAVING qty > 0
 ORDER BY o.shop_id, et_date, qty DESC
 LIMIT 500000;

-- SQL-06  Query_time: 20.152167  Rows_sent: 72521  Rows_examined: 2090482
--         与上面逐字相同，只有标记 ▲ 的两处不同
SELECT o.shop_id,
       DATE(CONVERT_TZ(o.pay_time, 'UTC', 'US/Eastern')) AS et_date,
       i.spu_code,                                        -- ▲
       SUM(i.sku_num)                                    AS qty
  FROM luckyus_sales_order.t_order o
  JOIN luckyus_sales_order.t_order_item i ON i.order_id = o.id
 WHERE o.tenant = 'LKUS' AND o.status = 90
   AND o.pay_time >= UTC_TIMESTAMP() - INTERVAL 90 DAY
   AND i.spu_code IS NOT NULL                             -- ▲
 GROUP BY o.shop_id, et_date, i.spu_code                   -- ▲
HAVING qty > 0
 ORDER BY o.shop_id, et_date
 LIMIT 500000;
```

`performance_schema` 累计（首见 2026-07-24，末次 2026-09-01 05:00）：

| 指标 | SQL-05（spu_name） | SQL-06（spu_code） |
|---|---:|---:|
| COUNT_STAR | 38 | 38 |
| SUM_TIMER_WAIT | **1,449.5 s** | **828.2 s** |
| AVG / MAX | 38.14 s / 48.84 s | 21.80 s / 31.92 s |
| SUM_ROWS_SENT | 2,559,557 | 2,559,600 |
| SUM_ROWS_EXAMINED | 74,866,034 | 74,866,093 |
| SUM_NO_INDEX_USED | 38（100%） | 38（100%） |
| SUM_SELECT_SCAN | 38（100%） | 38（100%） |

> 两条的 `SUM_ROWS_EXAMINED` 只差 **59 行**，`SUM_ROWS_SENT` 只差 **43 行** —— 这就是「同一份数据扫两遍」的量化证据。

### 3. 表内容及表上当前索引情况

| 表 | 注释 | 行数 | 数据 | 索引 |
|---|---|---:|---:|---:|
| `t_order` | 订单主表 | 1,335,649 | 413.0 MB | 297.8 MB |
| `t_order_item` | 订单行表 | 1,776,937 | **3,086.0 MB** | 42.6 MB |

`t_order_item` 单行平均约 1.8 KB（含 `commodity_info` 等宽字段），是本查询 IO 成本的主要来源。

**`t_order` 索引**

| 索引名 | 列 | 基数 |
|---|---|---:|
| PRIMARY | id | 1,326,239 |
| idx_pay_time | pay_time | 1,335,650 |
| idx_create_time | create_time, tenant, display_flag | 1,282,296 |
| idx_finish_time | finish_time, tenant | 1,301,151 |
| idx_shop_unfinish | shop_id, tenant, display_flag, create_time | 1,335,650 |
| idx_user_no | user_no, tenant, display_flag | 395,175 |
| idx_cancel_time | cancel_time, tenant | 51,658 |

**`t_order_item` 索引**：只有 `PRIMARY(id)` 与 `idx_order_id(order_id)` 两个。

> `t_order` 上**没有** `(tenant, status, pay_time)` 这类能同时吃下本查询三个过滤条件的复合索引；`idx_pay_time` 是单列索引。

### 4. SQL 执行计划

| id | table | type | possible_keys | key | key_len | ref | rows | filtered | Extra |
|---|---|---|---|---|---:|---|---:|---:|---|
| 1 | o | **ALL** | PRIMARY, idx_pay_time | **NULL** | NULL | NULL | 1,335,653 | 0.50 | Using where; **Using temporary; Using filesort** |
| 1 | i | ref | idx_order_id | idx_order_id | 8 | `o.id` | 1 | 100.00 | — |

**计划解读**

- `o` 的 `possible_keys` 里有 `idx_pay_time`，但**优化器主动放弃**了它：`pay_time >= now-90d` 覆盖了 `t_order` 绝大部分行，走索引再回表比直接全表扫更贵。这是正确的选择，问题出在**窗口本身太宽**。
- `i` 走 `idx_order_id` 逐单查回，每单约 1 行 —— 这一步没有问题，但每行要读约 1.8 KB 的宽行。
- `Using temporary; Using filesort`：`GROUP BY shop_id, et_date, <spu>` 里 `et_date` 是 `CONVERT_TZ` 的计算结果，任何索引都无法支撑，必然建临时表再排序。
- 单次实际：扫 **2,090,482** 行、返回 **72,521** 行、耗时 20~48 秒。两条加起来每天约 **60 秒**、扫 **418 万行**。

### 5. 问题分析

**（1）两条查询是同一份扫描的两个投影，代价翻倍**

`orders.py` 的代码注释自己写明了原因：

> *"The TOP-N display path uses spu_name (human-readable); the materialLossRate path needs spu_code (matches t_formula_average's join key). Kept as a separate collector so the two consumers stay decoupled."*

解耦本身是合理的设计取向，但它的代价是**每天在生产库上多做一次 209 万行的全表扫、多花 22 秒**。两个消费者要的是同一批订单行的同一个聚合值，只是分组键不同。

**（2）90 天窗口是全表扫的直接原因**

`RETAIN_DAYS` 默认 90。`t_order` 共 133 万行，90 天窗口几乎覆盖全表，于是 `idx_pay_time` 失去意义。同族对照可以证明这一点：`efficiency.py` 里还有一条**结构完全一样、只是窗口 3 天**的半小时粒度查询，实测 **0.15 秒 / 扫 27,523 行**（CloudWatch `05:00:35`）—— 同一份代码，窗口从 3 天变 90 天，成本涨 **68 倍**。

**（3）每天重算 90 天是架构层的浪费**

看板每天全量重算过去 90 天的聚合，而其中 89 天的数据是不会再变的。真正需要每天重算的只有最近 1~2 天（考虑晚到的订单状态变更）。

**（4）资源影响**

05:00 UTC 期间 `salesorder` CPU 峰值 **24.2%**（基线 8~11%），`ReadLatency` 从 0.9~2.5 ms 抬到 **4.2 ms**。`CPUCreditBalance` 全程满值 576，未触及积分风险。影响可控，但每天扫掉 400 多万行宽行对 4 GiB 内存实例的 buffer pool 是明确的冲刷。

### 6. 优化建议

| 优先级 | 建议 | 归属 | 预期收益 | 风险 |
|---|---|---|---|---|
| **B-03** P1 | **合并两条查询**：`GROUP BY o.shop_id, et_date, i.spu_code, i.spu_name` 一次取回，Python 侧再按各自维度聚合出两份结果 | DBA（本仓库） | 每天省一次 209 万行全表扫，**-22 s/天** | 需在 Python 侧对 spu_name 再聚合一次（同名不同 code 会拆成多行）。实测两条返回行数只差 43，合并后行数几乎不变 |
| **B-04** P1 | **改增量收集**：每天只取最近 2~3 天重算，与已存 payload 合并，不再每天重算 90 天。过渡措施：先把 `RETAIN_DAYS` 环境变量降到实际需要的天数（一行改动，立即见效） | DBA（本仓库） | 窗口 90→3 天，同族查询实测 **-99%**（20 s → 0.15 s） | 需要 payload 合并逻辑；历史回补要单独处理 |
| **B-05** P2 | **错峰**：刷新时间从 05:00 UTC 挪到 06:30 UTC，避开每日批量窗口 | DBA（本仓库） | 削峰，不降总量 | 看板数据新鲜度延后 1.5 小时，需确认可接受 |
| B-11 P3 | 若 B-04 短期做不了，可评估给 `t_order` 加 `(tenant, status, pay_time)` 复合索引 | DBA | 有限 —— 90 天窗口下优化器仍可能选全表扫 | 133 万行表新增约 40 MB；收益不确定，**建议先做 B-04 再评估** |

---

## SQL-11 · 门店效率（接单/制作时长）取数

### 1. 所在数据库实例、Schema

同 SQL-05/06（`aws-luckyus-salesorder-rw` / `luckyus_sales_order` / `diagtools@10.238.3.43`）。
代码位置：`/app/luckin-store-ops-dashboard/pipeline/collectors/efficiency.py` L68~74（`orders.py` L88~94 有同族实现）。执行频率：每天 1 次，05:00 UTC。

### 2. SQL 完整内容

CloudWatch 慢日志 `2026-09-01T05:00:13.782039Z`：

```sql
# Query_time: 7.995776  Rows_sent: 1791  Rows_examined: 1859578
SELECT o.shop_id,
       DATE(CONVERT_TZ(o.pay_time, 'UTC', 'US/Eastern'))         AS et_date,
       COUNT(*)                                                  AS orders,
       SUM(TIMESTAMPDIFF(SECOND, o.pay_time, m.accept_time))     AS accept_secs,
       SUM(TIMESTAMPDIFF(SECOND, m.accept_time, m.finish_time))  AS make_secs
  FROM luckyus_sales_order.t_order o
  JOIN luckyus_sales_order.t_order_make m ON m.order_id = o.id
 WHERE o.tenant = 'LKUS' AND o.status = 90
   AND o.pay_time >= UTC_TIMESTAMP() - INTERVAL 90 DAY
   AND m.accept_time IS NOT NULL AND m.finish_time IS NOT NULL
 GROUP BY o.shop_id, et_date
 ORDER BY o.shop_id, et_date
 LIMIT 100000;
```

`performance_schema` 累计：38 次 / **200.8 s** / 平均 5.28 s / 最大 9.67 s / 返回 64,743 行 / 扫描 66,280,734 行 / `SUM_SELECT_SCAN` 38（100%）。

### 3. 表内容及表上当前索引情况

| 表 | 注释 | 行数 | 数据 | 索引 |
|---|---|---:|---:|---:|
| `t_order` | 订单主表 | 1,335,649 | 413.0 MB | 297.8 MB |
| `t_order_make` | 订单制作表 | 1,447,423 | 213.8 MB | 41.6 MB |

`t_order_make` 索引：`PRIMARY(id)`、`uniq_order_id(order_id, tenant)` —— 只有两个，`accept_time` / `finish_time` 无索引（本查询只用它们做 `IS NOT NULL` 判断，无需索引）。

### 4. SQL 执行计划

| id | table | type | possible_keys | key | key_len | ref | rows | filtered | Extra |
|---|---|---|---|---|---:|---|---:|---:|---|
| 1 | o | **ALL** | PRIMARY, idx_pay_time | **NULL** | NULL | NULL | 1,335,653 | 0.50 | Using where; Using temporary; Using filesort |
| 1 | m | ref | uniq_order_id | uniq_order_id | 8 | `o.id` | 1 | 81.00 | Using index condition; Using where |

与 SQL-05/06 同型：`o` 全表扫（90 天窗口过宽），`m` 走唯一索引逐单查回。

### 5. 问题分析

根因与 SQL-05/06 完全相同 —— **90 天窗口导致 `t_order` 全表扫**，加上 `CONVERT_TZ` 计算列导致的临时表 + filesort。

区别在于返回行数少得多（1,791 行 vs 72,521 行），所以耗时更低（5.28 s vs 38 s）；扫描量仍高达 186 万行。

同族对照再次印证窗口是主因：`efficiency.py` 里 3 天窗口的半小时粒度版本实测 **0.15 秒 / 27,523 行**。

### 6. 优化建议

与 A 组统一处理：**B-04（改增量 / 缩窗口）**、**B-05（错峰）**。本条不需要单独的索引改造。

---

# B 组 · 02:00 财务对账任务（3 条）

三条来自同一个每天 02:00 UTC 的财务对账任务，账号 `isalesorderservice_A_o`，按租户循环执行（实测出现 `LKUS` / `LKMY` / `IQA1` / `IQA2` 四个租户）。

## 🔴 共同根因：近似索引陷阱

`t_finance_receipt` 与 `t_finance_refund` 上都存在索引 **`idx_checking_time_and_status(checking_time, status)`**，
而三条查询过滤的列是 **`checking_date`**（不是 `checking_time`）配 **`checking_status`**（不是 `status`，仅退款表）。

列名只差几个字母，索引全部落空 —— 三条 `EXPLAIN` 的 `possible_keys` 有两条直接是 `NULL`。这类「看起来有索引，实际一个也用不上」的情况，靠看建表语句很难发现，必须跑 `EXPLAIN` 才会暴露。

## SQL-07 · 退款对账计数

### 1. 所在数据库实例、Schema
`aws-luckyus-salesorder-rw`（db.t4g.medium / 8.4.10）· `luckyus_sales_order` · L0 · 张晓松
账号 `isalesorderservice_A_o`，每天 03:00 UTC 附近，7 天内 80 次。

### 2. SQL 完整内容
CloudWatch 慢日志 `2026-09-01T03:00:04.635056Z`：
```sql
# Query_time: 4.599620  Rows_sent: 1  Rows_examined: 21107
SELECT COUNT(*) AS total
  FROM t_finance_refund
 WHERE deleted = 0
   AND (checking_status = 1 AND checking_date BETWEEN '2026-08-25 03:00:00.03' AND '2026-09-01 03:00:00.03')
   AND t_finance_refund.tenant = 'LKUS';
```
7 天窗口：80 次 / 93.9 s / 平均 1.17 s / 最大 5.07 s / 每次扫 20,597 行返回 1 行 / 未走索引 80 次。
（本周该指纹计数发生过重置，采集侧标记 `首见/重置 = 1`。）

### 3. 表内容及表上当前索引情况
`t_finance_refund` 退款信息表：**21,572 行 / 9.5 MB 数据 + 9.3 MB 索引**。

| 索引名 | 列 | 基数 |
|---|---|---:|
| PRIMARY | id | 21,488 |
| uniq_refund_no | refund_no | 21,572 |
| idx_create_time | create_time, status | 13,816 |
| idx_modify_time_and_status | modify_time, status | 1,409 |
| **idx_checking_time_and_status** | **checking_time, status** | 1,321 |
| idx_approve_time | approve_time | 1,373 |
| idx_refund_success_time | refund_success_time | 13,610 |
| idx_refund_object_id | refund_object_id | 21,572 |
| idx_tp_serial_no | tp_serial_no | 6,625 |
| idx_user_no | user_no | 15,859 |

> 10 个索引（索引体积已接近数据体积），**却没有一个能用于 `checking_date` + `checking_status`**。

### 4. SQL 执行计划

| id | table | type | possible_keys | key | rows | filtered | Extra |
|---|---|---|---|---|---:|---:|---|
| 1 | t_finance_refund | **ALL** | **NULL** | NULL | 21,572 | 0.01 | Using where |

`possible_keys = NULL` —— 优化器连一个候选索引都找不到，只能全表扫。

### 5. 问题分析
- 表只有 2.1 万行 / 9.5 MB，全表扫本身应该在**毫秒级**。实测平均 1.17 s、峰值 4.6 s，说明**主要成本来自 02:00~03:00 批量窗口的资源争用**（该时段 `salesorder` CPU 峰值 28.4%、`ReadLatency` 从 0.9 ms 抬到 6.1 ms）。
- 但「无索引可用」是确凿的结构性缺陷：表一旦增长，这条会线性变慢，且它现在就把每次执行的 CPU 白白花在扫全表上。
- 该表有 10 个索引、索引体积 9.3 MB ≈ 数据体积 9.5 MB，属于**索引偏多但没建在点子上**。

### 6. 优化建议

| 优先级 | 建议 | 归属 | 预期收益 | 风险 |
|---|---|---|---|---|
| **B-06** P1 | 加索引 `idx_tenant_ckstatus_ckdate(tenant, checking_status, deleted, checking_date)` —— 前三列等值、末列范围 | DBA | 扫 20,597 行 → 命中行级别；消除全表扫 | 2.1 万行小表，在线 DDL 秒级完成 |
| **B-07** P2 | 与研发确认 `checking_time` vs `checking_date`、`status` vs `checking_status` 的语义差异，以及 10 个索引中是否有可下线的冗余索引 | DBA + 张晓松 | 减少写放大与索引空间 | 需业务确认，勿擅自删索引 |

---

## SQL-08 · 收款对账明细查询

### 1. 所在数据库实例、Schema
同上实例 / Schema。账号 `isalesorderservice_A_o`，来源 `10.238.35.249`，每天 **02:01 UTC**，按租户循环，7 天内 14 次（`performance_schema` 累计 58 次）。

### 2. SQL 完整内容
CloudWatch 慢日志 `2026-09-01T02:01:41.958169Z`：
```sql
# Query_time: 5.288455  Rows_sent: 31  Rows_examined: 1362124
SELECT id, receipt_no, receipt_account_no, status, receipt_method_no, payment_method,
       tp_serial_no, third_serial_no, receipt_object_type, order_no, user_no,
       receipt_amount, discount_amount, currency, receipt_date, checking_date,
       checking_amount, checking_result, checking_failed_reason, checking_time,
       difference_amount, create_time, modify_time, creator_id, creator_name,
       modifier_id, modifier_name, remark, tenant
  FROM t_finance_receipt
 WHERE deleted = 0
   AND (status = 1 AND checking_date BETWEEN '2026-08-25 02:01:35.818' AND '2026-09-01 02:01:35.818')
   AND t_finance_receipt.tenant = 'IQA2'
 ORDER BY modify_time DESC
 LIMIT 10000;
```
`performance_schema` 累计：58 次 / **328.7 s** / 平均 5.67 s / 最大 6.68 s / 返回 208,743 行 / 扫描 **73,379,666** 行 / `SUM_SELECT_SCAN` 58（100%）。

### 3. 表内容及表上当前索引情况
`t_finance_receipt` 收款信息表：**1,307,351 行 / 260.8 MB 数据 + 334.1 MB 索引**（索引比数据还大）。

| 索引名 | 列 | 基数 |
|---|---|---:|
| PRIMARY | id | 1,270,627 |
| uniq_receipt_no | receipt_no | 1,307,354 |
| idx_order_no | order_no | 1,307,354 |
| idx_tp_serial_no | tp_serial_no | 1,307,354 |
| idx_user_no | user_no | 323,935 |
| idx_receipt_date | receipt_date | 1,150 |
| **idx_checking_time_and_status** | **checking_time, status** | 33,706 |
| idx_modify_time_and_status | modify_time, status | 101,756 |

> 同样：`checking_date` 无索引，`tenant` 无索引。

### 4. SQL 执行计划

| id | table | type | possible_keys | key | key_len | rows | filtered | Extra |
|---|---|---|---|---|---:|---:|---:|---|
| 1 | t_finance_receipt | **index** | **NULL** | idx_modify_time_and_status | 5 | 10,000 | 0.01 | Using where; **Backward index scan** |

**计划解读 —— 与前序报告 SQL-03 同一类陷阱**

`possible_keys = NULL` 说明 `WHERE` 条件没有任何索引可用。优化器转而利用 `ORDER BY modify_time DESC`：沿 `idx_modify_time_and_status` **倒序扫描**，指望「很快就能凑满 `LIMIT 10000`」。

但实际只有 **31 行**满足条件，于是它把整个 `modify_time` 索引倒着走完（**1,362,124 行**）也没凑满 LIMIT。`rows = 10000` 是优化器按 LIMIT 给出的乐观估算，与实际相差 136 倍。

> 规律：`ORDER BY <有索引列> + LIMIT N` 配上**无索引的 WHERE 条件**时，LIMIT 给得越大、命中率越低，这个陷阱越贵。

### 5. 问题分析
- 每次扫 136 万行（该租户下的整张表）返回 31 行，选择率约 **0.002%**。
- 查询取回 **29 个字段**，包含 `checking_failed_reason`、`remark` 等宽字段，回表开销显著。
- `IQA2` / `IQA1` 是测试类租户，其数据量远小于 `LKUS`，但因为没有 `tenant` 索引，**每个租户的查询都要扫全表**——租户越多，这条越贵。
- 02:00 UTC 期间该实例 `ReadLatency` 达 6.1 ms（基线 0.9~2.5 ms），CPU 峰值 28.4%。

### 6. 优化建议

| 优先级 | 建议 | 归属 | 预期收益 | 风险 |
|---|---|---|---|---|
| **B-08** P1 | 加索引 `idx_tenant_status_ckdate(tenant, status, deleted, checking_date)` —— 一并修好 SQL-08 与 SQL-09 | DBA | 扫 136 万行 → 几十行，**5.7 s → 毫秒级** | 131 万行 / 595 MB 表，`ALGORITHM=INPLACE, LOCK=NONE` 在线加索引，预计新增约 50 MB。建议低峰执行，需走变更申请 |
| B-12 P2 | 收窄 `SELECT` 列，去掉对账不需要的 `remark` / `creator_name` / `modifier_name` 等宽字段 | 张晓松 | 减少回表与传输 | 无 |

---

## SQL-09 · 收款对账计数（与 SQL-08 配套）

### 1. 所在数据库实例、Schema
同 SQL-08。同一任务、同一秒（`02:01:36` 的 COUNT → `02:01:41` 的 SELECT），是「先 COUNT 再取列表」的分页写法。7 天内 16 次（`performance_schema` 累计 80 次）。

### 2. SQL 完整内容
CloudWatch 慢日志 `2026-09-01T02:01:36.668728Z`：
```sql
# Query_time: 0.849427  Rows_sent: 1  Rows_examined: 1362124
SELECT COUNT(*) AS total
  FROM t_finance_receipt
 WHERE deleted = 0
   AND (status = 1 AND checking_date BETWEEN '2026-08-25 02:01:35.818' AND '2026-09-01 02:01:35.818')
   AND t_finance_receipt.tenant = 'IQA2';
```
`performance_schema` 累计：80 次 / **292.1 s** / 平均 3.65 s / 最大 9.65 s / 返回 80 行 / 扫描 **101,129,788 行**（1.01 亿）/ 未走索引 80 次 / 全表扫 80 次。

### 3. 表内容及表上当前索引情况
同 SQL-08（`t_finance_receipt`，1,307,351 行，8 个索引，`checking_date` 与 `tenant` 均无索引）。

### 4. SQL 执行计划

| id | table | type | possible_keys | key | rows | filtered | Extra |
|---|---|---|---|---|---:|---:|---|
| 1 | t_finance_receipt | **ALL** | **NULL** | NULL | 1,307,355 | 0.01 | Using where |

### 5. 问题分析
- **80 次执行、扫描 1.01 亿行，只为得到 80 个数字。** 这是本批 9 条里单位产出成本最高的一条。
- 与 SQL-08 是同一个 `WHERE`，因此 B-08 的索引可以同时修好两条。
- 更深一层：结果集只有 31 行，却先跑一次 COUNT 再跑一次 SELECT，**把同一次全表扫做了两遍**。在这种「结果集只有几十行」的场景里，先 COUNT 的分页写法没有价值。

### 6. 优化建议

| 优先级 | 建议 | 归属 | 预期收益 | 风险 |
|---|---|---|---|---|
| **B-08** P1 | 同 SQL-08 的复合索引，一并解决 | DBA | 1.01 亿行扫描 → 可忽略 | 见 SQL-08 |
| B-09 P2 | 去掉配套的 COUNT：先执行 SELECT，用返回行数代替 total（结果集只有几十行，且 `LIMIT 10000` 远大于实际命中数） | 张晓松 | 再省一次同样的扫描 | 需确认前端分页是否真的需要总数 |

---

# C 组 · 争用受害者（1 条）

## SQL-04 · 触达活动实例去重

### 1. 所在数据库实例、Schema

| 项目 | 内容 |
|---|---|
| 实例标识 | `aws-luckyus-cdpactivity-rw` |
| 规格 | db.t4g.medium（2 vCPU / 4 GiB），Multi-AZ，80 GB gp3 / 3000 IOPS |
| 引擎版本 | MySQL 8.4.10 |
| Schema | `luckyus_cdp_activity` |
| 服务等级 | L0 核心业务 / 国际营销增长 / 张晓松 |
| 执行频率 | **每小时整点（:00）**，末次 2026-09-01 15:00:01 |

### 2. SQL 完整内容

采集表中的完整指纹（162 字符，未截断）：
```sql
SELECT DISTINCTROW activity_id
  FROM t_contact_activity_instance_record
 WHERE create_time >= ? AND create_time <= ? AND tenant = ?
 ORDER BY create_time;
```
`performance_schema` 累计（首见 2026-07-21，末次 2026-09-01 15:00）：550 次 / **905.4 s** / 平均 **1.65 s** / 最大 3.14 s / 返回 22,959 行 / 扫描 6,789,496 行 / 全表扫 550 次（100%）/ 排序 22,959 行。
7 天窗口：104 次 / 191.7 s / 平均 1.84 s / 每次扫 12,337 行。

### 3. 表内容及表上当前索引情况

`t_contact_activity_instance_record` 触达活动实例记录：**13,331 行（实测）/ 3.5 MB 数据 + 3.5 MB 索引**。

| 索引名 | 列 |
|---|---|
| PRIMARY | id |
| idx_activity_id | activity_id |
| idx_activity_no | activity_no |
| idx_instance_no | activity_instance_no |

> `create_time` 与 `tenant` **均无索引**。

### 4. SQL 执行计划

| id | table | type | possible_keys | key | key_len | rows | filtered | Extra |
|---|---|---|---|---|---:|---:|---:|---|
| 1 | t_contact_activity_instance_record | index | idx_activity_id | idx_activity_id | 8 | 12,557 | 1.11 | Using where; **Using temporary; Using filesort** |

优化器用 `idx_activity_id` 做全索引扫描（只为避免更贵的全表扫），`create_time` 范围与 `tenant` 条件只能在扫描后逐行过滤；`DISTINCTROW` + `ORDER BY create_time` 触发临时表 + filesort。

### 5. 问题分析

**🔴 现场复现：这条 SQL 本身不慢。**

用相同语句在该实例上连跑三次（2026-09-01 15:5x UTC，非整点）：

| 次数 | 耗时 |
|---|---:|
| 1 | **0.027 s** |
| 2 | **0.027 s** |
| 3 | **0.029 s** |

而 `performance_schema` 记录的平均耗时是 **1.65 s** —— **相差约 60 倍**。

3.5 MB 的表做一次全索引扫描，本来就该是几十毫秒。因此 1.65 s 里绝大部分**不是查询自身的开销，而是它执行那一刻的资源争用**：该任务固定在**每小时整点（:00）**触发，与全 fleet 的整点批量窗口完全重合（`cdpactivity` CPU 峰值在 04:00 达 34.2%、09:00~12:00 达 19~37%，基线仅 7~8%）。

**这条的正确结论是：不要按「慢 SQL」去优化它。** 把它当成 SQL 问题去加索引、改写语句，最多省掉那 27 毫秒，1.65 s 的观测值不会有明显变化。

**次要问题（仍值得顺手修）**：`create_time` / `tenant` 无索引确实是结构缺陷。现在表只有 1.3 万行所以无感，一旦触达活动放量到百万级，这条会真正变慢。

### 6. 优化建议

| 优先级 | 建议 | 归属 | 预期收益 | 风险 |
|---|---|---|---|---|
| **B-01** P2 | 加索引 `idx_tenant_create_time(tenant, create_time)` —— 等值 + 范围，同时消除 filesort | DBA | 27 ms → 个位数毫秒；更重要的是消除表增长后的隐患 | 3.5 MB 表，在线 DDL 秒级完成 |
| **B-02** P2 | **错峰**：触发时间从整点 `:00` 挪到 `:07` 或 `:23` 之类的非整点 | 张晓松 | 这才是把观测耗时从 1.65 s 降下来的手段 | 需确认下游对整点对齐无依赖 |
| — | ❌ **不建议**为这条改写 SQL 或做深度优化 | — | — | 会把工时花在 27 ms 上 |

---

# D 组 · 已停跑 / 计划合理（2 条）

## SQL-10 · 门店任务量统计（**已停止执行**）

### 1. 所在数据库实例、Schema
`aws-luckyus-salesorder-rw` / `luckyus_sales_order` / L0 / 张晓松。

### 2. SQL 完整内容
采集表完整指纹（684 字符）：
```sql
SELECT o.shop_id AS deptId,
       SUM(CASE WHEN i.spu_mode = ? THEN ? ELSE ? END) AS taskSelfQuantity,
       SUM(CASE WHEN i.spu_mode = ? THEN ? ELSE ? END) AS taskPurchaseQuantity,
       date_format(CONVERT_TZ(o.finish_time, ?, ...), ?)         AS dateStr
  FROM t_order o LEFT JOIN t_order_item i ON o.id = i.order_id
 WHERE o.order_category = ? AND o.status = ? AND i.return_type IN (...)
   AND o.finish_time >= ? AND o.finish_time < ? AND o.order_type = ?
   AND o.shop_id IN (...) AND o.tenant = ?
 GROUP BY o.shop_id, date_format(CONVERT_TZ(o.finish_time, ?, ...), ?);
```

**🔴 `performance_schema`：`FIRST_SEEN` 2026-07-28 20:17，`LAST_SEEN` 2026-08-28 01:51 —— 距今已 4 天没有执行过。**
累计 34 次 / 127.0 s / 平均 3.74 s / 最大 16.46 s / 返回 30 行 / 扫描 3,028,668 行。
7 天窗口里记到的 55.7 s，全部来自 08-28 及以前的执行。

### 3. 表内容及表上当前索引情况
`t_order`（1,335,649 行）+ `t_order_item`（1,776,937 行 / 3,086 MB），索引同 SQL-05/06 一节。

### 4. SQL 执行计划

| id | table | type | possible_keys | key | key_len | rows | filtered | Extra |
|---|---|---|---|---|---:|---:|---:|---|
| 1 | o | range | PRIMARY, idx_finish_time, idx_shop_unfinish | idx_shop_unfinish | 50 | *(注)* | 1.67 | Using index condition; Using where; Using temporary |
| 1 | i | ref | idx_order_id | idx_order_id | 8 | 1 | 20.00 | Using where |

*注：EXPLAIN 用的是构造的 `shop_id` 列表，`rows` 估算不具代表性；以实测每次扫描 89,078 行为准。*

计划走了 `idx_shop_unfinish(shop_id, tenant, display_flag, create_time)` 的范围扫描，但过滤条件用的是 `finish_time` 而非索引末列的 `create_time`，因此索引只吃到 `shop_id + tenant` 两列，`finish_time` 只能扫描后过滤。

### 5. 问题分析
计划不算差（走了索引、没有全表扫），每次扫 89,078 行返回约 1 行，主要成本是 `CONVERT_TZ` 计算列导致的临时表。

**但该 SQL 自 2026-08-28 起已不再执行**，投入优化没有意义。

### 6. 优化建议

| 优先级 | 建议 | 归属 |
|---|---|---|
| — | **不投入优化。** 台账登记为 `accepted`，`recheck_after = 2026-10-01`；若届时重新出现在榜单上，再按 `idx_finish_time(finish_time, tenant)` 方向评估 | DBA |
| B-13 P3 | 顺带与研发确认该功能是否已下线，若已下线可清理对应定时任务配置 | 张晓松 |

---

## SQL-12 · 交易流水日批拉取（**执行计划本身合理**）

### 1. 所在数据库实例、Schema

| 项目 | 内容 |
|---|---|
| 实例标识 | `aws-luckyus-salespayment-rw` |
| 规格 | db.t4g.medium（2 vCPU / 4 GiB），Multi-AZ，20 GB gp3 |
| 引擎版本 | MySQL 8.4.10 |
| Schema | `luckyus_sales_payment` |
| 服务等级 | L0 核心业务 / 国际营销增长 / 张晓松 |
| 执行频率 | 每天 1 次，**03:00 UTC**（末次 2026-09-01 03:00:01） |

### 2. SQL 完整内容
采集表完整指纹（696 字符）：
```sql
SELECT id, tenant, channel_id, channel_scene_id, channel_scene_account_id, trade_no,
       order_type, order_id, order_subject, order_body, amount, currency,
       request_extra_data, third_trade_no, third_request_time, third_response_time,
       third_notify_time, status, finish_time, result_code, result_message,
       origin_result_code, origin_result_message, response_extra_data,
       create_time, modify_time, version, user_no, fee, fee_currency_code,
       fee_query_times, app_version, source, guest_flag
  FROM t_trade
 WHERE status IN (...) AND create_time >= ? AND create_time <= ?
 ORDER BY create_time, id
 LIMIT ?;
```
`performance_schema` 累计（首见 2026-07-23，末次 2026-09-01 03:00）：41 次 / **120.6 s** / 平均 2.94 s / 最大 4.31 s / 返回 3,128 行 / 扫描 437,497 行 / 全表扫 **0** 次。

### 3. 表内容及表上当前索引情况
`t_trade` 交易流水表：**1,420,350 行 / 410.0 MB 数据 + 294.3 MB 索引**。

| 索引名 | 列 |
|---|---|
| PRIMARY | id |
| uniq_trade_no | trade_no |
| **idx_create_time** | **create_time** |
| idx_order_id | order_id |
| idx_third_trade_no | third_trade_no |
| idx_user_no | user_no |

### 4. SQL 执行计划

| id | table | type | possible_keys | key | key_len | rows | filtered | Extra |
|---|---|---|---|---|---:|---:|---:|---|
| 1 | t_trade | **range** | idx_create_time | idx_create_time | 5 | 5,340 | 20.00 | Using index condition; Using where |

**没有全表扫、没有 filesort、没有临时表** —— `ORDER BY create_time, id` 与 `idx_create_time` 的顺序天然一致，排序被索引消化掉了。这是本批 9 条里唯一一条执行计划本身没有问题的。

### 5. 问题分析
- 每次扫 10,671 行返回 76 行，选择率合理。
- 2.94 s 的耗时来自两处，都不是计划问题：
  1. **34 个字段的宽行回表** —— `t_trade` 单行含 `request_extra_data` / `response_extra_data` / `order_body` 等大字段，410 MB / 142 万行 ≈ 每行 300 B 起，回表 IO 是主要成本；
  2. **03:00 UTC 批量窗口争用** —— 与财务对账任务同一时段。
- 该表 `create_time` 索引齐备，无结构性缺陷。

### 6. 优化建议

| 优先级 | 建议 | 归属 | 预期收益 | 风险 |
|---|---|---|---|---|
| B-10 P3 | 收窄 `SELECT` 列：日批消费方大概率用不到 `request_extra_data` / `response_extra_data` / `order_body` 三个大字段 | 张晓松 | 减少回表与网络传输 | 需确认下游字段依赖 |
| — | ❌ **不建议加索引** —— 计划已是最优 | — | — | — |

---

# 附录

## A · 资源水位（2026-08-31 16:00 ~ 2026-09-01 16:00，CloudWatch AWS/RDS）

| 实例 | 规格 | CPU 基线 | CPU 峰值（时段） | ReadLatency | CPUCreditBalance |
|---|---|---|---|---|---|
| aws-luckyus-salesorder-rw | db.t4g.medium | 8~11% | **28.4%（02:00 财务对账）**<br>24.2%（05:00 看板取数）<br>21.5%（13:00 整点批量） | 基线 0.9~2.5 ms<br>**02:00 → 6.1 ms**<br>04:00~05:00 → 4.2 ms | 576（满值，全程未消耗） |
| aws-luckyus-cdpactivity-rw | db.t4g.medium | 7~8% | 37.7%（12:00）<br>34.2%（04:00）<br>19~25%（09:00~11:00） | — | 576（12:00 短暂降至 566） |
| aws-luckyus-salespayment-rw | db.t4g.medium | 6.1~6.8% | — | — | 576（满值） |

三台 CPU 积分全程接近满值，**当前均无性能事故**。`salesorder` 上 02:00 与 05:00 两个批量窗口是明确可见的峰值来源，也正是本批 6 条 SQL 所在的时段。

## B · 行动项汇总

| 编号 | 事项 | 优先级 | 归属 | 类型 |
|---|---|---|---|---|
| B-03 | 合并 `spu_name` / `spu_code` 两条取数为一条 | P1 | **DBA（本仓库）** | 代码改造 |
| B-04 | 看板取数改增量；过渡先降 `RETAIN_DAYS` | P1 | **DBA（本仓库）** | 代码 / 配置 |
| B-06 | `t_finance_refund` 加 `(tenant, checking_status, deleted, checking_date)` | P1 | DBA | **变更申请** |
| B-08 | `t_finance_receipt` 加 `(tenant, status, deleted, checking_date)`（同时修好 SQL-08、SQL-09） | P1 | DBA | **变更申请** |
| B-01 | `t_contact_activity_instance_record` 加 `(tenant, create_time)` | P2 | DBA | 变更申请（3.5 MB 小表） |
| B-02 | cdpactivity 触达任务从整点 `:00` 错峰 | P2 | 张晓松 | 配置变更 |
| B-05 | 看板刷新从 05:00 UTC 错峰到 06:30 UTC | P2 | **DBA（本仓库）** | 配置变更 |
| B-07 | 核对 `checking_time`/`checking_date`、`status`/`checking_status` 语义；评估冗余索引 | P2 | DBA + 张晓松 | 治理 |
| B-09 | 对账任务去掉配套 COUNT | P2 | 张晓松 | 应用改造 |
| B-12 | SQL-08 收窄 SELECT 列 | P2 | 张晓松 | 应用改造 |
| B-10 | SQL-12 收窄 SELECT 列 | P3 | 张晓松 | 应用改造 |
| B-11 | 评估 `t_order(tenant, status, pay_time)` 复合索引（**做完 B-04 再评估**） | P3 | DBA | 变更申请 |
| B-13 | 确认 SQL-10 对应功能是否已下线 | P3 | 张晓松 | 核查 |

> B-06 / B-08 / B-01 / B-11 涉及生产库 DDL，需按《变更申请》四段式提交，变更原因以慢日志与 `performance_schema` 原始数据为主，本报告的分析结论作为辅助材料标注。

## C · 台账处置

9 条全部从 `pending` 结项，写回 `reports/slow-sql-weekly/analyzed-registry.csv`：

| 处置 | 条数 | 明细 |
|---|---:|---|
| `analyzed`（已出结论，改造待跟进） | 7 | SQL-04、05、06、07、08、09、11 |
| `accepted`（评估后接受现状，不改造） | 2 | SQL-10（已停跑）、SQL-12（计划合理） |

`recheck_after` 统一设为 **2026-10-01**；SQL-10 若届时重新上榜，按本报告第 6 节的方向重新评估。

## D · 本次分析沉淀的两条判别手法

1. **观测均值与现场计时差一个数量级 ⇒ 慢的不是 SQL，是时刻。**
   `performance_schema` 的 `AVG_TIMER_WAIT` 是「执行时的实际耗时」，天然包含了当时的资源争用。拿同一条 SQL 在空闲时段现场跑一遍，如果快出 1~2 个数量级，就说明该指纹是争用的**受害者**而非**成因**——这类应该去改调度时刻，不是改 SQL。

2. **`EXPLAIN` 的 `possible_keys = NULL` 是「近似索引」的照妖镜。**
   建表语句里索引一大把（`t_finance_refund` 有 10 个），肉眼很容易以为「这表索引很全」。但 `checking_time` 与 `checking_date`、`status` 与 `checking_status` 这种只差几个字母的列名，会让所有索引同时落空。**只有 `EXPLAIN` 会说实话。**
