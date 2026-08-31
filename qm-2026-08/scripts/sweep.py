#!/usr/bin/env python3
"""Fleet-wide information_schema sweep for QM-2026-08 source discovery. READ-ONLY."""
import json, sys
from pathlib import Path
from mcpcli import MCPSSEClient

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "raw" / "discovery"
OUT.mkdir(parents=True, exist_ok=True)

PAT = sys.argv[1] if len(sys.argv) > 1 else None
SERVERS = sys.argv[2:] if len(sys.argv) > 2 else None

SQL = """
SELECT TABLE_SCHEMA AS s, TABLE_NAME AS t, TABLE_ROWS AS n, UPDATE_TIME AS upd
FROM information_schema.TABLES
WHERE TABLE_SCHEMA NOT IN ('information_schema','mysql','performance_schema','sys')
  AND ({where})
ORDER BY TABLE_SCHEMA, TABLE_NAME
"""

def main():
    pats = PAT.split(",")
    where = " OR ".join([f"TABLE_NAME LIKE '%{p}%'" for p in pats])
    sql = SQL.format(where=where)
    c = MCPSSEClient(timeout=120); c.start(); c.initialize()
    servers = SERVERS
    if not servers:
        r = c.call("tools/call", {"name": "list_servers", "arguments": {}}, mid=5)
        txt = r["result"]["content"][0]["text"]
        servers = json.loads(txt)["mysql"]
    mid = 100
    hits = {}
    for srv in servers:
        mid += 1
        try:
            out = c.query(srv, sql, mid=mid)
        except Exception as e:
            print(f"[!!] {srv}: {e}"); continue
        rows = out.get("rows", [])
        if rows:
            hits[srv] = rows
            for r in rows:
                print(f"{srv:42s} {r['s']}.{r['t']:<52s} rows={r['n']} upd={r['upd']}")
    (OUT / f"sweep_{PAT.replace(',','_').replace('%','')}.json").write_text(
        json.dumps(hits, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[sweep] pattern={PAT} servers={len(servers)} hit_servers={len(hits)}")
    c.stop()

main()
