主题：aws-luckyus-salesorder-rw 财务对账两表新增复合索引（t_finance_receipt、t_finance_refund）


变更原因

原始记录一：CloudWatch 慢查询日志 `/aws/rds/instance/aws-luckyus-salesorder-rw/slowquery`
日志时间 2026-09-01T02:01:41.958169Z（原文，字段与格式未改动）

    # Query_time: 5.288455  Rows_sent: 31  Rows_examined: 1362124
    SELECT id, receipt_no, receipt_account_no, status, receipt_method_no, payment_method,
           tp_serial_no, third_serial_no, receipt_object_type, order_no, user_no,
           receipt_amount, discount_amount, currency, receipt_date, checking_date,
           checking_amount, checking_result, checking_failed_reason, checking_time,
           difference_amount, create_time, modify_time, creator_id, creator_name,
           modifier_id, modifier_name, remark, tenant
      FROM t_finance_receipt
     WHERE deleted = 0
       AND (status = 1 AND checking_date BETWEEN '2026-08-25 02:01:35.818' AND '2026-09-01 02:01:35.818')
       AND t_finance_receipt.tenant = 'IQA2'
     ORDER BY modify_time DESC
     LIMIT 10000;

原始记录二：同一日志，时间 2026-09-01T02:01:36.668728Z（原文）

    # Query_time: 0.849427  Rows_sent: 1  Rows_examined: 1362124
    SELECT COUNT(*) AS total
      FROM t_finance_receipt
     WHERE deleted = 0
       AND (status = 1 AND checking_date BETWEEN '2026-08-25 02:01:35.818' AND '2026-09-01 02:01:35.818')
       AND t_finance_receipt.tenant = 'IQA2';

原始记录三：同一日志，时间 2026-09-01T03:00:04.635056Z（原文）

    # Query_time: 4.599620  Rows_sent: 1  Rows_examined: 21107
    SELECT COUNT(*) AS total
      FROM t_finance_refund
     WHERE deleted = 0
       AND (checking_status = 1 AND checking_date BETWEEN '2026-08-25 03:00:00.03' AND '2026-09-01 03:00:00.03')
       AND t_finance_refund.tenant = 'LKUS';

原始记录四：实例 `performance_schema.events_statements_summary_by_digest` 累计值（原始采集值，未加工）

    t_finance_receipt SELECT   COUNT_STAR 58   SUM_TIMER_WAIT 328.7 s  AVG 5.67 s  MAX 6.68 s
                              SUM_ROWS_SENT 208,743      SUM_ROWS_EXAMINED 73,379,666
                              SUM_SELECT_SCAN 58（100%）
    t_finance_receipt COUNT   COUNT_STAR 80   SUM_TIMER_WAIT 292.1 s  AVG 3.65 s  MAX 9.65 s
                              SUM_ROWS_SENT 80             SUM_ROWS_EXAMINED 101,129,788
                              SUM_NO_INDEX_USED 80（100%）  SUM_SELECT_SCAN 80（100%）
    t_finance_refund  COUNT   7 天窗口 80 次 / 93.9 s / AVG 1.17 s / MAX 5.07 s
                              每次 Rows_examined 20,597 → Rows_sent 1  未走索引 80 次

原始记录五：生产实例 EXPLAIN 实测（2026-09-01，只读，语句与上述慢日志原文一致）

    t_finance_receipt COUNT :  type=ALL   possible_keys=NULL  key=NULL  rows=1,308,345  filtered=0.01
    t_finance_refund  COUNT :  type=ALL   possible_keys=NULL  key=NULL  rows=21,578     filtered=0.01

`possible_keys = NULL` 是数据库自身给出的结论：这两条语句的 WHERE 条件在当前表结构下没有任何可用索引，
只能全表扫描。本次变更即为补上这两个条件对应的索引。


以下为 DBA 侧辅助分析，供参考，不作为本次变更的主要理由：

