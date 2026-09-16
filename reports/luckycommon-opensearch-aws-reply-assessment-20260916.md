# luckycommon OpenSearch —— AWS Support 二次回复评估与追问

| | |
|---|---|
| **报告日期** | 2026-09-16 |
| **对象域** | `luckycommon`（us-east-1，Elasticsearch 6.8，VPC，FGAC） |
| **新增数据窗口** | 2026-09-15 12:00 ~ 2026-09-16 16:00 UTC（承接 09-15 核验报告） |
| **前置文档** | `reports/luckycommon-opensearch-node-drop-verification-20260915.md` |
| **编写** | 曾翔宇（DBA / Infrastructure） |

---

## 结论摘要

1. **AWS 第 1 点属实，但等于撤回自己的根因。** `MasterCPUCreditBalance` 确为 T2 专有指标（AWS 官方文档原文：*"available only for T2 instance types"*），t3.small 不发布。AWS 因此**无法为「突增额度耗尽」提供任何观测证据** —— 该判定系由实例类型推断得出，应正式从案卷中撤回，而不是留着当结论。
2. **AWS 第 2 点是实质性答复，且推翻了 AWS 自己的第 1 点。** 节点日志显示 12:46:53,533 出站传输通道 `ClosedChannelException` → ping 失败 → `master_left`，进程未崩溃、无 OOM、无 GC 停顿。这与我方 09-15 报告「证据 1」（节点存活、指标全程不中断）完全一致，并证明该次掉线与主节点 CPU 无关。
3. **但第 2 点给出的是机制，不是根因。** `ClosedChannelException` 只说明 socket 被关闭，没有说明**是什么关闭了它**。AWS 自述「该节点自身网络路径/实例层出现问题」—— 这正是 AWS 托管范围。真正的答案仍在未交付的第 3 点里。
4. **🔴 故障仍在继续，且已升级。** 09-15 报告收口后的 28 小时内又发生 **3 次**掉线（累计 10 天 13 次），其中一次**专用主节点被彻底替换**，另一次持续 100 分钟以 2/3 主节点运行。三次集群全程 GREEN，**再次零告警**。
5. **🔴 最硬的新证据：15 天内 3 节点主节点池出现了 8 个不同的 NodeId，即至少 5 次主节点替换，平均约 3 天一次。** ES 节点重启会保留 NodeId（持久化在 data path），NodeId 变更意味着节点被换掉。这是 AWS 侧基础设施在反复替换主机，与我方负载无关。
6. **该事实同时独立证伪额度归因**：按实测负载，从满额跑到 0 需要连续 15.4 天高于基准线；而主节点平均 3 天就被换掉一次，额度根本不可能累积到耗尽。

---

## 第一部分：对 AWS 三点答复的逐条评估

### 1.1 第 1 点（信用额度数据）—— 属实，但结论应随之撤回

已核验 AWS 说法成立：

- AWS 官方文档 *Monitoring OpenSearch cluster metrics with Amazon CloudWatch* → `MasterCPUCreditBalance` 条目原文标注 **"available only for T2 instance types"**。
- 本账户 `AWS/ES` 命名空间实际发布 **177 个**指标名，其中含 `redit` 的：**0 个**。与 09-15 报告 §1.1 一致。

**因此：AWS 承认无法提供任何支持其根因的数据。** 一个无法用观测数据支持、且被 AWS 自己第 2 点答复推翻的判定，不应继续作为本 case 的结论留存。

#### 对我方口径的一处精确化（主动披露，避免被反驳）

09-15 报告称主节点 CPU「从未持续超过 20% 基准线」。按最新数据，这一表述需要收紧：

被选举主节点（elected master）确实会**持续略高于基准线**。`fveZ-PKLTSus14WVO7eMLQ` 自 2026-09-13 20:00 起接任 elected master 后，连续 **52 小时**运行在 20.13–23.10%（均值 **21.29%**），直至 09-15 23:20 消失。

| 项 | 数值 |
|---|---|
| 连续高于基准线时长 | 52 h |
| 均值 CPU | 21.29% |
| 净消耗速率 | **-1.54 credit/h** |
| 52 小时后模拟余额底 | **495.7 / 576（86%）** |
| 从满额跑到 0 所需时长 | **369 h ＝ 15.4 天连续运行** |

结论不变：**存在缓慢净消耗，但距离耗尽差一个数量级**，且主节点平均 3 天即被替换（见 §2.2），不可能累积 15.4 天。

> 非 elected master 的两个节点全程 6–10%，持续净积累。elected master ≈21%、follower ≈6–10% 是本域稳定的身份特征，可用于反查哪个节点在何时当选。

### 1.2 第 2 点（数据节点掉线日志）—— 接受，并与我方证据互证

AWS 提供的节点日志与我方 CloudWatch 观测逐项吻合：

