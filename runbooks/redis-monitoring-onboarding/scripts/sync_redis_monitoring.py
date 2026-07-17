#!/usr/bin/env python3
"""
sync_redis_monitoring.py — 全自动维护 AWS Redis 监控的三个文件（零手工）。

替代旧的 aws-redis.py / diff.py / target_diff.py，并且**连密码都不用手工维护**。

数据源（三个）：
  · AWS ElastiCache  describe-replication-groups  → 每集群 endpoint + TransitEncryptionEnabled + AuthTokenEnabled
  · ldas CMDB        luckyus_ozono.cache_cloud_app(app_status=1) → 每在营实例 host_info(host:port)
                     （只用于发现集群 + 与 AWS 对账，**不再取 password**）
  · 现有 redis-password.file → 每集群 token 的**权威来源**（见下方 token 规则）

join 键：DB 的 host_info  ==  AWS 的 PrimaryEndpoint.Address + ":" + Port

派生规则（每集群）：
  · prefix = "rediss://" if TransitEncryptionEnabled else "redis://"    ← 真实 TLS，取自 AWS
  · token  = 现有 redis-password.file 里该集群的 token（按 host:port 查，前缀无关）
             非 AUTH 集群一律空；AUTH 集群但文件里没有 → 标 token_missing，人工补，先写空、绝不猜值
    ⚠️ token 绝不取自 ozono：ozono.cache_cloud_app.password 对 AUTH 集群与真实 AUTH token 不符，
       2026-07-16 曾因 --apply 用 ozono 密码覆盖，导致 71 个 AUTH 集群认证失败 redis_up=0，已回滚。
       现有密码文件才是 token 的唯一权威来源；脚本只增删 key/前缀、绝不改动已有 token。

生成三个文件，**同一集群三处前缀一致**：
  · redis-password.file            {  "<prefix><host>:<port>": "<token>"  }   (0600 权限)
  · exporter aws-redis-targets.json   [ { "targets": ["<prefix><host>:<port>", ...], "labels": {} } ]
  · prometheus aws-redis-targets.json 同上

用法：
  python3 sync_redis_monitoring.py                       # dry-run：拉数据、join、报告差异，不写（默认）
  python3 sync_redis_monitoring.py --apply               # 备份后写回三个文件
  python3 sync_redis_monitoring.py --cron [--webhook 飞书URL]  # 定时对账：只读，仅漂移/硬问题时告警(发飞书)，恒退出 0
  （每次都会额外查 Prometheus，找"应监控却未有效监控"的实例；--skip-monitoring-check 可关；
   Prometheus 地址默认 http://10.238.3.136:9090，可用环境变量 PROMETHEUS_URL 覆盖）

AWS 不可达时的行为（权限/凭证/网络/缺 aws CLI，如 cron 主机身份无
elasticache:DescribeReplicationGroups）：
  · --cron：不崩溃、不吐 traceback。降级为"仅监控状态检查"——用现网 targets 文件当
            应监控集合去查 Prometheus，并把"AWS 不可达"当硬问题告警，恒退出 0。
  · --apply / dry-run：缺 TLS/AUTH 真值绝不写文件，干净退出非 0（不吐 traceback）。

ldas 连接信息统一放在一个 0600 配置文件里（endpoint/port/user/password/database 在一起，
不再有裸密码文件），默认 <EXPORTER_DIR>/ldas.conf，可用 --ldas-conf / 环境变量 LDAS_CONF 指定；
password 一项允许被环境变量 LDAS_PASSWORD 覆盖（密管注入场景）。参考模板见同目录 ldas.conf.example。

AWS 凭证：默认走本机 aws cli 凭证链（instance profile / ~/.aws / 环境变量）。若 cron 主机
默认身份没有 elasticache:DescribeReplicationGroups，可在**同一个 ldas.conf 里加可选的 [aws] 段**
（见 load_aws_conf）指定 profile 或 access_key_id/secret_access_key（+可选 region）——密钥只经
环境变量传给子进程、绝不进命令行（防 ps 泄露）。不写 [aws] 段则保持现状（默认链）。

写完后：Prometheus file_sd 热加载 targets（无需 reload）；
       若 redis-password.file 有变化，重启 exporter（密码启动时才读）：
       kill "$(pgrep -f 'redis_exporter .*-web.listen-address=\":9321\"')" ; ./start.sh

告警走飞书自定义机器人（interactive 卡片，红色标题）：--webhook 传机器人 URL；
若机器人开了"签名校验"，把密钥放环境变量 FEISHU_SIGN_SECRET，脚本自动叠加 timestamp+sign。

crontab（无需 shell 包装，直接调本脚本的 --cron 模式）：
  */30 * * * * cd <EXPORTER_DIR> && python3 sync_redis_monitoring.py --cron --webhook https://open.feishu.cn/open-apis/bot/v2/hook/xxxx
"""

