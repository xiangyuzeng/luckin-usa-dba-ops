# 生产变更申请（CR）— OpenSearch `luckylfe-log` EBS 存储扩容

| 项目 | 内容 |
|------|------|
| **变更标题** | `luckylfe-log` 数据节点 EBS 卷扩容 80 GiB → **150 GiB**（单节点，共 4 节点） |
| **变更类型** | **紧急变更（Emergency Change）** |
| **执行状态** | ✅ **已执行 2026-08-20 01:00–02:00 UTC，实际扩容至 100 GiB（非申请的 150 GiB）** —— 详见下节「执行结果」 |
| **优先级** | **P0** |
| **申请人** | 曾翔宇 (David Zeng) / DBA |
| **审批人** | Michael (CTO) |
| **申请时间** | 2026-08-19 20:40 UTC（16:40 EDT） |
| **建议执行窗口** | **批准后立即执行**。变更为 EBS 在线扩容，不触发 blue/green、无停机，无需等低峰 |
| **AWS 账号 / 区域** | 257394478466 / us-east-1 |
| **关联告警** | 宙斯【DB告警】AWS-ES磁盘空间不足10G_语音（P0，旧策略 id=97 迁移），2026-08-19 14:47 EDT 触发，当前值 9963.88 MiB |

---

## 执行结果（2026-08-20 补记）

> **状态：✅ 已执行。实际扩容至 `gp2 100 GiB`/节点（集群 400 GiB），非申请的方案 B 150 GiB。**
> 批准与执行：David Zeng / 2026-08-20。同时已要求开发侧清理过期日志。

### 执行确认（2026-08-20 17:00 UTC 实测）

| 项 | 值 |
|---|---|
| `EBSOptions.VolumeSize` | **100**（gp2），`Processing` = `false` ✅ |
| 生效时点 | **2026-08-20 01:00 → 02:00 UTC**（最紧节点 8,032 → 24,034 MiB） |
| 实际增益（最紧节点） | **+16.0 GiB**（名义 +20 GiB，差额为文件系统预留开销） |
| `ClusterStatus.green` / `Shards.unassigned` | `1` / `0` ✅ |
| `ClusterIndexWritesBlocked` | `0` ✅ |
| `JVMMemoryPressure` | 71.3%（此前 74–75%，本变更不针对此项） |
| 未触发 blue/green | ✅ 与第八节评估一致，业务无中断 |

### ⚠️ 余量重算：100 GiB 恰好落在阈值公式的拐点上

AWS 写失败阈值 = min(20% × 卷容量, 20 GiB)：

| 卷容量 | 阈值 | 说明 |
|---:|---:|---|
| 80 GiB | **16 GiB** | 20% 项起作用 |
| **100 GiB** | **20 GiB** | **恰好是两项相等的拐点** |
| 120 / 150 / 200 GiB | 20 GiB | 20 GiB 上限封顶，**此后每多 1 GiB 都是净余量** |

**后果**：80 → 100 GiB 时阈值同步从 16 GiB 涨到 20 GiB，**吃掉 4 GiB**。
最紧节点实得 +16 GiB，减去阈值上涨的 4 GiB，**阈值以上净增仅 12 GiB**。

**即 100 GiB 是本区间内每 GiB 性价比最低的一档**：付了满额 20 GiB 阈值，却买到最少的阈值以上容量。
若当时取 120 GiB，多出的 20 GiB 是 1:1 的净余量（阈值不再上涨）。

### 当前余量与剩余时间

| 项 | 值 |
|---|---|
| 最紧节点可用 | **23,191 MiB ≈ 22.6 GiB** |
| 写失败阈值 | 20,480 MiB = 20 GiB |
| **阈值以上余量** | **仅 2,711 MiB ≈ 2.6 GiB** |
| 实测消耗（扩容后 15 小时） | **−56 MiB/小时 ≈ −1.32 GiB/天** |
| 历史净日趋势 | −0.95 GiB/天（08-03→08-19），近两日加速至约 −1.5 GiB/天 |
| **预计重新跌破 20 GiB 阈值** | **约 2–3 天，即 2026-08-22 ~ 08-23** |

