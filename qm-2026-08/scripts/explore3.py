import json
from pathlib import Path
from mcpcli import MCPSSEClient
OUT=Path("../raw/discovery"); QC="aws-luckyus-opqualitycontrol-rw"
Q={
 "cs_biz_tree": (QC, """
   SELECT id, code, name, parent_code, path, level, deleted, enabled
   FROM luckyus_opqualitycontrol.t_cs_biz_type_config
   WHERE tenant='LKUS' AND deleted=0 ORDER BY path, sort LIMIT 400"""),
 "cs_jul_sheets": (QC, """
   SELECT sheet_no, create_time, dept_id, feedback_source, status,
          l1_biz_type, l2_biz_type, l3_biz_type, comment_type, LEFT(feedback_detail,120) fd, LEFT(comment,120) cm
   FROM luckyus_opqualitycontrol.t_cs_sheet
   WHERE tenant='LKUS' AND create_time>='2026-07-01' AND create_time<'2026-08-01'
   ORDER BY create_time LIMIT 300"""),
 "cs_month_counts": (QC, """
   SELECT DATE_FORMAT(create_time,'%Y-%m') ym, COUNT(*) n, COUNT(DISTINCT dept_id) stores
   FROM luckyus_opqualitycontrol.t_cs_sheet
   WHERE tenant='LKUS' AND create_time>='2026-01-01' AND create_time<'2026-09-01'
   GROUP BY ym ORDER BY ym LIMIT 20"""),
}
c=MCPSSEClient(timeout=180); c.start(); c.initialize(); mid=400
for k,(s,sql) in Q.items():
    mid+=1; out=c.query(s,sql,mid=mid); rows=out.get("rows",out)
    (OUT/f"{k}.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding="utf-8")
    print(f"[{k}] {len(rows) if isinstance(rows,list) else out}")
c.stop()
