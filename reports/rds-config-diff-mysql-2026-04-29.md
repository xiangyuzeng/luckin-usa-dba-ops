# RDS 配置差异比对报告

- 生成时间: 2026-04-29T16:37:15Z
- Region: `us-east-1`
- 实例总数: **74**
- 多数派阈值: 70%（低于此比例视为离群）

## 1. 差异摘要

| 维度组 | 属性 | 取值数 | 多数派值 | 多数派占比 | 状态 |
|---|---|---:|---|---:|---|
| Network | `VpcId` | 1 | `vpc-0dce7ca7770422d33` | 100% | 一致 |
| Network | `DBSubnetGroupName` | 1 | `rds-group` | 100% | 一致 |
| Network | `SubnetAvailabilityZones` | 1 | `us-east-1a,us-east-1b` | 100% | 一致 |
| Network | `Port` | 1 | `3306` | 100% | 一致 |
| Network | `PubliclyAccessible` | 1 | `False` | 100% | 一致 |
| Network | `MultiAZ` | 1 | `True` | 100% | 一致 |
| Network | `AvailabilityZone` | 2 | `us-east-1a` | 57% | ❌ 分散（2 种取值） |
| Security | `VpcSecurityGroupIds` | 1 | `sg-0deaa7cf7437e39c7` | 100% | 一致 |
| Security | `StorageEncrypted` | 1 | `True` | 100% | 一致 |
| Security | `KmsKeyId` | 1 | `arn:aws:kms:us-east-1:257394478466:key/5c5c743d-b79f-4d3a-86…` | 100% | 一致 |
| Security | `IAMDatabaseAuthenticationEnabled` | 1 | `False` | 100% | 一致 |
| Security | `DeletionProtection` | 2 | `True` | 99% | ⚠️ 1 个离群 |
| Security | `CACertificateIdentifier` | 1 | `rds-ca-rsa2048-g1` | 100% | 一致 |
| Security | `AutoMinorVersionUpgrade` | 2 | `False` | 99% | ⚠️ 1 个离群 |
| Backup | `BackupRetentionPeriod` | 2 | `7` | 99% | ⚠️ 1 个离群 |
| Backup | `CopyTagsToSnapshot` | 1 | `True` | 100% | 一致 |
| Backup | `PreferredBackupWindow` | 61 | `05:54-06:24` | 4% | ❌ 分散（61 种取值） |
| Backup | `PreferredMaintenanceWindow` | 65 | `wed:08:06-wed:08:36` | 3% | ❌ 分散（65 种取值） |
| Monitoring | `PerformanceInsightsEnabled` | 2 | `False` | 96% | ⚠️ 1 个离群 |
| Monitoring | `PerformanceInsightsKMSKeyId` | 2 | `(unset)` | 96% | ⚠️ 1 个离群 |
| Monitoring | `MonitoringInterval` | 1 | `0` | 100% | 一致 |
| Monitoring | `EnabledCloudwatchLogsExports` | 2 | `slowquery` | 95% | ⚠️ 1 个离群 |
| Engine | `Engine` | 1 | `mysql` | 100% | 一致 |
| Engine | `EngineVersion` | 6 | `8.0.40` | 74% | ⚠️ 5 个离群 |
| Engine | `DBParameterGroup` | 4 | `luckyus-prod-80-new` | 92% | ⚠️ 3 个离群 |
| Engine | `OptionGroup` | 2 | `default:mysql-8-0` | 99% | ⚠️ 1 个离群 |
| Engine | `DBInstanceClass` | 6 | `db.t4g.micro` | 58% | ❌ 分散（6 种取值） |
| Engine | `StorageType` | 2 | `gp3` | 95% | ⚠️ 1 个离群 |

## 2. 离群实例明细

### Network

#### `AvailabilityZone`

_无清晰多数派，所有取值分布如下：_

