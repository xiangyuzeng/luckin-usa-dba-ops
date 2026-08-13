# 故障根因分析 — aws-luckyus-scm-ordering-rw 主从切换（2026-08-13）

**告警**：【DB告警】AWS RDS 发生重启或者主从切换_语音 — P0（旧版策略 id=93 迁移）
**实例**：`aws-luckyus-scm-ordering-rw` | **结论**：✅ **真实告警（非误报）**
**排查时间**：2026-08-13 约 22:00–22:45 UTC | **DBA**：曾翔宇 (David Zeng)

---

## 1. 摘要

实例确实发生了 Multi-AZ 主从切换并重启。AWS 官方事件原因为：
**"The RDS Multi-AZ primary instance is busy and unresponsive."**（主实例繁忙且无响应）

根因：**db.t4g.micro 规格过小，导致 EBS 吞吐额度（`EBSByteBalance%`）耗尽**。
该实例仅有 128 MB 的 InnoDB buffer pool，无法容纳约 800 MB 的工作集，因此几乎所有读请求
都变成物理 EBS 读。13:00 UTC 左右出现负载阶跃变化，持续物理读超过了 t4g.micro 的 EBS 基线
吞吐额度；额度在 8.5 小时内线性耗尽归零后，EBS I/O 被限速到基线水平，主实例无法继续提供
I/O 服务，RDS 随即将其切换。

**这不是** CPU、内存、连接数或锁的问题 —— 上述指标全程平稳正常。

**今天这已经是第二台以完全相同方式故障的实例**（`aws-luckyus-iopocp-rw` 在 2026-08-13
早些时候以相同特征发生切换）。同样的实例规格，同样的机理。

### ⚠️ 复发风险 —— 该负载仍在运行

切换后额度桶重置回 99%，但读负载立即恢复（ReadIOPS 74 → 151），且额度**已经开始回落
（99% → 98%）**。按观测到的消耗速率（约 11.6%/小时），额度将在
**2026-08-14 约 06:00–07:00 UTC（美东 02:00–03:00）** 再次耗尽 —— 若不处理，今晚很可能
再次发生切换。

---

## 2. 时间线（UTC）

| 时间 | 事件 |
|------|------|
| 03:36–03:39 | 例行自动备份（与本次故障无关） |
| ~13:00 | **负载阶跃变化。** ReadIOPS 5–25 → 70–130；ReadThroughput 30–150 KB/s → 400–970 KB/s；慢查询频率 10 → 约 90 条/30 分钟。`EBSByteBalance%` 自 99% 开始单调下降 |
| 16:00:24–16:00:52 | `t_shop_order_calendar_warehouse_history` 上爆发 33 次 `MAX(dt)` 扫描，每次扫描约 15–16 万行。读峰值 3.37 MB/s；该 30 分钟区间产生 297 条慢查询 |
| 21:30–21:35 | `EBSByteBalance%` 触及 **0%** → EBS I/O 被限速至基线 |
| 21:39–21:54 | **指标空洞** —— 实例停止上报（即无响应的证据）。21:30 区间记录到 1,111 条慢查询，因为所有 I/O 都在阻塞 |
| 21:55:26 | Multi-AZ 主从切换**开始** |
| 21:55:55 | 实例完成重启 |
| 21:56:21 | 上报 "primary instance is busy and unresponsive" + **切换完成** |
| 21:57 | 宙斯 P0 告警触发 |
| 22:00 之后 | 额度重置回 99%；**ReadIOPS 回到 151 —— 消耗重新开始** |

**不可用时长：约 55 秒**（21:55:26 → 21:56:21）。

---

## 3. 证据

