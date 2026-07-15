#!/usr/bin/env python3
"""
sync_redis_monitoring.py — 一站式维护 AWS Redis 监控的三个文件。

替代原来的 aws-redis.py / diff.py / target_diff.py。

单一数据源 = redis-password.file（你手工维护的唯一文件）：
    {
      "rediss://master.luckyus-<svc>.<token>.use1.cache.amazonaws.com:6379": "<AUTH-TOKEN>",
      "redis://master.luckyus-<非加密svc>....:6379": ""
    }
  · key 的前缀 = 该实例真实 TLS 状态：加密 rediss://，非加密 redis://
  · value = AUTH token；非加密/无 AUTH 实例填空字符串 ""

脚本据此派生并写回两个 targets 文件（格式与旧脚本一致 [{"targets":[...],"labels":{}}]）：
  · EXPORTER_TARGETS   —— 全部 rediss://（去重、排序）
  · PROMETHEUS_TARGETS —— 原样保留 redis://redis:// 前缀（排序、去重）

并对照 ldas CMDB 表 cache_cloud_app(app_status=1) 做旁路校验（可选，连不上就跳过）：
  · 在营但密码文件里没有        → 你漏加了，需补
  · 密码文件里有但 CMDB 已下线   → 僵尸项，建议清理

用法：
  python3 sync_redis_monitoring.py            # 只检查 + 打印将要发生的变化，不写文件（默认 dry-run）
  python3 sync_redis_monitoring.py --apply     # 备份后真正写回两个 targets 文件
  LDAS_PWD=xxx python3 sync_redis_monitoring.py --apply   # 提供 ldas 密码以启用 CMDB 旁路校验

改完 targets 文件后：Prometheus 是 file_sd 热加载，无需 reload。
若你**改动了 redis-password.file**（加/改密码），记得重启 exporter（密码启动时才读）：
  kill "$(pgrep -f 'redis_exporter .*-web.listen-address=\":9321\"')" ; ./start.sh
"""

import argparse
import json
import os
import sys
import datetime

# ----- 路径（按主机实际情况调整）-----------------------------------------
EXPORTER_DIR       = "/data/redis-exporter/redis_exporter-v1.74.0.linux-amd64"
PASSWORD_FILE      = os.path.join(EXPORTER_DIR, "redis-password.file")
EXPORTER_TARGETS   = os.path.join(EXPORTER_DIR, "aws-redis-targets.json")
PROMETHEUS_TARGETS = "/data/prometheus-2.43.0.linux-amd64/aws-redis-targets.json"

# ----- ldas CMDB（旁路校验用，可选）--------------------------------------
LDAS = {
    "host": "aws-luckyus-ldas-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com",
    "user": "luckyozono_A_o",
    "password": os.environ.get("LDAS_PWD", ""),   # 不硬编码；没给就跳过 CMDB 校验
    "database": "luckyus_ozono",
    "port": 3306,
}


def hostport(uri: str) -> str:
    """去掉 scheme，返回 host:port，用于跨前缀比较。"""
    return uri.split("://", 1)[-1]


def to_rediss(uri: str) -> str:
    return "rediss://" + hostport(uri)


def load_password_file(path: str) -> dict:
    if not os.path.exists(path):
        sys.exit(f"[FATAL] 密码文件不存在: {path}")
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        sys.exit(f"[FATAL] {path} 应为 JSON 对象 {{uri: token}}")
    return data


def build_targets(pwd: dict):
    """从密码文件派生两个 targets 列表。"""
    prom = sorted(set(pwd.keys()))                        # 原样前缀
    expo = sorted({to_rediss(u) for u in pwd.keys()})     # 全 rediss://
    return expo, prom


def write_targets(path: str, targets: list, apply: bool):
    payload = [{"targets": targets, "labels": {}}]
    new_text = json.dumps(payload, indent=2)
    old_text = ""
    if os.path.exists(path):
        with open(path) as f:
            old_text = f.read()
    if old_text.strip() == new_text.strip():
        print(f"  [=] {path} 无变化 ({len(targets)} 项)")
        return
    print(f"  [~] {path}: {len(json.loads(old_text)[0]['targets']) if old_text.strip() else 0} → {len(targets)} 项")
    if apply:
        if old_text:
            bak = f"{path}.bak.{datetime.datetime.now():%Y%m%d-%H%M%S}"
            with open(bak, "w") as f:
                f.write(old_text)
            print(f"      备份 → {bak}")
        with open(path, "w") as f:
            f.write(new_text)
        print(f"      已写入")


def sanity_checks(pwd: dict):
    """密码文件自检：同一 host 出现多前缀 / 空密码统计。"""
    seen, dups, empty = {}, [], 0
    for uri, tok in pwd.items():
        hp = hostport(uri)
        if hp in seen:
            dups.append(hp)
        seen[hp] = uri
        if not tok:
            empty += 1
    if dups:
        for hp in dups:
            print(f"  [!] 同一 host 多前缀重复: {hp}（一个 host 只应有一条）")
    print(f"  [i] 密码文件共 {len(pwd)} 条；其中空密码(非加密/无AUTH) {empty} 条")
    return not dups


def cmdb_crosscheck(pwd: dict):
    if not LDAS["password"]:
        print("  [skip] 未提供 LDAS_PWD，跳过 CMDB 旁路校验")
        return
    try:
        import pymysql
    except ImportError:
        print("  [skip] 未安装 pymysql，跳过 CMDB 旁路校验")
        return
    try:
        conn = pymysql.connect(**LDAS)
    except Exception as e:
        print(f"  [skip] 连 ldas 失败，跳过 CMDB 校验: {e}")
        return
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT host_info FROM cache_cloud_app WHERE app_status=1")
            active = {r[0] for r in cur.fetchall()}
    finally:
        conn.close()

    pwd_hp = {hostport(u) for u in pwd.keys()}
    missing = sorted(active - pwd_hp)         # 在营但密码文件没有
    stale   = sorted(pwd_hp - active)         # 密码文件有但已下线
    print(f"  [i] CMDB 在营 {len(active)} / 密码文件 {len(pwd_hp)}")
    for hp in missing:
        print(f"  [!] 在营但密码文件缺失（需手工补 {{uri: token}}）: {hp}")
    for hp in stale:
        print(f"  [?] 密码文件有但 CMDB 已下线（建议清理）: {hp}")
    if not missing and not stale:
        print("  [ok] 密码文件与 CMDB 在营实例集合一致")


def main():
    ap = argparse.ArgumentParser(description="一站式维护 AWS Redis 监控三文件")
    ap.add_argument("--apply", action="store_true",
                    help="真正写回 targets 文件（默认只 dry-run 检查）")
    args = ap.parse_args()

    print(f"源: {PASSWORD_FILE}")
    pwd = load_password_file(pwd_path := PASSWORD_FILE)

    print("\n[1] 密码文件自检")
    ok = sanity_checks(pwd)

    print("\n[2] CMDB 旁路校验")
    cmdb_crosscheck(pwd)

    print("\n[3] 生成 targets" + ("（--apply 写回）" if args.apply else "（dry-run，不写）"))
    expo, prom = build_targets(pwd)
    write_targets(EXPORTER_TARGETS, expo, args.apply)
    write_targets(PROMETHEUS_TARGETS, prom, args.apply)

    if not args.apply:
        print("\n这是 dry-run。确认无误后加 --apply 写回。")
    else:
        print("\n完成。Prometheus file_sd 会热加载 targets。")
        print("若你改过 redis-password.file，请重启 exporter 使新密码生效。")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
