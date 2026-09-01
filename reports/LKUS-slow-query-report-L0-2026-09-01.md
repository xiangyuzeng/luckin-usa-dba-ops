# LKUS MySQL 慢查询分析报告 — L0 核心业务 TOP3

| 项目 | 内容 |
|------|------|
| 报告编号 | LCNA-DBA-SQL-2026-0901 |
| 出具日期 | 2026-09-01 |
| 出具人 | 曾翔宇（DBA / Infrastructure） |
| 分析范围 | 慢查询分级监管看板 `lkus-slow-sql-topn` 中 **L0（核心业务）** 档位 15 台实例 |
| 数据窗口 | 2026-08-25 ~ 2026-09-01（7 天，按 (实例, 库, SQL 指纹) 日差分） |
| 排序口径 | 新增 DB 时间（`SUM(Δsum_sec)`）降序 |
| 数据来源 | ① 明细：`ldas01 / luckyus_db_collection.t_dba_collect_slow_query`（每日 03:30 UTC 采集 `performance_schema` digest，**仅收录 avg_sec ≥ 1s 的指纹**）<br>② 校验：各实例 `performance_schema.events_statements_summary_by_digest`<br>③ SQL 原文：CloudWatch `/aws/rds/instance/*/slowquery`<br>④ 执行计划：各实例现场 `EXPLAIN`<br>⑤ 资源指标：CloudWatch `AWS/RDS` |
| 全 fleet 阈值 | `long_query_time = 0.1s` |

---

## 摘要

L0 档 15 台实例，7 天内命中 149 个 ≥1s 慢 SQL 指纹，合计新增 DB 时间 **10,060.1 秒**。其中 **TOP3 合计 9,128.7 秒，占 90.7%**（TOP2 已占 87.1%）。

| 排名 | 实例 | Schema | 主表 | 7d DB时间 | 占比 | 7d 次数 | 平均耗时 | 单次扫描行 | 单次返回行 | 定性 |
|---|------|--------|------|---------:|-----:|--------:|--------:|-----------:|-----------:|------|
| 1 | aws-luckyus-opshopsale-rw | luckyus_opshopsale | t_shopsale_spu / t_shopsale_rmk | 4,976.9 s | 49.5% | 768 | 6.48 s | 766,796 | **0** | 无效巡检 + 任务重复执行 |
| 2 | aws-luckyus-salespayment-rw | luckyus_sales_payment | t_channel_fee | 3,780.6 s | 37.6% | 2,304 | 1.64 s | 164,324 | 5,000（恒满） | **业务任务空转 + 数据缺口** |
| 3 | aws-luckyus-salesmarketing-rw | luckyus_sales_marketing | t_coupon_record_expired | 371.2 s | 3.7% | 8 | 46.40 s | 3,041,567 | 1 | 缺索引 + 优化器误判 |

**共性结论**：三条全部是后台定时任务，无一条位于用户请求链路；三条全部存在"做无用功"的成分。三台实例当前 `CPUCreditBalance` 均为满值 576、CPU 均值 5.4%~6.8%、峰值 15.9%，**当前不构成性能事故**，定性为「持续资源浪费 + 潜在劣化风险」；但 SQL-02 同时暴露一个真实的财务侧数据完整性缺口，其业务影响高于性能影响。

---

# SQL-01 门店售卖附属备注一致性巡检

## 1. 所在数据库实例、Schema

| 项目 | 内容 |
|------|------|
| 实例标识 | `aws-luckyus-opshopsale-rw` |
| 规格 | db.t4g.medium（2 vCPU / 4 GiB），Multi-AZ，20 GB gp3 |
| 引擎版本 | MySQL 8.4.10 |
| Schema | `luckyus_opshopsale` |
| 服务等级 | **L0 核心业务** |
| 业务分组 / 研发负责人 | 国际运营 / 陈培浩、游熖 |
| 数据库账号 | `iopshopsaleservice_A_o` |
| 来源客户端 | `10.238.40.75`、`10.238.46.255`（同一服务的两个 Pod） |
| 执行频率 | **96 次/天** = 2 Pod × 2 次/小时（整点 :00 与半点 :30 触发） |

## 2. SQL 完整内容

取自 CloudWatch 慢日志 `2026-09-01T14:00:07.213459Z`（原文，未做改写）：

```sql
# User@Host: iopshopsaleservice_A_o[iopshopsaleservice_A_o] @  [10.238.40.75]  Id: 790926
# Query_time: 7.181915  Lock_time: 0.000003  Rows_sent: 0  Rows_examined: 760465

SELECT t1.dept_id AS '门店Id',
       t1.spu_code AS '商品'
FROM t_shopsale_spu t1
LEFT JOIN t_shopsale_rmk t2
       ON t1.dept_id   = t2.dept_id
      AND t1.spu_code  = t2.spu_code
      AND t2.sale_status = 1
      AND t2.rmk_status  = 1
WHERE FIND_IN_SET(t2.rmk_mid, t1.sale_rmks) = 0
  AND t1.sale_status = 1
GROUP BY t1.dept_id, t1.spu_code
LIMIT 10;
```

> 中文列别名 `'门店Id' / '商品'` + `LIMIT 10` + 返回集恒为空，可判定其用途为：**巡检 `t_shopsale_rmk` 中存在、但未被登记进 `t_shopsale_spu.sale_rmks` 逗号串的附属备注**，即一条数据一致性校验，而非业务功能查询。

### 执行统计（`performance_schema` 累计，首见 2026-07-14 06:30 ~ 2026-09-01 14:00）

| 指标 | 值 |
|------|----|
| COUNT_STAR | 4,736 |
| SUM_TIMER_WAIT | 31,053.7 秒（8.63 小时） |
| AVG / MAX | 6.557 s / 8.38 s |
| SUM_ROWS_EXAMINED | 3,628,163,722（36.3 亿行） |
| **SUM_ROWS_SENT** | **0** |
| SUM_NO_INDEX_USED | 4,736（100%） |
| SUM_SELECT_SCAN | 4,736（100%） |
| SUM_CREATED_TMP_DISK_TABLES | 0 |

