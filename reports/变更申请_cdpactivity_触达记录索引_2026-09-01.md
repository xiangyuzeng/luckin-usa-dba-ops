主题：aws-luckyus-cdpactivity-rw t_contact_activity_instance_record 新增索引 (tenant, create_time)


变更原因

原始记录一：慢 SQL 采集表 `ldas01.t_dba_collect_slow_query` 中的完整指纹（原文，162 字符未截断）

    SELECT DISTINCTROW activity_id
      FROM t_contact_activity_instance_record
     WHERE create_time >= ? AND create_time <= ? AND tenant = ?
     ORDER BY create_time;

原始记录二：实例 `performance_schema.events_statements_summary_by_digest` 累计值（原始采集值，未加工）

    FIRST_SEEN 2026-07-21    LAST_SEEN 2026-09-01 15:00:01
    COUNT_STAR 550           SUM_TIMER_WAIT 905.4 s   AVG 1.65 s   MAX 3.14 s
    SUM_ROWS_SENT 22,959     SUM_ROWS_EXAMINED 6,789,496
    SUM_SELECT_SCAN 550（100%）  SUM_SORT_ROWS 22,959
    7 天窗口：104 次 / 191.7 s / AVG 1.84 s / 每次扫 12,337 行

原始记录三：生产实例 EXPLAIN 实测（2026-09-01，只读）

    type=index  possible_keys=idx_activity_id  key=idx_activity_id  key_len=8
    rows=12,557  filtered=1.11  Extra=Using where; Using temporary; Using filesort

原始记录四：该表当前索引（`information_schema.STATISTICS`，2026-09-01 实测）

    PRIMARY          id                      CARDINALITY 12,228
    idx_activity_id  activity_id             CARDINALITY  1,052
    idx_activity_no  activity_no             CARDINALITY  1,305
    idx_instance_no  activity_instance_no    CARDINALITY 12,557

即：查询过滤的 `create_time` 与 `tenant` 两列均无索引，优化器只能退而全索引扫描
`idx_activity_id`，再逐行过滤，并因 `DISTINCTROW` + `ORDER BY create_time` 额外产生临时表与 filesort。


以下为 DBA 侧辅助分析，供参考，不作为本次变更的主要理由：

🔴 需要如实说明的一点：**这条 SQL 现在并不慢，本次变更不会显著改变它的观测耗时。**

在同实例上以相同语句连跑三次（2026-09-01 15:5x UTC，非整点）实测为 0.027 / 0.027 / 0.029 秒，
而 `performance_schema` 记录的平均耗时是 1.65 s，相差约 60 倍。3.5 MB 的表做一次全索引扫描本就该是
几十毫秒，因此那 1.65 s 中绝大部分不是查询自身开销，而是它执行时刻（每小时整点 :00）的资源争用
—— 该实例基线 CPU 仅 7~8%，而 04:00 峰值 34.2%、09:00~12:00 达 19~37%，与全 fleet 的整点批量重合。

把观测耗时真正降下来的手段是任务错峰（从 `:00` 挪到 `:07` / `:23` 之类，属应用侧配置，
已记为行动项 B-02，归属张晓松），不是本次索引。

那么本次为什么仍建议做：`create_time` / `tenant` 无索引是确凿的结构性缺陷，
现在表只有 1.3 万行所以无感，一旦触达活动放量到百万级，这条会从「争用受害者」变成「真正的慢 SQL」。
表只有 3.5 MB，在线加索引秒级完成，代价极低。**这是一次预防性变更，不是故障处置。**


变更内容

在 `aws-luckyus-cdpactivity-rw`（MySQL 8.4.10，db.t4g.medium，Multi-AZ）的 `luckyus_cdp_activity` 库
新增一个复合索引，等值列在前、范围列在末：

    ALTER TABLE luckyus_cdp_activity.t_contact_activity_instance_record
      ADD INDEX idx_tenant_create_time (tenant, create_time),
      ALGORITHM=INPLACE, LOCK=NONE;

