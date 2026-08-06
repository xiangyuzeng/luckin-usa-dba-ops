# 《北美数据库周报 0806》采集数据包

**报告周期**：本周 = 2026-07-30 00:00 ~ 2026-08-06 00:00 UTC（7 整天）｜上周 = 2026-07-23 00:00 ~ 2026-07-30 00:00 UTC
**采集时间**：2026-08-06 ~14:20 UTC
**口径**：全部 UTC。08-06 当日为不完整日，单独列出，**不计入本周合计**。
**说明**：仓库里已有的 `alert-mailserver/report/alert-weekly-2026-W31.md` 覆盖的是 07-27~08-02（ISO 周），与本期窗口不一致，**未直接复用**；我用 `scripts/alert_report.py --start 2026-07-23 --end 2026-08-06`（只读 SELECT）重新拉了原始行后按本期窗口重算。

---

## 1. 本周单周告警口径

数据源：`luckyus_db_collection.t_dba_alert_reports`（@ aws-luckyus-ldas01-rw，AI 分析平台落库表）+ `luckyus_izeus.t_alert`（@ aws-luckyus-devops-rw，Zeus 全量）。两边以 `finger_print` + 分钟级时间逐条对账。

### a) 按天告警条数（P0 / P1 / P2）

| 日期(UTC) | 总条数 | P0 | P1 | P2 |
|---|---:|---:|---:|---:|
| 2026-07-30 | 27 | 20 | 3 | 4 |
| 2026-07-31 | 2 | 0 | 0 | 2 |
| 2026-08-01 | 4 | 0 | 0 | 4 |
| 2026-08-02 | 2 | 0 | 0 | 2 |
| 2026-08-03 | 4 | 2 | 0 | 2 |
| 2026-08-04 | 11 | 5 | 0 | 6 |
| 2026-08-05 | 6 | 0 | 0 | 6 |
| **本周合计** | **56** | **27** | **3** | **26** |
| 上周合计 | 127 | 61 | 15 | 51 |
| **环比** | **127 → 56（-71，-55.9%）** | 61 → 27（-34） | 15 → 3（-12） | 51 → 26（-25） |

> 来源：`t_dba_alert_reports`，按 `created_at` 分日（与 0730 期同字段，保证可比）；`alert_level` 取自告警名里的 Pn。
> 本周 56 条中：已 AI 分析 48 条、去重抑制 8 条（`record_kind`）；上周为 78 / 49。

**08-06 当日（partial，至 14:00 UTC，不计入上表）**：16 条 = P0 6 / P2 3 / **P3 7**。
其中 P3 来自新规则 `【pod-cpu】P3 CPU使用率连续3分钟大于70%`（`record_kind=info`），08-06 首次出现 —— 即 pod-cpu 冷启动尖峰规则已从 P0 降级为 P3，是上期「分析结论回流告警规则」待办的落地信号。另 08-04 起出现 `【pod-cpu】CPU使用率连续3分钟大于70%(新增-podAge过滤)` 3 条。

### b) 事件合并后的独立故障点数与收敛比

| 收敛层级 | 本周 | 上周 | 本周收敛比 |
|---|---:|---:|---:|
| ① 原始告警条数 | 56 | 127 | 1.00 |
| ② `finger_print` + 分钟级时间（去重复投递） | 56 | 127 | **1.00 : 1** |
| ③ 独立 `finger_print` 数 | 35 | 41 | 1.60 : 1 |
| ④ 事件合并：同对象 + 同规则族，间隔 ≤30min 归一 | **50** | 95 | **1.12 : 1** |
| ⑤ 事件合并：同对象 + 同规则族，间隔 ≤60min 归一 | 46 | 94 | 1.22 : 1 |
| ⑥ 独立告警对象数 | **21** | 32 | **2.67 : 1**（上周 3.97 : 1） |

> 来源：`t_dba_alert_reports` 原始行本地聚合（脚本 `analyze_merge.py`）。规则族 = 把规则名中的阈值数字归一（如 70%/85%、大于30/大于45 视为同族）。

**必须说明的一点**：你指定的合并键「`finger_print` + 分钟级时间」在本期**收敛比为 1.00 : 1**，即一条都合并不掉 —— 因为平台在落库前已按同一粒度判过重（本周 8 条 `record_kind=duplicate` 就是被判掉的），该键只用于和 Zeus 对账，不产生额外收敛。
**建议本期用第 ④ 层（50 个独立故障点，收敛比 1.12 : 1）作为「独立故障点」口径**，并在文中同时给出第 ⑥ 层「21 个独立告警对象（收敛比 2.67 : 1）」—— 后者与上期「避免以告警量误判系统健康度」的表述最贴合：**56 条告警实际只落在 21 个对象上**。

### c) 本周 Top5 告警来源对象

| # | 来源对象 / 服务族 | 条数 | 占比 | 涉及对象数 | 出现天数 | 级别 | 根因归类 |
|---|---|---:|---:|---:|---:|---|---|
| 1 | `aws-luckyus-isalescdp-rw` | 22 | 39.3% | 1 | **7/7** | P2×22 | 批处理/定时任务(14)、连接池/连接泄漏(11)、误报/阈值噪声(11)、真实故障(6) |
| 2 | `iscmpurchase-pdawsus-*`（4 个 Pod） | 10 | 17.9% | 4 | 2 | P0×8 / P2×2 | 发布/变更引发（滚动发布 JVM 冷启动尖峰），已自愈 |
| 3 | `iscmsims-pdawsus-*`（2 个 Pod） | 4 | 7.1% | 2 | 1 | P0×4 | 同上：发布冷启动尖峰 |
| 4 | `iscmsrm-pdawsus-*`（3 个 Pod） | 4 | 7.1% | 3 | 2 | P0×3 / P2×1 | 同上：发布冷启动尖峰 |
| 5 | `meta-platform-rel-*`（2 个 Pod） | 3 | 5.4% | 2 | 1 | **P1×3** | 容量/内存不足 + 真实故障（周期性 OOMKilled，见第 2 节） |