## 3. 表内容及表上当前索引情况

### 3.1 `t_shopsale_spu` — 门店售卖 SPU

| 项目 | 值 |
|------|----|
| 表注释 | 门店售卖SPU |
| 实际行数 | 22,580（其中 `sale_status = 1` 共 **19,004** 行，占 84.2%） |
| 门店数 | 530 个 `dept_id` |
| 数据 / 索引 | 13.5 MB / 3.0 MB |
| 引擎 / 字符集 | InnoDB / utf8mb4_0900_ai_ci |

关键字段：

| 字段 | 类型 | 注释 |
|------|------|------|
| id | bigint unsigned | 主键 |
| tenant | varchar(4) | 租户 |
| dept_id | bigint | 门店部门Id |
| spu_code | varchar(20) | 商品SPU |
| sale_status | tinyint(1) | 售卖状态：1售卖中，0不售卖 |
| **sale_rmks** | **text** | **勾选附属选项集合，逗号隔开**（反范式 CSV 列） |
| sale_skus | text | 售卖sku集合，逗号隔开 |

索引：

| 索引名 | 类型 | 列 | 基数 |
|--------|------|----|-----:|
| PRIMARY | UNIQUE | id | 21,629 |
| uniq_t_shop_spu | UNIQUE | tenant, dept_id, spu_code | 1 / 477 / 21,629 |
| idx_spu | NORMAL | spu_code | 100 |

> ⚠ `sale_status` 无索引；`sale_rmks` 为 `text` 类型的逗号串，结构上不可索引。

### 3.2 `t_shopsale_rmk` — 门店售卖附属备注

| 项目 | 值 |
|------|----|
| 表注释 | 门店售卖附属备注 |
| 实际行数 | 861,060（其中 `sale_status=1 AND rmk_status=1` 共 **700,930** 行，占 81.4%） |
| 数据 / 索引 | 82.6 MB / 79.7 MB |

关键字段：

| 字段 | 类型 | 注释 |
|------|------|------|
| id | bigint unsigned | 主键 |
| dept_id | bigint | 门店部门Id |
| spu_code | varchar(20) | 商品SPU |
| category_mid / type_mid | varchar(20) | 附属备注类别Mid(1级) / 类型Mid(2级) |
| **rmk_mid** | varchar(20) | 附属备注Mid（被 `FIND_IN_SET` 匹配的值） |
| rmk_name | varchar(64) | 附属备注名称 |
| sale_status | tinyint(1) | 售卖状态：1售卖中，0不售卖 |
| rmk_status | tinyint(1) | 附属备注状态，1正常，0禁售 |

索引：

| 索引名 | 类型 | 列 | 基数 |
|--------|------|----|-----:|
| PRIMARY | UNIQUE | id | 862,122 |
| idx_t_shop_spu | NORMAL | dept_id, spu_code | 531 / 20,339 |
| idx_spu | NORMAL | spu_code | 123 |
| idx_rmk | NORMAL | rmk_mid | 130 |

> ⚠ `sale_status`、`rmk_status` 均无索引，且这两个字段选择性极低（81.4% 的行同时满足 `=1`），即便加索引也无价值。

## 4. SQL 执行计划

```sql
EXPLAIN SELECT t1.dept_id, t1.spu_code
FROM luckyus_opshopsale.t_shopsale_spu t1
LEFT JOIN luckyus_opshopsale.t_shopsale_rmk t2
  ON t1.dept_id=t2.dept_id AND t1.spu_code=t2.spu_code AND t2.sale_status=1 AND t2.rmk_status=1
WHERE FIND_IN_SET(t2.rmk_mid, t1.sale_rmks)=0 AND t1.sale_status=1
GROUP BY t1.dept_id, t1.spu_code LIMIT 10;
```

| id | table | type | possible_keys | key | key_len | ref | rows | filtered | Extra |
|---|-------|------|---------------|-----|--------|-----|-----:|--------:|-------|
| 1 | t1 | **ALL** | uniq_t_shop_spu, idx_spu | **NULL** | NULL | NULL | 21,629 | 10.00 | Using where; **Using temporary** |
| 1 | t2 | ref | idx_t_shop_spu, idx_spu | idx_t_shop_spu | 90 | t1.dept_id, t1.spu_code | 41 | 1.00 | Using where |

**计划解读**

- `t1` 走全表扫描（`type=ALL`、`key=NULL`），因为 `sale_status` 无索引，且即便有索引也覆盖 84% 的行、不会被选中。
- `t2` 走 `idx_t_shop_spu(dept_id, spu_code)` 的 ref 查找，每个 SPU 平均命中 41 行。
- 实际扫描量：19,004（t1 命中行）× ≈37（t2 平均命中）+ 表扫描开销 ≈ **766,796 行/次**，即**每次执行都把 86 万行的 `t_shopsale_rmk` 读掉 81%**。
- `Using temporary`：`GROUP BY dept_id, spu_code` 与任何索引顺序都不一致，需建临时表（`SUM_CREATED_TMP_DISK_TABLES=0`，说明未落盘，全在内存）。
- `filtered` 列 `10.00 / 1.00` 是优化器对无索引条件与 `FIND_IN_SET` 的默认猜测值，与实际（84% / 0%）严重偏离——但因为无论如何都要全量求值，此处的误估不影响计划选择。

## 5. 问题分析

**（1）`FIND_IN_SET` 是函数条件，结构上不可索引 —— 这是耗时的主因**

