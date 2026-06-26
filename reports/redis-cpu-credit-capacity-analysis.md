# Redis (ElastiCache Burstable) CPU 积分容量风险分析

**作者**: 曾翔宇 (David Zeng) — Senior DBA / Infrastructure
**日期**: 2026-06-26
**账户/区域**: 257394478466 / us-east-1
**采集窗口**: 过去 14 天 (CloudWatch `AWS/ElastiCache`, Period=3600)
**范围**: 156 个 ElastiCache Redis 节点(78 主从对),其中 154 个 burstable 节点纳入积分分析

---

## TL;DR

- 你们的 Redis 全部跑在 **burstable 机型(T3/T4g)**,"积分"= **CPU Credits**:平时 CPU 受限到 baseline,靠攒下的积分允许短时突增;积分耗尽 → ElastiCache 把 CPU **限流到 baseline**(无 unlimited 透支模式)→ 延迟飙升。
- **真实风险 = 极低。** 全队列 `EngineCPUUtilization` 峰值最高仅 **9.3%**(p50=0.5%),没有任何节点 Redis 单线程跑到过半核;积分余额中位数 = **288(满)**,业务**从未消耗积分**。
- 14 天内出现的 3 个"积分触底"节点全是 **节点 recovery/重建的生命周期假象**(新节点从 0 积分充电),**不是业务过载**。
- 建议:加一条"积分低 + CPU 高于 baseline 持续 1h"的复合告警(自动忽略生命周期充电);机型选型合理,无需为积分扩容。

---

## 1. 机制:积分怎么算、突增规则

burstable 节点均为 2 vCPU。CPU Credit 规则:

- **1 积分 = 1 vCPU 跑满 1 分钟**。
- 节点以固定速率**持续赚积分**,按**实际 CPU 用量花积分**。CPU = baseline 时赚=花,净额 0。
- CPU **< baseline** → 攒积分(封顶上限);**> baseline** → 透支积分。
- 积分**余额到 0** → CPU 被**限流到 baseline**。
  ⚠️ ElastiCache 的 T 节点**不支持 EC2 的 unlimited 透支模式**,所以耗尽 = **性能被掐 = 延迟风险**,不是额外计费。

| 机型 | 节点数 | baseline(整机) | earn 速率 | 积分上限 |
|---|---:|---:|---:|---:|
| `cache.t4g.micro` | 129 | 10% | 12/小时 | 288 |
| `cache.t3.micro` | 6 | 10% | 12/小时 | 288 |
| `cache.t4g.small` | 15 | 20% | 24/小时 | 576 |
| `cache.t4g.medium` | 4 | 20% | 24/小时 | 576 |
| `cache.m6g.large` | 2 | 固定性能(无积分约束) | — | — |

---

## 2. 怎么拿指标(三个问题对应的指标)

全部在 CloudWatch namespace `AWS/ElastiCache`,维度 `CacheClusterId`(主从分开看):

| 问题 | 指标 | 读法 |
|---|---|---|
| 集群有多少积分可用 | `CPUCreditBalance` (Average, 最新值) | 当前余额;÷ 上限 = 健康度 |
| 是否达到过限制 | `CPUCreditBalance` (**Minimum**, 14d) **+** `CPUUtilization` (Maximum) | 余额贴 0 **且** 整机 CPU 持续 > baseline = 真限流 |
| 量化 CPU 容量风险 | `CPUUtilization`(整机,花积分依据) **+** `EngineCPUUtilization`(Redis 单线程,真饱和信号) | 套用第 3 节公式 |

复现命令:
```bash
aws cloudwatch get-metric-data --region us-east-1 \
  --metric-data-queries '[{"Id":"bal","MetricStat":{"Metric":{"Namespace":"AWS/ElastiCache",
    "MetricName":"CPUCreditBalance","Dimensions":[{"Name":"CacheClusterId","Value":"luckyus-XXX-001"}]},
    "Period":3600,"Stat":"Minimum"}}]' \
  --start-time $(date -u -d '14 days ago' +%FT%T) --end-time $(date -u +%FT%T)
```

