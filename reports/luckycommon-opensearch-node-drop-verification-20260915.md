# luckycommon OpenSearch 节点掉线 —— AWS 归因核验与告警对账

| | |
|---|---|
| **报告日期** | 2026-09-15 |
| **对象域** | `luckycommon`（us-east-1，Elasticsearch 6.8，VPC，FGAC） |
| **拓扑** | 4× `m5.large.search` 数据节点 + 3× `t3.small.search` 专用主节点，2 AZ，gp3 150GiB/节点 |
| **数据窗口** | 2026-09-07 00:00 ~ 2026-09-15 12:00 UTC（8 天，CloudWatch 1 分钟粒度） |
| **起因** | AWS Support 就 09-14 12:47–14:06 UTC 掉线事件给出根因判定：t3.small 专用主节点突增算力额度不足 |
| **编写** | 曾翔宇（DBA / Infrastructure） |

---

## 结论摘要

1. **AWS 的根因判定不成立。** 「t3.small 突增额度耗尽导致掉线」在本域没有任何观测证据支持：OpenSearch 不发布 CPU 信用额度指标，AWS 也未引用任何余额数据；按实测 CPU 反推，8 天内额度从未掉出满额的 90%。
2. **AWS 引用的证据存在因果倒置。** 全周所有 ≥70% 的主节点 CPU 样本，无一例外出现在掉线**之后** 4–79 分钟，是节点重新入群后的主选举与分片恢复开销。
3. **AWS 对 09-14 事件的描述与指标不符。** 触发 RED 的是**数据节点**掉线，当时三个主节点 CPU 为 4%/13%/7% 且指标无中断；主节点指标中断发生在 51 分钟之后。
4. **真实形态是节点整体消失后重启，不是算力受限。** 7 次主节点事件均为指标完整中断 6–42 分钟后带高 CPU 尖峰返回；同一次事故中被踢出集群但宿主存活的数据节点则全程持续上报 —— 两种形态在同一份数据里形成对照。
5. **这 8 天里 10 次节点掉线，我方只收到 1 次告警（09-14 的集群 RED）。** 其余 7 次主节点掉线在 Zeus 与本地分析平台均为零记录。根因是 ES 告警仅有「集群颜色/磁盘/CPU」4 条判据，而掉 1 个主节点时集群全程 GREEN；更底层的卡点是采集侧只有 4 个 `aws_es_*` 指标，节点数与可达性**根本没采**。
6. **主节点升配这件事仍应做，但理由不同：** 不是算力超基准，而是 2 GiB 内存导致 JVM 堆余量不足（全周 p99 73–74%、峰值 77%）。而**真正导致 RED 的是副本缺失**，不是掉线本身。

---

## 第一部分：AWS 归因核验

### 1.1 「突增额度耗尽」没有观测证据

整个 AWS 账户 `AWS/ES` 命名空间下**不存在 `CPUCreditBalance` / `CPUCreditUsage` 指标** —— OpenSearch 托管域不向客户发布 CPU 信用额度。AWS 回信中同样未引用任何余额数据，该结论系由实例类型推断得出。

用实测 CPU 均值反推额度消耗（t3.small：2 vCPU，基准利用率 20%，每小时赚 24 credit，上限 576；按**标准模式最坏假设**、起点满额模拟）：

| 主节点 | 8 天均 CPU | 最大 1h 均值 | 最大 24h 均值 | 连续 >20% 最长 | 模拟最低余额 |
|---|---|---|---|---|---|
| `NGfx2-02SgWO3ekOUHAy0w` | 6.9% | 10.5% | 7.4% | 1 min | 575.6 / 576 |
| `zip4p__KRSua3vTT-LK37A` | 11.6% | 21.0% | 20.1% | 11 min | 572.5 / 576 |
| `fveZ-PKLTSus14WVO7eMLQ` | 11.4% | 22.3% | 21.4% | 5 min | **518.6 / 576（90%）** |
| `uHd_i_NhTuOnijaIMvTCwA` | 9.6% | 16.8% | 10.6% | 11 min | 571.5 / 576 |

