#!/usr/bin/env python3
"""
test_sync_redis_monitoring.py — build_plan / render_files 纯函数单测。

只测纯逻辑 + 配置解析：不连 AWS / ldas、无需 pymysql、无需真实凭证
（load_ldas_conf 用例只读写临时文件 + 环境变量）：
    python3 -m unittest test_sync_redis_monitoring -v
或直接：
    python3 test_sync_redis_monitoring.py

覆盖的关键规则（都是这个脚本容易出错、出错就静默污染监控的地方）：
  · TLS 前缀取自 AWS（rediss:// / redis://），不是 CMDB。
  · token 只在 AuthTokenEnabled 时保留；非 AUTH 实例即使 CMDB 存了密码也必须丢空。
  · join 用 host_info，不用 app_name（app_name 常与真实 RG 名不符）。
  · db_only（在营却在 AWS 找不到）= 硬问题；aws_only（AWS 有但未纳管）= 待确认。
  · entries 按 uri 稳定排序，render 出的三文件前缀一致。
"""

import os
import tempfile
import unittest

import sync_redis_monitoring as m


def _aws(id, tls, auth):
    return {"id": id, "tls": tls, "auth": auth}


class TestBuildPlan(unittest.TestCase):
    # 注意：build_plan(db_rows, aws_map, existing_tokens) → 4-tuple。
    # token 只来自 existing_tokens（现有密码文件），绝不来自 ozono/db_rows。

    def test_auth_token_from_existing_file_rediss_prefix(self):
        aws = {"ep-a:6379": _aws("luckyus-isales-coupon", True, True)}
        db = [{"app": "luckyus_isales_coupondata",   # app_name 故意与 RG 名不符
               "hostport": "ep-a:6379"}]
        entries, db_only, aws_only, missing = m.build_plan(
            db, aws, {"ep-a:6379": "realA"})
        self.assertEqual((db_only, aws_only, missing), ([], [], []))
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertEqual(e["prefix"], "rediss://")
        self.assertEqual(e["uri"], "rediss://ep-a:6379")
        self.assertEqual(e["token"], "realA")       # 来自现有密码文件
        self.assertTrue(e["tls"])
        self.assertEqual(e["id"], "luckyus-isales-coupon")  # id 来自 AWS，不是 app_name

    def test_token_NEVER_from_ozono_regression_20260716(self):
        # 事故回归测试：即使 db_row 里带了 ozono 的（错）密码，token 也只认现有密码文件。
        # 这是 71 个 AUTH 集群被 --apply 打挂 redis_up=0 的直接防线。
        aws = {"ep-a:6379": _aws("luckyus-a", True, True)}
        db = [{"app": "a", "hostport": "ep-a:6379", "password": "OZONO-WRONG"}]
        entries, *_ = m.build_plan(db, aws, {"ep-a:6379": "real-good"})
        self.assertEqual(entries[0]["token"], "real-good")   # 绝不是 OZONO-WRONG

    def test_non_auth_always_empty_even_if_file_has_junk(self):
        # 非 AUTH：一律空，即使现有文件里意外存了东西（塞 token 会被 redis:// 拒）。
        aws = {"ep-b:6379": _aws("luckyus-web", False, False)}
        db = [{"app": "luckyus_web", "hostport": "ep-b:6379"}]
        entries, _, _, missing = m.build_plan(db, aws, {"ep-b:6379": "junk"})
        self.assertEqual(entries[0]["prefix"], "redis://")
        self.assertEqual(entries[0]["uri"], "redis://ep-b:6379")
        self.assertEqual(entries[0]["token"], "")   # 强制空
        self.assertFalse(entries[0]["tls"])
        self.assertEqual(missing, [])               # 非 AUTH 不缺 token

    def test_auth_missing_token_flagged_not_guessed(self):
        # AUTH 但现有文件没有该集群 → token_missing，先写空，绝不猜值。
        aws = {"ep-a:6379": _aws("luckyus-a", True, True)}
        db = [{"app": "a", "hostport": "ep-a:6379"}]
        entries, db_only, aws_only, missing = m.build_plan(db, aws, {})
        self.assertEqual(entries[0]["token"], "")
        self.assertEqual(missing, ["ep-a:6379"])
        self.assertEqual((db_only, aws_only), ([], []))

    def test_auth_present_but_blank_token_respected_not_missing(self):
        # 文件里 key 在、值为空 = 已纳管（尊重文件），不算 token_missing。
        aws = {"ep-a:6379": _aws("luckyus-a", True, True)}
        db = [{"app": "a", "hostport": "ep-a:6379"}]
        entries, _, _, missing = m.build_plan(db, aws, {"ep-a:6379": ""})
        self.assertEqual(entries[0]["token"], "")
        self.assertEqual(missing, [])

    def test_db_only_flagged_as_hard_problem(self):
        aws = {"ep-a:6379": _aws("luckyus-a", True, True)}
        db = [{"app": "a", "hostport": "ep-a:6379"},
              {"app": "ghost", "hostport": "ep-z:6379"}]
        entries, db_only, aws_only, _ = m.build_plan(db, aws, {"ep-a:6379": "x"})
        self.assertEqual([e["hostport"] for e in entries], ["ep-a:6379"])
        self.assertEqual(db_only, ["ep-z:6379"])
        self.assertEqual(aws_only, [])

    def test_aws_only_flagged_as_unmanaged(self):
        aws = {"ep-a:6379": _aws("luckyus-a", True, True),
               "ep-x:6379": _aws("luckyus-orphan", True, True)}
        db = [{"app": "a", "hostport": "ep-a:6379"}]
        _, db_only, aws_only, _ = m.build_plan(db, aws, {"ep-a:6379": "x"})
        self.assertEqual(db_only, [])
        self.assertEqual(aws_only, ["luckyus-orphan"])

    def test_entries_sorted_by_uri(self):
        aws = {"z-ep:6379": _aws("z", True, True),
               "a-ep:6379": _aws("a", True, True),
               "m-ep:6379": _aws("m", False, False)}
        db = [{"app": "z", "hostport": "z-ep:6379"},
              {"app": "a", "hostport": "a-ep:6379"},
              {"app": "m", "hostport": "m-ep:6379"}]
        entries, _, _, _ = m.build_plan(db, aws, {"z-ep:6379": "1", "a-ep:6379": "2"})
        uris = [e["uri"] for e in entries]
        self.assertEqual(uris, sorted(uris))
        # rediss:// 排在 redis:// 之后（字典序 rediss > redis），确保确定性
        self.assertEqual(uris, ["redis://m-ep:6379",
                                "rediss://a-ep:6379",
                                "rediss://z-ep:6379"])

    def test_db_only_and_aws_only_are_sorted(self):
        aws = {"b-x:6379": _aws("bbb", True, True),
               "a-x:6379": _aws("aaa", True, True)}
        db = [{"app": "g2", "hostport": "z2:6379"},
              {"app": "g1", "hostport": "y1:6379"}]
        _, db_only, aws_only, _ = m.build_plan(db, aws, {})
        self.assertEqual(db_only, ["y1:6379", "z2:6379"])
        self.assertEqual(aws_only, ["aaa", "bbb"])

    def test_shared_endpoint_deduped_to_single_entry(self):
        # 同一端点被多 app 登记 → 只产出一条；token 按 host:port 查，与哪条 app 行无关。
        aws = {"ep-a:6379": _aws("luckyus-shared", True, True)}
        db = [{"app": "app_one", "hostport": "ep-a:6379"},
              {"app": "app_two", "hostport": "ep-a:6379"}]
        entries, db_only, aws_only, missing = m.build_plan(
            db, aws, {"ep-a:6379": "tok"})
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["token"], "tok")
        self.assertEqual((db_only, aws_only, missing), ([], [], []))

    def test_duplicate_db_only_reported_once(self):
        db = [{"app": "g1", "hostport": "z:6379"},
              {"app": "g2", "hostport": "z:6379"}]
        _, db_only, _, _ = m.build_plan(db, {}, {})
        self.assertEqual(db_only, ["z:6379"])

    def test_empty_inputs(self):
        self.assertEqual(m.build_plan([], {}, {}), ([], [], [], []))


