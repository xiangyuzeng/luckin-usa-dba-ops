# MySQL 8.0.45 → 8.4.9 升级跟踪表

> **生成日期**：2026-06-03 ｜ **当前版本（全车队已统一）**：8.0.45 ｜ **目标版本**：8.4.9（8.4 LTS）
> **实例总数**：59 ｜ **AWS 账户**：257394478466 / us-east-1
> 数据库大小为 2026-06-03 经 mcp-db-gateway `information_schema` 实时刷新（ilsopdevopsdata 未经网关暴露，沿用 5 月基线）。
> 规格 / 内存 / 可用内存 / Swap 沿用 2026-04~05 月 8.0.45 升级跟踪基线（机型未变；可用内存/Swap 为 CloudWatch 时点快照）。

## ⚠️ 这是一次「大版本」升级，与 8.0.41→8.0.45 小版本升级有本质区别

8.0 → 8.4 是 RDS MySQL 的 **major version upgrade**，必须按大版本流程处理。以下为升级前必做的兼容性核查（每个实例都要过）：

| # | 检查项 | 说明 |
|---|--------|------|
| 1 | **mysql_native_password 认证插件** | 8.4 中该插件默认 **disabled**（`--mysql-native-password=OFF`）。升级前必须审计 `mysql.user` 中 `plugin='mysql_native_password'` 的账号并迁移到 `caching_sha2_password`，否则应用连接会失败。鉴权/核心库（devops、iluckyauthapi、ipermission、salescrm 等）尤其重点。 |
| 2 | **新建 mysql8.4 参数组** | 不能复用 8.0 family 参数组；需为每实例建 `mysql8.4` family 参数组。**`lower_case_table_names` 创建后不可改**——8.0.45 升级时 `luckyus-prod` 参数组就因缺该项导致 ldas 多次部署失败，本轮务必先对齐。 |
| 3 | **已移除/重命名的系统变量** | 8.4 移除了多个 8.0 中已弃用的变量（如部分 `innodb_*`、复制相关、`expire_logs_days` 等）。自定义参数组需逐项核对，移除已废弃项后再创建。 |
| 4 | **RDS 升级前置预检（pre-upgrade check）** | RDS 大版本升级会自动跑 pre-check；提前用 blue/green 或测试实例（`dba84test`）跑一遍，查看 `PrePatchCompatibility` / 升级预检日志中的不兼容项与孤立表/分区。 |
| 5 | **蓝绿部署（Blue/Green Deployment）** | 8.0→8.4 支持蓝绿。L0/L1 强烈建议走蓝绿：绿环境先升 8.4 验证、回切风险可控、切换窗口短。原库与蓝绿环境的清理需登记在「原库及蓝绿部署清理」列。 |
| 6 | **应用驱动兼容性** | 确认 JDBC / 各语言 connector 版本支持 `caching_sha2_password`（旧驱动需 RSA 公钥或 SSL）。Nacos（framework01）、鉴权服务为重点。 |
| 7 | **内存压力** | 升级中 RDS 执行 Multi-AZ 故障转移，短暂增加内存压力。当前 **39 个实例可用内存 < 150MB（风险「高」，全部为 db.t4g.micro 1GB 机型的长期状态）**。先例：iluckyams 曾在 83–148MB 可用内存下成功完成自动升级；isalescdp 曾于 3/12 发生 OOM/failover，需重点关注。 |

## 升级批次（沿用 8.0.45 升级的风险分级顺序：基础/普通服务先行，L0 核心最后）

| 批次 | 实例数 | 说明 |
|------|--------|------|
| 第1批 | 12 | 基础服务 / 大数据（ldas、devops、framework、upush、iotplatform 等） |
| 第2批 | 6 | L2 普通业务服务（scm-wmssimulate、fichargecontrol、iopocp 等） |
| 第3批 | 27 | L1 重要业务服务（公共平台 / 供应链 / 运营 / 营销，含 1 个 L0 iriskcontrol） |
| 第4批 | 14 | L0 核心业务服务（支付、订单、CRM、CDP、shopstock 等），逐个升级、全面验证 |

> **计划日期 / 操作人**：本轮均为「待定」，待大版本预检通过、参数组与认证插件迁移方案确认后再排期。