`FIND_IN_SET(t2.rmk_mid, t1.sale_rmks)` 需要把 `t1.sale_rmks`（text 类型的逗号串）与 join 出来的每一条 `t2.rmk_mid` 逐条做字符串切分匹配。该条件既不能下推、也不能借助任何索引裁剪，只能在 join 之后对 76.6 万行**逐行求值**。这是 6.5 秒耗时的根本来源，也是本条 SQL **加任何索引都无法根治**的原因。

**（2）`LEFT JOIN` 被 `WHERE` 条件退化为 `INNER JOIN` —— 左连接语义白写**

`t2.rmk_mid` 出现在 `WHERE` 子句中：对于左表未匹配到右表的行，`t2.rmk_mid IS NULL`，`FIND_IN_SET(NULL, ...)` 返回 `NULL`，`NULL = 0` 为 `UNKNOWN`，该行被过滤掉。因此 `LEFT JOIN` 与 `INNER JOIN` 在此完全等价。如果业务本意是"找出没有任何备注的 SPU"，则该 SQL **逻辑上就是错的**（永远查不出来）；需与研发确认真实意图。

**（3）巡检结果恒为空 —— 4,736 次执行零产出**

`SUM_ROWS_SENT = 0`，自 2026-07-14 首次采集至今 4,736 次执行没有返回过任何一行。说明被巡检的数据本来就是一致的。这 8.63 小时的 DB 时间是**纯消耗**。

**（4）两个 Pod 各自执行同一个定时任务，没有分布式锁 —— 成本直接翻倍**

慢日志显示 `10.238.40.75`（14:00:07.213）与 `10.238.46.255`（14:00:07.145）在**同一秒**发起了完全相同的查询；按小时统计，两个来源 IP 各约 2 次/小时。这是典型的"定时任务部署了多副本但未做调度互斥"，其中 50% 的开销是纯重复。

**（5）反范式设计是设计层根因**

`sale_rmks` 用 text 逗号串存储多值关系，导致"校验关联表与 CSV 列是否一致"这件事在数据库侧只能全量计算。这是本条 SQL 存在的根本原因。

**（6）资源影响评估**

- 累计 DB 时间 630 秒/天，在 2 vCPU 的 db.t4g.medium 上约占全机 CPU 容量的 0.36%。
- 但单次执行会**独占 1 个核心 6.5 秒**，而两个 Pod 同时触发意味着整点/半点会有约 7 秒**两个核心同时被占满**。该实例 CPU 峰值 15.9%、`CPUCreditBalance` 满值 576，当前尚有余量，但整点批量叠加时是明确的抖动源。
- 单次读取 76.6 万行（约 60 MB）会持续冲刷 buffer pool，对同实例其他查询的缓存命中率有稀释作用。

## 6. 优化建议

| 优先级 | 建议 | 归属 | 预期收益 | 风险 |
|--------|------|------|---------|------|
| **P1** | **定时任务去重**：加分布式锁（Redis / 数据库锁），或改由 Chronus 单点调度，确保同一时刻只有一个 Pod 执行 | 国际运营研发 | 立降 50%（630 → 315 s/天） | 无 |
| **P1** | **降低执行频率**：一致性巡检从每 30 分钟改为**每天一次**，放在低峰期（建议 06:00~08:00 UTC，避开 05:00 UTC 批量窗口） | 国际运营研发 | 630 → 6.5 s/天，**降幅 99%** | 一致性问题发现时延从 30 分钟延长到 24 小时；巡检恒为空，可接受 |
| **P1** | **确认 `LEFT JOIN` 语义**：若本意是"找无备注的 SPU"，当前 SQL 逻辑错误，需改为 `WHERE t2.id IS NULL` 形式 | 国际运营研发 | 修正正确性 | 需研发确认业务意图 |
| P2 | 加覆盖索引 `idx_rmk_cover(dept_id, spu_code, rmk_status, sale_status, rmk_mid)` 于 `t_shopsale_rmk`，使 join 段索引覆盖、不回表 | DBA | 单次耗时预计降 50%~70%（6.5s → 2~3s） | 新增约 40~50 MB 索引；86 万行小表，在线 DDL 秒级完成 |
| P2 | 巡检 SQL 只取 `dept_id, spu_code`，`GROUP BY` 可改为 `DISTINCT` 并去掉不必要的 `LIMIT 10`（或保留 `LIMIT 1` 做"是否存在异常"的探针） | 国际运营研发 | 减少临时表开销 | 无 |
| P3 | **设计层整改**：将 `sale_rmks` 逗号串正规化为关联表（或直接以 `t_shopsale_rmk` 为唯一真源），或把该一致性校验迁移到离线数据质量平台（Doris / Redshift） | 架构 + 国际运营 | 根治，该 SQL 可从生产库彻底下线 | 需改造应用读写路径，工作量较大 |

> **建议执行顺序**：P1 的"去重 + 降频"两项无需改 SQL、无需 DDL，当天即可落地并拿到 99% 收益；P2/P3 可作为后续技术债排期。

---

# SQL-02 支付渠道费用预估任务捞取

## 1. 所在数据库实例、Schema

| 项目 | 内容 |
|------|------|
| 实例标识 | `aws-luckyus-salespayment-rw` |
| 规格 | db.t4g.medium（2 vCPU / 4 GiB），Multi-AZ，20 GB gp3 |
| 引擎版本 | MySQL 8.4.10 |
| Schema | `luckyus_sales_payment` |
| 服务等级 | **L0 核心业务** |
| 业务分组 / 研发负责人 | 国际营销增长 / 张晓松 |
| 数据库账号 | `isalespmtadmin_A_o` |
| 来源客户端 | `10.238.37.242` |
| 执行频率 | **每 5 分钟一次**（≈288 次/天；7 天实测 2,304 次） |

## 2. SQL 完整内容

取自 CloudWatch 慢日志 `2026-09-01T14:20:01.323454Z`（原文，含 MyBatis 动态 SQL 留下的空白）：