class TestRenderFiles(unittest.TestCase):
    def _entries(self):
        aws = {"ep-a:6379": _aws("luckyus-a", True, True),
               "ep-b:6379": _aws("luckyus-b", False, False)}
        db = [{"app": "a", "hostport": "ep-a:6379"},
              {"app": "b", "hostport": "ep-b:6379"}]
        entries, _, _, _ = m.build_plan(db, aws, {"ep-a:6379": "secretA"})
        return entries

    def test_render_shapes_and_prefix_consistency(self):
        import json
        pwd_text, sd_text = m.render_files(self._entries())
        pwd = json.loads(pwd_text)
        sd = json.loads(sd_text)

        # password.file: uri -> token
        self.assertEqual(pwd, {
            "redis://ep-b:6379": "",
            "rediss://ep-a:6379": "secretA",
        })

        # sd: 单个 target-group，targets 是 uri 列表，labels 空
        self.assertEqual(len(sd), 1)
        self.assertEqual(sd[0]["labels"], {})
        self.assertEqual(sd[0]["targets"],
                         ["redis://ep-b:6379", "rediss://ep-a:6379"])

        # 三文件前缀一致：password.file 的键集合 == sd targets 集合
        self.assertEqual(set(pwd.keys()), set(sd[0]["targets"]))
        # targets 无重复（重复会导致 Prometheus 对同一实例双抓）
        self.assertEqual(len(sd[0]["targets"]), len(set(sd[0]["targets"])))

    def test_render_empty(self):
        import json
        pwd_text, sd_text = m.render_files([])
        self.assertEqual(json.loads(pwd_text), {})
        self.assertEqual(json.loads(sd_text), [{"targets": [], "labels": {}}])


