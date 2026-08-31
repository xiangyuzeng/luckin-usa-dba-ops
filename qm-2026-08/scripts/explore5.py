import json
from pathlib import Path
from mcpcli import MCPSSEClient
OUT=Path("../raw/discovery"); SRM="aws-luckyus-scmsrm-rw"
Q={
 "sup_by_month": (SRM, """
   SELECT DATE_FORMAT(created_time,'%Y-%m') ym, sup_class, status, COUNT(*) n
   FROM luckyus_scm_srm.t_mdm_supplier
   WHERE tenant='LKUS' AND created_time>='2026-01-01' AND created_time<'2026-09-01'
   GROUP BY 1,2,3 ORDER BY 1,2 LIMIT 100"""),
 "sup_jul_aug": (SRM, """
   SELECT mid, name, sup_class, sup_nature, status, nc_type, created_time, creator_name,
          approve_instance_no, current_approve_node, business_source_mid
   FROM luckyus_scm_srm.t_mdm_supplier
   WHERE tenant='LKUS' AND created_time>='2026-07-01' AND created_time<'2026-09-01'
   ORDER BY created_time LIMIT 100"""),
 "enterprise_all": (SRM, """
   SELECT id, name, status, sup_class, nc_type, submit_time, first_audit_time, second_audit_time,
          created_time, delete_flag, tenant
   FROM luckyus_scm_srm.t_enterprise ORDER BY created_time LIMIT 50"""),
 "spec_draft_month": (SRM, """
   SELECT DATE_FORMAT(created_time,'%Y-%m') ym, status, COUNT(*) n
   FROM luckyus_scm_srm.t_mdm_goods_spec_draft
   WHERE tenant='LKUS' AND created_time>='2026-01-01' AND created_time<'2026-09-01'
   GROUP BY 1,2 ORDER BY 1,2 LIMIT 100"""),
}
c=MCPSSEClient(timeout=180); c.start(); c.initialize(); mid=600
for k,(s,sql) in Q.items():
    mid+=1; out=c.query(s,sql,mid=mid); rows=out.get("rows",out)
    (OUT/f"{k}.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding="utf-8")
    print(f"[{k}] {len(rows) if isinstance(rows,list) else str(out)[:200]}")
    if isinstance(rows,list):
        for r in rows[:30]: print("   ", json.dumps(r,ensure_ascii=False)[:210])
c.stop()
