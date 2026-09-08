# 告警缺失分析报告 / Missing Alert Root Cause Report

## 【无告警】iluckydpbi03-prod-usa-aws 主机死机17小时，Zeus全程零告警

| Field | Value |
|-------|-------|
| **Incident ID** | INC-20260907-DPBI03-NOALERT |
| **Host / 主机** | iluckydpbi03-prod-usa-aws |
| **Instance ID** | i-04b4ad1b0469397da |
| **Private IP** | 10.238.65.5 |
| **Instance Type** | r6i.4xlarge |
| **Application / service label** | iluckydpbi（BigDataPlatform，`service_level=off_line`） |
| **Environment** | Production |
| **故障发现方式** | 人工发现（非告警触发），peng.chen03 于09-08 03:42 UTC 通过Console手动重启 |
| **Report Time** | 2026-09-08T15:22:56Z |
| **Author** | David Zeng (曾翔宇) |

---

## 1. 结论摘要 / Executive Summary

- 主机于 **2026-09-07 10:45 UTC** 起完全无响应（SSH/应用/node_exporter全部失联），持续约 **17小时**，直到 09-08 03:42 UTC 才被人工发现并通过Console重启恢复。期间**Zeus告警平台零告警**，CloudWatch原生Alarm也**零配置**。
- 根因已定位到具体策略配置：Zeus的两条通用"VM宕机"P0策略，一条**把这台机器的service标签显式排除在监控范围外**，另一条的判定逻辑存在盲区，两条都没能触发。
- 主机死机本身的操作系统级触发原因（OOM/panic/其它）**未能确认**——由于09-08 03:45 UTC那次"重启→强制断电(skipOsShutdown=true)→开机"的处置流程跳过了正常关机，崩溃现场的journal日志被标记为损坏并重命名保留在磁盘上，但排查权限不够（当前登录账号不在sudoers，AWS侧`databasecheck`账号也没有`GetConsoleOutput`/`SSM`权限），未继续深挖，作为遗留待办列在第5节。

---

## 2. 故障时间线 / Timeline（UTC）

```
09-07 00:00-09:00   NetworkOut明显放量（最高5.6MB/h vs 平时22KB/h），
                     符合夜间BI批处理/ETL特征

09-07 10:45         🔴 StatusCheckFailed_Instance = 1（AWS原生状态检查首次失败）
                     NetworkOut同时归零；StatusCheckFailed_System全程=0
                     （说明是Guest OS层面死机，非AWS宿主机/硬件故障）
                     Prometheus up{job="node-metrics"} 同时段变为0

09-07 10:45→09-08 03:40   持续死机，NetworkIn仍有~19.6KB/15min的探测流量
                          （外部一直在探测，主机完全不回包）
                          Prometheus up{job="node-ping-iprod"}（ICMP探活）
                          全程仍为1 —— 内核网络栈还能答ICMP，但TCP层
                          （SSH/应用/node_exporter）全部无响应

09-08 03:42:16      peng.chen03 通过AWS Console手动 RebootInstances

09-08 03:45:39      peng.chen03 StopInstances(skipOsShutdown=true)
                     —— 跳过OS正常关机，直接断电

09-08 03:45:57      peng.chen03 StartInstances，主机重新拉起
                     journald检测到system.journal未正常关闭，
                     标记corrupted并重命名保留

09-08 03:45→现在     StatusCheckFailed_Instance恢复=0，
                     CPU/网络/EBS指标均正常，未再复现
```

**整个17小时窗口内，Zeus `t_alert` 表中查无任何提及该IP/主机名/实例ID的记录，查无任何EC2/host级别的infra告警。**

---

## 3. 告警缺失根因分析 / Alerting Gap Root Cause

### 3.1 Zeus现有的两条通用"VM宕机"策略

| 策略ID | 名称 | alert_level（实际配置） | 表达式 | 状态 |
|---|---|---|---|---|
| #66 | 【vm-全局】P0 监控心跳丢失，且ping不可达，设备宕机 | 实际为 **P2**（与策略名称不符） | `(probe_success{} + on(ip) group_left(endpoint) up{simpleEnv="prod",system="Linux",service!~"isslvpn\|nclbvip\|rm-apiserver\|idoris"}) ==0` | ENABLE |
| #76 | 【vm-宕机】P0 up监控指标心跳丢失5分钟 | P0 | `up{service!~"isslvpn\|nclbvip\|idoris\|idpcd\|lfetools\|iluckydpbi",ip!~"",job!~'kubelet'}==0` | ENABLE |

### 3.2 为什么两条都没触发

**策略#76**：表达式的排除正则里**显式包含 `iluckydpbi`**，即这台机器所属service被硬编码排除在P0宕机检测之外。查了`t_alert_strategy_history`，这条排除从可查到的最早版本（2026-04-09，备注"旧版告警策略id=43迁移"）起就已存在，是长期的、非近期误改的配置，同批被排除的还有isslvpn/nclbvip/idoris/idpcd/lfetools——推测是当年为避免"这类允许计划性启停的机器"造成误报而拉黑，但从未给iluckydpbi补建替代告警。**结果：这台机器无论宕机多久，策略#76永远不会响。**

**策略#66**：没有按service名单排除iluckydpbi，但要求 `probe_success`（ICMP探活）与 `up`（exporter探活）**同时**为0才判定宕机。本次故障中：
- `up{job="node-metrics", instance="10.238.65.5:10087"}`（真实node_exporter探活）：整个17小时窗口**持续为0**
- `up{job="node-ping-iprod", instance="10.238.65.5"}`（ICMP ping探活）：整个17小时窗口**持续为1**

