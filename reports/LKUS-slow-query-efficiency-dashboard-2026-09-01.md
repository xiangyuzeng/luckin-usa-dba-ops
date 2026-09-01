# 效能看板（luckin-efficiency-dashboard）慢查询复盘与修复

| 项目 | 内容 |
|------|------|
| 报告编号 | LCNA-DBA-SQL-2026-0901-D |
| 出具日期 | 2026-09-01 |
| 出具人 | 曾翔宇（DBA / Infrastructure） |
| 背景 | 该看板因性能问题已于 2026-08-25 由 David 停用；本次复盘其慢查询并修复 |
| 数据来源 | CloudWatch 慢日志原文（`aws-luckyus-salesorder-rw`，2026-08-25 当天）+ 现场 `EXPLAIN` + 生产实测 |
| 归属 | **DBA 自有**（账号 `diagtools`，来源 `10.238.3.43` = dbtools02） |

---

## 摘要

停用当天（2026-08-25）留在慢日志里的证据：**14 条 / 138.9 秒 / 2,514.6 万扫描行，单条最高 49.6 秒**。
两条**每 15 分钟执行一次**的实时查询是主因，**两条都在全表扫 `t_order`（133.7 万行）**。

🔴 **其中一条不只是慢，它的结果是错的**：实时「压单」统计**没有任何时间下界**，
把 2025-06-11 以来所有未完成订单都算成「当前压单」——**7,018 单，而 2026-09-01 的真实值是 6 单**。
看板最核心的那个数字，错了约三个数量级。

两条都已修复并合入 main（`73e49da`，经 `84e59e05` 合并）。**一次改动同时修好了计划和数字。**

---

## 一、停用当天的原始证据

CloudWatch 慢日志 `/aws/rds/instance/aws-luckyus-salesorder-rw/slowquery`，
`User@Host: diagtools[...] @ [10.238.3.43]`，2026-08-25：

| 时间 (UTC) | 查询 | Query_time | Rows_examined |
|---|---|---:|---:|
| 05:00:14 | 日更 · 每日每店总量 | 13.91 s | 2,175,548 |
| 05:01:03 | 日更 · 等效商品数（join `t_order_item`） | **49.65 s** | 3,530,563 |
| 05:01:13 | 日更 · 半小时区间 | 9.88 s | 2,175,548 |
| 05:01:51 | 日更 · 半小时区间（join `t_order_item`） | **37.75 s** | 3,530,563 |
| 11:00–13:15，每 15 分钟 ×10 | **实时 · 今日总量 + 压单** | 1.66 ~ 5.88 s | 每次约 1,372,000 |

合计 14 条 / 138.87 秒 / 25,146,417 行。当天 05:00 那批之后再无记录 —— 与停用时点吻合。

> 实时查询**每一次执行都进了慢日志**（阈值 `long_query_time=0.1s`），即它没有「快的时候」。
> 按原定节奏（ET 07:00–19:45 每 15 分钟）每天约 52 轮 × 2 条 ≈ **每天 1.43 亿扫描行**。

---

## 二、根因一：把索引列包进了函数（实时查询 #1）

### 原写法

```sql
FROM luckyus_sales_order.t_order o
LEFT JOIN luckyus_sales_order.t_order_make m ON m.order_id = o.id AND m.tenant = o.tenant
WHERE o.tenant = 'LKUS'
  AND o.pay_time IS NOT NULL
  AND DATE(CONVERT_TZ(o.pay_time, 'UTC', 'US/Eastern')) = DATE(CONVERT_TZ(UTC_TIMESTAMP(), 'UTC', 'US/Eastern'))
  AND o.shop_number NOT LIKE 'US999%' AND o.shop_number <> 'US00000'
GROUP BY o.shop_number
```

### `EXPLAIN`（2026-09-01 实测）

| table | type | possible_keys | key | rows | Extra |
|---|---|---|---|---:|---|
| o | **ALL** | **idx_pay_time** | **NULL** | 1,337,633 | Using where; Using temporary |
| m | eq_ref | uniq_order_id | uniq_order_id | 1 | Using where; Using index |

**`possible_keys` 有 `idx_pay_time`，`key` 却是 `NULL`** —— 优化器看得见这个索引，但用不了：
`DATE(CONVERT_TZ(o.pay_time, ...))` 是 `pay_time` 的函数，不是 `pay_time` 本身，索引有序性对它不成立。
于是每 15 分钟全表扫 133.7 万行，只为取当天那几千单。

### 改写与效果

把边界算成常量、让列裸露：

```sql
  AND o.pay_time >= CONVERT_TZ(%s, 'US/Eastern', 'UTC')   -- 今日 ET 00:00
  AND o.pay_time <  CONVERT_TZ(%s, 'US/Eastern', 'UTC')   -- 次日 ET 00:00
```

| table | type | key | rows | Extra |
|---|---|---|---:|---|
| o | **range** | **idx_pay_time** | **4,845** | Using index condition; Using where; Using temporary |

**1,337,633 → 4,845 行，约 276 倍。** 口径不变（同一个 ET 自然日）。

> 通用判据：**`possible_keys` 有值而 `key` 为 `NULL`，几乎总是「列被函数包住了」**，
> 与 `possible_keys` 本身就是 `NULL`（压根没有可用索引，见 -0901-B 财务对账那三条）是两类不同的病。