信用额度仅在 CPU 持续高于 20% 基准线时才净消耗。实测负载连长期贴近基准线都未做到，**8 天内额度从未掉出满额的 90%**。

### 1.2 掉线前 CPU 是个位数，高 CPU 全部出现在掉线之后

各次掉线节点消失前最后 12 分钟的 CPU 均在 3–24% 区间（多数 4–14%），JVM 内存压力 39–73%，无爬坡、无节流平台期。

全周 ≥70% 的主节点 CPU 样本共 11 个，**全部位于掉线开始之后**：

| 节点 | 时刻 (UTC) | CPU | 相对掉线起点 |
|---|---|---|---|
| `zip4p` | 09-14 14:05 | 95% | +78 min |
| `zip4p` | 09-14 14:06 | 92% | +79 min |
| `uHd_i` | 09-11 10:36–10:38 | 89/93/85% | +17 ~ +19 min |
| `uHd_i` | 09-12 20:36–20:38 | 89/99/81% | +17 ~ +19 min |
| `uHd_i` | 09-14 00:24–00:26 | 86/80/81% | +4 ~ +6 min |

这些尖峰是节点重新加入集群后执行主选举、集群状态同步与分片恢复的开销，属于**结果**而非原因。AWS 将其作为「主节点承压不稳定」的证据，存在因果倒置。

### 1.3 09-14 事件的描述与指标不符

AWS 称「每次掉线都对应 MasterCPUUtilization 数据中断」。但触发 RED 的 09-14 12:46–12:47 那次：

- 掉线的是**数据节点** `5a-S3WqQSLuABRVeJ-MGBw`；
- 当时三个主节点全部正常上报，CPU 分别为 **4% / 13% / 7%**，一分钟都未中断；
- 主节点 `zip4p` 的指标中断发生在 **13:38**，比故障晚 51 分钟，属次生事件。

以主节点 CPU 解释一次数据节点掉线，逻辑不成立。

### 1.4 指标中断形态说明节点是「消失」而非「被压制」

同一次事故内部提供了理想对照组：

| | 数据节点 `5a-S3`（被踢出集群，宿主存活） | 7 次主节点事件 |
|---|---|---|
| 指标上报 | **持续 79/79 分钟不中断** | **完全消失 6–42 分钟** |
| CPU 表现 | 由 16% 塌至 6%（空转） | 消失，返回时 83–99% 尖峰 |

受信用额度节流的实例不会停止上报指标，而会持续上报并将 CPU 钉在基准线附近。**指标整段消失 + 返回时高 CPU 尖峰 = 节点进程/宿主重启**。

此外，主节点 `NGfx2` 于 09-09 11:52 消失后未再返回，12:39 由新 NodeId `uHd_i` 接替 —— 这是一次 **AWS 侧的节点替换**。

### 1.5 三个主节点轮流掉线，非单台硬件问题

`fveZ` 3 次、`uHd_i` 3 次、`zip4p` 1 次、`NGfx2` 1 次后被替换。

### 1.6 其他因素排查（均已排除）

| 因素 | 实测 | 结论 |
|---|---|---|
| 交换分区 `HighSwapUsage` | 8 天仅 2 个孤立分钟（09-08 21:25、09-09 13:38），均不在掉线之前 | 排除 |
| EBS 吞吐节流 `ThroughputThrottle` | 仅 09-15 00:40 一分钟，在全部事件之后 | 排除 |
| EBS IOPS 节流 / 卷卡顿 | `IopsThrottle`、`VolumeStalledIOCheck` 全周恒为 0 | 排除 |
| 主节点 JVM 内存 | p99 73–74%，峰值 77.4%，OldGen 峰值 63.9%，掉线前无尖峰 | 非直接触发因素，但余量偏薄（见 3.1） |

---

## 第二部分：告警对账 —— 10 次掉线，1 次告警

### 2.1 实际收到的告警

查询 Zeus `luckyus_izeus.t_alert`（全景视角）与本地分析平台 `luckyus_db_collection.t_dba_alert_reports`（重点关注），窗口内 `luckycommon` 的 ES 告警共 **6 条，全部集中在 09-14 一次事件**：