import argparse
import configparser
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
DEFAULT_LDAS_CONF  = os.path.join(EXPORTER_DIR, "ldas.conf")
PROM_JOB           = "aws-redis-job"                                    # Prometheus 里 Redis 的 job 标签
PROMETHEUS_URL     = os.environ.get("PROMETHEUS_URL", "http://10.238.3.136:9090")  # 监控状态检查用


# ----- ldas CMDB 连接配置（单文件，endpoint/port/user/password/database 在一起）-----
def load_ldas_conf(path: str) -> dict:
    """从 INI 配置读 ldas 连接信息。缺文件/缺段/缺字段一律 FATAL，绝不半路裸奔。

    password 允许被环境变量 LDAS_PASSWORD 覆盖（用于密管/CI 注入，不落盘）。
    """
    cp = configparser.ConfigParser()
    if not cp.read(path):
        sys.exit(f"[FATAL] 读不到 ldas 配置文件: {path}"
                 f"（复制 ldas.conf.example 为 {os.path.basename(path)} 并填好，chmod 600）")
    if not cp.has_section("ldas"):
        sys.exit(f"[FATAL] {path} 缺少 [ldas] 段（见 ldas.conf.example）")
    s = cp["ldas"]
    conf = {
        "host": s.get("host", "").strip(),
        "port": s.getint("port", 3306),
        "user": s.get("user", "").strip(),
        "password": os.environ.get("LDAS_PASSWORD", s.get("password", "")).strip(),
        "database": s.get("database", "").strip(),
    }
    missing = [k for k in ("host", "user", "password", "database") if not conf[k]]
    if missing:
        sys.exit(f"[FATAL] ldas 配置缺字段: {', '.join(missing)}（见 {path}）")
    return conf


def load_aws_conf(path: str) -> dict:
    """读同一 ldas.conf 里**可选的 [aws] 段** → AWS 凭证/Profile（全部可选）。

    缺文件 / 缺 [aws] 段 → 返回 {}（退回 aws CLI 默认凭证链，即现状行为，不 FATAL），
    因此完全向后兼容：不写 [aws] 段的老配置照跑。二选一（优先 profile）：
      profile          = <~/.aws/credentials 里的 profile 名>  ← 推荐，密钥由 aws CLI 托管
      access_key_id    = ...        ┐ 明文落盘，仅在这个 0600 文件里用；
      secret_access_key= ...        ┘ 两者必须同时给（只给一个 = 配置错，FATAL）
      region           = us-east-1  （可选，覆盖默认 REGION）
    profile 与 access_key 同时给 = 歧义 → FATAL，让用户明确二选一。
    这里只读文件、不碰 env：既然选了"写进配置文件"，就以文件为准（env 覆盖场景请留空
    [aws] 段、改用 crontab 的 AWS_PROFILE= 前缀，aws CLI 原生认）。
    """
    cp = configparser.ConfigParser()
    if not cp.read(path) or not cp.has_section("aws"):
        return {}
    s = cp["aws"]
    profile = s.get("profile", "").strip()
    ak = s.get("access_key_id", "").strip()
    sk = s.get("secret_access_key", "").strip()
    if bool(ak) != bool(sk):
        sys.exit("[FATAL] [aws] 段 access_key_id 与 secret_access_key 必须同时提供"
                 "（或都留空、改用 profile）")
    if profile and (ak or sk):
        sys.exit("[FATAL] [aws] 段 profile 与 access_key_id/secret_access_key 只能二选一")
    return {"profile": profile, "access_key_id": ak,
            "secret_access_key": sk, "region": s.get("region", "").strip()}