- **`us-east-1a`** (42 个): `aws-luckyus-datalink-84test-rw`, `aws-luckyus-dbatest-rw`, `aws-luckyus-fichargecontrol-rw`, `aws-luckyus-fitax-rw`, `aws-luckyus-framework01-rw-old1`, `aws-luckyus-framework02-rw`, `aws-luckyus-framework02-rw-old1`, `aws-luckyus-ibizconfigcenter-rw`, `aws-luckyus-igers-rw`, `aws-luckyus-ijumpserver-jumpserver-rw` ...+32
- **`us-east-1b`** (32 个): `aws-luckyus-cdpactivity-rw`, `aws-luckyus-devops-rw`, `aws-luckyus-devops-rw-old1`, `aws-luckyus-framework01-rw`, `aws-luckyus-iadmin-rw`, `aws-luckyus-ibillingcentersrv-rw`, `aws-luckyus-icyberdata-rw`, `aws-luckyus-icyberdata-rw-old1`, `aws-luckyus-iehr-rw`, `aws-luckyus-ifiaccounting-rw` ...+22

### Security

#### `DeletionProtection`

_多数派 (73 个): `True`_

- 离群值 **`False`** (1 个): `dbatest-xiangyuzeng`

#### `AutoMinorVersionUpgrade`

_多数派 (73 个): `False`_

- 离群值 **`True`** (1 个): `aws-luckyus-isalescouponservice-rw`

### Backup

#### `BackupRetentionPeriod`

_多数派 (73 个): `7`_

- 离群值 **`0`** (1 个): `aws-luckyus-dbatest-rw`

#### `PreferredBackupWindow`

_无清晰多数派，所有取值分布如下：_