---

## 三、🔴 根因二：压单统计没有时间下界 —— 慢，而且错（实时查询 #2）

### 原写法

```sql
FROM luckyus_sales_order.t_order o
JOIN luckyus_sales_order.t_order_item i ON i.order_id = o.id AND i.tenant = o.tenant
LEFT JOIN luckyus_sales_order.t_order_make m ON m.order_id = o.id AND m.tenant = o.tenant
WHERE o.tenant = 'LKUS'
  AND o.pay_time IS NOT NULL
  AND m.finish_time IS NULL
  AND TIMESTAMPDIFF(MINUTE, o.pay_time, UTC_TIMESTAMP()) > 10
  AND ...
GROUP BY o.shop_number
```

**没有任何日期条件。** `m.finish_time IS NULL AND 距今 > 10 分钟` 对**历史上每一笔未完成订单**都成立。

### 错到什么程度（2026-09-01 实测）

| 口径 | 结果 |
|---|---:|
| 该查询实际统计到的订单数（全历史） | **7,018** |
| 最早一笔 | **2025-06-11** |
| 跨越天数 | **440 天** |
| **当日（2026-09-01）真实未完成且超时的订单** | **6**（分布在 4 家门店） |

看板上的「压单」——这块看板存在的理由——长期显示的是一个**约 1,170 倍**于真实值的数字。
它没被质疑过，大概是因为 7,018 这个数看上去并非不可能。

### 还是最贵的一条

`EXPLAIN`：`o` 全表扫 1,337,636 行，再对每行探 `t_order_make` 与 **`t_order_item`（3 GB 宽表）**。
每天 96 次（48 轮 × 2 表探测）。

### 修复

补上与 #1 相同的 ET 自然日边界。修完当日结果：

| 门店 | 压单订单 | 等效商品 |
|---|---:|---:|
| US00008 | 2 | 4 |
| US00009 | 2 | 2 |
| US00004 | 1 | 1 |
| US00027 | 1 | 2 |

合计 6 单 —— 与独立核对的当日真实值一致。**计划与数字被同一处改动同时修好。**

---

## 四、日更链路：本次未改，理由与数据

日更 collector 每次重算 `RETENTION_DAYS = 180` 天（`pipeline/config/settings.py`），
4 条查询各扫 217 万 ~ 353 万行，当天合计约 111 秒。它的写法本身是 sargable 的
（`o.pay_time >= CONVERT_TZ(%s, ...)`），问题只在**窗口太宽**：180 天覆盖了 133 万行表的很大一部分，
优化器因此仍倾向全表扫 —— 与 store-ops 看板同一类问题（-0901-B，B-04）。

**没有一并改的原因**：按扫描量算，两条实时查询约占该看板 DB 负载的 **93%**，日更约 **7%**；
而日更改增量需要 payload 拼接逻辑（就是今天 store-ops 那一套），改动面和风险都大得多。
先修 93% 并让看板可以重新上线，比把两件事捆在一起更稳妥。

**建议下一步**：复用 store-ops 的增量方案（每次只重算最近 3 天，splice 进上一份 payload，
周日全量重算，上一份 payload 太旧则自动转全量）。预计日更从 111 秒降到秒级。

### 顺带已改

日更时刻从 **01:00 ET（05:00 UTC）移到 02:45 ET（06:45 UTC）**：
05:00 UTC 正是 salesorder 的夜间批量窗口（该时段 CPU 24.2% vs 基线 8~11%），
store-ops 今天已移出该窗口至 02:30 ET；02:45 同时避开 store-ops，两者不会同时扫 `t_order`。

---

## 五、回归保护

新增 `pipeline/tests/test_query_shape.py`（5 个用例），把这次的三件事钉住：

1. 任何 `WHERE` 子句都不得过滤被函数包住的 `o.pay_time`；
2. 两条实时查询都必须带 ET 自然日的上下界；
3. 日更时刻不得是 01:00 ET。

把旧文本放回去，三项分别失败。

---

## 六、行动项

| 编号 | 事项 | 优先级 | 归属 | 状态 |
|---|---|---|---|---|
| D-01 | 实时查询 #1 改 sargable（1,337,633 → 4,845 行） | P1 | DBA（本仓库） | **已合并 `73e49da`** |
| D-02 | 实时查询 #2 补 ET 日边界（修正 7,018 → 6，并消除全表扫） | P1 | DBA（本仓库） | **已合并 `73e49da`** |
| D-03 | 日更时刻移出 05:00 UTC 批量窗口 | P2 | DBA（本仓库） | **已合并 `73e49da`** |
| D-04 | 日更改增量（复用 store-ops 方案），180 天窗口收窄 | P2 | DBA（本仓库） | 待做 |
| D-05 | 重新上线前，先跑一轮实时 collector 核对压单数与门店明细 | P1 | DBA | 待做（需容器） |

> 该看板的查询指纹**不在慢 SQL 台账里**：它 2026-06-01 起就停了，
> `t_dba_collect_slow_query` 的 7 天窗口里没有它。本次是按**执行账号**回溯慢日志原文找到的
> （手法见 -0901-C）。重新上线后应把新指纹按周流程入册。
