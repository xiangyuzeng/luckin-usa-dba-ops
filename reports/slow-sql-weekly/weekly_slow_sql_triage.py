#!/usr/bin/env python3
"""
每周慢 SQL 分诊 —— 把本周榜单和「已分析台账」做差集，只把真正需要人看的推到面前。

    NEW        台账里没有 → 本周要分析
    REGRESSED  台账里有，但日均 DB 时间/平均耗时较基线劣化超过阈值 → 要复查
    RECURRED   台账标 fixed，却又出现在榜单上 → 修复没生效
    DUE        台账标 deferred/analyzed 且 recheck_after 到期 → 到期复查
    STALE      台账标 pending 且挂了太久没出结论 → 催办
    KNOWN      台账里有且稳定 → 静默（--show-known 才显示）

用法：
    python3 weekly_slow_sql_triage.py                      # L0，近 7 天
    python3 weekly_slow_sql_triage.py --level L0,L1        # 多档
    python3 weekly_slow_sql_triage.py --emit-md out.md     # 输出周报可直接贴的 markdown
    python3 weekly_slow_sql_triage.py --append-new         # 把 NEW 以 pending 追加进台账

口径提醒：数据来自 t_dba_collect_slow_query，该表只收录 avg_sec >= 1s 的指纹，
不代表慢查询总量（总量看 Prometheus mysql_global_status_slow_queries）。
"""

import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTRY = os.path.join(HERE, "analyzed-registry.csv")
DEFAULT_TIERMAP = "/app/luckin-slow-sql-tier-map.csv"
DEFAULT_ENV = "/app/alert-mailserver/scripts/.env"
DEFAULT_HOST_ID = "aws-luckyus-ldas01-rw"

VALID_STATUS = ("pending", "analyzed", "fixed", "accepted", "deferred")
REGISTRY_COLS = [
    "digest_id", "instance", "schema_name", "main_table", "level", "status",
    "first_analyzed", "last_reviewed", "report_id", "owner", "action_ids",
    "base_dbtime_7d_sec", "base_exec_7d", "base_avg_sec", "base_rows_examined",
    "recheck_after", "verdict",
]


# ---------------------------------------------------------------- helpers

def read_csv_skip_comments(path, what):
    """台账和分级表都以 # 开头的注释行打头，csv 模块要先滤掉。"""
    if not os.path.exists(path):
        sys.exit(f"[FATAL] 找不到{what}：{path}\n"
                 f"        用 --{'registry' if 'registry' in path else 'tier-map'} 指定正确路径，脚本不猜。")
    with open(path, encoding="utf-8") as fh:
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def load_tier_map(path):
    rows = read_csv_skip_comments(path, "分级映射表")
    tiers = {}
    for r in rows:
        inst = (r.get("instance") or "").strip()
        if inst:
            tiers[inst] = {
                "level": (r.get("level") or "").strip(),
                "group": (r.get("group") or "").strip(),
                "owner": (r.get("owner") or "").strip(),
            }
    if not tiers:
        sys.exit(f"[FATAL] 分级映射表 {path} 解析出 0 台实例，格式可能变了。")
    return tiers


def load_registry(path):
    rows = read_csv_skip_comments(path, "分析台账")
    reg, bad, malformed = {}, [], []
    for r in rows:
        # 字段里出现没加引号的逗号会让 DictReader 多切出一列（键为 None），
        # 后面所有列跟着错位。宁可报错也不要静默错位。
        if None in r or any(v is None for v in r.values()):
            malformed.append(r.get("digest_id", "?")[:8])
            continue
        st = (r.get("status") or "").strip()
        if st not in VALID_STATUS:
            bad.append((r.get("digest_id", "?")[:8], st))
        key = ((r.get("instance") or "").strip(),
               (r.get("schema_name") or "").strip(),
               (r.get("digest_id") or "").strip())
        reg[key] = r
    if malformed:
        sys.exit("[FATAL] 台账有 %d 行列数不符（多半是 verdict/备注里有没加引号的逗号）：%s\n"
                 "        修法：用 csv 模块重写该文件，含逗号的字段会自动加引号。"
                 % (len(malformed), ", ".join(malformed)))
    if bad:
        sys.exit("[FATAL] 台账里有非法 status（只能是 %s）：%s"
                 % ("/".join(VALID_STATUS), ", ".join(f"{d}={s!r}" for d, s in bad)))
    return reg


