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


class TestResolveRgEndpoint(unittest.TestCase):
    """端点解析：cluster mode 开/关走不同字段。2026-08-20 漏监控事故的直接防线。"""

    def test_cluster_mode_disabled_uses_primary_endpoint(self):
        r = {"id": "luckyus-iadmin", "ce": False,
             "ep": "master.luckyus-iadmin.vyllrs.use1.cache.amazonaws.com", "port": 6379,
             "cfg_ep": None, "cfg_port": None}
        self.assertEqual(
            m.resolve_rg_endpoint(r),
            ("master.luckyus-iadmin.vyllrs.use1.cache.amazonaws.com:6379", False))

    def test_cluster_mode_enabled_uses_configuration_endpoint_regression_20260820(self):
        # 真实数据：3 分片，NodeGroups[].PrimaryEndpoint 全 null，只有 clustercfg 可连。
        # 老代码在这里 `continue` 静默丢弃 → luckyus-icdpactivityengine 长期漏监控。
        r = {"id": "luckyus-icdpactivityengine", "ce": True,
             "ep": None, "port": None,
             "cfg_ep": "clustercfg.luckyus-icdpactivityengine.vyllrs.use1.cache.amazonaws.com",
             "cfg_port": 6379}
        hostport, cluster = m.resolve_rg_endpoint(r)
        self.assertEqual(
            hostport,
            "clustercfg.luckyus-icdpactivityengine.vyllrs.use1.cache.amazonaws.com:6379")
        self.assertTrue(cluster)

    def test_cluster_mode_enabled_prefers_config_over_primary_if_both_present(self):
        # 万一 AWS 两个都给：分片集群必须连 clustercfg，连某个分片 primary 只能看到 1/N
        r = {"id": "rg", "ce": True, "ep": "shard1", "port": 6379,
             "cfg_ep": "clustercfg", "cfg_port": 6379}
        self.assertEqual(m.resolve_rg_endpoint(r), ("clustercfg:6379", True))

    def test_non_cluster_falls_back_to_config_endpoint(self):
        # ce 为假但只有 cfg（字段缺失/形态异常）→ 兜底用它，总比丢掉强
        r = {"id": "rg", "ce": False, "ep": None, "port": None,
             "cfg_ep": "cfg-host", "cfg_port": 6379}
        self.assertEqual(m.resolve_rg_endpoint(r), ("cfg-host:6379", False))

    def test_no_endpoint_at_all_returns_none(self):
        r = {"id": "rg-creating", "ce": False, "ep": None, "port": None,
             "cfg_ep": None, "cfg_port": None}
        self.assertEqual(m.resolve_rg_endpoint(r), (None, False))

    def test_missing_port_is_not_usable(self):
        # 有地址没端口拼不出 host:port，别拼出 "host:None" 这种鬼 target
        self.assertEqual(
            m.resolve_rg_endpoint({"id": "rg", "ce": False, "ep": "h", "port": None}),
            (None, False))


class TestFetchAwsRgsParse(unittest.TestCase):
    """fetch_aws_rgs 解析层：两种形态都要进 aws_map，取不到端点的必须上报而不是静默丢。"""

    def _patch_output(self, payload):
        import json as _json
        orig = m.subprocess.check_output
        m.subprocess.check_output = lambda *a, **k: _json.dumps(payload).encode()
        self.addCleanup(setattr, m.subprocess, "check_output", orig)

    def test_both_cluster_shapes_land_in_aws_map(self):
        self._patch_output([
            {"id": "luckyus-iadmin", "tls": True, "auth": True, "status": "available",
             "ce": False, "ngids": ["0001"], "ep": "master.iadmin", "port": 6379,
             "cfg_ep": None, "cfg_port": None},
            {"id": "luckyus-icdpactivityengine", "tls": True, "auth": True,
             "status": "available", "ce": True, "ngids": ["0001", "0002", "0003"],
             "ep": None, "port": None, "cfg_ep": "clustercfg.icdp", "cfg_port": 6379},
        ])
        amap, no_endpoint = m.fetch_aws_rgs()
        self.assertEqual(no_endpoint, [])
        self.assertEqual(sorted(amap), ["clustercfg.icdp:6379", "master.iadmin:6379"])
        self.assertEqual(amap["clustercfg.icdp:6379"],
                         {"id": "luckyus-icdpactivityengine", "tls": True, "auth": True,
                          "cluster": True, "shards": 3})
        self.assertFalse(amap["master.iadmin:6379"]["cluster"])
        self.assertEqual(amap["master.iadmin:6379"]["shards"], 1)

    def test_rg_without_endpoint_is_reported_not_silently_dropped(self):
        self._patch_output([
            {"id": "luckyus-new", "tls": False, "auth": False, "status": "creating",
             "ce": False, "ngids": None, "ep": None, "port": None,
             "cfg_ep": None, "cfg_port": None},
        ])
        amap, no_endpoint = m.fetch_aws_rgs()
        self.assertEqual(amap, {})
        self.assertEqual(no_endpoint,
                         [{"id": "luckyus-new", "status": "creating", "cluster": False}])

    def test_no_endpoint_sorted_by_id(self):
        self._patch_output([
            {"id": "zzz", "tls": False, "auth": False, "status": "creating", "ce": False},
            {"id": "aaa", "tls": False, "auth": False, "status": "creating", "ce": False},
        ])
        _, no_endpoint = m.fetch_aws_rgs()
        self.assertEqual([r["id"] for r in no_endpoint], ["aaa", "zzz"])


