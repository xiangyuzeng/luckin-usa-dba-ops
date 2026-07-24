# RDS 扩展支持（Extended Support）分级开启包

> 生成日期：2026-07-24 ｜ AWS 账户：257394478466 / us-east-1 ｜ 申请 DBA：曾翔宇 (David Zeng)
> 来源分级：`mysql-8.4.9-upgrade-tracker`（跟踪表 2），按实例内最高业务等级归纳为实例级 L0/L1/L2。

## 目标

为生产 RDS MySQL 实例设置 `EngineLifecycleSupport = open-source-rds-extended-support`，
**提前锁定扩展支持偏好**，使得所在 MySQL 大版本到达 RDS 标准支持终止日时，AWS 不会执行**强制自动大版本升级**——把升级时机控制权保留在 DBA 手中，避免以后被动升级引发故障。

## ⚠️ 现场前提（务必知悉）

跟踪表(2)（2026-06-03）记录 59 个实例待从 8.0.45 升级到 8.4.9；**但截至 2026-07-24 这些实例已全部升级到 8.4.9 / 8.4.10**。因此：

- 本次目标 = **所有生产 MySQL 实例，排除**蓝绿部署遗留原库（`*-rw-old1`）与测试/验证机（`swqtest*`、`ldasverify*`、`*dba84*`）。
- **当前增量成本 = $0**：扩展支持费用只在大版本过了标准支持终止日后才按 vCPU·小时计费；8.4 标准支持还有数年。现在开启只是设置未来偏好。
- 该偏好可随时**无停机回退**。

## 分级与范围（62 个实例）

| 等级 | 含义 | 实例数 | vCPU | 执行顺序 | 未来参考成本¹ | 工单 |
|------|------|--------|------|----------|---------------|------|
| **L2** | 普通业务 / 基础设施 | 10 | 20 | 首批（灰度） | ~$1,460/月 | [ticket-L2.md](ticket-L2.md) |
| **L1** | 重要业务服务 | 36 | 72 | 第二批 | ~$5,256/月 | [ticket-L1.md](ticket-L1.md) |
| **L0** | 核心业务服务 | 16 | 36 | 最后（会签） | ~$2,628/月 | [ticket-L0.md](ticket-L0.md) |
| 合计 | | **62** | **128** | | ~$9,344/月 | |

¹ 未来参考成本仅当 8.4 进入扩展支持期（约 2032 后）才可能发生，按 Yr1–2 费率 $0.100/vCPU·小时估算；届时若已升级到更高 LTS 则永不产生。

完整分级清单见 [`extended_support_targets.csv`](extended_support_targets.csv)。

### 排除清单（12 个，不在本次范围）

- 蓝绿遗留原库（9，待删除清理）：`cdpactivity/iluckyams/isalescdp/isalescouponservice/isalesprivatedomain/salesmarketing/salesorder/salespayment/swqtest8045` 的 `-rw-old1`
- 测试 / 验证机（3）：`ldasverify01-rw`、`ldasverify02-rw`、`swqtest8045-rw`

### 跟踪表(2)未收录、由研发确认级别（2026-07-24）

| 实例 | 级别 | 说明 |
|------|------|------|
| `aws-luckyus-isalescouponservice-rw` | L0 | 券服务，研发确认 |
| `aws-luckyus-ibehr-rw` | L1 | eHR，研发确认 |
| `aws-luckyus-iluckyams-rw` | L2 | 研发确认 |

## 交付物

| 文件 | 用途 |
|------|------|
| `ticket-L0.md` / `ticket-L1.md` / `ticket-L2.md` | 分级变更工单，走审批流程 |
| `scripts/enable-extended-support-L0.sh` / `-L1.sh` / `-L2.sh` | 分级批量开启脚本（默认 dry-run，`--apply` 执行） |
| `scripts/check-extended-support-status.sh` | 全量 RDS 扩展支持状态检查（只读） |
| `scripts/_common.sh` | 开启脚本共享逻辑 |
| `extended_support_targets.csv` | 权威分级清单（62 实例） |

## 执行流程

```bash
cd scripts/

# 0) 现状核对（只读）
./check-extended-support-status.sh --only-disabled --csv before.csv

# 1) 预演（默认 dry-run，改不了任何东西）
./enable-extended-support-L2.sh          # 逐级预演

# 2) 工单审批通过后，按 L2 -> L1 -> L0 顺序执行
./enable-extended-support-L2.sh --apply
#   验证后再 L1、最后 L0
./enable-extended-support-L1.sh --apply
./enable-extended-support-L0.sh --apply

# 3) 收尾核对：应无本批实例仍为 disabled
./check-extended-support-status.sh --only-disabled
```

## 变更特性 / 安全

- **无停机、无重启、无 failover**：`EngineLifecycleSupport` 是计费/生命周期偏好，`modify-db-instance` 立即生效，不触及数据面。
- **幂等**：已开启的实例自动跳过（`[ALDY]`）。
- **范围锁定**：每个脚本内置固定实例清单，不做通配匹配；找不到 / 非 mysql / 非本清单实例一律跳过。
- **可回退**：`--engine-lifecycle-support open-source-rds-extended-support-disabled` 同样无停机。
- **审计**：每次执行写 `scripts/logs/enable-<level>-<ts>.log`，记录操作者 ARN 与逐实例结果。
- 权限：需 `rds:ModifyDBInstance`。`databasecheck` 若无该权限，`--apply` 会在 `[FAIL]` 处报 AccessDenied，需用具备变更权限的角色执行。