- **`05:54-06:24`** (3 个): `aws-luckyus-devops-rw`, `aws-luckyus-devops-rw-old1`, `aws-luckyus-iluckyauthapi-rw`
- **`04:34-05:04`** (3 个): `aws-luckyus-icyberdata-rw`, `aws-luckyus-icyberdata-rw-old1`, `aws-luckyus-iopocp-rw`
- **`05:23-05:53`** (2 个): `aws-luckyus-fichargecontrol-rw`, `aws-luckyus-salesorder-rw`
- **`10:12-10:42`** (2 个): `aws-luckyus-framework01-rw`, `aws-luckyus-framework01-rw-old1`
- **`05:47-06:17`** (2 个): `aws-luckyus-framework02-rw`, `aws-luckyus-framework02-rw-old1`
- **`09:17-09:47`** (2 个): `aws-luckyus-ibillingcentersrv-rw`, `aws-luckyus-salesmarketing-rw`
- **`03:40-04:10`** (2 个): `aws-luckyus-iluckydorisops-rw`, `aws-luckyus-iluckydorisops-rw-green-9dk6oa`
- **`03:35-04:05`** (2 个): `aws-luckyus-iotplatform-rw`, `aws-luckyus-iotplatform-rw-green-5kpg5j`
- **`07:12-07:42`** (2 个): `aws-luckyus-ldas-rw`, `aws-luckyus-ldas-rw-old1`
- **`08:25-08:55`** (2 个): `aws-luckyus-upush-rw`, `aws-luckyus-upush-rw-green-mjda9r`
- **`00:00-00:30`** (2 个): `aws-luckyus-ybwtest8040-rw`, `aws-luckyus-ybwtest8040-rw-green-ldlylo`
- **`05:49-06:19`** (1 个): `aws-luckyus-cdpactivity-rw`
- **`06:09-06:39`** (1 个): `aws-luckyus-datalink-84test-rw`
- **`04:47-05:17`** (1 个): `aws-luckyus-dbatest-rw`
- **`05:03-05:33`** (1 个): `aws-luckyus-fitax-rw`
- **`08:07-08:37`** (1 个): `aws-luckyus-iadmin-rw`
- **`09:13-09:43`** (1 个): `aws-luckyus-ibizconfigcenter-rw`
- **`05:13-05:43`** (1 个): `aws-luckyus-iehr-rw`
- **`08:30-09:00`** (1 个): `aws-luckyus-ifiaccounting-rw`
- **`06:20-06:50`** (1 个): `aws-luckyus-igers-rw`
- **`05:06-05:36`** (1 个): `aws-luckyus-ijumpserver-jumpserver-rw`
- **`05:09-05:39`** (1 个): `aws-luckyus-ilsopdevopsdata-rw`
- **`07:36-08:06`** (1 个): `aws-luckyus-iluckyams-rw`
- **`09:26-09:56`** (1 个): `aws-luckyus-iluckyhealth-rw`
- **`05:19-05:49`** (1 个): `aws-luckyus-iluckymedia-rw`
- **`07:53-08:23`** (1 个): `aws-luckyus-iopenadmin-rw`
- **`03:21-03:51`** (1 个): `aws-luckyus-iopenlinker-rw`
- **`08:08-08:38`** (1 个): `aws-luckyus-iopenservice-rw`
- **`04:20-04:50`** (1 个): `aws-luckyus-iopshopexpand-rw`
- **`04:41-05:11`** (1 个): `aws-luckyus-ipermission-rw`
- **`06:40-07:10`** (1 个): `aws-luckyus-ireplenishment-rw`
- **`03:10-03:40`** (1 个): `aws-luckyus-iriskcontrolservice-rw`
- **`03:39-04:09`** (1 个): `aws-luckyus-isalescdp-rw`
- **`08:41-09:11`** (1 个): `aws-luckyus-isalescouponservice-rw`
- **`05:44-06:14`** (1 个): `aws-luckyus-isalesdatamarketing-rw`
- **`06:08-06:38`** (1 个): `aws-luckyus-isalesmembermarketing-rw`
- **`07:20-07:50`** (1 个): `aws-luckyus-isalesprivatedomain-rw`
- **`08:54-09:24`** (1 个): `aws-luckyus-iunifiedreconcile-rw`
- **`09:18-09:48`** (1 个): `aws-luckyus-iworkflowmidlayer-rw`
- **`04:48-05:18`** (1 个): `aws-luckyus-ldas01-rw`
- **`08:20-08:50`** (1 个): `aws-luckyus-mfranchise-rw`
- **`07:55-08:25`** (1 个): `aws-luckyus-opempefficiency-rw`
- **`10:21-10:51`** (1 个): `aws-luckyus-oplog-rw`
- **`03:51-04:21`** (1 个): `aws-luckyus-opproduction-rw`
- **`04:26-04:56`** (1 个): `aws-luckyus-opqualitycontrol-rw`
- **`07:08-07:38`** (1 个): `aws-luckyus-opshop-rw`
- **`07:18-07:48`** (1 个): `aws-luckyus-opshopsale-rw`
- **`08:01-08:31`** (1 个): `aws-luckyus-pubdm-rw`
- **`07:06-07:36`** (1 个): `aws-luckyus-salescrm-rw`
- **`07:45-08:15`** (1 个): `aws-luckyus-salespayment-rw`
- **`08:57-09:27`** (1 个): `aws-luckyus-scm-asset-rw`
- **`05:20-05:50`** (1 个): `aws-luckyus-scmcommodity-rw`
- **`09:30-10:00`** (1 个): `aws-luckyus-scm-openapi-rw`
- **`03:26-03:56`** (1 个): `aws-luckyus-scm-ordering-rw`
- **`10:00-10:30`** (1 个): `aws-luckyus-scm-plan-rw`
- **`03:59-04:29`** (1 个): `aws-luckyus-scm-purchase-rw`
- **`09:09-09:39`** (1 个): `aws-luckyus-scm-shopstock-rw`
- **`05:32-06:02`** (1 个): `aws-luckyus-scmsrm-rw`
- **`03:22-03:52`** (1 个): `aws-luckyus-scm-wds-rw`
- **`04:14-04:44`** (1 个): `aws-luckyus-scm-wmssimulate-rw`
- **`09:52-10:22`** (1 个): `dbatest-xiangyuzeng`

