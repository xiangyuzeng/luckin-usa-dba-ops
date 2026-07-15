#!/usr/bin/env python3
"""
sync_redis_monitoring.py — 全自动维护 AWS Redis 监控的三个文件（零手工）。

替代旧的 aws-redis.py / diff.py / target_diff.py，并且**连密码都不用手工维护**。

数据源（两个，都是权威）：
  · AWS ElastiCache  describe-replication-groups  → 每集群 endpoint + TransitEncryptionEnabled + AuthTokenEnabled
  · ldas CMDB        luckyus_ozono.cache_cloud_app(app_status=1) → 每实例 host_info(host:port) + password

join 键：DB 的 host_info  ==  AWS 的 PrimaryEndpoint.Address + ":" + Port

派生规则（每集群）：
  · prefix = "rediss://" if TransitEncryptionEnabled else "redis://"    ← 真实 TLS
  · token  = DB password if AuthTokenEnabled else ""                    ← 非 AUTH 一律空
    （DB 对非 AUTH 实例也存了密码，但那种密码塞给 exporter 反而会被 Redis 拒，故置空）

生成三个文件，**同一集群三处前缀一致**：
  · redis-password.file            {  "<prefix><host>:<port>": "<token>"  }   (0600 权限)
  · exporter aws-redis-targets.json   [ { "targets": ["<prefix><host>:<port>", ...], "labels": {} } ]
  · prometheus aws-redis-targets.json 同上

用法：
  python3 sync_redis_monitoring.py             # dry-run：拉数据、join、报告差异，不写文件（默认）
  python3 sync_redis_monitoring.py --apply      # 备份后写回三个文件
  环境变量 LDAS_PWD 必填（ldas 只读密码）；AWS 走本机 aws cli 凭证。

写完后：Prometheus file_sd 热加载 targets（无需 reload）；
       若 redis-password.file 有变化，重启 exporter（密码启动时才读）：
       kill "$(pgrep -f 'redis_exporter .*-web.listen-address=\":9321\"')" ; ./start.sh
"""

import argparse
import json
import os
import subprocess
import sys
import datetime

# ----- 路径（按主机实际情况调整）-----------------------------------------
EXPORTER_DIR       = "/data/redis-exporter/redis_exporter-v1.74.0.linux-amd64"
PASSWORD_FILE      = os.path.join(EXPORTER_DIR, "redis-password.file")
EXPORTER_TARGETS   = os.path.join(EXPORTER_DIR, "aws-redis-targets.json")
PROMETHEUS_TARGETS = "/data/prometheus-2.43.0.linux-amd64/aws-redis-targets.json"
REGION             = "us-east-1"

# ----- ldas CMDB ----------------------------------------------------------
LDAS = {
    "host": "aws-luckyus-ldas-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com",
    "user": "luckyozono_A_o",
    "password": os.environ.get("LDAS_PWD", ""),   # 不硬编码
    "database": "luckyus_ozono",
    "port": 3306,
}


# ========================= 数据采集层 =========================
def fetch_aws_rgs(region=REGION) -> dict:
    """返回 { "<ep>:<port>": {"id":.., "tls":bool, "auth":bool} }。走本机 aws cli。"""
    q = ("ReplicationGroups[].{id:ReplicationGroupId,"
         "tls:TransitEncryptionEnabled,auth:AuthTokenEnabled,"
         "ep:NodeGroups[0].PrimaryEndpoint.Address,"
         "port:NodeGroups[0].PrimaryEndpoint.Port}")
    out = subprocess.check_output(
        ["aws", "elasticache", "describe-replication-groups",
         "--region", region, "--query", q, "--output", "json"])
    rgs = json.loads(out)
    amap = {}
    for r in rgs:
        if not r.get("ep"):
            continue
        amap[f"{r['ep']}:{r['port']}"] = {
            "id": r["id"], "tls": bool(r["tls"]), "auth": bool(r["auth"])}
    return amap


def fetch_db_instances() -> list:
    """返回 [ {"app": app_name, "hostport": host_info, "password": pwd}, ... ]（app_status=1）。"""
    import pymysql
    conn = pymysql.connect(**LDAS)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT app_name, host_info, password "
                        "FROM cache_cloud_app WHERE app_status=1")
            return [{"app": a, "hostport": h, "password": p or ""}
                    for (a, h, p) in cur.fetchall()]
    finally:
        conn.close()


