import json
from pathlib import Path
from mcpcli import MCPSSEClient
RAW=Path(__file__).resolve().parent.parent/"raw"
sql="""
 SELECT d.id AS check_no, d.dept_id, d.large_category_id, d.large_category_name, d.check_date,
        d.status AS submitted, d.deleted, d.checker_name, d.checker_id, d.create_time, d.modify_time,
        (SELECT COUNT(*) FROM luckyus_opqualitycontrol.t_shopcheck_opportunity o
          WHERE o.shopcheck_data_id=d.id AND o.deleted=0) AS opp_n,
        (SELECT r.score FROM luckyus_opqualitycontrol.t_shopcheck_report r
          WHERE r.shopcheck_data_id=d.id LIMIT 1) AS score
 FROM luckyus_opqualitycontrol.t_shopcheck_data d
 WHERE d.tenant='LKUS' AND d.check_date>='2026-01-01' AND d.check_date<'2026-07-01'
 ORDER BY d.check_date, d.id LIMIT 1500"""
c=MCPSSEClient(timeout=240); c.start(); c.initialize()
out=c.query("aws-luckyus-opqualitycontrol-rw", sql, mid=5001); rows=out.get("rows")
if rows is None: print("!!", str(out)[:300])
else:
    (RAW/"audit_headers_2026H1.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding="utf-8")
    log=json.loads((RAW/"_pull_log.json").read_text()); log["audit_headers_2026H1"]={"server":"aws-luckyus-opqualitycontrol-rw","rows":len(rows),"sql":sql}
    (RAW/"_pull_log.json").write_text(json.dumps(log,ensure_ascii=False,indent=1),encoding="utf-8")
    print("rows",len(rows))
c.stop()