两表上目前分别有 8 个和 10 个索引，其中都有 `idx_checking_time_and_status(checking_time, status)`。
查询过滤的列是 `checking_date` + `status`（收款表）/ `checking_status`（退款表），与索引列名只差几个字母，
因此索引全部落空。表面上「索引很全」，实际一个也用不上，这也是它长期没有被发现的原因。

选择率（2026-09-01 实测）说明新索引的收益空间：
- `t_finance_receipt` 共 1,366,013 行，其中 `status=1` 仅 12,970 行（0.95%），`deleted=0` 占 100%；
- `t_finance_refund` 共约 21,578 行，其中 `checking_status=1` 仅 66 行；
- 即每次全表扫 136 万行，真实命中只有几十行（慢日志 Rows_sent=31）。

关于 DATE 列能否走索引：`checking_date` 是 `date` 类型，而应用传入的是带毫秒的 datetime 字面量。
用同表已有的 `idx_receipt_date`（同为 date 列）做等价验证，EXPLAIN 结果为
`type=range, key=idx_receipt_date, key_len=3, Using index`，确认这种比较可以正常使用索引，
本次新增索引不会因类型差异而失效。

顺带发现（不属于本次变更范围，建议转研发核对）：`checking_date` 是 DATE 类型，
`BETWEEN '2026-08-25 02:01:35.818' AND ...` 会把 DATE 提升为 DATETIME 比较，
`2026-08-25 00:00:00 < 2026-08-25 02:01:35.818`，因此窗口首日实际被排除，
7 天窗口实际只覆盖 6 天。加索引不改变这一行为，需应用侧确认是否符合预期。


变更内容

在 `aws-luckyus-salesorder-rw`（MySQL 8.4.10，db.t4g.medium，Multi-AZ）的 `luckyus_sales_order` 库
新增两个复合索引，列顺序均为「等值列在前、范围列在末」：

    ALTER TABLE luckyus_sales_order.t_finance_receipt
      ADD INDEX idx_tenant_status_ckdate (tenant, status, deleted, checking_date),
      ALGORITHM=INPLACE, LOCK=NONE;

    ALTER TABLE luckyus_sales_order.t_finance_refund
      ADD INDEX idx_tenant_ckstatus_ckdate (tenant, checking_status, deleted, checking_date),
      ALGORITHM=INPLACE, LOCK=NONE;

变更的意义：使每天 02:00~03:00 UTC 的财务对账任务不再全表扫描。收款表一条 SELECT 加一条配套 COUNT
每次各扫 136 万行只为取回 31 行；按 `performance_schema` 累计，两条合计已扫描 1.74 亿行。
加索引后按 `tenant + status/checking_status` 定位到万行以内，再按 `checking_date` 范围收敛到几十行。
`deleted` 目前全为 0，保留在索引中是为了与 WHERE 条件完全对齐，将来若启用软删除无需再改索引。

不涉及：表结构（不增删改任何列）、字段类型、字符集、主键与现有索引（一个都不删）、
实例类型（db.t4g.medium）、引擎版本（MySQL 8.4.10）、参数组（luckyus-prod-84）、
存储容量与类型（gp3）、备份策略、Multi-AZ 配置、网络与安全组，以上均保持不变。
也不涉及任何应用代码改动 —— 现有 SQL 一字不改即可命中新索引。

业务中断：无。`ALGORITHM=INPLACE, LOCK=NONE` 为在线加索引，执行期间该表可正常读写。
仅在语句开始与结束的瞬间需要短暂的 metadata lock；若此刻该表上有长事务，加索引会等待，
因此执行窗口须避开 02:00~03:00 UTC 的对账批量。建议 08:00~09:00 UTC（04:00~05:00 ET）执行。
影响范围：`luckyus_sales_order` 库两张表。收款表 1,366,013 行 / 260.8 MB 数据 + 334.1 MB 索引，
预计新增索引约 40~55 MB，耗时数十秒；退款表 21,578 行 / 9.5 MB，秒级完成。
数据风险：无。加索引不改变任何行数据，不涉及数据迁移与类型转换。
性能影响：执行期间该表写入会有额外的索引维护开销；两表日增量均在千行级，影响可忽略。
变更后每次 INSERT/UPDATE 多维护一个索引，代价换取的是每天两次 136 万行全表扫的消除。
成本影响：新增约 41~56 MB 存储。该实例存储按已分配容量计费，不触发扩容则账单不变。
回滚方案：`ALTER TABLE ... DROP INDEX idx_tenant_status_ckdate;`（退款表同理），
同为在线 DDL，回滚后即恢复变更前的执行计划。
执行权限：需 `ALTER` 权限。DBA 账号 databasecheck 为只读，无法执行，需由具备该权限的账号操作。