class TestBuildPlanClusterMode(unittest.TestCase):
    """cluster-mode 集群 join 后应与普通集群一视同仁地进三文件，并带上 cluster 标记。"""

    def test_cluster_entry_joins_and_keeps_flag(self):
        hp = "clustercfg.luckyus-icdpactivityengine.vyllrs.use1.cache.amazonaws.com:6379"
        aws = {hp: {"id": "luckyus-icdpactivityengine", "tls": True, "auth": True,
                    "cluster": True, "shards": 3}}
        db = [{"app": "luckyus_icdpactivityengine", "hostport": hp}]   # ozono 登记的正是 clustercfg
        entries, db_only, aws_only, token_missing = m.build_plan(db, aws, {hp: "tok"})
        self.assertEqual(db_only, [])          # 不再被误报成"AWS 无对应 RG"
        self.assertEqual(aws_only, [])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["uri"], "rediss://" + hp)
        self.assertEqual(entries[0]["token"], "tok")
        self.assertTrue(entries[0]["cluster"])
        self.assertEqual(entries[0]["shards"], 3)

    def test_plain_entry_cluster_flag_defaults_false(self):
        aws = {"ep-a:6379": _aws("rg", False, False)}     # 老 helper 不带 cluster 键
        entries, _, _, _ = m.build_plan(
            [{"app": "a", "hostport": "ep-a:6379"}], aws, {})
        self.assertFalse(entries[0]["cluster"])
        self.assertEqual(entries[0]["shards"], 0)


def _nodes(rg, n=3, port=6379):
    """构造 fetch_aws_nodes 形状的节点表：rg-000X-001，端点排序稳定。"""
    return {rg: [{"node": f"{rg}-000{i}-001", "hostport": f"{rg}-000{i}-001.host:{port}"}
                 for i in range(1, n + 1)]}