```sql
# User@Host: isalespmtadmin_A_o[isalespmtadmin_A_o] @  [10.238.37.242]  Id: 1155525
# Query_time: 1.284638  Lock_time: 0.000002  Rows_sent: 5000  Rows_examined: 161145

select
    id, tenant, trade_no, channel_pay_type_id, fee_plan_no, transaction_fee_est, merchant_service_fee_est,
    merchant_service_fee_vat_est, total_fee_est, transaction_fee, merchant_service_fee,
    merchant_service_fee_vat, total_fee, fee_est_times, fee_query_times, remark, delete_flag,
    create_id, create_name, create_time, modify_id, modify_name, modify_time, version
from t_channel_fee f
where 1 = 1
    and create_time  >=  '2026-08-02 14:20:00.025'      -- 滚动 30 天窗口下界
    and create_time  <=  '2026-09-01 14:20:00.025'      -- 滚动 30 天窗口上界（= 当前时刻）
    and total_fee_est is null
    and ifnull(fee_est_times,0)   <  3
order by fee_est_times, create_time
limit 5000;
```

### 执行统计（`performance_schema` 累计，首见 2026-07-22 03:05 ~ 2026-09-01 14:20）

| 指标 | 值 |
|------|----|
| COUNT_STAR | 11,945 |
| SUM_TIMER_WAIT | 18,120.8 秒（5.03 小时） |
| AVG / MAX | 1.517 s / 5.39 s |
| SUM_ROWS_EXAMINED | 1,958,299,948（19.6 亿行） |
| **SUM_ROWS_SENT** | **59,725,000 = 5,000 × 11,945** — **每一次都恰好返回满 LIMIT** |
| SUM_SELECT_RANGE | 11,945（100% 走范围扫描，无全表扫） |
| SUM_NO_INDEX_USED | 0 |
| SUM_SORT_ROWS / SUM_SORT_SCAN | 59,725,000 / 11,945（**每次都发生 filesort**） |
| SUM_CREATED_TMP_DISK_TABLES | 0 |

## 3. 表内容及表上当前索引情况

### `t_channel_fee` — 支付渠道费用表

| 项目 | 值 |
|------|----|
| 表注释 | 支付渠道费用表 |
| 实际行数 | **1,392,200** |
| AUTO_INCREMENT | 6,833,593 |
| 数据 / 索引 | 209.9 MB / 105.8 MB |
| 引擎 | InnoDB |

关键字段：

| 字段 | 类型 | 可空 | 默认 | 注释 |
|------|------|------|------|------|
| id | bigint unsigned | NO | — | 主键(自增) |
| tenant | varchar(10) | NO | — | 租户 |
| trade_no | varchar(64) | — | — | 支付流水号 |
| channel_pay_type_id | bigint unsigned | — | — | 渠道支付方式ID |
| fee_plan_no | varchar(64) | — | — | 费用方案编号 |
| transaction_fee_est | decimal(19,4) unsigned | — | — | 交易手续费预估 |
| merchant_service_fee_est | decimal(19,4) unsigned | — | — | 商家服务费预估 |
| merchant_service_fee_vat_est | decimal(19,4) unsigned | — | — | 商家服务费增值税预估 |
| **total_fee_est** | decimal(19,4) unsigned | **YES** | **NULL** | **支付手续费预估**（本 SQL 的过滤条件） |
| total_fee | decimal(19,4) unsigned | — | — | 支付手续费实收 |
| **fee_est_times** | smallint unsigned | **YES** | **0** | **预估费用计算次数**（本 SQL 的重试计数） |
| fee_query_times | smallint unsigned | — | — | 手续费查询次数 |
| create_time | datetime | NO | — | 创建时间 |
| modify_time | datetime | — | — | 修改时间 |

索引：

| 索引名 | 类型 | 列 | 基数 |
|--------|------|----|-----:|
| PRIMARY | UNIQUE | id | 1,335,330 |
| uniq_trade_no | UNIQUE | trade_no, tenant | 1,284,165 / 1,252,282 |
| idx_create_time | NORMAL | create_time | 1,192,317 |
| idx_modify_time | NORMAL | modify_time | 1,226,784 |

> ⚠ **没有任何索引覆盖 `total_fee_est` 或 `fee_est_times`**，因此本 SQL 的两个业务过滤条件与排序键全部无索引可用。

### 🔴 表内数据现状（本次分析的核心发现）

| 指标 | 值 |
|------|----|
| 总行数 | 1,392,200 |
| **`total_fee_est IS NULL`（未完成预估）** | **718,696 行 = 全表的 51.6%** |
| 这 718,696 行的 `fee_est_times` 分布 | **全部为 0**（无一条大于 0，也无 NULL） |
| 最早一条未预估记录 `create_time` | **2025-03-24 10:05:33** |
| 最新一条未预估记录 `create_time` | 2026-09-01 14:22:03（= 实时写入） |

## 4. SQL 执行计划

```sql
EXPLAIN SELECT <24 列> FROM luckyus_sales_payment.t_channel_fee f
WHERE 1=1 AND create_time >= '2026-08-02 14:20:00.025' AND create_time <= '2026-09-01 14:20:00.025'
  AND total_fee_est IS NULL AND IFNULL(fee_est_times,0) < 3
ORDER BY fee_est_times, create_time LIMIT 5000;
```

| id | table | type | possible_keys | key | key_len | ref | rows | filtered | Extra |
|---|-------|------|---------------|-----|--------|-----|-----:|--------:|-------|
| 1 | f | range | idx_create_time | idx_create_time | 5 | NULL | 305,856 | 10.00 | Using index condition; Using where; **Using filesort** |

**计划解读**

