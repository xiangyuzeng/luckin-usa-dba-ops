-- =====================================================================
-- LDAS  luckyus_db_collection  分级清理脚本（仅供审阅，勿一键全跑）
-- 服务器: aws-luckyus-ldas01-rw   MySQL 8.0.45   file_per_table=1
-- 生成日期: 2026-06-09     基准 CURDATE() 动态计算保留窗口
-- 安全约定: 生产只读为默认；以下为写操作，需 DBA 确认后在低峰逐段执行。
--          每段先跑 SELECT 预览影响行数，再执行 DELETE/OPTIMIZE。
-- =====================================================================

-- 分级保留策略
--   Tier A 指标表(5min粒度, 有 _daily 汇总兜底)         保留 90 天
--   Tier B schema 每日全量快照(列定义极少变, 冗余高)      保留 30 天
--   Tier C 诊断日志(大事务/锁等待/慢查询)               保留 60 天
--   processlist 仅 OPTIMIZE(外部采集已只留 ~3h, 纯膨胀)   不删数据
--   *_daily 汇总表 / 维表(instances/describe 等)         不动
--   空表 + zshadow_* 影子表                              可选 DROP


-- =====================================================================
-- 0. 预检（只读，先跑）
-- =====================================================================
-- 0.1 确认无长事务/重负载
SHOW PROCESSLIST;
-- 0.2 当前各大表物理大小 & 真实行数基线
SELECT table_name,
       ROUND((data_length+index_length)/1024/1024/1024,2) AS total_gb,
       ROUND(data_free/1024/1024/1024,2)                  AS free_gb
FROM information_schema.TABLES
WHERE table_schema='luckyus_db_collection'
ORDER BY (data_length+index_length) DESC LIMIT 15;


-- =====================================================================
-- 1. processlist —— 仅重建回收 ~49.7 GB（真实仅 ~3.6 万活行）
--    MySQL 8 InnoDB OPTIMIZE = online rebuild，活行极少，秒级完成。
-- =====================================================================
-- 预览真实活行数
SELECT COUNT(*) FROM luckyus_db_collection.t_dba_collect_processlist_info;
-- 重建（回收空间到 OS）
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_processlist_info;


-- =====================================================================
-- 2. 分批删除（每段：先 SELECT 预览 → 反复执行 DELETE 直到 0 行 → OPTIMIZE）
--    分批 LIMIT 20000 防止大事务/binlog 暴涨/主从延迟。
-- =====================================================================

-- ---- Tier A: 指标表 保留 90 天 -------------------------------------
-- ec2_metrics（删除占比高 ~46%，建议优先用第 3 节 swap 方案，更快）
SELECT COUNT(*) FROM luckyus_db_collection.t_dba_collect_ec2_metrics
  WHERE collect_timestamp < DATE_SUB(CURDATE(), INTERVAL 90 DAY);
-- 反复执行直到 Rows matched = 0：
DELETE FROM luckyus_db_collection.t_dba_collect_ec2_metrics
  WHERE collect_timestamp < DATE_SUB(CURDATE(), INTERVAL 90 DAY)
  ORDER BY collect_timestamp LIMIT 20000;

-- rds_metrics 保留 90 天
DELETE FROM luckyus_db_collection.t_dba_collect_rds_metrics
  WHERE collect_timestamp < DATE_SUB(CURDATE(), INTERVAL 90 DAY)
  ORDER BY collect_timestamp LIMIT 20000;

-- redis_cluster_metrics 保留 90 天
DELETE FROM luckyus_db_collection.t_dba_collect_redis_cluster_metrics
  WHERE collect_timestamp < DATE_SUB(CURDATE(), INTERVAL 90 DAY)
  ORDER BY collect_timestamp LIMIT 20000;

-- index_used / index_unused 保留 90 天（data_date）
DELETE FROM luckyus_db_collection.t_dba_collect_index_used
  WHERE data_date < DATE_SUB(CURDATE(), INTERVAL 90 DAY)
  ORDER BY data_date LIMIT 20000;
DELETE FROM luckyus_db_collection.t_dba_collect_index_unused
  WHERE data_date < DATE_SUB(CURDATE(), INTERVAL 90 DAY)
  ORDER BY data_date LIMIT 20000;

-- ---- Tier B: schema 每日全量快照 保留 30 天 ------------------------
DELETE FROM luckyus_db_collection.t_dba_collect_table_column_info
  WHERE data_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY)
  ORDER BY data_date LIMIT 20000;
DELETE FROM luckyus_db_collection.t_dba_collect_table_index_info
  WHERE data_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY)
  ORDER BY data_date LIMIT 20000;
DELETE FROM luckyus_db_collection.t_dba_collect_table_info
  WHERE data_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY)
  ORDER BY data_date LIMIT 20000;
DELETE FROM luckyus_db_collection.t_dba_collect_mysql_table_info
  WHERE data_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY)
  ORDER BY data_date LIMIT 20000;
DELETE FROM luckyus_db_collection.t_dba_collect_created_tmp_table
  WHERE data_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY)
  ORDER BY data_date LIMIT 20000;
DELETE FROM luckyus_db_collection.t_dba_collect_no_index_used_query
  WHERE data_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY)
  ORDER BY data_date LIMIT 20000;