def build_aws_invocation(query, region, aws_conf, base_env):
    """构造 aws describe-replication-groups 的 (argv, env)。纯函数、可单测、不碰网络。

    凭证注入规则（安全关键）：
      · access_key_id/secret_access_key 走 **env**（AWS_ACCESS_KEY_ID/SECRET），
        **绝不进 argv**——命令行参数会出现在 ps/进程列表里，等于泄密。同时 pop 掉
        env 里可能残留的 AWS_PROFILE/SESSION_TOKEN，避免与显式密钥冲突。
      · profile 走 `--profile <名>`（profile 名不敏感），并 pop 掉 env 里可能继承来的
        静态 AWS_ACCESS_KEY_ID/SECRET/SESSION_TOKEN（否则主机默认 env 身份会盖过 profile）
        + 同时设 AWS_PROFILE 双保险。
      · 两者都没给 → 原样继承 base_env，退回 aws 默认凭证链（现状行为）。
    """
    aws_conf = aws_conf or {}
    argv = ["aws"]
    env = dict(base_env)
    ak = aws_conf.get("access_key_id", "")
    sk = aws_conf.get("secret_access_key", "")
    if ak and sk:
        env["AWS_ACCESS_KEY_ID"] = ak
        env["AWS_SECRET_ACCESS_KEY"] = sk
        for k in ("AWS_PROFILE", "AWS_SESSION_TOKEN"):
            env.pop(k, None)
    elif aws_conf.get("profile"):
        argv += ["--profile", aws_conf["profile"]]
        env["AWS_PROFILE"] = aws_conf["profile"]
        for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
            env.pop(k, None)
    argv += ["elasticache", "describe-replication-groups",
             "--region", region, "--query", query, "--output", "json"]
    return argv, env


# ========================= 数据采集层 =========================
class AwsUnavailable(Exception):
    """AWS ElastiCache 拉取失败（权限/凭证/网络/aws CLI 缺失）。

    调用方应据此降级：--cron 降为"仅监控状态检查"并告警，绝不崩溃；
    --apply/dry-run 缺真值时干净退出非 0，绝不用残缺数据写文件。
    2026-07-17 事故：cron 主机身份 dba-downloaddblog-api 无
    elasticache:DescribeReplicationGroups → check_output 抛 CalledProcessError
    直接把整个 cron 打崩（连 Prometheus 监控检查都没跑）。此异常即为兜底。
    """


def fetch_aws_rgs(region=REGION, aws_conf=None) -> dict:
    """返回 { "<ep>:<port>": {"id":.., "tls":bool, "auth":bool} }。走本机 aws cli。

    aws_conf（来自 ldas.conf 的 [aws] 段，见 load_aws_conf）可选，指定 profile 或密钥；
    缺省则用主机默认凭证链。argv/env 由纯函数 build_aws_invocation 构造（密钥只走 env）。
    aws CLI 非零退出（权限/凭证/网络）或不在 PATH 上 → 抛 AwsUnavailable（带原因），
    由调用方降级处理，不让异常冒泡成 traceback 把 cron 打崩。
    """
    q = ("ReplicationGroups[].{id:ReplicationGroupId,"
         "tls:TransitEncryptionEnabled,auth:AuthTokenEnabled,"
         "ep:NodeGroups[0].PrimaryEndpoint.Address,"
         "port:NodeGroups[0].PrimaryEndpoint.Port}")
    argv, env = build_aws_invocation(q, region, aws_conf, os.environ)
    try:
        out = subprocess.check_output(argv, stderr=subprocess.PIPE, env=env)
    except FileNotFoundError as e:                      # aws CLI 不在 PATH
        raise AwsUnavailable("aws CLI 不在 PATH 上") from e
    except subprocess.CalledProcessError as e:          # 权限/凭证/网络：非零退出
        err = (e.stderr or b"").decode("utf-8", "replace").strip()
        raise AwsUnavailable(err or f"aws 退出码 {e.returncode}") from e
    rgs = json.loads(out)
    amap = {}
    for r in rgs:
        if not r.get("ep"):
            continue
        amap[f"{r['ep']}:{r['port']}"] = {
            "id": r["id"], "tls": bool(r["tls"]), "auth": bool(r["auth"])}
    return amap


