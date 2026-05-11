# Redis ElastiCache 网络带宽限流分析报告

**报告编号**: LCNA-DBA-2026-026  
**日期**: 2026-05-11  
**分析周期**: 2026-05-04 ~ 2026-05-10（7天）  
**数据来源**: CloudWatch → `luckyus_db_collection.t_dba_collect_redis_cluster_metrics`（5分钟采样）

---

## 1. 背景

今天在排查 Redis 实例 `luckyus-isales-commodity` 的流量报警时，偶然发现该节点存在入站网络带宽限流（`NetworkBandwidthInAllowanceExceeded`）的情况。随后将排查范围扩大至全部 154 个 ElastiCache Redis 节点，采集了近 7 天（5/4 ~ 5/10）的入站限流（`NetworkBandwidthInAllowanceExceeded`）和出站限流（`NetworkBandwidthOutAllowanceExceeded`）指标，汇总统计如下。

## 2. 发现

### 关于网络带宽限流

ElastiCache 每种节点类型都有一个**网络带宽上限**。以当前使用的 `cache.t4g.micro` 为例，AWS 标称网络性能为"Up to 5 Gbps"，但这是**突发（burst）上限**，不是持续可用的带宽：

- **基线带宽（Baseline）**：节点可以**持续、稳定**使用的网络吞吐量。t4g.micro 的基线带宽远低于 5 Gbps，实际仅约数百 Mbps 级别。
- **突发带宽（Burst）**：节点积累了网络信用（credit）后，可以短时间冲到标称的 5 Gbps，但信用耗尽后会**回落到基线**。
- **限流（Throttling）**：当实际流量超过当前可用带宽（信用耗尽后即基线带宽），超出部分的数据包会被**丢弃或排队**，CloudWatch 将其记录为 `NetworkBandwidthIn/OutAllowanceExceeded`。

简单说：AWS 宣传的"Up to 5 Gbps"只是峰值能力，日常能用多少取决于基线。对于 t4g 系列的 burstable 节点，如果业务流量持续超过基线，就会出现常态性限流。

---

154 个节点中，**7 个节点**在过去一周出现过限流，其中 3 个需要关注：

### 2.1 luckyus-isales-commodity（P1 — 需升级）

| 日期 | 限流时长 | 5min均值 | 峰值(packets) |
|------|:-------:|:-------:|:------------:|
| 5/9  | 6.1h | 2.74 | 175 |
| 5/7  | 5.2h | 1.92 | 120 |
| 5/5  | 5.2h | 2.55 | 101 |
| 5/6  | 5.2h | 2.26 | 82 |
| 5/4  | 4.9h | 1.83 | 106 |
| 5/8  | 4.9h | 1.76 | 94 |
| 5/10 | 4.7h | 1.91 | 121 |

- **方向**: 入站为主
- **当前节点**: `cache.t4g.micro`（0.5 GiB，突发网络，基线带宽极低）
- **架构**: 1 shard，1 主 + 1 副本，非 Cluster Mode
- **结论**: 每天约 5~6 小时持续限流，属于**常态性瓶颈**，不是偶发

### 2.2 luckyus-web（P2 — 观察）

- **方向**: 出站为主
- **最严重**: 5/7 限流 1.8h，峰值 57 packets
- 其余天数限流时长 < 30min，暂可观察

### 2.3 luckyus-ldas（P3 — 偶发）

- **方向**: 双向
- 仅 5/8 出现一个 5 分钟窗口的突发限流，峰值 187 packets
- 属偶发突发，暂不需要处理

## 3. 升级建议

### luckyus-isales-commodity — 建议升级

| 方案 | 节点类型 | 内存 | 网络带宽 | 月费/节点(EDP 69折) |
|------|---------|------|---------|:------------------:|
| 当前 | cache.t4g.micro | 0.5 GiB | 突发/基线极低 | ~$4 |
| 经济型 | cache.t4g.medium | 1.59 GiB | 突发/基线提高 | ~$17 |
| **推荐** | **cache.m6g.large** | **6.38 GiB** | **稳定 10 Gbps** | **~$56** |
| 充裕型 | cache.r6g.large | 13.07 GiB | 稳定 10 Gbps | ~$73 |

**推荐 m6g.large**：彻底脱离 burstable 网络模型，获得稳定 10 Gbps 基线带宽，从根本上消除限流。2 节点（主+副本）月增约 $104。

### luckyus-web — 暂不升级，持续监控

限流频次和时长较低，建议积累 2~4 周数据后再评估。若出站限流趋势上升，参照 isales-commodity 方案升级。

## 4. 后续行动

| 项目 | 负责人 | 目标时间 |
|------|-------|---------|
| isales-commodity 升级变更窗口申请 | DBA | 本周 |
| 持续采集限流数据（已上线） | DBA | 持续 |
| 2~4 周后复查 web-001 / ldas-001 趋势 | DBA | 6月初 |
