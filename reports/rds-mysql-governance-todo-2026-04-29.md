# RDS MySQL 配置治理 TODO 清单

- 生成时间: 2026-04-29T16:38:17Z
- 数据来源: `rds-config-diff-mysql-2026-04-29.json`
- MySQL 实例总数: **74**

> 行动原则：先保证 P1（安全基线一致），再做 P2（版本/参数组标准化），最后处理 P3（运维窗口）。
> 每条工单都给出 `aws rds modify-db-instance` 命令骨架，**默认 `--no-apply-immediately`**，下次维护窗口生效。

## P1 — 安全 / 合规基线偏离

### P1-1. `DeletionProtection`: 离群值 `False`

- **目标**: 删除保护应保持开启（True）（多数派 = `True`，占比 99%）
- **离群实例 (1 个)**: `dbatest-xiangyuzeng`
- **建议动作**: 评估业务影响后，将上述实例对齐到 `True`
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier dbatest-xiangyuzeng --deletion-protection --no-apply-immediately
  ```

### P1-2. `BackupRetentionPeriod`: 离群值 `0`

- **目标**: 备份保留期应统一（多数派 = `7`，占比 99%）
- **离群实例 (1 个)**: `aws-luckyus-dbatest-rw`
- **建议动作**: 评估业务影响后，将上述实例对齐到 `7`
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-dbatest-rw --backup-retention-period 7 --no-apply-immediately
  ```

### P1-3. `AutoMinorVersionUpgrade`: 离群值 `True`

- **目标**: 自动小版本升级策略应统一（多数派 = `False`，占比 99%）
- **离群实例 (1 个)**: `aws-luckyus-isalescouponservice-rw`
- **建议动作**: 评估业务影响后，将上述实例对齐到 `False`
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-isalescouponservice-rw --no-auto-minor-version-upgrade --no-apply-immediately
  ```

### P1-4. `EnabledCloudwatchLogsExports`: 离群值 `(unset)`

- **目标**: CloudWatch 日志导出应统一（至少 slowquery）（多数派 = `slowquery`，占比 95%）
- **离群实例 (4 个)**: `aws-luckyus-datalink-84test-rw`, `aws-luckyus-dbatest-rw`, `aws-luckyus-isalescouponservice-rw`, `dbatest-xiangyuzeng`
- **建议动作**: 评估业务影响后，将上述实例对齐到 `slowquery`
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-datalink-84test-rw --cloudwatch-logs-export-configuration '{"EnableLogTypes":["slowquery"]}' --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-dbatest-rw --cloudwatch-logs-export-configuration '{"EnableLogTypes":["slowquery"]}' --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-isalescouponservice-rw --cloudwatch-logs-export-configuration '{"EnableLogTypes":["slowquery"]}' --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier dbatest-xiangyuzeng --cloudwatch-logs-export-configuration '{"EnableLogTypes":["slowquery"]}' --no-apply-immediately
  ```

### P1-5. `PerformanceInsightsEnabled`: 离群值 `True`

- **目标**: Performance Insights 启用策略应统一（多数派 = `False`，占比 96%）
- **离群实例 (3 个)**: `aws-luckyus-icyberdata-rw`, `aws-luckyus-icyberdata-rw-old1`, `aws-luckyus-salesmarketing-rw`
- **建议动作**: 评估业务影响后，将上述实例对齐到 `False`
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-icyberdata-rw --no-enable-performance-insights --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-icyberdata-rw-old1 --no-enable-performance-insights --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-salesmarketing-rw --no-enable-performance-insights --no-apply-immediately
  ```

## P2 — 版本与参数组标准化

### P2-1. `EngineVersion`: 离群值 `8.0.45`

- **目标**: 引擎版本统一到主流 GA 版本（多数派 = `8.0.40`，占比 74%）
- **离群实例 (15 个)**: `aws-luckyus-dbatest-rw`, `aws-luckyus-devops-rw`, `aws-luckyus-framework01-rw`, `aws-luckyus-framework02-rw`, `aws-luckyus-icyberdata-rw`, `aws-luckyus-ijumpserver-jumpserver-rw`, `aws-luckyus-ilsopdevopsdata-rw`, `aws-luckyus-iluckydorisops-rw-green-9dk6oa`, `aws-luckyus-iluckyhealth-rw`, `aws-luckyus-iotplatform-rw-green-5kpg5j`, `aws-luckyus-isalescouponservice-rw`, `aws-luckyus-ldas01-rw`, `aws-luckyus-ldas-rw`, `aws-luckyus-upush-rw-green-mjda9r`, `dbatest-xiangyuzeng`
- **风险**: 跨版本升级需要在测试环境先验证，注意应用兼容性 + 主从同步
- **建议动作**: 加入下一轮季度版本治理批次
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-dbatest-rw --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-devops-rw --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-framework01-rw --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-framework02-rw --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-icyberdata-rw --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-ijumpserver-jumpserver-rw --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-ilsopdevopsdata-rw --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-iluckydorisops-rw-green-9dk6oa --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-iluckyhealth-rw --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-iotplatform-rw-green-5kpg5j --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-isalescouponservice-rw --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-ldas01-rw --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-ldas-rw --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-upush-rw-green-mjda9r --engine-version 8.0.40 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier dbatest-xiangyuzeng --engine-version 8.0.40 --no-apply-immediately
  ```