> 来源：`t_dba_alert_reports.instance` / `.subject` / `.conclusion` / `.root_cause`（根因标签为对结论段关键词提取，一条可命中多标签）。
> 其余：`iscmcommodityadmin` 3、`iscmwds` 3、`iscmordering` 3、`idm` 2、`iscmplan` 1、`redis:luckyus-aigatewayadmin` **1**。

**结构变化很大**：上周 Top1 是 `redis:luckyus-aigatewayadmin` 38 条（29.9%）+ `iluckyaigatewayadmin` Pod 21 条，本周该族合计只剩 **1 条**；`isalescdp` 从 11 条升到 22 条并成为唯一 7/7 天复现的慢性项。

本周全部告警的根因标签分布（分母 = 已分析 48 条）：发布/变更引发 32（66.7%）、误报/阈值噪声 30（62.5%）、真实故障 24（50.0%）、容量/内存不足 22（45.8%）、批处理/定时任务 20（41.7%）、连接池/连接泄漏 17（35.4%）、已自愈/无需处理 14（29.2%）。

### d) 规则重叠重复上报（pod-cpu 70% 与 pod-cpu-兜底 85%）

| 指标 | 本周 | 上周 |
|---|---:|---:|
| `【pod-cpu】…大于70%` 条数（含 podAge 过滤变体 3 条） | 20 | — |
| `【pod-cpu-兜底】…大于85%` 条数 | 10 | — |
| **同一 Pod 被两条规则同时命中的 Pod 数** | **10** | 8 |
| **涉及的告警条数** | **22** | 16 |
| 其中两条告警间隔 ≤60 分钟的配对数 | 12 | — |
| **可压缩掉的冗余条数**（22 条 → 10 个事件） | **12** | 8 |

> 来源：`t_dba_alert_reports`，按 `instance` + `subject` 前缀配对，`created_at` 计算间隔。
> 典型样例：`iscmcommodityadmin-pdawsus-8d8847c54-t8xqv` 07-30 09:02:48（70%）与 09:07:35（85%）相隔 4 分钟；`iscmpurchase-pdawsus-7f9598c8dc-ndn5r` 08-04 一次冷启动被 3 条规则（兜底85% / podAge变体 / 70%）命中 3 次。

**即：本周 56 条中有 12 条（21.4%）是规则重叠造成的纯冗余上报。**

### e) 超 1 小时未恢复 / 无人认领被自动升级

| 口径 | 本周 | 上周 |
|---|---|---|
| **重点关注（进入分析平台的 56 条）** | | |
| — 持续 >1 小时的告警对象 | **0** | 0 |
| — 仍未恢复（`alert_status != RESOLVED`） | **0** | 0 |
| — 被 Zeus 自动升级（`alert_upgrade_status=UPGRADED`） | **0** | 0 |
| — 自动恢复 / 人工恢复 | 56（100%）/ 0 | 127（100%）/ 0 |
| — 已认领 | 0 | 1 |
| — 持续时长 P50 / P90 / 最大 | **5m01s / 7m00s / 13m00s** | 5m00s / 8m00s / 29m00s |
| **DBA 域全景（Zeus DB+POD+MSK，107 条）** | | |
| — >1h / 未恢复 / 被升级 | **0 / 0 / 0** | 0 / 0 / 0 |
| **全公司全景（Zeus 全量 275 条）** | | |
| — >1h | 8 条 | 2 条 |
| — 被自动升级 | 4 条 | 4 条 |

> 来源：`luckyus_izeus.t_alert` 的 `duration` / `alert_status` / `claimed_status` / `alert_upgrade_status`。

**结论：DBA 域本周零条超 1 小时未恢复、零条被自动升级。** 全公司那 8 条 >1h 与 4 条被升级的**全部落在「其他域」（非 DBA 域）**，明细：

| 持续 | 级别 | 告警规则 | 触发(UTC) | 升级 | 认领 |
|---|---|---|---|---|---|
| 16.08h / 12.08h / 8.08h / 4.08h | P2 | `CPUResourceRequireHigh`（4 条） | 07-30 12:35 | 未升级 | 未认领 |
| 10.03h | P0 | 【触达】【北美】触达过滤率持续30分钟大于99% | 08-04 11:59 | **UPGRADED** | 未认领 |
| 10.03h | P0 | 【触达】【北美】触达发送率持续30分钟小于1% | 08-04 11:59 | **UPGRADED** | 未认领 |
| 7.90h ×2 | P0 | 【触达】【北美】渠道供应商成功率持续4小时低于65% | 08-05 14:06 | 1 条 UPGRADED | 未认领 |
| 0.98h | P1 | 【北美】30分钟内营销短信回执成功率低于 60% | 08-05 13:23 | **UPGRADED** | 未认领 |

> 触达 P0 已在 `reports/触达-渠道供应商成功率告警排查-2026-08-05.md` 定性（cyberdata 运维短信拖低租户成功率，无业务影响）。

**Zeus 全景对账**：本周 Zeus 全量 275 条（上周 397）→ DBA 域 107 条（上周 151）→ 进入分析平台 56 条（上周 127），未进平台 51 条全部是 MSK：`【kafadmin-AWS MSK】CPU使用率超过85%` 33、`副本未同步分区大于0` 12、`TCP端口不通` 6。

> **结论（≤80字）**：告警条数 127→56 腰斩，56 条只落在 21 个对象上（收敛比 2.67:1），其中 12 条是 pod-cpu 双规则冗余。DBA 域零条超 1 小时、零条被自动升级。

---

## 2. meta-platform-rel 容器 OOM 本周状态

对象：`cyberdata-prod / meta-platform-rel`（cluster `prod-native-eks-us`，Deployment 2 副本，镜像 `cyberdata:cyber-platform-5.4.6.20251216_release`）

