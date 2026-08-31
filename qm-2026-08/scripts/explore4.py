import json
from pathlib import Path
from mcpcli import MCPSSEClient
OUT=Path("../raw/discovery"); SO="aws-luckyus-salesorder-rw"
Q={
 "oc_jul_kw": (SO, """
   SELECT id, order_id, dept_id, create_time, level, labels, comment_business_type,
          complaint_flag, LEFT(comment,200) cmt, origin
   FROM luckyus_sales_order.t_order_comment
   WHERE tenant='LKUS' AND create_time>='2026-07-01' AND create_time<'2026-08-01'
     AND (comment LIKE '%spoil%' OR comment LIKE '%sour%' OR comment LIKE '%gone bad%'
          OR comment LIKE '%curdled%' OR comment LIKE '%chemical taste%'
          OR comment LIKE '%Hair in%' OR comment LIKE '%piece of plastic%' OR comment LIKE '%expired milk%')
   ORDER BY create_time LIMIT 100"""),
 "oc_jul_labels": (SO, """
   SELECT LEFT(labels,120) lb, COUNT(*) n
   FROM luckyus_sales_order.t_order_comment
   WHERE tenant='LKUS' AND create_time>='2026-07-01' AND create_time<'2026-08-01'
   GROUP BY lb ORDER BY n DESC LIMIT 60"""),
 "oc_month": (SO, """
   SELECT DATE_FORMAT(create_time,'%Y-%m') ym, COUNT(*) n,
          SUM(CASE WHEN complaint_flag=1 THEN 1 ELSE 0 END) complaints,
          SUM(CASE WHEN level=3 THEN 1 ELSE 0 END) lvl3
   FROM luckyus_sales_order.t_order_comment
   WHERE tenant='LKUS' AND create_time>='2026-01-01' AND create_time<'2026-09-01'
   GROUP BY ym ORDER BY ym LIMIT 20"""),
}
c=MCPSSEClient(timeout=180); c.start(); c.initialize(); mid=500
for k,(s,sql) in Q.items():
    mid+=1; out=c.query(s,sql,mid=mid); rows=out.get("rows",out)
    (OUT/f"{k}.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding="utf-8")
    print(f"[{k}] {len(rows) if isinstance(rows,list) else out}")
c.stop()
