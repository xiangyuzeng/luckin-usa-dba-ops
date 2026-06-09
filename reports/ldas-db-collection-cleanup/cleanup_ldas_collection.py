#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDAS luckyus_db_collection 分级清理脚本（可正式执行，逐表处理）
================================================================
服务器: aws-luckyus-ldas01-rw   MySQL 8.0.45   file_per_table=1

安全设计:
  * 默认 dry-run，只统计不删除；加 --execute 才真正删数据。
  * 两种清理模式，保留窗口/逐表配置完全一致，仅删除手段不同:
      - 默认 DELETE 模式: 分批 DELETE + 节流，避免大事务/binlog 暴涨/主从延迟，
        对持续写入表最稳；删除后可选 --optimize 回收空间。
      - --swap 模式: 建新表→只导近 N 天→原子 RENAME→DROP 旧表。删除占比高的表
        (如 ec2_metrics ~46% 过期)比逐批 DELETE 快得多，且天然回收空间(无需 OPTIMIZE)。
        RENAME 后会从旧表回补切换窗口内新到的保留行(INSERT IGNORE 按唯一键去重)，防丢。
        仅作用于带 swap_ok 标记的表(或 --only 显式指定的表)，其余表自动回退 DELETE。
  * processlist 只 OPTIMIZE(真实仅几万活行,纯膨胀)，不删数据。
  * 凭据只从环境变量读取，绝不硬编码。
  * 每批之间 sleep 节流；每表删除后可选 OPTIMIZE 回收空间。

环境变量:
  LDAS_HOST   (默认 aws-luckyus-ldas01-rw 的内网地址，需填)
  LDAS_PORT   (默认 3306)
  LDAS_USER   清理账号(需 DELETE/ALTER 权限)
  LDAS_PASSWORD
  LDAS_DB     (默认 luckyus_db_collection)

用法:
  # 预览(dry-run)所有表将删除多少行
  python3 cleanup_ldas_collection.py

  # 只预览某张表
  python3 cleanup_ldas_collection.py --only t_dba_collect_ec2_metrics

  # 正式执行全部清理(分批删除)，不做 OPTIMIZE
  python3 cleanup_ldas_collection.py --execute

  # 正式执行 + 删除后逐表 OPTIMIZE 回收空间
  python3 cleanup_ldas_collection.py --execute --optimize

  # 用 swap 模式重建高过期占比表(ec2_metrics 默认 swap_ok)，其余表仍走分批 DELETE
  python3 cleanup_ldas_collection.py --swap --execute

  # 只对 ec2_metrics 用 swap 重建
  python3 cleanup_ldas_collection.py --only t_dba_collect_ec2_metrics --swap --execute

  # 只重建 processlist(零数据损失，回收 ~49GB)
  python3 cleanup_ldas_collection.py --only t_dba_collect_processlist_info --execute --optimize

依赖: pip install pymysql
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime

pymysql = None  # 惰性加载: 仅在真正连库时才 import，便于 --help 在无依赖环境下也可用