### a) OOMKilled 次数 / 累计重启 / 本周净增

| 副本 | 07-30 00:00 累计重启 | 08-06 14:00 累计重启 | **本周净增** |
|---|---:|---:|---:|
| `…-665ccfdd7f-29zxr` | 29 | **38** | **+9** |
| `…-665ccfdd7f-hqdzq` | 27 | **36** | **+9** |
| **合计** | 56 | **74** | **+18** |

> 来源：Prometheus `kube_pod_container_status_restarts_total{namespace="cyberdata-prod"}`（datasource `victoriametrics-basic-us` / uid `ZBv6_UeHz`），及 `manage_k8s_resource read Pod` 的 `containerStatuses[].restartCount`。
> 口径提示：上期引用的「28 / 31」是 07-30 10:00–18:00 UTC 之间的快照（不是 07-30 00:00）。以那个快照为基线，本周净增为 hqdzq +8 / 29zxr +7 = **+15**。两种基线我都列出，建议周报统一用周界 07-30 00:00 的 **+18**（与上期「一周内净增 18 次」数量级一致）。

**最近一次终止原因两副本均为 `OOMKilled`（exitCode 137）**：
- `29zxr`：2026-08-05 13:36:50 → 2026-08-06 05:52:07 UTC，运行 **16h15m** 后被杀
- `hqdzq`：2026-08-05 07:52:14 → 2026-08-06 03:45:24 UTC，运行 **19h53m** 后被杀
- 上周 OOM 周期为 12.5h / 13.2h → **本周周期拉长**

> ⚠️ **本周 18 次重启的逐次 exitCode 未取到**（Kubernetes 只保留 `lastState` 一次），仅能确认最近一次为 OOMKilled。
> ⚠️ **告警覆盖缺口**：本周 18 次重启只产生了 **3 条** `【pod-宕机】P1 WSS内存使用率连续3分钟等于100%` 告警（全部在 07-30，Zeus 侧同为 3 条），07-31 之后 15 次 OOM 重启**未触发任何告警**。建议单独跟进。

### b) 内存峰值是否仍在 8.3—8.6GB

| 副本 | 本周峰值（GiB） | 换算十进制 GB | 容器 limit |
|---|---:|---:|---|
| `29zxr` | **7.9985 GiB** | **8.588 GB** | 8Gi = 8.0 GiB = 8.590 GB |
| `hqdzq` | **7.9994 GiB** | **8.589 GB** | 同上 |

> 来源：Prometheus `max_over_time(container_memory_working_set_bytes{...}[7d])`。逐小时序列在 **7.29–7.93 GiB** 区间震荡，各重启周期峰值未逐周抬高。

**判断：仍稳定在 8.3–8.6GB 区间（上沿），未出现持续恶化型泄漏，与上周结论一致。**
单位提醒：上期「8.3–8.6GB」是十进制 GB，换算成 GiB 为 7.73–8.01 GiB —— 本周 7.999 GiB 正好贴住 8Gi 上限，属"稳态占用与 limit 几乎重合"，不是"泄漏在加速"。

### c) 上周三项建议落地情况

| # | 建议 | 状态 | 证据 |
|---|---|---|---|
| 1 | 内存 limit 上调至 10—12Gi | **未落地** | `resources.limits.memory = 8Gi`，`requests = 8Gi`，`qosClass = Guaranteed`（两副本一致） |
| 2 | 堆上限下调至 5—5.5G | **未落地** | 启动命令仍为 `-Xms5G -Xmx7G -XX:MetaspaceSize=512M -XX:MaxMetaspaceSize=1024M`（两副本一致） |
| 3 | 新增 Pod 反亲和策略 | **未落地** | Pod spec 中**无** `affinity` / `podAntiAffinity` 字段 |
| 4 | 两副本是否仍在同一节点 | **是，仍同节点** | 两副本 `spec.nodeName = ip-10-238-60-159.ec2.internal` |

> 来源：`manage_k8s_resource(operation=read, kind=Pod)` 读取两个 Pod 的完整 spec。
> 佐证「本周确实没有任何变更」：两副本 `pod-template-hash` 仍为 `665ccfdd7f`、`creationTimestamp` 仍为 2026-06-09、镜像 tag 未变。

> **结论（≤80字）**：三项建议全部未落地，两副本仍同节点、仍 8Gi limit / -Xmx7G。本周净增 18 次 OOM 重启，峰值 8.59GB 未恶化，但 15 次重启未触发告警，存在监控缺口。

---

## 3. MySQL 实例 devops-rw 连接数上涨原因

### a) 连接来源分解

采样时刻 2026-08-06 ~14:20 UTC，`Threads_connected = 675`。

| 客户端 IP | 主机 | user | 库 | 连接数 | 占比 | 状态 |
|---|---|---|---|---:|---:|---|
| **10.238.3.178** | **lauthservice01-prod-usa-aws**（`i-09d2b232a1430b412`, c6i.large） | `authservice_w` | `luckyus_authservice` | **500** | **74.1%** | 全部 `Sleep`；idle 均值 387s，最大 782s |
| 10.238.3.201 | — | `izeusmetric_A_o/w` | `luckyus_izeus` | 21 | 3.1% | Sleep |
| 10.238.3.179 | — | `izeusmetric_A_o/w` | `luckyus_izeus` | 17 | 2.5% | Sleep |
| 10.238.3.181 | — | `ilopamanager_A_w` | `luckyus_ilopamanager` | 13 | 1.9% | Sleep |
| 10.238.3.198 | — | `ilopamanager_A_w` | `luckyus_ilopamanager` | 13 | 1.9% | Sleep |
| 10.238.3.119 | **lauthservice02-prod-usa-aws**（`i-07231f36fcc0430bd`） | `authservice_w` | `luckyus_authservice` | **6** | 0.9% | Sleep，idle 均值 9s |
| 其余约 49 个来源 | — | — | — | 约 105 | 15.6% | — |