| 时间 (UTC) | 告警名 | 级别 | 持续 |
|---|---|---|---|
| 09-14 12:53 | 【DB告警】AWS-ES 集群状态Red | P2 ×2 | 40 min |
| 09-14 12:53 | 【DB告警】AWS-ES 集群状态Red_语音 | P0 ×2 | 40 min |
| 09-14 13:30 | 【DB告警】AWS-ES 集群状态Yellow | P2 ×2 | 51 min |

**其余 7 次主节点掉线（09-09 11:57、09-10 00:14、09-11 10:19、09-11 12:54、09-12 20:19、09-13 19:54、09-14 00:20）在两个库中均无任何记录。**

### 2.2 第一层原因：判据与事件不在同一维度

Zeus 现有 ES 策略共 4 条判据（id 56/58/59/60，另 127/128/129 为 `_语音` 复制）：

```promql
[56/129] aws_es_free_storage_space_average      offset 3m <= 10000   # 磁盘
[58/128] aws_es_cpuutilization_average          offset 3m >= 90      # CPU
[59]     aws_es_cluster_status_yellow_maximum   offset 5m != 0       # 黄
[60/127] aws_es_cluster_status_red_maximum      offset 3m != 0       # 红
```

全部只观察「集群颜色 + 磁盘 + CPU」。3 个专用主节点掉 1 个时仲裁仍然成立（2/3），分片不发生重分配 —— 逐事件核验确认，**那 7 次期间 `ClusterStatus.yellow` 与 `.red` 全程为 0，集群一直是 GREEN**：

| 事件窗口 (UTC) | 掉线节点 | 最低 Nodes | 期间 yellow | 期间 red |
|---|---|---|---|---|
| 09-09 11:57 → 12:35 | 主 `NGfx2` | 6 | 0 | 0 |
| 09-10 00:14 → 00:56 | 主 `fveZ` | 6 | 0 | 0 |
| 09-11 10:19 → 10:38 | 主 `uHd_i` | 6 | 0 | 0 |
| 09-11 12:54 → 13:29 | 主 `fveZ` | 6 | 0 | 0 |
| 09-12 20:19 → 20:37 | 主 `uHd_i` | 6 | 0 | 0 |
| 09-13 19:54 → 20:30 | 主 `fveZ` | 6 | 0 | 0 |
| 09-14 00:20 → 00:26 | 主 `uHd_i` | 6 | 0 | 0 |
| 09-14 12:47 → 14:07 | 数据 `5a-S3` + 主 `zip4p` | 5 | 1 | 1 |

策略在设计上就不可能覆盖主节点掉线。

### 2.3 第二层原因（更硬的卡点）：指标根本没采

dbtools01:9106 的 cloudwatch-exporter 推送到 VictoriaMetrics（datasource uid `ZBv6_UeHz`）的 ES 指标**只有 4 个**，即上述判据所用的那 4 个。

**未采集**：`Nodes`、`MasterReachableFromNode`、`MasterCPUUtilization`、`MasterJVMMemoryPressure`、`JVMMemoryPressure`、`ClusterIndexWritesBlocked`。

→ **当前即便想新增告警策略也无法实现，必须先改采集配置。**

附带说明：AWS 回信建议「升级完成后请持续观察 Nodes、MasterReachableFromNode 与 MasterCPUUtilization」—— 这三项我方目前一项都未采集。

### 2.4 CloudWatch 侧无兜底

账户内 36 条 CloudWatch 告警中，ES 相关仅 1 条「AWS ES 磁盘空间不足」：

- 判据 `MAX(FreeStorageSpace) GROUP BY DomainName <= 1000`，取的是每个域中**最空闲的节点**，与分片按节点分配、水位线按节点生效的机制不符，会绕开单节点写满的情况；
- 状态自 2025-10-20 起未发生变化。

### 2.5 MTTD 基线

即便 09-14 的真实 RED，告警也在 12:53 才触发 —— 比 RED 起点（12:47）晚 6 分钟，比数据节点掉线（12:46）晚 7 分钟。规则自带 `offset 3m`，叠加采集与评估延迟。

---

## 第三部分：整改优先级

