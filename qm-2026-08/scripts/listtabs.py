import json, sys
from pathlib import Path
from mcpcli import MCPSSEClient
srv = sys.argv[1]
c = MCPSSEClient(timeout=120); c.start(); c.initialize()
out = c.query(srv, """SELECT TABLE_SCHEMA s, TABLE_NAME t, TABLE_ROWS n, UPDATE_TIME upd
FROM information_schema.TABLES WHERE TABLE_SCHEMA NOT IN ('information_schema','mysql','performance_schema','sys')
ORDER BY TABLE_SCHEMA, TABLE_NAME""", mid=11)
rows = out.get("rows", [])
Path(f"../raw/discovery/tables_{srv}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
for r in rows: print(f"{r['s']}.{r['t']:<50s} {r['n']:>8} {r['upd']}")
print("count", len(rows))
c.stop()