> 来源：`information_schema.PROCESSLIST` 分组统计（只读）；`performance_schema.hosts`。
> `performance_schema.hosts` 交叉验证：`10.238.3.178` → `CURRENT_CONNECTIONS=500`，`TOTAL_CONNECTIONS=659,449`；`10.238.3.119` → `CURRENT_CONNECTIONS=6`，`TOTAL_CONNECTIONS=655,307`。**两台机历史连接总量几乎一样，当前持有量却是 500 : 6。**
> 主机名解析命令：`aws ec2 describe-instances --filters Name=private-ip-address,Values=10.238.3.178`

**增量来源结论：100% 来自 lauthservice01 一台机器。**

### b) 是连接池未回收，还是监控采集 / 定时任务？

**是应用连接池未回收（lauthservice01 单机），不是监控采集，也不是定时任务。** 依据：

1. **不是「持续上涨」，是一次性阶跃**。CloudWatch `AWS/RDS DatabaseConnections`（`Maximum`，5 分钟粒度）：
   | 时刻(UTC) | 值 |
   |---|---:|
   | 2026-07-28 02:25 | 177 |
   | **2026-07-28 02:30** | **672** |
   | 2026-07-28 02:35 → 2026-08-06 08:11 | 668 ~ 692（**9 天平稳，无爬升**） |

   5 分钟内 **+495**，与 lauthservice01 当前持有的 500 条几乎完全对应。
2. 全部 500 条 `COMMAND=Sleep`，`wait_timeout` / `interactive_timeout` 均为 **28800 秒（8 小时）**，闲置连接不会被服务端回收。
3. 同账号同库的 lauthservice02 历史连接总量相当，却只保持 6 条 → **两台机的连接池配置不一致**，问题在 lauthservice01 一侧。
4. 监控采集类账号（`diagtools` 4–5 条、`dbms_dbsearch` 2 条）和 Zeus 采集（`izeus*` 合计约 60 条）量级都很小，可排除。
5. ⚠️ **客户端程序名未取到** —— `performance_schema.session_connect_attrs` 对这批连接无记录（`_client_name` / `program_name` 查询返回 0 行），无法从 DB 侧直接确认是哪个连接池实现。需应用侧配合确认 `maxPoolSize` / `minIdle`。

### c) max_connections 与峰值占比

| 指标 | 值 | 来源 |
|---|---|---|
| `max_connections` | **4000** | `performance_schema.global_variables` |
| `Max_used_connections`（历史峰值） | **778** | `performance_schema.global_status` |
| 峰值发生时间 | 2026-07-28 06:11:53 | `Max_used_connections_time` |
| **峰值占比** | **778 / 4000 = 19.5%** | 计算 |
| 当前占比 | 675 / 4000 = 16.9% | 计算 |
| `max_user_connections` | 0（不限） | `global_variables` |

**无触顶风险**，距上限还有 4 倍余量。

### d) 结论一句话

**需要处理但不紧急** —— 是 lauthservice01 单机连接池在 2026-07-28 02:30 UTC 一次性建满 500 条常驻连接且不回收（非泄漏、非持续上涨、9 天完全平稳），占用上限仅 19.5%；建议与应用侧核对 lauthservice01 的连接池 `maxPoolSize`/`minIdle` 并与 lauthservice02 对齐，本周内可归为"观察 + 应用侧跟进"，不需紧急变更。

> **补充（会影响周报措辞）**：看板显示的「592 → 672 继续上涨」是口径造成的假象，实际是 07-28 一次阶跃后完全平稳。详见第 6 节。

---

## 4. MySQL 8.4 升级与 8.0 扩展支持进展

### a) 截至 2026-08-06 全部实例 8.4 升级状态

| 状态 | 实例数 | 占比 |
|---|---:|---:|
| **已完成（8.4.x）** | **64** | **100%** |
| — 其中 8.4.10 | 22 | |
| — 其中 8.4.9 | 42 | |
| 待升级（8.0.x 或更低） | **0** | 0% |
| 未排期 | **0** | 0% |

> 来源：`aws rds describe-db-instances --region us-east-1`（`Engine=='mysql'`，共 64 个实例，全部 `available`）。
> 另有 PostgreSQL 1 个（`aws-luckyus-pgilkmap-rw`，17.9）、DocumentDB 12 个（5.0.0），不在本议题范围。

### b) 第 5 批及后续批次

**无第 5 批 —— 全部 MySQL 实例已完成，没有待升级实例，无需再排期。**

蓝绿部署与原库清理状态（复核）：
| 检查项 | 结果 | 命令 |
|---|---|---|
| 残留 `*-old*` 实例 | **0 个** | `describe-db-instances --query "…contains(DBInstanceIdentifier,'old')…"` |
| 进行中的蓝绿部署 | **0 个** | `aws rds describe-blue-green-deployments` |
| 本周新建 RDS 实例 | **0 个** | `describe-db-instances --query "…InstanceCreateTime>='2026-07-23'…"` |

### c) 扩展支持启用情况全量核对

| `EngineLifecycleSupport` | MySQL 实例数 |
|---|---:|
| `open-source-rds-extended-support`（**已启用**） | **64** |
| `open-source-rds-extended-support-disabled`（未启用） | **0** |

**未启用名单：无（0 个）。**

> 来源：`reports/rds-extended-support-enablement/scripts/check-extended-support-status.sh --region us-east-1`（只读脚本，仅调用 describe-*），以及 `aws rds describe-db-instances --query "DBInstances[?Engine=='mysql'].[EngineVersion,EngineLifecycleSupport]"` 交叉验证。

启用执行时间线（脚本审计日志 `reports/rds-extended-support-enablement/scripts/logs/`）：