# ---------------------------------------------------------------------------
# 分级保留策略 (逐表定义)
#   time_col : 用于判断过期的时间列(已逐表核实)
#   days     : 保留天数; None 表示不按时间删(仅 OPTIMIZE)
#   tier     : 仅用于日志归类
# ---------------------------------------------------------------------------
RETENTION = [
    # ---- 特殊: processlist 仅重建，不删数据 ----
    {"table": "t_dba_collect_processlist_info", "time_col": None, "days": None, "tier": "REBUILD-ONLY"},

    # ---- Tier A: 指标表(5min粒度, 有 _daily 汇总兜底) 保留 90 天 ----
    # ec2_metrics 过期占比高(~46%)，swap_ok=True: 加 --swap 时默认走重建更快。
    {"table": "t_dba_collect_ec2_metrics",            "time_col": "collect_timestamp", "days": 90, "tier": "A-metrics", "swap_ok": True},
    {"table": "t_dba_collect_rds_metrics",            "time_col": "collect_timestamp", "days": 90, "tier": "A-metrics"},
    {"table": "t_dba_collect_redis_cluster_metrics",  "time_col": "collect_timestamp", "days": 90, "tier": "A-metrics"},
    {"table": "t_dba_collect_index_used",             "time_col": "data_date",         "days": 90, "tier": "A-metrics"},
    {"table": "t_dba_collect_index_unused",           "time_col": "data_date",         "days": 90, "tier": "A-metrics"},

    # ---- Tier B: schema 每日全量快照(列定义极少变,冗余高) 保留 30 天 ----
    {"table": "t_dba_collect_table_column_info",      "time_col": "data_date", "days": 30, "tier": "B-snapshot"},
    {"table": "t_dba_collect_table_index_info",       "time_col": "data_date", "days": 30, "tier": "B-snapshot"},
    {"table": "t_dba_collect_table_info",             "time_col": "data_date", "days": 30, "tier": "B-snapshot"},
    {"table": "t_dba_collect_mysql_table_info",       "time_col": "data_date", "days": 30, "tier": "B-snapshot"},
    {"table": "t_dba_collect_created_tmp_table",      "time_col": "data_date", "days": 30, "tier": "B-snapshot"},
    {"table": "t_dba_collect_no_index_used_query",    "time_col": "data_date", "days": 30, "tier": "B-snapshot"},

    # ---- Tier C: 诊断日志 保留 60 天 ----
    {"table": "t_dba_collect_big_trx_info",           "time_col": "create_time", "days": 60, "tier": "C-diag"},
    {"table": "t_dba_collect_lock_waits_info",        "time_col": "create_time", "days": 60, "tier": "C-diag"},
    {"table": "t_dba_collect_slow_query",             "time_col": "data_date",   "days": 60, "tier": "C-diag"},
]

# ---------------------------------------------------------------------------
log = logging.getLogger("ldas_cleanup")


def setup_logging():
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", "%Y-%m-%d %H:%M:%S")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)
    # 日志默认写到脚本目录下的 logs/ 子目录(不再散落在脚本同级目录);
    # 可用环境变量 LDAS_LOG_DIR 覆盖。目录不存在则自动创建。
    log_dir = os.environ.get(
        "LDAS_LOG_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"))
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(
        log_dir, "cleanup_run_%s.log" % datetime.now().strftime("%Y%m%d_%H%M%S"))
    fh = logging.FileHandler(log_path)
    fh.setFormatter(fmt)
    log.addHandler(fh)
    log.info("日志文件: %s", log_path)


def connect(autocommit=True):
    global pymysql
    if pymysql is None:
        try:
            import pymysql as _pymysql
            pymysql = _pymysql
        except ImportError:
            sys.exit("缺少依赖: 请先 `pip install pymysql`")
    host = os.environ.get("LDAS_HOST")
    user = os.environ.get("LDAS_USER")
    pwd = os.environ.get("LDAS_PASSWORD")
    db = os.environ.get("LDAS_DB", "luckyus_db_collection")
    port = int(os.environ.get("LDAS_PORT", "3306"))
    if not (host and user and pwd):
        sys.exit("请先设置环境变量 LDAS_HOST / LDAS_USER / LDAS_PASSWORD")
    return pymysql.connect(host=host, port=port, user=user, password=pwd,
                           database=db, autocommit=autocommit, charset="utf8mb4",
                           connect_timeout=10, read_timeout=600, write_timeout=600)


def fmt_gb(b):
    # MySQL 驱动可能把 data_length+index_length 返回为 decimal.Decimal，
    # Decimal / float 在 Python3 会抛 TypeError，这里统一转 float。
    return "%.2f GB" % (float(b) / 1024.0 / 1024.0 / 1024.0)


def table_size(cur, db, table):
    """返回 (总字节, 估算行数, data_free 字节)。data_free 即可回收的碎片空间。"""
    cur.execute(
        "SELECT IFNULL(data_length+index_length,0), IFNULL(table_rows,0), IFNULL(data_free,0) "
        "FROM information_schema.TABLES WHERE table_schema=%s AND table_name=%s",
        (db, table))
    row = cur.fetchone()
    # 驱动可能返回 Decimal，统一转 int 便于后续算术/格式化(避免 Decimal/float 混算报错)。
    return (int(row[0]), int(row[1]), int(row[2])) if row else (0, 0, 0)