class TestLoadLdasConf(unittest.TestCase):
    """load_ldas_conf 只碰临时文件 + 环境变量，不连 ldas，无需凭证。"""

    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".conf")
        with os.fdopen(fd, "w") as f:
            f.write(text)
        self.addCleanup(os.unlink, path)
        return path

    _FULL = ("[ldas]\n"
             "host = h.example\n"
             "port = 3306\n"
             "user = u\n"
             "password = pw\n"
             "database = db\n")

    def setUp(self):
        # 每个用例前清掉 LDAS_PASSWORD，避免相互污染
        os.environ.pop("LDAS_PASSWORD", None)
        self.addCleanup(lambda: os.environ.pop("LDAS_PASSWORD", None))

    def test_full_conf_parsed(self):
        conf = m.load_ldas_conf(self._write(self._FULL))
        self.assertEqual(conf, {"host": "h.example", "port": 3306,
                                "user": "u", "password": "pw", "database": "db"})
        self.assertIsInstance(conf["port"], int)   # port 必须是 int，给 pymysql

    def test_env_password_overrides_file(self):
        os.environ["LDAS_PASSWORD"] = "from_env"
        conf = m.load_ldas_conf(self._write(self._FULL))
        self.assertEqual(conf["password"], "from_env")

    def test_env_password_when_file_blank(self):
        os.environ["LDAS_PASSWORD"] = "from_env"
        conf = m.load_ldas_conf(self._write(self._FULL.replace("password = pw", "password =")))
        self.assertEqual(conf["password"], "from_env")

    def test_missing_field_is_fatal(self):
        # 缺 password 且无 env 覆盖 → SystemExit，绝不半路裸奔连库
        with self.assertRaises(SystemExit):
            m.load_ldas_conf(self._write(self._FULL.replace("password = pw", "password =")))

    def test_missing_section_is_fatal(self):
        with self.assertRaises(SystemExit):
            m.load_ldas_conf(self._write("[other]\nx=1\n"))

    def test_missing_file_is_fatal(self):
        with self.assertRaises(SystemExit):
            m.load_ldas_conf("/nonexistent/path/ldas.conf")