#### `PreferredMaintenanceWindow`

_无清晰多数派，所有取值分布如下：_

- **`wed:08:06-wed:08:36`** (2 个): `aws-luckyus-devops-rw`, `aws-luckyus-devops-rw-old1`
- **`tue:06:53-tue:07:23`** (2 个): `aws-luckyus-framework01-rw`, `aws-luckyus-framework01-rw-old1`
- **`sun:08:41-sun:09:11`** (2 个): `aws-luckyus-framework02-rw`, `aws-luckyus-framework02-rw-old1`
- **`tue:08:44-tue:09:14`** (2 个): `aws-luckyus-icyberdata-rw`, `aws-luckyus-icyberdata-rw-old1`
- **`sun:06:52-sun:07:22`** (2 个): `aws-luckyus-iluckydorisops-rw`, `aws-luckyus-iluckydorisops-rw-green-9dk6oa`
- **`wed:09:33-wed:10:03`** (2 个): `aws-luckyus-iotplatform-rw`, `aws-luckyus-iotplatform-rw-green-5kpg5j`
- **`thu:05:57-thu:06:27`** (2 个): `aws-luckyus-ldas-rw`, `aws-luckyus-ldas-rw-old1`
- **`sat:04:39-sat:05:09`** (2 个): `aws-luckyus-upush-rw`, `aws-luckyus-upush-rw-green-mjda9r`
- **`wed:05:47-wed:06:17`** (2 个): `aws-luckyus-ybwtest8040-rw`, `aws-luckyus-ybwtest8040-rw-green-ldlylo`
- **`mon:03:01-mon:03:31`** (1 个): `aws-luckyus-cdpactivity-rw`
- **`sat:09:34-sat:10:04`** (1 个): `aws-luckyus-datalink-84test-rw`
- **`thu:06:38-thu:07:08`** (1 个): `aws-luckyus-dbatest-rw`
- **`fri:03:19-fri:03:49`** (1 个): `aws-luckyus-fichargecontrol-rw`
- **`tue:06:10-tue:06:40`** (1 个): `aws-luckyus-fitax-rw`
- **`sun:07:27-sun:07:57`** (1 个): `aws-luckyus-iadmin-rw`
- **`wed:10:27-wed:10:57`** (1 个): `aws-luckyus-ibillingcentersrv-rw`
- **`fri:06:36-fri:07:06`** (1 个): `aws-luckyus-ibizconfigcenter-rw`
- **`tue:09:56-tue:10:26`** (1 个): `aws-luckyus-iehr-rw`
- **`wed:03:05-wed:03:35`** (1 个): `aws-luckyus-ifiaccounting-rw`
- **`sun:05:44-sun:06:14`** (1 个): `aws-luckyus-igers-rw`
- **`mon:03:18-mon:03:48`** (1 个): `aws-luckyus-ijumpserver-jumpserver-rw`
- **`sun:08:53-sun:09:23`** (1 个): `aws-luckyus-ilsopdevopsdata-rw`
- **`tue:05:29-tue:05:59`** (1 个): `aws-luckyus-iluckyams-rw`
- **`sat:09:39-sat:10:09`** (1 个): `aws-luckyus-iluckyauthapi-rw`
- **`mon:10:00-mon:10:30`** (1 个): `aws-luckyus-iluckyhealth-rw`
- **`sat:08:53-sat:09:23`** (1 个): `aws-luckyus-iluckymedia-rw`
- **`fri:04:00-fri:04:30`** (1 个): `aws-luckyus-iopenadmin-rw`
- **`wed:07:40-wed:08:10`** (1 个): `aws-luckyus-iopenlinker-rw`
- **`thu:04:06-thu:04:36`** (1 个): `aws-luckyus-iopenservice-rw`
- **`thu:07:04-thu:07:34`** (1 个): `aws-luckyus-iopocp-rw`
- **`sun:08:38-sun:09:08`** (1 个): `aws-luckyus-iopshopexpand-rw`
- **`tue:07:27-tue:07:57`** (1 个): `aws-luckyus-ipermission-rw`
- **`mon:09:41-mon:10:11`** (1 个): `aws-luckyus-ireplenishment-rw`
- **`thu:05:42-thu:06:12`** (1 个): `aws-luckyus-iriskcontrolservice-rw`
- **`sat:04:52-sat:05:22`** (1 个): `aws-luckyus-isalescdp-rw`
- **`thu:06:39-thu:07:09`** (1 个): `aws-luckyus-isalescouponservice-rw`
- **`sat:04:58-sat:05:28`** (1 个): `aws-luckyus-isalesdatamarketing-rw`
- **`sat:07:10-sat:07:40`** (1 个): `aws-luckyus-isalesmembermarketing-rw`
- **`thu:03:59-thu:04:29`** (1 个): `aws-luckyus-isalesprivatedomain-rw`
- **`tue:08:13-tue:08:43`** (1 个): `aws-luckyus-iunifiedreconcile-rw`
- **`thu:10:02-thu:10:32`** (1 个): `aws-luckyus-iworkflowmidlayer-rw`
- **`sun:09:55-sun:10:25`** (1 个): `aws-luckyus-ldas01-rw`
- **`wed:06:52-wed:07:22`** (1 个): `aws-luckyus-mfranchise-rw`
- **`tue:05:52-tue:06:22`** (1 个): `aws-luckyus-opempefficiency-rw`
- **`thu:03:04-thu:03:34`** (1 个): `aws-luckyus-oplog-rw`
- **`mon:09:09-mon:09:39`** (1 个): `aws-luckyus-opproduction-rw`
- **`thu:08:46-thu:09:16`** (1 个): `aws-luckyus-opqualitycontrol-rw`
- **`fri:04:03-fri:04:33`** (1 个): `aws-luckyus-opshop-rw`
- **`sat:05:32-sat:06:02`** (1 个): `aws-luckyus-opshopsale-rw`
- **`fri:06:34-fri:07:04`** (1 个): `aws-luckyus-pubdm-rw`
- **`tue:04:40-tue:05:10`** (1 个): `aws-luckyus-salescrm-rw`
- **`sun:05:30-sun:06:00`** (1 个): `aws-luckyus-salesmarketing-rw`
- **`mon:03:40-mon:04:10`** (1 个): `aws-luckyus-salesorder-rw`
- **`fri:03:02-fri:03:32`** (1 个): `aws-luckyus-salespayment-rw`
- **`sat:03:20-sat:03:50`** (1 个): `aws-luckyus-scm-asset-rw`
- **`tue:07:22-tue:07:52`** (1 个): `aws-luckyus-scmcommodity-rw`
- **`sun:07:50-sun:08:20`** (1 个): `aws-luckyus-scm-openapi-rw`
- **`thu:06:36-thu:07:06`** (1 个): `aws-luckyus-scm-ordering-rw`
- **`sun:08:42-sun:09:12`** (1 个): `aws-luckyus-scm-plan-rw`
- **`sat:07:07-sat:07:37`** (1 个): `aws-luckyus-scm-purchase-rw`
- **`sun:07:57-sun:08:27`** (1 个): `aws-luckyus-scm-shopstock-rw`
- **`tue:09:38-tue:10:08`** (1 个): `aws-luckyus-scmsrm-rw`
- **`wed:08:11-wed:08:41`** (1 个): `aws-luckyus-scm-wds-rw`
- **`thu:07:13-thu:07:43`** (1 个): `aws-luckyus-scm-wmssimulate-rw`
- **`mon:06:03-mon:06:33`** (1 个): `dbatest-xiangyuzeng`

