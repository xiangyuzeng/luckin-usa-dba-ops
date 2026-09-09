-- =====================================================================
-- 04_evidence.sql
-- LCNA 人员管理看板 — 数据可行性核验 全部证据查询
-- 生成日期：2026-09-09（UTC）
-- 执行方式：只读，经 mcp-db-gateway（SSE http://10.238.3.43:8080/sse）
--           网关仅放行 SELECT / SHOW / DESCRIBE / EXPLAIN
-- 服务器命名：aws-luckyus-{service}-rw
-- 说明：本文件按核验项编号分段。每条查询前的 -- note: 说明该查询回答什么，
--       -- result: 给出本次真实返回结果的摘录（报告 03 中的每个数字都对应到这里）。
--       标记 [ERROR] 的查询是本次执行中失败的尝试，保留以说明排查过程。
-- 全程未执行任何 INSERT / UPDATE / DELETE / DDL / KILL / SET。
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. 数据源发现 —— 全机队表名扫描
--    对 list_servers 返回的全部 64 台 MySQL 逐台执行同一条语句（脚本 sweep_tables.py，
--    8 线程，约 90 秒，64/64 成功、0 报错）。
-- ---------------------------------------------------------------------
-- server: <每一台 aws-luckyus-*-rw>
-- note: 按表名模式在全机队定位考勤/排班/打卡/门店/闭店/请假相关表
-- result: 命中 40 台服务器；opempefficiency 26 张、iehr 43 张、opshop 15 张、
--         iadmin 14 张（全部为审批流表，无考勤表）、ibehr 11 张（全部 0 行）
SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_ROWS, CREATE_TIME, UPDATE_TIME, TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA NOT IN ('mysql','information_schema','performance_schema','sys')
  AND TABLE_NAME REGEXP 'attend|clock|punch|shift|schedul|roster|work_hour|working|employee|emp_|staff|store|shop|closure|close|business_hour|leave|absence|approval|position|post|area|holiday|vacation|pto'
ORDER BY TABLE_SCHEMA, TABLE_NAME;


-- =====================================================================
-- SCHEMA — 核心表结构提取
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: column definitions for core tables on luckyus_opempefficiency
-- result: count=284
--   {"TABLE_NAME": "t_attendance", "ORDINAL_POSITION": 1, "COLUMN_NAME": "id", "COLUMN_TYPE": "bigint unsigned", "IS_NULLABLE": "NO", "COLUMN_KEY": "PRI", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "主键Id"}
--   {"TABLE_NAME": "t_attendance", "ORDINAL_POSITION": 2, "COLUMN_NAME": "tenant", "COLUMN_TYPE": "varchar(4)", "IS_NULLABLE": "NO", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "租户"}
--   {"TABLE_NAME": "t_attendance", "ORDINAL_POSITION": 3, "COLUMN_NAME": "emp_no", "COLUMN_TYPE": "varchar(20)", "IS_NULLABLE": "NO", "COLUMN_KEY": "MUL", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "员工编号"}
--   {"TABLE_NAME": "t_attendance", "ORDINAL_POSITION": 4, "COLUMN_NAME": "attendance_date", "COLUMN_TYPE": "date", "IS_NULLABLE": "NO", "COLUMN_KEY": "MUL", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "考勤日期"}
--   {"TABLE_NAME": "t_attendance", "ORDINAL_POSITION": 5, "COLUMN_NAME": "type", "COLUMN_TYPE": "tinyint(1)", "IS_NULLABLE": "YES", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "班次类型 1:考勤，3:会议，4:培训 5:请假 6:其他 9:训练"}
--   {"TABLE_NAME": "t_attendance", "ORDINAL_POSITION": 6, "COLUMN_NAME": "scheduling_dept_id", "COLUMN_TYPE": "bigint", "IS_NULLABLE": "YES", "COLUMN_KEY": "MUL", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "排班门店Id"}
--   {"TABLE_NAME": "t_attendance", "ORDINAL_POSITION": 7, "COLUMN_NAME": "scheduling_period", "COLUMN_TYPE": "varchar(300)", "IS_NULLABLE": "YES", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "排班时段"}
--   {"TABLE_NAME": "t_attendance", "ORDINAL_POSITION": 8, "COLUMN_NAME": "rest_period", "COLUMN_TYPE": "varchar(300)", "IS_NULLABLE": "YES", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "休息时段"}
--   ... （共 284 行，此处摘录前 8 行）
SELECT TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='luckyus_opempefficiency' AND TABLE_NAME IN ('t_attendance','t_attendance_shift','t_clock_in','t_emp_scheduling','t_employee','t_attendance_config','t_attendance_change','t_working_time_apply','t_emp_snapshot','t_shop_info','t_attendance_remark')
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- server: aws-luckyus-opshop-rw
-- note: column definitions for core tables on luckyus_opshop
-- result: count=154
--   {"TABLE_NAME": "t_focus_closed_plan", "ORDINAL_POSITION": 1, "COLUMN_NAME": "id", "COLUMN_TYPE": "bigint unsigned", "IS_NULLABLE": "NO", "COLUMN_KEY": "PRI", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "主键"}
--   {"TABLE_NAME": "t_focus_closed_plan", "ORDINAL_POSITION": 2, "COLUMN_NAME": "tenant", "COLUMN_TYPE": "varchar(4)", "IS_NULLABLE": "NO", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "租户"}
--   {"TABLE_NAME": "t_focus_closed_plan", "ORDINAL_POSITION": 3, "COLUMN_NAME": "dept_id", "COLUMN_TYPE": "bigint", "IS_NULLABLE": "YES", "COLUMN_KEY": "MUL", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "门店部门Id"}
--   {"TABLE_NAME": "t_focus_closed_plan", "ORDINAL_POSITION": 4, "COLUMN_NAME": "reason_id", "COLUMN_TYPE": "bigint", "IS_NULLABLE": "YES", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "闭店原因Id"}
--   {"TABLE_NAME": "t_focus_closed_plan", "ORDINAL_POSITION": 5, "COLUMN_NAME": "reason_name", "COLUMN_TYPE": "varchar(100)", "IS_NULLABLE": "YES", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "闭店原因描述"}
--   {"TABLE_NAME": "t_focus_closed_plan", "ORDINAL_POSITION": 6, "COLUMN_NAME": "close_start_time", "COLUMN_TYPE": "datetime", "IS_NULLABLE": "YES", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "闭店开始时间"}
--   {"TABLE_NAME": "t_focus_closed_plan", "ORDINAL_POSITION": 7, "COLUMN_NAME": "close_end_time", "COLUMN_TYPE": "datetime", "IS_NULLABLE": "YES", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "闭店结束时间"}
--   {"TABLE_NAME": "t_focus_closed_plan", "ORDINAL_POSITION": 8, "COLUMN_NAME": "status", "COLUMN_TYPE": "tinyint(1)", "IS_NULLABLE": "YES", "COLUMN_KEY": "MUL", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "状态 0.待生效 1.生效 2.完成 3.取消"}
--   ... （共 154 行，此处摘录前 8 行）
SELECT TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='luckyus_opshop' AND TABLE_NAME IN ('t_shop_info','t_shop_opening_time','t_shop_opening_plan','t_shop_focus_operation_log','t_nobody_focus_closed_log','t_focus_closed_reason','t_focus_closed_plan','t_shop_focus_closed_log')
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- server: aws-luckyus-iehr-rw
-- note: column definitions for core tables on luckyus_iehr
-- result: count=146
--   {"TABLE_NAME": "t_ehr_employee", "ORDINAL_POSITION": 1, "COLUMN_NAME": "id", "COLUMN_TYPE": "bigint unsigned", "IS_NULLABLE": "NO", "COLUMN_KEY": "PRI", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "t_ehr_employee_id"}
--   {"TABLE_NAME": "t_ehr_employee", "ORDINAL_POSITION": 2, "COLUMN_NAME": "name", "COLUMN_TYPE": "varchar(400)", "IS_NULLABLE": "NO", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "员工名称"}
--   {"TABLE_NAME": "t_ehr_employee", "ORDINAL_POSITION": 3, "COLUMN_NAME": "nick_name", "COLUMN_TYPE": "varchar(400)", "IS_NULLABLE": "YES", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "员工昵称"}
--   {"TABLE_NAME": "t_ehr_employee", "ORDINAL_POSITION": 4, "COLUMN_NAME": "emp_no", "COLUMN_TYPE": "varchar(40)", "IS_NULLABLE": "NO", "COLUMN_KEY": "MUL", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "员工编号"}
--   {"TABLE_NAME": "t_ehr_employee", "ORDINAL_POSITION": 5, "COLUMN_NAME": "sex", "COLUMN_TYPE": "tinyint", "IS_NULLABLE": "YES", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "性别 0-男，1-女"}
--   {"TABLE_NAME": "t_ehr_employee", "ORDINAL_POSITION": 6, "COLUMN_NAME": "area_code", "COLUMN_TYPE": "varchar(20)", "IS_NULLABLE": "YES", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "地区区号"}
--   {"TABLE_NAME": "t_ehr_employee", "ORDINAL_POSITION": 7, "COLUMN_NAME": "telephone", "COLUMN_TYPE": "varchar(100)", "IS_NULLABLE": "YES", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "电话"}
--   {"TABLE_NAME": "t_ehr_employee", "ORDINAL_POSITION": 8, "COLUMN_NAME": "address", "COLUMN_TYPE": "varchar(1024)", "IS_NULLABLE": "YES", "COLUMN_KEY": "", "COLUMN_DEFAULT": null, "COLUMN_COMMENT": "地址"}
--   ... （共 146 行，此处摘录前 8 行）
SELECT TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='luckyus_iehr' AND TABLE_NAME IN ('t_ehr_employee','t_ehr_post','t_ehr_employee_leave_application','t_ehr_employee_leave_application_day_detail','t_ehr_employee_leave_type','t_ehr_employee_post_relation','t_ehr_employee_employment_period')
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- server: aws-luckyus-opempefficiency-rw
-- note: columns of the store-employee mirror t_employee
-- result: count=29
--   {"COLUMN_NAME": "id", "COLUMN_TYPE": "bigint unsigned", "COLUMN_COMMENT": "主键Id"}
--   {"COLUMN_NAME": "tenant", "COLUMN_TYPE": "varchar(4)", "COLUMN_COMMENT": "租户"}
--   {"COLUMN_NAME": "emp_id", "COLUMN_TYPE": "bigint", "COLUMN_COMMENT": "员工id"}
--   {"COLUMN_NAME": "dept_id", "COLUMN_TYPE": "bigint", "COLUMN_COMMENT": "所属部门Id"}
--   {"COLUMN_NAME": "emp_no", "COLUMN_TYPE": "varchar(20)", "COLUMN_COMMENT": "员工编号"}
--   {"COLUMN_NAME": "name", "COLUMN_TYPE": "varchar(400)", "COLUMN_COMMENT": "员工名称"}
--   {"COLUMN_NAME": "sex", "COLUMN_TYPE": "tinyint(1)", "COLUMN_COMMENT": "性别 0-男，1-女"}
--   {"COLUMN_NAME": "status", "COLUMN_TYPE": "tinyint(1)", "COLUMN_COMMENT": "员工状态  0-离职，1-在职"}
--   ... （共 29 行，此处摘录前 8 行）
SELECT COLUMN_NAME,COLUMN_TYPE,COLUMN_COMMENT FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='luckyus_opempefficiency' AND TABLE_NAME='t_employee' ORDER BY ORDINAL_POSITION;

-- server: aws-luckyus-opempefficiency-rw
-- note: columns of t_emp_snapshot (门店员工快照表)
-- result: count=26
--   {"COLUMN_NAME": "id", "COLUMN_TYPE": "bigint unsigned", "COLUMN_COMMENT": "主键Id"}
--   {"COLUMN_NAME": "tenant", "COLUMN_TYPE": "varchar(4)", "COLUMN_COMMENT": "租户"}
--   {"COLUMN_NAME": "dept_id", "COLUMN_TYPE": "bigint", "COLUMN_COMMENT": "所属部门Id"}
--   {"COLUMN_NAME": "emp_no", "COLUMN_TYPE": "varchar(20)", "COLUMN_COMMENT": "员工编号"}
--   {"COLUMN_NAME": "name", "COLUMN_TYPE": "varchar(400)", "COLUMN_COMMENT": "员工名称"}
--   {"COLUMN_NAME": "sex", "COLUMN_TYPE": "tinyint(1)", "COLUMN_COMMENT": "性别 0-男，1-女"}
--   {"COLUMN_NAME": "status", "COLUMN_TYPE": "tinyint(1)", "COLUMN_COMMENT": "员工状态  0-离职，1-在职"}
--   {"COLUMN_NAME": "property", "COLUMN_TYPE": "tinyint(1)", "COLUMN_COMMENT": "员工性质0-全职，1-兼职，2-实习，3-外包"}
--   ... （共 26 行，此处摘录前 8 行）
SELECT COLUMN_NAME,COLUMN_TYPE,COLUMN_COMMENT FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='luckyus_opempefficiency' AND TABLE_NAME='t_emp_snapshot' ORDER BY ORDINAL_POSITION;


-- =====================================================================
-- F-01 — 排班是否精确到班次级起止时间（澄清项 B-03，P0）
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: rows in t_emp_scheduling per employee-day, Aug 2026, status=1
-- result: count=2
--   {"n_rows_per_emp_day": 1, "emp_days": 2861}
--   {"n_rows_per_emp_day": 2, "emp_days": 62}
SELECT n_rows_per_emp_day, COUNT(*) emp_days FROM (
  SELECT emp_no, scheduling_date, COUNT(*) n_rows_per_emp_day
  FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' AND status=1 AND scheduling_date>='2026-08-01' AND scheduling_date<'2026-09-01'
  GROUP BY emp_no, scheduling_date) t GROUP BY n_rows_per_emp_day ORDER BY n_rows_per_emp_day;

-- server: aws-luckyus-opempefficiency-rw
-- note: segment count inside scheduling_times string
-- [ERROR] Permission denied for operation
SELECT CHAR_LENGTH(scheduling_times)-CHAR_LENGTH(REPLACE(scheduling_times,',',''))+1 n_segments, COUNT(*) c
FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' AND status=1 AND scheduling_date>='2026-08-01' AND scheduling_date<'2026-09-01'
AND scheduling_times IS NOT NULL AND scheduling_times<>'' GROUP BY 1 ORDER BY 1;

-- server: aws-luckyus-opempefficiency-rw
-- note: status/source_Type/work_type/cross_day_type enum distribution
-- result: count=10
--   {"status": 1, "source_Type": "scheduling", "work_type": "1", "cross_day_type": 0, "c": 36869}
--   {"status": 2, "source_Type": "scheduling", "work_type": "1", "cross_day_type": 0, "c": 3507}
--   {"status": 1, "source_Type": "working_time_apply", "work_type": "4", "cross_day_type": 0, "c": 863}
--   {"status": 2, "source_Type": "working_time_apply", "work_type": "4", "cross_day_type": 0, "c": 115}
--   {"status": 1, "source_Type": "working_time_apply", "work_type": "3", "cross_day_type": 0, "c": 97}
--   {"status": 2, "source_Type": "working_time_apply", "work_type": "3", "cross_day_type": 0, "c": 27}
--   {"status": 0, "source_Type": "working_time_apply", "work_type": "4", "cross_day_type": 0, "c": 9}
--   {"status": 2, "source_Type": "scheduling", "work_type": "1", "cross_day_type": 4, "c": 3}
--   ... （共 10 行，此处摘录前 8 行）
SELECT status,source_Type,work_type,cross_day_type,COUNT(*) c FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' GROUP BY 1,2,3,4 ORDER BY c DESC;

