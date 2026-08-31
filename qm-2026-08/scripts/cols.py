import json, sys
from pathlib import Path
from mcpcli import MCPSSEClient
srv = sys.argv[1]; tabs = sys.argv[2].split(",")
inlist = ",".join(f"'{t}'" for t in tabs)
c = MCPSSEClient(timeout=120); c.start(); c.initialize()
out = c.query(srv, f"""SELECT TABLE_NAME t, ORDINAL_POSITION p, COLUMN_NAME c, COLUMN_TYPE ty, COLUMN_COMMENT cm
FROM information_schema.COLUMNS WHERE TABLE_NAME IN ({inlist}) AND TABLE_SCHEMA NOT IN ('information_schema')
ORDER BY TABLE_NAME, ORDINAL_POSITION""", mid=12)
rows = out.get("rows", [])
cur=None
for r in rows:
    if r['t']!=cur: cur=r['t']; print(f"\n### {cur}")
    print(f"  {r['c']:<40s} {r['ty']:<28s} {r['cm']}")
Path(f"../raw/discovery/cols_{srv}_{tabs[0]}.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding="utf-8")
c.stop()