### 3.1 耗尽的是吞吐（字节）额度，不是 IOPS
| 指标 | 13:00 → 21:35 表现 |
|------|---------------------|
| `EBSByteBalance%` | **99% → 0%**，单调下降 ← 已耗尽 |
| `EBSIOBalance%` | 平稳在 74–75% ← 全程无风险 |
| `BurstBalance` | 无数据点（gp3 卷不适用该指标） |
| `CPUUtilization` | 6–11%，平稳 |
| `FreeableMemory` | 约 90–108 MB，平稳（无泄漏、无骤降） |
| `DatabaseConnections` | 13–18，平稳 |
| `ReadLatency` | 约 0.7 ms，限速前平稳 |

CPU、内存、连接数均可排除常见的切换诱因。唯一触及上限的指标就是 EBS 字节额度。

### 3.2 实例内存严重不足
| 项目 | 数值 |
|------|------|
| 实例规格 | `db.t4g.micro`（1 GB 内存，2 vCPU） |
| `innodb_buffer_pool_size` | **128 MB** |
| 库大小（`luckyus_scm_ordering`） | 约 800 MB |
| 最大表 `t_auto_order_small_log` | **243.6 MB**（169 万行；其中 144 MB 是索引） |
| Buffer pool 命中率（重启以来） | **92.9%**（健康值应 >99%） |

单张最大表就约为整个 buffer pool 的 2 倍，根本无法缓存，因此读流量持续打到 EBS。

**关于 128 MB buffer pool 的说明：** 这**并非**参数组配置缺陷。参数组 `luckyus-prod-84`
中 `innodb_buffer_pool_size` 未设置（Source = engine-default），由 MySQL 根据探测到的内存
自动伸缩。已用反例验证：`aws-luckyus-salesmarketing-rw`（db.t4g.xlarge，**同一个参数组**）
的 buffer pool 为 **11,520 MB**。t4g.micro 落在 MySQL 的 ≤1 GB 档位，因此被固定为 128 MB。
**结论：升配实例规格会自动修复 buffer pool —— 不需要改参数组。**

### 3.3 具体问题 SQL

**(a) 缺少联合索引 —— `t_shop_order_calendar_warehouse_history`（26 万行）**

```sql
SELECT max(dt) FROM t_shop_order_calendar_warehouse_history
WHERE shop_dept_id = ? AND wh_dept_id = ? AND tenant = 'LKUS';
-- Rows_examined：152,951–160,384   Rows_sent：1
```
现有索引全部是**单列索引**：`idx_shop`（基数 24）、`idx_warehouse`（基数 4）、
`idx_dt`（基数 113）、`idx_operated_time`。由于没有联合索引，优化器只能沿 `idx_dt` 倒序
遍历再过滤，为了返回 1 个值需要扫描全表约 60% 的数据。且以「按门店循环」的方式调用
（16:00 时 28 秒内执行了 33 次）。

**(b) 索引前缀无法命中 —— `t_auto_order_small_log`（169 万行，243.6 MB）**

```sql
SELECT small_class_mid FROM t_auto_order_small_log
WHERE shop_dept_id = ? AND order_date = ? AND tenant = ?;
-- 平均每次执行 143 ms，返回约 214 行
```
唯一的二级索引是 `uniq_shop_small_order_date` =
`(shop_dept_id, small_class_mid, order_date, tenant)`。该查询**没有**过滤 `small_class_mid`
（位于第 2 位），因此只能用到 `shop_dept_id` 这一前缀，之后必须扫描该门店的全部索引条目。
它是**读取量第一的表**（重启以来 14,133 次读，超过其余所有表之和）。

### 3.4 需要如实说明的局限

我无法将持续的 80–150 ReadIOPS 完全归因到某一条具体 SQL。`performance_schema` 在 21:55
重启时已被清空（仅剩约 20 分钟的历史数据），而 `long_query_time = 0.1` 意味着慢查询日志
看不到那些真正贡献了大部分 I/O 的百毫秒以内的语句。主导**表**是明确的
（`t_auto_order_small_log`），上述两条 SQL 也已确认有问题，但 13:00 UTC 那次阶跃变化的
确切触发点尚未定位。

**→ 需运维团队确认：** 2026-08-13 **13:00 UTC（美东 09:00）** 前后是否有发版，或有批
处理/定时任务的调度变更？

