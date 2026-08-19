#!/usr/bin/env python3
"""
Pull ALL July-2026 QA-inspection raw datasets straight to raw/*.json via MCP-SSE.
READ-ONLY (SELECT only). Reuses the proven May/June tables / joins with the July window.
"""
import json
from pathlib import Path
from mcp_sse_pull import MCPSSEClient

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
RAW.mkdir(exist_ok=True)
SRV = "aws-luckyus-opqualitycontrol-rw"
SHOP = "aws-luckyus-opshop-rw"

Q = {
 "july_headers": (SRV, """
   SELECT id, dept_id, large_category_id, large_category_name, check_date, status,
          checker_id, checker_name, process_status
   FROM luckyus_opqualitycontrol.t_shopcheck_data
   WHERE check_date>='2026-07-01' AND check_date<'2026-08-01'
     AND status=1 AND deleted=0 AND large_category_id IN (1084,1134,1184)
   ORDER BY id"""),

 "july_reports": (SRV, """
   SELECT shopcheck_data_id, score, score_desc, opportunity_desc, checker_post_code,
          shop_level, dept_id, large_category_id
   FROM luckyus_opqualitycontrol.t_shopcheck_report
   WHERE check_date>='2026-07-01' AND check_date<'2026-08-01'
     AND large_category_id IN (1084,1134,1184)
   ORDER BY shopcheck_data_id"""),

 "july_opps": (SRV, """
   SELECT o.id AS opp_id, o.shopcheck_data_id AS iid, o.check_item_id,
          o.remark, o.status AS opp_status,
          CASE WHEN o.first_appeal_detail IS NOT NULL AND o.first_appeal_detail<>'' THEN 1 ELSE 0 END AS has_first_appeal,
          CASE WHEN o.second_appeal_detail IS NOT NULL AND o.second_appeal_detail<>'' THEN 1 ELSE 0 END AS has_second_appeal,
          ic.deduction_type, ic.score_config,
          leaf.name AS leaf_cat_name, module.name AS module_name
   FROM luckyus_opqualitycontrol.t_shopcheck_opportunity o
   JOIN luckyus_opqualitycontrol.t_shopcheck_data d ON o.shopcheck_data_id=d.id
   JOIN luckyus_opqualitycontrol.t_shopcheck_item_config ic ON o.check_item_id=ic.id
   JOIN luckyus_opqualitycontrol.t_shopcheck_category_config leaf ON ic.category_config_id=leaf.id
   JOIN luckyus_opqualitycontrol.t_shopcheck_category_config module ON leaf.parent_id=module.id
   WHERE d.check_date>='2026-07-01' AND d.check_date<'2026-08-01'
     AND d.status=1 AND d.deleted=0 AND o.deleted=0
   ORDER BY o.shopcheck_data_id, o.id"""),

 "july_appeals": (SRV, """
   SELECT o.shopcheck_data_id AS iid, o.id AS opp_id, o.status AS opp_status,
          o.first_appeal_detail, o.second_appeal_detail
   FROM luckyus_opqualitycontrol.t_shopcheck_opportunity o
   JOIN luckyus_opqualitycontrol.t_shopcheck_data d ON o.shopcheck_data_id=d.id
   WHERE d.check_date>='2026-07-01' AND d.check_date<'2026-08-01'
     AND d.status=1 AND d.deleted=0 AND o.deleted=0
     AND ((o.first_appeal_detail IS NOT NULL AND o.first_appeal_detail<>'')
          OR (o.second_appeal_detail IS NOT NULL AND o.second_appeal_detail<>''))
   ORDER BY o.shopcheck_data_id, o.id"""),

 "july_stores": (SHOP, """
   SELECT id, dept_id, shop_no, shop_name, address, status, set_up_time, operation_area,
          shop_level, locality_name, administrative_area_name, sublocality_name, tenant, test_flag
   FROM luckyus_opshop.t_shop_info
   WHERE tenant='LKUS'
   ORDER BY shop_no"""),

 # June reports needed to extend the Jan-Jun inspector trend into July
 "june_reports_hist": (SRV, """
   SELECT shopcheck_data_id, score, checker_post_code, large_category_id
   FROM luckyus_opqualitycontrol.t_shopcheck_report
   WHERE check_date>='2026-06-01' AND check_date<'2026-07-01'
     AND large_category_id IN (1084,1134,1184)
   ORDER BY shopcheck_data_id"""),
}

def main():
    c = MCPSSEClient(timeout=120)
    c.start()
    c.initialize()
    mid = 10
    for name, (server, sql) in Q.items():
        mid += 1
        out = c.query(server, sql, mid=mid)
        rows = out.get("rows", [])
        (RAW / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[pull] {name:20s} -> {len(rows):4d} rows")
    c.stop()
    print("DONE")

if __name__ == "__main__":
    main()
