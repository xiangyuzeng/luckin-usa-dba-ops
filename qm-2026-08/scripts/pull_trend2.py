import json
from pathlib import Path
from mcpcli import MCPSSEClient
RAW=Path(__file__).resolve().parent.parent/"raw"
Q={
 # responsibility as first recorded (= the value a report published in-month would have seen)
 "trend_pqnc_firstjudge": ("aws-luckyus-scmsrm-rw", """
   SELECT DATE_FORMAT(p.created_time,'%Y-%m') ym,
          (SELECT d.responsibility FROM luckyus_scm_srm.t_pqnc_operate_detail d
            WHERE d.pqnc_id=p.id AND d.operate_type=1 ORDER BY d.id LIMIT 1) first_resp,
          p.responsibility current_resp,
          COUNT(*) n, ROUND(SUM(COALESCE(p.value_amount,0)),2) value_amount
   FROM luckyus_scm_srm.t_pqnc p
   WHERE p.tenant='LKUS' AND p.delete_flag=0
     AND p.created_time>='2026-01-01' AND p.created_time<'2026-09-01'
   GROUP BY 1,2,3 ORDER BY 1,2,3 LIMIT 300"""),
 "trend_pqnc_rejudge": ("aws-luckyus-scmsrm-rw", """
   SELECT DATE_FORMAT(p.created_time,'%Y-%m') ym, COUNT(*) rejudged
   FROM luckyus_scm_srm.t_pqnc p
   WHERE p.tenant='LKUS' AND p.delete_flag=0
     AND p.created_time>='2026-01-01' AND p.created_time<'2026-09-01'
     AND (SELECT COUNT(*) FROM luckyus_scm_srm.t_pqnc_operate_detail d
           WHERE d.pqnc_id=p.id AND d.operate_type=1)>1
   GROUP BY 1 ORDER BY 1 LIMIT 20"""),
 # supplier-responsibility monthly cases by goods category, both bases
 "trend_supplier_cat": ("aws-luckyus-scmsrm-rw", """
   SELECT DATE_FORMAT(p.created_time,'%Y-%m') ym, p.responsibility, p.supplier_mid, p.spec_mid,
          COUNT(*) n, ROUND(SUM(COALESCE(p.value_amount,0)),2) amt
   FROM luckyus_scm_srm.t_pqnc p
   WHERE p.tenant='LKUS' AND p.delete_flag=0
     AND p.created_time>='2026-01-01' AND p.created_time<'2026-09-01'
   GROUP BY 1,2,3,4 ORDER BY 1,2 LIMIT 2000"""),
}
c=MCPSSEClient(timeout=240); c.start(); c.initialize(); mid=4000
for k,(s,sql) in Q.items():
    mid+=1; out=c.query(s,sql,mid=mid); rows=out.get("rows")
    if rows is None: print(f"[{k}] !! {str(out)[:200]}"); continue
    (RAW/f"{k}.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding="utf-8")
    print(f"[{k}] {len(rows)} rows")
    log=json.loads((RAW/"_pull_log.json").read_text()); log[k]={"server":s,"rows":len(rows),"sql":sql}
    (RAW/"_pull_log.json").write_text(json.dumps(log,ensure_ascii=False,indent=1),encoding="utf-8")
c.stop()
