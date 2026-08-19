# MySQL 8.0.45 升级工作计划 V2

**文档编号**: LCNA-DBA-2026-022-V2  
**日期**: 2026-04-20  
**作者**: David Zeng (DBA)  
**脚本仓库**: https://github.com/xiangyuzeng/mysql_upgrade.git  
**目标版本**: MySQL 8.0.45  
**截止日期**: 2026-05-31 (AWS 强制自动升级)

---

## 1. 升级范围

| 当前版本 | 实例数 | 操作 |
|---------|--------|------|
| 8.0.40 | 58 | 必须升级 |
| 8.0.41 | 1 (ldas01) | 必须升级 |
| **合计** | **59** | |

---

## 2. 工作流程总览

每台实例按以下 5 步执行：

| 步骤 | 方式 | 说明 |
|------|------|------|
| Step 1 | 脚本 `environment_check.sh` | 升级前环境基线采集 |
| Step 2 | 脚本 `start_binlog.sh` | 启动 binlog 流式备份 |
| Step 3 | AWS Console 手工操作 | 创建快照 → 修改版本 → 等待完成 |
| Step 4 | 脚本 `environment_check.sh` | 升级后环境检查 + 与 Step 1 对比 |
| Step 5 | 脚本 `stop_binlog.sh` | 停止 binlog 备份进程 |

---

## 3. 详细工作步骤

### Step 1: 升级前环境检查

**脚本**: `./environment_check.sh <instance-name>`  
**执行位置**: 跳板机 (10.238.3.43)  
**效果**: 采集实例 AWS 信息和 MySQL 运行基线，保存到 `.out` 文件，包含：
- 实例规格、版本、Multi-AZ、参数组名称与状态
- MySQL 版本和 GTID
- 按用户统计的活跃连接数
- 超过 60 秒的长事务
- 未提交事务 (innodb_trx)
- 12 个关键系统变量值
- Top 20 业务表行数与数据量

**继续条件**: Status = available、无长事务、无 pending 修改

---

### Step 2: 启动 Binlog 备份

**脚本**: `./start_binlog.sh <instance-name>`  
**执行位置**: 跳板机 (10.238.3.43)  
**效果**: 记录当前 binlog 位置，启动后台流式拉取进程，持续备份升级期间 binlog 到本地目录。

---

### Step 3: AWS Console 手工升级

#### 3.1 创建升级前快照

1. 进入 RDS → Databases → 选中目标实例
2. 点击 Actions → Take snapshot
3. Snapshot 名称填写: `<instance>-pre-8045-<YYYYMMDD>`
4. 点击 Take snapshot，等待状态变为 Available

*(截图: )*

#### 3.2 修改引擎版本

5. 选中实例，点击 Modify
6. 找到 Engine version 下拉框，选择 `8.0.45`
7. 页面底部点击 Continue
8. 选择 Apply immediately
9. 点击 Modify DB instance 确认

*(截图: )*

#### 3.3 等待升级完成

10. 观察实例状态变为 Upgrading
11. 等待状态恢复为 Available，确认版本显示 8.0.45

*(截图: )*

**预计耗时**: micro 5-8 分钟 / medium 8-12 分钟 / large+ 10-18 分钟

#### 3.4 创建升级后快照

12. Actions → Take snapshot，命名: `<instance>-post-8045-<YYYYMMDD>`
13. 等待状态变为 Available

*(截图: )*

---

### Step 4: 升级后环境检查 + 对比

**脚本**: `./environment_check.sh <instance-name>`  
**执行位置**: 跳板机 (10.238.3.43)  
**效果**: 再次采集相同内容，生成新的 `.out` 文件

#### 对比方法

```bash
diff <升级前.out> <升级后.out>
```

#### 预期差异（正常）

| 检查项 | 升级前 | 升级后 | 说明 |
|--------|--------|--------|------|
| `@@version` | 8.0.40 或 8.0.41 | **8.0.45** | 升级成功标志 |
| 活跃连接数 | N | 可能短暂低于 N | 应用重连中，几分钟内恢复 |
| `innodb_trx` | 可能有活跃事务 | 空 | 重启后无历史事务，正常 |
| Top 20 表 TABLE_ROWS | X | X ± 5% | InnoDB 统计为估算值，微小浮动正常 |