测试信息

1) 索引创建成功确认（变更后立即）

    SELECT TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX, COLUMN_NAME
      FROM information_schema.STATISTICS
     WHERE TABLE_SCHEMA = 'luckyus_sales_order'
       AND INDEX_NAME IN ('idx_tenant_status_ckdate', 'idx_tenant_ckstatus_ckdate')
     ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

   预期：收款表 4 行（tenant, status, deleted, checking_date），退款表 4 行
   （tenant, checking_status, deleted, checking_date），顺序与变更内容一致。

2) 执行计划确认 —— 验证「现有 SQL 一字不改即可命中」这条声明

   用上述三条慢日志原文语句加 EXPLAIN 各跑一次。
   预期：`type` 由 `ALL` 变为 `range` 或 `ref`，`key` = 新索引名，`possible_keys` 不再为 NULL，
   `rows` 由 130 万级降到万行以内。若 `key` 仍为 NULL，说明索引未被采用，应立即回滚并复查列顺序。

3) 不重启确认 —— 验证「业务中断：无」

    SHOW GLOBAL STATUS LIKE 'Uptime';

   预期：`Uptime` 大于变更开始前的取值（未归零），即实例全程未重启。

4) 不断连接确认 —— 验证「执行期间该表可正常读写」

   CloudWatch `AWS/RDS` → `DatabaseConnections`，实例 aws-luckyus-salesorder-rw，
   取变更前后各 30 分钟、1 分钟粒度。预期：无掉零、无断崖式下跌。
   执行期间同时观察 `SHOW PROCESSLIST`，预期无 `Waiting for table metadata lock` 堆积。

5) 锁等待与应用报错确认

   执行窗口内检查应用侧（isalesorderservice）日志，预期无 `Lock wait timeout exceeded`、
   无 `ER_LOCK_WAIT_TIMEOUT`、无对账任务失败告警。

6) 实际收益确认（变更次日 02:00~03:00 UTC 批次跑完后）

   - CloudWatch 慢日志：预期上述三条语句不再出现在慢日志中（Query_time 应降至 1 s 以下）。
   - `performance_schema`：对比同一 digest 的 `AVG_TIMER_WAIT` 与 `SUM_ROWS_EXAMINED` 增量，
     预期单次 Rows_examined 由 1,362,124 / 20,597 降到千行以内，收款表 SELECT 平均耗时
     由 5.67 s 降到毫秒级。
   - 若次日批次的 Rows_examined 没有明显下降，说明索引未被使用，按第 2 项复查。

7) 存储与写入影响确认（变更次日）

    SELECT TABLE_NAME, TABLE_ROWS,
           ROUND(DATA_LENGTH/1024/1024, 1)  AS data_mb,
           ROUND(INDEX_LENGTH/1024/1024, 1) AS index_mb
      FROM information_schema.TABLES
     WHERE TABLE_SCHEMA = 'luckyus_sales_order'
       AND TABLE_NAME IN ('t_finance_receipt', 't_finance_refund');

   预期：收款表 `index_mb` 增加约 40~55 MB，退款表增加约 1 MB，与变更内容中的估算相符。
   同时检查 CloudWatch `FreeStorageSpace` 无异常下降、`WriteLatency` 与变更前同期持平
   —— 验证「写入额外开销可忽略」这条声明。
