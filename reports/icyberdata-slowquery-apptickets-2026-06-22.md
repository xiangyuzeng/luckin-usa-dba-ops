# 【DB优化需求】icyberdata 调度平台多条 SQL 写法导致全表扫描,请改写

| 项 | 内容 |
|----|------|
| 接收方 | 数据调度平台 / 元数据服务 应用团队 |
| 抄送 | Michael (CTO) |
| 提交人 | 曾翔宇 (David Zeng) / Senior DBA |
| 实例 | `aws-luckyus-icyberdata-rw`(库 `luckyus_icyberdata`) |
| 优先级 | P2(无线上故障,但 6/21 已触发一次慢查询告警,需排期整改) |
| 日期 | 2026-06-22 |

---

## 一、背景

6/21 该实例触发告警「AWS RDS 慢查询数量持续三分钟 > 300」。DBA 侧已对热点表 `monitor_alert_message` 补索引,主因(占全部慢查询 58%)已消除。

复盘 6/15–6/22 全量慢查询日志(共 131 万条)后发现,**剩余慢查询中有一批是 SQL 写法问题——把索引列包进函数或用 `NOT IN(子查询)`,导致索引失效、全表扫描。这类问题 DBA 加索引无法解决,需应用侧改写 SQL。** 现整理如下,烦请评估排期。

> 说明:另有一大批慢查询(`QRTZ_LOCKS`、`core_node`、`roles`、`users` 等,Rows_examined≈1)属锁/IO 争用,是上述热点表扫表风暴的连带影响,DBA 侧修复后预计自行缓解,**不在本工单范围**。

## 二、需整改项

### ① `sys_node_history` 清理任务(影响最大,单次扫 31 万行)

- **现状 SQL:**
  ```sql
  DELETE FROM sys_node_history
  WHERE TIMESTAMPDIFF(DAY, create_time, CURRENT_TIMESTAMP) > 7;
  -- 同样写法还有:INSERT INTO core_node_history_archive SELECT * FROM sys_node_history WHERE TIMESTAMPDIFF(...) > 7;
  ```
- **问题:** `create_time` 被 `TIMESTAMPDIFF()` 包裹,索引完全失效,每次全表扫 ~311,045 行(Query_time 最高 3.5s)。
- **建议改写:**
  ```sql
  DELETE FROM sys_node_history
  WHERE create_time < CURRENT_TIMESTAMP - INTERVAL 7 DAY;
  ```
  改写后 DBA 侧补索引 `idx_create_time (create_time)` 即可走范围扫描。**请确认改写后由 DBA 加索引。**

### ② `task_instance` 归档任务(同类问题)

- **现状 SQL:**
  ```sql
  INSERT INTO task_instance_history
  SELECT * FROM task_instance
  WHERE run_mode IN (0,1,3)
    AND TIMESTAMPDIFF(DAY, create_time, CURRENT_TIMESTAMP) > 7;
  ```
- **问题:** 同上,`create_time` 被函数包裹,全表扫 ~54,000 行(最高 8.2s)。
- **建议改写:** `... AND create_time < CURRENT_TIMESTAMP - INTERVAL 7 DAY;`,改写后 DBA 补 `(create_time)` 相关索引。

### ③ `task_instance_dependency` 清理任务(NOT IN 反连接)

- **现状 SQL:**
  ```sql
  DELETE FROM task_instance_dependency
  WHERE child_instance_id  NOT IN (SELECT id FROM task_instance)
    AND parent_instance_id NOT IN (SELECT id FROM task_instance);
  ```
- **问题:** `NOT IN (子查询)` 无法有效利用现有索引 `cin_idx / pin_idx`,扫 ~190,848 行。
- **建议改写为 LEFT JOIN 反连接**(现有索引即可命中):
  ```sql
  DELETE d FROM task_instance_dependency d
  LEFT JOIN task_instance c ON d.child_instance_id  = c.id
  LEFT JOIN task_instance p ON d.parent_instance_id = p.id
  WHERE c.id IS NULL AND p.id IS NULL;
  ```

### ④ `task_instance` 调度轮询查询(高频,11.2 万次/周)

- **现状 SQL(节选):**
  ```sql
  SELECT i.* FROM task_instance i
  WHERE (i.run_type = 4 || i.event_dependency_satisfied = 1)
    AND i.run_mode NOT IN (3) AND i.env NOT IN (1)
    AND ((i.run_mode=1 AND perform_type IN(1,5,9) AND i.last_state IN(1,3)
          AND TIMESTAMPDIFF(SECOND, i.schedule_time, CURRENT_TIMESTAMP) BETWEEN 0 AND 172800)
         OR (...));
  ```
- **问题:** 顶层 `OR` + `schedule_time` 被 `TIMESTAMPDIFF()` 包裹,优化器无法用单列索引,平均扫 ~4,661 行 × 11.2 万次/周。
- **建议方向:**(需应用评估)
  1. 把 `TIMESTAMPDIFF(SECOND, schedule_time, NOW()) BETWEEN 0 AND 172800` 改成 `schedule_time BETWEEN NOW()-INTERVAL 2 DAY AND NOW()`;
  2. 顶层 `OR` 拆成 `UNION`,使各分支可分别命中索引;
  3. 若可行,`SELECT i.*` 收窄为实际需要的列。
  改写后 DBA 协助评估并补复合索引。

### ⑤ `meta_table_partition` 删除任务(IN 列表未去重)

- **现状 SQL:**
  ```sql
  DELETE FROM meta_table_partition
  WHERE meta_table_id IN (276179, 276179, 276179, ... 同一值重复上千次);
  ```
- **问题:** 应用拼 `IN` 列表时未去重,同一 `meta_table_id` 重复数千次,Query_time 最高 **40.6s**。
- **建议:** 拼 `IN` 列表前做去重(`Set` 去重),或改为单值 `=` 查询。
  > 附:DBA 侧已发现该表存在**重复索引**(`idx_meta_table_partition_table_id` 与 `mtid_idx` 均为 `(meta_table_id)`),将由 DBA 删除其一,与本项无关。

## 三、汇总与优先级

| # | 表 | 问题 | 改法 | 建议优先级 |
|---|----|------|------|:---:|
| ① | sys_node_history | 函数包裹 create_time | 改 `<` 比较 + DBA 加索引 | **高** |
| ② | task_instance | 函数包裹 create_time | 改 `<` 比较 + DBA 加索引 | **高** |
| ③ | task_instance_dependency | NOT IN 子查询 | 改 LEFT JOIN 反连接 | 中 |
| ④ | task_instance 轮询 | OR + 函数包裹 | 拆 UNION + 去函数 + 收窄列 | 中 |
| ⑤ | meta_table_partition | IN 列表未去重 | 应用层去重 | 中 |

## 四、配合方式

①②④ 改写完成后请知会 DBA,由我方在生产补对应索引并验证 `EXPLAIN`。如需我方提供测试库验证或一起评审改写,随时联系。

---

*证据来源:CloudWatch `/aws/rds/instance/aws-luckyus-icyberdata-rw/slowquery`,统计窗口 2026-06-15 ~ 2026-06-22。*