> 与 AWS 建议的排序相反：升配不是第一优先级。节点掉线在本域已是常态（8 天 10 次），**没有副本兜底才是 RED 的直接原因**。

### P0 — 补副本 + 修 index template

09-14 事故前实测 `Shards.active=112` / `activePrimary=63` → 14 个主分片（22%）零副本。掉线时 27 个分片 unassigned、RED 持续 35 分钟。5/18 runbook 的 P0-A（补副本）/ P0-B（修 index template 防新日索引以 0 副本落地）截至今日仍未执行，这已是第 4 次 RED。

**责任人**：DBA + Michael（需 FGAC role mapping 或 Kibana Dev Tools 权限）

### P1 — 补采集，关闭告警盲区

1. 修改 dbtools01:9106 cloudwatch-exporter 配置，新增：`Nodes`、`MasterReachableFromNode`、`ClusterIndexWritesBlocked`、`JVMMemoryPressure`、`MasterCPUUtilization`、`MasterJVMMemoryPressure`。**不需要 AWS 权限。** 注意：指标名中的 `%` 会被转义为双下划线；端口写在 ENTRYPOINT 中。
2. Zeus 新增策略（基础设施类用空 label selector 全量匹配，新域自动覆盖）：

| 判据 | 建议级别 | 理由 |
|---|---|---|
| `aws_es_cluster_index_writes_blocked_maximum != 0` | **P0** | 直接对应业务写入不可用 |
| `aws_es_cluster_status_red_maximum != 0` | P0（现有） | 保持 |
| `aws_es_master_reachable_from_node_minimum == 0` 持续 2m | P2 | 见下方取舍 |
| `aws_es_nodes_minimum` 低于近 1h 基线 | P2 | 见下方取舍 |

**级别取舍（需拍板）**：节点数/可达性类告警按本周频率为**每周约 7 次**，且每次集群均为 GREEN、业务无感（触发时刻分布于纽约时间 06:19–20:20）。若配为 P0 将产生大量无业务影响的响铃。建议按分级告警架构思路，节点数类走 P2 做趋势观察，`ClusterIndexWritesBlocked` 与 RED 保留 P0/语音通道，使「有业务影响」与「有异常」分属两档。

### P1 — 开启日志投递

`luckycommon` / `luckylfe-log` / `luckyur-log` 三个域 `LogPublishingOptions` 全部为 null，应用日志、慢日志、审计日志全关，已导致连续 4 次 RED 事后零取证能力（连索引由谁删除都无法回答）。

### P2 — 主节点升配

由 `t3.small.search` 升至 `m5.large.search` / `m6g.large.search`。

**变更原因应写**：专用主节点 2 GiB 内存导致 JVM 堆余量不足（全周 JVM 压力 p99 73–74%、峰值 77.4%，长期贴近 GC 触发线），且消除 burstable 实例带来的不确定变量。

**不应写**：算力超出基准 / 突增额度耗尽 —— 本报告第一部分已证伪。

域配置 3 个专用主节点，变更主节点实例类型通常不触发蓝绿部署，但仍建议先执行 dry run 确认。**注意：`databasecheck` 无 `es:UpdateDomainConfig` 权限，连 dry run 都无法执行，须由 Michael 或提权角色操作。**

### P3 — 向 AWS 追问底层原因

见第四部分。

---

## 第四部分：给 AWS Support 的回复要点

1. 请提供 `luckycommon` 专用主节点的 **CPU 信用额度余额数据**以支持「突增额度耗尽」的判断；若该指标不对客户发布，请说明该结论的观测依据。我方实测 8 天主节点 CPU 均值 6.9–11.6%，最大 24h 滚动均值 21.4%，从未持续超过 20% 基准线。

2. 09-14 12:46 触发 RED 的是**数据节点** `5a-S3WqQSLuABRVeJ-MGBw`；当时三个专用主节点 CPU 分别为 4% / 13% / 7%，指标无任何中断，主节点指标中断出现在 51 分钟后的 13:38。请说明主节点 CPU 如何解释这次数据节点掉线。