### Monitoring

#### `PerformanceInsightsEnabled`

_多数派 (71 个): `False`_

- 离群值 **`True`** (3 个): `aws-luckyus-icyberdata-rw`, `aws-luckyus-icyberdata-rw-old1`, `aws-luckyus-salesmarketing-rw`

#### `PerformanceInsightsKMSKeyId`

_多数派 (71 个): `(unset)`_

- 离群值 **`arn:aws:kms:us-east-1:257394478466:key/5c5c743d-b79f-4d3a-867f-5e849ee4b52b`** (3 个): `aws-luckyus-icyberdata-rw`, `aws-luckyus-icyberdata-rw-old1`, `aws-luckyus-salesmarketing-rw`

#### `EnabledCloudwatchLogsExports`

_多数派 (70 个): `slowquery`_

- 离群值 **`(unset)`** (4 个): `aws-luckyus-datalink-84test-rw`, `aws-luckyus-dbatest-rw`, `aws-luckyus-isalescouponservice-rw`, `dbatest-xiangyuzeng`

### Engine

#### `EngineVersion`

_多数派 (55 个): `8.0.40`_

- 离群值 **`8.0.45`** (15 个): `aws-luckyus-dbatest-rw`, `aws-luckyus-devops-rw`, `aws-luckyus-framework01-rw`, `aws-luckyus-framework02-rw`, `aws-luckyus-icyberdata-rw`, `aws-luckyus-ijumpserver-jumpserver-rw`, `aws-luckyus-ilsopdevopsdata-rw`, `aws-luckyus-iluckydorisops-rw-green-9dk6oa`, `aws-luckyus-iluckyhealth-rw`, `aws-luckyus-iotplatform-rw-green-5kpg5j`, `aws-luckyus-isalescouponservice-rw`, `aws-luckyus-ldas01-rw`, `aws-luckyus-ldas-rw`, `aws-luckyus-upush-rw-green-mjda9r`, `dbatest-xiangyuzeng`
- 离群值 **`8.4.7`** (1 个): `aws-luckyus-datalink-84test-rw`
- 离群值 **`8.0.44`** (1 个): `aws-luckyus-iluckyams-rw`
- 离群值 **`8.0.42`** (1 个): `aws-luckyus-ybwtest8040-rw`
- 离群值 **`8.0.43`** (1 个): `aws-luckyus-ybwtest8040-rw-green-ldlylo`

