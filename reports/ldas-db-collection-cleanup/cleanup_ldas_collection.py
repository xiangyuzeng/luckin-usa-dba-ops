#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDAS luckyus_db_collection 分级清理脚本（可正式执行，逐表处理）
================================================================
服务器: aws-luckyus-ldas01-rw   MySQL 8.0.45   file_per_table=1

安全设计:
  * 默认 dry-run，只统计不删除；加 --execute 才真正删数据。
  * 持续写入表用"分批 DELETE + 节流"，避免大事务/binlog 暴涨/主从延迟。
  * 批量写入表(每日一次回填)可用 swap，但本脚本统一走分批 DELETE，最稳。
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
    {"table": "t_dba_collect_ec2_metrics",            "time_col": "collect_timestamp", "days": 90, "tier": "A-metrics"},
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
    fh = logging.FileHandler(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "cleanup_run_%s.log" % datetime.now().strftime("%Y%m%d_%H%M%S")))
    fh.setFormatter(fmt)
    log.addHandler(fh)


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
    return "%.2f GB" % (b / 1024.0 / 1024.0 / 1024.0)


def table_size(cur, db, table):
    cur.execute(
        "SELECT IFNULL(data_length+index_length,0), IFNULL(table_rows,0) "
        "FROM information_schema.TABLES WHERE table_schema=%s AND table_name=%s",
        (db, table))
    row = cur.fetchone()
    return (row[0], row[1]) if row else (0, 0)


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


def main():
    p = argparse.ArgumentParser(description="LDAS luckyus_db_collection 分级清理")
    p.add_argument("--execute", action="store_true", help="真正执行删除(默认仅 dry-run 预览)")
    p.add_argument("--optimize", action="store_true", help="删除后逐表 OPTIMIZE 回收空间")
    p.add_argument("--only", action="append", default=None, help="只处理指定表(可多次)")
    p.add_argument("--batch", type=int, default=20000, help="每批删除行数(默认 20000)")
    p.add_argument("--sleep", type=float, default=0.5, help="批间隔秒(默认 0.5，节流防主从延迟)")
    p.add_argument("--max-seconds", type=int, default=0, help="单表删除时间上限秒(0=不限)")
    args = p.parse_args()

    setup_logging()
    db = os.environ.get("LDAS_DB", "luckyus_db_collection")
    mode = "执行" if args.execute else "DRY-RUN(仅预览)"
    log.info("=" * 70)
    log.info("LDAS 清理开始  库=%s  模式=%s  batch=%d  sleep=%.2fs",
             db, mode, args.batch, args.sleep)
    log.info("=" * 70)

    targets = RETENTION
    if args.only:
        targets = [t for t in RETENTION if t["table"] in args.only]
        if not targets:
            sys.exit("--only 未匹配到任何表: %s" % args.only)

    conn = connect(autocommit=True)
    cur = conn.cursor()

    # 预检: 确认无明显长事务
    cur.execute("SELECT COUNT(*) FROM information_schema.INNODB_TRX "
                "WHERE TIMESTAMPDIFF(SECOND, trx_started, NOW()) > 60")
    long_trx = cur.fetchone()[0]
    if long_trx:
        log.warning("预检: 存在 %d 个 >60s 长事务，建议低峰再删。", long_trx)

    grand_deleted = 0
    for spec in targets:
        table, time_col, days, tier = spec["table"], spec["time_col"], spec["days"], spec["tier"]
        size_b, est_rows = table_size(cur, db, table)
        log.info("-" * 70)
        log.info("[%s] %s  当前 %s (估算 %s 行)", tier, table, fmt_gb(size_b), f"{est_rows:,}")

        # processlist: 仅 OPTIMIZE
        if days is None:
            log.info("    策略: 仅重建(外部采集已只留数小时, 纯空间膨胀)")
            if args.execute and args.optimize:
                optimize_table(cur, db, table)
            elif args.execute:
                log.info("    (未加 --optimize, 跳过重建)")
            else:
                log.info("    DRY-RUN: 将执行 OPTIMIZE 回收 ~%s", fmt_gb(size_b))
            continue

        # 时间删除类
        expired = count_expired(cur, db, table, time_col, days)
        log.info("    策略: 保留 %d 天 (按 %s)，过期待删 %s 行", days, time_col, f"{expired:,}")
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
            optimize_table(cur, db, table)

    cur.close()
    conn.close()
    log.info("=" * 70)
    log.info("全部完成。本次累计删除 %s 行。模式=%s", f"{grand_deleted:,}", mode)
    if not args.execute:
        log.info("以上为预览。确认无误后加 --execute (可选 --optimize) 正式执行。")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