| 批次 | 时间(UTC) | 模式 | 目标数 | 结果 |
|---|---|---|---:|---|
| L2 | 2026-07-24 14:42:52 | APPLY | 10 | done=10 already=0 skipped=0 **failed=0** |
| L1 | 2026-07-29 17:17:31 | APPLY | 36 | done=36 already=0 skipped=0 **failed=0** |
| L0 | 2026-07-29 17:21:02 | APPLY | 16 | done=16 already=0 skipped=0 **failed=0** |
| — | — | — | **62** | 加上原本已启用的 2 个 = **64**，全部在 7/31 标准支持到期前完成 |

> 上期提到的「首批 10 个」= L2 那一批（`fichargecontrol` / `ifiaccounting` / `iluckyams` / `iluckydorisops` / `iluckyhealth` / `ilsopdevopsdata` / `iopocp` / `oplog` / `opqualitycontrol` / `scm-wmssimulate`），已逐个复核，均为 `open-source-rds-extended-support`。

**7/31 之后是否有实例被云厂商自动升级至 8.4：无。**
`aws rds describe-events`（2026-07-23 ~ 08-06 全量，逐条筛查）中，**唯一的引擎版本升级事件**是：

| 时间(UTC) | 实例 | 事件 |
|---|---|---|
| 2026-08-01 10:03:32 | `aws-luckyus-pgilkmap-rw` | The pre-check started / finished for the DB engine version upgrade |
| 2026-08-01 10:03:57–10:04:55 | `aws-luckyus-pgilkmap-rw` | downtime started → shutdown → upgrade started → restarted → upgrade finished |
| 2026-08-01 10:09:25 | `aws-luckyus-pgilkmap-rw` | Monitoring Interval changed to 0 |

该实例是 **PostgreSQL**，属自动小版本升级，**与 MySQL 8.0 强制升级无关**。MySQL 侧本期零条 engine upgrade 事件。
补充：由于 64 个 MySQL 实例在 7/31 前就已全部到 8.4.x，「未启用扩展支持会被强制升级」这一风险本期已**不适用**。

### d) 已启用实例中版本低于 8.0.46 的是否被自动升至 8.0.46

**不适用 —— 无此类实例。** 全部 64 个 MySQL 已在 8.4.x，8.0.x 实例数为 0，不存在 8.0.45 → 8.0.46 的自动小版本升级场景。

### e) 扩展支持的计费影响估算

**本期计费影响 = $0（未产生扩展支持费用）。**

> 来源：`aws ce get-cost-and-usage --time-period Start=2026-07-01,End=2026-08-06 --granularity MONTHLY --filter SERVICE="Amazon Relational Database Service" --group-by USAGE_TYPE`（1 次 CE 调用，$0.01）。
> 2026-07 与 2026-08（至 08-06）两个账期的 RDS usage type 明细中，**均无任何 extended-support 相关 usage type**。7 月 RDS 全部费用构成为 `Multi-AZUsage:*`（实例）、`RDS:Multi-AZ-GP3-Storage`、`HeavyUsage:db.t4g.medium`、`CPUCredits:db.t4g`、`RDS:ChargedBackupUsage` 等常规项。
> 原因合理：扩展支持只对**处于扩展支持期的版本**（8.0）计费；本方全部实例已升到 8.4（标准支持期内），`EngineLifecycleSupport=enabled` 只是一个保险标志，不触发计费。

> **结论（≤80字）**：64 个 MySQL 全部完成 8.4 升级（8.4.10×22 / 8.4.9×42），无第 5 批；扩展支持 64/64 已启用、0 未启用，7/24–7/29 分三批完成；7/31 后无 MySQL 被强制升级；计费影响 $0。

---

## 5. 本周扩容 / 下线 / LSOP 工单

### a) RDS / Redis 扩容或下线

| 类别 | 本周结果 |
|---|---|
| RDS 存储扩容 | **本周无** |
| RDS 规格变更 | **本周无** |
| RDS 实例下线 | **本周无** |
| RDS 实例新建 | **本周无** |
| ElastiCache 扩容 / 规格变更 | **本周无** |
| ElastiCache 集群下线 | **本周无** |

**本周唯一的基础设施变更：**

| 工单号 | 对象 | 变更内容 | 执行时间(UTC) |
|---|---|---|---|
| **无工单号**（AWS 自动维护动作） | `aws-luckyus-pgilkmap-rw`（PostgreSQL 17.9） | 引擎小版本自动升级（pre-check → downtime → upgrade → restart，全程约 83 秒）；随后 Monitoring Interval 改为 0 | 2026-08-01 10:03:32 ~ 10:09:25 |

> 来源：`aws rds describe-events --duration 11520`（全量逐条筛查，剔除快照/备份类）；`aws elasticache describe-events --duration 20160`（近 14 天除自动快照外**无任何其他事件**）；`aws elasticache describe-replication-groups`（79 个复制组全部 `available`，`PendingModifiedValues` 均为空）。
> ⚠️ **工单号未取到** —— 上述均为 AWS 侧事件，本地没有可关联的 LSOP / 变更工单记录。

上期完成的 10 个 `*-old1` 蓝绿源库下线（07-24 ~ 07-28）**不在本期窗口**，明细供参考：`isalesprivatedomain-rw-old1`(07-24 00:00)、`swqtest8045-rw-old1`(07-24 02:15)、`swqtest8045-rw`(07-24 02:28)、`iluckyams-rw-old1`(07-24 16:40)、`salesmarketing-rw-old1`(07-27 13:29)、`isalescouponservice-rw-old1`(07-27 13:30)、`cdpactivity-rw-old1`(07-28 05:33)、`isalescdp-rw-old1`(07-28 05:34)、`salesorder-rw-old1`(07-28 13:46)、`salespayment-rw-old1`(07-28 13:47)。

### b) LSOP 工单自动执行

| 时间(UTC) | 模式 | 结果 |
|---|---|---|
| 2026-07-30 14:35:29 | dry_run | matched=0，would_approve=0 |
| 2026-07-30 16:16:01 | dry_run | candidates=1，would_execute=1 |
| **2026-07-30 16:16:21** | **execute** | ticket `44748eea-…`「生产环境lfeserver服务SSH登录权限申请」，root_type=uam，env=prod，http=200，code=1000，**status=OK** |