#### `DBParameterGroup`

_多数派 (68 个): `luckyus-prod-80-new`_

- 离群值 **`luckyus-prod`** (4 个): `aws-luckyus-devops-rw`, `aws-luckyus-devops-rw-old1`, `aws-luckyus-ldas-rw`, `aws-luckyus-ldas-rw-old1`
- 离群值 **`luckyus-prod-84-lctn0`** (1 个): `aws-luckyus-datalink-84test-rw`
- 离群值 **`luckyus-prod-80-new-groupconcatmaxlen`** (1 个): `aws-luckyus-salesorder-rw`

#### `OptionGroup`

_多数派 (73 个): `default:mysql-8-0`_

- 离群值 **`default:mysql-8-4`** (1 个): `aws-luckyus-datalink-84test-rw`

#### `DBInstanceClass`

_无清晰多数派，所有取值分布如下：_

- **`db.t4g.micro`** (43 个): `aws-luckyus-datalink-84test-rw`, `aws-luckyus-dbatest-rw`, `aws-luckyus-fichargecontrol-rw`, `aws-luckyus-fitax-rw`, `aws-luckyus-iadmin-rw`, `aws-luckyus-ibillingcentersrv-rw`, `aws-luckyus-ibizconfigcenter-rw`, `aws-luckyus-iehr-rw`, `aws-luckyus-ifiaccounting-rw`, `aws-luckyus-igers-rw` ...+33
- **`db.t4g.medium`** (23 个): `aws-luckyus-cdpactivity-rw`, `aws-luckyus-devops-rw`, `aws-luckyus-devops-rw-old1`, `aws-luckyus-framework01-rw`, `aws-luckyus-framework01-rw-old1`, `aws-luckyus-framework02-rw`, `aws-luckyus-framework02-rw-old1`, `aws-luckyus-icyberdata-rw`, `aws-luckyus-icyberdata-rw-old1`, `aws-luckyus-iotplatform-rw` ...+13
- **`db.t4g.large`** (3 个): `aws-luckyus-ldas01-rw`, `aws-luckyus-ldas-rw`, `aws-luckyus-ldas-rw-old1`
- **`db.t3.micro`** (3 个): `aws-luckyus-ybwtest8040-rw`, `aws-luckyus-ybwtest8040-rw-green-ldlylo`, `dbatest-xiangyuzeng`
- **`db.t3.small`** (1 个): `aws-luckyus-iluckyhealth-rw`
- **`db.t4g.xlarge`** (1 个): `aws-luckyus-salesmarketing-rw`