**结论：本次扩容把最紧节点从「阈值下 9.1 GiB」拉到「阈值上 2.6 GiB」，
确实脱离了写失败风险区（当前 `ClusterIndexWritesBlocked=0`、集群 green），
但买到的是天，不是月。第七节 P1-1 的日志清理由「配套推进项」升级为唯一的关键路径。**

### 日志清理尚未生效（截至 2026-08-20 17:00 UTC）

`ClusterUsedSpace`（索引数据实际大小，不受卷容量变化影响）仍在**增长**：

| 日期 | 日均 | 日期 | 日均 |
|---|---:|---|---:|
| 08-12 | 199.0 GiB | 08-17 | 203.6 GiB |
| 08-14 | 201.2 GiB | 08-18 | 205.9 GiB |
| 08-16 | 201.8 GiB | 08-19 | 208.2 GiB |
| | | 08-20 | 208.8 GiB |

08-17 起明显加速（约 +2.2 GiB/天）。

> **口径修正（David 2026-08-20）**：**08-17 起这段加速是业务异常期，不是新基线。**
> 故上文「2–3 天」是按异常期速率外推的**下界**，业务回正后实际可用时间会更长。
> **处置决定：本次不补扩，等告警再处理。** 补扩为随时可用的后手（EBS 冷却已过）。
> ⚠️ 但该策略成立的前提是告警能提前响——见下节，现行告警不满足，需先改 per-node Minimum。
验证口径：看 `ClusterUsedSpace` 是否真的下降 —— `FreeStorageSpace` 会被卷容量变化干扰，`ClusterUsedSpace` 不会。

### ⚠️ 当前告警无法在写阻断前预警（P1-2 升级为紧急）

宙斯现行策略按**域级 Average**、阈值「不足 10 GiB」。实测 Average 与 Minimum 稳定相差约 **3 GiB**
（08-19：Avg ≈ 9,900–10,200 / Min = 7,091；08-20：Avg = 26,070 / Min = 23,191）。

即该告警触发时，最紧节点约在 **7 GiB**，已**深入写失败区内 13 GiB**。
**这条告警按当前配置在结构上就不可能提前预警。** 必须改为 per-node `Minimum`、阈值 20 GiB。

### 后续选项

- **EBS 6 小时冷却窗口已过**（02:00 UTC 完成，现 17:00 UTC），**随时可再次扩容**。
- 若清理无法在 08-22 前落地，建议直接补到 **120–150 GiB**：

  | 目标 | 集群总量 | 阈值以上余量（最紧节点） | 约可用 | 月成本(EDP) | 相对现状月增 |
  |---|---:|---:|---:|---:|---:|
  | 现状 100 GiB | 400 GB | 2.6 GiB | 2–3 天 | $37.26 | — |
  | 120 GiB | 480 GB | ~18.6 GiB | ~14 天 | $44.71 | **+$7.45** |
  | 150 GiB | 600 GB | ~42.6 GiB | ~32 天 | $55.89 | **+$18.63** |

  （按实测 −1.32 GiB/天、每档实得约名义值的 80% 估算；清理生效后可用天数将显著拉长。）

---

## 一、变更内容

将 OpenSearch 域 `luckylfe-log` 的 **4 个数据节点** EBS 卷由 `gp2 80 GiB` 扩容至 `gp2 150 GiB`
（集群总容量 320 GiB → **600 GiB**）。

**不涉及**：实例类型、节点数量、卷类型（保持 gp2）、引擎版本、网络与安全组、访问策略、加密配置，均保持不变。

> 卷类型保持 gp2 是有意选择，理由见第六节。

---

## 二、背景与现状数据

### 2.1 集群拓扑

| 项 | 值 |
|----|----|
| 域名 / 引擎 | `luckylfe-log` / Elasticsearch 7.10（VPC，FGAC 开启） |
| 数据节点 | 4 × `m5.large.search`（2 vCPU / 8 GiB RAM，堆约 4 GiB） |
| 专用主节点 | 3 × `t3.medium.search` |
| 可用区 | 2 AZ（us-east-1a / us-east-1b） |
| 存储 | **gp2 80 GiB / 节点 = 320 GiB** |
| 副本策略 | 单副本（日志集群，按既定策略不配 replica） |

### 2.2 当前磁盘水位（2026-08-19 19:00 UTC，CloudWatch `FreeStorageSpace` 分节点）