| 指标 | 本周 |
|---|---|
| 执行单数 | **1** |
| 成功 / 失败 | **1 / 0** |
| **执行成功率** | **100%** |
| **新增覆盖的工单类型** | **无** —— `config.json` 的 `match.name_contains` 仍为 `["SSH登录权限申请"]`，`root_type_in=["uam"]`，未扩展 |
| 失败案例 | **无** |

> 来源：`/app/lsop-auto-approve/audit.log`（全量仅上述 3 行）、`/app/lsop-auto-approve/config.json`、`whitelist.json`（审批人白名单仅 `jingyu.li@…`，有效期至 2027-01-30）。
> ⚠️ **限制必须标注**：该工具以 Docker 部署在另一台主机，本环境无 `docker` 命令，无法核对线上容器的执行记录是否与本地 `audit.log` 一致。若线上另有执行，本地日志不含。**建议周报注明"以本地审计日志为准，线上记录待核"。**

### c) 本周容量类告警

**本周有容量类告警（上期为零，本期非零）。**

| 对象 | 告警内容 | 本周条数 | 首条 / 最新(UTC) | 状态 |
|---|---|---:|---|---|
| `aws-luckyus-icyberdata-rw` | `Storage size 900 GiB is approaching the maximum storage threshold 1000 GiB. Increase the maximum storage threshold.` | **91**（每 2 小时一条） | 2026-07-30 00:45:03 / **2026-08-06 13:30:06** | **仍在持续** |

当前配置（`aws rds describe-db-instances --db-instance-identifier aws-luckyus-icyberdata-rw`）：

| 项 | 值 |
|---|---|
| AllocatedStorage | **900 GiB** |
| MaxAllocatedStorage（存储自动扩展上限） | **1000 GiB** |
| 余量 | 100 GiB（10%） |
| StorageType / IOPS | gp3 / 12000 |
| 实例规格 / 引擎 | db.t4g.medium / MySQL 8.4.10 |
| PendingModifiedValues | 空 |

> 该告警自 2026-07-23（`describe-events` 可查询范围起点）起就连续存在，属**跨周慢性项，非本周新增**。
> ⚠️ **监控覆盖缺口**：该告警只进 AWS RDS 事件流，**未进 Zeus，也未进 AI 分析平台**（本周 Zeus 全量 275 条中无对应条目）。建议纳管。

> **结论（≤80字）**：本周无 RDS/Redis 扩容与下线，仅 pgilkmap 一次 PG 自动小版本升级；LSOP 执行 1 单成功率 100%、无新增类型；容量告警**非零** —— icyberdata 存储 900/1000 GiB 已告警 91 条且未纳管。

---

## 6. 指标口径校验

### 6.0 看板口径全表（Grafana uid `4jhaMqDDk`，文件夹 DBA-US，**只读，未做任何修改**）

数据源不是 Prometheus，而是 MySQL `luckyus_db_collection`（Grafana datasource uid `LJ7ObqYNk`，实例 `aws-luckyus-ldas01-rw`）。

| 面板 | 底表 | **聚合方式** |
|---|---|---|
| 上周/本周 CPU使用率(P95)〔Redis〕 | `t_dba_collect_redis_cluster_metrics`，`metric_name='EngineCPUUtilization'` | 对窗口内**每日 `maximum` 取 P95**（SQL 里用 ROW_NUMBER 手算），`HAVING p95>5`，`LIMIT 3` |
| 上周/本周 内存使用率〔Redis〕 | 同表，`metric_name='DatabaseMemoryUsagePercentage'` | 每日 `maximum` 的 P95，`HAVING p95>30`，`LIMIT 3` |
| **上周/本周 客户端连接数〔Redis〕** | `t_dba_collect_redis_group_info` | **`MAX(connected_clients)`**，`HAVING max>200` |
| 上周/本周 CPU使用率(P95)〔MySQL〕 | `t_dba_collect_rds_metrics`，`metric_name='CPUUtilization'` | 每日 `Maximum` 的 P95，`LIMIT 3` |
| **上周/本周 数据库连接数〔MySQL〕** | `t_dba_collect_rds_metrics_daily`，`metric_name='DatabaseConnections'` | **`AVG(Average)`**（日均值的均值），`LIMIT 5` |
| 数据库剩余空间 / 空间占用率(%) | `t_dba_collect_rds_instances` | 取近 2 天内的**最新一条快照**，非窗口聚合 |

**没有一个面板用「末值」；Redis 连接数用 MAX，MySQL 连接数用 AVG，CPU/内存用 P95 —— 三种聚合混用。**

**时间窗定义（所有面板写死在 SQL 里，完全一致）**：
```sql
-- 上周
data_date >= subdate(curdate(), weekday(curdate())+7)
  AND data_date < subdate(curdate(), weekday(curdate()))
-- 本周
data_date >= subdate(curdate(), weekday(curdate()))     -- 注意：无上界
```
MySQL `weekday()` 周一 = 0 → 窗口是 **ISO 周（周一起算）**，且**「本周」永远是从本周一到今天的不完整周**。

今天 2026-08-06 是**周四**（weekday=3），因此看板此刻的实际窗口是：

| 看板标签 | 实际区间 | 天数 |
|---|---|---|
| **上周** | **[2026-07-27(周一), 2026-08-03(周一))** | 完整 7 天 |
| **本周** | **[2026-08-03(周一), 至今]** | **只有 08-03 / 04 / 05 三天有数**（08-06 当日尚未落库） |

**时区 = UTC（有算术证据，非推断）**：`record_date` / `data_date` 是 DATE 类型，表里无时区字段。用 devops-rw 的阶跃反推——阶跃发生在 2026-07-28 02:30 UTC，若按 UTC 分日，07-28 当日均值应为 `(2.5h×172 + 21.5h×670)/24 ≈ 618`，实测 `Average` = **616.5**，吻合；若按美东（UTC-4）分日，07-28 全天都在阶跃后，均值应约 670，与实测不符。**故 data_date 按 UTC 分日。**

