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
    def test_tls_auth_keeps_password_and_rediss_prefix(self):
        aws = {"ep-a:6379": _aws("luckyus-isales-coupon", True, True)}
        db = [{"app": "luckyus_isales_coupondata",   # app_name 故意与 RG 名不符
               "hostport": "ep-a:6379", "password": "secretA"}]
        entries, db_only, aws_only = m.build_plan(db, aws)
        self.assertEqual(db_only, [])
        self.assertEqual(aws_only, [])
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertEqual(e["prefix"], "rediss://")
        self.assertEqual(e["uri"], "rediss://ep-a:6379")
        self.assertEqual(e["token"], "secretA")     # AUTH → 保留
        self.assertTrue(e["tls"])
        self.assertEqual(e["id"], "luckyus-isales-coupon")  # id 来自 AWS，不是 app_name

    def test_non_auth_drops_password_and_redis_prefix(self):
        # 非 TLS / 非 AUTH：即使 CMDB 存了密码，也必须丢空，否则 redis:// 连接会被 Redis 拒。
        aws = {"ep-b:6379": _aws("luckyus-web", False, False)}
        db = [{"app": "luckyus_web", "hostport": "ep-b:6379", "password": "junkB"}]
        entries, _, _ = m.build_plan(db, aws)
        self.assertEqual(entries[0]["prefix"], "redis://")
        self.assertEqual(entries[0]["uri"], "redis://ep-b:6379")
        self.assertEqual(entries[0]["token"], "")   # 丢空
        self.assertFalse(entries[0]["tls"])

    def test_db_only_flagged_as_hard_problem(self):
        # 在营实例在 AWS 找不到对应 endpoint（改名 / 尾随空格 / 非 ElastiCache）。
        aws = {"ep-a:6379": _aws("luckyus-a", True, True)}
        db = [
            {"app": "a", "hostport": "ep-a:6379", "password": "x"},
            {"app": "ghost", "hostport": "ep-z:6379", "password": "z"},
        ]
        entries, db_only, aws_only = m.build_plan(db, aws)
        self.assertEqual([e["hostport"] for e in entries], ["ep-a:6379"])
        self.assertEqual(db_only, ["ep-z:6379"])
        self.assertEqual(aws_only, [])

    def test_aws_only_flagged_as_unmanaged(self):
        # AWS 有 RG 但 CMDB 未登记在营（未纳管）。
        aws = {
            "ep-a:6379": _aws("luckyus-a", True, True),
            "ep-x:6379": _aws("luckyus-orphan", True, True),
        }
        db = [{"app": "a", "hostport": "ep-a:6379", "password": "x"}]
        entries, db_only, aws_only = m.build_plan(db, aws)
        self.assertEqual(db_only, [])
        self.assertEqual(aws_only, ["luckyus-orphan"])

    def test_entries_sorted_by_uri(self):
        aws = {
            "z-ep:6379": _aws("z", True, True),
            "a-ep:6379": _aws("a", True, True),
            "m-ep:6379": _aws("m", False, False),
        }
        db = [
            {"app": "z", "hostport": "z-ep:6379", "password": "1"},
            {"app": "a", "hostport": "a-ep:6379", "password": "2"},
            {"app": "m", "hostport": "m-ep:6379", "password": "3"},
        ]
        entries, _, _ = m.build_plan(db, aws)
        uris = [e["uri"] for e in entries]
        self.assertEqual(uris, sorted(uris))
        # rediss:// 排在 redis:// 之后（字典序 rediss > redis），确保确定性
        self.assertEqual(uris, ["redis://m-ep:6379",
                                "rediss://a-ep:6379",
                                "rediss://z-ep:6379"])

    def test_db_only_and_aws_only_are_sorted(self):
        aws = {
            "b-x:6379": _aws("bbb", True, True),
            "a-x:6379": _aws("aaa", True, True),
        }
        db = [
            {"app": "g2", "hostport": "z2:6379", "password": ""},
            {"app": "g1", "hostport": "y1:6379", "password": ""},
        ]
        _, db_only, aws_only = m.build_plan(db, aws)
        self.assertEqual(db_only, ["y1:6379", "z2:6379"])
        self.assertEqual(aws_only, ["aaa", "bbb"])

    def test_shared_endpoint_deduped_to_single_entry(self):
        # 同一 Redis 端点被多个 app 登记（共用集群）→ 只应产出一条 entry，
        # 否则 file_sd targets 会重复、Prometheus 对同一实例双抓。
        aws = {"ep-a:6379": _aws("luckyus-shared", True, True)}
        db = [
            {"app": "app_one", "hostport": "ep-a:6379", "password": ""},
            {"app": "app_two", "hostport": "ep-a:6379", "password": "secretA"},
        ]
        entries, db_only, aws_only = m.build_plan(db, aws)
        self.assertEqual(len(entries), 1)
        # AUTH 集群：两行里保留非空密码那条
        self.assertEqual(entries[0]["token"], "secretA")
        self.assertEqual(db_only, [])
        self.assertEqual(aws_only, [])

    def test_duplicate_db_only_reported_once(self):
        aws = {}
        db = [
            {"app": "g1", "hostport": "z:6379", "password": ""},
            {"app": "g2", "hostport": "z:6379", "password": ""},
        ]
        _, db_only, _ = m.build_plan(db, aws)
        self.assertEqual(db_only, ["z:6379"])

    def test_empty_inputs(self):
        entries, db_only, aws_only = m.build_plan([], {})
        self.assertEqual((entries, db_only, aws_only), ([], [], []))

    def test_missing_password_field_treated_as_empty(self):
        # fetch_db_instances 用 `p or ""`，但 build_plan 也不该因缺 password 崩。
        aws = {"ep-a:6379": _aws("luckyus-a", True, True)}
        db = [{"app": "a", "hostport": "ep-a:6379", "password": ""}]
        entries, _, _ = m.build_plan(db, aws)
        self.assertEqual(entries[0]["token"], "")   # AUTH 但密码为空 → 仍是空


class TestRenderFiles(unittest.TestCase):
    def _entries(self):
        aws = {
            "ep-a:6379": _aws("luckyus-a", True, True),
            "ep-b:6379": _aws("luckyus-b", False, False),
        }
        db = [
            {"app": "a", "hostport": "ep-a:6379", "password": "secretA"},
            {"app": "b", "hostport": "ep-b:6379", "password": "junkB"},
        ]
        entries, _, _ = m.build_plan(db, aws)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