class TestLoadAwsConf(unittest.TestCase):
    """可选 [aws] 段：缺段向后兼容返回 {}；profile / key-pair / 校验。只碰临时文件。"""

    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".conf")
        with os.fdopen(fd, "w") as f:
            f.write(text)
        self.addCleanup(os.unlink, path)
        return path

    _LDAS = ("[ldas]\nhost=h\nport=3306\nuser=u\npassword=pw\ndatabase=db\n")

    def test_no_aws_section_returns_empty(self):
        # 老配置（只有 [ldas]）→ {}，退回默认凭证链，完全向后兼容
        self.assertEqual(m.load_aws_conf(self._write(self._LDAS)), {})

    def test_missing_file_returns_empty(self):
        self.assertEqual(m.load_aws_conf("/nonexistent/ldas.conf"), {})

    def test_profile_only(self):
        conf = m.load_aws_conf(self._write(
            self._LDAS + "[aws]\nprofile = databasecheck\nregion = us-east-1\n"))
        self.assertEqual(conf, {"profile": "databasecheck", "access_key_id": "",
                                "secret_access_key": "", "region": "us-east-1"})

    def test_key_pair(self):
        conf = m.load_aws_conf(self._write(
            self._LDAS + "[aws]\naccess_key_id = AKIA1\nsecret_access_key = s3cr3t\n"))
        self.assertEqual(conf["access_key_id"], "AKIA1")
        self.assertEqual(conf["secret_access_key"], "s3cr3t")
        self.assertEqual(conf["profile"], "")

    def test_only_one_key_is_fatal(self):
        with self.assertRaises(SystemExit):
            m.load_aws_conf(self._write(self._LDAS + "[aws]\naccess_key_id = AKIA1\n"))

    def test_profile_and_key_together_is_fatal(self):
        with self.assertRaises(SystemExit):
            m.load_aws_conf(self._write(
                self._LDAS + "[aws]\nprofile = p\naccess_key_id = a\nsecret_access_key = s\n"))


class TestBuildAwsInvocation(unittest.TestCase):
    """argv/env 构造：密钥只走 env 绝不进 argv（防 ps 泄露）；profile 清冲突 env。"""

    _Q = "ReplicationGroups[]"

    def test_no_conf_inherits_env_default_chain(self):
        base = {"PATH": "/bin", "AWS_PROFILE": "host-default"}
        argv, env = m.build_aws_invocation(self._Q, "us-east-1", None, base)
        self.assertEqual(argv[0], "aws")
        self.assertNotIn("--profile", argv)
        self.assertEqual(env, base)                     # 原样继承，退回默认链

    def test_profile_goes_to_argv_and_clears_static_env_keys(self):
        base = {"PATH": "/bin", "AWS_ACCESS_KEY_ID": "HOSTKEY",
                "AWS_SECRET_ACCESS_KEY": "HOSTSEC", "AWS_SESSION_TOKEN": "t"}
        argv, env = m.build_aws_invocation(
            self._Q, "us-east-1", {"profile": "databasecheck"}, base)
        self.assertIn("--profile", argv)
        self.assertEqual(argv[argv.index("--profile") + 1], "databasecheck")
        self.assertEqual(env["AWS_PROFILE"], "databasecheck")
        # 主机默认静态密钥被清掉，确保 profile 权威
        self.assertNotIn("AWS_ACCESS_KEY_ID", env)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)
        self.assertNotIn("AWS_SESSION_TOKEN", env)

    def test_keys_go_to_env_NEVER_argv(self):
        base = {"PATH": "/bin", "AWS_PROFILE": "host-default"}
        conf = {"access_key_id": "AKIASECRET", "secret_access_key": "TOPSECRET"}
        argv, env = m.build_aws_invocation(self._Q, "us-east-1", conf, base)
        # 密钥绝不出现在命令行（否则 ps 泄露）
        self.assertNotIn("AKIASECRET", argv)
        self.assertNotIn("TOPSECRET", argv)
        self.assertNotIn("--profile", argv)
        # 走 env，且清掉可能冲突的 AWS_PROFILE
        self.assertEqual(env["AWS_ACCESS_KEY_ID"], "AKIASECRET")
        self.assertEqual(env["AWS_SECRET_ACCESS_KEY"], "TOPSECRET")
        self.assertNotIn("AWS_PROFILE", env)

    def test_region_and_query_reach_argv(self):
        argv, _ = m.build_aws_invocation(self._Q, "eu-west-1", None, {"PATH": "/bin"})
        self.assertIn("--region", argv)
        self.assertEqual(argv[argv.index("--region") + 1], "eu-west-1")
        self.assertIn(self._Q, argv)
        self.assertEqual(argv[-2:], ["--output", "json"])

    def test_does_not_mutate_base_env(self):
        base = {"PATH": "/bin"}
        m.build_aws_invocation(self._Q, "us-east-1",
                               {"profile": "p"}, base)
        self.assertEqual(base, {"PATH": "/bin"})        # base_env 不被就地改动