> ⚠️ **方法论坑**:`CPUCreditBalance` 的 Minimum 贴 0 **不等于过载**。节点 failover/重建后**从 0 积分开始充电**,Minimum 自然是 0。必须用 `aws elasticache describe-events` 排除 recovery/failover,并核对同期 `CPUUtilization` 是否真的持续高于 baseline。本次 3 个"触底"节点全是这个假象(见第 4 节)。

---

## 3. 量化:每天多长时间尖峰会耗尽积分

设整机 CPU 峰值 = p%,baseline = b%(2 vCPU 节点),off-peak = q%:

- **花积分速率** = `1.2·p` (积分/小时);**净透支** `D = 1.2·(p − b)`
- **满积分单次持续尖峰耗尽**:`T_耗尽 = 积分上限 / D`
- **可长期维持的每日尖峰时长**:`t_可持续 = 24·(b − q)/(p − q)`

关键约束:**Redis 单线程**,单个尖峰最多打满 1 个核 = 整机 ~**50%**(p=100% 需引擎+后台同时占满两核,极端)。off-peak 取实测 q≈2%。

| 机型 | 尖峰强度 p | 净透支 D | 满积分撑多久 | 每日可持续尖峰 |
|---|---|---:|---:|---:|
| **micro**(上限288, b10) | 50%(单核满) | 48/h | **6.0 小时** | **~4 小时/天** |
| micro | 100%(双核满,极端) | 108/h | 2.7 小时 | ~2 小时/天 |
| **small/medium**(上限576, b20) | 50% | 36/h | **16 小时** | **~9 小时/天** |
| small/medium | 100% | 96/h | 6.0 小时 | ~4.4 小时/天 |

**读法**:一个 micro 节点即使把 Redis 一个核**持续打满**,也要 **6 小时**才从满积分耗尽;每天尖峰只要 ≤ **4 小时**即可永久自持。

---

## 4. 本队列真实风险

实测分布(154 burstable 节点,14 天):

| 指标 | p50 | p90 | max |
|---|---:|---:|---:|
| `EngineCPUUtilization`(Redis 单线程) | 0.5% | 1.9% | **9.3%** |
| `CPUUtilization`(整机) | 11.9% | 17.0% | 34.9% |
| `CPUCreditBalance` min(14d) | — | — | 中位数 **288(满)** |

- 整机 CPU >20% 的仅 **3** 个节点;Redis 引擎 >50%(半核)的 **0** 个。
- 实际峰值几乎贴着 baseline,到不了透支区。典型 micro 节点峰值 18% → D=1.2·8=9.6/h → 从满积分要 **30 小时连续**才耗尽,而它从不持续。
- **结论:CPU 积分容量风险 = 极低。** 唯一短暂掉积分的是节点 recovery(新节点 ~24–30h 充满),期间被限到 baseline——真实但**自愈**的脆弱窗口。

### 14 天内的"积分触底"节点(全为生命周期假象)

| 节点 | bal_min | cpu_max | engine_max | 判定 |
|---|---:|---:|---:|---|
| `luckyus-ibbcauthbackend-001/002` | 0.0 | 34.9% | 0.4% | 仅 60h 指标历史 + 线性充电曲线 → 新节点重建 |
| `luckyus-scm-purchase-003` | 0.3 | 14.9% | 0.5% | `describe-events` 显示 2026-06-16 "Finished recovery" → 节点恢复 |

均非业务过载:Redis 引擎近乎空闲(<0.5%),掉积分的 CPU 来自后台进程(快照/复制/TLS/引导)。

### CPU Util 峰值 Top 25(逐节点)

