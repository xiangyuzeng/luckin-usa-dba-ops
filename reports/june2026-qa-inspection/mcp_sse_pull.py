#!/usr/bin/env python3
"""
Minimal MCP-over-SSE client for the Luckin db-gateway.
Pulls June 2026 QA-inspection raw data straight to raw/*.json (no transcription).

Gateway: http://10.238.3.43:8080/sse   (tool: mysql_query {server, sql})
Read-only. SELECT only.
"""
import json, sys, time, threading, queue
import requests

BASE = "http://10.238.3.43:8080"
SSE_URL = BASE + "/sse"

class MCPSSEClient:
    def __init__(self, timeout=60):
        self.timeout = timeout
        self.endpoint = None
        self.session = requests.Session()
        self.resp_by_id = {}
        self.events = {}         # id -> threading.Event
        self._endpoint_ready = threading.Event()
        self._stop = False
        self._t = threading.Thread(target=self._reader, daemon=True)

    def _reader(self):
        r = self.session.get(SSE_URL, stream=True, timeout=(10, self.timeout))
        event = None
        data_lines = []
        for raw in r.iter_lines(decode_unicode=True):
            if self._stop:
                break
            if raw is None:
                continue
            line = raw.rstrip("\r")
            if line == "":
                # dispatch accumulated event
                if data_lines:
                    data = "\n".join(data_lines)
                    self._dispatch(event, data)
                event, data_lines = None, []
                continue
            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())

    def _dispatch(self, event, data):
        if event == "endpoint":
            self.endpoint = data if data.startswith("http") else (BASE + data)
            self._endpoint_ready.set()
            return
        # message event: JSON-RPC
        try:
            msg = json.loads(data)
        except Exception:
            return
        mid = msg.get("id")
        if mid is not None:
            self.resp_by_id[mid] = msg
            ev = self.events.get(mid)
            if ev:
                ev.set()

    def start(self):
        self._t.start()
        if not self._endpoint_ready.wait(timeout=15):
            raise RuntimeError("SSE endpoint handshake timed out")

    def _post(self, payload):
        r = self.session.post(self.endpoint, json=payload,
                              headers={"Content-Type": "application/json"}, timeout=15)
        r.raise_for_status()

    def call(self, method, params, mid):
        ev = threading.Event()
        self.events[mid] = ev
        self._post({"jsonrpc": "2.0", "id": mid, "method": method, "params": params})
        if not ev.wait(timeout=self.timeout):
            raise RuntimeError(f"timeout waiting for id={mid} method={method}")
        return self.resp_by_id.pop(mid)

    def notify(self, method, params=None):
        self._post({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def initialize(self):
        res = self.call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "june-qa-pull", "version": "1.0"},
        }, mid=1)
        self.notify("notifications/initialized")
        return res

    def query(self, server, sql, mid):
        res = self.call("tools/call", {
            "name": "mysql_query",
            "arguments": {"server": server, "sql": sql},
        }, mid=mid)
        # tools/call result -> content[0].text is JSON string {rows, count}
        result = res.get("result", {})
        content = result.get("content", [])
        if content and isinstance(content, list):
            txt = content[0].get("text", "")
            try:
                return json.loads(txt)
            except Exception:
                return {"raw": txt}
        return res

    def stop(self):
        self._stop = True

if __name__ == "__main__":
    c = MCPSSEClient(timeout=60)
    c.start()
    print("[sse] endpoint:", c.endpoint)
    init = c.initialize()
    print("[sse] initialized:", json.dumps(init.get("result", {}).get("serverInfo", init.get("result")))[:200])
    # smoke test
    out = c.query("aws-luckyus-opqualitycontrol-rw",
                  "SELECT COUNT(*) AS n FROM luckyus_opqualitycontrol.t_shopcheck_data "
                  "WHERE check_date>='2026-06-01' AND check_date<'2026-07-01' AND status=1 AND deleted=0",
                  mid=2)
    print("[sse] smoke:", out)
    c.stop()