class TestParseExistingTokens(unittest.TestCase):
    """现有密码文件 = token 权威来源；解析成 host:port -> token，前缀无关。"""

    def test_strips_scheme_to_hostport(self):
        t = '{"rediss://ep-a:6379": "x", "redis://ep-b:6379": ""}'
        self.assertEqual(m.parse_existing_tokens(t),
                         {"ep-a:6379": "x", "ep-b:6379": ""})

    def test_lookup_survives_prefix_flip(self):
        # 文件记成 rediss://，即使集群后来被判为非 TLS，也应按 host:port 命中 token
        tokens = m.parse_existing_tokens('{"rediss://ep-a:6379": "tok"}')
        self.assertEqual(tokens.get("ep-a:6379"), "tok")

    def test_blank_or_empty_is_empty_dict(self):
        self.assertEqual(m.parse_existing_tokens(""), {})
        self.assertEqual(m.parse_existing_tokens("   "), {})

    def test_unparseable_is_empty_dict(self):
        self.assertEqual(m.parse_existing_tokens("not json"), {})


class TestEntriesFromTargets(unittest.TestCase):
    """AWS 不可达降级：把现网 targets 文件重建成 check_monitoring 能用的 entries。"""

    def test_reconstructs_id_and_uri(self):
        sd = ('[{"targets": ["rediss://ep-a:6379", "redis://ep-b:6379"], '
              '"labels": {}}]')
        self.assertEqual(m.entries_from_targets(sd), [
            {"id": "ep-b:6379", "uri": "redis://ep-b:6379"},    # 按 uri 排序
            {"id": "ep-a:6379", "uri": "rediss://ep-a:6379"},
        ])

    def test_dedupes_and_sorts_by_uri(self):
        sd = ('[{"targets": ["redis://b:1", "rediss://a:1", "redis://b:1"], '
              '"labels": {}}]')
        self.assertEqual([e["uri"] for e in m.entries_from_targets(sd)],
                         ["redis://b:1", "rediss://a:1"])

    def test_merges_multiple_target_groups(self):
        sd = ('[{"targets": ["redis://a:1"], "labels": {}},'
              ' {"targets": ["rediss://b:1"], "labels": {}}]')
        self.assertEqual([e["uri"] for e in m.entries_from_targets(sd)],
                         ["redis://a:1", "rediss://b:1"])

    def test_empty_or_broken_is_empty(self):
        self.assertEqual(m.entries_from_targets(""), [])
        self.assertEqual(m.entries_from_targets("   "), [])
        self.assertEqual(m.entries_from_targets("not json"), [])

    def test_output_feeds_check_monitoring(self):
        # 降级链路端到端：现网 targets → entries → check_monitoring 能挑出 not_scraped
        sd = '[{"targets": ["rediss://ep-a:6379"], "labels": {}}]'
        entries = m.entries_from_targets(sd)
        got = m.check_monitoring(entries, {}, {})     # Prometheus 里啥都没有
        self.assertEqual(got, [{"id": "ep-a:6379", "uri": "rediss://ep-a:6379",
                                "reason": "not_scraped"}])