## 实例明细（59 实例）

| # | 实例 | 服务等级 | 当前→目标 | 规格 | 内存GB | 可用MB | Swap MB | 风险¹ | 数据库大小 | 业务分组 | 批次 | 状态 | 备注 |
|---|------|----------|-----------|------|-------|--------|---------|------|-----------|----------|------|------|------|
| 1 | ldas01 | L2<br>L1<br>L2 | 8.0.45→8.4.9 | db.t4g.large | 8 | 649 | 219 | 低 | 127.64 GB | 架构<br>运维 | 第1批 | 未开始 | 原 8.0.41，已随车队升至 8.0.45；major 升级需新建 mysql8.4 参数组 |
| 2 | ilsopdevopsdata | L2 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 116 | 375 | 高 | 20.00 MB | 质量效能 | 第1批 | 未开始 | 大小为 5月基线（未经 gateway 暴露，未刷新） |
| 3 | iluckyhealth | L2 | 8.0.45→8.4.9 | db.t3.small | 2 | 66 | 868 | 高 | 34.66 GB | 运维 | 第1批 | 未开始 | 可用内存仅 66MB，车队最低；major 升级 Multi-AZ failover 内存压力风险高 |
| 4 | ldas | L1<br>L1<br>L2<br>L2 | 8.0.45→8.4.9 | db.t4g.large | 8 | 1065 | 327 | 低 | 1.58 GB | 架构<br>运维 | 第1批 | 未开始 | 8.0.45 升级曾多次部署失败、参数组缺 lower_case_table_names；8.4 必须新建 mysql8.4 参数组且 lctn 创建后不可改 |
| 5 | ijumpserver | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 96 | 627 | 高 | 153.58 MB | 信息安全 | 第1批 | 未开始 | — |
| 6 | devops | L1<br>L2 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 1604 | 9 | 低 | 343.14 MB | 质量效能<br>运维 | 第1批 | 未开始 | 存储 gp2；含 uam/auth 鉴权库 —— 重点核查 mysql_native_password 用户 |
| 7 | framework01 | L1<br>L2 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 1601 | 32 | 低 | 511.50 MB | 架构 | 第1批 | 未开始 | 12 库 283 表；含 Nacos 配置中心 —— 升级期间确认配置中心连接驱动兼容 caching_sha2_password |
| 8 | framework02 | L2<br>L1 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 997 | 88 | 低 | 3.32 GB | 架构 | 第1批 | 未开始 | — |
| 9 | upush | L1 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 256 | 335 | 中 | 20.11 GB | 架构 | 第1批 | 未开始 | 可用内存偏低 256MB；上轮因 datalink 续传 binlog 问题暂缓，本轮蓝绿前需复核 |
| 10 | iotplatform | L1<br>L1<br>L1 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 1504 | 8 | 低 | 692.48 MB | AIot | 第1批 | 未开始 | 上轮因 datalink 续传 binlog 问题暂缓，本轮蓝绿前需复核 |
| 11 | icyberdata | L1 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 676 | 1423 | 低 | 26.11 GB | 大数据 | 第1批 | 未开始 | 最大存储 635GB；Swap 1423MB |
| 12 | iluckydorisops | L2 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 124 | 405 | 高 | 8.16 MB | 大数据 | 第1批 | 未开始 | — |
| 13 | scm-wmssimulate | L2 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 111 | 534 | 高 | 44.41 MB | 国际供应链 | 第2批 | 未开始 | — |
| 14 | fichargecontrol | L2 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 105 | 559 | 高 | 51.70 MB | 国际公共平台 | 第2批 | 未开始 | — |
| 15 | ifiaccounting | L2 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 99 | 871 | 高 | 323.23 MB | 国际公共平台 | 第2批 | 未开始 | — |
| 16 | iopocp | L2 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 96 | 622 | 高 | 2.17 GB | 国际运营 | 第2批 | 未开始 | — |
| 17 | opqualitycontrol | L2 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 90 | 754 | 高 | 707.34 MB | 国际运营 | 第2批 | 未开始 | — |
| 18 | oplog | L2 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 110 | 410 | 高 | 8.13 MB | 国际运营 | 第2批 | 未开始 | — |
| 19 | iadmin | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 113 | 511 | 高 | 129.11 MB | 国际公共平台 | 第3批 | 未开始 | — |
| 20 | ibizconfigcenter | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 116 | 435 | 高 | 32.55 MB | 国际公共平台 | 第3批 | 未开始 | — |
| 21 | igers | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 118 | 401 | 高 | 8.22 MB | 国际公共平台 | 第3批 | 未开始 | — |
| 22 | iluckyauthapi | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 112 | 408 | 高 | 8.06 MB | 国际公共平台 | 第3批 | 未开始 | 鉴权服务 —— 重点核查 mysql_native_password 用户与连接驱动 |
| 23 | ibillingcentersrv | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 104 | 670 | 高 | 1.76 GB | 国际公共平台 | 第3批 | 未开始 | — |
| 24 | iehr | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 109 | 554 | 高 | 40.64 MB | 国际公共平台 | 第3批 | 未开始 | — |
| 25 | iopenlinker | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 117 | 493 | 高 | 124.00 MB | 国际营销增长 | 第3批 | 未开始 | — |
| 26 | iopenservice | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 120 | 408 | 高 | 8.34 MB | 国际公共平台 | 第3批 | 未开始 | — |
| 27 | iopshopexpand | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 115 | 423 | 高 | 8.86 MB | 国际运营 | 第3批 | 未开始 | — |
| 28 | iunifiedreconcile | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 126 | 426 | 高 | 11.92 MB | 国际公共平台 | 第3批 | 未开始 | — |
| 29 | mfranchise | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 122 | 457 | 高 | 10.67 MB | 国际公共平台 | 第3批 | 未开始 | — |
| 30 | iworkflowmidlayer | L1<br>L1 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 525 | 218 | 低 | 6.29 GB | 国际公共平台 | 第3批 | 未开始 | 1/31 发生过 innodb_buffer_pool_size 被缩减事故，升级后必须验证 buffer pool 配置 |
| 31 | scm-asset | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 108 | 594 | 高 | 25.72 MB | 国际供应链 | 第3批 | 未开始 | — |
| 32 | scm-openapi | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 116 | 577 | 高 | 165.69 MB | 国际供应链 | 第3批 | 未开始 | — |
| 33 | scm-plan | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 119 | 472 | 高 | 13.03 MB | 国际供应链 | 第3批 | 未开始 | — |
| 34 | scm-ordering | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 90 | 771 | 高 | 513.42 MB | 国际供应链 | 第3批 | 未开始 | — |
| 35 | scm-purchase | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 101 | 799 | 高 | 159.84 MB | 国际供应链 | 第3批 | 未开始 | — |
| 36 | scm-wds | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 102 | 720 | 高 | 214.83 MB | 国际供应链 | 第3批 | 未开始 | — |
| 37 | scmsrm | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 104 | 733 | 高 | 125.89 MB | 国际供应链 | 第3批 | 未开始 | — |
| 38 | pubdm | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 109 | 511 | 高 | 16.81 MB | 国际供应链 | 第3批 | 未开始 | — |
| 39 | iopenadmin | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 123 | 419 | 高 | 8.66 MB | 国际供应链 | 第3批 | 未开始 | — |
| 40 | ireplenishment | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 119 | 647 | 高 | 1.93 GB | 供应链算法 | 第3批 | 未开始 | — |
| 41 | opempefficiency | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 101 | 546 | 高 | 117.27 MB | 国际运营 | 第3批 | 未开始 | — |
| 42 | iluckymedia | L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 120 | 416 | 高 | 8.83 MB | 国际运营 | 第3批 | 未开始 | — |
| 43 | isalesmembermarketing | L2<br>L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 115 | 425 | 高 | 8.97 MB | 国际营销增长 | 第3批 | 未开始 | — |
| 44 | isalesdatamarketing | L1<br>L1 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 666 | 490 | 低 | 9.47 GB | 国际营销增长 | 第3批 | 未开始 | — |
| 45 | iriskcontrolservice | L0 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 94 | 1207 | 高 | 23.59 GB | 信息安全 | 第3批 | 未开始 | Swap 最高 1207MB；L0 核心，1GB 机型承载 23.6GB 数据，蓝绿期间内存压力高 |
| 46 | ipermission | L0<br>L1 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 96 | 591 | 高 | 99.61 MB | 国际公共平台 | 第4批 | 未开始 | L0 鉴权 —— 重点核查 mysql_native_password 用户 |
| 47 | fitax | L0 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 119 | 393 | 高 | 8.67 MB | 国际公共平台 | 第4批 | 未开始 | — |
| 48 | scm-shopstock | L1<br>L0 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 466 | 325 | 低 | 8.11 GB | 国际供应链 | 第4批 | 未开始 | — |
| 49 | scmcommodity | L1<br>L0 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 2057 | 0 | 低 | 199.91 MB | 国际供应链 | 第4批 | 未开始 | — |
| 50 | opproduction | L0 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 90 | 594 | 高 | 5.80 GB | 国际运营 | 第4批 | 未开始 | L0 核心，1GB 机型承载 5.8GB 数据 |
| 51 | opshopsale | L0 | 8.0.45→8.4.9 | db.t4g.micro | 1 | 83 | 658 | 高 | 304.28 MB | 国际运营 | 第4批 | 未开始 | 可用内存 83MB，车队偏低；L0 核心 |
| 52 | opshop | L0<br>L2 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 2254 | 0 | 低 | 40.53 MB | 国际运营 | 第4批 | 未开始 | — |
| 53 | isalesprivatedomain | L2<br>L1<br>L0 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 661 | 135 | 低 | 2.64 GB | 国际营销增长 | 第4批 | 未开始 | — |
| 54 | salescrm | L0<br>L0<br>L0 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 1785 | 0 | 低 | 632.09 MB | 国际营销增长 | 第4批 | 未开始 | 全 L0 核心 |
| 55 | cdpactivity | L1<br>L0<br>L0 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 485 | 375 | 低 | 18.19 GB | 国际营销增长 | 第4批 | 未开始 | — |
| 56 | isalescdp | L1<br>L0 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 993 | 0 | 低 | 2.69 GB | 国际营销增长 | 第4批 | 未开始 | 3/12 发生过 OOM/Multi-AZ 故障转移事故，升级后扩展验证 |
| 57 | salesmarketing | L1<br>L0<br>L0 | 8.0.45→8.4.9 | db.t4g.xlarge | 16 | 1509 | 204 | 低 | 25.20 GB | 国际营销增长 | 第4批 | 未开始 | 车队最大实例 xlarge 16GB；大小由 46GB→25GB（疑似清理/binlog 回收）；最后升级、全面验证 |
| 58 | salespayment | L0<br>L1 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 1687 | 0 | 低 | 793.06 MB | 国际营销增长 | 第4批 | 未开始 | 核心支付系统，逐个升级、单独蓝绿 |
| 59 | salesorder | L0<br>L2<br>L0<br>L0 | 8.0.45→8.4.9 | db.t4g.medium | 4 | 421 | 218 | 低 | 5.82 GB | 国际营销增长 | 第4批 | 未开始 | 核心订单系统；升级后必须验证 group_concat_max_len = 1048576 |

## 汇总统计

| 指标 | 值 |
|------|-----|
| 必须升级 | 59 |
| 已完成 | 0 |
| 完成率 | 0.0% |
| 可用内存「高」风险（<150MB） | 39 |
| 可用内存「中」风险（150–300MB） | 1 |
| 可用内存「低」风险（>300MB） | 19 |

**机型分布**：db.t4g.micro × 38、db.t4g.medium × 17、db.t4g.large × 2、db.t4g.xlarge × 1、db.t3.small × 1

---
¹ **内存风险**：升级过程中 RDS 执行 Multi-AZ 故障转移，短暂增加内存压力。「高」= 可用内存 < 150MB（全部为 db.t4g.micro 1GB 机型长期运行状态，非升级引入的新风险）；「中」= 150–300MB；「低」= > 300MB。

> 完整可编辑跟踪表见同目录 `mysql_8.4.9_upgrade_tracker.csv`（21 列，含数据库列表 / 关联服务 / 研发负责人 / 操作人 / 计划日期 / 原库及蓝绿清理 等）。
