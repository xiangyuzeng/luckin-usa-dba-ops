import json
from pathlib import Path
from mcpcli import MCPSSEClient
RAW=Path(__file__).resolve().parent.parent/"raw"
ids=open('/tmp/claude-1001/-app/5cd33a08-7227-401b-b075-c60fb10f5461/scratchpad/oc_ids.txt').read().strip()
c=MCPSSEClient(timeout=180); c.start(); c.initialize()
out=c.query("aws-luckyus-salesorder-rw", f"""
 SELECT order_id, spu_name, spu_code, sku_name, sku_num, one_category_name, two_category_name
 FROM luckyus_sales_order.t_order_item
 WHERE tenant='LKUS' AND order_id IN ({ids}) LIMIT 300""", mid=3101)
rows=out.get("rows")
if rows is None:
    # discover the column names once, then retry
    out2=c.query("aws-luckyus-salesorder-rw",
      "SELECT COLUMN_NAME c FROM information_schema.COLUMNS WHERE TABLE_NAME='t_order_item' ORDER BY ORDINAL_POSITION LIMIT 80", mid=3102)
    print([r['c'] for r in out2.get("rows",[])])
else:
    (RAW/"fs_order_items.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding="utf-8")
    print("fs_order_items", len(rows))
c.stop()
