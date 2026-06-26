# AWS 账单上涨核对报告 — 根因：GuardDuty Runtime Monitoring

**日期**: 2026-06-26
**分析人**: 曾翔宇 (David Zeng) / DBA
**账号**: 257394478466 (us-east-1) · IAM: databasecheck
**触发**: "AWS 账单多了 ~$2000，疑似升级导致"

---

## 一、结论（TL;DR）

账单上涨的**根因**是 **2026-03-19 03:01 UTC 开启的 GuardDuty 付费安全功能**，**不是**实例升配、**也不是**新购预留实例。

- **Runtime Monitoring（运行时监控，EC2 + EKS agent 按 vCPU 计费）** + **EBS Malware Protection**
- GuardDuty 从 ~$90/月 → ~$1,400/月，**持续净增约 +$1,300/月**
- 发生在 Cost Explorer 明细数据起点（4/14）之前，所以单纯按月对比看不出来；由 AWS 成本异常检测器 + detector 时间戳定位

用户直觉"是升级导致"正确 —— 是**GuardDuty 安全功能的升级开启**，非实例升配。

---

## 二、证据链

### 1. detector 配置时间戳（实锤，精确到分钟）
```
Detector eccbd3135d133038ad6fecc912dd5fef  UpdatedAt: 2026-03-19T03:01:24Z
RUNTIME_MONITORING        : ENABLED  @ 2026-03-19T03:01:24   ← 根因
  ├─ EC2_AGENT_MANAGEMENT : ENABLED  @ 2026-02-11   (自动给 233 台 EC2 装 agent)
  └─ EKS_ADDON_MANAGEMENT : ENABLED  @ 2026-02-11
EBS_MALWARE_PROTECTION    : ENABLED  @ 2026-03-19T03:00:30   ← 根因
```

### 2. AWS 成本异常检测（`ce get-anomalies`，3/19 起最大一笔）
| 日期 | 服务 | 影响 | 实际 vs 预期 | 性质 |
|---|---|---|---|---|
| **3/19–4/4** | **GuardDuty** | **+$630** | $680 vs $49（**+1274%**） | **持续，根因** |
| 6/12–6/16 | EC2 m6i.8xlarge | +$553 | $1,382 vs $830 | 一次性，已回落 |
| 4/4–4/7 | EC2 | +$82 | $448 vs $366 | 一次性 |
| 5/19 | RDS db.t4g.xlarge MultiAZ | +$32 | — | couponservice 升配 |
| 其余 | S3/CloudFront/API GW | 几分钱~$5 | — | 噪声 |

GuardDuty 异常根因用量类型：`PaidEKSvCPUMonitored` $372、`PaidKubernetesAuditLogsAnalyzed` $126、`PaidS3DataEventsAnalyzed` $96、`PaidEventsAnalyzed-Bytes` $64。

### 3. GuardDuty 月度实测
- 3/19 前 ≈ $90/月（异常检测 expected）
- 4 月 $841(17天) · 5 月 $1,438 · 6 月(1-25) $1,310 → 稳态 ~$1,400/月

---

## 三、排除项（重要，避免误判）

### EC2 RI 月费 $24K —— 不是涨价来源
- `ec2 describe-reserved-instances`：**202 台 EC2 RI 全部 2025-08-27/28 购买**，No Upfront，2026-08 到期。无任何 2026 新购。
- 费率求和 $32.43/h × 730 ≈ $23,677/月，对上账单 "Recurring" $24K。**2025-08 就一直存在。**
- RDS/ElastiCache/OpenSearch RI 同样全是 2025-08 购买，部分已 retired，无 2026 新购。
- RI 覆盖率 89.6%（`ce get-reservation-coverage`），正常工作，非空转。c6i.2xlarge/4xlarge 显示 0% 是 RI 尺寸弹性把容量汇集到 c6i.large(100%)/xlarge(72%) 所致。

### 月对月本就持平
- 5/1–25 ≈ $47,180 vs 6/1–25 ≈ $47,264（+0.2%）；整月均 ~$52K。
- 底层日均用量 4/5/6 月都 ~$890/天，无用量增长。
- 4 月 CE 数据仅 4/14–30（前 13 天为 $0），月度对比失真的根源。

### 实例升配事件（CloudTrail）—— 量级太小
8 起 `ModifyDBInstance` 改规格，全是小库（t4g.medium/large/xlarge、docdb r6g.large），合计撑死几百美元/月，且 RDS 总费用 5→6 月反而下降。

---

## 四、相对旧基线 $49,645 的拆账

| 来源 | 金额/月 | 持续? |
|---|---|---|
| 🔴 GuardDuty Runtime Monitoring + EBS Malware（3/19） | ~+$1,300 | 是 |
| 用量自然增长 + 小库升配 | ~+$700–1,000 | 是 |
| EC2 6/12–16 临时尖峰 | +$553 | 一次性 |
| EC2 RI $24K | $0（非新增） | — |
| **持续净增合计** | **≈ +$2,000–2,300/月** | 与感知一致 |

---

## 五、决策建议

Runtime Monitoring 是实打实的运行时入侵检测能力。
- **若为安全合规有意开启** → 合理支出，保留。
- **若误开或可收窄**：关闭 `EC2_AGENT_MANAGEMENT`（不再监控 233 台 EC2，通常是 vCPU 费用大头）只保留 EKS，或整体关 `RUNTIME_MONITORING`，预计省 ~$1,000–1,300/月。
- **下一步**：先找 Michael / 安全负责人确认是不是 3 月的安全加固，再决定是否调整。

---

## 六、数据局限
- Cost Explorer 明细数据只回溯到 **2026-04-14**，3/19 的变更靠异常检测 + detector 时间戳定位。
- CloudTrail `lookup-events` 仅 90 天（到 ~3/28），3/19 的 `UpdateDetector` 操作人查不到。
- `databasecheck` 无 `ce:GetReservationCoverage/GetAnomalies/GetCostAndUsageWithResources`（已由 xiangyu.zeng 在 dbtools02-prod 用更高权限补跑）；资源级费用需 payer 账户在 CE 设置里 opt-in。
