# 生产变更申请（CR）— RDS 实例升配

| 项目 | 内容 |
|------|------|
| **变更标题** | `aws-luckyus-scm-ordering-rw` 实例规格升配 db.t4g.micro → db.t4g.medium |
| **变更类型** | 紧急变更（Emergency Change）— 故障修复 |
| **优先级** | **P0** |
| **申请人** | 曾翔宇 (David Zeng) / DBA |
| **审批人** | Michael (CTO) |
| **申请时间** | 2026-08-13 |
| **建议执行窗口** | **2026-08-13 23:00 – 2026-08-14 01:00 美东时间**（即 08-14 03:00–05:00 UTC） |
| **AWS 账号 / 区域** | 257394478466 / us-east-1 |
| **关联故障** | 2026-08-13 21:55 UTC Multi-AZ 主从切换（P0），RCA 见同目录报告 |

---

## 一、变更内容

将生产实例 `aws-luckyus-scm-ordering-rw` 的实例规格从 `db.t4g.micro`（1 GB 内存）
升配至 `db.t4g.medium`（4 GB 内存）。

**不涉及**：引擎版本、参数组、存储容量/类型、网络与安全组、备份策略，均保持不变。

---

## 二、变更背景与必要性

### 2.1 今日已发生一次 P0 故障

2026-08-13 21:55:26 UTC，该实例发生 Multi-AZ 主从切换，AWS 官方事件原因为
**"The RDS Multi-AZ primary instance is busy and unresponsive."**，业务不可用约 **55 秒**。

根因经排查确认为 **EBS 吞吐额度（`EBSByteBalance%`）耗尽**：

- 该实例为 `db.t4g.micro`，MySQL 依据探测内存自动将 buffer pool 定为 **128 MB**；
- 而 `luckyus_scm_ordering` 库约 **800 MB**，单最大表 `t_auto_order_small_log` 即 243.6 MB；
- 工作集约为 buffer pool 的 **6 倍**，数据无法缓存，buffer pool 命中率仅 **92.9%**（健康值应 >99%），
  绝大部分读请求直接落到 EBS；
- 13:00 UTC 起负载阶跃上升（ReadIOPS 5–25 → 70–130），持续物理读超过 t4g.micro 的 EBS 基线吞吐额度，
  `EBSByteBalance%` 在 8.5 小时内由 99% 单调耗尽至 **0%**，EBS I/O 被限速至基线，
  主实例无法继续提供 I/O 服务，RDS 触发切换。

期间 CPU（6–11%）、内存、连接数（13–18）全程平稳 —— **本次故障与业务量、慢 SQL 突增、
锁等待均无关，纯粹是实例规格不足导致的 I/O 额度耗尽。**

### 2.2 不处理则今晚大概率复发

切换后额度桶重置回 99%，但**引发问题的负载仍在运行**：ReadIOPS 已回到 151，
`EBSByteBalance%` 已从 99% 回落至 98%。按实测消耗速率（约 11.6%/小时）推算，
额度将于 **2026-08-14 约 06:00–07:00 UTC（美东 02:00–03:00）再次耗尽**，
届时极可能发生**第二次主从切换**。

### 2.3 这是同一模式的第二次故障

同日早些时候，`aws-luckyus-iopocp-rw`（同为 db.t4g.micro）已因完全相同的机理发生过一次切换。
当前全账号共有 **32 台 db.t4g.micro** 生产实例，属同类风险敞口。

---

## 三、方案选型

| 方案 | 内存 | 预计 buffer pool | 评估 |
|------|------|------------------|------|
| 维持 db.t4g.micro | 1 GB | 128 MB | ❌ 今晚必然复发，且问题会持续存在 |
| 升配 db.t4g.small | 2 GB | 约 0.9 GB | ⚠️ 勉强覆盖 800 MB 工作集，**无余量**，数据继续增长后将再次触顶 |
| **升配 db.t4g.medium** | **4 GB** | **约 1.9 GB** | ✅ **推荐**：约 2 倍余量，同时获得更高的 EBS 基线吞吐 |

**为什么升配能同时解决两个问题：**
MySQL 的 buffer pool 由引擎依据实例内存自动伸缩（参数组 `luckyus-prod-84` 中该参数未显式设置）。
已用反例验证：`aws-luckyus-salesmarketing-rw`（db.t4g.xlarge，**同一参数组**）的 buffer pool 为
11,520 MB。因此 **升配实例规格即可自动放大 buffer pool，无需修改参数组**；
数据能被缓存后物理读大幅下降，EBS 额度消耗随之回到安全水位；更大的规格本身也具备更高的
EBS 基线吞吐，形成双重保障。

> 说明：约 1.9 GB 为按 MySQL 自动伸缩规则的预估值，实际值以变更后执行
> `SELECT @@innodb_buffer_pool_size` 验证为准。

---

## 四、成本影响