def fetch_db_instances(ldas_conf: dict) -> list:
    """返回 [ {"app": app_name, "hostport": host_info}, ... ]（app_status=1）。

    只取 host_info：用于发现在营集群 + 与 AWS 对账。**token 不再从 ozono 取**——
    其 password 列对 AUTH 集群与真实 token 不符（2026-07-16 曾因此 --apply 打挂 71 个 AUTH）。
    token 的权威来源是现有 redis-password.file，见 parse_existing_tokens / build_plan。
    """
    import pymysql
    conn = pymysql.connect(**ldas_conf)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT app_name, host_info "
                        "FROM cache_cloud_app WHERE app_status=1")
            return [{"app": a, "hostport": h} for (a, h) in cur.fetchall()]
    finally:
        conn.close()


def fetch_monitoring_state(prom_url: str = PROMETHEUS_URL, job: str = PROM_JOB):
    """查 Prometheus 现状，返回 (up_map, redis_up_map)：{instance -> 0/1}。

    instance 标签 = targets 文件里的 URI（prefix+host:port），与 build_plan 的 entry["uri"] 对齐。
    查询失败抛异常，由调用方兜底（监控状态检查是尽力而为，Prometheus 不可达不该让脚本崩）。
    """
    import urllib.parse
    import urllib.request

    def q(expr):
        url = prom_url.rstrip("/") + "/api/v1/query?query=" + urllib.parse.quote(expr)
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        if data.get("status") != "success":
            raise RuntimeError(f"Prometheus 查询未成功: {expr} -> {data.get('status')}")
        return {it["metric"].get("instance", ""): float(it["value"][1])
                for it in data["data"]["result"]}

    return q(f'up{{job="{job}"}}'), q(f'redis_up{{job="{job}"}}')


# ========================= 纯逻辑层（可单测）=========================
def parse_existing_tokens(pwd_text: str) -> dict:
    """把现有 redis-password.file 文本解析成 { "host:port" -> token }。

    去掉 scheme 前缀按 host:port 归键，使前缀变化（rediss://<->redis://）仍能按集群命中 token。
    空/损坏文本 => {}。**这是 token 的权威来源**：脚本以现有密码文件里的 token 为准，绝不从 ozono 覆盖。
    """
    if not pwd_text.strip():
        return {}
    try:
        raw = json.loads(pwd_text)
    except ValueError:
        return {}
    return {uri.split("://", 1)[-1]: token for uri, token in raw.items()}


def entries_from_targets(sd_text: str) -> list:
    """AWS 不可达时的降级基准：把现网 exporter/prometheus targets 文件当作"应监控集合"，
    重建最小 entries（只含 id/uri）供 check_monitoring 用。

    没有 AWS 就拿不到真实 RG 名 → id 用剥掉 scheme 的 host:port 占位（告警可读即可）。
    去重 + 按 uri 稳定排序；空/损坏文本 => []。这样 AWS 挂了 cron 仍能查
    "现网该被抓的实例，Prometheus 里是不是真在抓且健康"。
    """
    if not sd_text.strip():
        return []
    try:
        groups = json.loads(sd_text)
    except ValueError:
        return []
    uris = set()
    for g in groups:
        for t in g.get("targets", []):
            uris.add(t)
    return [{"id": uri.split("://", 1)[-1], "uri": uri} for uri in sorted(uris)]