def count_expired(cur, db, table, time_col, days):
    cur.execute(
        "SELECT COUNT(*) FROM `%s`.`%s` WHERE `%s` < DATE_SUB(CURDATE(), INTERVAL %d DAY)"
        % (db, table, time_col, days))
    return cur.fetchone()[0]


def batched_delete(cur, db, table, time_col, days, batch, sleep_s, max_seconds):
    """逐批删除过期行，返回删除总数。"""
    total = 0
    start = time.time()
    sql = ("DELETE FROM `%s`.`%s` WHERE `%s` < DATE_SUB(CURDATE(), INTERVAL %d DAY) "
           "ORDER BY `%s` LIMIT %d" % (db, table, time_col, days, time_col, batch))
    while True:
        n = cur.execute(sql)
        total += n
        if n:
            log.info("    ...已删 %d (本批 %d)", total, n)
        if n < batch:
            break
        if max_seconds and (time.time() - start) > max_seconds:
            log.warning("    达到单表时间上限 %ds，暂停(剩余下次再删)。已删 %d", max_seconds, total)
            break
        time.sleep(sleep_s)
    return total


def optimize_table(cur, db, table):
    log.info("    OPTIMIZE TABLE `%s`.`%s` ...", db, table)
    t0 = time.time()
    cur.execute("OPTIMIZE TABLE `%s`.`%s`" % (db, table))
    cur.fetchall()  # 消费结果集
    log.info("    OPTIMIZE 完成，用时 %.1fs", time.time() - t0)
    # OPTIMIZE 后 InnoDB 统计可能滞后，强制 ANALYZE 刷新存储/行数估算与优化器统计，
    # 使 information_schema.TABLES 的 data_length/table_rows 立即反映回收后的真实值。
    log.info("    ANALYZE TABLE `%s`.`%s` ...", db, table)
    t1 = time.time()
    cur.execute("ANALYZE TABLE `%s`.`%s`" % (db, table))
    cur.fetchall()  # 消费结果集
    log.info("    ANALYZE 完成，用时 %.1fs", time.time() - t1)


def maybe_optimize(cur, db, table, free_b, min_free_bytes):
    """仅当可回收碎片 data_free >= 阈值时才 OPTIMIZE。
    碎片过小则重建不划算(纯耗 IO/binlog 却几乎回收不到空间)，跳过。
    """
    if free_b < min_free_bytes:
        log.info("    跳过 OPTIMIZE: data_free %s < 阈值 %s，碎片过小不值得重建。",
                 fmt_gb(free_b), fmt_gb(min_free_bytes))
        return False
    log.info("    data_free %s ≥ 阈值 %s，执行 OPTIMIZE。", fmt_gb(free_b), fmt_gb(min_free_bytes))
    optimize_table(cur, db, table)
    return True


def has_unique_key(cur, db, table):
    """表是否有主键/唯一键(决定 swap 回补能否安全去重)。"""
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.STATISTICS "
        "WHERE table_schema=%s AND table_name=%s AND non_unique=0",
        (db, table))
    return cur.fetchone()[0] > 0