| 节点 ID | 可用 (MiB) | 已用率 |
|---------|-----------:|-------:|
| `UaNXEYuTSPWKBtiTSP5VEQ` | 13,186 | 83.9% |
| **`1QzeThCnSmqhgfEyQy219Q`** | **6,890** | **91.6%** ← 最紧节点 |
| `9I6KFYaHSIudpVpd6vztVg` | 9,327 | 88.6% |
| `giTtseDQRZuDcs7sq5cvCQ` | 10,050 | 87.7% |
| **合计** | **39,452（38.5 GiB）** | **88.0%** |

其他指标：`ClusterUsedSpace` = 216.4 GiB（索引数据）；`Shards.active` = 662；
`Shards.unassigned` = 0；`ClusterStatus.green` = 1；**`ClusterIndexWritesBlocked` = 0（写入尚未被阻断）**；
`JVMMemoryPressure` 峰值 74–75%；`IndexingRate` 1,400–3,400 docs/s。

### 2.3 已越过 AWS 文档给出的写失败阈值

AWS 官方文档（Troubleshooting → ClusterBlockException → Lack of available storage space）明确：

> "If one or more nodes in your cluster has storage space less than the minimum value of
> 1) 20% of available storage space, or 2) 20 GiB of storage space, basic write operations
> like adding documents and creating indexes **can start to fail**."

本集群单卷 80 GiB → 阈值 = min(20% × 80, 20) = **16 GiB / 节点**。

**当前 4 个数据节点全部低于 16 GiB**，最紧节点仅 6.7 GiB。
即：集群已整体处于 AWS 文档定义的写失败风险区内，只是尚未实际触发阻断。

### 2.4 消耗趋势与剩余时间

| 口径 | 区间 | 净消耗速率 |
|------|------|-----------|
| 集群总可用空间 | 2026-07-15 → 08-19（35 天，77,748 → 39,452 MiB） | **-1,094 MiB/天** |
| 集群总可用空间 | 2026-08-09 → 08-18（近 9 天） | **-1,467 MiB/天** |
| 最紧节点日最低值 | 2026-08-03 → 08-19（22,117 → 6,890 MiB） | **-952 MiB/天** |

**每日回收在跑，但跑不赢新增**：每天 01:00–02:00 UTC 可观测到一次空间回收
（例：08-17 23:02 UTC 44,163 MiB → 08-18 02:02 UTC 48,832 MiB，+4.7 GiB），
说明索引生命周期清理正常执行，**但单日回收量小于单日新增量**，因此日水位逐日下移。

**剩余时间估算（最紧节点）**：按 -952 MiB/天约 **7 天**见底；按近 8 天回归斜率
(-594 MiB/天) 约 **12 天**。取 **7–12 天**作为硬见底区间 —— 但写入失败风险在阈值内**已经存在**，
不需要等到见底。

---

## 三、不变更的后果

1. **日志写入失败**：`luckylfe-log` 为应用日志集群，写阻断后新日志直接丢失，且故障排查期间恰好没有日志可查。
2. **集群转红风险**：磁盘写满会导致分片无法分配，`ClusterStatus.red`，恢复需人工干预。
3. **告警值本身偏乐观**（见第七节 P1-2）：宙斯上报的 9,963.88 MiB 与域级 **Average** 统计一致
   （同时刻 Average ≈ 9,900–10,200 MiB，Minimum = 7,091 MiB），
   **最紧节点比告警显示的还要低约 3 GiB**。实际余量比告警面板看起来更小。

---

## 四、容量方案与选型

当前文件系统已用约 **281.5 GiB**（320 GiB 总量 − 38.5 GiB 可用）。
扩容后每节点写失败阈值变为 min(20% × 新容量, 20 GiB) = **20 GiB**。

| 方案 | 单节点 | 集群总量 | 最紧节点扩容后可用 | 阈值以上可用余量 | 可用天数 @1.5 GiB/天 | 可用天数 @1.07 GiB/天 | 月成本(EDP) | 月净增 |
|------|-------:|--------:|------------------:|----------------:|--------------------:|---------------------:|-----------:|-------:|
| 现状 | 80 GiB | 320 GiB | 6.7 GiB | **已为负** | — | — | $29.81 | — |
| A | 120 GiB | 480 GiB | 46.7 GiB | 118.5 GiB | 79 天 | 111 天 | $44.71 | +$14.90 |
| **B（推荐）** | **150 GiB** | **600 GiB** | **76.7 GiB** | **238.5 GiB** | **159 天（5.3 月）** | **223 天（7.3 月）** | **$55.89** | **+$26.08** |
| C | 200 GiB | 800 GiB | 126.7 GiB | 438.5 GiB | 292 天（9.7 月） | 410 天（13.5 月） | $74.52 | +$44.71 |