---

### 6.1 MySQL `devops-rw` 连接数：0730 正文 166→484 vs 看板 592→672

| 口径 | 上周值 → 本周值（变化量） | 出处 |
|---|---|---|
| **看板面板（今天跑）** | **591.9 → 671.6（+79.7）** | `avg(Average)`，上周=[07-27,08-03)，本周=[08-03,08-05] |
| **0730 报告正文（07-30 那天跑同一面板）** | **165.9 → 484.5（+318.6）** | 同一 SQL，当时上周=[07-20,07-27)，本周=[07-27,07-29] |
| **报告周期口径（[07-23,07-30) vs [07-30,08-06)）** | **302.2 → 672.1（+369.9）** | 同 `avg(Average)`，换成本报告窗口 |
| **物理事实（CloudWatch 1–5min `Maximum`）** | **~172 → ~670**，一次性阶跃 **+495 @ 2026-07-28 02:25→02:30 UTC**，此后 9 天平稳 668–692 | — |

逐日原始值（`t_dba_collect_rds_metrics_daily`，`instance_id='aws-luckyus-devops-rw'`）：

| 日期 | avg(Average) | max(Maximum) |
|---|---:|---:|
| 07-20 ~ 07-27 | 166.1 / 169.8 / 163.8 / 163.7 / 165.0 / 167.5 / 165.6 / 166.0 | 176 ~ 189 |
| **07-28** | **616.5** | **722** ← 阶跃日 |
| 07-29 ~ 08-05 | 670.9 / 674.5 / 675.7 / 671.0 / 668.8 / 669.7 / 670.7 / 674.5 | 679 ~ 692 |

**逐个复现（全部对上）**：
- 看板上周 `(166.0+616.5+670.9+674.5+675.7+671.0+668.8)/7 = 591.9` ✓ = 看板 592
- 看板本周 `(669.7+670.7+674.5)/3 = 671.6` ✓ = 看板 672
- 0730 正文本周 `(166.0+616.5+670.9)/3 = 484.5` ✓ = 正文 484
- 0730 正文上周 `07-20~07-26 均值 = 165.9` ✓ = 正文 166

**结论：三组数字全部正确，且出自同一个面板、同一段 SQL —— 差异 100% 来自「跑的日子不同 → 窗口不同」。**
关键一句：**「592 → 672 继续上涨」是算术假象** —— 上周均值 592 之所以偏低，只是因为 [07-27,08-03) 里 07-27 那一天（166）还在阶跃之前把均值拉下来了。真实情况是 07-28 02:30 一次阶跃后**连续 9 天完全平稳，没有任何继续上涨**。

### 6.2 Redis `aigatewayadmin` 客户端连接数：0730 正文 1724→794 vs 看板 1290→1507

`t_dba_collect_redis_group_info.connected_clients` 的字段注释是「**当前连接的客户端数量**」，且实测 **每天只有 1 个采样点**（`COUNT(*) = 1/天`）。面板对这些**单点**取 MAX。

而该实例连接数是**锯齿波**：每 50–70 分钟从约 150–400 爬升到 1700–1800 再骤降重置（来源：本平台 2026-07-29 / 07-30 的 AI 分析结论）。**每天那 1 个采样点落在锯齿的哪个位置基本随机。**

逐日采样值：

| 日期 | 07-23 | 07-24 | 07-25 | 07-26 | 07-27 | 07-28 | 07-29 | 07-30 | 07-31 | 08-01 | 08-02 | 08-03 | 08-04 | 08-05 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| connected_clients | 1706 | 812 | 790 | **1724** | **794** | 650 | 117 | 743 | 625 | **1290** | 300 | 942 | 825 | **1507** |

**逐个复现（全部对上）**：
- 看板上周 = MAX over [07-27,08-03) = **1290**（08-01 那点）✓
- 看板本周 = MAX over [08-03,今) = **1507**（08-05 那点）✓
- 0730 正文上周 = MAX over [07-20,07-27) = **1724**（07-26 那点）✓
- 0730 正文本周 = MAX over [07-27,07-30) = **794**（07-27 那点）✓

**结论：两组数同样都"对"，同样出自同一面板不同运行日；但这个指标根本不适合做环比 —— 1 天 1 个随机采样点再取 MAX，噪声远大于信号（同一周内单点在 117 ~ 1724 之间跳）。**

**真实趋势（CloudWatch `AWS/ElastiCache CurrConnections`，主节点 `luckyus-aigatewayadmin-001`）**：

| 指标 | 上周 [07-23,07-30) | 本周 [07-30,08-06) | 变化 |
|---|---:|---:|---|
| 日峰值 `Maximum` 的最大值 | **1998**（07-24） | **1789**（07-30） | **-209** |
| 日 `p95` 的均值 | **1581.1** | **1410.2** | **-170.9（-10.8%）** |
| 日 p95 区间 | 1546.9 ~ 1611.8 | 1385.7 ~ 1459.2 | 整体下移一档 |

**实际是下降，不是上涨。** 07-31 起 p95 稳定在 1385–1443（上周为 1547–1612）。
**佐证**：Redis 缓冲告警从上周 **20 条**（平台）/ 38 条（含 Pod 侧）降到本周 **1 条**（仅 07-30 01:22），Zeus 侧同为 1 条。
副本节点 `-002` 的 `CurrConnections` 恒为 7（只读副本无业务连接），不影响判断。

### 6.3 建议

**① 本期统一采用的口径**

> **CloudWatch 原始指标 + 报告周期窗口 `[2026-07-30 00:00, 2026-08-06 00:00) UTC`，聚合方式在表头显式标注。**
> 连接数类指标给**两个数**：窗口内 `p95`（代表常态）+ 窗口内 `Maximum`（代表峰值），**不使用日单点 MAX**。