def swap_rebuild(cur, db, table, time_col, days, execute):
    """swap 方式重建表: 只保留近 days 天。返回 (kept_rows, dropped_est)。
    步骤: 建新表 LIKE → 导入保留窗口 → 原子 RENAME → 回补切换窗口新行 → DROP 旧表。
    适合过期占比高的表; 天然回收空间，无需 OPTIMIZE。
    """
    new = table + "_new"
    old = table + "_old"
    cutoff = "DATE_SUB(CURDATE(), INTERVAL %d DAY)" % days

    # 预览: 将保留多少 / 丢弃多少
    cur.execute("SELECT COUNT(*) FROM `%s`.`%s` WHERE `%s` >= %s"
                % (db, table, time_col, cutoff))
    keep = cur.fetchone()[0]
    _, est_rows, _ = table_size(cur, db, table)
    drop_est = max(est_rows - keep, 0)

    if not execute:
        log.info("    DRY-RUN swap: 新表保留 %s 行(近 %d 天)，丢弃约 %s 行；RENAME 后自动回收空间",
                 f"{keep:,}", days, f"{drop_est:,}")
        return keep, drop_est

    # 中间表残留检查: _new 是本脚本自建的临时表，可安全清掉重来;
    # _old 若残留(上次中断)则不自动删，RENAME 会报错暴露，交人工确认。
    cur.execute("SELECT COUNT(*) FROM information_schema.TABLES "
                "WHERE table_schema=%s AND table_name=%s", (db, old))
    if cur.fetchone()[0]:
        sys.exit("    中止: 残留旧表 `%s`.`%s` 存在(疑似上次 swap 中断)，请人工确认后删除再重试。"
                 % (db, old))
    cur.execute("DROP TABLE IF EXISTS `%s`.`%s`" % (db, new))

    # 1. 建新表(同结构/索引)
    cur.execute("CREATE TABLE `%s`.`%s` LIKE `%s`.`%s`" % (db, new, db, table))
    log.info("    swap: 已建新表 %s (LIKE %s)", new, table)

    # 2. 导入保留窗口(单条 INSERT...SELECT，是一个较大事务，低峰执行)
    t0 = time.time()
    n = cur.execute("INSERT INTO `%s`.`%s` SELECT * FROM `%s`.`%s` WHERE `%s` >= %s"
                    % (db, new, db, table, time_col, cutoff))
    log.info("    swap: 已导入 %s 行(近 %d 天)，用时 %.1fs", f"{n:,}", days, time.time() - t0)

    # 3. 原子 RENAME(瞬时切换，对读写影响极小)
    cur.execute("RENAME TABLE `%s`.`%s` TO `%s`.`%s`, `%s`.`%s` TO `%s`.`%s`"
                % (db, table, db, old, db, new, db, table))
    log.info("    swap: RENAME 完成 (%s→%s, %s→%s)", table, old, new, table)

    # 4. 回补: 切换窗口内(步骤2~3之间)新到的保留行，按唯一键去重，防丢
    if has_unique_key(cur, db, table):
        c = cur.execute("INSERT IGNORE INTO `%s`.`%s` SELECT * FROM `%s`.`%s` WHERE `%s` >= %s"
                        % (db, table, db, old, time_col, cutoff))
        log.info("    swap: 回补切换窗口新行 %s 行(INSERT IGNORE 去重)", f"{c:,}")
    else:
        log.warning("    swap: 表无主键/唯一键，跳过回补(切换瞬间可能丢极少数行)")

    # 5. DROP 旧表(空间立即归还 OS)
    cur.execute("DROP TABLE `%s`.`%s`" % (db, old))
    log.info("    swap: 已 DROP 旧表 %s，空间已回收", old)
    return keep, drop_est