价格口径：gp2 $0.135/GB-月（us-east-1，Pricing API 实取），EDP 31% 折扣即 × 0.69。

**为什么推荐 B（150 GiB）**：
- 方案 A 只买到约 3 个月，且 EBS 修改有 6 小时冷却窗口，半年内大概率要再动一次，不划算；
- 方案 B 覆盖 5–7 个月，足以完整覆盖第七节 P1 保留策略治理的推进周期并留出缓冲；
- 方案 C 也完全安全，月增 $44.71 相对 AWS 月度总支出 $49,645 仅 0.09%。
  **如果希望一年内不再碰这个集群，直接批 C 亦无异议** —— B 与 C 的差价仅 $18.63/月。

m5.large.search 的 gp2 卷上限为 512 GiB，B、C 两方案均在限制内。

---

## 五、成本影响

| 项 | 现状 | 变更后（方案 B） |
|----|-----:|----------------:|
| 存储容量 | 320 GB | 600 GB |
| 按需月成本 | $43.20 | $81.00 |
| EDP 折后月成本 | **$29.81** | **$55.89** |
| **月度净增** | — | **+$26.08（年化 $312.96）** |

占当前 AWS 月度总支出 $49,645 的约 **0.05%**。实例、主节点费用不变。

---

## 六、为什么本次不顺便切 gp3

gp3 单价 $0.122/GB-月，低于 gp2 的 $0.135 —— 600 GB 下每月可省约 $7.80（折后 $5.38）。但：

1. **切换卷类型会触发 blue/green 部署**（AWS 文档明确将 "changing the storage type, volume type"
   列入 blue/green 操作），而**单纯增大卷容量不会**。P0 场景下应选风险最低、见效最快的路径。
2. **当前不存在 I/O 瓶颈**：近 3 天实测 ReadIOPS 峰值 28、WriteIOPS 峰值 43、写吞吐峰值 2.9 MB/s，
   远低于 gp2 80 GiB 的 240 IOPS 基线，`ThreadpoolWriteRejected` 全程为 0。
   **gp3 在这里只是成本项，不是性能项**，不构成紧急理由。

**建议**：gp2 → gp3 与当前待处理的服务软件更新（`Elasticsearch_7_10_R20260720`，同样是 blue/green）
合并为一次计划内变更，另行提申请。

---

## 七、本变更的定位：这不是根因修复

**必须说明：扩容不解决根因。** 根因是**日志保留策略与当前日志产生量不匹配** ——
每日清理确实在跑，但净增仍有 1.1–1.5 GiB/天。扩容只是把墙往后推 5–7 个月。

配套推进项（不阻塞本变更）：

| # | 级别 | 事项 |
|---|------|------|
| P1-1 | 高 | **保留策略复核**。在 Kibana Dev Tools 执行 `GET _cat/indices?v&s=store.size:desc&bytes=gb`，定位 top 占用索引族，按 2026-07-21 `luckyur-log` 的处置方式缩短保留期。目标：把净增压到 ≤0 |
| P1-2 | 高 | **告警取值改为 Minimum**。当前策略按域级节点均值报警，最紧节点比告警值低约 3 GiB。应改为 per-node `Minimum`，阈值按 AWS 口径 min(20%×卷容量, 20 GiB) 设置 —— 扩容后即 **20 GiB** |
| P1-3 | 中 | **分片治理**。662 活跃分片 / 4 数据节点 ≈ **165 分片/节点**；m5.large 堆约 4 GiB，AWS 建议 ≤25 分片/GiB 堆（即 ≤100/节点），当前超出约 65%，`JVMMemoryPressure` 已长期 74–75%。**扩容会让索引留存更久、分片更多**，若不同步治理，下一堵墙是 JVM 92% 触发的写阻断 |

---

## 八、影响与风险评估