| cluster | node | baseline | credit_max | bal_min(14d) | cpu_max | engine_max |
|---|---|---:|---:|---:|---:|---:|
| luckyus-ibbcauthbackend-001 | cache.t4g.micro | 10% | 288 | 0.0 | 34.9% | 0.4% |
| luckyus-ibbcauthbackend-002 | cache.t4g.micro | 10% | 288 | 0.0 | 34.3% | 0.4% |
| luckyus-waf-001 | cache.t4g.micro | 10% | 288 | 288.0 | 20.5% | 2.1% |
| luckyus-scm-commodity-001 | cache.t4g.micro | 10% | 288 | 288.0 | 18.4% | 1.0% |
| luckyus-qualitycontrol-001 | cache.t4g.micro | 10% | 288 | 288.0 | 18.3% | 0.4% |
| luckyus-mdm-001 | cache.t4g.micro | 10% | 288 | 287.8 | 18.1% | 0.4% |
| luckyus-ifitax-001 | cache.t4g.micro | 10% | 288 | 287.9 | 17.9% | 0.5% |
| luckyus-scm-commodity-002 | cache.t4g.micro | 10% | 288 | 288.0 | 17.8% | 0.5% |
| luckyus-ilkm-001 | cache.t4g.micro | 10% | 288 | 288.0 | 17.7% | 1.9% |
| luckyus-isales-commodity-001 | cache.t4g.medium | 20% | 576 | 576.0 | 17.5% | 1.6% |
| luckyus-qualitycontrol-002 | cache.t4g.micro | 10% | 288 | 287.9 | 17.3% | 0.4% |
| luckyus-onepiece-002 | cache.t4g.micro | 10% | 288 | 288.0 | 17.3% | 0.4% |
| luckyus-billcenterservice-001 | cache.t4g.micro | 10% | 288 | 288.0 | 17.1% | 1.0% |
| luckyus-isales-marketcapi-001 | cache.t4g.micro | 10% | 288 | 288.0 | 17.1% | 1.5% |
| luckyus-shopsale-002 | cache.t4g.micro | 10% | 288 | 288.0 | 17.1% | 0.9% |
| luckyus-isales-crm-001 | cache.t4g.micro | 10% | 288 | 288.0 | 17.0% | 4.0% |
| luckyus-imessageflow-002 | cache.t4g.micro | 10% | 288 | 288.0 | 16.9% | 0.4% |
| luckyus-scm-ordering-001 | cache.t4g.micro | 10% | 288 | 287.9 | 16.9% | 0.7% |
| luckyus-daq-002 | cache.t4g.micro | 10% | 288 | 287.9 | 16.9% | 0.4% |
| luckyus-iriskcontrol-002 | cache.t4g.micro | 10% | 288 | 288.0 | 16.7% | 0.6% |
| luckyus-igers-002 | cache.t4g.micro | 10% | 288 | 288.0 | 16.5% | 0.4% |
| luckyus-igers-001 | cache.t4g.micro | 10% | 288 | 288.0 | 16.4% | 0.5% |
| luckyus-iriskcontrol-001 | cache.t4g.micro | 10% | 288 | 287.9 | 16.4% | 1.9% |
| luckyus-chronus-001 | cache.t4g.micro | 10% | 288 | 288.0 | 16.3% | 0.5% |
| luckyus-isales-tradecapi-002 | cache.t4g.micro | 10% | 288 | 288.0 | 16.2% | 0.7% |

> 全部 154 节点明细见同目录 `redis-cpu-credit-node-detail.csv`。

---

## 5. 建议

1. **复合告警**:`CPUCreditBalance < 50`(micro)/ `< 100`(small/medium) **且** `CPUUtilization > baseline` 持续 1h 才告警——能抓真过载,自动忽略生命周期充电假阳性。
2. **机型选型合理**:micro 节点引擎峰值 <10%,无积分压力;反而说明无需为积分扩容。降配空间需结合内存使用另行评估(已是最小档,降配可能性低)。
3. **recovery 后观察**:节点 failover/重建后 24h 内积分未满、延迟敏感,建议短期重点观察。