#### 不允许出现的差异（异常，需立即排查）

| 检查项 | 预期 | 异常情况 | 处理 |
|--------|------|----------|------|
| 参数组名称 | 不变 | 变为 default.mysql8.0 | 参数组关联丢失，需重新 attach |
| 参数组状态 | in-sync | pending-reboot | 等 5 分钟重查，持续则需 reboot |
| `character_set_server` | utf8mb4 | 变化 | 参数组异常，立即检查 |
| `collation_server` | 不变 | 变化 | 参数组异常 |
| `innodb_buffer_pool_size` | 原值 | 134217728 (128MB) | OOM 保护触发，报告并手动恢复 |
| `max_connections` | 4000 | 变小 | 参数组异常 |
| `long_query_time` | 0.1 | 变化 | 参数组异常 |
| `transaction_isolation` | READ-COMMITTED | 变化 | 参数组异常 |
| `gtid_mode` | ON | 变化 | 严重异常 |
| `enforce_gtid_consistency` | ON | 变化 | 严重异常 |
| `slow_query_log` | 1 | 0 | 慢查询日志关闭，需重新开启 |
| `performance_schema` | 1 | 0 | 性能监控丢失 |
| `lower_case_table_names` | 1 | 变化 | 严重异常（只读参数） |
| `group_concat_max_len` | 1048576 (salesorder) | 变小 | 参数组异常 |

#### 对比确认 Checklist

- [ ] `@@version` = 8.0.45
- [ ] 参数组名称与升级前一致
- [ ] 参数组状态 = in-sync
- [ ] 12 个关键系统变量全部一致（除 @@version 外）
- [ ] 活跃连接数已恢复
- [ ] 无异常长事务
- [ ] Top 20 表行数无数量级偏差

---

### Step 5: 停止 Binlog 备份

**脚本**: `./stop_binlog.sh <instance-name>`  
**执行位置**: 跳板机 (10.238.3.43)  
**效果**: 终止后台 binlog 流式进程，本地文件保留 7 天后清理。

---

## 4. 批次计划

| 批次 | 日期 | 实例数 | 范围 | 估时 |
|------|------|--------|------|------|
| Batch 1 | 04-22 (周三) | 2 | ldas, ldas01 (试点) | ~40 min |
| Batch 2a | 04-24 (周四) | 20 | 低风险 micro 第一批 | ~3.5 hr |
| Batch 2b | 04-29 (周二) | 17 | 低风险 micro 第二批 | ~3.5 hr |
| Batch 3 | 05-01 (周四) | 11 | 中等规格 + 框架 | ~3 hr |
| Batch 4 | 05-06 (周二) | 9 | 销售/CRM 核心 | ~2.5 hr |

**升级窗口**: 09:00-12:30 UTC (04:00-07:30 EST)  
**禁止时段**: 05:00 UTC (每日批处理)

---

## 5. 异常处理

| 场景 | 处理 |
|------|------|
| Step 1 发现长事务 | 等待结束或通知业务方 |
| Step 3 升级超 30 分钟未完成 | 检查 RDS Events，继续等待 |
| Step 4 参数组 pending-reboot | 等 5 分钟重查，持续则手动 reboot |
| Step 4 buffer_pool 缩为 128MB | 记录并报告，需手动恢复 |
| Step 4 连接数长时间不恢复 | 检查应用 Pod 状态和日志 |
| 升级后业务报错 | 从 pre-snapshot 回滚 |

---

## 6. 前置准备

- [ ] 跳板机 clone 脚本仓库并授权
- [ ] 确认 59 台实例的 `mysql --login-path` 已配置
- [ ] 确认 AWS Console 账号有 RDS 修改权限
- [ ] 准备升级通知模板
- [ ] 与领导确认 Batch 1 试点日期
- [ ] 准备 Grafana 告警静默规则

---

*计划制定: 2026-04-20 | David Zeng*