class TestExpandClusterEntries(unittest.TestCase):
    """--expand-shards：分片集群展开成每节点 target。clustercfg 单 target 会随机落到
    N 个节点之一（2026-08-20 实测：一条 DNS 名 6 个 IP、顺序每次轮换），指标不可用。"""

    def _cluster_entry(self, token="T0K"):
        return {"hostport": "clustercfg.rg1:6379", "prefix": "rediss://",
                "uri": "rediss://clustercfg.rg1:6379", "token": token,
                "id": "rg1", "tls": True, "cluster": True, "shards": 3}

    def test_expands_to_one_target_per_node(self):
        render, pwd, missing = m.expand_cluster_entries(
            [self._cluster_entry()], _nodes("rg1"), {})
        self.assertEqual(missing, [])
        self.assertEqual([e["uri"] for e in render],
                         ["rediss://rg1-0001-001.host:6379",
                          "rediss://rg1-0002-001.host:6379",
                          "rediss://rg1-0003-001.host:6379"])
        self.assertEqual([e["id"] for e in render],
                         ["rg1-0001-001", "rg1-0002-001", "rg1-0003-001"])
        for e in render:                       # 前缀/TLS/父集群信息随节点带下去
            self.assertEqual(e["prefix"], "rediss://")
            self.assertEqual(e["token"], "T0K")     # AUTH token 是集群级的，N 个节点同一个
            self.assertEqual(e["parent"], "rg1")
            self.assertTrue(e["cluster"])

    def test_non_cluster_entries_pass_through_untouched(self):
        plain = {"hostport": "master.a:6379", "prefix": "redis://",
                 "uri": "redis://master.a:6379", "token": "", "id": "a",
                 "tls": False, "cluster": False, "shards": 0}
        render, pwd, missing = m.expand_cluster_entries([plain], _nodes("rg1"), {})
        self.assertEqual(render, [plain])
        self.assertEqual(pwd, [plain])         # 没有分片集群 → 不多留任何 key
        self.assertEqual(missing, [])

    def test_parent_key_kept_in_password_file_for_token_roundtrip(self):
        render, pwd, _ = m.expand_cluster_entries(
            [self._cluster_entry()], _nodes("rg1"), {})
        uris = [e["uri"] for e in pwd]
        self.assertIn("rediss://clustercfg.rg1:6379", uris)   # 父 key 必须留下
        self.assertEqual(len(pwd), len(render) + 1)

    def test_token_roundtrip_is_idempotent_across_runs(self):
        """回归：展开后若密码文件只剩节点 key，下一轮就找不到 clustercfg 的 token →
        build_plan 报 token_missing 并置空 → 再 --apply 会把 N 个节点的 token 全清掉。"""
        hp = "clustercfg.rg1:6379"
        aws = {hp: {"id": "rg1", "tls": True, "auth": True, "cluster": True, "shards": 3}}
        db = [{"app": "rg1", "hostport": hp}]

        # 第 1 轮：人工把真实 token 放进密码文件
        e1, _, _, tm1 = m.build_plan(db, aws, {hp: "T0K"})
        self.assertEqual(tm1, [])
        r1, pwd1, _ = m.expand_cluster_entries(e1, _nodes("rg1"), {hp: "T0K"})
        pwd_text, sd_text = m.render_files(r1, pwd1)

        # 第 2 轮：只读回上一轮写下的密码文件
        toks = m.parse_existing_tokens(pwd_text)
        e2, _, _, tm2 = m.build_plan(db, aws, toks)
        self.assertEqual(tm2, [])                       # 不再误报 token_missing
        r2, pwd2, _ = m.expand_cluster_entries(e2, _nodes("rg1"), toks)
        self.assertEqual(m.render_files(r2, pwd2), (pwd_text, sd_text))   # 完全幂等
        for e in r2:
            self.assertEqual(e["token"], "T0K")         # token 没被清空

    def test_without_parent_key_the_token_would_be_lost_next_run(self):
        """反证上一条：不保留父 key 时，第 2 轮 token_missing 会复发（故意留档）。"""
        hp = "clustercfg.rg1:6379"
        aws = {hp: {"id": "rg1", "tls": True, "auth": True, "cluster": True, "shards": 3}}
        db = [{"app": "rg1", "hostport": hp}]
        e1, _, _, _ = m.build_plan(db, aws, {hp: "T0K"})
        r1, _, _ = m.expand_cluster_entries(e1, _nodes("rg1"), {hp: "T0K"})
        pwd_text, _ = m.render_files(r1)                 # ← 不传 pwd_entries = 丢父 key
        _, _, _, tm2 = m.build_plan(db, aws, m.parse_existing_tokens(pwd_text))
        self.assertEqual(tm2, [hp])                      # token 丢了

    def test_per_node_token_override_wins_over_parent(self):
        toks = {"rg1-0002-001.host:6379": "NODE2"}
        render, _, _ = m.expand_cluster_entries(
            [self._cluster_entry("PARENT")], _nodes("rg1"), toks)
        got = {e["id"]: e["token"] for e in render}
        self.assertEqual(got["rg1-0002-001"], "NODE2")
        self.assertEqual(got["rg1-0001-001"], "PARENT")

    def test_blank_node_token_respected_not_overridden_by_parent(self):
        # 显式空值 = 人工声明"这个节点不带密码"，不能被父 token 覆盖
        toks = {"rg1-0001-001.host:6379": ""}
        render, _, _ = m.expand_cluster_entries(
            [self._cluster_entry("PARENT")], _nodes("rg1"), toks)
        self.assertEqual({e["id"]: e["token"] for e in render}["rg1-0001-001"], "")

    def test_missing_nodes_is_hard_problem_and_falls_back(self):
        render, pwd, missing = m.expand_cluster_entries(
            [self._cluster_entry()], {}, {})              # 拿不到任何节点
        self.assertEqual(missing, ["rg1"])
        self.assertEqual([e["uri"] for e in render], ["rediss://clustercfg.rg1:6379"])
        self.assertEqual(pwd, render)                     # 没展开就别多留 key

    def test_render_sorted_by_uri_across_mixed_entries(self):
        plain = {"hostport": "zzz:6379", "prefix": "redis://", "uri": "redis://zzz:6379",
                 "token": "", "id": "zzz", "tls": False, "cluster": False, "shards": 0}
        render, _, _ = m.expand_cluster_entries(
            [self._cluster_entry(), plain], _nodes("rg1"), {})
        self.assertEqual([e["uri"] for e in render], sorted(e["uri"] for e in render))

    def test_empty_input(self):
        self.assertEqual(m.expand_cluster_entries([], {}, {}), ([], [], []))