def build_plan(db_rows: list, aws_map: dict, existing_tokens: dict):
    """
    join 在营实例与 AWS RG；prefix 取自 AWS TLS，**token 取自现有密码文件**（existing_tokens: host:port -> token）。
    ⚠️ token 绝不取自 ozono（其 password 对 AUTH 集群不可信）。脚本只增删 key/前缀，绝不改动已有 token。产出：
      entries:  [ {"hostport":.., "prefix":.., "uri":.., "token":.., "id":.., "tls":..} ]  已 join 上的
      db_only:  [hostport, ...]  DB 在营但 AWS 找不到（改名/非 ElastiCache?）
      aws_only: [id, ...]        AWS 有 RG 但 DB 未登记为在营（未纳管?）
      token_missing: [hostport, ...]  AUTH 集群但现有密码文件里没有 token（新集群/未纳管）→ 先写空，需人工补，不猜值
    """
    matched = {}          # hostport -> entry；同端点被多 app 共用时只留一条，避免重复 target
    db_only = set()       # 用 set 去重，多条 ghost 行指向同一 endpoint 只报一次
    token_missing = set()
    for row in db_rows:
        hp = row["hostport"]
        if hp in matched:
            continue      # 同端点被多 app 共用，只留一条；token 按 host:port 查，与哪条 app 行无关
        rg = aws_map.get(hp)
        if rg is None:
            db_only.add(hp)
            continue
        prefix = "rediss://" if rg["tls"] else "redis://"
        if rg["auth"]:
            token = existing_tokens.get(hp, "")
            if hp not in existing_tokens:
                token_missing.add(hp)     # AUTH 但文件里没有 → 不猜，标出来
        else:
            token = ""                    # 非 AUTH 一律空（塞 token 会被 redis:// 拒）
        matched[hp] = {
            "hostport": hp, "prefix": prefix, "uri": prefix + hp,
            "token": token, "id": rg["id"], "tls": rg["tls"]}
    aws_only = sorted(v["id"] for k, v in aws_map.items() if k not in matched)
    entries = sorted(matched.values(), key=lambda e: e["uri"])
    return entries, sorted(db_only), aws_only, sorted(token_missing)


def render_files(entries: list):
    """从 entries 渲染三个文件的目标内容（字符串）。"""
    pwd_obj = {e["uri"]: e["token"] for e in entries}
    targets = [e["uri"] for e in entries]
    sd_obj = [{"targets": targets, "labels": {}}]
    return (json.dumps(pwd_obj, indent=2),
            json.dumps(sd_obj, indent=2))


def _canonical(obj):
    """把 JSON 结构规范化：dict 用 == 天然忽略键序，list 按内容排序，从而顺序无关。"""
    if isinstance(obj, dict):
        return {k: _canonical(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return sorted((_canonical(x) for x in obj),
                      key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False))
    return obj


def content_equivalent(old_text: str, new_text: str) -> bool:
    """语义等价判断：两边解析成 JSON 后忽略顺序/排版比较（targets 顺序、键序、缩进都无所谓）。

    任一边解析不了（如空文件/损坏）就退回首尾 strip 的文本比较——空文件 vs 非空 => 不等价 => 算漂移。
    这只喂给 --cron 的漂移告警门槛；写文件层仍走文本比对以把磁盘归一化成规范格式。
    """
    try:
        return _canonical(json.loads(old_text)) == _canonical(json.loads(new_text))
    except (ValueError, TypeError):
        return old_text.strip() == new_text.strip()


def check_monitoring(entries: list, up_map: dict, redis_up_map: dict) -> list:
    """比对"应监控"(entries) 与 Prometheus 现状，挑出**未有效监控**的实例（纯函数，可单测）。

    up_map / redis_up_map: {instance -> 0/1}，来自 Prometheus up{} / redis_up{}。
    返回 [ {"id":.., "uri":.., "reason":..} ]，按 uri 排序；健康(up==1 且 redis_up==1)的不返回。reason：
      not_scraped  应监控但 Prometheus 里根本没有这个 target（漏纳管 / 漂移未 apply / 名字带空格等）
      scrape_down  有 target 但 up==0（DNS/网络，exporter 抓不到）
      auth_down    up==1 但 redis_up==0（连上但认证/连接失败，如缺/错 token）
    """
    problems = []
    for e in entries:
        uri = e["uri"]
        if uri not in up_map:
            reason = "not_scraped"
        elif up_map.get(uri, 0) != 1:
            reason = "scrape_down"
        elif redis_up_map.get(uri, 0) != 1:
            reason = "auth_down"
        else:
            continue                      # up==1 且 redis_up==1 → 健康，跳过
        problems.append({"id": e["id"], "uri": uri, "reason": reason})
    return sorted(problems, key=lambda p: p["uri"])


# ========================= 写文件层 =========================
def write_if_changed(path, new_text, apply, secret=False, old=None):
    if old is None:                              # 允许调用方传入已读内容，避免二次读盘
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


def build_feishu_payload(subject: str, body: str) -> dict:
    """构造飞书自定义机器人消息体（interactive 交互式卡片，红色标题）。

    纯函数、不碰网络/时间，便于单测。签名（开启"签名校验"的机器人才需要）
    由 feishu_sign() 单独在发送时叠加，不放进这里以保持可测。
    """
    content = body.strip() if body.strip() else "（无详情）"
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "red",                       # 告警用红色标题栏
                "title": {"tag": "plain_text", "content": subject},
            },
            "elements": [
                {"tag": "div",
                 "text": {"tag": "lark_md", "content": content}},
            ],
        },
    }