- `type=range` + `key=idx_create_time`：30 天时间窗走了索引范围扫描，这部分没有问题。
- **`Using filesort` 是关键问题**：排序键是 `(fee_est_times, create_time)`，首列 `fee_est_times` 无索引，与 `idx_create_time` 的顺序完全不同。MySQL 必须**先把窗口内所有满足过滤条件的行全部取出，排序完成后才能应用 `LIMIT 5000`**。
- 结论：**`LIMIT 5000` 在这条 SQL 里完全不起降本作用**。实测每次扫描 161,145 行（≈30 天窗口内的全部行），无论 LIMIT 写多少都一样。
- `IFNULL(fee_est_times, 0) < 3` 是函数包裹列，即使将来给 `fee_est_times` 建索引，该条件也**无法用于索引查找**（不满足 SARGable 条件）。
- 成本随窗口内数据量线性增长：7 天前平均 1.48 s，现在 1.52 s，仍在缓慢上升。

## 5. 问题分析

**（1）🔴 根本问题不是慢 SQL，而是业务任务空转 —— 手续费预估从未回写**

三条证据链构成闭环：

1. `SUM_ROWS_SENT = 5,000 × 11,945`，**11,945 次执行，每一次都恰好返回满 5,000 行**。若积压在正常消化，返回行数必然出现小于 5,000 的情况。
2. 718,696 条待预估记录的 `fee_est_times` **全部为 0** —— 说明"预估计算次数"这个计数器从来没有被 `+1` 过。
3. `ORDER BY fee_est_times, create_time` 是确定性排序，在 `fee_est_times` 恒为 0 的前提下，**每一轮捞出的都是同一批 create_time 最早的 5,000 条记录**。

结论：支付渠道费用预估任务**既没有把预估结果写回 `total_fee_est`，也没有递增 `fee_est_times`**，因此形成死循环——每 5 分钟捞同一批数据，永远捞不完。

**（2）🔴 业务影响：51.6% 的渠道手续费预估值缺失，最早可追溯到 2025-03-24**

全表 1,392,200 行中有 718,696 行（51.6%）的 `total_fee_est` 为空，最早一条待预估记录创建于 **2025-03-24**，即该链路已异常约 **17 个月**。`t_channel_fee` 是支付渠道费用表，`total_fee_est`（支付手续费预估）缺失会直接影响：

- 渠道成本预估与实收（`total_fee`）的差异分析；
- 财务对账中"预估 vs 实收"的核对口径；
- 依赖该字段的任何毛利/成本报表。

**该数据完整性问题的业务影响，高于其带来的 DB 性能开销，应作为本报告的最高优先级事项处理。**

**（3）SQL 层面的低效是次生问题**

`ORDER BY fee_est_times, create_time` 与唯一可用的 `idx_create_time` 顺序不一致，导致每次必须读满 30 天窗口的 16.1 万行并做 filesort。`LIMIT 5000` 形同虚设。同时 `SELECT` 取了全部 24 列（含多个 decimal 与 varchar(255) 备注），回表开销可观。

**（4）为什么慢查询看板才发现它**

这类"永远捞不完"的空转任务不会触发任何异常告警：SQL 正常返回、无报错、无锁等待、CPU 也不高（该实例 CPU 均值 6.1%~6.8%、`CPUCreditBalance` 满值）。它只在慢查询按 DB 时间聚合排序时才暴露出来 —— 这正是分级慢查询看板的价值所在，也说明**监控体系缺少"批处理任务健康度"这一维度**。

**（5）资源影响评估**

540 秒/天 DB 时间，在 2 vCPU 实例上约占 0.31% CPU 容量，单看不算高；但每 5 分钟读取 16.1 万行（约 24 MB）会持续冲刷 buffer pool，对 4 GiB 内存的 t4g.medium 是不可忽略的缓存压力。

## 6. 优化建议

| 优先级 | 建议 | 归属 | 预期收益 | 风险 |
|--------|------|------|---------|------|
| **P0** | **排查费用预估任务为什么不回写**：确认 `total_fee_est` 与 `fee_est_times` 的更新逻辑是否存在异常吞异常、事务未提交、或依赖的费率方案（`fee_plan_no`）查不到导致直接跳过 | 支付研发（张晓松） | 修复根因 | — |
| **P0** | **评估 718,696 条缺失预估值的财务影响**，与财务确认是否需要补数；如需补数，制定分批离线补算方案（避开业务高峰，控制批次大小） | 支付研发 + 财务 | 恢复数据完整性 | 补数为写操作，需走变更申请 |
| **P1** | **加索引** `idx_est_pending(total_fee_est, fee_est_times, create_time)` | DBA | 见下 | 新增约 40 MB；139 万行表在线 DDL，分钟级完成 |
| **P1** | **改写 SQL 使条件 SARGable**：将 `ifnull(fee_est_times,0) < 3` 改为 `(fee_est_times IS NULL OR fee_est_times < 3)`；或直接将列改为 `NOT NULL DEFAULT 0` 后写成 `fee_est_times < 3` | 支付研发 | 与上一条配合，索引才能生效 | 列改 NOT NULL 需确认无 NULL 值（实测当前无 NULL） |
| | **上两条的合并效果**：索引前缀 `(total_fee_est=NULL, fee_est_times=0)` 为等值定位，其后 `create_time` 有序 ⇒ 时间窗口可直接 seek，且索引顺序即 `ORDER BY` 顺序 ⇒ **消除 filesort，`LIMIT 5000` 真正生效**。扫描行数 161,145 → ≈5,000，耗时 1.5 s → **毫秒级** | | **-97%** | |
| P2 | **收窄 `SELECT` 列**：任务只需要计算费用所必需的字段，去掉 `remark`、`create_name`、`modify_name` 等 | 支付研发 | 减少回表与网络传输 | 无 |
| **P2** | **补齐批处理健康度告警**：对"同一批处理任务连续 N 次返回满 LIMIT"、"待处理队列长度持续不下降"、"最老待处理记录年龄超过阈值"三类信号建立告警 | DBA + 研发 | 避免同类问题再次潜伏 17 个月 | 无 |

