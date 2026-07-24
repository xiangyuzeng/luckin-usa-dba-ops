# 变更工单 — RDS 扩展支持开启（L2 普通业务服务 / 基础设施）

| 字段 | 内容 |
|------|------|
| 工单标题 | 为 L2（普通业务服务 / 基础设施）10 个 RDS 实例开启 AWS Extended Support 偏好 |
| 变更类型 | 标准变更 / 配置项修改（无停机、无重启） |
| 优先级 / 审批 | P3 / DBA 主管审批(可作为首批灰度) |
| 申请人 | 曾翔宇 (David Zeng) — Senior DBA |
| 执行人 | DBA 值班 |
| AWS 账户 / 区域 | 257394478466 / us-east-1 |
| 影响实例数 | 10（20 vCPU） |
| 执行顺序 | 首批执行,作为灰度验证 |
| 计划窗口 | 待定（本变更无停机，可业务时段执行；建议错峰） |
| 回滚方式 | `modify-db-instance --engine-lifecycle-support open-source-rds-extended-support-disabled`（同样无停机，仅偏好回退） |

## 1. 变更目的

为该批实例设置 `EngineLifecycleSupport = open-source-rds-extended-support`（AWS RDS 扩展支持偏好）。
目的是**提前锁定扩展支持偏好**：当实例所在 MySQL 大版本走到 RDS 标准支持终止日时，AWS 不会对其执行**强制自动大版本升级**，把升级时机的控制权保留在 DBA 手中，避免未来被动升级引发故障。

## 2. 成本影响

- **当前增量成本 = $0**。本批实例现均运行 MySQL 8.4（仍在标准支持期内），扩展支持费用只在大版本**过了标准支持终止日之后**才开始按 vCPU·小时计费。
- **未来参考成本**（仅当 8.4 进入扩展支持期、约 2032 年后才可能发生，按 Yr1–2 费率 $0.100/vCPU·小时估算）：本批 20 vCPU ≈ **$1,460/月**。到期前若已升级到更高 LTS，则永不产生此费用。
- 该偏好可随时无停机回退，不构成长期财务承诺。

## 3. 变更内容与风险

- 操作：对每个实例执行 `aws rds modify-db-instance --db-instance-identifier <id> --engine-lifecycle-support open-source-rds-extended-support --apply-immediately`。
- **无停机、无重启、无 failover**：`EngineLifecycleSupport` 为计费/生命周期偏好项，修改立即生效，不触及数据面。
- 幂等：已开启的实例脚本自动跳过。
- 风险等级：低。主要风险为误操作实例范围 —— 已通过脚本内置固定清单 + dry-run 预演规避。

## 4. 执行脚本

- 预演（默认，只读不改）：`./scripts/enable-extended-support-L2.sh`
- 正式执行：`./scripts/enable-extended-support-L2.sh --apply`
- 执行后核对：`./scripts/check-extended-support-status.sh --only-disabled`（本批应不再出现在列表中）

## 5. 影响实例明细（L2，10 个）

| # | db_instance_identifier | 实例简称 | 当前版本 | 规格 | 当前扩展支持 | 分级来源 |
|---|------------------------|----------|----------|------|--------------|----------|
| 1 | `aws-luckyus-fichargecontrol-rw` | fichargecontrol | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 2 | `aws-luckyus-ifiaccounting-rw` | ifiaccounting | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 3 | `aws-luckyus-ilsopdevopsdata-rw` | ilsopdevopsdata | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 4 | `aws-luckyus-iluckyams-rw` | iluckyams | 8.4.10 | db.t4g.micro | 未开启 | 研发确认 |
| 5 | `aws-luckyus-iluckydorisops-rw` | iluckydorisops | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 6 | `aws-luckyus-iluckyhealth-rw` | iluckyhealth | 8.4.9 | db.t3.small | 未开启 | 跟踪表(2) |
| 7 | `aws-luckyus-iopocp-rw` | iopocp | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 8 | `aws-luckyus-oplog-rw` | oplog | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 9 | `aws-luckyus-opqualitycontrol-rw` | opqualitycontrol | 8.4.9 | db.t4g.medium | 未开启 | 跟踪表(2) |
| 10 | `aws-luckyus-scm-wmssimulate-rw` | scm-wmssimulate | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |

## 6. 审批签字

| 角色 | 姓名 | 意见 | 日期 |
|------|------|------|------|
| 申请 DBA | 曾翔宇 | | |
| DBA 主管 | | | |