-- ---- Tier C: 诊断日志 保留 60 天 ----------------------------------
DELETE FROM luckyus_db_collection.t_dba_collect_big_trx_info
  WHERE create_time < DATE_SUB(CURDATE(), INTERVAL 60 DAY)
  ORDER BY create_time LIMIT 20000;
DELETE FROM luckyus_db_collection.t_dba_collect_lock_waits_info
  WHERE create_time < DATE_SUB(CURDATE(), INTERVAL 60 DAY)
  ORDER BY create_time LIMIT 20000;
DELETE FROM luckyus_db_collection.t_dba_collect_slow_query
  WHERE data_date < DATE_SUB(CURDATE(), INTERVAL 60 DAY)
  ORDER BY data_date LIMIT 20000;


-- =====================================================================
-- 3. ec2_metrics 可选 swap 方案（删除占比高时比逐批 DELETE 快得多）
--    思路: 只把"要保留的近 90 天"导入新表 → 原子 RENAME → 删旧表。
--    需短暂业务窗口确认采集端可容忍切换瞬间。
-- =====================================================================
-- CREATE TABLE luckyus_db_collection.t_dba_collect_ec2_metrics_new
--   LIKE luckyus_db_collection.t_dba_collect_ec2_metrics;
-- INSERT INTO luckyus_db_collection.t_dba_collect_ec2_metrics_new
--   SELECT * FROM luckyus_db_collection.t_dba_collect_ec2_metrics
--   WHERE collect_timestamp >= DATE_SUB(CURDATE(), INTERVAL 90 DAY);
-- RENAME TABLE
--   luckyus_db_collection.t_dba_collect_ec2_metrics     TO luckyus_db_collection.t_dba_collect_ec2_metrics_old,
--   luckyus_db_collection.t_dba_collect_ec2_metrics_new TO luckyus_db_collection.t_dba_collect_ec2_metrics;
-- DROP TABLE luckyus_db_collection.t_dba_collect_ec2_metrics_old;


-- =====================================================================
-- 4. 删除完成后回收空间（逐表，低峰执行；online，不阻塞读写）
-- =====================================================================
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_ec2_metrics;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_rds_metrics;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_table_column_info;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_big_trx_info;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_table_index_info;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_table_info;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_index_used;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_redis_cluster_metrics;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_lock_waits_info;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_index_unused;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_mysql_table_info;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_created_tmp_table;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_no_index_used_query;
OPTIMIZE TABLE luckyus_db_collection.t_dba_collect_slow_query;


-- =====================================================================
-- 5. （可选）建立保留定时任务，避免再次膨胀  event_scheduler 已 ON
--    每日 18:00 UTC（≈13:00/14:00 EST 业务低峰前）滚动清理。
--    注: 大批量首次清理完成后再启用，日常增量删除量小。
-- =====================================================================
-- DELIMITER //  -- (MCP 单条执行时无需 DELIMITER，逐条建 event)
CREATE EVENT IF NOT EXISTS luckyus_db_collection.ev_purge_ec2_metrics
  ON SCHEDULE EVERY 1 DAY STARTS (TIMESTAMP(CURDATE()) + INTERVAL 1 DAY + INTERVAL 18 HOUR)
  DO DELETE FROM luckyus_db_collection.t_dba_collect_ec2_metrics
     WHERE collect_timestamp < DATE_SUB(CURDATE(), INTERVAL 90 DAY) LIMIT 200000;
-- 同理为 rds_metrics / redis_cluster_metrics / index_used (90d),
--          table_column/index/info / mysql_table_info / created_tmp / no_index_used (30d),
--          big_trx / lock_waits / slow_query (60d) 各建一个 ev_purge_* 事件。
-- 查看: SELECT event_name,status,last_executed FROM information_schema.EVENTS
--        WHERE event_schema='luckyus_db_collection';


-- =====================================================================
-- 6. （可选）清理无用空表 / 影子表（DROP 前务必二次确认）
-- =====================================================================
-- 以下表当前 0 行；zshadow_* 为历史影子表，t_dba_healthy_info 等长期为空：
-- DROP TABLE IF EXISTS
--   luckyus_db_collection.zshadow_t_dba_collect_instance_info,
--   luckyus_db_collection.zshadow_t_dba_collect_deadlock_info,
--   luckyus_db_collection.zshadow_t_dba_collect_table_column_info,
--   luckyus_db_collection.zshadow_t_dba_collect_table_index_info,
--   luckyus_db_collection.zshadow_t_dba_collect_table_info,
--   luckyus_db_collection.zshadow_t_dba_healthy_info,
--   luckyus_db_collection.zshadow_t_dba_collect_db_info,
--   luckyus_db_collection.zshadow_t_dba_collect_big_trx_info,
--   luckyus_db_collection.zshadow_t_dba_collect_user_pris_info,
--   luckyus_db_collection.zshadow_t_dba_collect_request_info,
--   luckyus_db_collection.zshadow_t_dba_collect_processlist_info,
--   luckyus_db_collection.zshadow_t_dba_collect_lock_waits_info;
-- 注意: t_dba_collect_deadlock_info / t_dba_healthy_info 等若采集端仍引用，勿删，仅留空即可。