def feishu_sign(secret: str, timestamp: str) -> str:
    """飞书机器人"签名校验"算法：base64(HMAC-SHA256(key=f"{ts}\\n{secret}", msg=""))。

    timestamp 由调用方传入（而非内部取 now）以便单测其确定性。
    """
    import base64
    import hashlib
    import hmac
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(string_to_sign.encode("utf-8"),
                      msg=b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def send_alert(subject: str, body: str, webhook: str = "", secret: str = ""):
    """漂移告警：有飞书 webhook 就 POST 卡片；没配就只打印（cron 已把输出重定向进日志文件）。

    不发邮件、不依赖 cron MAILTO：无 webhook / 发送失败一律打印到 stdout，让它落进日志即可。
    secret 非空（环境变量 FEISHU_SIGN_SECRET）时叠加 timestamp+sign（机器人开了签名校验）。
    飞书即使 HTTP 200 也可能业务失败（返回体 code!=0），故要检查返回码。
    """
    if not webhook:
        print("[ALERT] 未配置飞书 webhook，仅打印（cron 输出已写入日志）：")
        print(subject)
        print(body)
        return

    import urllib.request
    payload = build_feishu_payload(subject, body)
    if secret:
        import time
        ts = str(int(time.time()))
        payload["timestamp"] = ts
        payload["sign"] = feishu_sign(secret, ts)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10).read()
    except Exception as e:                       # 网络/端点问题不该让 cron 崩，打印即可
        print(f"      [WARN] 飞书 webhook 发送失败: {e}")
        print(subject)
        print(body)
        return
    try:
        code = json.loads(resp.decode("utf-8")).get("code", 0)
    except Exception:
        code = 0                                 # 返回体解析不了就当发出去了
    if code:                                     # code!=0 = 飞书侧拒绝（签名错/机器人停用等）
        print(f"      [WARN] 飞书返回错误码 code={code}: {resp!r}")
        print(subject)
        print(body)
    else:
        print(f"      告警已发送到飞书 → {webhook}")