class TestFetchAwsRgsDegrade(unittest.TestCase):
    """fetch_aws_rgs 遇权限/凭证/缺 CLI → 抛 AwsUnavailable（带原因），不冒泡成 traceback。"""

    def _patch(self, fn):
        orig = m.subprocess.check_output
        m.subprocess.check_output = fn
        self.addCleanup(setattr, m.subprocess, "check_output", orig)

    def test_access_denied_raises_AwsUnavailable_with_reason(self):
        import subprocess as sp

        def boom(*a, **k):
            raise sp.CalledProcessError(
                255, a[0], output=b"",
                stderr=b"An error occurred (AccessDenied) ... DescribeReplicationGroups")
        self._patch(boom)
        with self.assertRaises(m.AwsUnavailable) as ctx:
            m.fetch_aws_rgs()
        self.assertIn("AccessDenied", str(ctx.exception))     # 原因带进异常，供告警展示

    def test_missing_cli_raises_AwsUnavailable(self):
        def boom(*a, **k):
            raise FileNotFoundError("aws")
        self._patch(boom)
        with self.assertRaises(m.AwsUnavailable):
            m.fetch_aws_rgs()

    def test_nonzero_without_stderr_still_raises(self):
        import subprocess as sp

        def boom(*a, **k):
            raise sp.CalledProcessError(1, a[0], output=b"", stderr=None)
        self._patch(boom)
        with self.assertRaises(m.AwsUnavailable) as ctx:
            m.fetch_aws_rgs()
        self.assertIn("1", str(ctx.exception))                # 退出码兜底进消息


class TestCheckMonitoring(unittest.TestCase):
    """把"应监控"(entries) 和 Prometheus up/redis_up 现状比对，挑未有效监控的实例。"""

    def _entries(self):
        return [{"id": "luckyus-a", "uri": "rediss://ep-a:6379"},
                {"id": "luckyus-b", "uri": "redis://ep-b:6379"},
                {"id": "luckyus-c", "uri": "rediss://ep-c:6379"}]

    def test_all_healthy_returns_empty(self):
        up = {"rediss://ep-a:6379": 1, "redis://ep-b:6379": 1, "rediss://ep-c:6379": 1}
        ru = dict(up)
        self.assertEqual(m.check_monitoring(self._entries(), up, ru), [])

    def test_not_scraped_when_absent_from_prometheus(self):
        # ep-c 应监控但 Prometheus 里根本没有 → not_scraped（漏纳管/漂移未 apply）
        up = {"rediss://ep-a:6379": 1, "redis://ep-b:6379": 1}
        ru = dict(up)
        got = m.check_monitoring(self._entries(), up, ru)
        self.assertEqual(got, [{"id": "luckyus-c", "uri": "rediss://ep-c:6379",
                                "reason": "not_scraped"}])

    def test_scrape_down_when_up_zero(self):
        up = {"rediss://ep-a:6379": 1, "redis://ep-b:6379": 0, "rediss://ep-c:6379": 1}
        ru = {"rediss://ep-a:6379": 1, "redis://ep-b:6379": 0, "rediss://ep-c:6379": 1}
        got = m.check_monitoring(self._entries(), up, ru)
        self.assertEqual([(p["id"], p["reason"]) for p in got],
                         [("luckyus-b", "scrape_down")])

    def test_auth_down_when_up1_but_redis_up0(self):
        # 经典缺/错 token：抓到了(up=1)但连不上(redis_up=0)
        up = {"rediss://ep-a:6379": 1, "redis://ep-b:6379": 1, "rediss://ep-c:6379": 1}
        ru = {"rediss://ep-a:6379": 0, "redis://ep-b:6379": 1, "rediss://ep-c:6379": 1}
        got = m.check_monitoring(self._entries(), up, ru)
        self.assertEqual([(p["id"], p["reason"]) for p in got],
                         [("luckyus-a", "auth_down")])

    def test_results_sorted_by_uri(self):
        up, ru = {}, {}                     # 全缺 → 全 not_scraped，应按 uri 排序
        got = m.check_monitoring(self._entries(), up, ru)
        self.assertEqual([p["uri"] for p in got],
                         ["redis://ep-b:6379", "rediss://ep-a:6379", "rediss://ep-c:6379"])

    def test_empty_plan_returns_empty(self):
        self.assertEqual(m.check_monitoring([], {"x": 1}, {"x": 1}), [])