理由：看板的 ISO 周窗口与报告周期（周四~周四）错位，且"本周"恒为不完整周，两周不可比；`t_dba_collect_redis_group_info` 每日单采样对锯齿型指标不可用。

**② 是否需要加口径脚注：需要，强烈建议加。** 建议脚注文案：

> 本报告「上周 / 本周」= 2026-07-23~07-30 / 2026-07-30~08-06（UTC）。Grafana「周报数据统计」看板的「上周 / 本周」按 ISO 周（周一起算）划分，且「本周」为**至今的不完整周**，与本报告窗口不一致；此外 MySQL 连接数面板取**日均值的均值**，Redis 客户端连接数面板取**每日单个采样点的最大值**，CPU / 内存面板取**日最大值的 P95**。因此看板数值与本报告正文数值存在差异，**属口径差异，非数据异常**。

**③ 看板本身的改进建议（仅建议，本次未做任何修改）**
- Redis 客户端连接数面板：底表每天仅 1 采样，无法代表锯齿型指标 → 改用 CloudWatch `CurrConnections` 的 p95，或提高 `t_dba_collect_redis_group_info` 采集频次。
- MySQL 连接数面板：`avg(Average)` 会把阶跃完全抹平 → 建议同时展示窗口内 `max(Maximum)` 与窗口末值。
- 两个「本周」面板的 SQL 无时间上界 → 「本周」恒为不完整周而「上周」是完整 7 天，二者不可比 → 至少在面板标题里标注「本周(至今 N 天)」。

### 6.4 aigatewayadmin 应用侧连接池本周是否有改动

**本周无任何改动。**

| 检查项 | 结果 | 来源 |
|---|---|---|
| Pod | `iluckyaigatewayadmin-pdawsus-69687b9db7-cvk7k` / `-dmmz5`（cluster `prod-worker01-eks-us`，ns `baseservices-architecturedata`） | `list_k8s_resources` |
| 创建时间 | **2026-07-23 08:34 UTC**（本周未重建） | `creationTimestamp` |
| 版本 | `iluckyaigatewayadmin-tag-v1.1.0-20260723161638-f5ffb51`（chart `infra_springboot-0.1.70`），本周未发版 | Pod labels `appVersion` |
| 本周重启次数 | **0**（07-30 ~ 08-06 全程 restartCount = 0） | Prometheus `kube_pod_container_status_restarts_total` |
| ElastiCache 侧 | `cache.t4g.micro`，2 节点，`PendingModifiedValues` 为空，近 14 天无变更事件 | `describe-replication-groups` / `describe-events` |

**含义**：本周连接数下降（p95 1581 → 1410）**不是配置改动带来的**，更可能是上游调用量变化。**上周判定的「应用侧连接池未及时释放」这一结构性问题仍然存在**（连接数仍在 1400 量级做锯齿），只是当前峰值退到了 32MB 缓冲阈值以下，所以告警不再触发。建议仍按上期待办跟进。

> **结论（≤80字）**：两组「矛盾」数字其实都对、且同源，差异全部来自看板窗口随运行日漂移。真实情况：MySQL 连接数 07-28 阶跃后平稳，Redis 连接数环比**下降** 10.8%。建议改用 CloudWatch + 报告窗口，并加口径脚注。

---

## 附：本次采集用到的命令 / 查询清单（全部只读）

| 用途 | 命令 / 查询 |
|---|---|
| 告警原始行 | `python3 alert-mailserver/scripts/alert_report.py --start 2026-07-23 --end 2026-08-06 --dump … --zeus-dump …`（内部为 SELECT） |
| 连接来源分解 | `SELECT USER, SUBSTRING_INDEX(HOST,':',1), DB, COMMAND, COUNT(*) FROM information_schema.PROCESSLIST GROUP BY …` @ aws-luckyus-devops-rw |
| 连接数上限/峰值 | `SELECT … FROM performance_schema.global_variables / global_status`；`performance_schema.hosts` |
| 主机名解析 | `aws ec2 describe-instances --filters Name=private-ip-address,Values=10.238.3.178` |
| 连接数曲线 | CloudWatch `AWS/RDS DatabaseConnections`（Maximum，5min） |
| Pod spec / 重启数 | `manage_k8s_resource(read, Pod)`；Prometheus `kube_pod_container_status_restarts_total` |
| 容器内存峰值 | Prometheus `max_over_time(container_memory_working_set_bytes[7d])` |
| RDS 版本 / 扩展支持 | `aws rds describe-db-instances`；`check-extended-support-status.sh`（只读） |
| RDS 事件 | `aws rds describe-events --duration 11520 / 20160` |
| ElastiCache | `aws elasticache describe-events / describe-replication-groups / describe-cache-clusters` |
| Redis 连接数真值 | CloudWatch `AWS/ElastiCache CurrConnections`（Maximum + p95） |
| 看板口径 | `get_dashboard_property(uid=4jhaMqDDk, jsonPath=$.panels[*].targets[*])`（**只读**） |
| 采集表复现 | `SELECT … FROM luckyus_db_collection.t_dba_collect_rds_metrics_daily / t_dba_collect_redis_group_info` @ aws-luckyus-ldas01-rw |
| 计费 | `aws ce get-cost-and-usage`（1 次调用，$0.01） |

**未取到的项（周报请标注为待跟进）**：
1. meta-platform-rel 本周 18 次重启的**逐次 exitCode**（k8s 只保留 lastState）
2. lauthservice01 那 500 条连接的**客户端程序名**（`performance_schema.session_connect_attrs` 无记录）
3. 本周基础设施变更的**LSOP 工单号**（均为 AWS 侧事件，本地无关联工单）
4. LSOP 工具**线上容器的执行记录**（部署在他机，本环境无 docker）
5. 采集表 `data_date` 的时区**声明**（已用算术反推为 UTC，但无字段/文档直证）
