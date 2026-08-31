import json
from pathlib import Path
from mcpcli import MCPSSEClient
RAW=Path(__file__).resolve().parent.parent/"raw"
ids=open('/tmp/claude-1001/-app/5cd33a08-7227-401b-b075-c60fb10f5461/scratchpad/oc_ids.txt').read().strip()
sql=f"""SELECT id AS order_id, shop_id, shop_name, shop_number, status, pay_time, create_time,
        refund_status, comment_status
 FROM luckyus_sales_order.t_order
 WHERE tenant='LKUS' AND id IN ({ids}) LIMIT 100"""
# also the goods lines behind those orders
sql2=f"""SELECT order_id, goods_name, spec_name, quantity
 FROM luckyus_sales_order.t_order_goods
 WHERE tenant='LKUS' AND order_id IN ({ids}) LIMIT 300"""
c=MCPSSEClient(timeout=180); c.start(); c.initialize()
for name,q,mid in [("fs_orders",sql,3001),("fs_order_goods",sql2,3002)]:
    out=c.query("aws-luckyus-salesorder-rw",q,mid=mid); rows=out.get("rows")
    if rows is None: print(f"[{name}] !! {str(out)[:200]}"); continue
    (RAW/f"{name}.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding="utf-8")
    print(f"[{name}] {len(rows)} rows")
c.stop()