内核网络栈深度hang但没有完全断网，ICMP还能答，TCP层全死——这种"半死"状态下两个信号相加≠0，策略#66的判定逻辑判断不出来。**这是一个通用的检测盲区，不只影响这台机器，任何出现同类"半死"故障的主机都会被这条策略漏判。**

### 3.3 覆盖面核查

- Zeus全库搜索未发现任何专门针对iluckydpbi/dpbi/BigDataPlatform的替代告警策略。
- 该实例**未挂载任何CloudWatch Alarm**（`describe-alarms`按InstanceId过滤零命中），AWS原生侧也没有兜底。
- 该实例**未挂载IAM Instance Profile**，即便未来给databasecheck或其他账号开通SSM权限，Session Manager也无法对这台机器生效，需要先补挂Profile。

---

## 4. 已完成的调查动作 / Actions Taken

| # | 动作 | 结果 |
|---|------|------|
| 1 | AWS CLI定位实例、状态检查、CPU/网络/EBS指标 | 当前健康；死机窗口=09-07 10:45→09-08 03:40 |
| 2 | CloudTrail查该实例事件 | 确认peng.chen03的reboot→强制stop→start三连操作 |
| 3 | 查CloudWatch Alarm | 该实例零告警配置 |
| 4 | 查IAM Instance Profile | 未挂载，SSM当前不可用 |
| 5 | 查Zeus `t_alert`表 | 死机窗口内零告警记录 |
| 6 | 查Zeus策略配置与变更历史 | 定位到#76排除名单与#66判定逻辑两处根因（详见3.2） |
| 7 | 查Prometheus `up{}`双信号 | 证实node-metrics与node-ping两路探活结果矛盾 |
| 8 | 尝试SSH登录主机排查OS级根因 | 需经指定跳板机(10.238.3.67/10.238.3.141等)，dbtools02不在白名单，后改用跳板成功登录 |
| 9 | 尝试读取崩溃现场journal（已重命名的corrupted文件 `system@00065af092f30168-69353149a1a45f6a.journal~`） | 当前账号无sudo权限，**未完成**，作为遗留待办 |

---

## 5. 后续改进 / Follow-up Action Items

### P0 — 尽快评估

| # | 事项 | 说明 |
|---|------|------|
| 1 | 决定iluckydpbi是否该从策略#76排除名单移除，或为其单独建一条P0/P1告警 | 需先确认当年排除的原始意图（是否有计划性启停），避免移除后产生新的误报噪音 |
| 2 | 评估策略#66"ping+exporter双信号AND"逻辑的检测盲区 | 这次是"exporter死、ICMP活"的组合漏判，非iluckydpbi独有，建议排查是否有其它机器有相同风险 |

### P1 — 一周内

| # | 事项 | 说明 |
|---|------|------|
| 3 | 给该实例挂载CloudWatch Alarm（至少StatusCheckFailed）作为Zeus之外的兜底 | 当前零配置 |
| 4 | 给该实例挂载IAM Instance Profile（含SSM权限）| 目前无法用Session Manager应急登录 |
| 5 | 核实journald持久化存储配置（`/etc/systemd/journald.conf` 的 `Storage=`） | 本次强制断电导致journal标记corrupted，若配置得当可减少下次类似情况的日志丢失风险 |

### P2 — 遗留待办（非本报告范围，待有权限人员跟进）

| # | 事项 | 说明 |
|---|------|------|
| 6 | 死机操作系统级根因排查 | 崩溃现场journal文件（`system@00065af092f30168-69353149a1a45f6a.journal~`，33MB，时间戳与断电时刻吻合）大概率仍完整保留在磁盘，需要root权限读取并核对OOM/panic/hung task痕迹，时间窗聚焦09-07 10:30-11:00 UTC |

---

## 6. 技术证据 / Technical Evidence

```
实例信息:
  Instance ID:     i-04b4ad1b0469397da
  Name:            iluckydpbi03-prod-usa-aws
  Private IP:      10.238.65.5
  Type:            r6i.4xlarge
  Security Group:  sg_bi_prod (SSH仅允许JumpServer前缀列表 pl-0486531655c2620e2)
  IAM Profile:     无

Zeus策略#76表达式:
  up{service!~"isslvpn|nclbvip|idoris|idpcd|lfetools|iluckydpbi",ip!~"",job!~'kubelet'}==0
  (duration=5m, alert_level=P0, status=ENABLE)
  排除名单最早可查记录: 2026-04-09（备注"旧版告警策略id=43迁移"）

Zeus策略#66表达式:
  (probe_success{} + on(ip) group_left(endpoint) up{simpleEnv="prod",system="Linux",
   service!~"isslvpn|nclbvip|rm-apiserver|idoris"}) ==0
  (duration=1m, alert_level=P2, status=ENABLE)

Prometheus up{} 双信号对比（09-07 10:45 → 09-08 03:40 UTC）:
  job=node-metrics,  instance=10.238.65.5:10087   → 持续 0（真实exporter失联）
  job=node-ping-iprod, instance=10.238.65.5       → 持续 1（ICMP仍可达）

CloudTrail关键事件:
  03:42:16  RebootInstances       peng.chen03  source_ip=104.251.225.59
  03:45:39  StopInstances(skipOsShutdown=true)  peng.chen03
  03:45:57  StartInstances        peng.chen03
```

---

*报告生成时间: 2026-09-08T15:22:56Z*
*本报告聚焦"为什么没有告警"，主机死机的操作系统级根因排查因权限不足暂停，见第5节P2遗留待办*