变更的意义：使查询按 `tenant` 等值定位后，直接用 `create_time` 有序范围收敛，
同时因索引本身按 `create_time` 有序，可消除 `ORDER BY create_time` 引起的 filesort。
消除该表随数据增长而线性劣化的隐患。

不涉及：表结构（不增删改任何列）、字段类型、字符集、主键与现有 3 个索引（一个都不删）、
实例类型（db.t4g.medium）、引擎版本（MySQL 8.4.10）、参数组、存储、备份策略、Multi-AZ 配置、
网络与安全组，以上均保持不变。不涉及任何应用代码改动。

业务中断：无。`ALGORITHM=INPLACE, LOCK=NONE` 在线加索引，执行期间该表可正常读写；
仅语句首尾瞬间需短暂 metadata lock。该任务固定在每小时整点触发，执行窗口须避开整点，
建议在 `:15~:45` 之间执行。
影响范围：单表 13,331 行 / 3.5 MB 数据 + 3.5 MB 索引，预计新增索引不足 1 MB，秒级完成。
数据风险：无。不改变任何行数据。
性能影响：新增一个索引的写入维护开销。该表日增量为百行级，影响可忽略。
成本影响：新增存储不足 1 MB，账单无变化。
回滚方案：`ALTER TABLE luckyus_cdp_activity.t_contact_activity_instance_record
DROP INDEX idx_tenant_create_time;` 同为在线 DDL，秒级回滚。
执行权限：需 `ALTER` 权限。DBA 账号 databasecheck 为只读，无法执行，需由具备该权限的账号操作。


测试信息

1) 索引创建成功确认（变更后立即）

    SELECT INDEX_NAME, SEQ_IN_INDEX, COLUMN_NAME, CARDINALITY
      FROM information_schema.STATISTICS
     WHERE TABLE_SCHEMA = 'luckyus_cdp_activity'
       AND TABLE_NAME = 't_contact_activity_instance_record'
       AND INDEX_NAME = 'idx_tenant_create_time'
     ORDER BY SEQ_IN_INDEX;

   预期：2 行，依次为 tenant、create_time。

2) 执行计划确认 —— 验证「消除全索引扫描与 filesort」这条声明

   对原始记录一的语句加 EXPLAIN 执行一次（参数取最近一小时窗口 + tenant='LKUS'）。
   预期：`key` = `idx_tenant_create_time`，`type` = `range`，
   `Extra` 中不再出现 `Using filesort`（`Using temporary` 可能因 DISTINCTROW 保留）。
   若 `key` 仍为 `idx_activity_id`，说明优化器未采用新索引，需复查列顺序，必要时回滚。

3) 不重启确认 —— 验证「业务中断：无」

    SHOW GLOBAL STATUS LIKE 'Uptime';

   预期：`Uptime` 大于变更开始前的取值（未归零）。

4) 不断连接确认

   CloudWatch `AWS/RDS` → `DatabaseConnections`，实例 aws-luckyus-cdpactivity-rw，
   变更前后各 30 分钟、1 分钟粒度。预期无掉零。

5) 整点任务正常确认（变更后的下一个整点）

   该任务每小时 `:00` 执行。变更后第一个整点过后，确认 `performance_schema` 中该 digest 的
   `COUNT_STAR` 有增长（任务照常执行）、且无新增错误。预期任务行为不变。

6) 收益与预期落差的如实记录（变更次日）

   对比该 digest 的 `AVG_TIMER_WAIT`。**预期不会有数量级改善** —— 按辅助分析，
   1.65 s 中的绝大部分是整点争用而非查询开销，本次索引只影响那约 27 ms 的部分。
   `SUM_ROWS_EXAMINED` 的单次增量应从 12,337 行降到百行级，这才是本次变更可验证的直接效果。
   观测耗时要真正下降，取决于行动项 B-02（任务错峰，应用侧）。
