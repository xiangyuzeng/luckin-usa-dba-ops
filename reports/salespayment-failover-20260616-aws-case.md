# AWS Support Case — RDS Multi-AZ Failover: `aws-luckyus-salespayment-rw`

| | |
|---|---|
| **Incident date** | 2026-06-16 00:24:20–00:24:55 UTC (2026-06-15 20:24 EDT) |
| **Instance** | `aws-luckyus-salespayment-rw` (payment-critical) |
| **AWS account** | 257394478466 |
| **Region** | us-east-1 |
| **Prepared by** | 曾翔宇 (David Zeng), Senior DBA |
| **Prepared on** | 2026-06-16 |
| **Alert** | 宙斯 P2 —【DB告警】AWS RDS 发生重启或者主从切换 (legacy policy id=92) |
| **Status** | ✅ Auto-recovered; instance `available` and healthy |

---

## 1. AWS Support Case (copy-paste ready)

**Console fields**

| Field | Value |
|---|---|
| Service | Relational Database Service (Amazon RDS) |
| Category | Availability / Multi-AZ Failover (or "Instance issues" / "Performance") |
| Severity | System impaired (Normal) — event self-healed; RCA requested for a payment-critical DB |
| Region | us-east-1 |
| Account ID | 257394478466 |

**Subject**

```
RCA request — Multi-AZ failover on RDS instance aws-luckyus-salespayment-rw caused by primary host network connectivity loss (2026-06-16 00:24 UTC)
```

**Description**

```
Hello AWS Support,

We are requesting a root cause analysis for an unexpected Multi-AZ automatic
failover on a production, payment-critical RDS instance.

== Instance details ==
- DB instance identifier : aws-luckyus-salespayment-rw
- ARN                    : arn:aws:rds:us-east-1:257394478466:db:aws-luckyus-salespayment-rw
- Engine / version       : MySQL 8.0.45
- Instance class         : db.t4g.medium
- Deployment             : Multi-AZ (instance, not cluster)
- AZ before failover     : primary us-east-1b / standby us-east-1a
- AZ after failover      : primary us-east-1a / standby us-east-1b

== Event timeline (from RDS events, UTC) ==
- 2026-06-16 00:24:20.961  Multi-AZ instance failover started.
- 2026-06-16 00:24:35.418  DB instance restarted
- 2026-06-16 00:24:55.864  Multi-AZ instance failover completed
- 2026-06-16 00:24:55.864  The primary host of the RDS Multi-AZ instance is
                           unreachable due to loss of network connectivity.

== Observed impact ==
- DatabaseConnections dropped from a steady ~18-20 to ~5 at 00:24 UTC and fully
  recovered to ~18-21 by 00:26-00:28 UTC.
- Approx. 30-40 seconds of write unavailability during the failover.
- This instance backs our customer payment service, so even a brief write
  interruption can fail in-flight payment transactions that then require
  application-level retry / reconciliation.

== Questions / requests ==
1. Please provide the root cause of the "loss of network connectivity" on the
   former primary host (underlying hardware failure, host network-fabric issue,
   or AWS-side maintenance?).
2. Was this isolated to our instance, or part of a broader network /
   infrastructure event in us-east-1a / us-east-1b around 00:24 UTC on
   2026-06-16?
3. Please confirm the new primary (us-east-1a) and the rebuilt standby are on
   healthy hardware, with no degraded host remaining in our Multi-AZ pair.
4. Any recommended actions on our side to reduce recurrence likelihood or
   shorten failover time (e.g., RDS Proxy, connection-handling best practices)?
5. Please share any internal RCA reference / event ID for this failover for our
   incident record.

Thank you.
```

---

## 1B. AWS 工单（中文正文版）

> 说明：us-east-1（AWS 全球区）技术支持通常以英文响应,提交时建议优先用上方英文正文;本中文版供内部审阅及中文同事参考。

**控制台字段**

| 字段 | 值 |
|---|---|
| Service（服务） | Relational Database Service (Amazon RDS) |
| Category（类别） | 可用性 / Multi-AZ 主从切换（或 "Instance issues" / "Performance"） |
| Severity（严重级别） | System impaired（Normal）— 事件已自愈,因属支付核心库故申请 RCA |
| Region（区域） | us-east-1 |
| Account ID（账号） | 257394478466 |

**Subject（标题）**

```
RCA 请求 — RDS 实例 aws-luckyus-salespayment-rw 因主机网络连接丢失触发 Multi-AZ 主从切换（2026-06-16 00:24 UTC）
```

**Description（正文）**