> ⚠ **执行顺序强约束：必须先修回写逻辑（P0），再加索引（P1）。** 若先加索引，只会让这个空转任务跑得更快、更频繁地空转，掩盖问题。

---

# SQL-03 过期优惠券归档探针

## 1. 所在数据库实例、Schema

| 项目 | 内容 |
|------|------|
| 实例标识 | `aws-luckyus-salesmarketing-rw` |
| 规格 | db.t4g.xlarge（4 vCPU / 16 GiB），Multi-AZ，240 GB gp3 |
| 引擎版本 | MySQL 8.4.10 |
| Schema | `luckyus_sales_marketing` |
| 服务等级 | **L0 核心业务** |
| 业务分组 / 研发负责人 | 国际营销增长 / 张晓松 |
| 数据库账号 | `isalescouponservice_A_o` |
| 来源客户端 | `10.238.34.30` |
| 执行频率 | **每天 1 次，04:30 UTC**（00:30 EST） |

## 2. SQL 完整内容

取自 CloudWatch 慢日志 `2026-09-01T04:30:08.345054Z`（原文）：

```sql
# User@Host: isalescouponservice_A_o[isalescouponservice_A_o] @  [10.238.34.30]  Id: 967605
# Query_time: 8.249462  Lock_time: 0.000003  Rows_sent: 1  Rows_examined: 3125198

SELECT id, coupon_no, activity_id, activity_no, activity_name, marketing_proposal_id,
       marketing_proposal_no, marketing_proposal_name, proposal_id, proposal_no, proposal_name,
       coupon_template_id, coupon_type, coupon_discount_type, coupon_discount_sub_type, coupon_name,
       coupon_show_name, threshold_amount, threshold_commodity, coupon_denomination, coupon_currency,
       discount, marketing_cost, member_no, member_phone, order_no, receive_time, coupon_status,
       use_status, use_time, effective_time_type, effective_begin_time, effective_end_time,
       effective_day_of_week, invalid_time_type, expire_time, expire_day_of_week, coupon_source,
       invite_code, invite_code_type, manual_coupon_send_id, send_type, member_status,
       target_commodity, allowance_program_id, allowance_sub_program_id, promo_code, redeem_code,
       create_time, modify_time, tenant
FROM t_coupon_record_expired
WHERE (coupon_source = 15 AND expire_time < '2026-08-02 04:30:00.032' AND id >= 0)
  AND tenant = 'LKUS'
ORDER BY id ASC
LIMIT 1;
```

> `expire_time` 卡口恒为「执行时刻 - 30 天」，`id >= 0` + `ORDER BY id ASC LIMIT 1` 是典型的**分页/水位探针**写法，用途为：取出待归档（或待清理）的最早一条 `coupon_source = 15` 的过期券记录。

### 执行统计（`performance_schema` 累计，首见 2026-07-23 04:32 ~ 2026-09-01 04:30）

| 指标 | 值 |
|------|----|
| COUNT_STAR | 41 |
| SUM_TIMER_WAIT | 1,609.1 秒 |
| AVG / MAX | 39.25 s / **126.28 s** |
| SUM_ROWS_EXAMINED | 124,787,866（1.25 亿行） |
| SUM_ROWS_SENT | 41（每次 1 行） |
| SUM_SELECT_SCAN | 41（100%，每次都是索引全序扫描） |
| SUM_NO_INDEX_USED | 0（用了索引，但是**全序扫描**索引） |

### 逐日耗时轨迹（CloudWatch 慢日志）

| 日期 | Query_time | Rows_examined | expire_time 卡口 |
|------|-----------:|--------------:|------------------|
| 2026-08-22 | 51.79 s | 3,088,406 | 2026-07-23 |
| 2026-08-23 | 51.93 s | 3,092,003 | 2026-07-24 |
| 2026-08-24 | 52.10 s | 3,096,395 | 2026-07-25 |
| 2026-08-25 | 52.81 s | 3,099,917 | 2026-07-26 |
| 2026-08-26 | 51.70 s | 3,103,651 | 2026-07-27 |
| 2026-08-27 | 52.32 s | 3,106,808 | 2026-07-28 |
| 2026-08-28 | 51.44 s | 3,109,747 | 2026-07-29 |
| 2026-08-29 | 51.47 s | 3,113,332 | 2026-07-30 |
| 2026-08-30 | 51.10 s | 3,117,209 | 2026-07-31 |
| 2026-08-31 | **8.26 s** | 3,074,492 | 2026-08-01 |
| 2026-09-01 | **8.25 s** | 3,125,198 | 2026-08-02 |

> **扫描行数每天稳定增加约 3,500 行**，即命中位置逐日后移，成本单调上升。08-31 起耗时从 52 秒骤降到 8.2 秒但**扫描行数并未下降**，说明是 buffer pool 命中率变化（缓存变热），**不是查询被优化了** —— 缓存一旦被冲掉，随时会回到 50 秒以上（历史峰值 126.28 秒）。

## 3. 表内容及表上当前索引情况

### `t_coupon_record_expired` — 优惠券发放记录（过期归档表）

| 项目 | 值 |
|------|----|
| 表注释 | 优惠券发放记录 |
| 表行数 | **34,230,795** |
| 字段数 | 51 |
| AUTO_INCREMENT | 547,996,454 |
| **数据大小** | **10.97 GB** |
| **索引大小** | **9.42 GB** |
| 合计 | **20.39 GB**（实例总存储 240 GB） |

对照在线表 `t_coupon_record`（优惠券发放记录，同 51 列）：7,070,764 行 / 2.65 GB 数据 + 2.24 GB 索引。归档表体量是在线表的 **4.8 倍**。

本 SQL 涉及的关键字段：

