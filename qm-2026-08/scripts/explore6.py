import json
from pathlib import Path
from mcpcli import MCPSSEClient
OUT=Path("../raw/discovery")
Q={
 "mdm_dict_sup": ("aws-luckyus-salesmarketing-rw", """
   SELECT d.*, l.language_value
   FROM luckyus_sales_marketing.t_mdm_dict d
   LEFT JOIN luckyus_sales_marketing.t_mdm_dict_language l
     ON l.relate_key=d.code AND l.language_code='en-US'
   WHERE d.type LIKE '%sup%' OR d.code LIKE '%sup%' OR d.name LIKE '%供应商%' LIMIT 100"""),
 "mdm_dict_types": ("aws-luckyus-salesmarketing-rw", """
   SELECT * FROM luckyus_sales_marketing.t_mdm_dict LIMIT 40"""),
 "enterprise_rows": ("aws-luckyus-scmsrm-rw", """
   SELECT id, enterprise_code, enterprise_name, type, status, sup_class, nc_type,
          submit_time, first_audit_time, second_audit_time, created_time, delete_flag, tenant
   FROM luckyus_scm_srm.t_enterprise ORDER BY created_time LIMIT 50"""),
}
c=MCPSSEClient(timeout=180); c.start(); c.initialize(); mid=700
for k,(s,sql) in Q.items():
    mid+=1; out=c.query(s,sql,mid=mid); rows=out.get("rows",out)
    (OUT/f"{k}.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding="utf-8")
    print(f"[{k}] {len(rows) if isinstance(rows,list) else str(out)[:180]}")
    if isinstance(rows,list):
        for r in rows[:14]: print("   ", json.dumps(r,ensure_ascii=False)[:220])
c.stop()