| AWS 日志结论 | 我方 09-15 报告对应证据 | 是否一致 |
|---|---|---|
| 进程未崩溃、无 OOM | 该节点指标 79/79 分钟持续上报 | ✅ |
| 无 GC 停顿 | `JVMMemoryPressure` 43–46% 平稳 | ✅ |
| 掉线前一秒仍在正常写入 | `WriteThroughput` ~2.1 MB/s，`5xx`=0 | ✅ |
| 传输层断连（`ClosedChannelException`） | 我方判定为「被踢出集群但宿主存活」 | ✅ |
| 与主节点 CPU 无关 | 当时三主节点 4%/13%/7%、指标无中断 | ✅ |

**补充观察（可作追问材料）**：日志显示 `master_left` 发生在 12:46:54,384，距 12:46:53,533 的 `ClosedChannelException` 仅 **0.85 秒**，而 ping 配置为 `tried [3] times, each with maximum [30s] timeout`。三次 ping 在不到 1 秒内全部失败，说明**不是超时（链路慢），而是连接已被关闭后立即失败（链路断）**。这进一步排除「节点响应慢/算力不足」，指向链路被外部切断。

**但这是机制，不是根因。** 需要 AWS 回答的是：**12:46:53 是什么关闭了该节点的出站传输通道。**

### 1.3 第 3 点（宿主机/底层事件记录）—— 未交付，且已成为唯一关键项

AWS 称「正在与内部团队沟通」。鉴于 §2 的新증据（15 天 5 次主节点替换），此项已从「补充材料」升级为**本 case 的核心诉求**。

---

## 第二部分：09-15 报告收口后的新增证据

### 2.1 又发生 3 次掉线，全部零告警（承接附录 B，事件 11–13）

| # | 起始 (UTC) | 结束 | 时长 | 最低 Nodes | `MasterReachableFromNode`=0 区间 | 掉线对象与形态 | 是否告警 |
|---|---|---|---|---|---|---|---|
| 11 | 09-15 20:45 | 21:35 | **50 min** | 6 | 20:45–21:20、21:25–21:35 | 主 `uHd_i`：**先被踢出集群但宿主存活**（20:45 起 Nodes=6，全部 7 节点指标均无中断），21:15–21:30 才出现硬性指标中断（重启），21:35 归队；20:45 与 06:30 分别有 61.3% / 57.3% 尖峰 | **否** |
| 12 | 09-15 23:25 | 09-16 01:05 | **100 min** | 6 | 23:25–23:30 | 主 `fveZ`（**当时的 elected master**）指标 23:20 终止后**再未返回**，01:00 由新 NodeId `iwVBdpKTSn6RTn9W_8LG1w` 接替 —— **AWS 侧节点替换** | **否** |
| 13 | 09-16 06:15 | 06:35 | 20 min | 6 | 06:15–06:20、06:25–06:35 | 主 `uHd_i`：指标中断 06:10–06:30 → 返回（57.3% 尖峰） | **否** |

**累计：2026-09-07 ~ 09-16 共 13 次节点掉线，仅 1 次告警（09-14 的集群 RED）。**

### 2.2 🔴 15 天内 8 个主节点身份 ＝ 至少 5 次替换

`aws cloudwatch list-metrics --namespace AWS/ES --metric-name MasterCPUUtilization` 对本域返回 **8 个不同 NodeId**，而本域专用主节点只有 **3 个槽位**。逐个拉取 `MasterCPUUtilization` 确定各身份的存活区间（2026-09-02 00:00 ~ 09-16 16:00 UTC，小时粒度）：

| NodeId | 首个数据点 | 末个数据点 | 状态 |
|---|---|---|---|
| `HSC3q7p5SwO7LRIvWg2SQw` | ≤09-02 00:00 | 09-02 14:00 | 已消失 |
| `Uu1J7H2ZSr6nMA1Zo0p0XQ` | 09-02 15:00 | 09-05 02:00 | 已消失 |
| `crM3FA6WQna-TcbPyg-ZRg` | ≤09-02 00:00 | 09-05 09:00 | 已消失 |
| `NGfx2-02SgWO3ekOUHAy0w` | 09-05 03:00 | 09-09 11:00 | 已消失（09-15 报告已记录） |
| `fveZ-PKLTSus14WVO7eMLQ` | ≤09-02 00:00 | **09-15 23:00** | **本次消失** |
| `zip4p__KRSua3vTT-LK37A` | （09-05 前后接任） | 09-16 15:00 | 在运行 |
| `uHd_i_NhTuOnijaIMvTCwA` | 09-09 12:39 | 09-16 15:00 | 在运行 |
| `iwVBdpKTSn6RTn9W_8LG1w` | **09-16 01:00** | 09-16 15:00 | **新接任** |

**判据**：Elasticsearch 节点 ID 持久化在节点 data path，**进程重启会保留同一 NodeId**；NodeId 变更只可能来自节点被重建/替换。3 个槽位出现 8 个身份 ⇒ **至少 5 次替换 / 15 天 ⇒ 平均约 3 天一次**。