#### `StorageType`

_多数派 (70 个): `gp3`_

- 离群值 **`gp2`** (4 个): `aws-luckyus-devops-rw`, `aws-luckyus-devops-rw-old1`, `aws-luckyus-ldas-rw`, `aws-luckyus-ldas-rw-old1`


## 3. 完整实例配置表

| DBInstanceIdentifier | Engine | EngineVersion | VpcId | DBSubnetGroupName | VpcSecurityGroupIds | PubliclyAccessible | StorageEncrypted | MultiAZ | DeletionProtection | BackupRetentionPeriod | CACertificateIdentifier |
|---|---|---|---|---|---|---|---|---|---|---|---|
| aws-luckyus-cdpactivity-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-datalink-84test-rw | mysql | 8.4.7 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-dbatest-rw | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 0 | rds-ca-rsa2048-g1 |
| aws-luckyus-devops-rw | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-devops-rw-old1 | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-fichargecontrol-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-fitax-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-framework01-rw | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-framework01-rw-old1 | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-framework02-rw | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-framework02-rw-old1 | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iadmin-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-ibillingcentersrv-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-ibizconfigcenter-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-icyberdata-rw | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-icyberdata-rw-old1 | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iehr-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-ifiaccounting-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-igers-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-ijumpserver-jumpserver-rw | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-ilsopdevopsdata-rw | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iluckyams-rw | mysql | 8.0.44 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iluckyauthapi-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iluckydorisops-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iluckydorisops-rw-green-9... | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iluckyhealth-rw | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iluckymedia-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iopenadmin-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iopenlinker-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iopenservice-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iopocp-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iopshopexpand-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iotplatform-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iotplatform-rw-green-5kpg5j | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-ipermission-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-ireplenishment-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iriskcontrolservice-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-isalescdp-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-isalescouponservice-rw | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-isalesdatamarketing-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-isalesmembermarketing-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-isalesprivatedomain-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iunifiedreconcile-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-iworkflowmidlayer-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-ldas-rw | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-ldas-rw-old1 | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-ldas01-rw | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-mfranchise-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-opempefficiency-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-oplog-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-opproduction-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-opqualitycontrol-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-opshop-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-opshopsale-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-pubdm-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-salescrm-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-salesmarketing-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-salesorder-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-salespayment-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-scm-asset-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-scm-openapi-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-scm-ordering-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-scm-plan-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-scm-purchase-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-scm-shopstock-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-scm-wds-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-scm-wmssimulate-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-scmcommodity-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-scmsrm-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-upush-rw | mysql | 8.0.40 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-upush-rw-green-mjda9r | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-ybwtest8040-rw | mysql | 8.0.42 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| aws-luckyus-ybwtest8040-rw-green-ldlylo | mysql | 8.0.43 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | True | 7 | rds-ca-rsa2048-g1 |
| dbatest-xiangyuzeng | mysql | 8.0.45 | vpc-0dce7ca7770422d33 | rds-group | sg-0deaa7cf7437e39c7 | False | True | True | False | 7 | rds-ca-rsa2048-g1 |