### P2-2. `EngineVersion`: 离群值 `8.4.7`

- **目标**: 引擎版本统一到主流 GA 版本（多数派 = `8.0.40`，占比 74%）
- **离群实例 (1 个)**: `aws-luckyus-datalink-84test-rw`
- **风险**: 跨版本升级需要在测试环境先验证，注意应用兼容性 + 主从同步
- **建议动作**: 加入下一轮季度版本治理批次
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-datalink-84test-rw --engine-version 8.0.40 --no-apply-immediately
  ```

### P2-3. `EngineVersion`: 离群值 `8.0.44`

- **目标**: 引擎版本统一到主流 GA 版本（多数派 = `8.0.40`，占比 74%）
- **离群实例 (1 个)**: `aws-luckyus-iluckyams-rw`
- **风险**: 跨版本升级需要在测试环境先验证，注意应用兼容性 + 主从同步
- **建议动作**: 加入下一轮季度版本治理批次
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-iluckyams-rw --engine-version 8.0.40 --no-apply-immediately
  ```

### P2-4. `EngineVersion`: 离群值 `8.0.42`

- **目标**: 引擎版本统一到主流 GA 版本（多数派 = `8.0.40`，占比 74%）
- **离群实例 (1 个)**: `aws-luckyus-ybwtest8040-rw`
- **风险**: 跨版本升级需要在测试环境先验证，注意应用兼容性 + 主从同步
- **建议动作**: 加入下一轮季度版本治理批次
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-ybwtest8040-rw --engine-version 8.0.40 --no-apply-immediately
  ```

### P2-5. `EngineVersion`: 离群值 `8.0.43`

- **目标**: 引擎版本统一到主流 GA 版本（多数派 = `8.0.40`，占比 74%）
- **离群实例 (1 个)**: `aws-luckyus-ybwtest8040-rw-green-ldlylo`
- **风险**: 跨版本升级需要在测试环境先验证，注意应用兼容性 + 主从同步
- **建议动作**: 加入下一轮季度版本治理批次
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-ybwtest8040-rw-green-ldlylo --engine-version 8.0.40 --no-apply-immediately
  ```

### P2-6. `DBParameterGroup`: 离群值 `luckyus-prod`

- **目标**: 参数组统一到生产标准（多数派 = `luckyus-prod-80-new`，占比 92%）
- **离群实例 (4 个)**: `aws-luckyus-devops-rw`, `aws-luckyus-devops-rw-old1`, `aws-luckyus-ldas-rw`, `aws-luckyus-ldas-rw-old1`
- **建议动作**: 比对当前参数组与 `luckyus-prod-80-new` 的差异（`describe-db-parameters`）→ 评估迁移影响 → 在维护窗口切换
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-devops-rw --db-parameter-group-name luckyus-prod-80-new --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-devops-rw-old1 --db-parameter-group-name luckyus-prod-80-new --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-ldas-rw --db-parameter-group-name luckyus-prod-80-new --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-ldas-rw-old1 --db-parameter-group-name luckyus-prod-80-new --no-apply-immediately
  ```

### P2-7. `DBParameterGroup`: 离群值 `luckyus-prod-84-lctn0`

- **目标**: 参数组统一到生产标准（多数派 = `luckyus-prod-80-new`，占比 92%）
- **离群实例 (1 个)**: `aws-luckyus-datalink-84test-rw`
- **建议动作**: 比对当前参数组与 `luckyus-prod-80-new` 的差异（`describe-db-parameters`）→ 评估迁移影响 → 在维护窗口切换
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-datalink-84test-rw --db-parameter-group-name luckyus-prod-80-new --no-apply-immediately
  ```

### P2-8. `DBParameterGroup`: 离群值 `luckyus-prod-80-new-groupconcatmaxlen`