def main():
    p = argparse.ArgumentParser(description="LDAS luckyus_db_collection 分级清理")
    p.add_argument("--execute", action="store_true", help="真正执行删除(默认仅 dry-run 预览)")
    p.add_argument("--optimize", action="store_true", help="删除后逐表 OPTIMIZE 回收空间")
    p.add_argument("--swap", action="store_true",
                   help="对高过期占比表用 swap 重建(建新表+RENAME+DROP)替代分批 DELETE; "
                        "无 --only 时仅作用于 swap_ok 标记表，其余仍走 DELETE")
    p.add_argument("--only", action="append", default=None, help="只处理指定表(可多次)")
    p.add_argument("--batch", type=int, default=20000, help="每批删除行数(默认 20000)")
    p.add_argument("--sleep", type=float, default=0.5, help="批间隔秒(默认 0.5，节流防主从延迟)")
    p.add_argument("--max-seconds", type=int, default=0, help="单表删除时间上限秒(0=不限)")
    p.add_argument("--min-free-gb", type=float, default=1.0,
                   help="OPTIMIZE 的 data_free 下限(GB,默认 1.0); 表碎片小于此值则跳过重建")
    p.add_argument("--min-table-gb", type=float, default=2.0,
                   help="整表总大小下限(GB,默认 2.0); 小于此值的表整张跳过(不删/不重建)")
    args = p.parse_args()
    min_free_bytes = int(args.min_free_gb * 1024 ** 3)
    min_table_bytes = int(args.min_table_gb * 1024 ** 3)

    setup_logging()
    db = os.environ.get("LDAS_DB", "luckyus_db_collection")
    mode = "执行" if args.execute else "DRY-RUN(仅预览)"
    clean_method = "swap重建(swap_ok表)+DELETE(其余)" if args.swap else "分批 DELETE"
    log.info("=" * 70)
    log.info("LDAS 清理开始  库=%s  模式=%s  清理手段=%s  batch=%d  sleep=%.2fs",
             db, mode, clean_method, args.batch, args.sleep)
    log.info("=" * 70)

    targets = RETENTION
    if args.only:
        targets = [t for t in RETENTION if t["table"] in args.only]
        if not targets:
            sys.exit("--only 未匹配到任何表: %s" % args.only)

    conn = connect(autocommit=True)
    cur = conn.cursor()

    # 预检: 列出当前 >60s 长事务，并区分"活跃长查询"与"空闲事务(idle-in-trx)"。
    #   trx_state=RUNNING 只表示事务活动，不代表有 SQL 在跑;
    #   若连接 COMMAND=Sleep 且 trx_query 为空 → 是开着事务但当前不执行 SQL 的空闲连接。
    cur.execute(
        "SELECT t.trx_mysql_thread_id, "
        "       TIMESTAMPDIFF(SECOND, t.trx_started, NOW()) AS trx_age, "
        "       p.COMMAND, p.TIME AS cmd_time, IFNULL(t.trx_rows_modified,0), "
        "       p.USER, p.HOST, "
        "       LEFT(REPLACE(REPLACE(IFNULL(NULLIF(t.trx_query,''), p.INFO), '\\n',' '), '\\t',' '), 100) AS q "
        "FROM information_schema.INNODB_TRX t "
        "LEFT JOIN information_schema.PROCESSLIST p ON p.ID = t.trx_mysql_thread_id "
        "WHERE TIMESTAMPDIFF(SECOND, t.trx_started, NOW()) > 60 "
        "ORDER BY trx_age DESC")
    long_rows = cur.fetchall()
    if long_rows:
        # 三类: 活跃查询 / 空闲但有未提交写入(rows_w>0) / 纯只读空闲(rows_w=0,疑似连接池保底)。
        #   前两类有实际风险 → WARNING; 纯只读空闲多为连接池保活 → 仅 INFO 提示。
        active, idle_write, idle_read = [], [], []
        for r in long_rows:
            cmd, rows_w, q = (r[2] or ""), int(r[4] or 0), (r[7] or "")
            if q or cmd not in ("Sleep", ""):
                active.append(r)
            elif rows_w > 0:
                idle_write.append(r)
            else:
                idle_read.append(r)
        concerning = active + idle_write
        emit = log.warning if concerning else log.info
        emit("预检: %d 个 >60s 长事务 —— 活跃查询 %d, 空闲未提交写 %d, 纯只读空闲 %d(疑似连接池保底)。",
             len(long_rows), len(active), len(idle_write), len(idle_read))
        emit("    %-10s %-8s %-7s %-8s %-7s %-24s %s",
             "thread", "trx_age", "cmd", "cmd_t", "rows_w", "user@host", "query(截断100)")
        for tid, trx_age, cmd, cmd_t, rows_w, usr, host, q in long_rows:
            who = "%s@%s" % (usr or "?", (host or "?").split(":")[0])
            if q or (cmd or "") not in ("Sleep", ""):
                kind = "活跃"
            elif int(rows_w or 0) > 0:
                kind = "空闲写"
            else:
                kind = "只读空闲"
            emit("    %-10s %-8s %-7s %-8s %-7s %-24s [%s]%s",
                 tid, int(trx_age), cmd or "?", int(cmd_t or 0), int(rows_w), who, kind, q or "")
        if active:
            log.warning("    注: %d 个为活跃长查询，会抢资源/致主从延迟，建议低峰再删。", len(active))
        if idle_write:
            log.warning("    注: %d 个空闲事务持有未提交写入，阻塞 purge 且可能持锁，"
                        "建议先让应用方提交或 KILL 对应 thread 再删/重建。", len(idle_write))
        if idle_read and not concerning:
            log.info("    注: 纯只读空闲事务通常无害(连接池保活)，不阻塞 DELETE；"
                     "但仍 pin read view 致删后空间回收滞后，若要 swap/OPTIMIZE 且其持表 MDL 需先回收。")

    grand_deleted = 0
    for spec in targets:
        table, time_col, days, tier = spec["table"], spec["time_col"], spec["days"], spec["tier"]
        size_b, est_rows, free_b = table_size(cur, db, table)
        log.info("-" * 70)
        log.info("[%s] %s  当前 %s (估算 %s 行, 可回收碎片 %s)",
                 tier, table, fmt_gb(size_b), f"{est_rows:,}", fmt_gb(free_b))

        # 整表过小: 不值得处理(删/重建收益有限)，整张跳过。
        # 注: --only 显式点名的表不受此限，便于强制处理小表。
        if size_b < min_table_bytes and not args.only:
            log.info("    跳过: 整表 %s < 阈值 %s，太小不处理。",
                     fmt_gb(size_b), fmt_gb(min_table_bytes))
            continue

        # processlist: 仅 OPTIMIZE
        if days is None:
            log.info("    策略: 仅重建(外部采集已只留数小时, 纯空间膨胀)")
            if args.execute and args.optimize:
                maybe_optimize(cur, db, table, free_b, min_free_bytes)
            elif args.execute:
                log.info("    (未加 --optimize, 跳过重建)")
            elif free_b < min_free_bytes:
                log.info("    DRY-RUN: data_free %s < 阈值 %s，将跳过 OPTIMIZE",
                         fmt_gb(free_b), fmt_gb(min_free_bytes))
            else:
                log.info("    DRY-RUN: 将执行 OPTIMIZE 回收 ~%s", fmt_gb(free_b))
            continue

        # 时间删除类: 选择 swap 还是分批 DELETE。
        #   --swap 且 (该表 swap_ok 或 --only 显式指定) → 走 swap 重建;
        #   否则一律走分批 DELETE(保留窗口/时间列完全一致)。
        use_swap = args.swap and (spec.get("swap_ok") or bool(args.only))

        if use_swap:
            log.info("    策略: swap 重建，保留 %d 天 (按 %s)", days, time_col)
            keep, drop_est = swap_rebuild(cur, db, table, time_col, days, args.execute)
            if args.execute:
                grand_deleted += drop_est
            continue

        expired = count_expired(cur, db, table, time_col, days)
        log.info("    策略: 分批 DELETE，保留 %d 天 (按 %s)，过期待删 %s 行",
                 days, time_col, f"{expired:,}")
        if expired == 0:
            log.info("    无过期数据，跳过。")
            continue

        if not args.execute:
            log.info("    DRY-RUN: 将分批删除 %s 行；如需回收空间记得加 --optimize", f"{expired:,}")
            continue

        t0 = time.time()
        deleted = batched_delete(cur, db, table, time_col, days,
                                 args.batch, args.sleep, args.max_seconds)
        grand_deleted += deleted
        log.info("    删除完成: %s 行，用时 %.1fs", f"{deleted:,}", time.time() - t0)
        if args.optimize:
            # 删除后碎片已增长，重新读取 data_free 再判断是否值得 OPTIMIZE。
            _, _, free_after = table_size(cur, db, table)
            maybe_optimize(cur, db, table, free_after, min_free_bytes)

    cur.close()
    conn.close()
    note = "(swap 表为估算丢弃行)" if args.swap else ""
    log.info("=" * 70)
    log.info("全部完成。本次累计删除/丢弃 %s 行%s。模式=%s", f"{grand_deleted:,}", note, mode)
    if not args.execute:
        hint = "--execute" + (" (swap 表无需 --optimize)" if args.swap else " (可选 --optimize)")
        log.info("以上为预览。确认无误后加 %s 正式执行。", hint)
    log.info("=" * 70)


if __name__ == "__main__":
    main()
