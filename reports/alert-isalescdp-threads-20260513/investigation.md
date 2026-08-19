# P2 告警调查：aws-luckyus-isalescdp-rw 活跃线程超 24

**告警时间**：2026-05-13 03:59 EDT (07:59 UTC)
**触发条件**：active threads > 24 持续 2 分钟（峰值 45）
**持续**：~5 分钟
**当前状态**：✅ 已自愈，资源全部回落到基线
**等级**：P2，无中断、无连接被拒、无 InnoDB 当前锁等待

---

## 1. 时间线（UTC）

| 时刻 | CPU | 连接数 | WriteIOPS | 状态 |
|---|---|---|---|---|
| 07:30-07:56 | 4-5% | ~50 | 1-10/s | 基线 |
| **07:57** | 4.2% | **276** | **528/s** | 突增起点 |
| **07:58** | 52.6% | 314 | 850/s | IO 峰值 |
| **07:59** | **66.7%** | **315** | 637/s | **告警触发** |
| 08:00 | 64.8% | 294 | 427/s | 峰值期 |
| 08:01 | 30.5% | 296 | 318/s | 开始回落 |
| 08:02 | 14.8% | 285 | 177/s | 回落中 |
| 08:03 | 10.1% | 306 | 160/s | 尾声 |
| **08:04** | 9.4% | **52** | 8/s | **已恢复** |
| 当前 (08:14) | 4.2% | 50, threads_running=4 | 1/s | 基线 |

数据源：CloudWatch `AWS/RDS` per-instance metrics（dbinstance_identifier=`aws-luckyus-isalescdp-rw`）。

---

## 2. 根因

**实时用户分群引擎（icdprealtimeuge）在 08:00:00 UTC 整点触发批量写入。**

| 证据 | 数值 |
|---|---|
| Top user (10 分钟内慢查询数) | `icdprealtimeuge_A_w` — **1032 条**，avg 137ms，max 458ms |
| 次要用户 | `icdprealtimeuge_A_o` — 25 条 |
| 命中表 1 | `t_realtime_user_group_log` — **431 条 INSERT** |
| 命中表 2 | `t_user_state` — 372 条 INSERT |
| 触发源 IP | 8 台应用机并行（10.238.33.19/35.177/35.200/36.188/40.223/43.113/44.11/44.219）|
| 批次特征 | 全部使用同一 `group_no = IQA2UG119363759499378688`、同一 `event_id = 1778659199975`（即 07:59:59.975 UTC）、`be_removed=1`、`tenant=IQA2` |

**机制**：营销用户群 `IQA2UG119363759499378688` 在 08:00 UTC 触发了一次"成员批量移除"事件，每个用户产生一条 audit log INSERT。8 台应用机并行单条插入 → 几百条并发写打到同一张热表 → InnoDB 行锁 + EBS write IOPS 排队 → 单条 INSERT 慢到 0.45s → 连接堆积到 315 → threads_running 持续 > 24，触发告警。

---

## 3. 资源饱和度判断

| 维度 | 评估 |
|---|---|
| CPU | 峰值 66.7%，未饱和（db.t4g.large 2 vCPU） |
| 内存 | FreeableMemory 仅下降 ~120MB，无压力 |
| ReadIOPS | 全程 < 4，无影响 |
| **WriteIOPS** | **峰值 850/s** — t4g.large + gp3 默认 baseline 远低于此，是真正瓶颈 |
| 连接数 | 峰值 315 / max_connections 4000，远未达上限 |
| InnoDB 当前锁等待 | 现在为 0（曾累计 883 次，非异常） |
| `Connection_errors_max_connections` | 0 — 无拒连 |

短结论：**写 IOPS 瓶颈触发的连接堆积**，非数据库容量问题。

---

## 4. 影响

- ✅ 无客户端被拒：max_connections=4000，连接数最高 315
- ✅ 无应用错误：1032 条慢查询全部成功完成（max 0.458s）
- ⚠️ 应用层下游可能感知到 0.4s 级的写延迟（icdprealtimeuge 组件）
- ⚠️ 5 月 13 日整 08:00 UTC 时段：业务侧任何依赖 `t_realtime_user_group_log` / `t_user_state` 写入完成的下游事件流可能延迟

---

## 5. 建议（按收益/成本排序）

| 优先级 | 行动 | 责任方 |
|---|---|---|
| **P1** | 应用侧：`t_realtime_user_group_log` INSERT 改为多行批量（`INSERT INTO ... VALUES (...),(...),(...)`），单批 200-500 行 | icdprealtimeuge 服务 owner |
| **P1** | 应用侧：检查为何 8 台应用机同时处理同一个 group_no — 是 fan-out 设计还是缺少幂等去重？若是后者，加分布式锁 | icdprealtimeuge 服务 owner |
| **P2** | 调度侧：将"整点触发"改为整点 + 随机 30s 抖动，避免与其它 :00 整点任务挤在同一秒 | 调度配置 |
| **P3** | DB 侧：审视 `t_realtime_user_group_log` 是否需要持久化每条事件，能否改写到 Kafka 由消费者异步落库 | DBA + 服务 owner |
| **P3** | 监控侧：当前 `threads_running > 24` 阈值对 db.t4g.large（2 vCPU）偏低；若误报多，考虑提高到 30 或加 `> 60s` 持续条件 | DBA |

---

## 6. 是否需要立即操作

**不需要。** 告警已自愈，下次同一群组的批量操作（通常每日 / 每周一次）会再次触发同样模式。建议在工作时间联系 icdprealtimeuge 服务 owner，按上述 P1 行动做应用层改造，无需 DB 侧紧急动作。

---

**调查耗时**：~4 分钟
**调查者**：DBA David Zeng
**数据源**：CloudWatch `AWS/RDS` metrics + CloudWatch Logs Insights on `/aws/rds/instance/aws-luckyus-isalescdp-rw/slowquery` + 实时 `information_schema.PROCESSLIST`