### 3.5 全局巡检 —— 当前无其它实例处于风险中

已对全部 RDS 实例扫描 `EBSByteBalance%`（取最低的 15 台）。`scm-ordering` 是唯一异常项
（0–5%）；**其余所有实例均在 99–100%**，包括已恢复的 `iopocp`。共有 61 台实例共用参数组
`luckyus-prod-84`，其中 **32 台是 db.t4g.micro** —— 正是今天已导致两次切换的规格。

---

## 4. 处理建议

| 优先级 | 动作 | 责任人 | 时间要求 |
|--------|------|--------|----------|
| **P0** | **将 `aws-luckyus-scm-ordering-rw` 升配至 `db.t4g.medium`。** 4 GB 内存可将 buffer pool 提升至约 2 GB（足以缓存全部约 800 MB 工作集 → 物理读大幅下降），同时提高 EBS 基线吞吐。实例为 Multi-AZ，可用滚动 modify 方式执行（中断约 1 分钟）。`db.t4g.small` 是最低要求，medium 更有余量。 | DBA + Michael | **今晚美东 02:00 之前** |
| **P1** | 增加联合索引 —— 将 16 万行扫描变为一次索引定位：<br>`ALTER TABLE t_shop_order_calendar_warehouse_history ADD INDEX idx_shop_wh_tenant_dt (shop_dept_id, wh_dept_id, tenant, dt);` | DBA | 升配之后，低峰期执行 |
| **P1** | 增加覆盖索引 —— 使热点查询变为索引覆盖扫描：<br>`ALTER TABLE t_auto_order_small_log ADD INDEX idx_shop_date_tenant_class (shop_dept_id, order_date, tenant, small_class_mid);` | DBA | 升配之后，低峰期执行 |
| **P1** | 与运维确认 13:00 UTC 的负载变化来源（发版？定时任务调整？） | 运维 | 24 小时内 |
| **P2** | 对 `t_auto_order_small_log` 建立数据保留/归档策略（243.6 MB 日志数据，其中 144 MB 为索引）。缩减该表对工作集的收益大于任何单项改动。 | DBA + SCM 研发 | 1 周内 |
| **P2** | **为所有 burstable 规格的 RDS 实例增加 `EBSByteBalance% < 30%` 的 CloudWatch 告警。** 今天的额度消耗过程提前约 5 小时就有征兆但无人察觉，而这一个指标同时预示了今天的两次切换。这是当前价值最高的监控缺口。 | DBA | 1 周内 |
| **P2** | 排查其余 31 台 `db.t4g.micro` 实例中是否还有工作集超过 1 GB 的 | DBA | 2 周内 |

> 两条 DDL 请在**升配之后**执行：虽然都是 Online DDL（`ALGORITHM=INPLACE`），但 I/O 开销较大，
> 在当前 t4g.micro 上执行会消耗掉我们正要保护的那部分额度。

---

## 5. 排查经验沉淀

1. **指标空洞本身就是证据，不是「数据缺失」。** 21:39–21:54 所有 CloudWatch 曲线的断档，
   正是「无响应」这件事本身。
2. **慢查询数量可能是果，不是因。** 在 `long_query_time = 0.1` 下，一旦 I/O 阻塞，日志会被
   `SELECT 1`、`SELECT @@session.transaction_read_only` 这类无害语句刷屏。21:30 的 1,111 条
   尖峰是被限速的结果，而不是触发原因。
3. **burstable 实例上，先看额度类指标，再看 CPU。** 今天两次切换的 CPU/内存都完全正常，
   只有 `EBSByteBalance%` 在动。
4. **实例规格小 → buffer pool 小 → 物理 I/O 被放大。** 在 t4g.micro 上，128 MB 的 buffer pool
   足以把一组普通的查询负载变成持续的 EBS 压力。

---
*排查完成于 2026-08-13 22:45 UTC。所用技能：RDS Alert Investigation SOP v2.0。*