class TestRenderFilesWithPwdEntries(unittest.TestCase):

    def test_pwd_entries_adds_keys_without_adding_targets(self):
        node = {"uri": "rediss://n1:6379", "token": "T"}
        parent = {"uri": "rediss://clustercfg:6379", "token": "T"}
        pwd_text, sd_text = m.render_files([node], [node, parent])
        import json as _json
        self.assertEqual(sorted(_json.loads(pwd_text)),
                         ["rediss://clustercfg:6379", "rediss://n1:6379"])
        self.assertEqual(_json.loads(sd_text)[0]["targets"], ["rediss://n1:6379"])

    def test_default_pwd_entries_is_entries(self):
        e = [{"uri": "redis://a:6379", "token": ""}]
        self.assertEqual(m.render_files(e), m.render_files(e, e))


class TestFetchAwsNodes(unittest.TestCase):

    def _patch_output(self, payload):
        import json as _json
        orig = m.subprocess.check_output
        m.subprocess.check_output = lambda *a, **k: _json.dumps(payload).encode()
        self.addCleanup(setattr, m.subprocess, "check_output", orig)

    def test_groups_by_rg_and_sorts(self):
        self._patch_output([
            {"rg": "rg1", "node": "rg1-0002-001", "ep": "b.host", "port": 6379},
            {"rg": "rg1", "node": "rg1-0001-001", "ep": "a.host", "port": 6379},
            {"rg": "rg2", "node": "rg2-0001-001", "ep": "c.host", "port": 6379},
        ])
        by_rg = m.fetch_aws_nodes()
        self.assertEqual([n["hostport"] for n in by_rg["rg1"]],
                         ["a.host:6379", "b.host:6379"])
        self.assertEqual(len(by_rg["rg2"]), 1)

    def test_rows_without_rg_or_endpoint_skipped(self):
        self._patch_output([
            {"rg": None, "node": "standalone", "ep": "x.host", "port": 6379},
            {"rg": "rg1", "node": "rg1-0001-001", "ep": None, "port": None},
        ])
        self.assertEqual(m.fetch_aws_nodes(), {})

    def test_aws_failure_raises_AwsUnavailable(self):
        import subprocess as sp

        def boom(*a, **k):
            raise sp.CalledProcessError(255, a[0], output=b"",
                                        stderr=b"AccessDenied DescribeCacheClusters")
        orig = m.subprocess.check_output
        m.subprocess.check_output = boom
        self.addCleanup(setattr, m.subprocess, "check_output", orig)
        with self.assertRaises(m.AwsUnavailable) as ctx:
            m.fetch_aws_nodes()
        self.assertIn("AccessDenied", str(ctx.exception))


class TestBuildAwsInvocationOperations(unittest.TestCase):
    """凭证注入只有一份实现，两个 elasticache 操作共用（--expand-shards 需要第二个）。"""

    def test_default_operation_unchanged(self):
        argv, _ = m.build_aws_invocation("Q", "us-east-1", {}, {})
        self.assertIn("describe-replication-groups", argv)
        self.assertNotIn("--show-cache-node-info", argv)

    def test_describe_cache_clusters_with_extra_args(self):
        argv, _ = m.build_aws_invocation(
            "Q", "us-east-1", {}, {}, operation="describe-cache-clusters",
            extra_args=("--show-cache-node-info",))
        self.assertEqual(argv[:4],
                         ["aws", "elasticache", "describe-cache-clusters",
                          "--show-cache-node-info"])
        self.assertIn("--region", argv)

    def test_credentials_still_never_reach_argv(self):
        conf = {"access_key_id": "AKIA_X", "secret_access_key": "SEKRIT"}
        argv, env = m.build_aws_invocation(
            "Q", "us-east-1", conf, {}, operation="describe-cache-clusters",
            extra_args=("--show-cache-node-info",))
        self.assertNotIn("SEKRIT", " ".join(argv))       # ps 泄露防线，对新操作同样成立
        self.assertEqual(env["AWS_SECRET_ACCESS_KEY"], "SEKRIT")