-- server: aws-luckyus-opempefficiency-rw
-- note: de-identified sample of schedule detail rows
-- result: count=10
--   {"emp_h": "344e24d0", "scheduling_date": "2026-08-10", "scheduling_dept_id": 20009, "work_type": "1", "source_Type": "scheduling", "status": 1, "version": 4, "scheduling_times": "13:30~21:00", "rest_times": "16:45~17:30", "effect_minutes": 405, "effect_hours": 6.75, "cross_day_type": 0, "create_time ...
--   {"emp_h": "d56466af", "scheduling_date": "2026-08-10", "scheduling_dept_id": 20009, "work_type": "1", "source_Type": "scheduling", "status": 1, "version": 4, "scheduling_times": "10:00~17:00", "rest_times": "13:00~13:45", "effect_minutes": 375, "effect_hours": 6.25, "cross_day_type": 0, "create_time ...
--   {"emp_h": "c4b53d79", "scheduling_date": "2026-08-10", "scheduling_dept_id": 20009, "work_type": "1", "source_Type": "scheduling", "status": 1, "version": 4, "scheduling_times": "06:00~14:00", "rest_times": "10:00~10:45", "effect_minutes": 435, "effect_hours": 7.25, "cross_day_type": 0, "create_time ...
--   {"emp_h": "df7dd0fb", "scheduling_date": "2026-08-10", "scheduling_dept_id": 20009, "work_type": "1", "source_Type": "scheduling", "status": 1, "version": 4, "scheduling_times": "13:00~21:00", "rest_times": "16:00~16:45", "effect_minutes": 435, "effect_hours": 7.25, "cross_day_type": 0, "create_time ...
--   {"emp_h": "e75c780b", "scheduling_date": "2026-08-10", "scheduling_dept_id": 20009, "work_type": "1", "source_Type": "scheduling", "status": 1, "version": 4, "scheduling_times": "06:00~13:30", "rest_times": "10:00~10:45", "effect_minutes": 405, "effect_hours": 6.75, "cross_day_type": 0, "create_time ...
--   {"emp_h": "9299c10a", "scheduling_date": "2026-08-11", "scheduling_dept_id": 20009, "work_type": "1", "source_Type": "scheduling", "status": 1, "version": 5, "scheduling_times": "13:30~21:00", "rest_times": "16:45~17:30", "effect_minutes": 405, "effect_hours": 6.75, "cross_day_type": 0, "create_time ...
--   {"emp_h": "24a9860c", "scheduling_date": "2026-08-11", "scheduling_dept_id": 20009, "work_type": "1", "source_Type": "scheduling", "status": 1, "version": 5, "scheduling_times": "06:00~13:30", "rest_times": "10:00~10:45", "effect_minutes": 405, "effect_hours": 6.75, "cross_day_type": 0, "create_time ...
--   {"emp_h": "d56466af", "scheduling_date": "2026-08-11", "scheduling_dept_id": 20009, "work_type": "1", "source_Type": "scheduling", "status": 1, "version": 5, "scheduling_times": "10:00~17:00", "rest_times": "13:00~13:45", "effect_minutes": 375, "effect_hours": 6.25, "cross_day_type": 0, "create_time ...
--   ... （共 10 行，此处摘录前 8 行）
SELECT LEFT(SHA2(emp_no,256),8) emp_h, scheduling_date, scheduling_dept_id, work_type, source_Type, status, version,
 scheduling_times, rest_times, effect_minutes, effect_hours, cross_day_type, create_time, modify_time
FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' AND status=1 AND scheduling_date BETWEEN '2026-08-10' AND '2026-08-16' ORDER BY id LIMIT 10;

-- server: aws-luckyus-opempefficiency-rw
-- note: format validity of scheduling_times string
-- result: count=1
--   {"empty_times": 0.0, "well_formed": 35754.0, "total": 35754}
SELECT SUM(scheduling_times IS NULL OR scheduling_times='') AS empty_times,
 SUM(scheduling_times REGEXP '^([0-9]{2}:[0-9]{2}~[0-9]{2}:[0-9]{2})(,[0-9]{2}:[0-9]{2}~[0-9]{2}:[0-9]{2})*$') AS well_formed,
 COUNT(*) total FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' AND status=1 AND scheduling_date>='2025-09-01';

-- server: aws-luckyus-opempefficiency-rw
-- note: multi-segment scheduling_times/rest_times counts
-- result: count=1
--   {"multi_seg_shift": 26.0, "multi_seg_rest": 12.0, "no_rest": 2419.0, "total": 35754}
SELECT SUM(scheduling_times LIKE '%,%') multi_seg_shift, SUM(rest_times LIKE '%,%') multi_seg_rest,
 SUM(rest_times IS NULL OR rest_times='') no_rest, COUNT(*) total
FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' AND status=1 AND scheduling_date>='2025-09-01';

-- server: aws-luckyus-opempefficiency-rw
-- note: composition of employee-days carrying more than one schedule row
-- result: count=3
--   {"source_Type": "scheduling", "work_type": "1", "c": 120}
--   {"source_Type": "working_time_apply", "work_type": "4", "c": 2}
--   {"source_Type": "working_time_apply", "work_type": "3", "c": 2}
SELECT s.source_Type, s.work_type, COUNT(*) c FROM luckyus_opempefficiency.t_emp_scheduling s
JOIN (SELECT emp_no,scheduling_date FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' AND status=1
      AND scheduling_date>='2026-08-01' AND scheduling_date<'2026-09-01' GROUP BY 1,2 HAVING COUNT(*)>1) d
 ON d.emp_no=s.emp_no AND d.scheduling_date=s.scheduling_date
WHERE s.tenant='LKUS' AND s.status=1 AND s.scheduling_date>='2026-08-01' AND s.scheduling_date<'2026-09-01'
GROUP BY 1,2 ORDER BY c DESC;


-- =====================================================================
-- F-02 — iAdmin 是否已有异常判定结果（澄清项 B-02，P0）
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: enum distribution of attendance_status / except_type / except_type_list on t_attendance_shift
-- [ERROR] Error: (1046, 'No database selected')
SELECT attendance_status,except_type,except_type_list,COUNT(*) c,MIN(attendance_date) min_d,MAX(attendance_date) max_d
FROM t_attendance_shift WHERE tenant='LKUS' GROUP BY attendance_status,except_type,except_type_list ORDER BY c DESC;

-- server: aws-luckyus-opempefficiency-rw
-- note: enum distribution on t_attendance (day grain)
-- [ERROR] Error: (1046, 'No database selected')
SELECT attendance_status,except_type,COUNT(*) c FROM t_attendance WHERE tenant='LKUS' GROUP BY attendance_status,except_type ORDER BY c DESC;

-- server: aws-luckyus-opempefficiency-rw
-- note: enum distribution attendance_status/except_type/except_type_list
-- result: count=9
--   {"attendance_status": 1, "except_type": 0, "except_type_list": "0", "c": 17644}
--   {"attendance_status": 0, "except_type": 1, "except_type_list": "1", "c": 15126}
--   {"attendance_status": 0, "except_type": 2, "except_type_list": "2", "c": 3881}
--   {"attendance_status": null, "except_type": null, "except_type_list": null, "c": 2902}
--   {"attendance_status": 1, "except_type": 0, "except_type_list": "", "c": 1099}
--   {"attendance_status": 0, "except_type": 4, "except_type_list": "4", "c": 890}
--   {"attendance_status": 0, "except_type": 3, "except_type_list": "3", "c": 597}
--   {"attendance_status": 0, "except_type": 1, "except_type_list": "1,3", "c": 86}
--   ... （共 9 行，此处摘录前 8 行）
SELECT attendance_status,except_type,except_type_list,COUNT(*) c FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' GROUP BY attendance_status,except_type,except_type_list ORDER BY c DESC;

-- server: aws-luckyus-opempefficiency-rw
-- note: enum distribution on t_attendance
-- result: count=6
--   {"attendance_status": 1, "except_type": 0, "c": 18671}
--   {"attendance_status": 0, "except_type": 1, "c": 15212}
--   {"attendance_status": 0, "except_type": 2, "c": 3869}
--   {"attendance_status": null, "except_type": null, "c": 2910}
--   {"attendance_status": 0, "except_type": 3, "c": 584}
--   {"attendance_status": 0, "except_type": 4, "c": 552}
SELECT attendance_status,except_type,COUNT(*) c FROM luckyus_opempefficiency.t_attendance WHERE tenant='LKUS' GROUP BY attendance_status,except_type ORDER BY c DESC;

-- server: aws-luckyus-opempefficiency-rw
-- note: shift type enum
-- result: count=5
--   {"type": 1, "c": 37786}
--   {"type": 9, "c": 3513}
--   {"type": 4, "c": 837}
--   {"type": 3, "c": 97}
--   {"type": 5, "c": 1}
SELECT type,COUNT(*) c FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' GROUP BY type ORDER BY c DESC;

-- server: aws-luckyus-opempefficiency-rw
-- note: split except_type=1 (late+early merged) into late-only / early-only / both by recomputation
-- [ERROR] Error: (1064, "You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version for the right syntax to use near 'both,\n SUM(late_min<=0 AND early_min<=0) neither,
SELECT
 SUM(late_min>0 AND early_min<=0) late_only,
 SUM(late_min<=0 AND early_min>0) early_only,
 SUM(late_min>0 AND early_min>0) both,
 SUM(late_min<=0 AND early_min<=0) neither,
 COUNT(*) n
FROM (
 SELECT TIMESTAMPDIFF(MINUTE, STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',1),'%H:%i'),
                              STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',1),'%H:%i:%s')) late_min,
        TIMESTAMPDIFF(MINUTE, STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',-1),'%H:%i:%s'),
                              STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',-1),'%H:%i')) early_min
 FROM luckyus_opempefficiency.t_attendance_shift
 WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01'
   AND except_type=1 AND scheduling_period LIKE '%~%' AND clock_in_period LIKE '_%~_%'
   AND scheduling_period NOT LIKE '%,%' AND clock_in_period NOT LIKE '%,%'
) t;

-- server: aws-luckyus-opempefficiency-rw
-- note: recomputability of except_type=1 rows
-- result: count=1
--   {"all_except1": 1076, "multi_segment": 0.0, "one_sided_or_empty": 0.0}
SELECT COUNT(*) all_except1,
 SUM(scheduling_period LIKE '%,%' OR clock_in_period LIKE '%,%') multi_segment,
 SUM(clock_in_period NOT LIKE '_%~_%') one_sided_or_empty
FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01' AND except_type=1;

-- server: aws-luckyus-opempefficiency-rw
-- note: recompute late vs early split from scheduled vs clocked period strings
-- result: count=1
--   {"late_only": 504.0, "early_only": 314.0, "late_and_early": 97.0, "neither_side": 161.0, "any_late": 601.0, "any_early": 411.0, "n": 1076}
SELECT
 SUM(late_min>0 AND early_min<=0) late_only,
 SUM(late_min<=0 AND early_min>0) early_only,
 SUM(late_min>0 AND early_min>0) late_and_early,
 SUM(late_min<=0 AND early_min<=0) neither_side,
 SUM(late_min>0) any_late, SUM(early_min>0) any_early, COUNT(*) n
FROM (
 SELECT TIMESTAMPDIFF(MINUTE, STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',1),'%H:%i'),
                              STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',1),'%H:%i:%s')) late_min,
        TIMESTAMPDIFF(MINUTE, STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',-1),'%H:%i:%s'),
                              STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',-1),'%H:%i')) early_min
 FROM luckyus_opempefficiency.t_attendance_shift
 WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01'
   AND except_type=1 AND scheduling_period LIKE '%~%' AND clock_in_period LIKE '_%~_%'
) t;

-- server: aws-luckyus-opempefficiency-rw
-- note: infer the late/early tolerance threshold iAdmin applies
-- result: count=2
--   {"except_type": 0, "min_late": -719, "max_late": 0, "late_1_5": 0.0, "late_gt5": 0.0, "not_late": 1561.0, "early_1_5": 0.0, "early_gt5": 0.0, "n": 1561}
--   {"except_type": 1, "min_late": -488, "max_late": 480, "late_1_5": 250.0, "late_gt5": 351.0, "not_late": 475.0, "early_1_5": 72.0, "early_gt5": 339.0, "n": 1076}
SELECT except_type,
 MIN(late_min) min_late, MAX(late_min) max_late,
 SUM(late_min BETWEEN 1 AND 5) late_1_5, SUM(late_min>5) late_gt5, SUM(late_min<=0) not_late,
 SUM(early_min BETWEEN 1 AND 5) early_1_5, SUM(early_min>5) early_gt5, COUNT(*) n
FROM (
 SELECT except_type,
   TIMESTAMPDIFF(MINUTE, STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',1),'%H:%i'),
                         STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',1),'%H:%i:%s')) late_min,
   TIMESTAMPDIFF(MINUTE, STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',-1),'%H:%i:%s'),
                         STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',-1),'%H:%i')) early_min
 FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01'
   AND except_type IN (0,1) AND scheduling_period LIKE '%~%' AND clock_in_period LIKE '_%~_%') t
GROUP BY except_type;

-- server: aws-luckyus-opempefficiency-rw
-- note: columns of the attendance change/appeal table
-- result: count=49
--   {"COLUMN_NAME": "id", "COLUMN_TYPE": "bigint unsigned", "COLUMN_COMMENT": "主键id"}
--   {"COLUMN_NAME": "tenant", "COLUMN_TYPE": "varchar(4)", "COLUMN_COMMENT": "租户"}
--   {"COLUMN_NAME": "type", "COLUMN_TYPE": "tinyint(1)", "COLUMN_COMMENT": "1 补卡 2排班变更"}
--   {"COLUMN_NAME": "sub_type", "COLUMN_TYPE": "int", "COLUMN_COMMENT": "101 常规补卡,102 异常补卡；调整班次 201，新增班次 202，删除班次203，替换班次204 "}
--   {"COLUMN_NAME": "attendance_type", "COLUMN_TYPE": "tinyint(1)", "COLUMN_COMMENT": "班次类型"}
--   {"COLUMN_NAME": "status", "COLUMN_TYPE": "tinyint(1)", "COLUMN_COMMENT": "1 已新建 2 已同意 3 已拒绝 4 已失效"}
--   {"COLUMN_NAME": "attendance_date", "COLUMN_TYPE": "date", "COLUMN_COMMENT": "考勤日期"}
--   {"COLUMN_NAME": "emp_no", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "员工编号"}
--   ... （共 49 行，此处摘录前 8 行）
SELECT COLUMN_NAME,COLUMN_TYPE,COLUMN_COMMENT FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='luckyus_opempefficiency' AND TABLE_NAME='t_attendance_change' ORDER BY ORDINAL_POSITION;

-- server: aws-luckyus-opempefficiency-rw
-- note: sample of except_type=1 rows that recomputation does not explain
-- result: count=0
SELECT LEFT(SHA2(emp_no,256),8) emp_h, attendance_date, scheduling_period, rest_period, clock_in_period,
 scheduling_hours, effective_hours, attendance_change_id, attendance_remark_id
FROM luckyus_opempefficiency.t_attendance_shift
WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01' AND except_type=1
 AND scheduling_period LIKE '%~%' AND clock_in_period LIKE '_%~_%'
 AND STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',1),'%H:%i:%s') <= STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',1),'%H:%i')
 AND STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',-1),'%H:%i:%s') >= STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',-1),'%H:%i')
LIMIT 8;

-- server: aws-luckyus-opempefficiency-rw
-- note: are the unexplained late/early rows driven by over-long mid-shift breaks?
-- result: count=1
--   {"eff_below_sched": null, "eff_ge_sched": null, "n": 0}
SELECT SUM(effective_hours < scheduling_hours) eff_below_sched, SUM(effective_hours>=scheduling_hours) eff_ge_sched, COUNT(*) n
FROM luckyus_opempefficiency.t_attendance_shift
WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01' AND except_type=1
 AND scheduling_period LIKE '%~%' AND clock_in_period LIKE '_%~_%'
 AND STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',1),'%H:%i:%s') <= STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',1),'%H:%i')
 AND STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',-1),'%H:%i:%s') >= STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',-1),'%H:%i');

-- server: aws-luckyus-opempefficiency-rw
-- note: distribution of the recomputed minutes for rows flagged late/early but neither by clock-boundary math
-- result: count=15
--   {"late_min": 0, "early_min": 0, "c": 25}
--   {"late_min": 0, "early_min": -1, "c": 16}
--   {"late_min": 0, "early_min": -2, "c": 11}
--   {"late_min": 0, "early_min": -5, "c": 7}
--   {"late_min": 0, "early_min": -9, "c": 7}
--   {"late_min": 0, "early_min": -6, "c": 5}
--   {"late_min": 0, "early_min": -3, "c": 5}
--   {"late_min": 0, "early_min": -8, "c": 4}
--   ... （共 15 行，此处摘录前 8 行）
SELECT late_min, early_min, COUNT(*) c FROM (
 SELECT TIMESTAMPDIFF(MINUTE, STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',1),'%H:%i'),
                              STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',1),'%H:%i:%s')) late_min,
        TIMESTAMPDIFF(MINUTE, STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',-1),'%H:%i:%s'),
                              STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',-1),'%H:%i')) early_min
 FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01'
  AND except_type=1 AND scheduling_period LIKE '%~%' AND clock_in_period LIKE '_%~_%') t
WHERE late_min<=0 AND early_min<=0 GROUP BY 1,2 ORDER BY c DESC LIMIT 15;

-- server: aws-luckyus-opempefficiency-rw
-- note: late/early split recomputed at SECOND resolution
-- result: count=1
--   {"late_by_seconds": 765.0, "early_by_seconds": 438.0, "still_neither": 0.0, "n": 1076}
SELECT SUM(late_sec>0) late_by_seconds, SUM(early_sec>0) early_by_seconds,
 SUM(late_sec<=0 AND early_sec<=0) still_neither, COUNT(*) n FROM (
 SELECT TIMESTAMPDIFF(SECOND, STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',1),'%H:%i'),
                              STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',1),'%H:%i:%s')) late_sec,
        TIMESTAMPDIFF(SECOND, STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',-1),'%H:%i:%s'),
                              STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',-1),'%H:%i')) early_sec
 FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01'
  AND except_type=1 AND scheduling_period LIKE '%~%' AND clock_in_period LIKE '_%~_%') t;

-- server: aws-luckyus-opempefficiency-rw
-- note: final late/early decomposition of except_type=1 at second resolution
-- result: count=1
--   {"late_only": 638.0, "early_only": 311.0, "late_and_early": 127.0, "neither": 0.0, "n": 1076}
SELECT SUM(late_sec>0 AND early_sec<=0) late_only, SUM(late_sec<=0 AND early_sec>0) early_only,
 SUM(late_sec>0 AND early_sec>0) late_and_early, SUM(late_sec<=0 AND early_sec<=0) neither, COUNT(*) n FROM (
 SELECT TIMESTAMPDIFF(SECOND, STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',1),'%H:%i'),
                              STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',1),'%H:%i:%s')) late_sec,
        TIMESTAMPDIFF(SECOND, STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',-1),'%H:%i:%s'),
                              STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',-1),'%H:%i')) early_sec
 FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01'
  AND except_type=1 AND scheduling_period LIKE '%~%' AND clock_in_period LIKE '_%~_%') t;

-- server: aws-luckyus-opempefficiency-rw
-- note: control group: normal shifts should show zero late and zero early seconds
-- result: count=1
--   {"any_late": 0.0, "any_early": 0.0, "max_late_sec": 0, "max_early_sec": 0, "n": 1561}
SELECT SUM(late_sec>0) any_late, SUM(early_sec>0) any_early, MAX(late_sec) max_late_sec, MAX(early_sec) max_early_sec, COUNT(*) n FROM (
 SELECT TIMESTAMPDIFF(SECOND, STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',1),'%H:%i'),
                              STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',1),'%H:%i:%s')) late_sec,
        TIMESTAMPDIFF(SECOND, STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',-1),'%H:%i:%s'),
                              STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',-1),'%H:%i')) early_sec
 FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01'
  AND except_type=0 AND scheduling_period LIKE '%~%' AND clock_in_period LIKE '_%~_%') t;

-- server: aws-luckyus-opempefficiency-rw
-- note: exception totals used for the 74% share
-- result: count=1
--   {"all_exceptions": 20580.0, "late_or_early": 15212.0, "all_rows": 42234}
SELECT SUM(attendance_status=0) all_exceptions,
 SUM(attendance_status=0 AND except_type=1) late_or_early, COUNT(*) all_rows
FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS';

-- server: aws-luckyus-opempefficiency-rw
-- note: effect of a 1-minute / 5-minute tolerance on the Aug-2026 late & early counts
-- result: count=1
--   {"late_any_sec": 765.0, "late_ge_1min": 601.0, "late_ge_5min": 381.0, "early_any_sec": 438.0, "early_ge_1min": 411.0, "early_ge_5min": 354.0, "n": 1076}
SELECT SUM(late_sec>0) late_any_sec, SUM(late_sec>=60) late_ge_1min, SUM(late_sec>=300) late_ge_5min,
 SUM(early_sec>0) early_any_sec, SUM(early_sec>=60) early_ge_1min, SUM(early_sec>=300) early_ge_5min, COUNT(*) n FROM (
 SELECT TIMESTAMPDIFF(SECOND, STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',1),'%H:%i'),
                              STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',1),'%H:%i:%s')) late_sec,
        TIMESTAMPDIFF(SECOND, STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',-1),'%H:%i:%s'),
                              STR_TO_DATE(SUBSTRING_INDEX(scheduling_period,'~',-1),'%H:%i')) early_sec
 FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01'
  AND except_type=1 AND scheduling_period LIKE '%~%' AND clock_in_period LIKE '_%~_%') t;


-- =====================================================================
-- F-03 — 有效工时 Valid Working Hours 的真实算法（澄清项 L-03，P0）
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: punch_type/virtual_type/type enum distribution in t_clock_in
-- result: count=8
--   {"punch_type": 1, "virtual_type": 0, "type": 4, "c": 32004}
--   {"punch_type": 2, "virtual_type": 0, "type": 4, "c": 31936}
--   {"punch_type": 3, "virtual_type": 0, "type": 4, "c": 30312}
--   {"punch_type": 4, "virtual_type": 0, "type": 4, "c": 29886}
--   {"punch_type": 1, "virtual_type": 0, "type": 3, "c": 905}
--   {"punch_type": 4, "virtual_type": 0, "type": 3, "c": 693}
--   {"punch_type": 2, "virtual_type": 0, "type": 3, "c": 626}
--   {"punch_type": 3, "virtual_type": 0, "type": 3, "c": 443}
SELECT punch_type, virtual_type, type, COUNT(*) c FROM luckyus_opempefficiency.t_clock_in WHERE tenant='LKUS' GROUP BY 1,2,3 ORDER BY c DESC;

-- server: aws-luckyus-opempefficiency-rw
-- note: clock-in record count per employee-day, Aug 2026
-- result: count=9
--   {"n": 1, "emp_days": 7}
--   {"n": 2, "emp_days": 445}
--   {"n": 3, "emp_days": 25}
--   {"n": 4, "emp_days": 2078}
--   {"n": 5, "emp_days": 13}
--   {"n": 6, "emp_days": 59}
--   {"n": 7, "emp_days": 4}
--   {"n": 8, "emp_days": 8}
--   ... （共 9 行，此处摘录前 8 行）
SELECT n, COUNT(*) emp_days FROM (SELECT emp_no, attendance_date, COUNT(*) n FROM luckyus_opempefficiency.t_clock_in
 WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01' GROUP BY emp_no,attendance_date) t GROUP BY n ORDER BY n;

-- server: aws-luckyus-opempefficiency-rw
-- note: punch_type composition Aug 2026
-- result: count=1
--   {"c_in": 2721.0, "c_out": 2699.0, "c_bstart": 2198.0, "c_bend": 2186.0, "c_null": 0.0, "total": 9804}
SELECT SUM(punch_type=1) c_in, SUM(punch_type=2) c_out, SUM(punch_type=3) c_bstart, SUM(punch_type=4) c_bend,
 SUM(punch_type IS NULL) c_null, COUNT(*) total
FROM luckyus_opempefficiency.t_clock_in WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01';

-- server: aws-luckyus-opempefficiency-rw
-- note: sample: scheduled vs clocked periods and effective_hours
-- result: count=12
--   {"emp_h": "24a9860c", "attendance_date": "2026-08-11", "scheduling_period": "06:00~13:30", "rest_period": "10:00~10:45", "scheduling_hours": 6.75, "clock_in_period": "05:59:37~13:31:28", "effective_hours": 6.79, "attendance_status": 1, "except_type": 0, "clock_in_ids": "286057,286073,286078,286181"}
--   {"emp_h": "c4b53d79", "attendance_date": "2026-08-11", "scheduling_period": "06:00~14:00", "rest_period": "10:00~10:45", "scheduling_hours": 7.25, "clock_in_period": "05:50:33~14:03:00", "effective_hours": 7.47, "attendance_status": 1, "except_type": 0, "clock_in_ids": "286027,286082,286095,286197"}
--   {"emp_h": "24a9860c", "attendance_date": "2026-08-12", "scheduling_period": "06:00~13:30", "rest_period": "10:00~10:45", "scheduling_hours": 6.75, "clock_in_period": "06:05:45~13:30:42", "effective_hours": 6.65, "attendance_status": 0, "except_type": 1, "clock_in_ids": "286376,286422,286449,286492"}
--   {"emp_h": "9299c10a", "attendance_date": "2026-08-12", "scheduling_period": "10:00~17:00", "rest_period": "13:00~13:45", "scheduling_hours": 6.25, "clock_in_period": "09:55:16~17:02:52", "effective_hours": 6.57, "attendance_status": 1, "except_type": 0, "clock_in_ids": "286400,286512,286525,286588"}
--   {"emp_h": "344e24d0", "attendance_date": "2026-08-12", "scheduling_period": "13:00~21:00", "rest_period": "16:30~17:15", "scheduling_hours": 7.25, "clock_in_period": "12:57:22~20:55:21", "effective_hours": 7.22, "attendance_status": 0, "except_type": 1, "clock_in_ids": "286476,286602,286609,286653"}
--   {"emp_h": "e75c780b", "attendance_date": "2026-08-12", "scheduling_period": "13:30~21:00", "rest_period": "15:45~16:30", "scheduling_hours": 6.75, "clock_in_period": "13:29:00~20:55:01", "effective_hours": 6.69, "attendance_status": 0, "except_type": 1, "clock_in_ids": "286490,286564,286583,286652"}
--   {"emp_h": "9299c10a", "attendance_date": "2026-08-13", "scheduling_period": "13:00~21:00", "rest_period": "16:45~17:30", "scheduling_hours": 7.25, "clock_in_period": "13:29:07~21:11:11", "effective_hours": 6.95, "attendance_status": 0, "except_type": 1, "clock_in_ids": "286824,286916,286929,286970"}
--   {"emp_h": "d56466af", "attendance_date": "2026-08-13", "scheduling_period": "10:00~17:00", "rest_period": "13:00~13:45", "scheduling_hours": 6.25, "clock_in_period": "13:25:07~20:56:22", "effective_hours": 6.75, "attendance_status": 0, "except_type": 1, "clock_in_ids": "286823,286874,286897,286964"}
--   ... （共 12 行，此处摘录前 8 行）
SELECT LEFT(SHA2(emp_no,256),8) emp_h, attendance_date, scheduling_period, rest_period, scheduling_hours,
 clock_in_period, effective_hours, attendance_status, except_type, clock_in_ids
FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date BETWEEN '2026-08-11' AND '2026-08-13' AND clock_in_period IS NOT NULL AND clock_in_period<>'' ORDER BY id LIMIT 12;

-- server: aws-luckyus-opempefficiency-rw
-- note: effective_hours quality check
-- result: count=1
--   {"null_eff": 0.0, "zero_eff": 4913.0, "neg_eff": 0.0, "gt24": 0.0, "min_e": 0.0, "max_e": 20.19, "total": 38642}
SELECT SUM(effective_hours IS NULL) null_eff, SUM(effective_hours=0) zero_eff, SUM(effective_hours<0) neg_eff,
 SUM(effective_hours>24) gt24, MIN(effective_hours) min_e, MAX(effective_hours) max_e, COUNT(*) total
FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2025-09-01' AND attendance_date<='2026-09-08';

-- server: aws-luckyus-opempefficiency-rw
-- note: test whether effective_hours = clocked span minus scheduled rest
-- result: count=1
--   {"n": 2188, "eq_span_no_break": 81.0, "eq_span_minus_rest": 1334.0, "neither": 773.0}
SELECT
 COUNT(*) n,
 SUM(ABS(eff_min - span_min) <= 1) eq_span_no_break,
 SUM(ABS(eff_min - (span_min - rest_min)) <= 1) eq_span_minus_rest,
 SUM(ABS(eff_min - span_min) > 1 AND ABS(eff_min - (span_min-rest_min)) > 1) neither
FROM (
 SELECT ROUND(effective_hours*60) eff_min,
   TIMESTAMPDIFF(MINUTE, STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',1),'%H:%i:%s'),
                         STR_TO_DATE(SUBSTRING_INDEX(clock_in_period,'~',-1),'%H:%i:%s')) span_min,
   TIMESTAMPDIFF(MINUTE, STR_TO_DATE(SUBSTRING_INDEX(rest_period,'~',1),'%H:%i'),
                         STR_TO_DATE(SUBSTRING_INDEX(rest_period,'~',-1),'%H:%i')) rest_min
 FROM luckyus_opempefficiency.t_attendance_shift
 WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01'
   AND effective_hours>0 AND clock_in_period LIKE '_%~_%' AND clock_in_period NOT LIKE '%,%'
   AND rest_period LIKE '%~%' AND rest_period NOT LIKE '%,%'
) t;

-- server: aws-luckyus-opempefficiency-rw
-- note: which exception types carry effective_hours=0
-- result: count=6
--   {"except_type": null, "n": 2865, "zero_eff": 0.0}
--   {"except_type": 0, "n": 17112, "zero_eff": 0.0}
--   {"except_type": 1, "n": 13820, "zero_eff": 86.0}
--   {"except_type": 2, "n": 3595, "zero_eff": 3582.0}
--   {"except_type": 3, "n": 493, "zero_eff": 488.0}
--   {"except_type": 4, "n": 757, "zero_eff": 757.0}
SELECT except_type, COUNT(*) n, SUM(effective_hours=0) zero_eff
FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2025-09-01' AND attendance_date<='2026-09-08' GROUP BY 1 ORDER BY 1;

-- server: aws-luckyus-opempefficiency-rw
-- note: punch-type completeness per person-day
-- result: count=8
--   {"has_in": 1, "has_out": 1, "has_bstart": 1, "has_bend": 1, "emp_days": 2148}
--   {"has_in": 1, "has_out": 1, "has_bstart": 0, "has_bend": 0, "emp_days": 455}
--   {"has_in": 1, "has_out": 0, "has_bstart": 1, "has_bend": 1, "emp_days": 16}
--   {"has_in": 1, "has_out": 1, "has_bstart": 1, "has_bend": 0, "emp_days": 11}
--   {"has_in": 1, "has_out": 0, "has_bstart": 0, "has_bend": 0, "emp_days": 6}
--   {"has_in": 1, "has_out": 0, "has_bstart": 1, "has_bend": 0, "emp_days": 2}
--   {"has_in": 0, "has_out": 1, "has_bstart": 1, "has_bend": 1, "emp_days": 1}
--   {"has_in": 0, "has_out": 1, "has_bstart": 0, "has_bend": 0, "emp_days": 1}
SELECT has_in,has_out,has_bstart,has_bend,COUNT(*) emp_days FROM (
 SELECT emp_no,attendance_date, MAX(punch_type=1) has_in, MAX(punch_type=2) has_out, MAX(punch_type=3) has_bstart, MAX(punch_type=4) has_bend
 FROM luckyus_opempefficiency.t_clock_in WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01'
 GROUP BY 1,2) t GROUP BY 1,2,3,4 ORDER BY emp_days DESC;

-- server: aws-luckyus-opempefficiency-rw
-- note: validate effective_hours against actual break punches
-- result: count=1
--   {"n": 2697, "matches_actual_break": 2490.0, "matches_no_break": 438.0, "matches_neither": 204.0}
SELECT COUNT(*) n,
 SUM(ABS(eff_min-(span_min-act_break_min))<=1) matches_actual_break,
 SUM(ABS(eff_min-span_min)<=1) matches_no_break,
 SUM(ABS(eff_min-(span_min-act_break_min))>1 AND ABS(eff_min-span_min)>1) matches_neither
FROM (
 SELECT s.id, ROUND(s.effective_hours*60) eff_min,
  TIMESTAMPDIFF(MINUTE, MIN(CASE WHEN c.punch_type=1 THEN c.clock_in_time END), MAX(CASE WHEN c.punch_type=2 THEN c.clock_in_time END)) span_min,
  COALESCE(TIMESTAMPDIFF(MINUTE, MIN(CASE WHEN c.punch_type=3 THEN c.clock_in_time END), MAX(CASE WHEN c.punch_type=4 THEN c.clock_in_time END)),0) act_break_min
 FROM luckyus_opempefficiency.t_attendance_shift s JOIN luckyus_opempefficiency.t_clock_in c ON c.emp_no=s.emp_no AND c.attendance_date=s.attendance_date AND c.tenant='LKUS'
 WHERE s.tenant='LKUS' AND s.attendance_date>='2026-08-01' AND s.attendance_date<'2026-09-01' AND s.effective_hours>0
 GROUP BY s.id, s.effective_hours HAVING span_min IS NOT NULL) t;

-- server: aws-luckyus-opempefficiency-rw
-- note: the attendance rule config table (2 rows)
-- result: count=2
--   {"id": 4, "tenant": "IQA2", "can_modified_days": 7, "effective_clock_in_time": 1.0, "effective_clock_out_time": 2.0, "create_time": "2023-04-27T16:39:27", "creator_name": "***", "create_by": 106, "modify_time": "2026-03-20T08:58:32", "modify_by": null, "modifier_name": null, "month_standa ...
--   {"id": 5, "tenant": "LKUS", "can_modified_days": 2, "effective_clock_in_time": 24.0, "effective_clock_out_time": 24.0, "create_time": "2023-04-27T16:39:27", "creator_name": "***", "create_by": 116, "modify_time": "2025-06-30T05:19:45", "modify_by": null, "modifier_name": null, "mont ...
SELECT id, tenant, can_modified_days, effective_clock_in_time, effective_clock_out_time,
       month_standard_work_hours, month_ot_work_hours, train_hours,
       half_day_leave_hours, all_day_leave_hours,
       work_time_audit_post_codes, compensation_audit_post_codes, schedule_change_audit_post_codes,
       compensation_view_self_post_codes, schedule_change_view_self_post_codes,
       create_time, modify_time
FROM luckyus_opempefficiency.t_attendance_config;   -- creator_name/modifier_name deliberately excluded (PII)

-- server: aws-luckyus-opempefficiency-rw
-- note: how many punches were created by request (makeup) vs device
-- result: count=1
--   {"makeup_or_requested": 119577.0, "device_punch": 0.0, "n": 119577}
SELECT SUM(request_by IS NOT NULL) makeup_or_requested, SUM(request_by IS NULL) device_punch, COUNT(*) n
FROM luckyus_opempefficiency.t_clock_in WHERE tenant='LKUS' AND attendance_date>='2025-09-01';

-- server: aws-luckyus-opempefficiency-rw
-- note: t_clock_in.type value totals
-- result: count=2
--   {"type": 4, "c": 124149}
--   {"type": 3, "c": 2667}
SELECT type, COUNT(*) c FROM luckyus_opempefficiency.t_clock_in WHERE tenant='LKUS' GROUP BY 1 ORDER BY c DESC;


-- =====================================================================
-- F-04 — 门店营业时间数据源（澄清项 S-09，P0）
-- =====================================================================

-- server: aws-luckyus-opshop-rw
-- note: daily business-hours table coverage
-- result: count=2
--   {"tenant": "IQA2", "rows_": 240146, "depts": 509, "min_d": "2025-03-20", "max_d": "2026-09-20", "biz_days": 239993.0, "closed_days": 0.0, "null_start": 153.0, "null_dur": 6084.0, "has_closed_ranges": 0.0}
--   {"tenant": "LKUS", "rows_": 6185, "depts": 25, "min_d": "2025-05-09", "max_d": "2026-09-20", "biz_days": 6162.0, "closed_days": 0.0, "null_start": 23.0, "null_dur": 300.0, "has_closed_ranges": 0.0}
SELECT tenant, COUNT(*) rows_, COUNT(DISTINCT dept_id) depts, MIN(date) min_d, MAX(date) max_d,
 SUM(is_business=1) biz_days, SUM(is_business=2) closed_days,
 SUM(opening_start_time IS NULL OR opening_start_time='') null_start,
 SUM(business_duration IS NULL) null_dur, SUM(closed_time_ranges IS NOT NULL AND closed_time_ranges<>'') has_closed_ranges
FROM luckyus_opshop.t_shop_opening_time GROUP BY tenant;

-- server: aws-luckyus-opshop-rw
-- note: sample daily business hours
-- result: count=12
--   {"dept_id": 1127, "date": "2026-08-11", "is_business": 1, "opening_start_time": "07:00", "opening_end_time": "19:00", "business_duration": 720, "closed_time_ranges": "", "update_time": "2026-08-11T04:01:01"}
--   {"dept_id": 1127, "date": "2026-08-12", "is_business": 1, "opening_start_time": "07:00", "opening_end_time": "19:00", "business_duration": 720, "closed_time_ranges": "", "update_time": "2026-08-12T04:01:00"}
--   {"dept_id": 1127, "date": "2026-08-13", "is_business": 1, "opening_start_time": "07:00", "opening_end_time": "19:00", "business_duration": 720, "closed_time_ranges": "", "update_time": "2026-08-13T04:01:00"}
--   {"dept_id": 1128, "date": "2026-08-11", "is_business": 1, "opening_start_time": "07:00", "opening_end_time": "19:00", "business_duration": 720, "closed_time_ranges": "", "update_time": "2026-08-11T04:01:01"}
--   {"dept_id": 1128, "date": "2026-08-12", "is_business": 1, "opening_start_time": "07:00", "opening_end_time": "19:00", "business_duration": 720, "closed_time_ranges": "", "update_time": "2026-08-12T04:01:00"}
--   {"dept_id": 1128, "date": "2026-08-13", "is_business": 1, "opening_start_time": "07:00", "opening_end_time": "19:00", "business_duration": 720, "closed_time_ranges": "", "update_time": "2026-08-13T04:01:00"}
--   {"dept_id": 1131, "date": "2026-08-11", "is_business": 1, "opening_start_time": "00:00", "opening_end_time": "24:00", "business_duration": 1440, "closed_time_ranges": "", "update_time": "2026-08-11T04:01:01"}
--   {"dept_id": 1131, "date": "2026-08-12", "is_business": 1, "opening_start_time": "00:00", "opening_end_time": "24:00", "business_duration": 1440, "closed_time_ranges": "", "update_time": "2026-08-12T04:01:00"}
--   ... （共 12 行，此处摘录前 8 行）
SELECT dept_id,date,is_business,opening_start_time,opening_end_time,business_duration,closed_time_ranges,update_time
FROM luckyus_opshop.t_shop_opening_time WHERE tenant='LKUS' AND date BETWEEN '2026-08-11' AND '2026-08-13' ORDER BY dept_id,date LIMIT 12;

-- server: aws-luckyus-opshop-rw
-- note: weekly/special business-hour plan structure
-- result: count=13
--   {"tenant": "IQA2", "date_type": 1, "date_mode": null, "date_apply": "", "is_business": 1, "c": 500, "depts": 500}
--   {"tenant": "IQA2", "date_type": 2, "date_mode": null, "date_apply": "", "is_business": 1, "c": 500, "depts": 500}
--   {"tenant": "IQA2", "date_type": 3, "date_mode": null, "date_apply": "", "is_business": 1, "c": 500, "depts": 500}
--   {"tenant": "LKUS", "date_type": 1, "date_mode": null, "date_apply": null, "is_business": 1, "c": 33, "depts": 33}
--   {"tenant": "LKUS", "date_type": 2, "date_mode": null, "date_apply": null, "is_business": 1, "c": 33, "depts": 33}
--   {"tenant": "LKUS", "date_type": 3, "date_mode": null, "date_apply": null, "is_business": 1, "c": 33, "depts": 33}
--   {"tenant": "IQA2", "date_type": 1, "date_mode": null, "date_apply": null, "is_business": 1, "c": 12, "depts": 12}
--   {"tenant": "IQA2", "date_type": 2, "date_mode": null, "date_apply": null, "is_business": 1, "c": 10, "depts": 10}
--   ... （共 13 行，此处摘录前 8 行）
SELECT tenant,date_type,date_mode,date_apply,is_business,COUNT(*) c,COUNT(DISTINCT dept_id) depts
FROM luckyus_opshop.t_shop_opening_plan GROUP BY 1,2,3,4,5 ORDER BY c DESC LIMIT 30;

-- server: aws-luckyus-opshop-rw
-- note: active stores with no daily business-hours rows in Aug 2026
-- result: count=1
--   {"active_stores_missing_aug_hours": 1}
SELECT COUNT(*) active_stores_missing_aug_hours FROM luckyus_opshop.t_shop_info si
WHERE si.tenant='LKUS' AND si.status=1
 AND NOT EXISTS (SELECT 1 FROM luckyus_opshop.t_shop_opening_time ot WHERE ot.dept_id=si.dept_id AND ot.date>='2026-08-01' AND ot.date<'2026-09-01');

-- server: aws-luckyus-opshop-rw
-- note: closure timestamps (datetime) vs business hours (HH:mm strings) on the same store-day
-- result: count=12
--   {"dept_id": 20029, "d": "2026-08-01", "closure_start_utc": "2026-08-01T10:10:01", "closure_end_utc": "2026-08-01T11:05:11", "closed_duration": 5, "opening_start_time": "07:00", "opening_end_time": "19:00", "business_duration": 714, "reason": "无人开早"}
--   {"dept_id": 20032, "d": "2026-08-01", "closure_start_utc": "2026-08-01T15:25:17", "closure_end_utc": "2026-08-01T15:35:02", "closed_duration": 9, "opening_start_time": "07:00", "opening_end_time": "20:00", "business_duration": 770, "reason": "In-store equipment malfunction."}
--   {"dept_id": 20028, "d": "2026-08-02", "closure_start_utc": "2026-08-02T10:10:00", "closure_end_utc": "2026-08-02T11:07:46", "closed_duration": 7, "opening_start_time": "07:00", "opening_end_time": "20:00", "business_duration": 772, "reason": "无人开早"}
--   {"dept_id": 20010, "d": "2026-08-02", "closure_start_utc": "2026-08-02T11:35:17", "closure_end_utc": "2026-08-02T13:00:36", "closed_duration": 60, "opening_start_time": "08:00", "opening_end_time": "18:00", "business_duration": 539, "reason": "One staff working"}
--   {"dept_id": 20016, "d": "2026-08-02", "closure_start_utc": "2026-08-02T17:00:48", "closure_end_utc": "2026-08-03T10:59:16", "closed_duration": 359, "opening_start_time": "07:00", "opening_end_time": "19:00", "business_duration": 360, "reason": "One staff working"}
--   {"dept_id": 20011, "d": "2026-08-02", "closure_start_utc": "2026-08-02T20:16:23", "closure_end_utc": "2026-08-03T00:08:39", "closed_duration": 193, "opening_start_time": "08:00", "opening_end_time": "19:30", "business_duration": 496, "reason": "One staff working"}
--   {"dept_id": 20035, "d": "2026-08-04", "closure_start_utc": "2026-08-04T10:10:00", "closure_end_utc": "2026-08-04T10:58:04", "closed_duration": 0, "opening_start_time": "07:00", "opening_end_time": "19:30", "business_duration": 750, "reason": "无人开早"}
--   {"dept_id": 20015, "d": "2026-08-04", "closure_start_utc": "2026-08-04T10:10:01", "closure_end_utc": "2026-08-04T10:59:56", "closed_duration": 0, "opening_start_time": "07:00", "opening_end_time": "20:00", "business_duration": 780, "reason": "无人开早"}
--   ... （共 12 行，此处摘录前 8 行）
SELECT l.dept_id, DATE(l.start_time) d, l.start_time closure_start_utc, l.end_time closure_end_utc, l.closed_duration,
 o.opening_start_time, o.opening_end_time, o.business_duration, l.reason
FROM luckyus_opshop.t_shop_focus_operation_log l JOIN luckyus_opshop.t_shop_opening_time o ON o.dept_id=l.dept_id AND o.date=DATE_FORMAT(l.start_time,'%Y-%m-%d') AND o.tenant='LKUS'
WHERE l.tenant='LKUS' AND l.operation_scene=1 AND l.start_time>='2026-08-01' ORDER BY l.start_time LIMIT 12;

-- server: aws-luckyus-opshop-rw
-- note: does business_duration already deduct forced-closure minutes?
-- result: count=1
--   {"store_days": 744, "equal_nominal": 696.0, "less_than_nominal": 48.0, "more_than_nominal": 0.0, "total_shortfall_min": 47814.0}
SELECT COUNT(*) store_days, SUM(nominal_min=business_duration) equal_nominal,
 SUM(business_duration<nominal_min) less_than_nominal, SUM(business_duration>nominal_min) more_than_nominal,
 SUM(nominal_min-business_duration) total_shortfall_min
FROM (SELECT dept_id,date,business_duration,
  TIMESTAMPDIFF(MINUTE, STR_TO_DATE(opening_start_time,'%H:%i'), STR_TO_DATE(IF(opening_end_time='24:00','23:59',opening_end_time),'%H:%i'))
   + IF(opening_end_time='24:00',1,0) nominal_min
 FROM luckyus_opshop.t_shop_opening_time WHERE tenant='LKUS' AND date>='2026-08-01' AND date<'2026-09-01' AND is_business=1 AND business_duration IS NOT NULL) t;

-- server: aws-luckyus-opshop-rw
-- note: store-days where actual business duration is below the nominal window
-- result: count=15
--   {"dept_id": 20032, "date": "2026-08-01", "opening_start_time": "07:00", "opening_end_time": "20:00", "business_duration": 770, "nominal_min": 780, "closed_min": 9.0}
--   {"dept_id": 20029, "date": "2026-08-01", "opening_start_time": "07:00", "opening_end_time": "19:00", "business_duration": 714, "nominal_min": 720, "closed_min": 5.0}
--   {"dept_id": 20010, "date": "2026-08-02", "opening_start_time": "08:00", "opening_end_time": "18:00", "business_duration": 539, "nominal_min": 600, "closed_min": 60.0}
--   {"dept_id": 20011, "date": "2026-08-02", "opening_start_time": "08:00", "opening_end_time": "19:30", "business_duration": 496, "nominal_min": 690, "closed_min": 193.0}
--   {"dept_id": 20016, "date": "2026-08-02", "opening_start_time": "07:00", "opening_end_time": "19:00", "business_duration": 360, "nominal_min": 720, "closed_min": 359.0}
--   {"dept_id": 20028, "date": "2026-08-02", "opening_start_time": "07:00", "opening_end_time": "20:00", "business_duration": 772, "nominal_min": 780, "closed_min": 7.0}
--   {"dept_id": 20011, "date": "2026-08-04", "opening_start_time": "07:00", "opening_end_time": "19:30", "business_duration": 657, "nominal_min": 750, "closed_min": 92.0}
--   {"dept_id": 20026, "date": "2026-08-08", "opening_start_time": "07:00", "opening_end_time": "19:00", "business_duration": 685, "nominal_min": 720, "closed_min": 34.0}
--   ... （共 15 行，此处摘录前 8 行）
SELECT o.dept_id, o.date, o.opening_start_time, o.opening_end_time, o.business_duration,
 TIMESTAMPDIFF(MINUTE, STR_TO_DATE(o.opening_start_time,'%H:%i'), STR_TO_DATE(o.opening_end_time,'%H:%i')) nominal_min,
 (SELECT SUM(l.closed_duration) FROM luckyus_opshop.t_shop_focus_operation_log l WHERE l.tenant='LKUS' AND l.dept_id=o.dept_id
   AND l.operation_scene=1 AND DATE(l.start_time)=o.date) closed_min
FROM luckyus_opshop.t_shop_opening_time o WHERE o.tenant='LKUS' AND o.date>='2026-08-01' AND o.date<'2026-09-01'
 AND o.business_duration < TIMESTAMPDIFF(MINUTE, STR_TO_DATE(o.opening_start_time,'%H:%i'), STR_TO_DATE(o.opening_end_time,'%H:%i'))
ORDER BY o.date LIMIT 15;


-- =====================================================================
-- F-05 — 时区与时间口径（澄清项 B-05，P0）
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: server/session timezone
-- result: count=1
--   {"gtz": "UTC", "stz": "UTC", "systz": "UTC", "now_": "2026-09-09T16:01:49", "utc_": "2026-09-09T16:01:49", "v": "8.4.9"}
SELECT @@global.time_zone gtz,@@session.time_zone stz,@@system_time_zone systz,NOW() now_,UTC_TIMESTAMP() utc_,VERSION() v;

-- server: aws-luckyus-opshop-rw
-- note: server/session timezone
-- result: count=1
--   {"gtz": "UTC", "stz": "UTC", "systz": "UTC", "now_": "2026-09-09T16:01:49", "utc_": "2026-09-09T16:01:49", "v": "8.4.10"}
SELECT @@global.time_zone gtz,@@session.time_zone stz,@@system_time_zone systz,NOW() now_,UTC_TIMESTAMP() utc_,VERSION() v;

-- server: aws-luckyus-iehr-rw
-- note: server/session timezone
-- result: count=1
--   {"gtz": "UTC", "stz": "UTC", "systz": "UTC", "now_": "2026-09-09T16:01:49", "utc_": "2026-09-09T16:01:49", "v": "8.4.9"}
SELECT @@global.time_zone gtz,@@session.time_zone stz,@@system_time_zone systz,NOW() now_,UTC_TIMESTAMP() utc_,VERSION() v;

-- server: aws-luckyus-opempefficiency-rw
-- note: raw clock rows behind clock_in_period '05:59:37~13:31:28' (attendance_date 2026-08-11)
-- result: count=5
--   {"id": 286057, "dept_id": 20009, "attendance_date": "2026-08-11", "clock_in_time": "2026-08-11T09:59:37", "punch_type": 1, "virtual_type": 0, "create_time": "2026-08-11T09:59:37"}
--   {"id": 286073, "dept_id": 20009, "attendance_date": "2026-08-11", "clock_in_time": "2026-08-11T13:00:00", "punch_type": 3, "virtual_type": 0, "create_time": "2026-08-11T13:00:00"}
--   {"id": 286078, "dept_id": 20009, "attendance_date": "2026-08-11", "clock_in_time": "2026-08-11T13:45:35", "punch_type": 4, "virtual_type": 0, "create_time": "2026-08-11T13:45:35"}
--   {"id": 286181, "dept_id": 20009, "attendance_date": "2026-08-11", "clock_in_time": "2026-08-11T17:31:28", "punch_type": 2, "virtual_type": 0, "create_time": "2026-08-11T17:31:28"}
--   {"id": 286718, "dept_id": 20009, "attendance_date": "2026-08-13", "clock_in_time": "2026-08-13T10:03:20", "punch_type": 2, "virtual_type": 0, "create_time": "2026-08-13T10:03:20"}
SELECT id,dept_id,attendance_date,clock_in_time,punch_type,virtual_type,create_time
FROM luckyus_opempefficiency.t_clock_in WHERE tenant='LKUS' AND id IN (286057,286073,286078,286181,286718) ORDER BY id;

-- server: aws-luckyus-opempefficiency-rw
-- note: hour-of-day distribution of clock_in_time
-- result: count=22
--   {"h": 0, "c": 610}
--   {"h": 1, "c": 379}
--   {"h": 2, "c": 26}
--   {"h": 3, "c": 1}
--   {"h": 5, "c": 1}
--   {"h": 7, "c": 1}
--   {"h": 8, "c": 2}
--   {"h": 9, "c": 772}
--   ... （共 22 行，此处摘录前 8 行）
SELECT HOUR(clock_in_time) h, COUNT(*) c FROM luckyus_opempefficiency.t_clock_in
WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01' GROUP BY 1 ORDER BY 1;

-- server: aws-luckyus-opshop-rw
-- note: t_shop_info columns
-- result: count=53
--   {"COLUMN_NAME": "id", "COLUMN_TYPE": "bigint unsigned", "COLUMN_COMMENT": "主键"}
--   {"COLUMN_NAME": "tenant", "COLUMN_TYPE": "varchar(4)", "COLUMN_COMMENT": "租户"}
--   {"COLUMN_NAME": "dept_id", "COLUMN_TYPE": "bigint", "COLUMN_COMMENT": "部门ID"}
--   {"COLUMN_NAME": "shop_no", "COLUMN_TYPE": "varchar(8)", "COLUMN_COMMENT": "门店序号"}
--   {"COLUMN_NAME": "shop_name", "COLUMN_TYPE": "varchar(128)", "COLUMN_COMMENT": "门店名称"}
--   {"COLUMN_NAME": "status", "COLUMN_TYPE": "int", "COLUMN_COMMENT": "门店状态"}
--   {"COLUMN_NAME": "dept_name", "COLUMN_TYPE": "varchar(128)", "COLUMN_COMMENT": "部门名称"}
--   {"COLUMN_NAME": "manager_name", "COLUMN_TYPE": "varchar(128)", "COLUMN_COMMENT": "负责人姓名"}
--   ... （共 53 行，此处摘录前 8 行）
SELECT COLUMN_NAME,COLUMN_TYPE,COLUMN_COMMENT FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='luckyus_opshop' AND TABLE_NAME='t_shop_info' ORDER BY ORDINAL_POSITION;

-- server: aws-luckyus-opempefficiency-rw
-- note: cross-midnight shift prevalence
-- result: count=1
--   {"n": 35754, "end_le_start": 0.0, "cross_day_flagged": 2.0, "touches_midnight": 2.0}
SELECT COUNT(*) n,
 SUM(SUBSTRING_INDEX(scheduling_times,'~',-1) <= SUBSTRING_INDEX(scheduling_times,'~',1)) end_le_start,
 SUM(cross_day_type<>0) cross_day_flagged,
 SUM(scheduling_times LIKE '%24:00%' OR scheduling_times LIKE '%00:00%') touches_midnight
FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' AND status=1 AND scheduling_date>='2025-09-01';

-- server: aws-luckyus-opempefficiency-rw
-- note: clocked periods whose end time is earlier than the start time
-- result: count=1
--   {"n": 32860, "clocked_cross_midnight": 0.0}
SELECT COUNT(*) n, SUM(SUBSTRING_INDEX(clock_in_period,'~',-1) < SUBSTRING_INDEX(clock_in_period,'~',1)) clocked_cross_midnight
FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2025-09-01' AND clock_in_period LIKE '_%~_%';


-- =====================================================================
-- F-06 — 跨店打卡的实际规模（澄清项 C-09）
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: cross-store clock-in scale, Aug 2026
-- result: count=1
--   {"shifts": 3128, "cross_store": 0.0, "emps_cross": 0, "depts_cross": 0, "null_clock_dept": 0.0, "null_sched_dept": 0.0}
SELECT COUNT(*) shifts, SUM(clock_in_dept_id<>scheduling_dept_id) cross_store,
 COUNT(DISTINCT CASE WHEN clock_in_dept_id<>scheduling_dept_id THEN emp_no END) emps_cross,
 COUNT(DISTINCT CASE WHEN clock_in_dept_id<>scheduling_dept_id THEN clock_in_dept_id END) depts_cross,
 SUM(clock_in_dept_id IS NULL) null_clock_dept, SUM(scheduling_dept_id IS NULL) null_sched_dept
FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01';

-- server: aws-luckyus-opempefficiency-rw
-- note: home store (dept_id) vs clock/schedule store, Aug 2026
-- result: count=1
--   {"rows_": 3094, "clock_ne_home": 140.0, "sched_ne_home": 140.0, "null_home": 0.0}
SELECT COUNT(*) rows_, SUM(a.dept_id<>a.clock_in_dept_id) clock_ne_home, SUM(a.dept_id<>a.scheduling_dept_id) sched_ne_home,
 SUM(a.dept_id IS NULL) null_home
FROM luckyus_opempefficiency.t_attendance a WHERE a.tenant='LKUS' AND a.attendance_date>='2026-08-01' AND a.attendance_date<'2026-09-01';

-- server: aws-luckyus-opempefficiency-rw
-- note: monthly cross-store rates over 12 months
-- result: count=12
--   {"ym": "2025-09", "shifts": 1927, "clock_ne_sched": 0.0, "sched_ne_home": 141.0}
--   {"ym": "2025-10", "shifts": 2361, "clock_ne_sched": 0.0, "sched_ne_home": 51.0}
--   {"ym": "2025-11", "shifts": 2134, "clock_ne_sched": 0.0, "sched_ne_home": 39.0}
--   {"ym": "2025-12", "shifts": 2690, "clock_ne_sched": 0.0, "sched_ne_home": 110.0}
--   {"ym": "2026-01", "shifts": 3046, "clock_ne_sched": 0.0, "sched_ne_home": 95.0}
--   {"ym": "2026-02", "shifts": 3152, "clock_ne_sched": 0.0, "sched_ne_home": 106.0}
--   {"ym": "2026-03", "shifts": 3863, "clock_ne_sched": 0.0, "sched_ne_home": 205.0}
--   {"ym": "2026-04", "shifts": 3673, "clock_ne_sched": 0.0, "sched_ne_home": 304.0}
--   ... （共 12 行，此处摘录前 8 行）
SELECT DATE_FORMAT(attendance_date,'%Y-%m') ym, COUNT(*) shifts,
 SUM(clock_in_dept_id<>scheduling_dept_id) clock_ne_sched, SUM(dept_id<>scheduling_dept_id) sched_ne_home
FROM luckyus_opempefficiency.t_attendance WHERE tenant='LKUS' AND attendance_date>='2025-09-01' AND attendance_date<'2026-09-01'
GROUP BY 1 ORDER BY 1;


-- =====================================================================
-- F-07 — 同日多异常的实际分布（澄清项 L-01）
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: exception-type combinations per shift, Aug 2026
-- result: count=5
--   {"except_type_list": "1", "c": 1070}
--   {"except_type_list": "2", "c": 266}
--   {"except_type_list": "4", "c": 59}
--   {"except_type_list": "3", "c": 48}
--   {"except_type_list": "1,3", "c": 6}
SELECT except_type_list, COUNT(*) c FROM luckyus_opempefficiency.t_attendance_shift
WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01' AND attendance_status=0
GROUP BY 1 ORDER BY c DESC;

-- server: aws-luckyus-opempefficiency-rw
-- note: exception count: record grain vs person-day grain
-- result: count=1
--   {"exception_shift_records": 1449, "exception_person_days": 1388}
SELECT COUNT(*) exception_shift_records,
 COUNT(DISTINCT CONCAT(emp_no,'|',attendance_date)) exception_person_days
FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01' AND attendance_status=0;

-- server: aws-luckyus-opempefficiency-rw
-- note: exception shifts per person-day
-- result: count=4
--   {"n_shifts_with_exc": 1, "person_days": 1334}
--   {"n_shifts_with_exc": 2, "person_days": 48}
--   {"n_shifts_with_exc": 3, "person_days": 5}
--   {"n_shifts_with_exc": 4, "person_days": 1}
SELECT n_shifts_with_exc, COUNT(*) person_days FROM (
 SELECT emp_no,attendance_date,COUNT(*) n_shifts_with_exc FROM luckyus_opempefficiency.t_attendance_shift
 WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01' AND attendance_status=0
 GROUP BY emp_no,attendance_date) t GROUP BY 1 ORDER BY 1;


-- =====================================================================
-- F-08 — 排班是否为审批后的最终排班（澄清项 L-04）
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: schedule rows edited on/after the shift date; version usage
-- result: count=1
--   {"modified_after_shift_day": 3568.0, "created_after_shift_day": 569.0, "version_gt1": 20784.0, "max_version": 19, "total": 34150}
SELECT SUM(DATE(modify_time)>scheduling_date) modified_after_shift_day,
 SUM(DATE(create_time)>scheduling_date) created_after_shift_day,
 SUM(version>1) version_gt1, MAX(version) max_version, COUNT(*) total
FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' AND status=1 AND scheduling_date>='2025-09-01' AND scheduling_date<'2026-09-01';

-- server: aws-luckyus-opempefficiency-rw
-- note: columns of t_working_time_apply
-- result: count=32
--   {"TABLE_NAME": "t_working_time_apply", "COLUMN_NAME": "id", "COLUMN_TYPE": "bigint unsigned", "COLUMN_COMMENT": "主键"}
--   {"TABLE_NAME": "t_working_time_apply", "COLUMN_NAME": "tenant", "COLUMN_TYPE": "varchar(4)", "COLUMN_COMMENT": "租户"}
--   {"TABLE_NAME": "t_working_time_apply", "COLUMN_NAME": "apply_no", "COLUMN_TYPE": "varchar(20)", "COLUMN_COMMENT": "申请编号"}
--   {"TABLE_NAME": "t_working_time_apply", "COLUMN_NAME": "apply_name", "COLUMN_TYPE": "varchar(256)", "COLUMN_COMMENT": "主题名称"}
--   {"TABLE_NAME": "t_working_time_apply", "COLUMN_NAME": "work_type", "COLUMN_TYPE": "tinyint(1)", "COLUMN_COMMENT": "工时类型"}
--   {"TABLE_NAME": "t_working_time_apply", "COLUMN_NAME": "locality_mid", "COLUMN_TYPE": "varchar(32)", "COLUMN_COMMENT": "二级行政区主数据Id"}
--   {"TABLE_NAME": "t_working_time_apply", "COLUMN_NAME": "date_period", "COLUMN_TYPE": "varchar(32)", "COLUMN_COMMENT": "日期范围"}
--   {"TABLE_NAME": "t_working_time_apply", "COLUMN_NAME": "time_period", "COLUMN_TYPE": "varchar(32)", "COLUMN_COMMENT": "时间范围"}
--   ... （共 32 行，此处摘录前 8 行）
SELECT TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,COLUMN_COMMENT FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='luckyus_opempefficiency' AND TABLE_NAME='t_working_time_apply' ORDER BY ORDINAL_POSITION;

-- server: aws-luckyus-opempefficiency-rw
-- note: makeup-punch / schedule-change request volumes by type and status
-- result: count=14
--   {"type": 1, "sub_type": 101, "status": 2, "c": 1632, "min_d": "2025-06-29", "max_d": "2026-09-08"}
--   {"type": 1, "sub_type": 101, "status": 3, "c": 475, "min_d": "2025-07-03", "max_d": "2026-09-08"}
--   {"type": 1, "sub_type": 101, "status": 4, "c": 146, "min_d": "2025-07-02", "max_d": "2026-09-03"}
--   {"type": 2, "sub_type": 202, "status": 2, "c": 57, "min_d": "2025-07-21", "max_d": "2026-07-29"}
--   {"type": 2, "sub_type": 201, "status": 2, "c": 30, "min_d": "2025-07-22", "max_d": "2026-08-06"}
--   {"type": 2, "sub_type": 203, "status": 2, "c": 28, "min_d": "2025-10-19", "max_d": "2026-08-06"}
--   {"type": 2, "sub_type": 201, "status": 4, "c": 26, "min_d": "2025-07-09", "max_d": "2026-08-22"}
--   {"type": 2, "sub_type": 202, "status": 4, "c": 19, "min_d": "2025-07-02", "max_d": "2026-09-04"}
--   ... （共 14 行，此处摘录前 8 行）
SELECT type,sub_type,status,COUNT(*) c,MIN(attendance_date) min_d,MAX(attendance_date) max_d
FROM luckyus_opempefficiency.t_attendance_change WHERE tenant='LKUS' GROUP BY 1,2,3 ORDER BY c DESC;

-- server: aws-luckyus-opempefficiency-rw
-- note: monthly approved makeup punches and shift changes
-- result: count=13
--   {"ym": "2025-09", "approved_makeup_punch": 80.0, "approved_shift_change": 1.0, "all_requests": 114}
--   {"ym": "2025-10", "approved_makeup_punch": 98.0, "approved_shift_change": 16.0, "all_requests": 140}
--   {"ym": "2025-11", "approved_makeup_punch": 64.0, "approved_shift_change": 10.0, "all_requests": 127}
--   {"ym": "2025-12", "approved_makeup_punch": 111.0, "approved_shift_change": 8.0, "all_requests": 165}
--   {"ym": "2026-01", "approved_makeup_punch": 92.0, "approved_shift_change": 6.0, "all_requests": 129}
--   {"ym": "2026-02", "approved_makeup_punch": 108.0, "approved_shift_change": 10.0, "all_requests": 172}
--   {"ym": "2026-03", "approved_makeup_punch": 115.0, "approved_shift_change": 7.0, "all_requests": 168}
--   {"ym": "2026-04", "approved_makeup_punch": 169.0, "approved_shift_change": 6.0, "all_requests": 233}
--   ... （共 13 行，此处摘录前 8 行）
SELECT DATE_FORMAT(attendance_date,'%Y-%m') ym, SUM(type=1 AND status=2) approved_makeup_punch, SUM(type=2 AND status=2) approved_shift_change, COUNT(*) all_requests
FROM luckyus_opempefficiency.t_attendance_change WHERE tenant='LKUS' AND attendance_date>='2025-09-01' GROUP BY 1 ORDER BY 1;


-- =====================================================================
-- F-09 — 请假 / PTO / 调休数据是否可得（澄清项 C-03）
-- =====================================================================

-- server: aws-luckyus-iehr-rw
-- note: leave application status/type distribution
-- result: count=2
--   {"status": 2, "application_type": 1, "c": 6, "min_d": "2025-10-10", "max_d": "2026-04-09", "emps": 4}
--   {"status": 2, "application_type": 0, "c": 1, "min_d": "2026-04-27", "max_d": "2026-04-27", "emps": 1}
SELECT status,application_type,COUNT(*) c,MIN(start_date) min_d,MAX(end_date) max_d,COUNT(DISTINCT emp_no) emps
FROM luckyus_iehr.t_ehr_employee_leave_application WHERE tenant='LKUS' GROUP BY 1,2 ORDER BY c DESC;

-- server: aws-luckyus-iehr-rw
-- note: leave types used vs dictionary
-- result: count=2
--   {"leave_type": "annual", "type_name": "年假", "c": 6, "approved": 0.0}
--   {"leave_type": "unpaid", "type_name": "事假", "c": 1, "approved": 0.0}
SELECT a.leave_type, t.name type_name, COUNT(*) c, SUM(a.status=1) approved
FROM luckyus_iehr.t_ehr_employee_leave_application a LEFT JOIN luckyus_iehr.t_ehr_employee_leave_type t ON t.code=a.leave_type AND t.tenant='LKUS'
WHERE a.tenant='LKUS' GROUP BY 1,2 ORDER BY c DESC;

-- server: aws-luckyus-iehr-rw
-- note: leave day-detail coverage
-- result: count=1
--   {"day_rows": 30, "emps": 5, "min_d": "2025-10-10", "max_d": "2026-04-27", "full_days": 28.0, "half_days": 2.0}
SELECT COUNT(*) day_rows, COUNT(DISTINCT emp_no) emps, MIN(leave_date) min_d, MAX(leave_date) max_d,
 SUM(leave_day=1.0) full_days, SUM(leave_day<1.0) half_days FROM luckyus_iehr.t_ehr_employee_leave_application_day_detail WHERE tenant='LKUS';

-- server: aws-luckyus-iehr-rw
-- note: LKUS leave type dictionary
-- result: count=9
--   {"code": "annual", "name": "年假"}
--   {"code": "compassionate", "name": "丧假"}
--   {"code": "electionDay", "name": "投票日"}
--   {"code": "fmla", "name": "FMLA"}
--   {"code": "juryDuty", "name": "Jury Duty"}
--   {"code": "maternity", "name": "产假"}
--   {"code": "nationalReserve", "name": "国民预备役"}
--   {"code": "sick", "name": "病假"}
--   ... （共 9 行，此处摘录前 8 行）
SELECT code,name FROM luckyus_iehr.t_ehr_employee_leave_type WHERE tenant='LKUS' ORDER BY code;

-- server: aws-luckyus-iehr-rw
-- note: leave applications by tenant and status
-- result: count=7
--   {"tenant": "IQA2", "status": 0, "c": 32}
--   {"tenant": "IQA2", "status": 1, "c": 7}
--   {"tenant": "IQA2", "status": 2, "c": 27}
--   {"tenant": "IQA2", "status": 3, "c": 1}
--   {"tenant": "IQA2", "status": 4, "c": 20}
--   {"tenant": "IQA2", "status": 5, "c": 1}
--   {"tenant": "LKUS", "status": 2, "c": 7}
SELECT tenant,status,COUNT(*) c FROM luckyus_iehr.t_ehr_employee_leave_application GROUP BY 1,2 ORDER BY 1,2;

-- server: aws-luckyus-opempefficiency-rw
-- note: attendance row 'type' (1考勤/3会议/4培训/5请假/6其他/9训练) usage
-- result: count=5
--   {"type": 1, "c": 37351, "min_d": "2025-06-29", "max_d": "2026-10-03"}
--   {"type": 9, "c": 3512, "min_d": "2025-06-29", "max_d": "2026-09-25"}
--   {"type": 4, "c": 837, "min_d": "2025-07-17", "max_d": "2026-09-02"}
--   {"type": 3, "c": 97, "min_d": "2026-02-02", "max_d": "2026-09-03"}
--   {"type": 5, "c": 1, "min_d": "2026-04-27", "max_d": "2026-04-27"}
SELECT type, COUNT(*) c, MIN(attendance_date) min_d, MAX(attendance_date) max_d
FROM luckyus_opempefficiency.t_attendance WHERE tenant='LKUS' GROUP BY 1 ORDER BY c DESC;


-- =====================================================================
-- F-10 — 强制闭店的原因分布（澄清项 C-04、L-06）
-- =====================================================================

-- server: aws-luckyus-opshop-rw
-- note: full forced-closure reason dictionary
-- result: count=15
--   {"id": 36, "tenant": "IQA2", "reason_no": "FC001", "reason": "IQA2Test_Goverment inspection", "reason_types": "1,2", "status": 1, "deleted": 0, "shop_models": "1,0", "for_day_start": 1, "for_day_end": 7}
--   {"id": 37, "tenant": "IQA2", "reason_no": "FC004", "reason": "IQA2Test_License issue", "reason_types": "2", "status": 1, "deleted": 0, "shop_models": "1", "for_day_start": 1, "for_day_end": 7}
--   {"id": 38, "tenant": "IQA2", "reason_no": "FC005", "reason": "IQA2Test_Weather issue", "reason_types": "1", "status": 1, "deleted": 0, "shop_models": "0", "for_day_start": null, "for_day_end": null}
--   {"id": 39, "tenant": "LKUS", "reason_no": "FC001", "reason": "One staff working", "reason_types": "1", "status": 1, "deleted": 0, "shop_models": "0", "for_day_start": 1, "for_day_end": 1}
--   {"id": 40, "tenant": "LKUS", "reason_no": "FC002", "reason": "Landlord’s issue", "reason_types": "1,2", "status": 1, "deleted": 0, "shop_models": "0", "for_day_start": 1, "for_day_end": 14}
--   {"id": 41, "tenant": "LKUS", "reason_no": "FC003", "reason": "Under renovation", "reason_types": "2", "status": 1, "deleted": 0, "shop_models": "0", "for_day_start": 1, "for_day_end": 14}
--   {"id": 42, "tenant": "LKUS", "reason_no": "FC004", "reason": "School holiday break", "reason_types": "2", "status": 1, "deleted": 0, "shop_models": "0", "for_day_start": 1, "for_day_end": 60}
--   {"id": 43, "tenant": "LKUS", "reason_no": "FC005", "reason": "1 staff working", "reason_types": "1", "status": 1, "deleted": 1, "shop_models": "0", "for_day_start": null, "for_day_end": null}
--   ... （共 15 行，此处摘录前 8 行）
SELECT id,tenant,reason_no,reason,reason_types,status,deleted,shop_models,for_day_start,for_day_end FROM luckyus_opshop.t_focus_closed_reason ORDER BY tenant,id;

-- server: aws-luckyus-opshop-rw
-- note: forced closure log profile: scene/source/open-ended/cross-day
-- result: count=8
--   {"tenant": "LKUS", "operation_scene": 1, "start_operation_source": 2, "c": 89, "min_t": "2025-07-06T10:10:00", "max_t": "2026-09-09T10:10:01", "open_ended": 0.0, "null_dur": 0.0, "cross_day": 0.0}
--   {"tenant": "LKUS", "operation_scene": 1, "start_operation_source": 1, "c": 81, "min_t": "2025-06-30T05:09:57", "max_t": "2026-09-07T10:56:29", "open_ended": 1.0, "null_dur": 1.0, "cross_day": 39.0}
--   {"tenant": "IQA2", "operation_scene": 1, "start_operation_source": 2, "c": 23, "min_t": "2025-03-24T06:30:16", "max_t": "2026-08-18T16:40:01", "open_ended": 1.0, "null_dur": 1.0, "cross_day": 1.0}
--   {"tenant": "IQA2", "operation_scene": 1, "start_operation_source": 1, "c": 7, "min_t": "2025-03-24T06:06:41", "max_t": "2026-08-05T06:41:01", "open_ended": 0.0, "null_dur": 0.0, "cross_day": 0.0}
--   {"tenant": "LKUS", "operation_scene": 1, "start_operation_source": 3, "c": 5, "min_t": "2026-05-17T04:00:01", "max_t": "2026-08-15T04:00:04", "open_ended": 0.0, "null_dur": 0.0, "cross_day": 3.0}
--   {"tenant": "IQA2", "operation_scene": 2, "start_operation_source": 1, "c": 4, "min_t": "2025-03-24T06:15:06", "max_t": "2026-08-05T06:42:35", "open_ended": 0.0, "null_dur": 0.0, "cross_day": 0.0}
--   {"tenant": "IQA2", "operation_scene": 1, "start_operation_source": 3, "c": 3, "min_t": "2025-04-16T10:00:01", "max_t": "2026-03-19T10:00:01", "open_ended": 0.0, "null_dur": 0.0, "cross_day": 0.0}
--   {"tenant": "IQA2", "operation_scene": 2, "start_operation_source": 2, "c": 1, "min_t": "2025-09-02T05:43:51", "max_t": "2025-09-02T05:43:51", "open_ended": 0.0, "null_dur": 0.0, "cross_day": 0.0}
SELECT tenant,operation_scene,start_operation_source,COUNT(*) c,MIN(start_time) min_t,MAX(start_time) max_t,
 SUM(end_time IS NULL) open_ended, SUM(closed_duration IS NULL) null_dur, SUM(DATE(end_time)<>DATE(start_time)) cross_day
FROM luckyus_opshop.t_shop_focus_operation_log GROUP BY 1,2,3 ORDER BY c DESC;

-- server: aws-luckyus-opshop-rw
-- note: t_nobody_focus_closed_log type distribution (1=warn,2=forced closure)
-- result: count=4
--   {"tenant": "LKUS", "type": 1, "c": 482, "depts": 23, "min_t": "2025-07-01T10:00:00", "max_t": "2026-09-09T10:00:01", "null_msg": 0.0}
--   {"tenant": "LKUS", "type": 2, "c": 88, "depts": 22, "min_t": "2025-07-06T10:10:01", "max_t": "2026-09-09T10:10:01", "null_msg": 0.0}
--   {"tenant": "IQA2", "type": 1, "c": 1, "depts": 1, "min_t": "2026-08-18T16:30:01", "max_t": "2026-08-18T16:30:01", "null_msg": 0.0}
--   {"tenant": "IQA2", "type": 2, "c": 1, "depts": 1, "min_t": "2026-08-18T16:40:01", "max_t": "2026-08-18T16:40:01", "null_msg": 0.0}
SELECT tenant,type,COUNT(*) c,COUNT(DISTINCT dept_id) depts,MIN(notify_time) min_t,MAX(notify_time) max_t,
 SUM(notify_msg IS NULL OR notify_msg='') null_msg FROM luckyus_opshop.t_nobody_focus_closed_log GROUP BY 1,2 ORDER BY c DESC;

-- server: aws-luckyus-opshop-rw
-- note: sample nobody-clocking alert rows
-- result: count=6
--   {"id": 1057, "dept_id": 1140, "type": 2, "msg": "New York City-New York City-100 Maiden Ln, 2026-09-09 no clocking record in (business hours 07:00-19:00), the store has been automatically forced to closed!", "notify_posts": "LKUS00000082,LKUS00000076,LKUS00000047,LKUS00000043,LKUS00000122,LKUS000000 ...
--   {"id": 1056, "dept_id": 1140, "type": 1, "msg": "New York City-New York City-100 Maiden Ln, 2026-09-09 no clocking record in (business hours 07:00-19:00), please verify to ensure the normal operation of the store!", "notify_posts": "LKUS00000082,LKUS00000076,LKUS00000047,LKUS00000043,LKUS00000094,LK ...
--   {"id": 1055, "dept_id": 20017, "type": 2, "msg": "New York City-New York City-180 Varick, 2026-09-08 no clocking record in (business hours 07:00-19:00), the store has been automatically forced to closed!", "notify_posts": "LKUS00000082,LKUS00000076,LKUS00000047,LKUS00000043,LKUS00000122,LKUS00000094 ...
--   {"id": 1054, "dept_id": 20017, "type": 1, "msg": "New York City-New York City-180 Varick, 2026-09-08 no clocking record in (business hours 07:00-19:00), please verify to ensure the normal operation of the store!", "notify_posts": "LKUS00000082,LKUS00000076,LKUS00000047,LKUS00000043,LKUS00000094,LKUS ...
--   {"id": 1053, "dept_id": 20009, "type": 1, "msg": "New York City-New York City-108th & Broadway, 2026-09-07 no clocking record in (business hours 07:00-20:00), please verify to ensure the normal operation of the store!", "notify_posts": "LKUS00000082,LKUS00000076,LKUS00000047,LKUS00000043,LKUS0000009 ...
--   {"id": 1052, "dept_id": 20031, "type": 1, "msg": "New York City-New York City-15th & 3rd, 2026-09-07 no clocking record in (business hours 07:00-18:00), please verify to ensure the normal operation of the store!", "notify_posts": "LKUS00000082,LKUS00000076,LKUS00000047,LKUS00000043,LKUS00000094,LKUS ...
SELECT id,dept_id,type,LEFT(notify_msg,180) msg,notify_posts,notify_time FROM luckyus_opshop.t_nobody_focus_closed_log
WHERE tenant='LKUS' ORDER BY id DESC LIMIT 6;

-- server: aws-luckyus-opshop-rw
-- note: closures per store-day
-- result: count=3
--   {"n_per_store_day": 1, "store_days": 149}
--   {"n_per_store_day": 2, "store_days": 8}
--   {"n_per_store_day": 3, "store_days": 1}
SELECT n_per_store_day,COUNT(*) store_days FROM (
 SELECT dept_id,DATE(start_time) d,COUNT(*) n_per_store_day FROM luckyus_opshop.t_shop_focus_operation_log
 WHERE tenant='LKUS' AND operation_scene=1 AND start_time>='2025-09-01' GROUP BY dept_id,DATE(start_time)) t
GROUP BY n_per_store_day ORDER BY n_per_store_day;

-- server: aws-luckyus-opshop-rw
-- note: closure count/duration by reason
-- result: count=10
--   {"reason_id": -1, "reason": "无人开早", "c": 84, "tot_min": 2795.0, "avg_min": 33.2738, "cross_day": 0.0, "open_ended": 0.0}
--   {"reason_id": 45, "reason": "In-store equipment malfunction.", "c": 26, "tot_min": 10981.0, "avg_min": 422.3462, "cross_day": 11.0, "open_ended": 0.0}
--   {"reason_id": 39, "reason": "One staff working", "c": 16, "tot_min": 2472.0, "avg_min": 154.5, "cross_day": 7.0, "open_ended": 0.0}
--   {"reason_id": 40, "reason": "Landlord’s issue", "c": 11, "tot_min": 3190.0, "avg_min": 290.0, "cross_day": 3.0, "open_ended": 0.0}
--   {"reason_id": 46, "reason": "Food safety issue", "c": 10, "tot_min": 1959.0, "avg_min": 195.9, "cross_day": 5.0, "open_ended": 0.0}
--   {"reason_id": 49, "reason": "Weather issue", "c": 8, "tot_min": 1797.0, "avg_min": 224.625, "cross_day": 8.0, "open_ended": 0.0}
--   {"reason_id": 50, "reason": "Water and power outage", "c": 4, "tot_min": 882.0, "avg_min": 220.5, "cross_day": 1.0, "open_ended": 0.0}
--   {"reason_id": 48, "reason": "Goverment inspection", "c": 4, "tot_min": 15212.0, "avg_min": 3803.0, "cross_day": 3.0, "open_ended": 0.0}
--   ... （共 10 行，此处摘录前 8 行）
SELECT l.reason_id,l.reason,COUNT(*) c,SUM(l.closed_duration) tot_min,AVG(l.closed_duration) avg_min,
 SUM(DATE(l.end_time)<>DATE(l.start_time)) cross_day, SUM(l.end_time IS NULL) open_ended
FROM luckyus_opshop.t_shop_focus_operation_log l WHERE l.tenant='LKUS' AND l.operation_scene=1 AND l.start_time>='2025-09-01'
GROUP BY 1,2 ORDER BY c DESC;

-- server: aws-luckyus-opshop-rw
-- note: search for an Emergency Closure field in opshop
-- result: count=0
SELECT TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,COLUMN_COMMENT FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='luckyus_opshop' AND (COLUMN_NAME REGEXP 'emerg|urgent|temp_close|急' OR COLUMN_COMMENT REGEXP '紧急|应急');

-- server: aws-luckyus-opshop-rw
-- note: match nobody-clocking forced closures to the closure log on store+date
-- result: count=1
--   {"nobody_forced": 88, "matched_to_closure": 88.0}
SELECT COUNT(*) nobody_forced, SUM(m.matched IS NOT NULL) matched_to_closure FROM (
 SELECT n.id, n.dept_id, DATE(n.notify_time) d,
   (SELECT 1 FROM luckyus_opshop.t_shop_focus_operation_log l WHERE l.tenant='LKUS' AND l.dept_id=n.dept_id
      AND DATE(l.start_time)=DATE(n.notify_time) AND l.reason_id=-1 LIMIT 1) matched
 FROM luckyus_opshop.t_nobody_focus_closed_log n WHERE n.tenant='LKUS' AND n.type=2) m;

-- server: aws-luckyus-opshop-rw
-- note: monthly comparison: nobody-clocking forced closures vs closure-log reason_id=-1
-- result: count=14
--   {"ym": "2025-07", "nobody_forced": 4, "closure_reason_minus1": 4}
--   {"ym": "2025-09", "nobody_forced": 1, "closure_reason_minus1": 1}
--   {"ym": "2025-10", "nobody_forced": 1, "closure_reason_minus1": 1}
--   {"ym": "2025-11", "nobody_forced": 1, "closure_reason_minus1": 1}
--   {"ym": "2025-12", "nobody_forced": 2, "closure_reason_minus1": 2}
--   {"ym": "2026-01", "nobody_forced": 3, "closure_reason_minus1": 3}
--   {"ym": "2026-02", "nobody_forced": 1, "closure_reason_minus1": 1}
--   {"ym": "2026-03", "nobody_forced": 3, "closure_reason_minus1": 3}
--   ... （共 14 行，此处摘录前 8 行）
SELECT ym, MAX(nobody2) nobody_forced, MAX(cl) closure_reason_minus1 FROM (
 SELECT DATE_FORMAT(notify_time,'%Y-%m') ym, COUNT(*) nobody2, NULL cl FROM luckyus_opshop.t_nobody_focus_closed_log WHERE tenant='LKUS' AND type=2 GROUP BY 1
 UNION ALL SELECT DATE_FORMAT(start_time,'%Y-%m'), NULL, COUNT(*) FROM luckyus_opshop.t_shop_focus_operation_log WHERE tenant='LKUS' AND reason_id=-1 GROUP BY 1) t
GROUP BY ym ORDER BY ym;

-- server: aws-luckyus-opshop-rw
-- note: multi-day closures: stored closed_duration vs wall-clock span
-- result: count=10
--   {"id": 1200, "dept_id": 20032, "reason": "Goverment inspection", "start_time": "2026-04-02T17:50:53", "end_time": "2026-04-20T11:00:17", "closed_duration": 14709, "wall_clock_min": 25509, "days_spanned": 18}
--   {"id": 1220, "dept_id": 1127, "reason": "Under renovation", "start_time": "2026-05-17T04:00:01", "end_time": "2026-05-31T04:00:01", "closed_duration": 10920, "wall_clock_min": 20160, "days_spanned": 14}
--   {"id": 1198, "dept_id": 20027, "reason": "In-store equipment malfunction.", "start_time": "2026-03-30T16:40:37", "end_time": "2026-04-05T10:59:01", "closed_duration": 4699, "wall_clock_min": 8298, "days_spanned": 6}
--   {"id": 1249, "dept_id": 20019, "reason": "Internet interruption", "start_time": "2026-07-03T11:08:06", "end_time": "2026-07-07T11:07:46", "closed_duration": 2878, "wall_clock_min": 5759, "days_spanned": 4}
--   {"id": 1175, "dept_id": 20032, "reason": "One staff working", "start_time": "2026-02-22T18:01:30", "end_time": "2026-02-24T12:02:23", "closed_duration": 480, "wall_clock_min": 2520, "days_spanned": 2}
--   {"id": 1174, "dept_id": 20011, "reason": "One staff working", "start_time": "2026-02-22T17:35:07", "end_time": "2026-02-24T11:58:08", "closed_duration": 444, "wall_clock_min": 2543, "days_spanned": 2}
--   {"id": 1163, "dept_id": 1127, "reason": "Weather issue", "start_time": "2026-01-25T18:01:35", "end_time": "2026-01-27T12:00:53", "closed_duration": 418, "wall_clock_min": 2519, "days_spanned": 2}
--   {"id": 1160, "dept_id": 20011, "reason": "In-store equipment malfunction.", "start_time": "2026-01-24T18:16:14", "end_time": "2026-01-29T12:02:06", "closed_duration": 405, "wall_clock_min": 6825, "days_spanned": 5}
--   ... （共 10 行，此处摘录前 8 行）
SELECT id,dept_id,reason,start_time,end_time,closed_duration,
 TIMESTAMPDIFF(MINUTE,start_time,end_time) wall_clock_min, DATEDIFF(end_time,start_time) days_spanned
FROM luckyus_opshop.t_shop_focus_operation_log WHERE tenant='LKUS' AND operation_scene=1 AND DATEDIFF(end_time,start_time)>=2
ORDER BY closed_duration DESC LIMIT 10;

-- server: aws-luckyus-opshop-rw
-- note: closure totals for the ratio quoted in the report
-- result: count=1
--   {"closures": 168, "total_min": 53318.0, "nobody_closures": 84.0, "nobody_min": 2795.0, "cross_day": 41.0}
SELECT COUNT(*) closures, SUM(closed_duration) total_min,
 SUM(reason_id=-1) nobody_closures, SUM(CASE WHEN reason_id=-1 THEN closed_duration END) nobody_min,
 SUM(DATE(end_time)<>DATE(start_time)) cross_day
FROM luckyus_opshop.t_shop_focus_operation_log WHERE tenant='LKUS' AND operation_scene=1 AND start_time>='2025-09-01';


-- =====================================================================
-- F-11 — 岗位与员工类型字典（澄清项 P-16、P-17）
-- =====================================================================

-- server: aws-luckyus-iehr-rw
-- note: LKUS position dictionary with active headcount
-- result: count=266
--   {"post_id": 495, "code": "LKUS00000095", "name": "Shift Supervisor Trainee", "status": 1, "emps_main": 125}
--   {"post_id": 496, "code": "LKUS00000096", "name": "Barista Trainee", "status": 1, "emps_main": 101}
--   {"post_id": 483, "code": "LKUS00000084", "name": "Barista", "status": 1, "emps_main": 79}
--   {"post_id": 484, "code": "LKUS00000085", "name": "Shift Supervisor", "status": 1, "emps_main": 68}
--   {"post_id": 400, "code": "LKUS00000001", "name": "技术岗", "status": 1, "emps_main": 64}
--   {"post_id": 498, "code": "LKUS00000098", "name": "Store Manager Trainee", "status": 1, "emps_main": 34}
--   {"post_id": 421, "code": "LKUS00000022", "name": "高级研发工程师", "status": 1, "emps_main": 31}
--   {"post_id": 481, "code": "LKUS00000082", "name": "Store Manager", "status": 1, "emps_main": 27}
--   ... （共 266 行，此处摘录前 8 行）
SELECT p.id post_id,p.code,p.name,p.status,COUNT(DISTINCT r.emp_no) emps_main
FROM luckyus_iehr.t_ehr_post p LEFT JOIN luckyus_iehr.t_ehr_employee_post_relation r ON r.post_id=p.id AND r.relation_type=0 AND r.tenant='LKUS'
LEFT JOIN luckyus_iehr.t_ehr_employee e ON e.emp_no=r.emp_no AND e.tenant='LKUS' AND e.status=1
WHERE p.tenant='LKUS' GROUP BY 1,2,3,4 ORDER BY emps_main DESC;

-- server: aws-luckyus-iehr-rw
-- note: employee status x property (0FT/1PT/2intern/3outsourced)
-- result: count=5
--   {"status": 0, "property": 0, "c": 336}
--   {"status": 0, "property": 1, "c": 52}
--   {"status": 1, "property": 0, "c": 582}
--   {"status": 1, "property": 1, "c": 35}
--   {"status": 1, "property": 4, "c": 4}
SELECT status,property,COUNT(*) c FROM luckyus_iehr.t_ehr_employee WHERE tenant='LKUS' GROUP BY 1,2 ORDER BY 1,2;

-- server: aws-luckyus-iehr-rw
-- note: active headcount by main post with FT/PT split
-- result: count=45
--   {"post_name": "技术岗", "post_code": "LKUS00000001", "active_emps": 60, "full_time": 60.0, "part_time": 0.0, "other_property": 0.0}
--   {"post_name": "Shift Supervisor", "post_code": "LKUS00000085", "active_emps": 48, "full_time": 48.0, "part_time": 0.0, "other_property": 0.0}
--   {"post_name": "Barista", "post_code": "LKUS00000084", "active_emps": 39, "full_time": 18.0, "part_time": 21.0, "other_property": 0.0}
--   {"post_name": "高级研发工程师", "post_code": "LKUS00000022", "active_emps": 29, "full_time": 29.0, "part_time": 0.0, "other_property": 0.0}
--   {"post_name": "Director", "post_code": "LKUS00000056", "active_emps": 23, "full_time": 23.0, "part_time": 0.0, "other_property": 0.0}
--   {"post_name": "Store Manager", "post_code": "LKUS00000082", "active_emps": 23, "full_time": 23.0, "part_time": 0.0, "other_property": 0.0}
--   {"post_name": "技术专家", "post_code": "LKUS00000087", "active_emps": 22, "full_time": 22.0, "part_time": 0.0, "other_property": 0.0}
--   {"post_name": "Barista Trainee", "post_code": "LKUS00000096", "active_emps": 22, "full_time": 9.0, "part_time": 13.0, "other_property": 0.0}
--   ... （共 45 行，此处摘录前 8 行）
SELECT p.name post_name,p.code post_code,
 COUNT(*) active_emps, SUM(e.property=0) full_time, SUM(e.property=1) part_time, SUM(e.property NOT IN (0,1)) other_property
FROM luckyus_iehr.t_ehr_employee e
JOIN luckyus_iehr.t_ehr_employee_post_relation r ON r.emp_no=e.emp_no AND r.tenant='LKUS' AND r.relation_type=0
JOIN luckyus_iehr.t_ehr_post p ON p.id=r.post_id AND p.tenant='LKUS'
WHERE e.tenant='LKUS' AND e.status=1 AND e.test_flag=0
GROUP BY 1,2 HAVING active_emps>0 ORDER BY active_emps DESC LIMIT 45;

-- server: aws-luckyus-iehr-rw
-- note: store-facing posts: headcount and FT/PT
-- result: count=10
--   {"post_name": "Shift Supervisor", "active_emps": 48, "ft": 48.0, "pt": 0.0, "prop4": 0.0}
--   {"post_name": "Barista", "active_emps": 39, "ft": 18.0, "pt": 21.0, "prop4": 0.0}
--   {"post_name": "Store Manager", "active_emps": 23, "ft": 23.0, "pt": 0.0, "prop4": 0.0}
--   {"post_name": "Barista Trainee", "active_emps": 22, "ft": 9.0, "pt": 13.0, "prop4": 0.0}
--   {"post_name": "Assistant Store Manager", "active_emps": 18, "ft": 18.0, "pt": 0.0, "prop4": 0.0}
--   {"post_name": "Operations Supervisor", "active_emps": 7, "ft": 7.0, "pt": 0.0, "prop4": 0.0}
--   {"post_name": "OPS Support", "active_emps": 5, "ft": 5.0, "pt": 0.0, "prop4": 0.0}
--   {"post_name": "Store Manager Trainee", "active_emps": 4, "ft": 4.0, "pt": 0.0, "prop4": 0.0}
--   ... （共 10 行，此处摘录前 8 行）
SELECT p.name post_name, COUNT(*) active_emps, SUM(e.property=0) ft, SUM(e.property=1) pt, SUM(e.property=4) prop4
FROM luckyus_iehr.t_ehr_employee e
JOIN luckyus_iehr.t_ehr_employee_post_relation r ON r.emp_no=e.emp_no AND r.tenant='LKUS' AND r.relation_type=0
JOIN luckyus_iehr.t_ehr_post p ON p.id=r.post_id AND p.tenant='LKUS'
WHERE e.tenant='LKUS' AND e.status=1 AND p.name REGEXP 'Store Manager|Assistant Store|Shift|Barista|OPS|Operations Supervisor'
GROUP BY 1 ORDER BY active_emps DESC;

-- server: aws-luckyus-iehr-rw
-- note: main vs secondary post relation counts
-- result: count=1
--   {"relation_type": 0, "c": 1009, "emps": 1009}
SELECT relation_type, COUNT(*) c, COUNT(DISTINCT emp_no) emps FROM luckyus_iehr.t_ehr_employee_post_relation WHERE tenant='LKUS' GROUP BY 1;

-- server: aws-luckyus-iehr-rw
-- note: the 4 employees carrying undocumented property=4
-- result: count=4
--   {"emp_h": "5c529f99", "property": 4, "status": 1, "join_date": "2026-07-20", "employment_type": null, "main_type": null, "test_flag": 0}
--   {"emp_h": "9357a4eb", "property": 4, "status": 1, "join_date": "2026-08-03", "employment_type": null, "main_type": null, "test_flag": 0}
--   {"emp_h": "51481e21", "property": 4, "status": 1, "join_date": "2026-08-03", "employment_type": null, "main_type": null, "test_flag": 0}
--   {"emp_h": "b5a9b6d2", "property": 4, "status": 1, "join_date": "2026-08-05", "employment_type": null, "main_type": null, "test_flag": 0}
SELECT LEFT(SHA2(emp_no,256),8) emp_h, property, status, join_date, employment_type, main_type, test_flag
FROM luckyus_iehr.t_ehr_employee WHERE tenant='LKUS' AND property=4;

-- server: aws-luckyus-opempefficiency-rw
-- note: distinct management-area codes present in attendance data
-- result: count=2
--   {"scheduling_dept_operation_area": "LKUS00000041", "clock_in_dept_operation_area": "LKUS00000041", "c": 31693}
--   {"scheduling_dept_operation_area": "LKUS00000052", "clock_in_dept_operation_area": "LKUS00000052", "c": 7396}
SELECT scheduling_dept_operation_area, clock_in_dept_operation_area, COUNT(*) c
FROM luckyus_opempefficiency.t_attendance WHERE tenant='LKUS' AND attendance_date>='2025-09-01' GROUP BY 1,2 ORDER BY c DESC LIMIT 20;

-- server: aws-luckyus-opempefficiency-rw
-- note: store -> management area mapping seen in attendance
-- result: count=32
--   {"scheduling_dept_id": 1127, "scheduling_dept_operation_area": "LKUS00000041", "c": 3690, "min_d": "2025-09-01", "max_d": "2026-09-12"}
--   {"scheduling_dept_id": 1128, "scheduling_dept_operation_area": "LKUS00000041", "c": 3609, "min_d": "2025-09-01", "max_d": "2026-09-19"}
--   {"scheduling_dept_id": 1131, "scheduling_dept_operation_area": "LKUS00000041", "c": 151, "min_d": "2025-09-02", "max_d": "2025-11-18"}
--   {"scheduling_dept_id": 1140, "scheduling_dept_operation_area": "LKUS00000041", "c": 1955, "min_d": "2025-09-07", "max_d": "2026-09-12"}
--   {"scheduling_dept_id": 1140, "scheduling_dept_operation_area": "LKUS00000052", "c": 1254, "min_d": "2025-12-24", "max_d": "2026-05-09"}
--   {"scheduling_dept_id": 1141, "scheduling_dept_operation_area": "LKUS00000041", "c": 3905, "min_d": "2025-09-01", "max_d": "2026-09-12"}
--   {"scheduling_dept_id": 20008, "scheduling_dept_operation_area": "LKUS00000041", "c": 2517, "min_d": "2025-11-28", "max_d": "2026-09-17"}
--   {"scheduling_dept_id": 20009, "scheduling_dept_operation_area": "LKUS00000041", "c": 1117, "min_d": "2026-03-03", "max_d": "2026-09-19"}
--   ... （共 32 行，此处摘录前 8 行）
SELECT scheduling_dept_id, scheduling_dept_operation_area, COUNT(*) c, MIN(attendance_date) min_d, MAX(attendance_date) max_d
FROM luckyus_opempefficiency.t_attendance WHERE tenant='LKUS' AND attendance_date>='2025-09-01' GROUP BY 1,2 ORDER BY 1;

-- server: aws-luckyus-opshop-rw
-- note: operation_area distribution in store master, all statuses
-- result: count=3
--   {"operation_area": "LKUS00000041", "status": 1, "c": 25, "shops": "US00000,US00001,US00002,US00003,US00004,US00005,US00006,US00007,US00008,US00009,US00010,US00011,US00012,US00013,US00015,US00018,US00019,US00020,US00021,US00022,US00024,US00025,US00027,US99998,US99999"}
--   {"operation_area": "LKUS00000041", "status": 2, "c": 3, "shops": "US00023,US00026,US00035"}
--   {"operation_area": "LKUS00000041", "status": 5, "c": 5, "shops": "US00014,US00016,US00017,US00028,US00029"}
SELECT operation_area, status, COUNT(*) c, GROUP_CONCAT(shop_no ORDER BY shop_no) shops
FROM luckyus_opshop.t_shop_info WHERE tenant='LKUS' GROUP BY 1,2 ORDER BY 1,2;

-- server: aws-luckyus-opempefficiency-rw
-- note: secondary-post population in attendance rows
-- result: count=1
--   {"has_secondary": 0.0, "null_post": 0.0, "total": 3094}
SELECT SUM(part_post_codes IS NOT NULL AND part_post_codes<>'') has_secondary, SUM(post_code IS NULL OR post_code='') null_post, COUNT(*) total
FROM luckyus_opempefficiency.t_attendance WHERE tenant='LKUS' AND attendance_date>='2026-08-01' AND attendance_date<'2026-09-01';

-- server: aws-luckyus-opempefficiency-rw
-- note: stores that ever carried the second management area
-- result: count=1
--   {"stores_with_052": 8, "min_d": "2025-12-24", "max_d": "2026-05-16", "rows_": 7396}
SELECT COUNT(DISTINCT scheduling_dept_id) stores_with_052, MIN(attendance_date) min_d, MAX(attendance_date) max_d, COUNT(*) rows_
FROM luckyus_opempefficiency.t_attendance WHERE tenant='LKUS' AND scheduling_dept_operation_area='LKUS00000052';


-- =====================================================================
-- F-12 — 同步方式与刷新频率可行性（澄清项 B-01，P0）
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: indexes on luckyus_opempefficiency core tables
-- result: count=33
--   {"TABLE_NAME": "t_attendance", "INDEX_NAME": "idx_attendance", "SEQ_IN_INDEX": 1, "COLUMN_NAME": "attendance_date", "NON_UNIQUE": 1, "CARDINALITY": 484}
--   {"TABLE_NAME": "t_attendance", "INDEX_NAME": "idx_attendance_date", "SEQ_IN_INDEX": 1, "COLUMN_NAME": "attendance_date", "NON_UNIQUE": 1, "CARDINALITY": 445}
--   {"TABLE_NAME": "t_attendance", "INDEX_NAME": "idx_empNo", "SEQ_IN_INDEX": 1, "COLUMN_NAME": "emp_no", "NON_UNIQUE": 1, "CARDINALITY": 481}
--   {"TABLE_NAME": "t_attendance", "INDEX_NAME": "idx_schedulingDeptId_date_empNo", "SEQ_IN_INDEX": 1, "COLUMN_NAME": "scheduling_dept_id", "NON_UNIQUE": 1, "CARDINALITY": 29}
--   {"TABLE_NAME": "t_attendance", "INDEX_NAME": "idx_schedulingDeptId_date_empNo", "SEQ_IN_INDEX": 2, "COLUMN_NAME": "attendance_date", "NON_UNIQUE": 1, "CARDINALITY": 4880}
--   {"TABLE_NAME": "t_attendance", "INDEX_NAME": "idx_schedulingDeptId_date_empNo", "SEQ_IN_INDEX": 3, "COLUMN_NAME": "emp_no", "NON_UNIQUE": 1, "CARDINALITY": 37126}
--   {"TABLE_NAME": "t_attendance", "INDEX_NAME": "PRIMARY", "SEQ_IN_INDEX": 1, "COLUMN_NAME": "id", "NON_UNIQUE": 0, "CARDINALITY": 42141}
--   {"TABLE_NAME": "t_attendance", "INDEX_NAME": "uniq_emp_att_dept_type", "SEQ_IN_INDEX": 1, "COLUMN_NAME": "emp_no", "NON_UNIQUE": 0, "CARDINALITY": 486}
--   ... （共 33 行，此处摘录前 8 行）
SELECT TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX,COLUMN_NAME,NON_UNIQUE,CARDINALITY
FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='luckyus_opempefficiency' AND TABLE_NAME IN ('t_attendance','t_attendance_shift','t_clock_in','t_emp_scheduling') ORDER BY TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX;

-- server: aws-luckyus-opshop-rw
-- note: indexes on luckyus_opshop core tables
-- result: count=10
--   {"TABLE_NAME": "t_nobody_focus_closed_log", "INDEX_NAME": "idx_dept_id", "SEQ_IN_INDEX": 1, "COLUMN_NAME": "dept_id", "NON_UNIQUE": 1, "CARDINALITY": 23}
--   {"TABLE_NAME": "t_nobody_focus_closed_log", "INDEX_NAME": "PRIMARY", "SEQ_IN_INDEX": 1, "COLUMN_NAME": "id", "NON_UNIQUE": 0, "CARDINALITY": 523}
--   {"TABLE_NAME": "t_shop_focus_operation_log", "INDEX_NAME": "idx_dept_id_operation_scene_start_time", "SEQ_IN_INDEX": 1, "COLUMN_NAME": "dept_id", "NON_UNIQUE": 1, "CARDINALITY": 29}
--   {"TABLE_NAME": "t_shop_focus_operation_log", "INDEX_NAME": "idx_dept_id_operation_scene_start_time", "SEQ_IN_INDEX": 2, "COLUMN_NAME": "operation_scene", "NON_UNIQUE": 1, "CARDINALITY": 30}
--   {"TABLE_NAME": "t_shop_focus_operation_log", "INDEX_NAME": "idx_dept_id_operation_scene_start_time", "SEQ_IN_INDEX": 3, "COLUMN_NAME": "start_time", "NON_UNIQUE": 1, "CARDINALITY": 204}
--   {"TABLE_NAME": "t_shop_focus_operation_log", "INDEX_NAME": "PRIMARY", "SEQ_IN_INDEX": 1, "COLUMN_NAME": "id", "NON_UNIQUE": 0, "CARDINALITY": 204}
--   {"TABLE_NAME": "t_shop_opening_time", "INDEX_NAME": "PRIMARY", "SEQ_IN_INDEX": 1, "COLUMN_NAME": "id", "NON_UNIQUE": 0, "CARDINALITY": 244240}
--   {"TABLE_NAME": "t_shop_opening_time", "INDEX_NAME": "uniq_tenant_no", "SEQ_IN_INDEX": 1, "COLUMN_NAME": "tenant", "NON_UNIQUE": 0, "CARDINALITY": 1}
--   ... （共 10 行，此处摘录前 8 行）
SELECT TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX,COLUMN_NAME,NON_UNIQUE,CARDINALITY
FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='luckyus_opshop' AND TABLE_NAME IN ('t_shop_opening_time','t_shop_focus_operation_log','t_nobody_focus_closed_log') ORDER BY TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX;

-- server: aws-luckyus-opempefficiency-rw
-- note: create_time/modify_time completeness for incremental extraction
-- result: count=4
--   {"t": "t_attendance", "null_ct": 0.0, "null_mt": 0.0, "max_ct": "2026-09-09T15:58:42", "max_mt": "2026-09-09T16:04:02", "n": 41798}
--   {"t": "t_attendance_shift", "null_ct": 0.0, "null_mt": 0.0, "max_ct": "2026-09-09T15:58:42", "max_mt": "2026-09-09T16:04:02", "n": 42234}
--   {"t": "t_clock_in", "null_ct": 0.0, "null_mt": null, "max_ct": "2026-09-09T16:04:02", "max_mt": null, "n": 126808}
--   {"t": "t_emp_scheduling", "null_ct": 0.0, "null_mt": 0.0, "max_ct": "2026-09-09T14:41:02", "max_mt": "2026-09-09T14:41:02", "n": 41492}
SELECT 't_attendance' t, SUM(create_time IS NULL) null_ct, SUM(modify_time IS NULL) null_mt, MAX(create_time) max_ct, MAX(modify_time) max_mt, COUNT(*) n FROM luckyus_opempefficiency.t_attendance WHERE tenant='LKUS'
UNION ALL SELECT 't_attendance_shift', SUM(create_time IS NULL), SUM(modify_time IS NULL), MAX(create_time), MAX(modify_time), COUNT(*) FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS'
UNION ALL SELECT 't_clock_in', SUM(create_time IS NULL), NULL, MAX(create_time), NULL, COUNT(*) FROM luckyus_opempefficiency.t_clock_in WHERE tenant='LKUS'
UNION ALL SELECT 't_emp_scheduling', SUM(create_time IS NULL), SUM(modify_time IS NULL), MAX(create_time), MAX(modify_time), COUNT(*) FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS';

-- server: aws-luckyus-opempefficiency-rw
-- note: 30-day insert/update volume for incremental sizing
-- result: count=5
--   {"t": "t_clock_in", "rows_30d": 9546, "per_day": 318.2}
--   {"t": "t_attendance", "rows_30d": 3287, "per_day": 109.6}
--   {"t": "t_attendance_shift", "rows_30d": 3327, "per_day": 110.9}
--   {"t": "t_emp_scheduling", "rows_30d": 3242, "per_day": 108.1}
--   {"t": "t_attendance_shift_MODIFIED", "rows_30d": 4069, "per_day": 135.6}
SELECT 't_clock_in' t, COUNT(*) rows_30d, ROUND(COUNT(*)/30,1) per_day FROM luckyus_opempefficiency.t_clock_in WHERE tenant='LKUS' AND create_time>=DATE_SUB(UTC_DATE(),INTERVAL 30 DAY)
UNION ALL SELECT 't_attendance', COUNT(*), ROUND(COUNT(*)/30,1) FROM luckyus_opempefficiency.t_attendance WHERE tenant='LKUS' AND create_time>=DATE_SUB(UTC_DATE(),INTERVAL 30 DAY)
UNION ALL SELECT 't_attendance_shift', COUNT(*), ROUND(COUNT(*)/30,1) FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND create_time>=DATE_SUB(UTC_DATE(),INTERVAL 30 DAY)
UNION ALL SELECT 't_emp_scheduling', COUNT(*), ROUND(COUNT(*)/30,1) FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' AND create_time>=DATE_SUB(UTC_DATE(),INTERVAL 30 DAY)
UNION ALL SELECT 't_attendance_shift_MODIFIED', COUNT(*), ROUND(COUNT(*)/30,1) FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND modify_time>=DATE_SUB(UTC_DATE(),INTERVAL 30 DAY);

-- server: aws-luckyus-opempefficiency-rw
-- note: how stale a business date can still be re-written
-- result: count=15
--   {"lag_days": 3, "c": 93}
--   {"lag_days": 2, "c": 146}
--   {"lag_days": 1, "c": 6125}
--   {"lag_days": 0, "c": 139}
--   {"lag_days": -1, "c": 9}
--   {"lag_days": -2, "c": 9}
--   {"lag_days": -3, "c": 13}
--   {"lag_days": -4, "c": 14}
--   ... （共 15 行，此处摘录前 8 行）
SELECT DATEDIFF(DATE(modify_time),attendance_date) lag_days, COUNT(*) c FROM luckyus_opempefficiency.t_attendance_shift
WHERE tenant='LKUS' AND modify_time>=DATE_SUB(UTC_DATE(),INTERVAL 60 DAY) GROUP BY 1 ORDER BY lag_days DESC LIMIT 15;

-- server: aws-luckyus-opempefficiency-rw
-- note: how late a business date can still change - bounds the incremental re-read window
-- result: count=1
--   {"max_lag_days": 18, "modified_more_than_7d_later": 230.0, "modified_more_than_2d_later": 722.0, "n": 42234}
SELECT MAX(DATEDIFF(DATE(modify_time),attendance_date)) max_lag_days,
 SUM(DATEDIFF(DATE(modify_time),attendance_date)>7) modified_more_than_7d_later,
 SUM(DATEDIFF(DATE(modify_time),attendance_date)>2) modified_more_than_2d_later, COUNT(*) n
FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS';

-- server: aws-luckyus-opempefficiency-rw
-- note: t_emp_scheduling status totals
-- result: count=3
--   {"status": 0, "c": 9}
--   {"status": 1, "c": 37831}
--   {"status": 2, "c": 3652}
SELECT status, COUNT(*) c FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' GROUP BY 1 ORDER BY 1;

-- server: aws-luckyus-opempefficiency-rw
-- note: total modifications in 60 days, to size the lag=1 share
-- result: count=1
--   {"mods_60d": 7271, "lag1": 6125.0, "future_rows": 767.0}
SELECT COUNT(*) mods_60d, SUM(DATEDIFF(DATE(modify_time),attendance_date)=1) lag1,
 SUM(DATEDIFF(DATE(modify_time),attendance_date)<0) future_rows
FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND modify_time>=DATE_SUB(UTC_DATE(),INTERVAL 60 DAY);


-- =====================================================================
-- F-13 — 历史数据可回溯范围（澄清项 S-02）
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: monthly row counts across the three core fact tables
-- result: count=17
--   {"ym": "2025-06", "attendance_rows": 81, "clock_rows": 127, "schedule_rows": 68, "depts": 4, "emps": 33}
--   {"ym": "2025-07", "attendance_rows": 1202, "clock_rows": 3101, "schedule_rows": 958, "depts": 3, "emps": 54}
--   {"ym": "2025-08", "attendance_rows": 1426, "clock_rows": 4004, "schedule_rows": 1191, "depts": 5, "emps": 81}
--   {"ym": "2025-09", "attendance_rows": 1927, "clock_rows": 5099, "schedule_rows": 1601, "depts": 6, "emps": 123}
--   {"ym": "2025-10", "attendance_rows": 2361, "clock_rows": 6773, "schedule_rows": 2090, "depts": 6, "emps": 133}
--   {"ym": "2025-11", "attendance_rows": 2134, "clock_rows": 6843, "schedule_rows": 2155, "depts": 8, "emps": 125}
--   {"ym": "2025-12", "attendance_rows": 2690, "clock_rows": 8161, "schedule_rows": 2701, "depts": 9, "emps": 154}
--   {"ym": "2026-01", "attendance_rows": 3046, "clock_rows": 9192, "schedule_rows": 3055, "depts": 10, "emps": 178}
--   ... （共 17 行，此处摘录前 8 行）
SELECT ym, MAX(att) attendance_rows, MAX(clk) clock_rows, MAX(sch) schedule_rows, MAX(depts) depts, MAX(emps) emps FROM (
  SELECT DATE_FORMAT(attendance_date,'%Y-%m') ym, COUNT(*) att, NULL clk, NULL sch, COUNT(DISTINCT scheduling_dept_id) depts, COUNT(DISTINCT emp_no) emps FROM luckyus_opempefficiency.t_attendance WHERE tenant='LKUS' GROUP BY 1
  UNION ALL SELECT DATE_FORMAT(attendance_date,'%Y-%m'), NULL, COUNT(*), NULL, NULL, NULL FROM luckyus_opempefficiency.t_clock_in WHERE tenant='LKUS' GROUP BY 1
  UNION ALL SELECT DATE_FORMAT(scheduling_date,'%Y-%m'), NULL, NULL, COUNT(*), NULL, NULL FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' GROUP BY 1
) t GROUP BY ym ORDER BY ym;

-- server: aws-luckyus-opshop-rw
-- note: monthly forced-closure counts
-- result: count=15
--   {"ym": "2025-06", "closures": 1, "depts": 1}
--   {"ym": "2025-07", "closures": 6, "depts": 2}
--   {"ym": "2025-09", "closures": 5, "depts": 3}
--   {"ym": "2025-10", "closures": 5, "depts": 2}
--   {"ym": "2025-11", "closures": 2, "depts": 2}
--   {"ym": "2025-12", "closures": 2, "depts": 2}
--   {"ym": "2026-01", "closures": 10, "depts": 7}
--   {"ym": "2026-02", "closures": 16, "depts": 10}
--   ... （共 15 行，此处摘录前 8 行）
SELECT DATE_FORMAT(start_time,'%Y-%m') ym, COUNT(*) closures, COUNT(DISTINCT dept_id) depts
FROM luckyus_opshop.t_shop_focus_operation_log WHERE tenant='LKUS' AND operation_scene=1 GROUP BY 1 ORDER BY 1;

-- server: aws-luckyus-opshop-rw
-- note: monthly business-hours row coverage
-- result: count=17
--   {"ym": "2025-05", "rows_": 23, "depts": 1, "null_dur": 0.0}
--   {"ym": "2025-06", "rows_": 37, "depts": 4, "null_dur": 0.0}
--   {"ym": "2025-07", "rows_": 124, "depts": 4, "null_dur": 0.0}
--   {"ym": "2025-08", "rows_": 136, "depts": 6, "null_dur": 0.0}
--   {"ym": "2025-09", "rows_": 202, "depts": 7, "null_dur": 0.0}
--   {"ym": "2025-10", "rows_": 217, "depts": 7, "null_dur": 0.0}
--   {"ym": "2025-11", "rows_": 238, "depts": 9, "null_dur": 0.0}
--   {"ym": "2025-12", "rows_": 345, "depts": 12, "null_dur": 0.0}
--   ... （共 17 行，此处摘录前 8 行）
SELECT LEFT(date,7) ym, COUNT(*) rows_, COUNT(DISTINCT dept_id) depts, SUM(business_duration IS NULL) null_dur
FROM luckyus_opshop.t_shop_opening_time WHERE tenant='LKUS' GROUP BY 1 ORDER BY 1;


-- =====================================================================
-- F-14 — 数据量级
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: tenant/date-range/volume of 4 core opempefficiency tables
-- [ERROR] Error: (1046, 'No database selected')
SELECT 't_attendance' tbl,tenant,COUNT(*) rows_,MIN(attendance_date) min_d,MAX(attendance_date) max_d,COUNT(DISTINCT emp_no) emps,COUNT(DISTINCT scheduling_dept_id) sched_depts FROM t_attendance GROUP BY tenant
UNION ALL SELECT 't_attendance_shift',tenant,COUNT(*),MIN(attendance_date),MAX(attendance_date),COUNT(DISTINCT emp_no),COUNT(DISTINCT scheduling_dept_id) FROM t_attendance_shift GROUP BY tenant
UNION ALL SELECT 't_clock_in',tenant,COUNT(*),MIN(attendance_date),MAX(attendance_date),COUNT(DISTINCT emp_no),COUNT(DISTINCT dept_id) FROM t_clock_in GROUP BY tenant
UNION ALL SELECT 't_emp_scheduling',tenant,COUNT(*),MIN(scheduling_date),MAX(scheduling_date),COUNT(DISTINCT emp_no),COUNT(DISTINCT scheduling_dept_id) FROM t_emp_scheduling GROUP BY tenant;

-- server: aws-luckyus-opempefficiency-rw
-- note: tenant/date-range/volume of 4 core tables
-- result: count=8
--   {"tbl": "t_attendance", "tenant": "IQA2", "rows_": 272, "min_d": "2025-03-22", "max_d": "2026-08-31", "emps": 16, "depts": 7}
--   {"tbl": "t_attendance", "tenant": "LKUS", "rows_": 41798, "min_d": "2025-06-29", "max_d": "2026-10-03", "emps": 463, "depts": 25}
--   {"tbl": "t_attendance_shift", "tenant": "IQA2", "rows_": 331, "min_d": "2025-03-22", "max_d": "2026-08-31", "emps": 16, "depts": 7}
--   {"tbl": "t_attendance_shift", "tenant": "LKUS", "rows_": 42234, "min_d": "2025-06-29", "max_d": "2026-10-03", "emps": 463, "depts": 25}
--   {"tbl": "t_clock_in", "tenant": "IQA2", "rows_": 321, "min_d": "2025-03-22", "max_d": "2026-08-30", "emps": 7, "depts": 5}
--   {"tbl": "t_clock_in", "tenant": "LKUS", "rows_": 126805, "min_d": "2025-06-29", "max_d": "2026-09-09", "emps": 424, "depts": 25}
--   {"tbl": "t_emp_scheduling", "tenant": "IQA2", "rows_": 349, "min_d": "2025-03-22", "max_d": "2026-08-31", "emps": 18, "depts": 8}
--   {"tbl": "t_emp_scheduling", "tenant": "LKUS", "rows_": 41492, "min_d": "2025-06-27", "max_d": "2026-10-03", "emps": 472, "depts": 23}
SELECT 't_attendance' tbl,tenant,COUNT(*) rows_,MIN(attendance_date) min_d,MAX(attendance_date) max_d,COUNT(DISTINCT emp_no) emps,COUNT(DISTINCT scheduling_dept_id) depts FROM luckyus_opempefficiency.t_attendance GROUP BY tenant
UNION ALL SELECT 't_attendance_shift',tenant,COUNT(*),MIN(attendance_date),MAX(attendance_date),COUNT(DISTINCT emp_no),COUNT(DISTINCT scheduling_dept_id) FROM luckyus_opempefficiency.t_attendance_shift GROUP BY tenant
UNION ALL SELECT 't_clock_in',tenant,COUNT(*),MIN(attendance_date),MAX(attendance_date),COUNT(DISTINCT emp_no),COUNT(DISTINCT dept_id) FROM luckyus_opempefficiency.t_clock_in GROUP BY tenant
UNION ALL SELECT 't_emp_scheduling',tenant,COUNT(*),MIN(scheduling_date),MAX(scheduling_date),COUNT(DISTINCT emp_no),COUNT(DISTINCT scheduling_dept_id) FROM luckyus_opempefficiency.t_emp_scheduling GROUP BY tenant;

-- server: aws-luckyus-opshop-rw
-- note: store master: timezone / status / operation area counts
-- result: count=6
--   {"tenant": "IQA2", "status": 1, "c": 508, "n_tz": 1, "tzs": "Pacific/Rarotonga", "n_op_area": 2, "test_stores": 500.0, "internal_stores": 501.0}
--   {"tenant": "LKUS", "status": 1, "c": 25, "n_tz": 1, "tzs": "America/New_York", "n_op_area": 1, "test_stores": 0.0, "internal_stores": 3.0}
--   {"tenant": "IQA2", "status": 2, "c": 12, "n_tz": 1, "tzs": "Pacific/Rarotonga", "n_op_area": 3, "test_stores": 0.0, "internal_stores": 0.0}
--   {"tenant": "LKUS", "status": 5, "c": 5, "n_tz": 1, "tzs": "America/New_York", "n_op_area": 1, "test_stores": 0.0, "internal_stores": 0.0}
--   {"tenant": "LKUS", "status": 2, "c": 3, "n_tz": 1, "tzs": "America/New_York", "n_op_area": 1, "test_stores": 0.0, "internal_stores": 0.0}
--   {"tenant": "IQA2", "status": 3, "c": 1, "n_tz": 1, "tzs": "Pacific/Rarotonga", "n_op_area": 1, "test_stores": 0.0, "internal_stores": 1.0}
SELECT tenant,status,COUNT(*) c,COUNT(DISTINCT time_zone) n_tz,GROUP_CONCAT(DISTINCT time_zone) tzs,
 COUNT(DISTINCT operation_area) n_op_area, SUM(test_flag=1) test_stores, SUM(internal=1) internal_stores
FROM luckyus_opshop.t_shop_info GROUP BY 1,2 ORDER BY c DESC LIMIT 20;

-- server: aws-luckyus-opshop-rw
-- note: LKUS active store list
-- result: count=25
--   {"dept_id": 1131, "shop_no": "US00000", "shop_name": "NJ Test Kitchen", "status": 1, "time_zone": "America/New_York", "operation_area": "LKUS00000041", "locality_name": null, "sublocality_name": null, "set_up": "2025-05-09", "off_d": null, "internal": 1, "test_flag": 0}
--   {"dept_id": 1127, "shop_no": "US00001", "shop_name": "8th & Broadway", "status": 1, "time_zone": "America/New_York", "operation_area": "LKUS00000041", "locality_name": null, "sublocality_name": null, "set_up": "2025-06-30", "off_d": null, "internal": 0, "test_flag": 0}
--   {"dept_id": 1128, "shop_no": "US00002", "shop_name": "28th & 6th", "status": 1, "time_zone": "America/New_York", "operation_area": "LKUS00000041", "locality_name": null, "sublocality_name": null, "set_up": "2025-06-30", "off_d": null, "internal": 0, "test_flag": 0}
--   {"dept_id": 1140, "shop_no": "US00003", "shop_name": "100 Maiden Ln", "status": 1, "time_zone": "America/New_York", "operation_area": "LKUS00000041", "locality_name": null, "sublocality_name": null, "set_up": "2025-09-09", "off_d": null, "internal": 0, "test_flag": 0}
--   {"dept_id": 20011, "shop_no": "US00004", "shop_name": "37th & Broadway", "status": 1, "time_zone": "America/New_York", "operation_area": "LKUS00000041", "locality_name": null, "sublocality_name": null, "set_up": "2025-11-20", "off_d": null, "internal": 0, "test_flag": 0}
--   {"dept_id": 1141, "shop_no": "US00005", "shop_name": "54th & 8th", "status": 1, "time_zone": "America/New_York", "operation_area": "LKUS00000041", "locality_name": null, "sublocality_name": null, "set_up": "2025-08-24", "off_d": null, "internal": 0, "test_flag": 0}
--   {"dept_id": 20010, "shop_no": "US00006", "shop_name": "102 Fulton", "status": 1, "time_zone": "America/New_York", "operation_area": "LKUS00000041", "locality_name": null, "sublocality_name": null, "set_up": "2025-08-28", "off_d": null, "internal": 0, "test_flag": 0}
--   {"dept_id": 20009, "shop_no": "US00007", "shop_name": "108th & Broadway", "status": 1, "time_zone": "America/New_York", "operation_area": "LKUS00000041", "locality_name": null, "sublocality_name": null, "set_up": "2026-04-30", "off_d": null, "internal": 0, "test_flag": 0}
--   ... （共 25 行，此处摘录前 8 行）
SELECT dept_id,shop_no,shop_name,status,time_zone,operation_area,locality_name,sublocality_name,
 DATE(set_up_time) set_up, DATE(off_time) off_d, internal, test_flag
FROM luckyus_opshop.t_shop_info WHERE tenant='LKUS' AND status=1 ORDER BY shop_no;

-- server: aws-luckyus-opshop-rw
-- note: opshop LKUS row counts
-- result: count=4
--   {"t": "t_shop_opening_time", "n": 6185}
--   {"t": "t_shop_focus_operation_log", "n": 175}
--   {"t": "t_nobody_focus_closed_log", "n": 570}
--   {"t": "t_shop_info(all status)", "n": 33}
SELECT 't_shop_opening_time' t, COUNT(*) n FROM luckyus_opshop.t_shop_opening_time WHERE tenant='LKUS'
UNION ALL SELECT 't_shop_focus_operation_log', COUNT(*) FROM luckyus_opshop.t_shop_focus_operation_log WHERE tenant='LKUS'
UNION ALL SELECT 't_nobody_focus_closed_log', COUNT(*) FROM luckyus_opshop.t_nobody_focus_closed_log WHERE tenant='LKUS'
UNION ALL SELECT 't_shop_info(all status)', COUNT(*) FROM luckyus_opshop.t_shop_info WHERE tenant='LKUS';

-- server: aws-luckyus-iehr-rw
-- note: active LKUS employees carrying a main post (test_flag=0)
-- result: count=1
--   {"active_with_post": 621}
SELECT COUNT(*) active_with_post FROM luckyus_iehr.t_ehr_employee e
JOIN luckyus_iehr.t_ehr_employee_post_relation r ON r.emp_no=e.emp_no AND r.tenant='LKUS' AND r.relation_type=0
JOIN luckyus_iehr.t_ehr_post p ON p.id=r.post_id AND p.tenant='LKUS'
WHERE e.tenant='LKUS' AND e.status=1 AND e.test_flag=0;


-- =====================================================================
-- F-15 — 数据质量
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: distinct employee counts across fact tables
-- result: count=1
--   {"clock_emps": 408, "att_emps": 443, "sch_emps": 450, "local_emp_rows": 477}
SELECT
 (SELECT COUNT(DISTINCT emp_no) FROM luckyus_opempefficiency.t_clock_in WHERE tenant='LKUS' AND attendance_date>='2025-09-01') clock_emps,
 (SELECT COUNT(DISTINCT emp_no) FROM luckyus_opempefficiency.t_attendance WHERE tenant='LKUS' AND attendance_date>='2025-09-01') att_emps,
 (SELECT COUNT(DISTINCT emp_no) FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' AND scheduling_date>='2025-09-01') sch_emps,
 (SELECT COUNT(*) FROM luckyus_opempefficiency.t_employee WHERE tenant='LKUS') local_emp_rows;

-- server: aws-luckyus-opempefficiency-rw
-- note: attendance rows with no matching row in the local employee mirror
-- result: count=1
--   {"att_rows": 3094, "orphan_emp": 0.0}
SELECT COUNT(*) att_rows, SUM(e.emp_no IS NULL) orphan_emp
FROM luckyus_opempefficiency.t_attendance a LEFT JOIN luckyus_opempefficiency.t_employee e ON e.emp_no=a.emp_no AND e.tenant='LKUS'
WHERE a.tenant='LKUS' AND a.attendance_date>='2026-08-01' AND a.attendance_date<'2026-09-01';

-- server: aws-luckyus-opempefficiency-rw
-- note: duplicate clock rows at identical timestamp
-- result: count=1
--   {"dup_groups": 22, "dup_rows": 47.0}
SELECT COUNT(*) dup_groups, SUM(c) dup_rows FROM (
 SELECT emp_no,clock_in_time,COUNT(*) c FROM luckyus_opempefficiency.t_clock_in WHERE tenant='LKUS' AND attendance_date>='2025-09-01'
 GROUP BY 1,2 HAVING c>1) t;

-- server: aws-luckyus-opempefficiency-rw
-- note: completeness of scheduled vs clocked periods
-- result: count=1
--   {"total": 38642, "no_sched_period": 757.0, "no_clock_period": 5048.0, "neither": 24.0, "null_sched_hours": 0.0}
SELECT COUNT(*) total,
 SUM(scheduling_period IS NULL OR scheduling_period='') no_sched_period,
 SUM(clock_in_period IS NULL OR clock_in_period='') no_clock_period,
 SUM((scheduling_period IS NULL OR scheduling_period='') AND (clock_in_period IS NULL OR clock_in_period='')) neither,
 SUM(scheduling_hours IS NULL) null_sched_hours
FROM luckyus_opempefficiency.t_attendance_shift WHERE tenant='LKUS' AND attendance_date>='2025-09-01' AND attendance_date<='2026-09-08';

-- server: aws-luckyus-opempefficiency-rw
-- note: schedule duration outliers
-- result: count=1
--   {"nonpositive_minutes": 0.0, "ge_24h": 0.0, "max_min": 720, "min_min": 60, "n": 35754}
SELECT SUM(effect_minutes<=0) nonpositive_minutes, SUM(effect_minutes>=1440) ge_24h, MAX(effect_minutes) max_min, MIN(effect_minutes) min_min, COUNT(*) n
FROM luckyus_opempefficiency.t_emp_scheduling WHERE tenant='LKUS' AND status=1 AND scheduling_date>='2025-09-01';

-- server: aws-luckyus-opempefficiency-rw
-- note: attendance store ids missing from the local store mirror
-- result: count=0
SELECT scheduling_dept_id, COUNT(*) c, MIN(attendance_date) min_d, MAX(attendance_date) max_d
FROM luckyus_opempefficiency.t_attendance WHERE tenant='LKUS' AND scheduling_dept_id NOT IN (SELECT dept_id FROM luckyus_opempefficiency.t_shop_info WHERE tenant='LKUS')
GROUP BY 1 ORDER BY c DESC LIMIT 10;

-- server: aws-luckyus-opempefficiency-rw
-- note: opempefficiency local store mirror row counts
-- result: count=6
--   {"tenant": "IQA2", "status": 1, "c": 8}
--   {"tenant": "IQA2", "status": 2, "c": 12}
--   {"tenant": "IQA2", "status": 3, "c": 1}
--   {"tenant": "LKUS", "status": 1, "c": 25}
--   {"tenant": "LKUS", "status": 2, "c": 3}
--   {"tenant": "LKUS", "status": 5, "c": 5}
SELECT tenant,status,COUNT(*) c FROM luckyus_opempefficiency.t_shop_info GROUP BY 1,2 ORDER BY 1,2;


-- =====================================================================
-- F-16 — PII 字段盘点（澄清项 B-04，P0）
-- =====================================================================

-- server: aws-luckyus-opempefficiency-rw
-- note: PII-bearing columns on luckyus_opempefficiency in-scope tables
-- result: count=28
--   {"TABLE_SCHEMA": "luckyus_opempefficiency", "TABLE_NAME": "t_attendance", "COLUMN_NAME": "creator_name", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "创建人名称"}
--   {"TABLE_SCHEMA": "luckyus_opempefficiency", "TABLE_NAME": "t_attendance", "COLUMN_NAME": "modifier_name", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "修改人名称"}
--   {"TABLE_SCHEMA": "luckyus_opempefficiency", "TABLE_NAME": "t_attendance_change", "COLUMN_NAME": "emp_name", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "员工姓名"}
--   {"TABLE_SCHEMA": "luckyus_opempefficiency", "TABLE_NAME": "t_attendance_change", "COLUMN_NAME": "creator_name", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "创建人名称"}
--   {"TABLE_SCHEMA": "luckyus_opempefficiency", "TABLE_NAME": "t_attendance_change", "COLUMN_NAME": "modifier_name", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "修改人名称"}
--   {"TABLE_SCHEMA": "luckyus_opempefficiency", "TABLE_NAME": "t_attendance_change", "COLUMN_NAME": "approver_name", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "审核人姓名"}
--   {"TABLE_SCHEMA": "luckyus_opempefficiency", "TABLE_NAME": "t_attendance_change", "COLUMN_NAME": "target_emp_name", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "目标员工姓名"}
--   {"TABLE_SCHEMA": "luckyus_opempefficiency", "TABLE_NAME": "t_attendance_shift", "COLUMN_NAME": "creator_name", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "创建人名称"}
--   ... （共 28 行，此处摘录前 8 行）
SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,COLUMN_COMMENT
FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='luckyus_opempefficiency' AND TABLE_NAME IN ('t_attendance','t_attendance_shift','t_clock_in','t_emp_scheduling','t_employee','t_emp_snapshot','t_working_time_apply','t_attendance_change') AND COLUMN_NAME REGEXP 'name|phone|tel|email|mail|address|passport|bank|id_card|idcard|credential|birth|salary|wage|pay|photo|feature|postal|epf|socso|tax|nationality|religion|race|marital|provident|foreign|unit_number|expiry|expire|issue|pr_date|emergency' 
ORDER BY TABLE_NAME,ORDINAL_POSITION;

-- server: aws-luckyus-opshop-rw
-- note: PII-bearing columns on luckyus_opshop in-scope tables
-- result: count=18
--   {"TABLE_SCHEMA": "luckyus_opshop", "TABLE_NAME": "t_nobody_focus_closed_log", "COLUMN_NAME": "notify_emp_names", "COLUMN_TYPE": "text", "COLUMN_COMMENT": "通知人名称"}
--   {"TABLE_SCHEMA": "luckyus_opshop", "TABLE_NAME": "t_shop_focus_operation_log", "COLUMN_NAME": "start_operation_name", "COLUMN_TYPE": "varchar(64)", "COLUMN_COMMENT": "关闭操作人"}
--   {"TABLE_SCHEMA": "luckyus_opshop", "TABLE_NAME": "t_shop_focus_operation_log", "COLUMN_NAME": "end_operation_name", "COLUMN_TYPE": "varchar(64)", "COLUMN_COMMENT": "恢复操作人"}
--   {"TABLE_SCHEMA": "luckyus_opshop", "TABLE_NAME": "t_shop_info", "COLUMN_NAME": "shop_name", "COLUMN_TYPE": "varchar(128)", "COLUMN_COMMENT": "门店名称"}
--   {"TABLE_SCHEMA": "luckyus_opshop", "TABLE_NAME": "t_shop_info", "COLUMN_NAME": "dept_name", "COLUMN_TYPE": "varchar(128)", "COLUMN_COMMENT": "部门名称"}
--   {"TABLE_SCHEMA": "luckyus_opshop", "TABLE_NAME": "t_shop_info", "COLUMN_NAME": "manager_name", "COLUMN_TYPE": "varchar(128)", "COLUMN_COMMENT": "负责人姓名"}
--   {"TABLE_SCHEMA": "luckyus_opshop", "TABLE_NAME": "t_shop_info", "COLUMN_NAME": "manager_phone", "COLUMN_TYPE": "varchar(64)", "COLUMN_COMMENT": "负责人电话"}
--   {"TABLE_SCHEMA": "luckyus_opshop", "TABLE_NAME": "t_shop_info", "COLUMN_NAME": "shop_email", "COLUMN_TYPE": "varchar(64)", "COLUMN_COMMENT": "门店邮箱"}
--   ... （共 18 行，此处摘录前 8 行）
SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,COLUMN_COMMENT
FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='luckyus_opshop' AND TABLE_NAME IN ('t_shop_info','t_shop_focus_operation_log','t_nobody_focus_closed_log','t_shop_opening_time') AND COLUMN_NAME REGEXP 'name|phone|tel|email|mail|address|passport|bank|id_card|idcard|credential|birth|salary|wage|pay|photo|feature|postal|epf|socso|tax|nationality|religion|race|marital|provident|foreign|unit_number|expiry|expire|issue|pr_date|emergency' 
ORDER BY TABLE_NAME,ORDINAL_POSITION;

-- server: aws-luckyus-iehr-rw
-- note: PII-bearing columns on luckyus_iehr in-scope tables
-- result: count=40
--   {"TABLE_SCHEMA": "luckyus_iehr", "TABLE_NAME": "t_ehr_employee", "COLUMN_NAME": "name", "COLUMN_TYPE": "varchar(400)", "COLUMN_COMMENT": "员工名称"}
--   {"TABLE_SCHEMA": "luckyus_iehr", "TABLE_NAME": "t_ehr_employee", "COLUMN_NAME": "nick_name", "COLUMN_TYPE": "varchar(400)", "COLUMN_COMMENT": "员工昵称"}
--   {"TABLE_SCHEMA": "luckyus_iehr", "TABLE_NAME": "t_ehr_employee", "COLUMN_NAME": "telephone", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "电话"}
--   {"TABLE_SCHEMA": "luckyus_iehr", "TABLE_NAME": "t_ehr_employee", "COLUMN_NAME": "address", "COLUMN_TYPE": "varchar(1024)", "COLUMN_COMMENT": "地址"}
--   {"TABLE_SCHEMA": "luckyus_iehr", "TABLE_NAME": "t_ehr_employee", "COLUMN_NAME": "email", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "邮箱"}
--   {"TABLE_SCHEMA": "luckyus_iehr", "TABLE_NAME": "t_ehr_employee", "COLUMN_NAME": "bank_code", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "银行code"}
--   {"TABLE_SCHEMA": "luckyus_iehr", "TABLE_NAME": "t_ehr_employee", "COLUMN_NAME": "open_bank_code", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "开户行code"}
--   {"TABLE_SCHEMA": "luckyus_iehr", "TABLE_NAME": "t_ehr_employee", "COLUMN_NAME": "bank_account", "COLUMN_TYPE": "varchar(100)", "COLUMN_COMMENT": "银行账号"}
--   ... （共 40 行，此处摘录前 8 行）
SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,COLUMN_COMMENT
FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='luckyus_iehr' AND TABLE_NAME IN ('t_ehr_employee','t_ehr_employee_post_relation','t_ehr_post','t_ehr_employee_leave_application') AND COLUMN_NAME REGEXP 'name|phone|tel|email|mail|address|passport|bank|id_card|idcard|credential|birth|salary|wage|pay|photo|feature|postal|epf|socso|tax|nationality|religion|race|marital|provident|foreign|unit_number|expiry|expire|issue|pr_date|emergency' 
ORDER BY TABLE_NAME,ORDINAL_POSITION;
