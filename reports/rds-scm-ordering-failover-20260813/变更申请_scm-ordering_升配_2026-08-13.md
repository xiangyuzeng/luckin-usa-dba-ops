# 生产变更申请（CR）— RDS 实例升配（可选 / 计划内）

| 项目 | 内容 |
|------|------|
| **变更标题** | `aws-luckyus-scm-ordering-rw` 实例规格升配 db.t4g.micro → **db.t4g.small** |
| **变更类型** | **计划内变更（Normal Change）— 抗风险余量优化** |
| **优先级** | **P3（可选）** |
| **申请人** | 曾翔宇 (David Zeng) / DBA |
| **审批人** | Michael (CTO) |
| **申请时间** | 2026-08-13（v2 修订 23:15 UTC） |
| **建议执行窗口** | 任意低峰窗口（美东 23:00 之后），**无时间压力** |
| **AWS 账号 / 区域** | 257394478466 / us-east-1 |
| **关联故障** | 2026-08-13 21:55 UTC Multi-AZ 主从切换（P0），RCA v2 见同目录报告 |

---

## ⚠️ v2 修订说明（请勿使用 v1 版本）

本申请 v1 版本以**紧急变更**提出，理由是"今晚 06:00–07:00 UTC 将再次耗尽额度并切换"，
并推荐升配至 db.t4g.medium。经复测，**该紧急性前提不成立**：

- 引发故障的异常负载**已随重启终止**，`EBSByteBalance%` 已由 97% **回升至 99%**，
  ReadIOPS 已回落至 7–20（13:00 前的基线水平）；
- v1 依据的"工作集 800 MB 是 buffer pool 的 6 倍"**是错的** —— 800 MB 是全库大小，
  **实测热数据仅约 114 MB**，128 MB 的 buffer pool 尚有 1,068 个空闲页，稳态命中率 98.3%。

**因此本变更由紧急降为计划内，推荐规格由 medium 下调为 small，且不再是必须项。**
详见 RCA v2 第 3.2 / 3.3 / 3.4 节。

---

## 一、变更内容

将生产实例 `aws-luckyus-scm-ordering-rw` 的实例规格从 `db.t4g.micro`（1 GB 内存）
升配至 `db.t4g.small`（2 GB 内存）。

**不涉及**：引擎版本、参数组、存储容量/类型、网络与安全组、备份策略，均保持不变。

---

## 二、背景

2026-08-13 21:55:26 UTC，该实例发生 Multi-AZ 主从切换，AWS 事件原因为
**"The RDS Multi-AZ primary instance is busy and unresponsive."**，业务不可用约 **55 秒**。

根因为 **EBS 吞吐额度（`EBSByteBalance%`）耗尽**：13:00 UTC 起实例上出现一段异常读负载
（ReadIOPS 由 5–25 升至 70–130 并持续 9 小时），额度在 8.5 小时内由 99% 耗尽至 0%，
EBS I/O 被限速后主实例无法提供服务，触发切换。

**该异常负载已随重启终止，额度已恢复正常，当前无风险。**

---

## 三、本变更的定位：这不是根因修复

**必须说明：升配并不解决本次故障的根因。** 根因是那段来源不明的异常读负载，
以及缺失的额度告警。相应的 P1 措施（查清负载来源、增加 `EBSByteBalance% < 30%` 告警）
和 P2 措施（补两条索引）另行推进，见 RCA v2 第 4 节。

本变更的**唯一价值是抗风险余量**：

| 维度 | db.t4g.micro（现状） | db.t4g.small（申请后） |
|------|----------------------|------------------------|
| 内存 | 1 GB | 2 GB |
| buffer pool | 128 MB（实测已用 114 MB，尚有空闲） | 约 0.95 GB |
| EBS 基线带宽 | 87 Mbps（10.88 MB/s） | 174 Mbps（约 21.7 MB/s） |

即：同类异常负载若再次出现，small 规格下额度消耗速度约减半，可争取到约 2 倍的响应时间，
且 buffer pool 余量能更好吸收大范围扫描造成的缓存冲刷。

**为什么不选 medium：** 稳态实测热数据仅 114 MB，不存在内存瓶颈；且故障期间实测读吞吐
1 分钟峰值仅 3.37 MB/s，**不到 micro 基线 10.88 MB/s 的三分之一**，"需要更高基线带宽"
这一理由数据上并不成立。跳两级缺乏依据。