- **目标**: 参数组统一到生产标准（多数派 = `luckyus-prod-80-new`，占比 92%）
- **离群实例 (1 个)**: `aws-luckyus-salesorder-rw`
- **建议动作**: 比对当前参数组与 `luckyus-prod-80-new` 的差异（`describe-db-parameters`）→ 评估迁移影响 → 在维护窗口切换
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-salesorder-rw --db-parameter-group-name luckyus-prod-80-new --no-apply-immediately
  ```

### P2-9. `OptionGroup`: 离群值 `default:mysql-8-4`

- **目标**: Option Group 统一到默认（多数派 = `default:mysql-8-0`，占比 99%）
- **离群实例 (1 个)**: `aws-luckyus-datalink-84test-rw`
- **建议动作**: 确认 Option Group 是否承载实际选项；若空则切换到默认
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-datalink-84test-rw --option-group-name default:mysql-8-0 --no-apply-immediately
  ```

### P2-10. `StorageType`: 离群值 `gp2`

- **目标**: 存储类型统一（gp3 优先于 gp2）（多数派 = `gp3`，占比 95%）
- **离群实例 (4 个)**: `aws-luckyus-devops-rw`, `aws-luckyus-devops-rw-old1`, `aws-luckyus-ldas-rw`, `aws-luckyus-ldas-rw-old1`
- **建议动作**: gp2 → gp3 在线迁移，单实例约 5-15 分钟，建议低峰执行
- **执行命令骨架**:
  ```bash
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-devops-rw --storage-type gp3 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-devops-rw-old1 --storage-type gp3 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-ldas-rw --storage-type gp3 --no-apply-immediately
  aws rds modify-db-instance --region us-east-1 --db-instance-identifier aws-luckyus-ldas-rw-old1 --storage-type gp3 --no-apply-immediately
  ```

## P3 — 运维窗口标准化

### PreferredBackupWindow

- **现状**: 当前有 **61 种取值**，几乎每实例一个窗口，无法统一巡检/告警基线
- **建议方案**: 按业务域分 4-6 个窗口段（错峰），例如：
  - DevOps/Platform: `17:00-18:00 UTC`（北京 01:00-02:00）
  - Sales/CRM:      `18:00-19:00 UTC`
  - SCM:            `19:00-20:00 UTC`
  - Finance/Ops:    `20:00-21:00 UTC`
- **批量切换**: 制定映射表后，循环执行 `aws rds modify-db-instance --preferredbackupwindow ...`
- **影响**: 无中断，立即生效

### PreferredMaintenanceWindow

- **现状**: 当前有 **65 种取值**，几乎每实例一个窗口，无法统一巡检/告警基线
- **建议方案**: 按业务域分 4-6 个窗口段（错峰），例如：
  - DevOps/Platform: `tue:21:00-tue:22:00 UTC`
  - Sales/CRM:      `tue:22:00-tue:23:00 UTC`
  - SCM:            `wed:21:00-wed:22:00 UTC`
  - Finance/Ops:    `wed:22:00-wed:23:00 UTC`
- **批量切换**: 制定映射表后，循环执行 `aws rds modify-db-instance --preferredmaintenancewindow ...`
- **影响**: 无中断，立即生效

## 附录 — 关键属性的实例分布速查

### `EngineVersion`

| 取值 | 实例数 | 占比 |
|---|---:|---:|
| `8.0.40` | 55 | 74% |
| `8.0.45` | 15 | 20% |
| `8.4.7` | 1 | 1% |
| `8.0.44` | 1 | 1% |
| `8.0.42` | 1 | 1% |
| `8.0.43` | 1 | 1% |

### `DBParameterGroup`

| 取值 | 实例数 | 占比 |
|---|---:|---:|
| `luckyus-prod-80-new` | 68 | 92% |
| `luckyus-prod` | 4 | 5% |
| `luckyus-prod-84-lctn0` | 1 | 1% |
| `luckyus-prod-80-new-groupconcatmaxlen` | 1 | 1% |

### `DBInstanceClass`

| 取值 | 实例数 | 占比 |
|---|---:|---:|
| `db.t4g.micro` | 43 | 58% |
| `db.t4g.medium` | 23 | 31% |
| `db.t4g.large` | 3 | 4% |
| `db.t3.micro` | 3 | 4% |
| `db.t3.small` | 1 | 1% |
| `db.t4g.xlarge` | 1 | 1% |

### `StorageType`

| 取值 | 实例数 | 占比 |
|---|---:|---:|
| `gp3` | 70 | 95% |
| `gp2` | 4 | 5% |