3. 全周 11 个 ≥70% 的主节点 CPU 样本全部出现在掉线开始之后 4–79 分钟。我方判断其为节点重新入群后的主选举与分片恢复开销。请确认这一判断，或提供相反证据。

4. 7 次主节点事件中，节点指标**完整消失 6–42 分钟后重启返回**；09-09 11:52 主节点 `NGfx2-02SgWO3ekOUHAy0w` 消失后由 `uHd_i_NhTuOnijaIMvTCwA` 接替。请提供这些时间窗内的**宿主机/底层事件记录**（是否存在 AWS 侧主机降级、替换或网络隔离）。

5. 本域服务软件版本停留在 `Elasticsearch_6_8_R20250625`，`R20260720` 已可更新。请确认该版本是否包含与节点稳定性/节点失联相关的修复。

6. 我方已确认 `Nodes`、`MasterReachableFromNode`、`MasterCPUUtilization` 三项指标此前未纳入监控采集，故过去一周的多次掉线在发生当时我方完全无感知，系事后翻查 CloudWatch 才发现。这进一步说明需要 AWS 提供底层事件记录以定位真实原因。

---

## 附录 A：方法与数据来源

| 项 | 说明 |
|---|---|
| 指标来源 | CloudWatch `AWS/ES`，`get_metric_data`，1 分钟粒度（内存类 5 分钟），2026-09-07 00:00 ~ 09-15 12:00 UTC |
| 域配置 | `aws opensearch describe-domain --domain-name luckycommon` |
| 告警来源 | Zeus `luckyus_izeus.t_alert` / `t_alert_strategy` / `t_alert_strategy_rule`（`aws-luckyus-devops-rw`，pymysql 直连）；本地平台 `luckyus_db_collection.t_dba_alert_reports`（`aws-luckyus-ldas01-rw`） |
| 采集面核查 | Grafana datasource `victoriametrics-basic-us`（uid `ZBv6_UeHz`）metric names 正则 `aws_es_.*` |
| 信用额度模型 | t3.small：2 vCPU、基准 20%、24 credit/h、上限 576；每分钟赚 0.4 credit、花 `CPU% × 2` credit；起点满额，标准模式（最坏假设） |
| 未能获取 | `aws health describe-events` —— `databasecheck` 无 `health:DescribeEvents` 权限，底层主机事件只能向 AWS 索取 |

## 附录 B：完整事件清单（8 天 10 次）

| # | 起始 (UTC) | 结束 | 时长 | 最低 Nodes | 掉线对象 | 形态 | 是否告警 |
|---|---|---|---|---|---|---|---|
| 1 | 09-09 11:57 | 12:35 | 39 min | 6 | 主 `NGfx2` | 指标中断后未返回，由 `uHd_i` 替换 | 否 |
| 2 | 09-10 00:14 | 00:56 | 43 min | 6 | 主 `fveZ` | 指标中断 → 返回 | 否 |
| 3 | 09-11 10:19 | 10:38 | 20 min | 6 | 主 `uHd_i` | 指标中断 → 返回（89–93% 尖峰） | 否 |
| 4 | 09-11 12:54 | 13:29 | 36 min | 6 | 主 `fveZ` | 指标中断 → 返回 | 否 |
| 5 | 09-11 13:31 | 13:36 | 6 min | 6 | 主（复掉） | 短暂 | 否 |
| 6 | 09-12 20:19 | 20:37 | 19 min | 6 | 主 `uHd_i` | 指标中断 → 返回（99% 尖峰） | 否 |
| 7 | 09-13 19:54 | 20:30 | 37 min | 6 | 主 `fveZ` | 指标中断 → 返回 | 否 |
| 8 | 09-13 20:32 | 20:37 | 6 min | 6 | 主（复掉） | 短暂 | 否 |
| 9 | 09-14 00:20 | 00:26 | 7 min | 6 | 主 `uHd_i` | 指标中断 → 返回（86% 尖峰） | 否 |
| 10 | **09-14 12:47** | **14:07** | **81 min** | **5** | 数据 `5a-S3`（存活被踢出）+ 主 `zip4p`（13:39 中断） | RED 35 min，27 分片 unassigned | **是（12:53）** |