def load_db_credentials(env_path):
    """凭据来自 alert-mailserver/scripts/.env —— 注意值是带引号的，必须 strip。"""
    user = os.environ.get("SLOWSQL_MYSQL_USER")
    pwd = os.environ.get("SLOWSQL_MYSQL_PASSWORD")
    if user and pwd:
        return user, pwd
    if not os.path.exists(env_path):
        sys.exit(f"[FATAL] 找不到凭据文件 {env_path}，也没有 SLOWSQL_MYSQL_USER/PASSWORD 环境变量。")
    env = {}
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    if not env.get("MYSQL_USER") or not env.get("MYSQL_PASSWORD"):
        sys.exit(f"[FATAL] {env_path} 里没有 MYSQL_USER / MYSQL_PASSWORD。")
    return env["MYSQL_USER"], env["MYSQL_PASSWORD"]


def resolve_endpoint(instance_id, region):
    out = subprocess.run(
        ["aws", "rds", "describe-db-instances", "--region", region,
         "--db-instance-identifier", instance_id,
         "--query", "DBInstances[0].Endpoint", "--output", "json"],
        capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"[FATAL] 解析 {instance_id} 端点失败：{out.stderr.strip()[:300]}")
    ep = json.loads(out.stdout)
    return ep["Address"], int(ep["Port"])


TABLE_RE = re.compile(r"\bFROM\s+`?(?:\w+`?\s*\.\s*`?)?(\w+)`?", re.IGNORECASE)


def guess_main_table(sql_head):
    """从指纹里抽第一个 FROM 目标，只作为填台账的初稿，人工需复核。抽不出就留空，不硬猜。"""
    m = TABLE_RE.search(sql_head or "")
    return m.group(1) if m else ""


# ---------------------------------------------------------------- fetch

QUERY = """
WITH base AS (
  SELECT s.data_date, s.instance, s.database_name, MD5(s.query) AS digest_id,
         s.exec_count, s.sum_sec, s.max_sec,
         s.avg_rows_examined, s.avg_rows_sent, s.sum_no_index_used,
         LEFT(s.query, 400) AS q,
         LAG(s.exec_count)        OVER w AS p_exec,
         LAG(s.sum_sec)           OVER w AS p_sum,
         LAG(s.sum_no_index_used) OVER w AS p_noidx
  FROM luckyus_db_collection.t_dba_collect_slow_query s
  WHERE s.data_date BETWEEN DATE_SUB(CURDATE(), INTERVAL %s DAY) AND CURDATE()
    AND s.instance IN ({placeholders})
  WINDOW w AS (PARTITION BY s.instance, s.database_name, MD5(s.query) ORDER BY s.data_date)
),
d AS (
  SELECT b.*,
    CASE WHEN p_exec  IS NULL OR exec_count        < p_exec  THEN exec_count        ELSE exec_count        - p_exec  END AS d_exec,
    CASE WHEN p_sum   IS NULL OR sum_sec           < p_sum   THEN sum_sec           ELSE sum_sec           - p_sum   END AS d_sum,
    CASE WHEN p_noidx IS NULL OR sum_no_index_used < p_noidx THEN sum_no_index_used ELSE sum_no_index_used - p_noidx END AS d_noidx,
    CASE WHEN p_exec  IS NULL OR exec_count        < p_exec  THEN 1 ELSE 0 END AS is_baseline
  FROM base b
  WHERE data_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
)
SELECT instance, database_name, digest_id,
       SUM(d_exec)                                   AS d_exec,
       ROUND(SUM(d_sum), 1)                          AS d_dbtime,
       ROUND(SUM(d_sum) / NULLIF(SUM(d_exec), 0), 2) AS avg_sec,
       MAX(max_sec)                                  AS max_sec,
       ROUND(MAX(avg_rows_examined))                 AS rows_examined,
       MAX(avg_rows_sent)                            AS rows_sent,
       SUM(d_noidx)                                  AS no_index,
       MAX(is_baseline)                              AS is_baseline,
       MIN(q)                                        AS sql_head
FROM d
GROUP BY instance, database_name, digest_id
HAVING SUM(d_sum) > 0
ORDER BY SUM(d_sum) DESC
"""


