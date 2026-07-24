# 变更工单 — RDS 扩展支持开启（L1 重要业务服务）

| 字段 | 内容 |
|------|------|
| 工单标题 | 为 L1（重要业务服务）36 个 RDS 实例开启 AWS Extended Support 偏好 |
| 变更类型 | 标准变更 / 配置项修改（无停机、无重启） |
| 优先级 / 审批 | P2 / 变更评审 + DBA 主管审批 |
| 申请人 | 曾翔宇 (David Zeng) — Senior DBA |
| 执行人 | DBA 值班 |
| AWS 账户 / 区域 | 257394478466 / us-east-1 |
| 影响实例数 | 36（72 vCPU） |
| 执行顺序 | L2 灰度验证通过后执行 |
| 计划窗口 | 待定（本变更无停机，可业务时段执行；建议错峰） |
| 回滚方式 | `modify-db-instance --engine-lifecycle-support open-source-rds-extended-support-disabled`（同样无停机，仅偏好回退） |

## 1. 变更目的

为该批实例设置 `EngineLifecycleSupport = open-source-rds-extended-support`（AWS RDS 扩展支持偏好）。
目的是**提前锁定扩展支持偏好**：当实例所在 MySQL 大版本走到 RDS 标准支持终止日时，AWS 不会对其执行**强制自动大版本升级**，把升级时机的控制权保留在 DBA 手中，避免未来被动升级引发故障。

## 2. 成本影响

- **当前增量成本 = $0**。本批实例现均运行 MySQL 8.4（仍在标准支持期内），扩展支持费用只在大版本**过了标准支持终止日之后**才开始按 vCPU·小时计费。
- **未来参考成本**（仅当 8.4 进入扩展支持期、约 2032 年后才可能发生，按 Yr1–2 费率 $0.100/vCPU·小时估算）：本批 72 vCPU ≈ **$5,256/月**。到期前若已升级到更高 LTS，则永不产生此费用。
- 该偏好可随时无停机回退，不构成长期财务承诺。

## 3. 变更内容与风险

- 操作：对每个实例执行 `aws rds modify-db-instance --db-instance-identifier <id> --engine-lifecycle-support open-source-rds-extended-support --apply-immediately`。
- **无停机、无重启、无 failover**：`EngineLifecycleSupport` 为计费/生命周期偏好项，修改立即生效，不触及数据面。
- 幂等：已开启的实例脚本自动跳过。
- 风险等级：低。主要风险为误操作实例范围 —— 已通过脚本内置固定清单 + dry-run 预演规避。

## 4. 执行脚本

- 预演（默认，只读不改）：`./scripts/enable-extended-support-L1.sh`
- 正式执行：`./scripts/enable-extended-support-L1.sh --apply`
- 执行后核对：`./scripts/check-extended-support-status.sh --only-disabled`（本批应不再出现在列表中）

## 5. 影响实例明细（L1，36 个）

| # | db_instance_identifier | 实例简称 | 当前版本 | 规格 | 当前扩展支持 | 分级来源 |
|---|------------------------|----------|----------|------|--------------|----------|
| 1 | `aws-luckyus-devops-rw` | devops | 8.4.9 | db.t4g.medium | 未开启 | 跟踪表(2) |
| 2 | `aws-luckyus-framework01-rw` | framework01 | 8.4.9 | db.t4g.medium | 未开启 | 跟踪表(2) |
| 3 | `aws-luckyus-framework02-rw` | framework02 | 8.4.9 | db.t4g.medium | 未开启 | 跟踪表(2) |
| 4 | `aws-luckyus-iadmin-rw` | iadmin | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 5 | `aws-luckyus-ibehr-rw` | ibehr | 8.4.9 | db.t4g.micro | 未开启 | 研发确认 |
| 6 | `aws-luckyus-ibillingcentersrv-rw` | ibillingcentersrv | 8.4.9 | db.t4g.medium | 未开启 | 跟踪表(2) |
| 7 | `aws-luckyus-ibizconfigcenter-rw` | ibizconfigcenter | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 8 | `aws-luckyus-icyberdata-rw` | icyberdata | 8.4.10 | db.t4g.medium | 未开启 | 跟踪表(2) |
| 9 | `aws-luckyus-iehr-rw` | iehr | 8.4.9 | db.t4g.small | 未开启 | 跟踪表(2) |
| 10 | `aws-luckyus-igers-rw` | igers | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 11 | `aws-luckyus-ijumpserver-jumpserver-rw` | ijumpserver | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 12 | `aws-luckyus-iluckyauthapi-rw` | iluckyauthapi | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 13 | `aws-luckyus-iluckymedia-rw` | iluckymedia | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 14 | `aws-luckyus-iopenadmin-rw` | iopenadmin | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 15 | `aws-luckyus-iopenlinker-rw` | iopenlinker | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 16 | `aws-luckyus-iopenservice-rw` | iopenservice | 8.4.10 | db.t4g.small | 未开启 | 跟踪表(2) |
| 17 | `aws-luckyus-iopshopexpand-rw` | iopshopexpand | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 18 | `aws-luckyus-iotplatform-rw` | iotplatform | 8.4.9 | db.t4g.medium | 未开启 | 跟踪表(2) |
| 19 | `aws-luckyus-ireplenishment-rw` | ireplenishment | 8.4.10 | db.t4g.small | 未开启 | 跟踪表(2) |
| 20 | `aws-luckyus-isalesdatamarketing-rw` | isalesdatamarketing | 8.4.9 | db.t4g.medium | 未开启 | 跟踪表(2) |
| 21 | `aws-luckyus-isalesmembermarketing-rw` | isalesmembermarketing | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 22 | `aws-luckyus-iunifiedreconcile-rw` | iunifiedreconcile | 8.4.10 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 23 | `aws-luckyus-iworkflowmidlayer-rw` | iworkflowmidlayer | 8.4.10 | db.t4g.medium | 未开启 | 跟踪表(2) |
| 24 | `aws-luckyus-ldas-rw` | ldas | 8.4.9 | db.t4g.large | 未开启 | 跟踪表(2) |
| 25 | `aws-luckyus-ldas01-rw` | ldas01 | 8.4.9 | db.t4g.large | 未开启 | 跟踪表(2) |
| 26 | `aws-luckyus-mfranchise-rw` | mfranchise | 8.4.10 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 27 | `aws-luckyus-opempefficiency-rw` | opempefficiency | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 28 | `aws-luckyus-pubdm-rw` | pubdm | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 29 | `aws-luckyus-scm-asset-rw` | scm-asset | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 30 | `aws-luckyus-scm-openapi-rw` | scm-openapi | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 31 | `aws-luckyus-scm-ordering-rw` | scm-ordering | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 32 | `aws-luckyus-scm-plan-rw` | scm-plan | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 33 | `aws-luckyus-scm-purchase-rw` | scm-purchase | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 34 | `aws-luckyus-scm-wds-rw` | scm-wds | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 35 | `aws-luckyus-scmsrm-rw` | scmsrm | 8.4.9 | db.t4g.micro | 未开启 | 跟踪表(2) |
| 36 | `aws-luckyus-upush-rw` | upush | 8.4.9 | db.t4g.medium | 未开启 | 跟踪表(2) |

## 6. 审批签字

| 角色 | 姓名 | 意见 | 日期 |
|------|------|------|------|
| 申请 DBA | 曾翔宇 | | |
| DBA 主管 | | | |