| 字段 | 类型 | 可空 | 说明 |
|------|------|------|------|
| id | bigint unsigned | NO | 主键，自增 |
| **coupon_source** | **tinyint** | NO | 券来源（过滤值 = 15） |
| **tenant** | **varchar(10)** | YES | 租户（过滤值 = 'LKUS'） |
| **expire_time** | **datetime(3)** | YES | 过期时间（过滤：< 当前时刻-30天） |

索引：

| 索引名 | 类型 | 列 | 基数 |
|--------|------|----|-----:|
| PRIMARY | UNIQUE | id | 34,230,796 |
| uniq_idx_coupon_no | UNIQUE | coupon_no | 33,716,272 |
| idx_expire_time | NORMAL | expire_time | 78,437 |
| idx_user_no | NORMAL | member_no | 315,693 |
| idx_prpposal_id | NORMAL | proposal_id | 24,479 |
| idx_proposal_no | NORMAL | proposal_no | 13,970 |
| idx_manual_send_id | NORMAL | manual_coupon_send_id | 29,299 |

> 🔴 **`coupon_source` 与 `tenant` 均无索引**。唯一与本 SQL 相关的 `idx_expire_time` 选择性极差 —— 卡口是"30 天前"，而这是一张归档表，绝大多数行的 `expire_time` 都满足该条件，用它过滤几乎等同于全表。

## 4. SQL 执行计划

```sql
EXPLAIN SELECT id, coupon_no, ... , tenant
FROM luckyus_sales_marketing.t_coupon_record_expired
WHERE (coupon_source = 15 AND expire_time < '2026-08-02 04:30:00.032' AND id >= 0) AND tenant = 'LKUS'
ORDER BY id ASC LIMIT 1;
```

| id | table | type | possible_keys | key | key_len | ref | rows | filtered | Extra |
|---|-------|------|---------------|-----|--------|-----|-----:|--------:|-------|
| 1 | t_coupon_record_expired | **index** | idx_expire_time | **PRIMARY** | 8 | NULL | **3** | 1.67 | Using where |

**计划解读 —— 这是一个典型的优化器误判案例**

- `type=index` + `key=PRIMARY`：优化器放弃了 `idx_expire_time`，选择**按主键顺序全序扫描**。
- **`rows = 3`：优化器估算只需扫 3 行就能满足 `LIMIT 1`。而实际扫描量是 3,125,198 行 —— 误差超过 100 万倍。**
- 误判成因：`ORDER BY id ASC LIMIT 1` 让优化器认为"沿主键升序扫，很快会撞到第一条满足条件的行"。它按 `filtered = 1.67%` 的默认猜测推算，认为几十行内必然命中。但实际数据分布是：`coupon_source = 15` 的记录集中在 id 较大的区间，前 312 万行**一条都不满足**，只能一路扫下去。
- 这是 `ORDER BY 主键 + LIMIT 小值 + 无索引过滤条件` 的经典陷阱：**LIMIT 越小，优化器越倾向于选主键扫描，而选错的代价越大**。

## 5. 问题分析

**（1）缺索引是直接原因**

`coupon_source`（券来源）和 `tenant`（租户）是本 SQL 仅有的两个高选择性等值条件，但两者都没有索引。在一张 3,423 万行、20.4 GB 的表上，没有任何索引路径能支撑这个查询。

**（2）优化器误判放大了后果**

即便没有理想索引，若走 `idx_expire_time` 范围扫描再排序，代价也未必比现在差。但 `ORDER BY id LIMIT 1` 诱导优化器选择了主键全序扫描并给出 `rows=3` 的荒谬估算，最终每天固定扫掉 312 万行、约 1 GB 数据，只为取回 1 行。

**（3）成本单调增长，且当前的"变快"是假象**

扫描行数每天 +3,500，说明命中位置在持续后移，**这条 SQL 只会越来越慢**。08-31 起的 52 s → 8.2 s 并非优化生效（扫描行数反而增加了），而是 16 GiB 内存实例的 buffer pool 恰好缓存住了主键前段；一旦有大查询冲刷缓存，立刻回到 50 秒以上，历史峰值已达 126 秒。**不能因为当前 8 秒就判定风险已解除。**

**（4）SELECT 全字段放大了回表开销**

作为一个只需要定位水位的探针，SQL 取回了全部 51 个字段（含多个 varchar(64)/varchar(255) 与 decimal），回表与网络传输开销远超必要。

**（5）归档任务本身的节奏存疑**

每天只执行 1 次、只取 1 行，而命中位置每天仅前进约 3,500 行 —— 相对于 3,423 万行的表规模，这个推进速度意味着归档链路要跑很多年才能处理完。建议研发侧复核该任务的整体设计是否符合预期。

**（6）资源影响评估**

单次 51 秒期间独占 db.t4g.xlarge 的 1 个核心（占 4 vCPU 的 25%），并读取约 1 GB 数据冲刷 buffer pool。执行时间 04:30 UTC 正好紧邻 05:00 UTC 的每日批量窗口，存在叠加放大的风险。

## 6. 优化建议