def cron_degraded_no_aws(aws_err: str, webhook: str):
    """--cron 且 AWS 不可达：跳过文件对账（缺 TLS/AUTH 真值，绝不猜/绝不写），
    但仍用现网 exporter targets 当"应监控集合"跑 Prometheus 监控状态检查，
    并把"AWS 不可达"本身当作硬问题告警。恒退出 0（cron 不靠退出码告警）。

    这样即便 cron 主机凭证无 elasticache 权限，"应监控却没在监控/认证挂了"这类
    最有价值的巡检仍照跑，不会因为拉不到 AWS 就整轮瞎掉。
    """
    print(f"    [WARN] AWS ElastiCache 不可达，降级为仅监控状态检查"
          f"（不做文件对账，不写任何文件）: {aws_err}")
    sd_text = ""
    if os.path.exists(EXPORTER_TARGETS):
        with open(EXPORTER_TARGETS) as f:
            sd_text = f.read()
    entries = entries_from_targets(sd_text)
    print(f"    以现网 targets 为降级基准，应监控实例 {len(entries)}")

    not_monitored = []
    print("[6] 检查现有监控状态（应监控但未有效监控的实例）...")
    try:
        up_map, redis_up_map = fetch_monitoring_state()
        not_monitored = check_monitoring(entries, up_map, redis_up_map)
        if not_monitored:
            for p in not_monitored:
                print(f"  [!] 应监控但未生效（{p['reason']}）: {p['id']}  {p['uri']}")
        else:
            print(f"    现网 {len(entries)} 个实例均在监控且健康（up=1, redis_up=1）")
    except Exception as e:                    # Prometheus 也不可达：尽力而为，不再崩
        print(f"    [WARN] 查询 Prometheus 失败，跳过监控状态检查: {e}")

    lines = [
        "硬问题——AWS ElastiCache 不可达，本轮无法做文件对账（TLS/AUTH 真值缺失）：",
        f"  - {aws_err}",
        "  修复方向：给 cron 的 AWS 身份补 elasticache:DescribeReplicationGroups 权限，",
        "  或让脚本用有该权限的凭证/Profile 运行（本轮已降级为仅 Prometheus 监控检查）。",
    ]
    if not_monitored:
        lines.append("硬问题——应监控但未有效监控（Prometheus 现状，基于现网 targets）：")
        lines += [f"  - {p['reason']}: {p['id']}  {p['uri']}" for p in not_monitored]
    subject = (f"[LKUS] AWS Redis 监控降级：ElastiCache 不可达 "
               f"(not_monitored={len(not_monitored)})")
    send_alert(subject, "\n".join(lines), webhook,
               os.environ.get("FEISHU_SIGN_SECRET", ""))
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description="全自动维护 AWS Redis 监控三文件")
    ap.add_argument("--apply", action="store_true",
                    help="真正写回三个文件（默认 dry-run 只报告）")
    ap.add_argument("--cron", action="store_true",
                    help="定时对账模式：只读，仅漂移/硬问题时告警，恒退出 0（不写文件）")
    ap.add_argument("--webhook", default=os.environ.get("REDIS_SYNC_WEBHOOK", ""),
                    help="--cron 告警的飞书机器人 webhook（发 interactive 卡片）；"
                         "缺省则只打印（cron 输出已重定向进日志，不发邮件）。签名校验密钥用环境变量 FEISHU_SIGN_SECRET")
    ap.add_argument("--ldas-conf", default=os.environ.get("LDAS_CONF", DEFAULT_LDAS_CONF),
                    help=f"ldas 连接配置文件（默认 {DEFAULT_LDAS_CONF}）")
    ap.add_argument("--skip-monitoring-check", action="store_true",
                    help="跳过对 Prometheus 现状的检查（默认会查 up/redis_up 找应监控但未生效的实例）")
    args = ap.parse_args()

    # --cron 恒为只读对账；--apply 只在非 cron 时生效
    apply = args.apply and not args.cron
    ldas_conf = load_ldas_conf(args.ldas_conf)
    aws_conf = load_aws_conf(args.ldas_conf)          # 可选 [aws] 段，同一个 0600 文件
    region = aws_conf.get("region") or REGION

    print("[1] 拉取 AWS ElastiCache 加密/AUTH 状态 ...")
    try:
        aws_map = fetch_aws_rgs(region, aws_conf)
    except AwsUnavailable as e:
        if args.cron:
            cron_degraded_no_aws(str(e), args.webhook)   # 降级 + 告警，恒退出 0
        # 非 cron（dry-run / --apply）：缺真值绝不写文件，干净退出非 0（不吐 traceback）
        sys.exit(f"[FATAL] AWS ElastiCache 不可达，无法生成/对账监控文件"
                 f"（需 elasticache:DescribeReplicationGroups 权限）：{e}")
    tls_n = sum(1 for v in aws_map.values() if v["tls"])
    print(f"    AWS RG {len(aws_map)}：TLS {tls_n} / 非TLS {len(aws_map)-tls_n}")

    print("[2] 拉取 ldas cache_cloud_app 在营实例 ...")
    db_rows = fetch_db_instances(ldas_conf)
    print(f"    在营实例 {len(db_rows)}")

    print("[3] 读现有 redis-password.file 里的 token（token 的权威来源，不取自 ozono）...")
    existing_pwd_text = ""
    if os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE) as f:
            existing_pwd_text = f.read()
    existing_tokens = parse_existing_tokens(existing_pwd_text)
    print(f"    现有密码文件已知 token 集群 {len(existing_tokens)}")

    print("[4] join + 派生 ...")
    entries, db_only, aws_only, token_missing = build_plan(
        db_rows, aws_map, existing_tokens)
    non_tls = [e["id"] for e in entries if not e["tls"]]
    print(f"    已匹配 {len(entries)}；其中非TLS(redis://) {len(non_tls)}: {non_tls}")
    for hp in db_only:
        print(f"  [!] DB 在营但 AWS 无对应 RG（改名/非ElastiCache?）: {hp}")
    for hp in token_missing:
        print(f"  [!] AUTH 集群但现有密码文件缺 token（需人工补，先写空 → redis_up 会为0）: {hp}")
    for rid in aws_only:
        print(f"  [?] AWS 有 RG 但 DB 未登记在营（未纳管?）: {rid}")

    print("[5] 生成三文件" + ("（--apply 写回）" if apply else "（dry-run，不写）"))
    pwd_text, sd_text = render_files(entries)
    changed_paths = []      # 文本层面会被改写的（驱动 --apply 归一化 + dry-run 报告）
    drift_paths = []        # 语义层面真的不同的（只喂给 --cron 漂移告警，忽略顺序/排版）
    for path, text, secret in ((PASSWORD_FILE, pwd_text, True),
                               (EXPORTER_TARGETS, sd_text, False),
                               (PROMETHEUS_TARGETS, sd_text, False)):
        old = ""
        if os.path.exists(path):
            with open(path) as f:
                old = f.read()
        semantically_diff = not content_equivalent(old, text)
        if semantically_diff:
            drift_paths.append(path)
        if write_if_changed(path, text, apply, secret=secret, old=old):
            changed_paths.append(path)
            if not semantically_diff:           # 文本变了但内容等价 = 纯归一化，非漂移
                print("      （仅顺序/排版差异，内容等价——写回只是归一化，不算漂移）")

    print("[6] 检查现有监控状态（应监控但未有效监控的实例）...")
    not_monitored = []
    if args.skip_monitoring_check:
        print("    （--skip-monitoring-check，跳过）")
    else:
        try:
            up_map, redis_up_map = fetch_monitoring_state()
            not_monitored = check_monitoring(entries, up_map, redis_up_map)
            if not_monitored:
                for p in not_monitored:
                    print(f"  [!] 应监控但未生效（{p['reason']}）: {p['id']}  {p['uri']}")
            else:
                print(f"    计划 {len(entries)} 个集群均在监控且健康（up=1, redis_up=1）")
        except Exception as e:  # Prometheus 不可达等：尽力而为，不让脚本崩
            print(f"    [WARN] 查询 Prometheus 失败，跳过监控状态检查: {e}")

    if args.cron:
        # 漂移判据 = drift_paths + db_only + token_missing + not_monitored（应监控却未生效）。
        drift = (bool(drift_paths) or bool(db_only) or bool(token_missing)
                 or bool(not_monitored))
        if drift:
            lines = []
            if db_only:
                lines.append("硬问题——DB 在营但 AWS 无对应 RG（改名/非 ElastiCache?）：")
                lines += [f"  - {hp}" for hp in db_only]
            if token_missing:
                lines.append("硬问题——AUTH 集群缺 token（现有密码文件里没有，需人工补，绝不从 ozono 猜）：")
                lines += [f"  - {hp}" for hp in token_missing]
            if not_monitored:
                lines.append("硬问题——应监控但未有效监控（Prometheus 现状）：")
                lines += [f"  - {p['reason']}: {p['id']}  {p['uri']}" for p in not_monitored]
            if drift_paths:
                lines.append("现网三文件与 AWS+ozono 不同步，待 --apply 更新：")
                lines += [f"  - {p}" for p in drift_paths]
            if aws_only:
                lines.append("AWS 有 RG 但 CMDB 未登记在营（仅提示，未纳管?）：")
                lines += [f"  - {rid}" for rid in aws_only]
            subject = (f"[LKUS] AWS Redis 监控漂移待处理 "
                       f"(files={len(drift_paths)}, db_only={len(db_only)}, "
                       f"token_missing={len(token_missing)}, not_monitored={len(not_monitored)})")
            send_alert(subject, "\n".join(lines), args.webhook,
                       os.environ.get("FEISHU_SIGN_SECRET", ""))
        else:
            print("\n[cron] 无漂移、无硬问题，静默。")
        sys.exit(0)   # cron 恒 0：告警走飞书/日志，退出码不用于告警，避免包装脚本误判

    if not apply:
        print("\n这是 dry-run。确认无误后加 --apply 写回。")
    else:
        print("\n完成。Prometheus file_sd 会热加载 targets。")
        print("redis-password.file 若有变化，请重启 exporter 使新密码生效。")
    # db_only / token_missing / not_monitored 是需要人工关注的硬问题 → 非零退出码
    sys.exit(1 if db_only or token_missing or not_monitored else 0)


if __name__ == "__main__":
    main()