def fetch_window(instances, days, host, port, user, pwd):
    import pymysql
    ph = ",".join(["%s"] * len(instances))
    sql = QUERY.format(placeholders=ph)
    params = [days + 1] + list(instances) + [days]
    conn = pymysql.connect(host=host, port=port, user=user, password=pwd,
                           connect_timeout=10, read_timeout=120,
                           cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------- classify

def to_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def classify(row, reg_row, days, args, today):
    """返回 (类别, 说明)。类别决定是否要人看。"""
    cur_dbt = to_float(row["d_dbtime"])
    cur_per_day = cur_dbt / days
    cur_avg = to_float(row["avg_sec"])

    if reg_row is None:
        return "NEW", "台账中无记录"

    status = (reg_row.get("status") or "").strip()
    base_dbt = to_float(reg_row.get("base_dbtime_7d_sec"))
    base_avg = to_float(reg_row.get("base_avg_sec"))
    base_per_day = base_dbt / 7.0 if base_dbt else 0.0

    if status == "fixed":
        return "RECURRED", f"台账标 fixed，本周仍产生 {cur_dbt:.0f}s DB 时间"

    reasons = []
    if base_per_day > 0 and cur_per_day > base_per_day * args.regress_factor:
        reasons.append(f"日均 DB 时间 {base_per_day:.1f}→{cur_per_day:.1f}s "
                       f"(×{cur_per_day / base_per_day:.1f})")
    if base_avg > 0 and cur_avg > base_avg * args.regress_factor:
        reasons.append(f"平均耗时 {base_avg:.2f}→{cur_avg:.2f}s "
                       f"(×{cur_avg / base_avg:.1f})")
    if reasons:
        return "REGRESSED", "；".join(reasons)

    recheck = (reg_row.get("recheck_after") or "").strip()
    if recheck:
        try:
            if dt.date.fromisoformat(recheck) <= today:
                return "DUE", f"recheck_after={recheck} 已到期"
        except ValueError:
            return "DUE", f"recheck_after={recheck!r} 格式非法，按到期处理"

    if status == "pending":
        first = (reg_row.get("first_analyzed") or "").strip()
        try:
            age = (today - dt.date.fromisoformat(first)).days if first else None
        except ValueError:
            age = None
        if age is not None and age >= args.stale_days:
            return "STALE", f"pending 已挂 {age} 天未出结论"
        return "KNOWN", f"pending{f'（{age} 天）' if age is not None else ''}"

    return "KNOWN", f"{status}，指标稳定"


ORDER = {"RECURRED": 0, "REGRESSED": 1, "NEW": 2, "DUE": 3, "STALE": 4, "KNOWN": 5}
MARK = {"RECURRED": "!!", "REGRESSED": "!", "NEW": "+", "DUE": "@", "STALE": "~", "KNOWN": " "}


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description="每周慢 SQL 分诊：本周榜单 vs 已分析台账")
    p.add_argument("--days", type=int, default=7, help="分析窗口天数（默认 7）")
    p.add_argument("--level", default="L0", help="等级过滤，逗号分隔，如 L0,L1；ALL 表示全部（默认 L0）")
    p.add_argument("--min-dbtime", type=float, default=30.0,
                   help="窗口内新增 DB 时间低于该秒数的指纹直接忽略（默认 30）")
    p.add_argument("--regress-factor", type=float, default=1.5,
                   help="日均 DB 时间或平均耗时超过基线的这个倍数即判为劣化（默认 1.5）")
    p.add_argument("--stale-days", type=int, default=30,
                   help="pending 状态挂满这么多天就催办（默认 30）")
    p.add_argument("--registry", default=DEFAULT_REGISTRY)
    p.add_argument("--tier-map", default=DEFAULT_TIERMAP)
    p.add_argument("--env-file", default=DEFAULT_ENV)
    p.add_argument("--host-instance", default=DEFAULT_HOST_ID, help="采集表所在 RDS 实例")
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--show-known", action="store_true", help="连 KNOWN 一起打印")
    p.add_argument("--show-sql", action="store_true", help="为需要关注的条目打印 SQL 指纹头部")
    p.add_argument("--emit-md", metavar="FILE", help="输出 markdown 到文件，可直接贴进周报")
    p.add_argument("--append-new", action="store_true",
                   help="把 NEW 以 status=pending 追加进台账（只追加，不改动已有行）")
    args = p.parse_args()

    today = dt.date.today()
    tiers = load_tier_map(args.tier_map)
    registry = load_registry(args.registry)

    wanted = None if args.level.upper() == "ALL" else {s.strip().upper() for s in args.level.split(",")}
    instances = sorted(i for i, t in tiers.items() if wanted is None or t["level"].upper() in wanted)
    if not instances:
        sys.exit(f"[FATAL] 分级表里没有等级为 {args.level} 的实例。")

    user, pwd = load_db_credentials(args.env_file)
    host, port = resolve_endpoint(args.host_instance, args.region)
    rows = fetch_window(instances, args.days, host, port, user, pwd)

    results, skipped_small = [], 0
    for r in rows:
        if to_float(r["d_dbtime"]) < args.min_dbtime:
            skipped_small += 1
            continue
        key = (r["instance"], r["database_name"], r["digest_id"])
        reg_row = registry.get(key)
        cat, why = classify(r, reg_row, args.days, args, today)
        results.append({
            "cat": cat, "why": why, "row": r, "reg": reg_row,
            "level": tiers.get(r["instance"], {}).get("level", "?"),
            "owner": (reg_row or {}).get("owner") or tiers.get(r["instance"], {}).get("owner", ""),
        })
    results.sort(key=lambda x: (ORDER[x["cat"]], -to_float(x["row"]["d_dbtime"])))

    counts = {}
    for x in results:
        counts[x["cat"]] = counts.get(x["cat"], 0) + 1
    actionable = [x for x in results if x["cat"] != "KNOWN"]

    # ---------- terminal ----------
    win = f"{today - dt.timedelta(days=args.days)} ~ {today}"
    print(f"\n慢 SQL 周度分诊 | 窗口 {win}（{args.days}d） | 等级 {args.level} "
          f"| {len(instances)} 台实例 | 阈值 >= {args.min_dbtime:g}s")
    print(f"台账 {len(registry)} 条 | 榜单命中 {len(results)} 条"
          f"（另有 {skipped_small} 条低于 {args.min_dbtime:g}s 已忽略）")
    print("统计：" + " ".join(f"{k}={counts[k]}" for k in sorted(counts, key=lambda c: ORDER[c])) or "统计：无")
    print("-" * 118)
    print(f"{'':2} {'类别':<10} {'等级':<4} {'实例':<32} {'指纹':<10} "
          f"{'DB时间':>9} {'次数':>7} {'均耗':>7}  说明")
    print("-" * 118)
    shown = results if args.show_known else actionable
    if not shown:
        print("  本周没有需要人看的条目 —— 榜单上的指纹全部已在台账中且指标稳定。")
    for x in shown:
        r = x["row"]
        print(f"{MARK[x['cat']]:2} {x['cat']:<10} {x['level']:<4} {r['instance']:<32} "
              f"{r['digest_id'][:8]:<10} {to_float(r['d_dbtime']):>8.1f}s "
              f"{int(to_float(r['d_exec'])):>7} {to_float(r['avg_sec']):>6.2f}s  {x['why']}")
        if args.show_sql and x["cat"] != "KNOWN":
            head = " ".join((r["sql_head"] or "").split())[:150]
            print(f"{'':22}{r['database_name']} | {head}")
    print("-" * 118)
    if counts.get("NEW"):
        print(f"→ {counts['NEW']} 条待分析。分析完把结论写回 {os.path.basename(args.registry)}"
              f"（status 改 analyzed，填 verdict / report_id / action_ids / 基线）。")
    if counts.get("RECURRED"):
        print("→ 有 RECURRED：台账标了 fixed 却又上榜，说明修复没生效，优先看。")

    # ---------- markdown ----------
    if args.emit_md:
        L = [f"## 慢 SQL 周度分诊 · {win}", "",
             f"- 窗口 {args.days} 天，等级 {args.level}（{len(instances)} 台实例），"
             f"忽略新增 DB 时间 < {args.min_dbtime:g}s 的指纹",
             f"- 台账 {len(registry)} 条；本周榜单命中 {len(results)} 条，"
             f"其中需处理 {len(actionable)} 条、已分析静默 {counts.get('KNOWN', 0)} 条",
             "", "| 类别 | 等级 | 实例 | 库 | 指纹 | 新增DB时间 | 次数 | 平均耗时 | 说明 | 负责人 |",
             "|---|---|---|---|---|---:|---:|---:|---|---|"]
        for x in (shown or []):
            r = x["row"]
            L.append(f"| {x['cat']} | {x['level']} | `{r['instance']}` | `{r['database_name']}` | "
                     f"`{r['digest_id'][:8]}` | {to_float(r['d_dbtime']):.1f} s | "
                     f"{int(to_float(r['d_exec']))} | {to_float(r['avg_sec']):.2f} s | "
                     f"{x['why']} | {x['owner']} |")
        if not shown:
            L.append("| — | | | | | | | | 本周无需处理条目 | |")
        L += ["", "> 口径：明细来自 `t_dba_collect_slow_query`，只收录 avg_sec ≥ 1s 的指纹，"
              "不代表慢查询总量（总量见 Prometheus `mysql_global_status_slow_queries`）。"]
        with open(args.emit_md, "w", encoding="utf-8") as fh:
            fh.write("\n".join(L) + "\n")
        print(f"→ markdown 已写入 {args.emit_md}")

    # ---------- append ----------
    if args.append_new:
        new_rows = [x for x in results if x["cat"] == "NEW"]
        if not new_rows:
            print("→ --append-new：没有 NEW，台账未改动。")
        else:
            with open(args.registry, "a", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=REGISTRY_COLS, extrasaction="ignore")
                for x in new_rows:
                    r = x["row"]
                    w.writerow({
                        "digest_id": r["digest_id"], "instance": r["instance"],
                        "schema_name": r["database_name"],
                        "main_table": guess_main_table(r["sql_head"]),
                        "level": x["level"], "status": "pending",
                        "first_analyzed": today.isoformat(), "last_reviewed": "",
                        "report_id": "", "owner": x["owner"], "action_ids": "",
                        "base_dbtime_7d_sec": round(to_float(r["d_dbtime"]) / args.days * 7, 1),
                        "base_exec_7d": int(round(to_float(r["d_exec"]) / args.days * 7)),
                        "base_avg_sec": to_float(r["avg_sec"]),
                        "base_rows_examined": int(to_float(r["rows_examined"])),
                        "recheck_after": "", "verdict": "",
                    })
            print(f"→ --append-new：已追加 {len(new_rows)} 条 status=pending 到 {args.registry}")
            print("  注意 main_table 是从指纹自动抽取的初稿，请人工复核后再提交。")

    return 1 if any(x["cat"] in ("RECURRED", "REGRESSED") for x in results) else 0


if __name__ == "__main__":
    sys.exit(main())