---

## 四、成本影响

按 us-east-1 / MySQL / Multi-AZ 按需价，套用 EDP 31% 折扣（On-Demand × 730h × 0.69）：

| 规格 | 按需单价 | 折后月成本 | 月度净增 |
|------|----------|------------|----------|
| db.t4g.micro（现状） | $0.032/h | $16.12 | — |
| **db.t4g.small（申请）** | **$0.065/h** | **$32.74** | **+$16.62** |
| db.t4g.medium（未采纳） | $0.129/h | $64.98 | +$48.86 |

**月度净增 $16.62（年化 $199.44）**，占当前 AWS 月度总支出 $49,645 的约 **0.03%**。

---

## 五、影响与风险评估

| 项目 | 评估 |
|------|------|
| **业务中断** | 约 **60 秒**。实例为 Multi-AZ，RDS 先升配备库 → 主备切换 → 再升配原主库 |
| **影响范围** | SCM 订货服务（`luckyus_scm_ordering`）。建议美东 23:00 后执行，门店已闭店 |
| **数据风险** | **无**。规格变更不涉及数据迁移、不改变存储卷、不影响备份与 binlog |
| **应用影响** | 应用需具备连接重连能力。今日 21:55 切换已实测：应用自动恢复连接，无需人工介入 |
| **不变更的风险** | **低**。当前额度 99%、稳态无内存瓶颈。风险仅在于同类异常负载再次出现时缺少余量 —— 而该场景的首要防线应是 P1 的额度告警，而非升配 |
| **变更失败风险** | 低。RDS 规格变更为标准托管操作，失败时实例自动保持原状态 |

---

## 六、执行步骤

**1）变更前检查**
```bash
aws rds describe-db-instances --db-instance-identifier aws-luckyus-scm-ordering-rw \
  --region us-east-1 \
  --query 'DBInstances[0].{Class:DBInstanceClass,Status:DBInstanceStatus,MultiAZ:MultiAZ,AZ:AvailabilityZone}'
```

**2）执行升配**
```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-scm-ordering-rw \
  --db-instance-class db.t4g.small \
  --apply-immediately \
  --region us-east-1
```

**3）观察切换过程**
```bash
aws rds describe-events --source-identifier aws-luckyus-scm-ordering-rw \
  --source-type db-instance --duration 30 --region us-east-1
# 等待状态由 modifying 回到 available
```

---

## 七、验证方法（变更后 30 分钟内）

| # | 验证项 | 预期结果 |
|---|--------|----------|
| 1 | `DBInstanceClass` | `db.t4g.small`，`DBInstanceStatus` = `available` |
| 2 | `SELECT @@innodb_buffer_pool_size/1024/1024` | 由 128 MB 提升至约 **950 MB** |
| 3 | `Innodb_buffer_pool_pages_free` | 大量空闲页（预期热数据仍约 114 MB） |
| 4 | CloudWatch `EBSByteBalance%` | 维持 99–100% |
| 5 | 业务侧 | SCM 订货功能正常，应用日志无持续连接异常 |

> 注意：由于稳态本就无内存瓶颈，**不应期待 ReadIOPS 或命中率有明显改善** ——
> 本变更的收益体现在异常负载场景下的余量，而非日常指标。

---

## 八、回滚方案

```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-scm-ordering-rw \
  --db-instance-class db.t4g.micro \
  --apply-immediately --region us-east-1
```
同样约 60 秒中断。

---

## 九、建议的决策方式

考虑到本变更为**可选项**，以下两种决定都是合理的：

- **方案 A（推荐）**：**先做 P1/P2 —— 查清 13:00 UTC 负载来源、加额度告警、补两条索引，
  再回头评估是否仍需升配。** 很可能索引和告警到位后，升配就没必要了。
- **方案 B**：直接批准本次升配（$16.62/月），以最小成本换取即时余量，P1/P2 并行推进。

**不建议的做法**：仅升配而不做 P1/P2 —— 那样根因仍在，只是把下一次故障推迟。

---

**申请人签字**：曾翔宇 (David Zeng) ______________  日期：2026-08-13

**审批人签字**：Michael (CTO) ______________  日期：__________