**这一条同时完成两件事**：

- 正面证据：主节点主机在被 AWS 反复替换，属托管层行为，与我方负载无关；
- 反面证伪：任何「额度长期累积耗尽」的解释都不成立 —— 节点活不到 15.4 天。

### 2.3 事件 11 是一份理想标本，建议指定其要日志

事件 11 在同一次故障中**同时呈现了两种形态**：

- 20:45–21:15：Nodes 掉到 6，但**全部 4 个数据节点 + 全部 3 个主节点的 CloudWatch 指标均无一分钟中断** —— 与 09-14 数据节点 `5a-S3` 的「被踢出集群、宿主存活」完全同构，即 AWS 第 2 点所述的传输层断连；
- 21:15–21:30：指标硬性中断 15 分钟 —— 宿主/进程重启；
- 21:35：归队，Nodes 回到 7。

即：**先网络隔离，后主机重启**。AWS 已能为 09-14 的数据节点提供完整节点日志，应同样可为本次提供，且本次是主节点，更贴近待查的第 3 点。

### 2.4 告警盲区未变（且这三次连 RED 判据都碰不到）

事件 11–13 期间实测：`ClusterStatus.red` 全程 0、`ClusterStatus.yellow` 全程 0、`Shards.unassigned` 全程 0、`ClusterIndexWritesBlocked` 全程 0。

Zeus 现有 4 条 ES 判据（磁盘 / CPU / 黄 / 红）在这三次中**没有任何一条可能成立**。09-15 报告 §2.3 的结论不变：卡点在采集侧 —— `Nodes`、`MasterReachableFromNode` 未采集，**新增策略在技术上无法实现**。

> 本次三起事件中 `MasterReachableFromNode` 共出现 **6 段** 0 值。该指标是唯一能在集群保持 GREEN 时暴露此类故障的判据，而它恰好没被采集。

---

## 第三部分：给 AWS Support 的回复（可直接发送）

> 见 `reports/aws-support-reply-luckycommon-20260916.md`

---

## 第四部分：整改优先级（相对 09-15 报告的变化）

| 项 | 09-15 定级 | 09-16 定级 | 变化理由 |
|---|---|---|---|
| **P0 补副本 + 修 index template** | P0 | **P0（更硬）** | AWS 已确认掉线为传输层/实例层故障，属我方不可预防。**副本是唯一可控防线**，且掉线频率已升至 10 天 13 次。距 5/18 runbook 提出已 4 个月未执行 |
| **P1 补采集（`Nodes`/`MasterReachableFromNode` 等 6 项）** | P1 | **P1（更硬）** | 新增 3 次掉线再次零告警；`MasterReachableFromNode` 本窗口出现 6 段 0 值，是唯一有效判据 |
| **P1 开启日志投递** | P1 | P1 | AWS 能读到节点日志而我方读不到，每次取证都要开 case、隔日才有结果 |
| **P2 主节点升配** | P2 | P2（不变） | 变更原因仍应写 **JVM 堆余量不足（2 GiB）+ 消除 burstable 不确定性**；**不得写「突增额度耗尽」**。注意：升配**不能**解决传输层掉线，不要在变更单里承诺该收益 |
| **P3 向 AWS 追问底层事件** | P3 | **P1** | 已是唯一未交付项，且 §2.2 提供了新的硬证据支撑 |

**权限卡点（未变）**：`databasecheck` 无 `es:UpdateDomainConfig`（升配/dry run 均不可执行）、无 `health:DescribeEvents`（底层主机事件不可查）、未做 FGAC role mapping（REST API 403）。P0/P2 须 Michael 或提权角色操作。

---

## 附录：方法与数据来源

| 项 | 说明 |
|---|---|
| 指标来源 | CloudWatch `AWS/ES`，`get_metric_data`，5 分钟粒度（节点身份区间用 1 小时粒度），2026-09-02 00:00 ~ 09-16 16:00 UTC |
| 节点身份枚举 | `aws cloudwatch list-metrics --namespace AWS/ES --metric-name MasterCPUUtilization --dimensions Name=DomainName,Value=luckycommon`（同法对 `CPUUtilization` 得 4 个数据节点，与事故前一致，无替换） |
| 指标名全量核查 | 同上 `list-metrics` 全量，177 个指标名，`redit` 匹配 0 个 |
| `MasterCPUCreditBalance` 口径 | AWS 官方文档 *Monitoring OpenSearch cluster metrics with Amazon CloudWatch*，原文 "available only for T2 instance types" |
| 信用额度模型 | t3.small：2 vCPU、基准 20%、24 credit/h、上限 576；每小时消耗 `CPU% × 2 × 60 / 100`；起点满额、标准模式（最坏假设） |
| 未能获取 | `aws health describe-events`（无 `health:DescribeEvents` 权限）；ES 应用日志（`LogPublishingOptions` 为 null） |