```
AWS 支持团队,你们好:

我们就一台生产支付核心 RDS 实例发生的一次非预期 Multi-AZ 自动主从切换,
申请根因分析(RCA)。

== 实例信息 ==
- 实例标识符    : aws-luckyus-salespayment-rw
- ARN          : arn:aws:rds:us-east-1:257394478466:db:aws-luckyus-salespayment-rw
- 引擎 / 版本   : MySQL 8.0.45
- 实例规格      : db.t4g.medium
- 部署方式      : Multi-AZ(实例级,非集群)
- 切换前可用区  : 主 us-east-1b / 备 us-east-1a
- 切换后可用区  : 主 us-east-1a / 备 us-east-1b

== 事件时间线(来自 RDS 事件,UTC)==
- 2026-06-16 00:24:20.961  Multi-AZ 故障切换开始
- 2026-06-16 00:24:35.418  数据库实例重启
- 2026-06-16 00:24:55.864  Multi-AZ 故障切换完成
- 2026-06-16 00:24:55.864  RDS Multi-AZ 主机因网络连接丢失而不可达

== 观察到的影响 ==
- DatabaseConnections 在 00:24 UTC 由稳定的 ~18-20 跌至 ~5,并于
  00:26-00:28 UTC 完全恢复至 ~18-21。
- 切换期间约 30-40 秒写不可用。
- 该实例承载客户支付服务,即使短暂写中断也可能导致处理中的支付交易
  失败,需应用层重试 / 对账。

== 问题 / 诉求 ==
1. 请提供原主机"网络连接丢失"的根本原因(底层硬件故障、主机网络结构
   问题,还是 AWS 侧维护?)。
2. 该事件是仅影响我们这一实例,还是 2026-06-16 约 00:24 UTC 期间
   us-east-1a / us-east-1b 更大范围网络 / 基础设施事件的一部分?
3. 请确认新主库(us-east-1a)与重建后的备库均运行在健康硬件上,
   Multi-AZ 主备中不存在仍处于降级状态的主机。
4. 我们侧是否有可降低复发概率或缩短切换时长的建议措施
   (例如 RDS Proxy、连接处理最佳实践)?
5. 请提供本次切换对应的内部 RCA 编号 / 事件 ID,供我们事件记录归档。

谢谢。
```

---

## 2. Investigation summary

**Verdict:** Real event, not a false positive. AWS-side infrastructure failure — the former primary host (us-east-1b) lost network connectivity, and RDS Multi-AZ automatically failed over to the standby (promoted in us-east-1a). Full sequence completed in **~35 seconds**.

**Ruled out:** not OOM / memory exhaustion, not a slow-query overload, not a manual reboot, not a configuration change. Only **one** failover in the prior 24h (plus a routine 07:53 UTC backup) — **no flapping**.

**Recommended follow-ups:**
1. Acknowledge / resolve the 宙斯 alert (policy id=92) — failover complete, no DBA remediation needed.
2. ⚠️ **Payment reconciliation:** have ops/app team check failed or in-flight payment transactions in the **00:24:20–00:24:55 UTC** window for retry/reconciliation.
3. Monitor 30–60 min for buffer-pool warm-up (slow queries may be briefly elevated).
4. File this AWS Support case for RCA; if host-level failover recurs, escalate.

---

## 3. Evidence appendix

### 3.1 RDS events (`aws rds describe-events`, last 24h)

```
2026-06-15 07:53:20 UTC  backup       Backing up DB instance
2026-06-15 07:55:23 UTC  backup       Finished DB Instance backup
2026-06-16 00:24:20 UTC  failover     Multi-AZ instance failover started.
2026-06-16 00:24:35 UTC  availability DB instance restarted
2026-06-16 00:24:55 UTC  failover     Multi-AZ instance failover completed
2026-06-16 00:24:55 UTC  (none)       The primary host of the RDS Multi-AZ instance is
                                       unreachable due to loss of network connectivity.
```

Command used:
```bash
aws rds describe-events \
  --source-identifier aws-luckyus-salespayment-rw \
  --source-type db-instance \
  --region us-east-1 --duration 1440
```

### 3.2 Current instance status (`aws rds describe-db-instances`)

```
Status      : available
MultiAZ     : true
AZ          : us-east-1a   (primary, post-failover)
SecondaryAZ : us-east-1b
Class       : db.t4g.medium
Engine      : MySQL 8.0.45
PendingReboot : none
```

### 3.3 CloudWatch `DatabaseConnections` (Average, around the event)

| Time (UTC) | Connections |
|---|---|
| 00:20 | 19 |
| 00:22 | 18 |
| **00:24** | **5.5  ← failover dip** |
| 00:26 | 16.5 |
| 00:28 | 21.5 (recovered) |
| 00:30 | 20.5 |

### 3.4 Direct DB health check (`SHOW GLOBAL STATUS`, ~00:51 UTC)

```
Uptime            : 1581   (~26 min — confirms 00:24:35 restart)
Threads_connected : 21
Threads_running   : 3
Aborted_clients   : 88     (post-failover stale-connection cleanup — expected)
Slow_queries      : 41     (buffer-pool warm-up — expected)
```
