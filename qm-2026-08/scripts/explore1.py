import json
from pathlib import Path
from mcpcli import MCPSSEClient
OUT = Path("../raw/discovery"); OUT.mkdir(parents=True, exist_ok=True)
QC="aws-luckyus-opqualitycontrol-rw"; SRM="aws-luckyus-scmsrm-rw"
Q = {
 "item_config_scoreprofile": (QC, """
   SELECT deduction_type, score_config, score_start, COUNT(*) n
   FROM luckyus_opqualitycontrol.t_shopcheck_item_config
   WHERE deleted=0 GROUP BY deduction_type, score_config, score_start ORDER BY deduction_type LIMIT 100"""),
 "large_categories": (QC, """
   SELECT id, name, parent_id, path, status, check_approach, tenant, create_time
   FROM luckyus_opqualitycontrol.t_shopcheck_category_config
   WHERE parent_id=0 OR parent_id IS NULL ORDER BY id LIMIT 100"""),
 "aug_headers_count": (QC, """
   SELECT large_category_id, large_category_name, status, deleted, COUNT(*) n
   FROM luckyus_opqualitycontrol.t_shopcheck_data
   WHERE check_date>='2026-08-01' AND check_date<'2026-09-01'
   GROUP BY large_category_id, large_category_name, status, deleted ORDER BY large_category_id LIMIT 100"""),
 "appeal_sample": (QC, """
   SELECT o.id opp_id, o.shopcheck_data_id, o.status, LEFT(o.first_appeal_detail,900) fa
   FROM luckyus_opqualitycontrol.t_shopcheck_opportunity o
   JOIN luckyus_opqualitycontrol.t_shopcheck_data d ON o.shopcheck_data_id=d.id
   WHERE d.check_date>='2026-08-01' AND d.check_date<'2026-09-01'
     AND o.first_appeal_detail IS NOT NULL AND o.first_appeal_detail<>'' LIMIT 3"""),
 "report_oppdesc_sample": (QC, """
   SELECT shopcheck_data_id, score, score_desc, LEFT(opportunity_desc,900) od, check_approach
   FROM luckyus_opqualitycontrol.t_shopcheck_report
   WHERE check_date>='2026-08-01' AND check_date<'2026-09-01' AND large_category_id=1134
   ORDER BY shopcheck_data_id LIMIT 3"""),
 "discard_all": (QC, """
   SELECT * FROM luckyus_opqualitycontrol.t_shopcheck_discard ORDER BY id LIMIT 50"""),
 "cs_biz_type": (QC, """
   SELECT id, name, parent_id, path, status, tenant FROM luckyus_opqualitycontrol.t_cs_biz_type_config
   ORDER BY id LIMIT 200"""),
 "cs_source_cfg": (QC, """
   SELECT * FROM luckyus_opqualitycontrol.t_cs_feedback_source_config LIMIT 30"""),
 "pqnc_type": (SRM, """
   SELECT * FROM luckyus_scm_srm.t_pqnc_type LIMIT 20"""),
 "pqnc_type_lang": (SRM, """
   SELECT * FROM luckyus_scm_srm.t_pqnc_type_language LIMIT 30"""),
 "pqnc_aug_status": (SRM, """
   SELECT status, delete_flag, COUNT(*) n FROM luckyus_scm_srm.t_pqnc
   WHERE tenant='LKUS' AND created_time>='2026-08-01' AND created_time<'2026-09-01'
   GROUP BY status, delete_flag ORDER BY status LIMIT 50"""),
 "pqnc_jul_status": (SRM, """
   SELECT status, delete_flag, responsibility, COUNT(*) n, ROUND(SUM(COALESCE(value_amount,0)),2) amt
   FROM luckyus_scm_srm.t_pqnc
   WHERE tenant='LKUS' AND created_time>='2026-07-01' AND created_time<'2026-08-01'
   GROUP BY status, delete_flag, responsibility ORDER BY status, responsibility LIMIT 50"""),
}
c = MCPSSEClient(timeout=180); c.start(); c.initialize()
mid=200
for k,(s,sql) in Q.items():
    mid+=1
    out = c.query(s, sql, mid=mid)
    rows = out.get("rows", out)
    (OUT/f"{k}.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding="utf-8")
    print(f"[{k}] {len(rows) if isinstance(rows,list) else out}")
c.stop()