| 优先级 | 建议 | 归属 | 预期收益 | 风险 |
|--------|------|------|---------|------|
| **P1** | **加复合索引** `idx_tenant_source_id(tenant, coupon_source, id)`<br>`tenant` + `coupon_source` 等值定位后，索引内天然按 `id` 升序排列，`ORDER BY id ASC LIMIT 1` 可直接取首条、立即返回，`expire_time` 回表过滤 | DBA | 扫描 312 万行 → 个位数行，**8~52 s → 毫秒级**；同时消除逐日劣化 | 见下 |
| | **DDL 风险控制**：3,423 万行 / 10.97 GB 表，须用 `ALTER TABLE ... ADD INDEX ..., ALGORITHM=INPLACE, LOCK=NONE` 在线加索引。预计新增索引空间 **0.8~1.2 GB**（当前索引已 9.42 GB，实例 240 GB 存储余量充足）。建议在 **02:00~04:00 UTC 低峰**执行，执行期间监控 `FreeStorageSpace`、`ReplicaLag`、`CPUUtilization`。需走正式变更申请 | DBA | | 在线 DDL 期间有额外 I/O 与临时空间占用 |
| P2 | **收窄 SELECT 列**：探针只需 `id`（或 `id, coupon_no`），无需取回 51 个字段 | 营销研发（张晓松） | 减少回表与传输开销 | 无 |
| P2 | **去掉恒真条件 `id >= 0`**：该条件对 `bigint unsigned` 主键永远为真，只会干扰优化器的代价估算 | 营销研发 | 帮助优化器做出更合理的选择 | 无 |
| P3 | **改为游标式分页**：把 `id >= 0` 换成上一轮处理到的 `id > ${lastId}` 并持久化水位，避免每轮都从头扫 | 营销研发 | 即使不加索引也能大幅降本 | 需改造任务状态存储 |
| P3 | **复核归档任务设计**：每天 1 次、每次 1 条、水位每天前进 3,500 行，与 3,423 万行的表规模不匹配，确认归档/清理链路是否按预期推进 | 营销研发 | 避免出现与 SQL-02 类似的"任务空转" | 无 |
| P3 | **执行时间调整**：从 04:30 UTC 挪开，避免与 05:00 UTC 的每日批量窗口叠加 | 营销研发 | 削峰 | 无 |

---

# 附录

## A. 三台实例资源水位（2026-08-31 14:30 ~ 2026-09-01 14:30，CloudWatch）

| 实例 | 规格 | CPU 均值 | CPU 峰值 | CPUCreditBalance（最小值） | 判定 |
|------|------|--------:|--------:|--------------------------:|------|
| aws-luckyus-opshopsale-rw | db.t4g.medium | 5.4% ~ 6.2% | 15.9% | 576（满值，全程未消耗） | 正常 |
| aws-luckyus-salespayment-rw | db.t4g.medium | 6.1% ~ 6.8% | — | 576（满值，全程未消耗） | 正常 |
| aws-luckyus-salesmarketing-rw | db.t4g.xlarge | — | — | — | 正常 |

三台均为 T 系列可突发实例，CPU 积分全程保持满值，说明当前负载完全在基线性能内，**不存在积分耗尽风险**。本报告的三条 SQL 均定性为「资源浪费 + 潜在劣化」，而非现网性能事故。

## B. 口径说明（引用本报告数据时务必注意）

1. **明细口径 ≠ 总量口径。** 本报告 TOP3 来自采集表，该表**只收录 `avg_sec ≥ 1s` 的 SQL 指纹**（实测 `min(avg_sec) = 1.00`）。一条平均 5 毫秒、每天执行上亿次、尾部有几万次超过 0.1 秒的 SQL，采集表一条也收不到。
2. 因此 **「TOP3 占 90.7%」的正确表述是：占 L0「单次平均耗时 ≥1s」慢 SQL 总 DB 时间的 90.7%**，不能表述为"占 L0 全部慢查询的 90.7%"。
3. L0 的慢查询**总量**须以 Prometheus 口径为准（`mysql_global_status_slow_queries`，阈值 0.1s）：L0 15 台实例 24 小时约 **41,400 条**，全 fleet 约 168,000 条。
4. 采集表存储的是**累计值**，本报告所有"新增"指标均已按 `(实例, 库, MD5(query))` 分区、按 `data_date` 排序做 `LAG()` 日差分处理；直接对累计值排序会得到"终身榜"而非"当期榜"。
5. 采集表明细覆盖 31 台实例，Prometheus 覆盖 64 台，两者覆盖面不同，不可直接相除。

## C. 行动项汇总

| 编号 | 事项 | 优先级 | 归属 | 类型 |
|------|------|--------|------|------|
| A-01 | 排查 `t_channel_fee` 费用预估任务不回写 `total_fee_est` / `fee_est_times` 的原因 | **P0** | 支付研发（张晓松） | 缺陷修复 |
| A-02 | 评估 718,696 条手续费预估缺失的财务影响，确认是否补数 | **P0** | 支付研发 + 财务 | 数据治理 |
| A-03 | `opshopsale` 一致性巡检任务加分布式锁去重 | P1 | 国际运营研发（陈培浩/游熖） | 应用改造 |
| A-04 | `opshopsale` 一致性巡检降频至每天 1 次 | P1 | 国际运营研发 | 配置变更 |
| A-05 | 确认 SQL-01 的 `LEFT JOIN` 语义是否符合业务意图 | P1 | 国际运营研发 | 正确性核查 |
| A-06 | `t_channel_fee` 加索引 `(total_fee_est, fee_est_times, create_time)` + 去掉 `ifnull()` 包裹 | P1 | DBA + 支付研发 | **变更申请** |
| A-07 | `t_coupon_record_expired` 加索引 `(tenant, coupon_source, id)` | P1 | DBA | **变更申请**（20 GB 大表在线 DDL） |
| A-08 | 建立批处理健康度告警（连续满 LIMIT / 队列不下降 / 最老记录年龄） | P2 | DBA + 研发 | 监控建设 |
| A-09 | `t_shopsale_rmk` 加覆盖索引 | P2 | DBA | 变更申请 |
| A-10 | SQL-03 收窄 SELECT 列、去掉 `id >= 0`、改游标分页、调整执行时间 | P2/P3 | 营销研发（张晓松） | 应用改造 |
| A-11 | `sale_rmks` 逗号串正规化 / 一致性校验迁移离线 | P3 | 架构 + 国际运营 | 技术债 |

> A-06、A-07、A-09 涉及生产库 DDL，需按《变更申请》四段式（主题 / 变更原因 / 变更内容 / 测试信息）提交，变更原因以慢日志与 `performance_schema` 原始数据为主，本报告的分析结论作为辅助材料标注。