class TestFeishuRetryable(unittest.TestCase):
    """限频要重试，签名错/机器人停用不重试（重试只是把同样的错再犯两遍）。"""

    def test_11232_frequency_limited_is_retryable(self):
        # 2026-08-20 早晨 cron 实际吃到的返回体
        self.assertTrue(m.feishu_retryable(
            11232, "frequency limited psm[lark.oapi.app_platform_runtime]appID[1500]"))

    def test_msg_based_detection_for_sibling_codes(self):
        self.assertTrue(m.feishu_retryable(99999, "Rate limit exceeded"))
        self.assertTrue(m.feishu_retryable(0, "too many requests"))

    def test_signature_and_disabled_bot_not_retryable(self):
        self.assertFalse(m.feishu_retryable(19021, "sign match fail"))
        self.assertFalse(m.feishu_retryable(19001, "param invalid"))

    def test_no_message_defaults_to_not_retryable(self):
        self.assertFalse(m.feishu_retryable(12345))


class TestRedactWebhook(unittest.TestCase):

    def test_token_masked(self):
        out = m.redact_webhook(
            "https://open.feishu.cn/open-apis/bot/v2/hook/abcd1234-secret-token")
        self.assertNotIn("secret-token", out)
        self.assertTrue(out.endswith("/abcd***"))
        self.assertIn("open.feishu.cn", out)          # 前缀保留，日志仍可辨认是哪个端点

    def test_empty_and_degenerate(self):
        self.assertEqual(m.redact_webhook(""), "(未配置)")
        self.assertEqual(m.redact_webhook("nohost"), "***")


class TestSendAlertRetry(unittest.TestCase):
    """send_alert 的投递语义：限频重试、不可重试立即放弃、全失败要留可 grep 标记。"""

    def _capture(self, responses):
        """responses: 每次调用返回的 bytes，或抛出的异常。返回 (调用次数记录, 打印文本)。"""
        import io as _io
        import contextlib
        calls = []

        class FakeResp:
            def __init__(self, b): self._b = b
            def read(self): return self._b

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            r = responses[min(len(calls) - 1, len(responses) - 1)]
            if isinstance(r, Exception):
                raise r
            return FakeResp(r)

        import urllib.request as ur
        orig = ur.urlopen
        ur.urlopen = fake_urlopen
        self.addCleanup(setattr, ur, "urlopen", orig)
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            m.send_alert("SUBJ", "BODY", "https://open.feishu.cn/hook/tok123456",
                         sleeper=lambda _s: None)          # 不真的等
        return calls, buf.getvalue()

    def test_rate_limited_then_success(self):
        calls, out = self._capture([
            b'{"code":11232,"msg":"frequency limited"}',
            b'{"code":0}',
        ])
        self.assertEqual(len(calls), 2)                    # 重试了一次就成功
        self.assertIn("告警已发送到飞书", out)
        self.assertIn("第 2 次尝试", out)
        self.assertNotIn("ALERT-UNDELIVERED", out)

    def test_rate_limited_all_attempts_marks_undelivered(self):
        calls, out = self._capture([b'{"code":11232,"msg":"frequency limited"}'])
        self.assertEqual(len(calls), m.FEISHU_MAX_ATTEMPTS)
        self.assertIn("[ALERT-UNDELIVERED]", out)          # 可 grep 的醒目标记
        self.assertIn("SUBJ", out)                         # 正文仍落日志，不丢信息
        self.assertIn("BODY", out)

    def test_non_retryable_gives_up_immediately(self):
        calls, out = self._capture([b'{"code":19021,"msg":"sign match fail"}'])
        self.assertEqual(len(calls), 1)                    # 签名错不重试
        self.assertIn("[ALERT-UNDELIVERED]", out)

    def test_network_error_is_retried(self):
        calls, out = self._capture([OSError("connection reset")])
        self.assertEqual(len(calls), m.FEISHU_MAX_ATTEMPTS)
        self.assertIn("[ALERT-UNDELIVERED]", out)

    def test_first_try_success_makes_one_call(self):
        calls, out = self._capture([b'{"code":0}'])
        self.assertEqual(len(calls), 1)
        self.assertNotIn("第 2 次尝试", out)

    def test_webhook_token_never_printed(self):
        _, out = self._capture([b'{"code":0}'])
        self.assertNotIn("tok123456", out)                 # 完整 URL 绝不进日志
        _, out2 = self._capture([b'{"code":11232,"msg":"frequency limited"}'])
        self.assertNotIn("tok123456", out2)

    def test_unparseable_body_treated_as_success(self):
        calls, out = self._capture([b'not json'])
        self.assertEqual(len(calls), 1)
        self.assertIn("告警已发送到飞书", out)

    def test_no_webhook_still_prints_alert(self):
        import io as _io, contextlib
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            m.send_alert("S", "B", "")
        self.assertIn("S", buf.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