| 项目 | 评估 |
|------|------|
| **业务中断** | **无**。增大 EBS 卷容量属 AWS 文档列明的"不触发 blue/green"操作，为在线原地扩容 |
| **影响范围** | `luckylfe-log` 日志集群。扩容期间写入与查询正常 |
| **数据风险** | **无**。不涉及数据迁移、不改卷类型、不改实例、不改分片分布 |
| **性能影响** | 扩容期间 EBS 卷处于 `optimizing` 状态，可能有轻微 I/O 抖动。当前 IOPS 用量不足基线的 20%，实际影响可忽略 |
| **变更失败风险** | 低。失败时域保持原配置，可从 `describe-domain-change-progress` 观察 |
| **约束** | EBS 修改后 **6 小时内不能再次修改**，因此需一次到位（这也是不推荐方案 A 的原因之一） |
| **不变更的风险** | **高**。4 个节点已全部低于 AWS 文档写失败阈值，最紧节点 7–12 天见底 |

---

## 九、执行步骤

**1）变更前检查**
```bash
aws opensearch describe-domain --domain-name luckylfe-log --region us-east-1 \
  --query 'DomainStatus.{EBS:EBSOptions,Instance:ClusterConfig.InstanceType,Count:ClusterConfig.InstanceCount,Processing:Processing}'
# 预期：VolumeType=gp2, VolumeSize=80, Processing=false
```

**2）Dry-run 确认不触发 blue/green**
```bash
aws opensearch update-domain-config --domain-name luckylfe-log --region us-east-1 \
  --ebs-options EBSEnabled=true,VolumeType=gp2,VolumeSize=150 \
  --dry-run --dry-run-mode Verbose
# 预期 DryRunProgressStatus 无阻塞项，DeploymentType 非 Blue/Green
```

**3）执行扩容**
```bash
aws opensearch update-domain-config --domain-name luckylfe-log --region us-east-1 \
  --ebs-options EBSEnabled=true,VolumeType=gp2,VolumeSize=150
```

**4）跟踪进度**
```bash
aws opensearch describe-domain-change-progress --domain-name luckylfe-log --region us-east-1
# 等待 Status 变为 COMPLETED
```

> 执行账号需具备 `es:UpdateDomainConfig` 权限。

---

## 十、验证方法（变更完成后 30 分钟内）

| # | 验证项 | 预期结果 |
|---|--------|----------|
| 1 | `describe-domain` → `EBSOptions.VolumeSize` | `150`，`Processing` = `false` |
| 2 | CloudWatch `FreeStorageSpace`（分节点 Minimum） | 每节点 ≥ 70 GiB（最紧节点约 76.7 GiB） |
| 3 | `ClusterStatus.green` / `Shards.unassigned` | `1` / `0` |
| 4 | `ClusterIndexWritesBlocked` | 保持 `0` |
| 5 | `JVMMemoryPressure` | 无跃升（预期仍在 74–75%，本变更不改善此项） |
| 6 | 宙斯告警 | P0 恢复为正常 |

> 注意：本变更**只解决磁盘容量**。不应期待 JVM 压力或分片数有任何改善 —— 那属于 P1-3 的范围。

---

## 十一、回滚方案

**本变更实质上不可回滚，也不需要回滚**：

- EBS 卷容量**不支持缩小**；若必须回退到 80 GiB，需通过 blue/green 重建，风险远高于变更本身，
  且当前数据量（281.5 GiB）也已装不回 320 GiB 的安全水位。
- 增加磁盘空间不会造成数据丢失、不改变数据布局，**失败模式只有"没生效"，没有"变更坏"**。
- 若扩容过程异常中断，域会保持原有 80 GiB 配置继续运行，此时按第七节 P1-1 紧急删除最大索引争取时间。

---

## 十二、请求批准事项

1. **批准 `luckylfe-log` 4 个数据节点 EBS 由 80 GiB 扩容至 150 GiB**（方案 B，月增 $26.08）；
   若倾向一年免维护，可改批方案 C（200 GiB，月增 $44.71）。
2. **授权立即执行**（在线操作、无停机，无需等待低峰窗口）。
3. 知悉第七节 P1 配套项将另行推进，扩容本身不构成根因修复。

---

**申请人签字**：曾翔宇 (David Zeng) ______________  日期：2026-08-19

**审批人签字**：Michael (CTO) ______________  日期：__________