按 us-east-1 / MySQL / Multi-AZ 按需价，套用 EDP 31% 折扣（On-Demand × 730h × 0.69）：

| 规格 | 按需单价 | 折后月成本 | 折后年成本 |
|------|----------|------------|------------|
| db.t4g.micro（现状） | $0.032/h | $16.12 | $193.44 |
| db.t4g.small | $0.065/h | $32.74 | $392.88 |
| **db.t4g.medium（申请）** | **$0.129/h** | **$64.98** | **$779.76** |

**月度净增：$48.86（年化 $586.32）。**

对照当前 AWS 月度总支出 $49,645，本次变更增量占比约 **0.10%**。
相对于一次 P0 生产中断（且今晚预计复发）的业务风险，成本可忽略。

---

## 五、影响与风险评估

| 项目 | 评估 |
|------|------|
| **业务中断** | 约 **60 秒**。实例为 Multi-AZ，RDS 先升配备库 → 主备切换 → 再升配原主库，中断仅等同一次切换 |
| **影响范围** | SCM 订货服务（`luckyus_scm_ordering`）。选择美东 23:00 后执行，门店已闭店，订货业务处于低峰 |
| **数据风险** | **无**。规格变更不涉及数据迁移、不改变存储卷、不影响备份与 binlog |
| **应用影响** | 应用需具备连接重连能力。今日 21:55 的切换已实测：应用在切换后自动恢复连接，无需人工介入 |
| **不变更的风险** | 今晚 02:00–03:00 美东预计再次发生非计划切换 —— 属**不可控时间点**的中断，风险高于本次可控变更 |
| **变更失败风险** | 低。RDS 规格变更为标准托管操作，失败时实例自动保持原状态 |

---

## 六、执行步骤

**1）变更前检查**
```bash
# 记录当前状态（用于回滚与比对）
aws rds describe-db-instances --db-instance-identifier aws-luckyus-scm-ordering-rw \
  --region us-east-1 \
  --query 'DBInstances[0].{Class:DBInstanceClass,Status:DBInstanceStatus,MultiAZ:MultiAZ,AZ:AvailabilityZone}'

# 确认当前 EBS 额度水位（若已接近 0，需立即执行）
# CloudWatch: AWS/RDS EBSByteBalance% / DBInstanceIdentifier=aws-luckyus-scm-ordering-rw
```

**2）执行升配**
```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-scm-ordering-rw \
  --db-instance-class db.t4g.medium \
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
| 1 | `DBInstanceClass` | `db.t4g.medium`，`DBInstanceStatus` = `available` |
| 2 | `SELECT @@innodb_buffer_pool_size/1024/1024` | 由 128 MB 提升至约 **1900 MB** |
| 3 | CloudWatch `ReadIOPS` | 由 ~80–150 显著下降（数据进入缓存后物理读减少） |
| 4 | CloudWatch `EBSByteBalance%` | 维持 99–100%，**不再出现单调下降** |
| 5 | Buffer pool 命中率 | `Innodb_buffer_pool_reads / read_requests` 由 7.1% 降至 <1% |
| 6 | 业务侧 | SCM 订货功能正常，应用日志无持续连接异常 |

**关键判据：变更后持续观察 `EBSByteBalance%` 至少 4 小时**，确认曲线走平（而非缓慢下降），
即可判定问题根除。

---

## 八、回滚方案

若升配后出现非预期问题，执行降配回滚（同样约 60 秒中断）：
```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-scm-ordering-rw \
  --db-instance-class db.t4g.micro \
  --apply-immediately --region us-east-1
```
> 注：回滚将恢复到今日已发生故障的配置，仅在升配引入新问题时使用；
> 单纯的额度耗尽问题不应通过回滚处理。

---

## 九、后续动作（不在本次变更范围内）

本次升配解决容量根因。以下为已识别的配套优化项，另行安排：

1. **P1 — 补两条索引**（升配完成后于低峰期执行，均为 Online DDL）：
   - `t_shop_order_calendar_warehouse_history` 加 `(shop_dept_id, wh_dept_id, tenant, dt)`
     —— 现状：为返回 1 个值需扫描 26 万行中的 16 万行；
   - `t_auto_order_small_log` 加 `(shop_dept_id, order_date, tenant, small_class_mid)`
     —— 现状：索引前缀失配，只能用到首列。
2. **P1 — 向运维确认** 13:00 UTC（美东 09:00）前后是否有发版或定时任务调度变更。
3. **P2 — 补监控告警**：为所有 burstable 规格 RDS 增加 `EBSByteBalance% < 30%` 告警。
   今日两次切换该指标均提前约 5 小时给出征兆但无告警覆盖 —— **当前价值最高的监控缺口**。
4. **P2 — 排查其余 31 台 db.t4g.micro** 中是否还有工作集超过 1 GB 的实例。

---

**申请人签字**：曾翔宇 (David Zeng) ______________  日期：2026-08-13

**审批人签字**：Michael (CTO) ______________  日期：__________
