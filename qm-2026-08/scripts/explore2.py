import json
from pathlib import Path
from mcpcli import MCPSSEClient
OUT=Path("../raw/discovery"); SRM="aws-luckyus-scmsrm-rw"
Q={
 "jul_typecodes": (SRM, """
   SELECT d.operate_type, d.one_pqnc_type_code o1, d.two_pqnc_type_code o2, d.three_pqnc_type_code o3,
          COUNT(*) n, COUNT(DISTINCT d.pqnc_id) np
   FROM luckyus_scm_srm.t_pqnc_operate_detail d
   JOIN luckyus_scm_srm.t_pqnc p ON d.pqnc_id=p.id
   WHERE p.tenant='LKUS' AND p.delete_flag=0
     AND p.created_time>='2026-07-01' AND p.created_time<'2026-08-01'
   GROUP BY 1,2,3,4 ORDER BY 1,2,3,4 LIMIT 100"""),
 "jul_operate_types": (SRM, """
   SELECT d.operate_type, d.return_reason, COUNT(*) n, COUNT(DISTINCT d.pqnc_id) np
   FROM luckyus_scm_srm.t_pqnc_operate_detail d
   JOIN luckyus_scm_srm.t_pqnc p ON d.pqnc_id=p.id
   WHERE p.tenant='LKUS' AND p.created_time>='2026-07-01' AND p.created_time<'2026-08-01'
   GROUP BY 1,2 ORDER BY 1,2 LIMIT 50"""),
 "jul_resp_by_supplier": (SRM, """
   SELECT p.responsibility, s.name supplier, COUNT(*) n, ROUND(SUM(COALESCE(p.value_amount,0)),2) amt
   FROM luckyus_scm_srm.t_pqnc p
   LEFT JOIN luckyus_scm_srm.t_mdm_supplier s ON s.mid=p.supplier_mid AND s.tenant=p.tenant
   WHERE p.tenant='LKUS' AND p.delete_flag=0
     AND p.created_time>='2026-07-01' AND p.created_time<'2026-08-01'
   GROUP BY 1,2 ORDER BY 1,4 DESC LIMIT 60"""),
 "jul_nos": (SRM, """
   SELECT p.pqnc_no, p.status, p.responsibility, p.value_amount, p.supplier_mid,
          p.judgment_time, p.modified_time, p.delete_flag
   FROM luckyus_scm_srm.t_pqnc p
   WHERE p.tenant='LKUS' AND p.created_time>='2026-07-01' AND p.created_time<'2026-08-01'
   ORDER BY p.pqnc_no LIMIT 200"""),
}
c=MCPSSEClient(timeout=180); c.start(); c.initialize(); mid=300
for k,(s,sql) in Q.items():
    mid+=1; out=c.query(s,sql,mid=mid); rows=out.get("rows",out)
    (OUT/f"{k}.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding="utf-8")
    print(f"[{k}] {len(rows) if isinstance(rows,list) else out}")
    if isinstance(rows,list) and k!="jul_nos":
        for r in rows: print("   ", json.dumps(r,ensure_ascii=False)[:200])
c.stop()