# ========================= 纯逻辑层（可单测）=========================
def build_plan(db_rows: list, aws_map: dict):
    """
    join DB 实例与 AWS RG，产出：
      entries: [ {"hostport":.., "prefix":.., "uri":.., "token":.., "id":.., "tls":..} ]  已 join 上的
      db_only:  [hostport, ...]  DB 在营但 AWS 找不到（改名/非 ElastiCache?）
      aws_only: [id, ...]        AWS 有 RG 但 DB 未登记为在营（未纳管?）
    """
    entries, db_only = [], []
    matched_hostports = set()
    for row in db_rows:
        hp = row["hostport"]
        rg = aws_map.get(hp)
        if rg is None:
            db_only.append(hp)
            continue
        matched_hostports.add(hp)
        prefix = "rediss://" if rg["tls"] else "redis://"
        token = row["password"] if rg["auth"] else ""
        entries.append({
            "hostport": hp, "prefix": prefix, "uri": prefix + hp,
            "token": token, "id": rg["id"], "tls": rg["tls"]})
    aws_only = sorted(v["id"] for k, v in aws_map.items() if k not in matched_hostports)
    entries.sort(key=lambda e: e["uri"])
    return entries, sorted(db_only), aws_only


def render_files(entries: list):
    """从 entries 渲染三个文件的目标内容（字符串）。"""
    pwd_obj = {e["uri"]: e["token"] for e in entries}
    targets = [e["uri"] for e in entries]
    sd_obj = [{"targets": targets, "labels": {}}]
    return (json.dumps(pwd_obj, indent=2),
            json.dumps(sd_obj, indent=2))


# ========================= 写文件层 =========================
def write_if_changed(path, new_text, apply, secret=False):
    old = ""
    if os.path.exists(path):
        with open(path) as f:
            old = f.read()
    if old.strip() == new_text.strip():
        print(f"  [=] {path} 无变化")
        return False
    print(f"  [~] {path} 将更新")
    if apply:
        if old:
            bak = f"{path}.bak.{datetime.datetime.now():%Y%m%d-%H%M%S}"
            with open(bak, "w") as f:
                f.write(old)
            print(f"      备份 → {bak}")
        with open(path, "w") as f:
            f.write(new_text)
        if secret:
            os.chmod(path, 0o600)
        print("      已写入" + ("（0600）" if secret else ""))
    return True


def main():
    ap = argparse.ArgumentParser(description="全自动维护 AWS Redis 监控三文件")
    ap.add_argument("--apply", action="store_true",
                    help="真正写回三个文件（默认 dry-run 只报告）")
    args = ap.parse_args()

    if not LDAS["password"]:
        sys.exit("[FATAL] 需设置环境变量 LDAS_PWD（ldas 只读密码）")

    print("[1] 拉取 AWS ElastiCache 加密/AUTH 状态 ...")
    aws_map = fetch_aws_rgs()
    tls_n = sum(1 for v in aws_map.values() if v["tls"])
    print(f"    AWS RG {len(aws_map)}：TLS {tls_n} / 非TLS {len(aws_map)-tls_n}")

    print("[2] 拉取 ldas cache_cloud_app 在营实例 ...")
    db_rows = fetch_db_instances()
    print(f"    在营实例 {len(db_rows)}")

    print("[3] join + 派生 ...")
    entries, db_only, aws_only = build_plan(db_rows, aws_map)
    non_tls = [e["id"] for e in entries if not e["tls"]]
    print(f"    已匹配 {len(entries)}；其中非TLS(redis://) {len(non_tls)}: {non_tls}")
    for hp in db_only:
        print(f"  [!] DB 在营但 AWS 无对应 RG（改名/非ElastiCache?）: {hp}")
    for rid in aws_only:
        print(f"  [?] AWS 有 RG 但 DB 未登记在营（未纳管?）: {rid}")

    print("[4] 生成三文件" + ("（--apply 写回）" if args.apply else "（dry-run，不写）"))
    pwd_text, sd_text = render_files(entries)
    changed = False
    changed |= write_if_changed(PASSWORD_FILE, pwd_text, args.apply, secret=True)
    changed |= write_if_changed(EXPORTER_TARGETS, sd_text, args.apply)
    changed |= write_if_changed(PROMETHEUS_TARGETS, sd_text, args.apply)

    if not args.apply:
        print("\n这是 dry-run。确认无误后加 --apply 写回。")
    else:
        print("\n完成。Prometheus file_sd 会热加载 targets。")
        print("redis-password.file 若有变化，请重启 exporter 使新密码生效。")
    # db_only 是需要人工关注的硬问题 → 非零退出码
    sys.exit(1 if db_only else 0)


if __name__ == "__main__":
    main()