class TestFeishuPayload(unittest.TestCase):
    """飞书消息体 + 签名：都是纯函数，不碰网络。"""

    def test_payload_is_red_interactive_card(self):
        p = m.build_feishu_payload("subj", "line1\nline2")
        self.assertEqual(p["msg_type"], "interactive")
        self.assertEqual(p["card"]["header"]["template"], "red")  # 告警红色标题
        self.assertEqual(p["card"]["header"]["title"]["content"], "subj")
        div = p["card"]["elements"][0]
        self.assertEqual(div["text"]["tag"], "lark_md")
        self.assertEqual(div["text"]["content"], "line1\nline2")
        # 未签名时不应带 timestamp/sign（构造层不管签名）
        self.assertNotIn("timestamp", p)
        self.assertNotIn("sign", p)

    def test_payload_serializes_cjk_without_escaping(self):
        # send_alert 用 ensure_ascii=False；确保中文正文能进卡片且可序列化
        import json
        p = m.build_feishu_payload("[LKUS] 漂移", "  - 硬问题：ep-z:6379")
        s = json.dumps(p, ensure_ascii=False)
        self.assertIn("硬问题", s)

    def test_empty_body_has_placeholder(self):
        p = m.build_feishu_payload("subj", "   ")
        self.assertEqual(p["card"]["elements"][0]["text"]["content"], "（无详情）")

    def test_feishu_sign_is_deterministic_known_vector(self):
        # base64(HMAC-SHA256(key="1700000000\nmysecret", msg="")) —— 固定输入固定输出
        sig = m.feishu_sign("mysecret", "1700000000")
        self.assertEqual(sig, "Jp33/xXhCipDEpjyHvEyc7mRSyXWHbNz6J8+C3qQKNo=")
        self.assertEqual(m.feishu_sign("mysecret", "1700000000"), sig)
        # 不同 timestamp → 不同签名
        self.assertNotEqual(m.feishu_sign("mysecret", "1700000001"), sig)


class TestContentEquivalent(unittest.TestCase):
    """--cron 漂移门槛：语义比对，忽略 targets 顺序/键序/缩进；解析失败退回文本比。"""

    def test_identical_is_equivalent(self):
        t = '[{"targets": ["redis://b:6379", "rediss://a:6379"], "labels": {}}]'
        self.assertTrue(m.content_equivalent(t, t))

    def test_reordered_targets_is_equivalent(self):
        a = '[{"targets": ["redis://b:6379", "rediss://a:6379"], "labels": {}}]'
        b = '[{"targets": ["rediss://a:6379", "redis://b:6379"], "labels": {}}]'
        self.assertTrue(m.content_equivalent(a, b))   # 顺序颠倒 → 不算漂移

    def test_reordered_password_keys_is_equivalent(self):
        a = '{"rediss://a:6379": "x", "redis://b:6379": ""}'
        b = '{"redis://b:6379": "", "rediss://a:6379": "x"}'
        self.assertTrue(m.content_equivalent(a, b))   # 键序不同 → 不算漂移

    def test_different_indent_is_equivalent(self):
        obj = [{"targets": ["rediss://a:6379"], "labels": {}}]
        import json
        self.assertTrue(m.content_equivalent(
            json.dumps(obj, indent=2), json.dumps(obj, indent=4)))

    def test_real_content_change_is_drift(self):
        a = '[{"targets": ["rediss://a:6379"], "labels": {}}]'
        b = '[{"targets": ["rediss://a:6379", "rediss://c:6379"], "labels": {}}]'
        self.assertFalse(m.content_equivalent(a, b))  # 多一个 target → 真漂移

    def test_changed_password_value_is_drift(self):
        a = '{"rediss://a:6379": "old"}'
        b = '{"rediss://a:6379": "new"}'
        self.assertFalse(m.content_equivalent(a, b))

    def test_missing_file_empty_old_is_drift(self):
        # 现网文件不存在（old=""）→ 解析失败退回文本比 → 与非空新内容不等价 → 漂移
        self.assertFalse(m.content_equivalent("", '[{"targets": [], "labels": {}}]'))

    def test_unparseable_falls_back_to_text_compare(self):
        self.assertTrue(m.content_equivalent("not json  ", "  not json"))   # strip 后相同
        self.assertFalse(m.content_equivalent("not json", "also not json"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
